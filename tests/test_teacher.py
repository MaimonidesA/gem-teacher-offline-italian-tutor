import base64
import copy
import io
import json
import ipaddress
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import wave

from teacher import config, engine, network
from teacher.store import Store
from teacher.profiles import Profiles
from teacher.server import AppServer, settings_values
from teacher.learning import compact_notes, clean_assessment, segment_kind

REPLY = {"segments": [{"language": "it", "text": "Ciao! Come stai?"}, {"language": "fr", "text": "Comment vas-tu ?"}],
         "heard": "", "correction": "", "phrase": {"text": "Come stai?", "translation": "Comment vas-tu ?", "english": "How are you?"},
         "score": 3, "focus": "Salutations"}

class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(config, "DATA", Path(self.tmp.name))
        self.patch.start()
        self.store = Store()
    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()
    def turn(self, sid, action="reply", result=None):
        return self.store.commit_turn(sid, "Sto bene.", copy.deepcopy(result or REPLY), action, {})

class NetworkTest(StoreCase):
    def test_lan_selection_excludes_vpn_and_restricts_clients(self):
        rows = [
            {"ifname": "wlan0", "flags": ["UP"], "addr_info": [{"family": "inet", "local": "192.168.1.5", "prefixlen": 24}]},
            {"ifname": "wg0", "flags": ["UP", "POINTOPOINT"], "addr_info": [{"family": "inet", "local": "10.0.0.2", "prefixlen": 24}]},
            {"ifname": "docker0", "flags": ["UP"], "addr_info": [{"family": "inet", "local": "172.17.0.1", "prefixlen": 16}]},
            {"ifname": "eth0", "flags": ["UP"], "addr_info": [{"family": "inet", "local": "8.8.8.8", "prefixlen": 24}]},
        ]
        with patch.object(network.subprocess, "check_output", return_value=json.dumps(rows).encode()):
            interfaces = network.interfaces()
        self.assertEqual([str(i) for i in interfaces], ["192.168.1.5/24"])
        for value in ("127.0.0.1", "192.168.1.20"):
            self.assertTrue(network.client_allowed(value, interfaces))
        for value in ("10.0.0.3", "192.168.2.2", "8.8.8.8", "invalid"):
            self.assertFalse(network.client_allowed(value, interfaces))
        self.assertFalse(network.client_allowed("192.168.1.20", []))

    def test_tls_renews_addresses_without_replacing_phone_trust(self):
        import ssl, subprocess
        with patch.dict(network.os.environ, {}, clear=True):
            self.assertFalse(network.enabled())
            network.save_enabled(True)
            self.assertTrue(network.enabled())
        interface = ipaddress.ip_interface("192.168.1.5/24")
        network.prepare_tls([interface])
        folder = config.DATA / "tls"
        ca = (folder / "phone-ca.crt").read_bytes()
        first = (folder / "server.crt").read_bytes()
        network.prepare_tls([interface])
        self.assertEqual((folder / "server.crt").read_bytes(), first)
        network.prepare_tls([ipaddress.ip_interface("192.168.1.6/24")])
        self.assertEqual((folder / "phone-ca.crt").read_bytes(), ca)
        self.assertNotEqual((folder / "server.crt").read_bytes(), first)
        for name in ("ca.key", "server.key"):
            self.assertEqual((folder / name).stat().st_mode & 0o777, 0o600)
        subprocess.run(["openssl", "verify", "-CAfile", str(folder / "phone-ca.crt"), "-verify_ip", "192.168.1.6", str(folder / "server.crt")], check=True, capture_output=True)
        ssl.create_default_context(cafile=str(folder / "phone-ca.crt"))

