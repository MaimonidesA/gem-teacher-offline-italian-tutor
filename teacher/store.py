"""SQLite is the source of truth; progress is awarded only for completed turns."""
import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from . import config, lessons
from .curriculum import BY_ID
from .learning import clean_assessment, compact_notes

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, path=None):
        config.prepare()
        self.path = path or config.DATA / "learning.sqlite3"
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, topic TEXT NOT NULL, target TEXT NOT NULL, base TEXT NOT NULL,
                level TEXT NOT NULL, started TEXT NOT NULL, finished TEXT, turns INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0, summary TEXT DEFAULT '', difficulty INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                role TEXT NOT NULL, content TEXT NOT NULL, payload TEXT DEFAULT '{}', created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS bookmarks (
                id TEXT PRIMARY KEY, target TEXT NOT NULL, text TEXT NOT NULL, translation TEXT DEFAULT '',
                english TEXT DEFAULT '', note TEXT DEFAULT '', created TEXT NOT NULL,
                due TEXT NOT NULL, stage INTEGER DEFAULT 0, reviews INTEGER DEFAULT 0,
                UNIQUE(target,text));
            CREATE TABLE IF NOT EXISTS activity (day TEXT NOT NULL, target TEXT NOT NULL, xp INTEGER NOT NULL,
                PRIMARY KEY(day,target));
            CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, session_id TEXT, message_id TEXT,
                note TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS learner_notes (
                target TEXT PRIMARY KEY, session_id TEXT NOT NULL, notes TEXT NOT NULL, updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS translations (
                message_id TEXT NOT NULL REFERENCES messages(id), segment INTEGER NOT NULL,
                language TEXT NOT NULL, text TEXT NOT NULL, PRIMARY KEY(message_id,segment,language));
            CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id,created);
            CREATE INDEX IF NOT EXISTS sessions_language ON sessions(target,started);
            """)
            columns = {r["name"] for r in db.execute("PRAGMA table_info(sessions)")}
            if "notes" not in columns:
                db.execute("ALTER TABLE sessions ADD COLUMN notes TEXT NOT NULL DEFAULT '{}'")
            if "mode" not in columns:
                db.execute("ALTER TABLE sessions ADD COLUMN mode TEXT NOT NULL DEFAULT 'lesson'")
            if "subject" not in columns:
                db.execute("ALTER TABLE sessions ADD COLUMN subject TEXT NOT NULL DEFAULT ''")
            if "lesson" not in columns:
                db.execute("ALTER TABLE sessions ADD COLUMN lesson TEXT NOT NULL DEFAULT '{}'")
            # Preserve old completions without inventing evidence for them.
            for row in db.execute("SELECT * FROM sessions WHERE mode='lesson' AND lesson='{}'").fetchall():
                plan = lessons.new_plan(row["topic"], row["level"], row["target"])
                if row["finished"]:
                    plan["status"] = "legacy"
                    plan["recap"] = compact_notes(json.loads(row["notes"]))
                db.execute("UPDATE sessions SET lesson=? WHERE id=?", (json.dumps(plan, ensure_ascii=False), row["id"]))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def settings(self):
        result = {"target": "it", "base": "fr", "model": config.DEFAULT_MODEL, "level": "A1",
                  "daily_goal": 30, "auto_speak": True, "audio_mode": "native", "pause_ms": 650,
                  "instructions": "", "auto_adapt": True, "speech_rate": 1.0, "mic_device": "",
                  "auto_translate": False, "humor": True, "teacher": "sofia", "feedback_base": "fr"}
        with self.connect() as db:
            result.update({r["key"]: json.loads(r["value"]) for r in db.execute("SELECT * FROM settings")})
        result["level"] = result.get("level_" + result["target"], result["level"])
        result = {k: v for k, v in result.items() if not k.startswith("level_")}
        if result.get("teacher") not in config.TEACHERS:
            result["teacher"] = "sofia"
        return result

    def update_settings(self, values):
        values = dict(values)
        if "level" in values:
            target = values.get("target", self.settings()["target"])
            values["level_" + target] = values.pop("level")
        with self.connect() as db:
            for key, value in values.items():
                db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))
        return self.settings()

    def session(self, sid, limit=80):
        with self.connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
            if not row:
                raise ValueError("Cette leçon est introuvable.")
            result = dict(row)
            # The stored base records the language at creation for legacy
            # messages. Active teaching follows the current global preference.
            initial_base = result["base"]
            result["base"] = self.settings()["base"]
            result["notes"] = compact_notes(json.loads(result["notes"]))
            result["lesson"] = lessons.read_plan(result)
            result["message_count"] = db.execute("SELECT COUNT(*) FROM messages WHERE session_id=?", (sid,)).fetchone()[0]
            result["messages"] = list(reversed([dict(r) for r in db.execute(
                "SELECT * FROM messages WHERE session_id=? ORDER BY created DESC,rowid DESC LIMIT ?", (sid, limit))]))
            result["older_messages"] = result["message_count"] - len(result["messages"])
            result["phase"] = "coffee" if result["mode"] == "coffee" else "conversation" if result["finished"] else "lesson"
            for message in result["messages"]:
                message["payload"] = json.loads(message["payload"])
                message["payload"].setdefault("base", initial_base)
            return result

    def new_session(self, topic, mode="lesson", subject=""):
        if mode not in ("lesson", "coffee") or not isinstance(subject, str) or len(subject) > 400:
            raise ValueError("Choisissez un sujet de 400 caractères maximum.")
        if mode == "coffee":
            topic = "free"
        if topic not in BY_ID:
            raise ValueError("Sujet inconnu.")
        prefs = self.settings()
        sid = uuid.uuid4().hex
        with self.connect() as db:
            plan = lessons.new_plan(topic, prefs["level"], prefs["target"]) if mode == "lesson" else {}
            db.execute("INSERT INTO sessions(id,topic,target,base,level,started,mode,subject,lesson) VALUES(?,?,?,?,?,?,?,?,?)",
                       (sid, topic, prefs["target"], prefs["base"], prefs["level"], now(), mode, subject.strip() if mode == "coffee" else "", json.dumps(plan, ensure_ascii=False)))
        return self.session(sid)

    def commit_turn(self, sid, user_text, result, action, metrics):
        mid = uuid.uuid4().hex
        award = 10 if action == "reply" else 0
        score = result.get("score", 2)
        adjustment = -1 if action in ("simplify", "english") or (award and score <= 1) else (1 if score >= 3 and award else 0)
        result["metrics"] = metrics
        result["action"] = action
        result["base"] = self.settings()["base"]
        result["teacher"] = self.settings()["teacher"]
        result["assessment_base"] = result.get("assessment_base", result["base"])
        result["assessment"] = clean_assessment(result.get("assessment"), action, result.get("correction", ""))
        notes = compact_notes(result.get("memory"))
        with self.connect() as db:
            session = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
            if not session:
                raise ValueError("Cette conversation est introuvable.")
            if action == "topic":
                if session["mode"] != "coffee" or not 1 <= len(user_text.strip()) <= 400:
                    raise ValueError("Ce changement de sujet appartient au salon café.")
                db.execute("UPDATE sessions SET subject=? WHERE id=?", (user_text.strip(), sid))
            if action not in ("start", "continue"):
                db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (uuid.uuid4().hex, sid, "user", user_text,
                           json.dumps({"action": action, "assessment": result["assessment"], "base": result["base"], "assessment_base": result["assessment_base"], "teacher": result["teacher"]}, ensure_ascii=False), now()))
            old_notes = compact_notes(json.loads(session["notes"]))
            if not notes["summary"]:
                notes = old_notes
                if not notes["summary"]:
                    notes["summary"] = ("Salon café · " + (user_text if action == "topic" else session["subject"])[:200]
                                        if session["mode"] == "coffee" else BY_ID[session["topic"]]["title"]) + " · " + result.get("focus", "")[:160]
                if result.get("correction"):
                    notes["practice"] = list(dict.fromkeys([result["correction"][:120], *notes["practice"]]))[:3]
            notes = compact_notes(notes)
            result["memory"] = notes
            plan = lessons.read_plan(session)
            achieved = lessons.update_plan(plan, result, user_text, action, session["turns"] + 1, result["base"])
            result["lesson_complete"] = achieved
            if achieved:
                plan["status"] = "achieved"
                plan["recap"] = notes
                result["segments"].append(lessons.completion_segment(session["target"]))
                db.execute("UPDATE sessions SET finished=?,summary=? WHERE id=?", (now(), "Objectifs atteints", sid))
            elif plan and plan["status"] == "active" and action in ("start", "reply"):
                # Give the next unfinished task after the independent check,
                # so role-play questions cannot keep the learner on a passed task.
                result["segments"].append(lessons.task_segment(plan, result["base"]))
            if plan:
                db.execute("UPDATE sessions SET lesson=? WHERE id=?", (json.dumps(plan, ensure_ascii=False), sid))
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (mid, sid, "assistant",
                       "\n".join(x["text"] for x in result["segments"]), json.dumps(result, ensure_ascii=False), now()))
            db.execute("UPDATE sessions SET turns=turns+?,xp=xp+?,difficulty=MAX(-3,MIN(3,difficulty+?)) WHERE id=?",
                       (int(award > 0), award, adjustment, sid))
            if award:
                db.execute("INSERT INTO activity VALUES(?,?,?) ON CONFLICT(day,target) DO UPDATE SET xp=xp+excluded.xp",
                           (date.today().isoformat(), session["target"], award))
            db.execute("UPDATE sessions SET notes=? WHERE id=?", (json.dumps(notes, ensure_ascii=False), sid))
            db.execute("INSERT OR REPLACE INTO learner_notes VALUES(?,?,?,?)",
                       (session["target"], sid, json.dumps(notes, ensure_ascii=False), now()))
        return mid, award

    def finish(self, sid):
        session = self.session(sid)
        if session["mode"] == "coffee":
            raise ValueError("Le salon café reste ouvert : quittez-le et reprenez quand vous voulez.")
        if session["finished"]:
            return session
        if session["turns"] < 1:
            raise ValueError("Essayez une réponse avant de terminer cette leçon.")
        plan = session["lesson"]
        plan.update(status="ended_early", recap=session["notes"])
        with self.connect() as db:
            db.execute("UPDATE sessions SET finished=?,summary=?,lesson=? WHERE id=? AND finished IS NULL",
                       (now(), "Séance terminée · objectifs à reprendre", json.dumps(plan, ensure_ascii=False), sid))
        return self.session(sid)

    def resume_objectives(self, sid):
        session = self.session(sid)
        if not session["lesson"] or session["lesson"]["status"] != "ended_early":
            raise ValueError("Cette leçon n’a pas d’objectifs interrompus.")
        plan = session["lesson"]
        plan.update(status="active", recap={})
        plan.pop("teacher_summary", None)
        with self.connect() as db:
            db.execute("UPDATE sessions SET finished=NULL,summary='',lesson=? WHERE id=?", (json.dumps(plan, ensure_ascii=False), sid))
        return self.session(sid)

    def summary_source(self, sid):
        session = self.session(sid)
        if not session["lesson"] or not session["finished"]:
            raise ValueError("Terminez la séance avant de demander son résumé.")
        plan = session["lesson"]
        with self.connect() as db:
            # Stop at the lesson boundary, even after later free conversation.
            rows = db.execute("""SELECT content,payload FROM messages WHERE session_id=?
                AND role='user' AND created<=? ORDER BY created DESC,rowid DESC LIMIT 80""",
                (sid, session["finished"])).fetchall()
        corrections = []
        for row in rows:
            payload = json.loads(row["payload"])
            assessment = payload.get("assessment") or {}
            if assessment.get("corrected"):
                corrections.append({"original": row["content"][:240], "corrected": assessment["corrected"][:300],
                                    "reason": assessment.get("explanation", "")[:300]})
            if len(corrections) == 4:
                break
        return session, {"topic": BY_ID[session["topic"]]["title"], "level": session["level"],
            "target": session["target"], "status": plan["status"], "objectives": plan["objectives"],
            "notes": plan["recap"], "grammar": plan["grammar"], "corrections": corrections,
            "vocabulary": [{"text": v["text"], "english": v.get("english", "")} for v in plan["vocabulary"]
                           if "+" not in v["text"] and "…" not in v["text"] and "..." not in v["text"]
                           and not any(name.casefold() in v["text"].casefold() for name in config.TEACHER_NAMES.values())][:8]}

    def save_lesson_summary(self, sid, finished, summary, teacher):
        with self.connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
            if not row or row["finished"] != finished:
                raise ValueError("La séance a changé. Rouvrez son bilan.")
            plan = lessons.read_plan(row)
            if plan.get("teacher_summary", {}).get("for_finished") == finished:
                return None
            plan["teacher_summary"] = {**summary, "for_finished": finished, "teacher": teacher}
            db.execute("UPDATE sessions SET lesson=? WHERE id=?", (json.dumps(plan, ensure_ascii=False), sid))
            payload = {"action": "summary", "teacher": teacher, "base": summary["language"],
                       "lesson_summary": summary, "segments": lessons.summary_segments(summary)}
            mid = uuid.uuid4().hex
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (mid, sid, "assistant",
                       "\n".join(s["text"] for s in payload["segments"]), json.dumps(payload, ensure_ascii=False), now()))
            return payload

    def review_lesson(self, sid, index, remembered):
        with self.connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
            if not row:
                raise ValueError("Cette leçon est introuvable.")
            plan = lessons.read_plan(row)
            if not plan or type(index) is not int or not 0 <= index < len(plan["vocabulary"]) or type(remembered) is not bool:
                raise ValueError("Expression ou réponse de révision incorrecte.")
            item = plan["vocabulary"][index]
            # Repeated button presses/retries do not inflate a day's practice count.
            today = date.today().isoformat()
            if item.get("reviewed") != today:
                item["reviews"] = item.get("reviews", 0) + 1
                item["reviewed"] = today
                item["remembered"] = remembered
            elif not remembered:
                item["remembered"] = False
            db.execute("UPDATE sessions SET lesson=? WHERE id=?", (json.dumps(plan, ensure_ascii=False), sid))
        return self.session(sid)

    def dashboard(self):
        prefs = self.settings()
        target = prefs["target"]
        with self.connect() as db:
            sessions = [dict(r) for r in db.execute("SELECT * FROM sessions WHERE target=? ORDER BY started DESC LIMIT 100", (target,))]
            completed_rows = db.execute("""SELECT topic,COUNT(*) AS total FROM sessions
                WHERE target=? AND mode='lesson' AND finished IS NOT NULL
                AND json_extract(lesson,'$.status') IN ('achieved','legacy') GROUP BY topic""", (target,)).fetchall()
            lesson_count = sum(r["total"] for r in completed_rows)
            completed = [r["topic"] for r in completed_rows]
            for session in sessions:
                session["notes"] = compact_notes(json.loads(session["notes"]))
                session["lesson"] = lessons.summary(lessons.read_plan(session))
            books = [dict(r) for r in db.execute("SELECT * FROM bookmarks WHERE target=? ORDER BY created DESC", (target,))]
            activity = [dict(r) for r in db.execute("SELECT * FROM activity WHERE target=? ORDER BY day", (target,))]
        days = {r["day"]: r["xp"] for r in activity}
        today = date.today()
        cursor = today if today.isoformat() in days else today - timedelta(days=1)
        streak = 0
        while cursor.isoformat() in days:
            streak += 1
            cursor -= timedelta(days=1)
        week = [{"day": (today - timedelta(days=i)).isoformat(), "xp": days.get((today - timedelta(days=i)).isoformat(), 0)} for i in range(6, -1, -1)]
        return {"settings": prefs, "sessions": sessions[:100], "bookmarks": books,
                "stats": {"xp": sum(days.values()), "today_xp": days.get(today.isoformat(), 0), "streak": streak,
                          "lessons": lesson_count, "week": week,
                          "due": sum(b["due"] <= today.isoformat() for b in books)},
                "completed_topics": completed, "memory": self.memory(target)}

    def memory(self, target):
        with self.connect() as db:
            row = db.execute("SELECT * FROM learner_notes WHERE target=?", (target,)).fetchone()
            if row:
                return {**dict(row), "notes": compact_notes(json.loads(row["notes"]))}
            # Existing histories remain useful after the migration; no expensive
            # background model pass and no fabricated personal facts.
            prior = db.execute("SELECT id,topic,started,notes FROM sessions WHERE target=? AND turns>0 ORDER BY started DESC LIMIT 1", (target,)).fetchone()
            if prior:
                notes = compact_notes(json.loads(prior["notes"]))
                notes["summary"] = notes["summary"] or "Dernier sujet : " + BY_ID[prior["topic"]]["title"]
                if not notes["practice"]:
                    notes["practice"] = [need[:120] for need in self.learning_memory(target)[:3]]
                return {"target": target, "session_id": prior["id"], "notes": notes, "updated": prior["started"]}
        return {"target": target, "session_id": None, "notes": compact_notes({}), "updated": None}

    def message(self, sid, mid):
        with self.connect() as db:
            row = db.execute("SELECT * FROM messages WHERE id=? AND session_id=? AND role='assistant'", (mid, sid)).fetchone()
        if not row:
            raise ValueError("Cette réponse est introuvable.")
        return {**dict(row), "payload": json.loads(row["payload"])}

    def translation(self, mid, segment, language):
        with self.connect() as db:
            row = db.execute("SELECT text FROM translations WHERE message_id=? AND segment=? AND language=?", (mid, segment, language)).fetchone()
        return row[0] if row else None

    def assessment_text(self, sid, mid):
        """Read feedback in its original support language, including old chats."""
        with self.connect() as db:
            row = db.execute("""SELECT m.rowid AS position,m.payload,s.base FROM messages m
                JOIN sessions s ON s.id=m.session_id
                WHERE m.id=? AND m.session_id=? AND m.role='user'""", (mid, sid)).fetchone()
            if not row:
                raise ValueError("Cette correction est introuvable.")
            payload = json.loads(row["payload"])
            assessment = payload.get("assessment") or {}
            text = assessment.get("explanation") or assessment.get("praise")
            if not text:
                raise ValueError("Cette phrase n’a pas d’explication à lire.")
            base = payload.get("assessment_base", payload.get("base"))
            if base not in ("fr", "en"):
                following = db.execute("""SELECT payload FROM messages WHERE session_id=?
                    AND role='assistant' AND rowid>? ORDER BY rowid LIMIT 1""", (sid, row["position"])).fetchone()
                following_payload = json.loads(following[0]) if following else {}
                base = following_payload.get("assessment_base", following_payload.get("base", row["base"]))
            return {"text": text, "language": base}

    def save_translations(self, mid, segment, values):
        with self.connect() as db:
            for language, text in values.items():
                db.execute("INSERT OR REPLACE INTO translations VALUES(?,?,?,?)", (mid, segment, language, text[:2000]))

    def save_bookmark(self, values):
        with self.connect() as db:
            db.execute("""INSERT INTO bookmarks(id,target,text,translation,english,note,created,due)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(target,text) DO UPDATE SET
                translation=excluded.translation,english=excluded.english,note=excluded.note""",
                (uuid.uuid4().hex, values.get("target", self.settings()["target"]), values["text"],
                 values.get("translation", ""), values.get("english", ""), values.get("note", ""), now(), date.today().isoformat()))

    def review(self, bid, remembered):
        with self.connect() as db:
            b = db.execute("SELECT * FROM bookmarks WHERE id=?", (bid,)).fetchone()
            if not b:
                raise ValueError("Expression introuvable.")
            if b["due"] > date.today().isoformat():
                raise ValueError("Cette expression a déjà été révisée aujourd’hui.")
            stage = min(5, b["stage"] + 1) if remembered else 0
            days = [0, 1, 3, 7, 14, 30][stage]
            db.execute("UPDATE bookmarks SET stage=?,due=?,reviews=reviews+1 WHERE id=?",
                       (stage, (date.today() + timedelta(days=days)).isoformat(), bid))

    def delete_bookmark(self, bid):
        with self.connect() as db:
            db.execute("DELETE FROM bookmarks WHERE id=?", (bid,))

    def feedback(self, sid, mid, note):
        if sid is not None:
            self.session(sid)
        if mid is not None:
            self.message(sid, mid)
        with self.connect() as db:
            db.execute("INSERT INTO feedback VALUES(?,?,?,?,?)", (uuid.uuid4().hex, sid, mid, note, now()))

    def learning_memory(self, target):
        """Carry specific recent learning needs into a new lesson, bounded for speed."""
        with self.connect() as db:
            rows = db.execute("""SELECT m.payload FROM messages m JOIN sessions s ON s.id=m.session_id
                WHERE s.target=? AND m.role='assistant' ORDER BY m.created DESC LIMIT 16""", (target,)).fetchall()
        needs = []
        for row in rows:
            payload = json.loads(row["payload"])
            if payload.get("action") in ("reply", "simplify", "english") and (payload.get("score", 2) <= 1 or payload.get("correction")):
                need = (payload.get("focus", "") + ": " + payload.get("correction", "")).strip(": ")
                if need and need not in needs:
                    needs.append(need[:240])
        return needs[:4]

    def export(self):
        with self.connect() as db:
            return {"format": "parliamo", "version": 1, "exported": now(), "tables": {
                table: [dict(r) for r in db.execute(f"SELECT * FROM {table}")]
                for table in ("settings", "sessions", "messages", "bookmarks", "activity", "feedback", "learner_notes", "translations")}}
