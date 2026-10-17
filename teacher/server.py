import argparse
import json
import mimetypes
import signal
import subprocess
import threading
import time
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from . import config, engine, network, lessons
from .curriculum import TOPICS, BY_ID
from .speech import Speech, transcribe
from .store import Store
from .profiles import Profiles

TURN_LOCK = threading.Lock()


def ensure_lesson_summary(store, sid):
    """Caller owns TURN_LOCK. A failed model must not lose lesson completion."""
    session, source = store.summary_source(sid)
    if session["lesson"].get("teacher_summary", {}).get("for_finished") == session["finished"]:
        return None
    prefs = store.settings()
    try:
        summary = engine.summarize_lesson(source, prefs["base"], prefs["model"])
    except (ValueError, OSError):
        summary = lessons.fallback_summary(source, prefs["base"])
    return store.save_lesson_summary(sid, session["finished"], summary, prefs["teacher"])

def settings_values(data):
    allowed = {"target", "base", "model", "level", "daily_goal", "auto_speak", "audio_mode", "pause_ms",
               "instructions", "auto_adapt", "speech_rate", "mic_device", "auto_translate", "humor", "teacher", "feedback_base"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError("Réglage inconnu.")
    for key, choices in [("target", config.LANGUAGES), ("base", ("fr", "en")), ("feedback_base", ("fr", "en")), ("level", config.LEVELS),
                         ("audio_mode", ("native", "whisper")), ("teacher", tuple(config.TEACHERS))]:
        if key in data and data[key] not in choices:
            raise ValueError(f"Valeur incorrecte : {key}")
    for key, lower, upper in [("daily_goal", 10, 100), ("pause_ms", 400, 1500), ("speech_rate", .7, 1.5)]:
        if key in data and (type(data[key]) not in (float, int) or not lower <= data[key] <= upper):
            raise ValueError(f"Valeur incorrecte : {key}")
    for key in ["auto_speak", "auto_adapt", "auto_translate", "humor"]:
        if key in data and type(data[key]) is not bool:
            raise ValueError(f"Valeur incorrecte : {key}")
    for key, limit in [("instructions", 1500), ("model", 160), ("mic_device", 256)]:
        if key in data and (not isinstance(data[key], str) or len(data[key]) > limit):
            raise ValueError(f"Valeur incorrecte : {key}")
    if "model" in data:
        engine.model_info(data["model"])
    return data

def health(store):
    prefs = store.settings()
    result = {"application": "parliamo", "version": "0.9.0", "busy": TURN_LOCK.locked(), "online": False, "model": prefs["model"], "models": [], "placement": "Non chargé", "audio": False,
              "voices": {lang: p.is_file() for lang, (p, _) in config.VOICES.items()},
              "whisper": (config.RUNTIME / "whisper/bin/whisper-cli").is_file()}
    try:
        result["models"] = [{"name": m["name"], "parameters": m.get("details", {}).get("parameter_size", "")} for m in engine.inventory()]
        info = engine.model_info(prefs["model"])
        result["audio"] = "audio" in info.get("capabilities", [])
        result["online"] = True
        for model in engine.query("/api/ps").get("models", []):
            if model.get("name") == prefs["model"]:
                total, gpu = model.get("size", 0), model.get("size_vram", 0)
                result["placement"] = f"{round(gpu / total * 100)} % GPU" if total else "Inconnu"
                result["vram_mb"] = round(gpu / 1024**2)
    except (OSError, ValueError) as exc:
        result["error"] = str(exc)
    return result

class AppServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, store=None, shared=None, local_interfaces=(), scheme="http"):
        self.shared = shared
        self.store = shared.store if shared else store or Store()
        self.profiles = shared.profiles if shared else Profiles(self.store)
        self.speech = shared.speech if shared else Speech()
        self.local_interfaces = local_interfaces
        self.scheme = scheme
        self.phone = {"enabled": False, "urls": [], "setup_urls": []}
        super().__init__(address, Handler)

    def server_close(self):
        if not self.shared:
            self.speech.close()
        super().server_close()

    def get_request(self):
        connection, address = super().get_request()
        if self.scheme == "https":
            connection.settimeout(20)
        return connection, address

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Paths only: no transcripts, recordings or request bodies in logs.
        if args and str(args[0]).startswith("POST /api/turn"):
            return
        super().log_message(fmt, *args)

    def safe_request(self):
        local_interfaces = self.server.local_interfaces
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        allowed.update(f"{i.ip}:{self.server.server_port}" for i in local_interfaces)
        host = self.headers.get("Host", "")
        if host not in allowed or not network.client_allowed(self.client_address[0], local_interfaces):
            return False
        origin = self.headers.get("Origin")
        # A tap from the HTTP setup page to HTTPS is a cross-site top-level
        # navigation. Permit that while still rejecting cross-site API fetches.
        navigation = (self.command == "GET" and self.headers.get("Sec-Fetch-Mode") == "navigate"
                      and self.headers.get("Sec-Fetch-Dest") == "document")
        return (self.headers.get("Sec-Fetch-Site") != "cross-site" or navigation) and (not origin or origin == f"{self.server.scheme}://{host}")

    def send_headers(self, code, content_type, size=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if size is not None:
            self.send_header("Content-Length", str(size))
        self.end_headers()

    def json(self, value, code=200):
        encoded = json.dumps(value, ensure_ascii=False).encode()
        self.send_headers(code, "application/json; charset=utf-8", len(encoded))
        self.wfile.write(encoded)

    def body(self):
        if "application/json" not in self.headers.get("Content-Type", ""):
            raise ValueError("Une requête JSON est nécessaire.")
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 1_500_000:
            raise ValueError("La requête est vide ou trop volumineuse.")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Objet JSON attendu.")
        return data

    def do_GET(self):
        if not self.safe_request():
            return self.json({"error": "Accès local uniquement."}, 403)
        path = urlsplit(self.path).path
        try:
            if path == "/api/profiles":
                return self.json({"profiles": self.server.profiles.list()})
            if path == "/api/network":
                return self.json(self.server.phone)
            if path.startswith("/api/"):
                profile, store = self.server.profiles.resolve(self.headers.get("X-Parliamo-Profile", "default"))
            if path == "/api/state":
                return self.json({**store.dashboard(), "topics": TOPICS, "profile": profile, "network": self.server.phone, "teachers": config.teacher_catalog(), "teacher_names": config.TEACHER_NAMES})
            if path == "/api/health":
                return self.json(health(store))
            if path == "/api/export":
                return self.json({**store.export(), "profile": profile})
            if path.startswith("/api/sessions/"):
                return self.json(store.session(path.rsplit("/", 1)[1]))
            if path == "/phone-ca.crt" and self.server.phone["enabled"]:
                file = config.DATA / "tls" / "phone-ca.crt"
            elif path.startswith("/audio/"):
                filename = path.rsplit("/", 1)[1]
                if not __import__("re").fullmatch(r"[a-f0-9]{64}\.wav", filename):
                    return self.json({"error": "Introuvable"}, 404)
                file = config.DATA / "speech" / filename
            else:
                name = "index.html" if path == "/" else path.lstrip("/")
                file = (config.ROOT / "web" / name).resolve()
                if not file.is_relative_to((config.ROOT / "web").resolve()):
                    return self.json({"error": "Introuvable"}, 404)
            if not file.is_file():
                return self.json({"error": "Introuvable"}, 404)
            data = file.read_bytes()
            content_type = "application/x-x509-ca-cert" if path == "/phone-ca.crt" else mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            self.send_headers(200, content_type, len(data))
            self.wfile.write(data)
        except (ValueError, OSError) as exc:
            self.json({"error": str(exc)}, 400)

    def do_POST(self):
        if not self.safe_request():
            return self.json({"error": "Accès local uniquement."}, 403)
        try:
            data = self.body()
            path = urlsplit(self.path).path
            self.profile, self.store = self.server.profiles.resolve(self.headers.get("X-Parliamo-Profile", "default"))
            store = self.store
            if path == "/api/profiles":
                return self.json(self.server.profiles.create(data.get("name"), data.get("base", "fr")))
            if path == "/api/profiles/rename":
                return self.json(self.server.profiles.rename(self.profile["id"], data.get("name")))
            if path == "/api/settings":
                if not TURN_LOCK.acquire(blocking=False):
                    return self.json({"error": "Attendez la fin de la réponse avant de modifier les réglages."}, 409)
                try:
                    return self.json(store.update_settings(settings_values(data)))
                finally:
                    TURN_LOCK.release()
            if path == "/api/sessions":
                return self.json(store.new_session(data.get("topic"), data.get("mode", "lesson"), data.get("subject", "")))
            if path in ("/api/finish", "/api/resume-objectives", "/api/lesson-review", "/api/lesson-summary"):
                if not TURN_LOCK.acquire(blocking=False):
                    return self.json({"error": "Attendez la fin de la réponse."}, 409)
                try:
                    sid = str(data.get("session_id", ""))
                    if path == "/api/lesson-review":
                        return self.json(store.review_lesson(sid, data.get("index"), data.get("remembered")))
                    if path == "/api/resume-objectives":
                        return self.json(store.resume_objectives(sid))
                    if path == "/api/finish":
                        store.finish(sid)
                    generated = ensure_lesson_summary(store, sid)
                    return self.json({**store.session(sid), "summary_created": bool(generated)})
                finally:
                    TURN_LOCK.release()
            if path == "/api/turn":
                return self.turn(data)
            if path == "/api/speech":
                text = data.get("text", "")
                language = data.get("language", "it")
                slow = data.get("slow", False)
                if not isinstance(text, str) or not 1 <= len(text) <= 1600 or language not in config.LANGUAGES or type(slow) is not bool:
                    raise ValueError("Texte ou langue incorrects.")
                prefs = store.settings()
                teacher = data.get("teacher", prefs["teacher"])
                if not isinstance(teacher, str) or teacher not in config.TEACHERS:
                    raise ValueError("Professeur inconnu.")
                rate = prefs["speech_rate"]
                # Piper's length_scale grows as speech slows; the normal setting stays intact.
                if slow:
                    rate = min(2.0, max(1.45, rate * 1.35))
                output = self.server.speech.synthesize(text, language, rate, teacher=teacher)
                return self.json({"url": "/audio/" + output.name})
            if path == "/api/assessment-explanation":
                mid = str(data.get("message_id", ""))
                language = data.get("language", "fr")
                if language not in ("fr", "en"):
                    raise ValueError("Choisissez le français ou l’anglais pour l’explication.")
                feedback = store.assessment_text(str(data.get("session_id", "")), mid)
                translated = feedback["text"] if feedback["language"] == language else store.translation(mid, -1, language)
                if not translated:
                    if not TURN_LOCK.acquire(blocking=False):
                        return self.json({"error": "Attendez la fin de la réponse pour traduire."}, 409)
                    try:
                        # Recheck after acquiring the shared model lock.
                        translated = store.translation(mid, -1, language)
                        if not translated:
                            values = engine.translate_phrase(feedback["text"], feedback["language"], language, store.settings()["model"])
                            translated = values["english" if language == "en" else "translation"]
                        # Reserved slot -1 stores the feedback explanation, never a dialogue segment.
                        store.save_translations(mid, -1, {language: translated})
                    finally:
                        TURN_LOCK.release()
                return self.json({"text": translated, "language": language, "message_id": mid})
            if path == "/api/translate":
                text = data.get("text", "")
                source = data.get("source", store.settings()["target"])
                base = data.get("base", store.settings()["base"])
                if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1000 or source not in config.LANGUAGES or base not in ("fr", "en"):
                    raise ValueError("Choisissez une expression de 1 à 1 000 caractères et des langues valides.")
                if not TURN_LOCK.acquire(blocking=False):
                    return self.json({"error": "Attendez la fin de la réponse pour traduire."}, 409)
                try:
                    return self.json(engine.translate_phrase(text, source, base, store.settings()["model"]))
                finally:
                    TURN_LOCK.release()
            if path == "/api/message-translation":
                language, index = data.get("language"), data.get("segment")
                message = store.message(str(data.get("session_id", "")), str(data.get("message_id", "")))
                segments = message["payload"].get("segments", [])
                if language not in ("fr", "en") or type(index) is not int or not 0 <= index < len(segments):
                    raise ValueError("Phrase ou langue incorrecte.")
                segment = segments[index]
                translated = store.translation(message["id"], index, language)
                if not translated:
                    if not TURN_LOCK.acquire(blocking=False):
                        return self.json({"error": "Attendez la fin de la réponse pour traduire."}, 409)
                    try:
                        values = engine.translate_phrase(segment["text"], segment["language"], "fr", store.settings()["model"])
                        translations = {"fr": values["translation"], "en": values["english"]}
                        store.save_translations(message["id"], index, translations)
                        translated = translations[language]
                    finally:
                        TURN_LOCK.release()
                return self.json({"text": translated, "language": language, "message_id": message["id"], "segment": index})
            if path == "/api/bookmarks":
                if not isinstance(data.get("text"), str) or not data["text"].strip() or len(data["text"]) > 1600:
                    raise ValueError("Ajoutez un mot ou une expression (1 600 caractères maximum).")
                for key in ("translation", "english", "note"):
                    if key in data and (not isinstance(data[key], str) or len(data[key]) > 2000):
                        raise ValueError("Cette note est trop longue.")
                if data.get("target", store.settings()["target"]) not in config.LANGUAGES:
                    raise ValueError("Langue inconnue.")
                store.save_bookmark(data)
                return self.json({"ok": True})
            if path == "/api/bookmarks/delete":
                store.delete_bookmark(str(data.get("id", "")))
                return self.json({"ok": True})
            if path == "/api/review":
                if type(data.get("remembered")) is not bool:
                    raise ValueError("Réponse de révision incorrecte.")
                store.review(str(data.get("id", "")), data["remembered"])
                return self.json({"ok": True})
            if path == "/api/feedback":
                note = data.get("note", "")
                if not isinstance(note, str) or not 1 <= len(note) <= 2000:
                    raise ValueError("Ajoutez une note de 1 à 2 000 caractères.")
                store.feedback(data.get("session_id"), data.get("message_id"), note)
                return self.json({"ok": True})
            if path == "/api/warmup":
                if not TURN_LOCK.acquire(blocking=False):
                    return self.json({"error": "Le professeur répond déjà."}, 409)
                try:
                    model = store.settings()["model"]
                    engine.model_info(model)
                    engine.query("/api/generate", {"model": model, "prompt": "", "stream": False,
                        "keep_alive": "15m", "options": {"num_ctx": 4096}}, timeout=120)
                    # Preload the Italian voice without occupying GPU memory.
                    try:
                        self.server.speech.synthesize("Ciao!", "it", teacher=store.settings()["teacher"])
                    except (OSError, ValueError):
                        pass
                    return self.json(health(store))
                finally:
                    TURN_LOCK.release()
            return self.json({"error": "Introuvable"}, 404)
        except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
            return self.json({"error": str(exc)}, 400)

    def turn(self, data):
        action = data.get("action", "reply")
        if action not in ("start", "reply", "english", "simplify", "hint", "continue", "topic"):
            raise ValueError("Action inconnue.")
        text = data.get("text", "")
        if not isinstance(text, str) or len(text) > 2500:
            raise ValueError("Votre message est trop long (2 500 caractères maximum).")
        audio = engine.wav_audio(data["audio"]) if data.get("audio") else None
        if action == "reply" and not text.strip() and not audio:
            raise ValueError("Écrivez ou enregistrez une phrase.")
        session = self.store.session(str(data.get("session_id", "")))
        if action == "topic":
            if session["mode"] != "coffee" or not 1 <= len(text.strip()) <= 400 or audio:
                raise ValueError("Choisissez un sujet de 1 à 400 caractères pour le salon café.")
            session["subject"] = text.strip()
        if action == "continue" and not session["finished"]:
            raise ValueError("La partie guidée est encore en cours.")
        if action == "start" and session["messages"]:
            raise ValueError("Cette conversation a déjà commencé.")
        if not TURN_LOCK.acquire(blocking=False):
            return self.json({"error": "Une réponse est déjà en cours. Réessayez dans un instant."}, 409)
        self.send_headers(200, "application/x-ndjson; charset=utf-8")
        def emit(value):
            self.wfile.write((json.dumps(value, ensure_ascii=False) + "\n").encode())
            self.wfile.flush()
        try:
            prefs = self.store.settings()
            session["base"] = prefs["base"]
            prefs["memory"] = self.store.memory(session["target"])["notes"]
            if session["notes"]["summary"]:
                # Resuming an older conversation should retain that conversation's context.
                prefs["memory"] = session["notes"]
            start = time.monotonic()
            stt_ms = 0
            mode = "native_audio" if audio else "text"
            if audio and prefs["audio_mode"] == "whisper":
                emit({"type": "status", "text": "Whisper transcrit votre phrase…"})
                text = transcribe(audio, session["target"])
                audio = None
                stt_ms = round((time.monotonic() - start) * 1000)
                mode = "whisper"
                emit({"type": "transcript", "text": text})
            name = config.TEACHERS[prefs["teacher"]]["name"]
            emit({"type": "status", "text": f"{name} vous écoute…" if audio else f"{name} prépare sa réponse…"})
            for event in engine.stream_turn(session, prefs, text, action, audio):
                if event["type"] == "result":
                    result = event["result"]
                    metrics = event["metrics"]
                    metrics.update({"input": mode, "transcription_ms": stt_ms, "total_ms": round((time.monotonic()-start)*1000)})
                    user_text = result.get("heard") if audio else text
                    if not user_text:
                        user_text = {"english": "Help in English", "hint": "Un indice", "simplify": "Plus simple"}.get(action, "[Enregistrement vocal]")
                    spoken_count = len(result["segments"])
                    mid, xp = self.store.commit_turn(session["id"], user_text, result, action, metrics)
                    # The verified completion is saved and spoken exactly once.
                    for index, segment in enumerate(result["segments"][spoken_count:], spoken_count):
                        emit({"type": "segment", "segment": segment, "index": index})
                    updated = self.store.session(session["id"])
                    if updated["finished"] and not session["finished"]:
                        emit({"type": "status", "text": "Préparation du résumé de la leçon…"})
                        summary_payload = ensure_lesson_summary(self.store, session["id"])
                        if summary_payload:
                            emit({"type": "lesson_summary", "summary": summary_payload["lesson_summary"],
                                  "segments": summary_payload["segments"]})
                        updated = self.store.session(session["id"])
                    emit({"type": "done", "result": result, "message_id": mid, "xp": xp, "metrics": metrics,
                          "just_completed": bool(updated["finished"] and not session["finished"]), "session": updated})
                else:
                    emit(event)
        except (BrokenPipeError, ConnectionResetError):
            # Closing the iterator closes the upstream response. Partial turns earn no XP.
            pass
        except Exception as exc:
            try:
                emit({"type": "error", "error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass
        finally:
            TURN_LOCK.release()

def refresh_phone(server, secure, local_interfaces, context=None):
    local_interfaces = tuple(local_interfaces)
    if context is not None and local_interfaces:
        network.prepare_tls(local_interfaces, context=context)
    phone = {"enabled": True,
        "urls": [f"https://{i.ip}:{secure.server_port}" for i in local_interfaces],
        "setup_urls": [f"http://{i.ip}:{server.server_port}/phone.html" for i in local_interfaces]}
    server.local_interfaces = secure.local_interfaces = local_interfaces
    server.phone = secure.phone = phone


def main():
    parser = argparse.ArgumentParser(description="Parliamo — votre professeur de langues local")
    parser.add_argument("command", choices=["serve", "doctor"], nargs="?", default="serve")
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--lan", action="store_true", default=network.enabled())
    args = parser.parse_args()
    if args.command == "doctor":
        print(json.dumps(health(Store()), ensure_ascii=False, indent=2))
        return
    local_interfaces = network.interfaces() if args.lan else []
    context = network.prepare_tls(local_interfaces) if args.lan else None
    server = AppServer(("0.0.0.0" if args.lan else "127.0.0.1", args.port), local_interfaces=local_interfaces)
    secure = None
    network_stopped = threading.Event()
    network_thread = None
    if context:
        try:
            secure = AppServer(("0.0.0.0", config.HTTPS_PORT), shared=server, local_interfaces=local_interfaces, scheme="https")
            # Handshake in each request thread, so an idle phone connection
            # cannot stall other clients while the listener accepts sockets.
            secure.socket = context.wrap_socket(secure.socket, server_side=True, do_handshake_on_connect=False)
            refresh_phone(server, secure, local_interfaces)
            threading.Thread(target=secure.serve_forever, daemon=True).start()
            network_thread = threading.Thread(target=network.watch_interfaces,
                args=(local_interfaces, lambda current: refresh_phone(server, secure, current, context), network_stopped),
                daemon=True, name="phone-network")
            network_thread.start()
        except Exception:
            if secure:
                secure.server_close()
            server.server_close()
            raise
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"Parliamo is ready at http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        network_stopped.set()
        if network_thread:
            network_thread.join(timeout=4)
        if secure:
            secure.shutdown()
            secure.server_close()
        server.server_close()

if __name__ == "__main__":
    main()
