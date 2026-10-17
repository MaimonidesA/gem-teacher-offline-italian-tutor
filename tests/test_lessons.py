import copy
import json
import threading
import urllib.request
from unittest.mock import patch

import test_teacher
from test_teacher import StoreCase, REPLY
from teacher import engine, lessons
from teacher.store import Store
from teacher.server import AppServer


def reply(step="step1", quote="Ciao, mi chiamo Luca."):
    return {**copy.deepcopy(REPLY), "assessment": {"rating": 5, "verdict": "correct", "clarity": "clear"},
            "objective_evidence": {"id": step, "achieved": True, "quote": quote},
            "memory": {"summary": "Présentation réussie.", "practice": ["Les articles"]}}


class LessonTest(StoreCase):
    def commit(self, sid, step, text, action="reply", **changes):
        self.store.commit_turn(sid, text, {**reply(step, text), **changes}, action, {})
        return self.store.session(sid)

    def test_objectives_require_actual_evidence_and_feedback_not_turn_counts(self):
        sid = self.store.new_session("hello")["id"]
        for _ in range(5):
            self.turn(sid, result={**REPLY, "lesson_complete": True})
        self.assertIsNone(self.store.session(sid)["finished"])
        for action in ("start", "hint", "simplify", "english"):
            self.commit(sid, "step1", "Ciao, mi chiamo Luca.", action)
        for changes in ({"objective_evidence": {"id": "step1", "achieved": True, "quote": "invented text"}},
                        {"assessment": {"rating": 0, "verdict": "unclear", "clarity": "unclear"}},
                        {"assessment": None}):
            self.commit(sid, "step1", "Ciao, mi chiamo Luca.", **changes)
        self.assertEqual(sum(bool(o["evidence"]) for o in self.store.session(sid)["lesson"]["objectives"]), 0)
        self.commit(sid, "step3", "Come stai?")
        self.assertEqual(sum(bool(o["evidence"]) for o in self.store.session(sid)["lesson"]["objectives"]), 0)

    def test_goal_completion_announces_once_freezes_recap_and_chat_stays_open(self):
        sid = self.store.new_session("hello")["id"]
        for step, text in [("step1", "Ciao, mi chiamo Luca."), ("step2", "Sono francese."), ("step3", "Come stai?")]:
            session = self.commit(sid, step, text)
            if step != "step3":
                self.assertEqual(session["messages"][-1]["payload"]["segments"][-1], lessons.task_segment(session["lesson"], "fr"))
        self.assertEqual(session["lesson"]["status"], "achieved")
        self.assertEqual(session["phase"], "conversation")
        self.assertEqual(session["messages"][-1]["payload"]["segments"][-1], lessons.completion_segment("it"))
        frozen = session["lesson"]
        for _ in range(3):
            later = self.commit(sid, "step3", "Parliamo di libri!", memory={"summary": "New conversation"},
                                phrase={"text": "New post-lesson phrase"})
            self.assertNotIn(lessons.completion_segment("it"), later["messages"][-1]["payload"]["segments"])
        self.assertEqual(later["lesson"], frozen)
        self.assertEqual(later["finished"], session["finished"])
        self.assertEqual(self.store.finish(sid)["lesson"], frozen)
        self.assertEqual(self.store.dashboard()["completed_topics"], ["hello"])
        self.assertEqual(self.store.dashboard()["stats"]["lessons"], 1)

    def test_finish_early_then_resume_keeps_evidence_without_false_completion(self):
        sid = self.store.new_session("hello")["id"]
        self.commit(sid, "step1", "Ciao, mi chiamo Luca.")
        finished = self.store.finish(sid)
        self.assertEqual(finished["lesson"]["status"], "ended_early")
        self.assertEqual(self.store.dashboard()["completed_topics"], [])
        resumed = self.store.resume_objectives(sid)
        self.assertIsNone(resumed["finished"])
        self.assertTrue(resumed["lesson"]["objectives"][0]["evidence"])
        self.commit(sid, "step2", "Sono francese.")
        self.assertEqual(self.commit(sid, "step3", "Come stai?")["lesson"]["status"], "achieved")

    def test_vocabulary_is_bounded_and_practice_survives_restart_without_xp(self):
        sid = self.store.new_session("cafe")["id"]
        for i in range(40):
            self.turn(sid, result={**REPLY, "phrase": {"text": f"espressione {i}", "translation": "une expression", "english": "an expression"}})
        session = self.store.session(sid)
        self.assertEqual(len(session["lesson"]["vocabulary"]), 12)
        before = session["xp"]
        self.store.review_lesson(sid, 0, True)
        self.store.review_lesson(sid, 0, True)
        self.store.review_lesson(sid, 0, False)
        restored = Store(self.store.path).session(sid)
        self.assertEqual(restored["lesson"]["vocabulary"][0]["reviews"], 1)
        self.assertFalse(restored["lesson"]["vocabulary"][0]["remembered"])
        self.assertEqual(restored["xp"], before)
        self.assertLess(len(json.dumps(restored["lesson"])), 9000)
        for index, remembered in ((-1, True), (12, True), (True, True), (0, "true")):
            with self.assertRaises(ValueError): self.store.review_lesson(sid, index, remembered)

    def test_existing_completed_lessons_keep_credit_without_fabricated_evidence(self):
        sid = self.store.new_session("hello")["id"]
        self.turn(sid)
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET lesson='{}',finished='2026-01-01' WHERE id=?", (sid,))
        migrated = Store(self.store.path)
        session = migrated.session(sid)
        self.assertEqual(session["lesson"]["status"], "legacy")
        self.assertTrue(all(not o["evidence"] for o in session["lesson"]["objectives"]))
        self.assertEqual(migrated.dashboard()["stats"]["lessons"], 1)
        self.assertEqual(session, Store(self.store.path).session(sid))

    def test_every_topic_has_level_appropriate_tip_and_no_italian_leaks_to_other_targets(self):
        for topic in lessons.OBJECTIVES:
            for level in ("A0", "A1", "A2", "B1", "B2"):
                plan = lessons.new_plan(topic, level, "it")
                self.assertEqual(len(plan["objectives"]), 3)
                self.assertTrue(all(plan["grammar"][key] for key in ("fr", "en", "example")))
                self.assertTrue(plan["vocabulary"])
            self.assertNotEqual(lessons.new_plan(topic, "A1", "it")["grammar"], lessons.new_plan(topic, "A2", "it")["grammar"])
        self.store.update_settings({"target": "fr"})
        plan = self.store.new_session("cafe")["lesson"]
        self.assertIsNone(plan["grammar"])
        self.assertEqual(plan["vocabulary"], [])
        self.assertIsNone(self.store.new_session("free", "coffee")["lesson"])

    def test_prompt_targets_remaining_objective_and_reviewer_uses_same_call(self):
        sid = self.store.new_session("hello")["id"]
        session = self.commit(sid, "step1", "Ciao, mi chiamo Luca.")
        prompt = engine.prompt(session, self.store.settings(), "reply")
        self.assertIn("CURRENT OBJECTIVE: Say where you are from", prompt)
        objective = session["lesson"]["objectives"][1]
        answer = {**reply()["assessment"], "objective": {"achieved": True, "quote": "Sono francese."}}
        with patch.object(engine, "query", return_value={"message": {"content": json.dumps(answer)}}) as query:
            assessment = engine.assess_phrase("Sono francese.", "it", "en", "local-model", "Di dove sei?", objective)
        query.assert_called_once()
        self.assertEqual(assessment["objective_evidence"]["id"], "step2")
        self.assertIn("objective", query.call_args.args[1]["format"]["required"])