class ProfilesTest(StoreCase):
    def test_existing_history_is_preserved_and_new_profiles_are_independent(self):
        sid = self.store.new_session("hello")["id"]
        self.turn(sid, result={**REPLY, "memory": {"summary": "Original learner", "facts": ["Reads mathematics"]}})
        self.store.update_settings({"base": "en", "level": "B1", "instructions": "My preferences"})
        self.store.save_bookmark({"text": "Ciao", "note": "My note"})
        before = self.store.export()["tables"]
        profiles = Profiles(self.store)
        self.assertEqual(profiles.resolve("default")[1].export()["tables"], before)
        wife = profiles.create("  Léa  ", "fr")
        self.assertEqual(wife["name"], "Léa")
        _, other = profiles.resolve(wife["id"])
        self.assertEqual(other.settings()["base"], "fr")
        self.assertEqual(other.settings()["level"], "A1")
        self.assertEqual(other.settings()["instructions"], "")
        self.assertEqual(other.dashboard()["stats"]["xp"], 0)
        self.assertEqual(other.dashboard()["sessions"], [])
        self.assertEqual(other.memory("it")["notes"]["facts"], [])
        with self.assertRaises(ValueError): other.session(sid)
        other.save_bookmark({"text": "Ciao", "note": "Her note"})
        self.assertEqual(other.dashboard()["bookmarks"][0]["note"], "Her note")
        self.assertEqual(self.store.dashboard()["bookmarks"][0]["note"], "My note")
        other_sid = other.new_session(None, "coffee", "Her books")["id"]
        other.commit_turn(other_sid, "Ciao", copy.deepcopy(REPLY), "reply", {})
        profiles.rename("default", "Yaron")
        profiles.rename(wife["id"], "Léa 🌻")
        restarted = Profiles(Store(self.store.path))
        self.assertEqual(restarted.resolve(wife["id"])[0]["name"], "Léa 🌻")
        self.assertEqual(restarted.resolve(wife["id"])[1].session(other_sid)["xp"], 10)
        self.assertEqual(restarted.resolve("default")[1].export()["tables"], before)
        self.assertEqual(len(restarted.list()), 2)

    def test_profiles_validate_names_and_never_resolve_arbitrary_files(self):
        profiles = Profiles(self.store)
        for name in ("", "   ", "a"*41, "a\nb", "a\x00b", None, []):
            with self.assertRaises(ValueError): profiles.create(name)
        with self.assertRaises(ValueError): profiles.create("Valid", "es")
        for pid in ("", "../learning", "missing"):
            with self.assertRaises(ValueError): profiles.resolve(pid)
            with self.assertRaises(ValueError): profiles.rename(pid, "Valid")
        # Names are display data, never filenames; no two-account quota.
        for name in ("../Name", "Third learner", "Fourth learner"):
            profiles.create(name)
        self.assertEqual(len(profiles.list()), 4)

