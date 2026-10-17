"""Opt-in end-to-end checks against a separate local test instance."""
import argparse
import json
import time
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True, help="Isolated test instance, never your learner database")
args = parser.parse_args()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
profile_id = "default"


def request(path, data=None):
    return opener.open(urllib.request.Request(args.url + path, json.dumps(data).encode() if data is not None else None,
                       headers={"Content-Type": "application/json", "X-Parliamo-Profile": profile_id}), timeout=180)


def api(path, data=None):
    with request(path, data) as response:
        return json.load(response)


records = []


def turn(sid, text="", action="reply"):
    start = time.monotonic()
    with request("/api/turn", {"session_id": sid, "text": text, "action": action}) as response:
        events = [json.loads(line) for line in response]
    assert not any(e["type"] == "error" for e in events), events
    done = events[-1]
    assert done["type"] == "done", events
    record = {"input": text or action, "seconds": round(time.monotonic() - start, 1),
              "result": done["result"], "lesson": done["session"]["lesson"], "just_completed": done["just_completed"]}
    records.append(record)
    print(json.dumps({"input": record["input"], "seconds": record["seconds"], "speech": done["result"]["segments"],
                      "assessment": done["result"]["assessment"], "evidence": done["result"].get("objective_evidence"),
                      "status": record["lesson"]["status"]}, ensure_ascii=False), flush=True)
    return done


profile_id = api("/api/profiles", {"name": "Lesson validation", "base": "fr"})["id"]
api("/api/settings", {"base": "fr", "auto_speak": False})
session = api("/api/sessions", {"topic": "cafe"})
sid = session["id"]
turn(sid, action="start")
unrelated = turn(sid, "Mi piace leggere libri di matematica.")
assert not any(o["evidence"] for o in unrelated["session"]["lesson"]["objectives"]), "Unrelated reply counted"
for index, text in enumerate(("Vorrei un caffè, per favore.", "Quanto costa il caffè?", "Pago con la carta, grazie!")):
    done = turn(sid, text)
    assert done["session"]["lesson"]["objectives"][index]["evidence"], "Demonstrated objective not recorded"
assert done["just_completed"]
assert done["session"]["lesson"]["status"] == "achieved"
assert "obiettivi" in done["result"]["segments"][-1]["text"]
frozen = done["session"]["lesson"]
after = turn(sid, "Quale dolce mi consigli con il caffè?")
assert not after["just_completed"] and after["session"]["lesson"] == frozen
assert api("/api/state")["completed_topics"] == ["cafe"]

api("/api/settings", {"base": "en"})
early = api("/api/sessions", {"topic": "hello"})
turn(early["id"], action="start")
turn(early["id"], "Ciao, mi chiamo Luca.")
ended = api("/api/finish", {"session_id": early["id"]})
assert ended["lesson"]["status"] == "ended_early"
assert api("/api/state")["stats"]["lessons"] == 1
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/lessons-live.json").write_text(json.dumps({"passed": True, "profile_id": profile_id, "session_id": sid, "early_id": early["id"], "turns": records}, ensure_ascii=False, indent=2))
print("PASS", sid, early["id"])
