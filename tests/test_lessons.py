import copy
import json
import threading
import urllib.request
from unittest.mock import patch

import test_teacher
from test_teacher import StoreCase, REPLY
from teacher import engine, lessons
from teacher.store import Store
from teacher.server import AppServer, ensure_lesson_summary, settings_values


def reply(step="step1", quote="Ciao, mi chiamo Luca."):
    return {**copy.deepcopy(REPLY), "assessment": {"rating": 5, "verdict": "correct", "clarity": "clear"},
            "objective_evidence": {"id": step, "achieved": True, "quote": quote},
            "memory": {"summary": "Présentation réussie.", "practice": ["Les articles"]}}


class LessonTest(StoreCase):
    def test_summary_uses_lesson_boundary_and_keeps_corrections_without_new_xp(self):
        sid = self.store.new_session("hello")["id"]
        assessment = {"rating": 3, "verdict": "needs_work", "clarity": "clear", "corrected": "Ho trent’anni.", "explanation": "Pour l’âge, utilisez avere."}
        self.store.commit_turn(sid, "Io sono trent’anni.", {**copy.deepcopy(REPLY), "assessment": assessment}, "reply", {})
        ended = self.store.finish(sid)
        self.store.commit_turn(sid, "Later conversation", {**copy.deepcopy(REPLY), "assessment": {**assessment, "corrected": "Later correction"}}, "reply", {})
        session, source = self.store.summary_source(sid)
        self.assertEqual([c["corrected"] for c in source["corrections"]], ["Ho trent’anni."])
        with self.store.connect() as db:
            plan = session["lesson"]
            plan["vocabulary"].extend([{"text": "Mi chiamo Sofia."}, {"text": "Sono di + paese"}])
            db.execute("UPDATE sessions SET lesson=? WHERE id=?", (json.dumps(plan), sid))
        _, source = self.store.summary_source(sid)
        self.assertNotIn("Mi chiamo Sofia.", [v["text"] for v in source["vocabulary"]])
        self.assertNotIn("Sono di + paese", [v["text"] for v in source["vocabulary"]])
        before = self.store.dashboard()["stats"]
        summary = {"language": "fr", "overview": "Nous avons pratiqué les présentations.", "points": ["Pour l’âge, utilisez avere."], "next_step": "Essayez une autre présentation."}
        with patch.object(engine, "summarize_lesson", return_value=summary) as generate:
            first = ensure_lesson_summary(self.store, sid)
            second = ensure_lesson_summary(self.store, sid)
            generate.assert_called_once()
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        saved = Store(self.store.path).session(sid)
        self.assertEqual(saved["lesson"]["teacher_summary"]["for_finished"], ended["finished"])
        self.assertEqual(sum(m["payload"].get("action") == "summary" for m in saved["messages"]), 1)
        self.assertEqual(self.store.dashboard()["stats"], before)
        self.store.resume_objectives(sid)
        self.assertNotIn("teacher_summary", self.store.session(sid)["lesson"])

    def test_summary_failure_keeps_completion_and_saves_useful_fallback(self):
        sid = self.store.new_session("cafe")["id"]
        self.turn(sid)
        finished = self.store.finish(sid)["finished"]
        with patch.object(engine, "summarize_lesson", side_effect=ValueError("invalid output")):
            payload = ensure_lesson_summary(self.store, sid)
        self.assertEqual(payload["lesson_summary"]["source"], "saved_learning")
        self.assertIn("caffè", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(self.store.session(sid)["finished"], finished)
        self.assertEqual(self.store.dashboard()["stats"]["lessons"], 0)

    def test_corrections_default_to_french_independently_of_support_language(self):
        self.store.update_settings({"base": "en"})
        self.assertEqual(self.store.settings()["feedback_base"], "fr")
        sid = self.store.new_session("hello")["id"]
        self.turn(sid, result={**copy.deepcopy(REPLY), "assessment_base": "fr", "assessment": {"explanation": "Utilisez avoir pour l’âge."}})
        mid = self.store.session(sid)["messages"][0]["id"]
        self.assertEqual(self.store.assessment_text(sid, mid)["language"], "fr")
        self.assertEqual(settings_values({"feedback_base": "en"}), {"feedback_base": "en"})
        with self.assertRaises(ValueError): settings_values({"feedback_base": "it"})
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

    def test_completion_and_one_summary_are_streamed_and_persisted(self):
        sid = self.store.new_session("hello")["id"]
        for step in ("step1", "step2"):
            self.store.commit_turn(sid, "Ciao", reply(step, "Ciao"), "reply", {})
        def stream(*args):
            result = reply("step3", "Come stai?")
            yield {"type": "segment", "segment": result["segments"][0], "index": 0}
            yield {"type": "result", "result": result, "metrics": {}}
        summary = {"language": "fr", "overview": "Nous avons fait connaissance.", "points": ["Vous avez donné votre nom."], "next_step": "Réutilisez ces phrases."}
        with patch.object(engine, "stream_turn", stream), patch.object(engine, "summarize_lesson", return_value=summary):
            with self.call("/api/turn", {"session_id": sid, "text": "Come stai?"}) as response:
                events = [json.loads(line) for line in response]
        self.assertTrue(events[-1]["just_completed"])
        self.assertIn(lessons.completion_segment("it"), [e["segment"] for e in events if e["type"] == "segment"])
        self.assertEqual(events[-2]["type"], "lesson_summary")
        self.assertEqual(events[-1]["session"]["lesson"]["status"], "achieved")
        with self.call("/api/lesson-review", {"session_id": sid, "index": 0, "remembered": True}) as response:
            self.assertEqual(json.load(response)["lesson"]["vocabulary"][0]["reviews"], 1)

    def test_finish_generates_summary_once_and_legacy_recap_can_request_one(self):
        sid = self.store.new_session("hello")["id"]
        self.turn(sid)
        with patch.object(engine, "summarize_lesson", side_effect=lambda source, base, model: lessons.fallback_summary(source, base)) as generate:
            for path in ("/api/finish", "/api/finish", "/api/lesson-summary"):
                with self.call(path, {"session_id": sid}) as response:
                    session = json.load(response)
                self.assertIn("teacher_summary", session["lesson"])
            generate.assert_called_once()
        self.assertEqual(session["xp"], 10)
        other = self.store.new_session("cafe")["id"]
        self.turn(other)
        self.store.finish(other)
        with patch.object(engine, "summarize_lesson", side_effect=lambda source, base, model: lessons.fallback_summary(source, base)):
            with self.call("/api/lesson-summary", {"session_id": other}) as response:
                self.assertTrue(json.load(response)["summary_created"])

    def test_feedback_french_and_english_use_separate_caches_and_original_language(self):
        sid = self.store.new_session("hello")["id"]
        assessment = {"rating": 3, "verdict": "needs_work", "explanation": "Pour l’âge, utilisez avere.", "corrected": "Ho trent’anni."}
        self.turn(sid, result={**copy.deepcopy(REPLY), "assessment_base": "fr", "assessment": assessment})
        mid = self.store.session(sid)["messages"][0]["id"]
        original = self.store.session(sid)
        with patch.object(engine, "translate_phrase", return_value={"translation": "For age, use avere.", "english": "For age, use avere."}) as translate:
            for language in (None, "en", "fr", "en", "fr"):
                with self.call("/api/assessment-explanation", {"session_id": sid, "message_id": mid, **({"language": language} if language else {})}) as response:
                    result = json.load(response)
                self.assertEqual(result["language"], language or "fr")
            translate.assert_called_once()
        self.assertEqual(self.store.session(sid), original)
        self.store.update_settings({"base": "en"})
        self.turn(sid, result={**copy.deepcopy(REPLY), "assessment_base": "en", "assessment": {**assessment, "explanation": "Use avere for age."}})
        mid = self.store.session(sid)["messages"][-2]["id"]
        with patch.object(engine, "translate_phrase", return_value={"translation": "Pour l’âge, utilisez avere.", "english": "Use avere for age."}) as translate:
            for _ in range(2):
                with self.call("/api/assessment-explanation", {"session_id": sid, "message_id": mid}) as response:
                    self.assertEqual(json.load(response)["language"], "fr")
            translate.assert_called_once_with("Use avere for age.", "en", "fr", self.store.settings()["model"])
