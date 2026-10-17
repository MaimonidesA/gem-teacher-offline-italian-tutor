"""Opt-in local-model validation on an isolated instance, port 8774 by default."""
import argparse
import json
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8774")
args = parser.parse_args()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
profile = "default"


def request(path, data=None):
    return opener.open(urllib.request.Request(args.url + path, json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", "X-Parliamo-Profile": profile}), timeout=180)


def api(path, data=None):
    with request(path, data) as response:
        return json.load(response)


def turn(sid, text="", action="reply"):
    with request("/api/turn", {"session_id": sid, "text": text, "action": action}) as response:
        events = [json.loads(line) for line in response]
    assert not any(e["type"] == "error" for e in events), events
    assert events[-1]["type"] == "done", events
    print(json.dumps({"input": text or action, "assessment": events[-1]["result"].get("assessment"),
                      "completed": events[-1]["just_completed"], "summary_events": sum(e["type"] == "lesson_summary" for e in events)}, ensure_ascii=False), flush=True)
    return events[-1], events


profile = api("/api/profiles", {"name": "Summary validation", "base": "fr"})["id"]
api("/api/settings", {"auto_speak": False})
session = api("/api/sessions", {"topic": "hello"})
sid = session["id"]
turn(sid, action="start")
first, _ = turn(sid, "Ciao, mi chiamo Luca. Io sono trent’anni.")
assert first["result"]["assessment"]["corrected"], "Expected an age correction"
mid = next(m["id"] for m in first["session"]["messages"] if m["role"] == "user")
for text in ("Vengo dalla Francia.", "Come stai?"):
    completed, events = turn(sid, text)
assert completed["just_completed"]
assert sum(e["type"] == "lesson_summary" for e in events) == 1
completion_events = events
summary = completed["session"]["lesson"]["teacher_summary"]
assert summary["source"] == "local_model", summary
assert summary["language"] == "fr" and len(summary["points"]) >= 3
assert any(word in json.dumps(summary, ensure_ascii=False).lower() for word in ("avere", "ho trent", "âge")), summary
print("French summary:", json.dumps(summary, ensure_ascii=False), flush=True)
before = api("/api/state")["stats"]
feedback = {lang: api("/api/assessment-explanation", {"session_id": sid, "message_id": mid, "language": lang}) for lang in ("fr", "en")}
assert feedback["fr"]["language"] == "fr" and feedback["en"]["language"] == "en"
assert feedback["fr"]["text"] != feedback["en"]["text"]
assert api("/api/state")["stats"] == before
assert api("/api/lesson-summary", {"session_id": sid})["summary_created"] is False
after, _ = turn(sid, "Maintenant, parlons de mon livre de mathématiques.")
assert after["session"]["lesson"]["teacher_summary"] == summary

api("/api/settings", {"base": "en"})
early = api("/api/sessions", {"topic": "cafe"})
turn(early["id"], action="start")
reply, _ = turn(early["id"], "Vorrei un caffè, per favore.")
assert reply["result"]["assessment_base"] == "fr"
early = api("/api/finish", {"session_id": early["id"]})
assert early["lesson"]["status"] == "ended_early"
assert early["lesson"]["teacher_summary"]["language"] == "en"
assert early["lesson"]["teacher_summary"]["source"] == "local_model"
print("English summary:", json.dumps(early["lesson"]["teacher_summary"], ensure_ascii=False), flush=True)
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/summaries-live.json").write_text(json.dumps({"passed": True, "profile_id": profile,
    "session_id": sid, "message_id": mid, "early_id": early["id"], "summary": summary, "feedback": feedback,
    "completion_events": completion_events}, ensure_ascii=False, indent=2))
print("PASS live summaries and French/English explanations")
