#!/usr/bin/env python3
"""Opt-in real model check. Run against an isolated PARLIAMO_DATA test server."""
import argparse
import base64
import io
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
import wave

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True, help="Isolated test server, e.g. http://127.0.0.1:8766")
parser.add_argument("--output", default="artifacts/live-validation.json")
args = parser.parse_args()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def request(path, data=None):
    return opener.open(urllib.request.Request(args.url + path,
        json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json"}), timeout=180)
def api(path, data=None):
    with request(path, data) as response: return json.load(response)

session = api("/api/sessions", {"topic": "hello"})
report = {"session_id": session["id"], "turns": [], "voices": {}}
def turn(action="reply", text="", audio=None):
    start = time.monotonic()
    first = None
    result = None
    with request("/api/turn", {"session_id": session["id"], "action": action, "text": text, **({"audio": audio} if audio else {})}) as response:
        for line in response:
            event = json.loads(line)
            if event["type"] == "error": raise RuntimeError(event["error"])
            if event["type"] == "segment" and first is None: first = round((time.monotonic() - start) * 1000)
            if event["type"] == "done": result = event
    assert result is not None, "Incomplete response"
    record = {"action": action, "first_segment_ms": first, "metrics": result["metrics"], "reply": result["result"]}
    report["turns"].append(record)
    print(json.dumps(record, ensure_ascii=False), flush=True)
    return result

turn("start")
turn(text="Ciao, mi chiamo Luca. Sto bene, grazie. E tu?")
english = turn("english")
assert any(s["language"] == "en" for s in english["result"]["segments"]), "English fallback missing"
turn("simplify")
for language, text in [("it", "Ciao, mi chiamo Giulia. Oggi sono un po’ stanca."), ("fr", "Bonjour, je voudrais apprendre l’italien."), ("en", "Hello, I would like to learn Italian.")]:
    start = time.monotonic()
    speech = api("/api/speech", {"language": language, "text": text})
    with request(speech["url"]) as response: audio = response.read()
    with wave.open(io.BytesIO(audio)) as wav:
        assert wav.getnframes() > 1000
        report["voices"][language] = {"synthesis_ms": round((time.monotonic()-start)*1000), "duration": round(wav.getnframes()/wav.getframerate(),2)}
    if language == "it":
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/"source.wav", Path(directory)/"input.wav"
            source.write_bytes(audio)
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(source), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target)], check=True)
            encoded = base64.b64encode(target.read_bytes()).decode()
            Path("/tmp/parliamo-validation-input.wav").write_bytes(target.read_bytes())
native = turn(audio=encoded)
assert native["result"]["heard"].strip(), "Native audio transcription missing"
assert "giulia" in native["result"]["heard"].lower(), "Native audio did not hear the changed speaker name"
api("/api/settings", {"audio_mode": "whisper"})
whisper = turn(audio=encoded)
api("/api/settings", {"audio_mode": "native"})
assert whisper["metrics"]["transcription_ms"] > 0
api("/api/bookmarks", {**native["result"]["phrase"], "target": "it", "note": "Live validation"})
finished = api("/api/finish", {"session_id": session["id"]})
assert finished["turns"] == 3 and finished["xp"] == 30
assert api("/api/finish", {"session_id": session["id"]})["xp"] == 30
exported = api("/api/export")
assert exported["format"] == "parliamo"
report["health"] = api("/api/health")
report["finished"] = {"turns": finished["turns"], "xp": finished["xp"], "summary": finished["summary"]}
path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print("PASSED", path, report["voices"], report["health"]["placement"], flush=True)