class StoreTest(StoreCase):
    def test_base_switch_applies_to_old_new_and_coffee_chats_without_rewriting_history(self):
        lesson = self.store.new_session("hello")["id"]
        coffee = self.store.new_session(None, "coffee", "Mes livres")["id"]
        self.turn(lesson)
        old_payload = copy.deepcopy(self.store.session(lesson)["messages"][-1]["payload"])
        self.store.update_settings({"base": "en"})
        for sid in (lesson, coffee): self.assertEqual(self.store.session(sid)["base"], "en")
        self.assertEqual(self.store.new_session("cafe")["base"], "en")
        self.assertEqual(self.store.session(lesson)["messages"][-1]["payload"], old_payload)
        self.turn(lesson)
        self.assertEqual(self.store.session(lesson)["messages"][-1]["payload"]["base"], "en")
        self.store.update_settings({"base": "fr"})
        self.assertEqual(self.store.session(lesson)["base"], "fr")
        self.assertEqual(self.store.session(lesson)["messages"][-1]["payload"]["base"], "en")
        self.assertEqual(self.store.session(lesson)["xp"], 20)
    def test_coffee_chat_awards_practice_without_completing_a_lesson(self):
        session = self.store.new_session(None, "coffee", "Mes livres de mathématiques")
        self.assertEqual(session["phase"], "coffee")
        self.assertEqual(session["topic"], "free")
        for _ in range(4): self.turn(session["id"], result={**REPLY, "lesson_complete": True})
        updated = self.store.session(session["id"])
        self.assertIsNone(updated["finished"])
        self.assertEqual(updated["subject"], session["subject"])
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 40)
        self.assertEqual(self.store.dashboard()["stats"]["lessons"], 0)
        self.assertEqual(self.store.dashboard()["completed_topics"], [])
        with self.assertRaises(ValueError): self.store.finish(session["id"])
    def test_coffee_topic_change_preserves_conversation_without_scoring_setup(self):
        sid = self.store.new_session("free", "coffee", "Mathématiques")["id"]
        self.turn(sid)
        self.store.commit_turn(sid, "Anna Karina et le cinéma", copy.deepcopy(REPLY), "topic", {})
        updated = self.store.session(sid)
        self.assertEqual(updated["turns"], 1)
        self.assertEqual(updated["subject"], "Anna Karina et le cinéma")
        self.assertEqual(len(updated["messages"]), 4)
        self.assertIsNone(updated["messages"][-2]["payload"]["assessment"])
        self.assertEqual(updated["messages"][-2]["payload"]["action"], "topic")
        lesson = self.store.new_session("hello")
        self.assertEqual(lesson["mode"], "lesson")
        with self.assertRaises(ValueError):
            self.store.commit_turn(lesson["id"], "Mathématiques", copy.deepcopy(REPLY), "topic", {})
    def test_progress_only_counts_learning_replies(self):
        sid = self.store.new_session("hello")["id"]
        for action in ("start", "english", "hint", "simplify"):
            self.turn(sid, action)
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 0)
        self.turn(sid)
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 10)
        self.assertEqual(self.store.session(sid)["turns"], 1)
    def test_finish_requires_three_turns_and_is_idempotent(self):
        sid = self.store.new_session("hello")["id"]
        with self.assertRaises(ValueError): self.store.finish(sid)
        for _ in range(3): self.turn(sid)
        first = self.store.finish(sid)
        second = self.store.finish(sid)
        self.assertEqual(first["finished"], second["finished"])
        self.assertEqual(self.store.dashboard()["stats"]["lessons"], 1)
        self.turn(sid, "continue")
        self.assertEqual(self.store.session(sid)["turns"], 3)
        self.turn(sid)
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 40)
        self.assertEqual(self.store.session(sid)["phase"], "conversation")
        self.assertEqual(self.store.session(sid)["finished"], first["finished"])
    def test_automatic_milestone_requires_successful_actual_replies(self):
        sid = self.store.new_session("hello")["id"]
        for _ in range(3): self.turn(sid, result={**REPLY, "score": 0})
        for _ in range(3): self.turn(sid, "hint")
        self.turn(sid, result={**REPLY, "lesson_complete": True})
        self.assertIsNone(self.store.session(sid)["finished"])
        for _ in range(2): self.turn(sid, result={**REPLY, "lesson_complete": True})
        self.assertEqual(self.store.session(sid)["phase"], "conversation")
        self.assertEqual(self.store.dashboard()["stats"]["lessons"], 1)
    def test_notes_replace_and_history_stays_bounded_without_data_loss(self):
        sid = self.store.new_session("hello")["id"]
        notes = {"summary": "Au café, commander sans sucre.", "next_step": "Revoir les articles.", "facts": ["Aime le thé."], "practice": ["un / una"]}
        for _ in range(45): self.turn(sid, result={**REPLY, "memory": notes})
        session = self.store.session(sid)
        self.assertEqual(len(session["messages"]), 80)
        self.assertEqual(session["older_messages"], 10)
        self.assertEqual(len(self.store.export()["tables"]["messages"]), 90)
        self.assertEqual(self.store.memory("it")["notes"]["facts"], notes["facts"])
        other = self.store.new_session("cafe")["id"]
        self.turn(other, result={**REPLY, "memory": {**notes, "summary": "Commande réussie."}})
        self.assertEqual(len(self.store.export()["tables"]["learner_notes"]), 1)
        self.assertEqual(self.store.memory("it")["notes"]["summary"], "Commande réussie.")
        self.assertEqual(self.store.session(sid)["notes"]["summary"], notes["summary"])
        self.assertFalse(self.store.memory("fr")["notes"]["summary"])
    def test_feedback_attaches_to_learner_phrase_and_help_has_no_rating(self):
        sid = self.store.new_session("hello")["id"]
        rating = {"rating": 3, "verdict": "needs_work", "corrected": "Ho 30 anni.", "explanation": "Utilisez avere pour l’âge.", "clarity": "clear"}
        self.turn(sid, result={**REPLY, "assessment": rating})
        self.turn(sid, "hint", {**REPLY, "assessment": rating})
        users = [m for m in self.store.session(sid)["messages"] if m["role"] == "user"]
        self.assertEqual(users[0]["payload"]["assessment"]["corrected"], "Ho 30 anni.")
        self.assertIsNone(users[1]["payload"]["assessment"])
    def test_language_progress_and_levels_are_separate(self):
        sid = self.store.new_session("hello")["id"]
        self.turn(sid)
        self.store.update_settings({"level": "A2"})
        self.store.update_settings({"target": "fr", "level": "B1"})
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 0)
        self.assertEqual(self.store.settings()["level"], "B1")
        self.store.update_settings({"target": "it"})
        self.assertEqual(self.store.settings()["level"], "A2")
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 10)
    def test_bookmark_deduplication_and_review_schedule(self):
        values = {"text": "Ciao", "translation": "Salut"}
        self.store.save_bookmark(values)
        self.store.save_bookmark({**values, "note": "Salutation"})
        books = self.store.dashboard()["bookmarks"]
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["note"], "Salutation")
        self.store.review(books[0]["id"], True)
        self.assertEqual(self.store.dashboard()["stats"]["due"], 0)
        with self.assertRaises(ValueError): self.store.review(books[0]["id"], True)
    def test_persistence_export_and_feedback(self):
        sid = self.store.new_session("cafe")["id"]
        mid, _ = self.turn(sid)
        self.store.feedback(sid, mid, "Plus d’exemples français")
        again = Store()
        self.assertEqual(again.session(sid)["turns"], 1)
        exported = again.export()
        self.assertEqual(len(exported["tables"]["feedback"]), 1)
        self.assertEqual(len(exported["tables"]["messages"]), 2)
    def test_adaptation_ignores_start_and_remembers_actual_correction(self):
        sid = self.store.new_session("hello")["id"]
        self.turn(sid, "start", {**REPLY, "score": 0})
        self.assertEqual(self.store.session(sid)["difficulty"], 0)
        self.turn(sid, result={**REPLY, "score": 1, "correction": "Utilisez mi chiamo."})
        self.assertEqual(self.store.session(sid)["difficulty"], -1)
        self.assertIn("Utilisez mi chiamo.", self.store.learning_memory("it")[0])
        self.assertEqual(self.store.learning_memory("fr"), [])