# Reuse the HTTP fixture without collecting all its inherited test methods twice.
class LessonHTTPTest(StoreCase):
    call = test_teacher.HTTPTest.call

    def setUp(self):
        super().setUp()
        self.server = AppServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        super().tearDown()

    def test_completion_segment_streamed_and_persisted_with_no_additional_generation(self):
        sid = self.store.new_session("hello")["id"]
        for step in ("step1", "step2"):
            self.store.commit_turn(sid, "Ciao", reply(step, "Ciao"), "reply", {})
        def stream(*args):
            result = reply("step3", "Come stai?")
            yield {"type": "segment", "segment": result["segments"][0], "index": 0}
            yield {"type": "result", "result": result, "metrics": {}}
        with patch.object(engine, "stream_turn", stream):
            with self.call("/api/turn", {"session_id": sid, "text": "Come stai?"}) as response:
                events = [json.loads(line) for line in response]
        self.assertTrue(events[-1]["just_completed"])
        self.assertEqual(events[-2]["segment"], lessons.completion_segment("it"))
        self.assertEqual(events[-1]["session"]["lesson"]["status"], "achieved")
        with self.call("/api/lesson-review", {"session_id": sid, "index": 0, "remembered": True}) as response:
            self.assertEqual(json.load(response)["lesson"]["vocabulary"][0]["reviews"], 1)