class EngineTest(unittest.TestCase):
    def test_coffee_prompt_follows_subject_without_lesson_agenda(self):
        session = {"topic": "free", "mode": "coffee", "subject": "Les groupes dans mon livre de maths", "target": "it", "base": "fr", "level": "A1", "difficulty": 0, "turns": 0}
        prefs = {"auto_adapt": True, "instructions": ""}
        prompt = engine.prompt(session, prefs, "start")
        self.assertIn(session["subject"], prompt)
        self.assertIn("COFFEE ROOM", prompt)
        self.assertNotIn("GUIDED LESSON", prompt)
        self.assertNotIn("today's goal", prompt)
        self.assertIn("lesson_complete=false always", prompt)
    def test_notes_and_context_are_bounded(self):
        notes = compact_notes({"summary": "x"*5000, "next_step": "y"*1000, **{k: [str(i)*500 for i in range(30)] for k in ("facts", "practice", "strengths")}}, 1000)
        self.assertLessEqual(len(json.dumps(notes, ensure_ascii=False)), 1000)
        session = {"messages": [{"role": "user", "content": "a"*500} for _ in range(10000)]}
        messages = engine.conversation_messages(session, "s"*4000, {"role": "user", "content": "u"*1000}, True)
        self.assertLessEqual(len(messages), 10)
        self.assertLessEqual(sum(len(m["content"]) for m in messages), 6500)
    def test_feedback_normalization_and_segment_semantics(self):
        self.assertEqual(clean_assessment({"verdict": "correct", "rating": 3}, "reply")["rating"], 5)
        self.assertEqual(clean_assessment({"verdict": "almost", "rating": 5}, "reply")["rating"], 4)
        self.assertIsNone(clean_assessment({}, "continue"))
        self.assertIsNone(clean_assessment(None, "reply")["rating"])
        self.assertEqual(segment_kind({"language": "fr"}, "it"), "translation")
        self.assertEqual(segment_kind({"language": "fr"}, "it", "hint"), "instruction")
        self.assertEqual(segment_kind({"language": "fr", "kind": "instruction"}, "it"), "instruction")
    def test_every_chunk_boundary_preserves_escaped_multilingual_segments(self):
        value = {**REPLY, "segments": [{"language": "fr", "kind": "instruction", "text": 'Dites « caffè » et "ciao".\nTrès bien!'}, {"language": "it", "kind": "dialogue", "text": "Piacere!"}]}
        encoded = json.dumps(value, ensure_ascii=False)
        for end in range(len(encoded) + 1):
            result = engine.extract_segments(encoded[:end])
            self.assertEqual(result, value["segments"][:len(result)])
        self.assertEqual(engine.extract_segments(encoded), value["segments"])
    def test_review_follows_streamed_speech_and_scores_current_phrase(self):
        from contextlib import contextmanager
        reply = {**REPLY, "memory": {"summary": "Présentation."}}
        @contextmanager
        def response(*args, **kwargs):
            yield iter([json.dumps({"message": {"content": json.dumps(reply)}, "done": True, "eval_count": 20, "eval_duration": 1000000000}).encode()])
        session = {"topic": "hello", "target": "it", "base": "fr", "level": "A1", "difficulty": 0, "turns": 0, "messages": []}
        prefs = {"model": "gemma4:latest", "auto_adapt": True, "instructions": ""}
        assessment = {"rating": 4, "verdict": "almost", "corrected": "Ho 30 anni.", "explanation": "L'âge utilise avere.", "clarity": "clear"}
        with patch.object(engine, "model_info", return_value={}), patch.object(engine, "request", response), patch.object(engine, "assess_phrase", return_value=assessment) as review:
            stream = engine.stream_turn(session, prefs, "Io sono 30 anni.", "reply")
            self.assertEqual(next(stream)["type"], "segment")
            review.assert_not_called()
            result = list(stream)[-1]["result"]
            review.assert_called_once_with("Io sono 30 anni.", "it", "fr", "gemma4:latest", "")
            self.assertEqual(result["score"], 2)
            self.assertEqual(result["correction"], "L'âge utilise avere.")
    def test_audio_validation_rejects_wrong_format_and_long_clips(self):
        for rate, seconds, valid in [(16000, 1, True), (48000, 1, False), (16000, 31, False), (16000, .1, False)]:
            output = io.BytesIO()
            with wave.open(output, "wb") as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(b'\0\0'*int(rate*seconds))
            encoded = base64.b64encode(output.getvalue()).decode()
            if valid: self.assertEqual(engine.wav_audio(encoded), output.getvalue())
            else:
                with self.assertRaises(ValueError): engine.wav_audio(encoded)
        with self.assertRaises(ValueError): engine.wav_audio("bad")
    def test_cloud_models_are_excluded(self):
        with patch.object(engine, "query", return_value={"models": [{"name": "gemma4:latest"}, {"name": "gemma4:cloud"}, {"name": "alias", "remote_host": "example.com"}]}):
            self.assertEqual([m["name"] for m in engine.inventory()], ["gemma4:latest"])
    def test_partial_transcript_waits_for_complete_escaped_string(self):
        self.assertIsNone(engine.transcript_from_partial('{"heard":"Ciao'))
        self.assertEqual(engine.transcript_from_partial('{"heard":"Ciao, \\"Giulia\\"!",'), 'Ciao, "Giulia"!')
    def test_bad_preferences_are_rejected(self):
        for value in [{"audio_mode": "cloud"}, {"base": "xx"}, {"daily_goal": -1}, {"auto_speak": "false"}, {"ollama_url": "https://example.com"}]:
            with self.assertRaises(ValueError): settings_values(value)

class HTTPTest(StoreCase):
    def setUp(self):
        super().setUp()
        self.server = AppServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        super().tearDown()
    def call(self, path, data=None, headers=None):
        request = urllib.request.Request(self.base + path, json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json", **(headers or {})})
        return self.opener.open(request)
    def test_static_and_state_are_served(self):
        with self.call("/") as response:
            self.assertIn(b"Parliamo", response.read())
            self.assertIn("connect-src 'self'", response.headers["Content-Security-Policy"])
        with self.call("/api/state") as response:
            self.assertEqual(len(json.load(response)["topics"]), 8)
    def test_slow_replay_changes_synthesis_without_changing_preferences(self):
        self.store.update_settings({"speech_rate": 1.1})
        with patch.object(self.server.speech, "synthesize", return_value=Path("a.wav")) as speak:
            for data in ({"text": "Come stai?", "language": "it"}, {"text": "Come stai?", "language": "it", "slow": True}):
                with self.call("/api/speech", data): pass
            self.assertEqual(speak.call_args_list[0].args, ("Come stai?", "it", 1.1))
            self.assertGreater(speak.call_args_list[1].args[2], 1.1)
            with self.assertRaises(urllib.error.HTTPError):
                self.call("/api/speech", {"text": "Ciao", "slow": "yes"})
        self.assertEqual(self.store.settings()["speech_rate"], 1.1)
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 0)

    def test_feedback_english_audio_uses_original_language_and_caches_translation(self):
        sid = self.store.new_session("hello")["id"]
        assessment = {"rating": 3, "verdict": "needs_work", "explanation": "Pour l’âge, utilisez avoir.", "corrected": "Ho 30 anni."}
        self.turn(sid, result={**REPLY, "assessment": assessment})
        mid = self.store.session(sid)["messages"][0]["id"]
        self.store.update_settings({"base": "en"})
        before = self.store.dashboard()["stats"]
        with patch.object(engine, "translate_phrase", return_value={"translation": "For age, use have.", "english": "For age, use have."}) as translate:
            for _ in range(2):
                with self.call("/api/assessment-explanation", {"session_id": sid, "message_id": mid}) as r:
                    value = json.load(r)
                self.assertEqual(value["language"], "en")
                self.assertEqual(value["text"], "For age, use have.")
            translate.assert_called_once_with(assessment["explanation"], "fr", "en", config.DEFAULT_MODEL)
        self.assertEqual(self.store.dashboard()["stats"], before)
        self.turn(sid, result={**REPLY, "assessment": {**assessment, "explanation": "Use have for age."}})
        mid = self.store.session(sid)["messages"][-2]["id"]
        # Legacy learner messages had no base field; their paired response does.
        with self.store.connect() as db:
            payload = json.loads(db.execute("SELECT payload FROM messages WHERE id=?", (mid,)).fetchone()[0]);payload.pop("base")
            db.execute("UPDATE messages SET payload=? WHERE id=?", (json.dumps(payload), mid))
        self.store.update_settings({"base": "fr"})
        with patch.object(engine, "translate_phrase") as translate:
            with self.call("/api/assessment-explanation", {"session_id": sid, "message_id": mid}) as r:
                self.assertEqual(json.load(r)["text"], "Use have for age.")
            translate.assert_not_called()
        other = self.server.profiles.create("Other")
        with self.assertRaises(urllib.error.HTTPError):
            self.call("/api/assessment-explanation", {"session_id": sid, "message_id": mid}, {"X-Parliamo-Profile": other["id"]})

    def test_lan_hosts_origins_and_public_certificate_are_scoped(self):
        interface = ipaddress.ip_interface("192.168.1.5/24")
        host = f"{interface.ip}:{self.server.server_port}"
        with self.assertRaises(urllib.error.HTTPError): self.call("/api/state", headers={"Host": host})
        self.server.local_interfaces = [interface]
        with self.call("/api/state", headers={"Host": host, "Origin": "http://"+host}) as r:
            self.assertEqual(r.status, 200)
        for headers in ({"Host": host, "Origin": "https://evil.example"}, {"Host": host, "Sec-Fetch-Site": "cross-site"}, {"Host": "192.168.1.6:"+str(self.server.server_port)}):
            with self.assertRaises(urllib.error.HTTPError): self.call("/api/state", headers=headers)
        with self.call("/", headers={"Host": host, "Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"}) as r:
            self.assertEqual(r.status, 200)
        self.server.phone["enabled"] = True
        folder = config.DATA / "tls";folder.mkdir()
        (folder / "phone-ca.crt").write_bytes(b"public certificate")
        (folder / "ca.key").write_bytes(b"private key")
        with self.call("/phone-ca.crt") as r:
            self.assertEqual(r.read(), b"public certificate")
            self.assertEqual(r.headers["Content-Type"], "application/x-x509-ca-cert")
        for path in ("/tls/ca.key", "/data/tls/ca.key", "/../data/tls/ca.key"):
            with self.assertRaises(urllib.error.HTTPError): self.call(path)
        secondary = AppServer(("127.0.0.1", 0), shared=self.server, scheme="https")
        try:
            self.assertIs(secondary.speech, self.server.speech)
            self.assertIs(secondary.profiles, self.server.profiles)
        finally:
            secondary.server_close()
    def test_profile_requests_scope_every_learning_resource(self):
        sid = self.store.new_session("hello")["id"]
        mid, _ = self.turn(sid, result={**REPLY, "memory": {"summary": "Original private context"}})
        self.store.save_bookmark({"text": "Ciao", "note": "Original notebook"})
        bid = self.store.dashboard()["bookmarks"][0]["id"]
        with self.call("/api/profiles", {"name": "Wife", "base": "en"}) as r:
            profile = json.load(r)
        headers = {"X-Parliamo-Profile": profile["id"]}
        with self.call("/api/state", headers=headers) as r:
            state = json.load(r)
        self.assertEqual(state["profile"], profile)
        self.assertEqual(state["settings"]["base"], "en")
        self.assertEqual(state["sessions"], [])
        self.assertEqual(state["bookmarks"], [])
        self.assertEqual(state["stats"]["xp"], 0)
        for path, data in [
            ("/api/sessions/"+sid, None), ("/api/turn", {"session_id": sid, "text": "Ciao"}),
            ("/api/finish", {"session_id": sid}), ("/api/review", {"id": bid, "remembered": True}),
            ("/api/feedback", {"session_id": sid, "message_id": mid, "note": "Wrong profile"}),
            ("/api/message-translation", {"session_id": sid, "message_id": mid, "segment": 0, "language": "en"})]:
            with self.assertRaises(urllib.error.HTTPError): self.call(path, data, headers)
        with self.call("/api/bookmarks/delete", {"id": bid}, headers): pass
        self.assertEqual(len(self.store.dashboard()["bookmarks"]), 1)
        with self.call("/api/settings", {"level": "A2", "instructions": "Her preference"}, headers): pass
        self.assertEqual(self.store.settings()["instructions"], "")
        with self.call("/api/sessions", {"mode": "coffee", "subject": "Her book"}, headers) as r:
            other_sid = json.load(r)["id"]
        captured = []
        def successful(session, prefs, text, action, audio):
            captured.append(copy.deepcopy(prefs))
            yield {"type": "result", "result": copy.deepcopy(REPLY), "metrics": {}}
        with patch.object(engine, "stream_turn", successful):
            with self.call("/api/turn", {"session_id": other_sid, "text": "Ciao"}, headers) as r:
                events = [json.loads(line) for line in r]
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(captured[0]["memory"]["summary"], "")
        self.assertEqual(captured[0]["instructions"], "Her preference")
        self.assertEqual(captured[0]["base"], "en")
        with self.call("/api/export", headers=headers) as r:
            export = json.load(r)
        self.assertEqual(export["profile"]["id"], profile["id"])
        self.assertEqual([s["id"] for s in export["tables"]["sessions"]], [other_sid])
        self.assertEqual(export["tables"]["bookmarks"], [])
        self.assertEqual(self.store.session(sid)["xp"], 10)
        self.assertEqual(len(self.store.dashboard()["sessions"]), 1)
        with self.call("/api/profiles/rename", {"name": "Léa"}, headers) as r:
            self.assertEqual(json.load(r)["name"], "Léa")
        with self.call("/api/state") as r:
            self.assertEqual(json.load(r)["profile"]["id"], "default")

    def test_unknown_profile_does_not_fall_back_to_original_learner(self):
        headers = {"X-Parliamo-Profile": "../learning"}
        for path, data in [("/api/state", None), ("/api/export", None), ("/api/settings", {"base": "en"})]:
            with self.assertRaises(urllib.error.HTTPError): self.call(path, data, headers)
        self.assertEqual(self.store.settings()["base"], "fr")

    def test_in_flight_turn_keeps_its_profile_while_another_profile_is_used(self):
        sid = self.store.new_session("hello")["id"]
        profile = self.server.profiles.create("Another learner", "en")
        started, finish = threading.Event(), threading.Event()
        events = []
        def slow(session, prefs, text, action, audio):
            started.set()
            if not finish.wait(5): raise ValueError("Test timed out")
            yield {"type": "result", "result": copy.deepcopy(REPLY), "metrics": {}}
        def request_turn():
            with self.call("/api/turn", {"session_id": sid, "text": "Ciao"}) as r:
                events.extend(json.loads(line) for line in r)
        with patch.object(engine, "stream_turn", slow):
            thread = threading.Thread(target=request_turn)
            thread.start()
            try:
                self.assertTrue(started.wait(3))
                with self.call("/api/state", headers={"X-Parliamo-Profile": profile["id"]}) as r:
                    self.assertEqual(json.load(r)["stats"]["xp"], 0)
            finally:
                finish.set(); thread.join(6)
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(self.store.session(sid)["xp"], 10)
        self.assertEqual(self.server.profiles.resolve(profile["id"])[1].dashboard()["sessions"], [])
    def test_coffee_creation_validation_and_topic_change(self):
        with self.call("/api/sessions", {"mode": "coffee", "subject": "Anna Karina"}) as response:
            session = json.load(response)
        self.assertEqual(session["mode"], "coffee")
        self.assertEqual(session["subject"], "Anna Karina")
        for data in ({"mode": "invalid"}, {"mode": "coffee", "subject": "x"*401}, {"mode": "coffee", "subject": []}):
            with self.assertRaises(urllib.error.HTTPError): self.call("/api/sessions", data)
        seen = []
        def successful(session, prefs, text, action, audio):
            seen.append((session["subject"], action))
            yield {"type": "result", "result": copy.deepcopy(REPLY), "metrics": {}}
        with patch.object(engine, "stream_turn", successful):
            with self.call("/api/turn", {"session_id": session["id"], "action": "topic", "text": "Mon livre de mathématiques"}) as response:
                done = [json.loads(line) for line in response][-1]
        self.assertEqual(seen, [("Mon livre de mathématiques", "topic")])
        self.assertEqual(done["xp"], 0)
        self.assertEqual(done["session"]["subject"], "Mon livre de mathématiques")
    def test_current_base_reaches_teacher_and_english_help_is_temporary(self):
        sid = self.store.new_session("hello")["id"]
        captured = []
        def successful(session, prefs, text, action, audio):
            captured.append((session["base"], action))
            yield {"type": "result", "result": copy.deepcopy(REPLY), "metrics": {}}
        with patch.object(engine, "stream_turn", successful):
            for base, action in (("en", "hint"), ("fr", "english"), ("fr", "hint")):
                with self.call("/api/settings", {"base": base}): pass
                with self.call("/api/turn", {"session_id": sid, "action": action}) as response:
                    events = [json.loads(line) for line in response]
                self.assertEqual(events[-1]["session"]["base"], base)
                self.assertEqual(self.store.settings()["base"], base)
        self.assertEqual(captured, [("en", "hint"), ("fr", "english"), ("fr", "hint")])
        self.assertEqual(self.store.session(sid)["turns"], 0)
    def test_base_switch_cannot_race_an_active_generation(self):
        from teacher.server import TURN_LOCK
        with TURN_LOCK:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.call("/api/settings", {"base": "en"})
            self.assertEqual(error.exception.code, 409)
        self.assertEqual(self.store.settings()["base"], "fr")
    def test_cross_origin_and_wrong_host_are_rejected(self):
        for headers in [{"Origin": "https://evil.example"}, {"Host": "evil.example"}]:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.call("/api/settings", {"base": "en"}, headers)
            self.assertEqual(error.exception.code, 403)
        self.assertEqual(self.store.settings()["base"], "fr")
    def test_streaming_success_commits_and_failure_does_not(self):
        sid = self.store.new_session("hello")["id"]
        def successful(*args):
            yield {"type": "segment", "segment": REPLY["segments"][0]}
            yield {"type": "result", "result": copy.deepcopy(REPLY), "metrics": {}}
        with patch.object(engine, "stream_turn", successful):
            with self.call("/api/turn", {"session_id": sid, "text": "Ciao"}) as response:
                events = [json.loads(line) for line in response]
            self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(self.store.session(sid)["xp"], 10)
        def failure(*args):
            yield {"type": "segment", "segment": REPLY["segments"][0]}
            raise ValueError("Generation failed")
        with patch.object(engine, "stream_turn", failure):
            with self.call("/api/turn", {"session_id": sid, "text": "Ciao"}) as response:
                events = [json.loads(line) for line in response]
            self.assertEqual(events[-1]["type"], "error")
        self.assertEqual(self.store.session(sid)["xp"], 10)
        self.assertEqual(len(self.store.session(sid)["messages"]), 2)
    def test_no_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.call("/../teacher/config.py")
        self.assertEqual(error.exception.code, 404)
    def test_translation_is_separate_from_learning_progress(self):
        translated = {"translation": "Je voudrais un café.", "english": "I would like a coffee."}
        with patch.object(engine, "translate_phrase", return_value=translated):
            with self.call("/api/translate", {"text": "Vorrei un caffè.", "source": "it", "base": "fr"}) as response:
                self.assertEqual(json.load(response), translated)
        self.assertEqual(self.store.dashboard()["stats"]["xp"], 0)
        with self.assertRaises(urllib.error.HTTPError):
            self.call("/api/translate", {"text": "", "source": "it"})
    def test_sentence_translation_uses_exact_segment_and_caches_both_languages(self):
        sid = self.store.new_session("hello")["id"]
        mid, _ = self.turn(sid)
        data = {"session_id": sid, "message_id": mid, "segment": 0, "language": "fr"}
        with patch.object(engine, "translate_phrase", return_value={"translation": "Salut ! Comment vas-tu ?", "english": "Hi! How are you?"}) as translate:
            with self.call("/api/message-translation", data) as response:
                self.assertEqual(json.load(response)["text"], "Salut ! Comment vas-tu ?")
            with self.call("/api/message-translation", {**data, "language": "en"}) as response:
                self.assertEqual(json.load(response)["text"], "Hi! How are you?")
            translate.assert_called_once_with(REPLY["segments"][0]["text"], "it", "fr", self.store.settings()["model"])
        self.assertEqual(self.store.session(sid)["turns"], 1)
        with self.assertRaises(urllib.error.HTTPError):
            self.call("/api/message-translation", {**data, "segment": -1})

if __name__ == "__main__": unittest.main()
