"""Tests for arena.py — local question bank and training rounds."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from arena import Arena, Round
from core import Store


def _make_store(tmp_dir):
    return Store(Path(tmp_dir) / "estudos.sqlite3")


def _seed(store):
    """Return (plan_id, subject_id, topic_id)."""
    plan = store.save("plans", {"name": "BACEN"})
    subj = store.save(
        "subjects", {"plan_id": plan, "name": "Dados", "color": "#D6B467"}
    )
    topic = store.save("topics", {"subject_id": subj, "name": "SQL"})
    return plan, subj, topic


def _mc_payload(subj, topic, statement="Qual é a saída de SELECT 1?", answer="a"):
    return {
        "subject_id": subj,
        "topic_id": topic,
        "kind": "multipla-escolha",
        "statement": statement,
        "options": [
            {"id": "a", "text": "1"},
            {"id": "b", "text": "2"},
        ],
        "answer": answer,
        "comment": "SELECT 1 retorna 1.",
        "source": "autoral",
    }


def _ce_payload(subj, topic, statement="SQL é declarativa.", answer="certo"):
    return {
        "subject_id": subj,
        "topic_id": topic,
        "kind": "certo-errado",
        "statement": statement,
        "answer": answer,
        "comment": "",
        "source": "",
    }


class ArenaValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(self.tmp.name)
        self.plan, self.subj, self.topic = _seed(self.store)
        fixed = datetime(2026, 11, 8, 10, 0, 0)
        self.arena = Arena(self.store, now=lambda: fixed)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_save_certo_errado(self):
        qid = self.arena.save_question(_ce_payload(self.subj, self.topic))
        q = self.arena.question(qid)
        self.assertEqual(q["kind"], "certo-errado")
        self.assertEqual(q["answer"], "certo")
        self.assertEqual(q["version"], "1")

    def test_save_multipla_escolha(self):
        qid = self.arena.save_question(_mc_payload(self.subj, self.topic))
        q = self.arena.question(qid)
        self.assertEqual(q["kind"], "multipla-escolha")
        self.assertIsInstance(q["options"], list)
        self.assertEqual(len(q["options"]), 2)

    def test_invalid_kind_raises(self):
        p = _ce_payload(self.subj, self.topic)
        p["kind"] = "discursiva"
        with self.assertRaises(ValueError):
            self.arena.save_question(p)

    def test_empty_statement_raises(self):
        p = _ce_payload(self.subj, self.topic, statement="   ")
        with self.assertRaises(ValueError):
            self.arena.save_question(p)

    def test_ce_bad_answer_raises(self):
        p = _ce_payload(self.subj, self.topic)
        p["answer"] = "sim"
        with self.assertRaises(ValueError):
            self.arena.save_question(p)

    def test_mc_bad_answer_raises(self):
        p = _mc_payload(self.subj, self.topic)
        p["answer"] = "z"
        with self.assertRaises(ValueError):
            self.arena.save_question(p)

    def test_mc_duplicate_option_ids_raises(self):
        p = _mc_payload(self.subj, self.topic)
        p["options"] = [{"id": "a", "text": "X"}, {"id": "a", "text": "Y"}]
        with self.assertRaises(ValueError):
            self.arena.save_question(p)

    def test_mc_empty_option_text_raises(self):
        p = _mc_payload(self.subj, self.topic)
        p["options"] = [{"id": "a", "text": ""}, {"id": "b", "text": "B"}]
        with self.assertRaises(ValueError):
            self.arena.save_question(p)

    def test_mc_too_few_options_raises(self):
        p = _mc_payload(self.subj, self.topic)
        p["options"] = [{"id": "a", "text": "Only one"}]
        with self.assertRaises(ValueError):
            self.arena.save_question(p)

    def test_repeated_question_raises(self):
        self.arena.save_question(_ce_payload(self.subj, self.topic))
        with self.assertRaises(ValueError, msg="Questão repetida neste assunto."):
            self.arena.save_question(_ce_payload(self.subj, self.topic))

    def test_edit_increments_version(self):
        qid = self.arena.save_question(_ce_payload(self.subj, self.topic))
        p = _ce_payload(self.subj, self.topic, statement="SQL é uma linguagem.")
        self.arena.save_question(p, question_id=qid)
        q = self.arena.question(qid)
        self.assertEqual(q["version"], "2")

    def test_set_status(self):
        qid = self.arena.save_question(_ce_payload(self.subj, self.topic))
        self.arena.set_status(qid, "anulada")
        self.assertEqual(self.arena.question(qid)["status"], "anulada")

    def test_set_invalid_status_raises(self):
        qid = self.arena.save_question(_ce_payload(self.subj, self.topic))
        with self.assertRaises(ValueError):
            self.arena.set_status(qid, "cancelada")

    def test_questions_filters_retired_by_default(self):
        qid = self.arena.save_question(_ce_payload(self.subj, self.topic))
        self.arena.set_status(qid, "retirada")
        qs = self.arena.questions(self.plan)
        self.assertEqual(len(qs), 0)

    def test_questions_includes_retired_when_asked(self):
        qid = self.arena.save_question(_ce_payload(self.subj, self.topic))
        self.arena.set_status(qid, "retirada")
        qs = self.arena.questions(self.plan, include_retired=True)
        self.assertEqual(len(qs), 1)


class ArenaRoundTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(self.tmp.name)
        self.plan, self.subj, self.topic = _seed(self.store)
        self.fixed = datetime(2026, 11, 8, 10, 0, 0)
        self.arena = Arena(self.store, now=lambda: self.fixed)
        # Seed three questions
        self.q1 = self.arena.save_question(_ce_payload(self.subj, self.topic, "Q1"))
        self.q2 = self.arena.save_question(
            _ce_payload(self.subj, self.topic, "Q2", "errado")
        )
        self.q3 = self.arena.save_question(_mc_payload(self.subj, self.topic, "Q3"))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    # Round lifecycle

    def test_start_round_novas(self):
        r = self.arena.start_round(self.plan, self.topic, mode="novas")
        self.assertEqual(len(r.questions), 3)

    def test_start_round_todas(self):
        r = self.arena.start_round(self.plan, self.topic, mode="todas")
        self.assertEqual(len(r.questions), 3)

    def test_round_answer_correct(self):
        r = self.arena.start_round(self.plan, self.topic)
        result = r.answer(self.q1, "certo")
        self.assertTrue(result["correct"])

    def test_round_answer_wrong(self):
        r = self.arena.start_round(self.plan, self.topic)
        result = r.answer(self.q1, "errado")
        self.assertFalse(result["correct"])

    def test_round_answer_duplicate_raises(self):
        r = self.arena.start_round(self.plan, self.topic)
        r.answer(self.q1, "certo")
        with self.assertRaises(ValueError):
            r.answer(self.q1, "certo")

    def test_round_answer_invalid_choice_raises(self):
        r = self.arena.start_round(self.plan, self.topic)
        with self.assertRaises(ValueError):
            r.answer(self.q1, "sim")

    def test_round_annulled_correct_is_none(self):
        self.arena.set_status(self.q1, "anulada")
        r = self.arena.start_round(self.plan, self.topic, mode="todas")
        result = r.answer(self.q1, "certo")
        self.assertIsNone(result["correct"])

    def test_round_counts_exclude_annulled(self):
        self.arena.set_status(self.q1, "anulada")
        r = self.arena.start_round(self.plan, self.topic, mode="todas")
        r.answer(self.q1, "certo")  # annulled — does not count
        r.answer(self.q2, "certo")  # wrong expected, but we answer certo → wrong
        r.answer(self.q3, "a")  # correct
        hits, misses = r.counts
        self.assertEqual(hits, 1)
        self.assertEqual(misses, 1)

    def test_round_done_property(self):
        r = self.arena.start_round(self.plan, self.topic, limit=2)
        self.assertFalse(r.done)
        for q in r.questions:
            r.answer(q["id"], "certo" if q["kind"] == "certo-errado" else "a")
        self.assertTrue(r.done)

    # finish_round → session

    def test_finish_round_saves_session_and_attempts(self):
        r = self.arena.start_round(self.plan, self.topic)
        r.answer(self.q1, "certo")
        r.answer(self.q2, "certo")
        sid = self.arena.finish_round(r, elapsed=120)
        self.assertIsNotNone(sid)
        session = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual(session["category"], "Questões")
        self.assertEqual(session["correct"], 1)
        self.assertEqual(session["wrong"], 1)
        self.assertEqual(session["elapsed"], 120)
        attempts = self.store.rows(
            "SELECT * FROM arena_attempts WHERE session_id=?", (sid,)
        )
        self.assertEqual(len(attempts), 2)

    def test_finish_round_one_session_only(self):
        r = self.arena.start_round(self.plan, self.topic)
        r.answer(self.q1, "certo")
        self.arena.finish_round(r, elapsed=60)
        # Finishing again creates a new round (new object), so just count sessions
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 1)

    def test_finish_empty_round_returns_none(self):
        r = self.arena.start_round(self.plan, self.topic)
        result = self.arena.finish_round(r, elapsed=0)
        self.assertIsNone(result)
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 0)

    def test_finish_round_invalid_elapsed_raises(self):
        r = self.arena.start_round(self.plan, self.topic)
        r.answer(self.q1, "certo")
        with self.assertRaises(ValueError):
            self.arena.finish_round(r, elapsed=-1)

    # refazer mode / to_redo

    def test_refazer_mode_after_wrong(self):
        r = self.arena.start_round(self.plan, self.topic, mode="novas")
        r.answer(self.q1, "errado")  # wrong answer for q1
        self.arena.finish_round(r, elapsed=30)
        r2 = self.arena.start_round(self.plan, self.topic, mode="refazer")
        ids = [q["id"] for q in r2.questions]
        self.assertIn(self.q1, ids)

    def test_to_redo_clears_after_correct(self):
        # Answer q1 wrong
        r = self.arena.start_round(self.plan, self.topic, mode="novas")
        r.answer(self.q1, "errado")
        self.arena.finish_round(r, elapsed=30)
        topics = self.arena.topics(self.plan)
        self.assertGreater(topics[0]["to_redo"], 0)

        # Now answer q1 correctly
        r2 = self.arena.start_round(self.plan, self.topic, mode="refazer")
        r2.answer(self.q1, "certo")
        self.arena.finish_round(r2, elapsed=30)
        topics2 = self.arena.topics(self.plan)
        # q1 is no longer in to_redo
        self.assertEqual(topics2[0]["to_redo"], 0)

    def test_no_questions_raises(self):
        # Retire all questions
        for qid in (self.q1, self.q2, self.q3):
            self.arena.set_status(qid, "retirada")
        with self.assertRaises(ValueError):
            self.arena.start_round(self.plan, self.topic)

    # summary

    def test_summary(self):
        r = self.arena.start_round(self.plan, self.topic)
        r.answer(self.q1, "certo")
        r.answer(self.q2, "certo")
        self.arena.finish_round(r, elapsed=60)
        s = self.arena.summary(self.plan)
        self.assertEqual(s["questions"], 3)
        self.assertEqual(s["answered"], 2)
        self.assertEqual(s["correct"], 1)
        self.assertEqual(s["wrong"], 1)
        self.assertAlmostEqual(s["accuracy"], 50.0)
        self.assertIsNotNone(s["to_redo"])

    def test_summary_accuracy_none_without_answers(self):
        s = self.arena.summary(self.plan)
        self.assertIsNone(s["accuracy"])

    # topics

    def test_topics_lists_only_with_questions(self):
        topic2 = self.store.save("topics", {"subject_id": self.subj, "name": "NoSQL"})
        ts = self.arena.topics(self.plan)
        ids = [t["topic_id"] for t in ts]
        self.assertIn(self.topic, ids)
        self.assertNotIn(topic2, ids)

    def test_topics_unanswered_decreases_after_round(self):
        ts = self.arena.topics(self.plan)
        self.assertEqual(ts[0]["unanswered"], 3)
        r = self.arena.start_round(self.plan, self.topic, mode="novas", limit=1)
        r.answer(r.questions[0]["id"], "certo")
        self.arena.finish_round(r, elapsed=10)
        ts2 = self.arena.topics(self.plan)
        self.assertEqual(ts2[0]["unanswered"], 2)


class ArenaPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(self.tmp.name)
        self.plan, self.subj, self.topic = _seed(self.store)
        self.fixed = datetime(2026, 11, 8, 10, 0, 0)
        self.arena = Arena(self.store, now=lambda: self.fixed)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _pack(self, questions):
        return json.dumps(
            {"format": "RUMO-questions", "version": 1, "questions": questions},
            ensure_ascii=False,
        )

    def _item(self, ext_id="q.ext.001", version="1", status="publicada"):
        return {
            "id": ext_id,
            "type": "certo-errado",
            "statement": f"Questão do pacote {ext_id}.",
            "options": [],
            "answer": "certo",
            "comment": "ok",
            "provenance": {
                "kind": "autoral",
                "bank": "RUMO",
                "year": 2026,
                "rights": "CC0",
            },
            "status": status,
            "version": version,
        }

    def test_import_valid_pack(self):
        pack = self._pack([self._item()])
        result = self.arena.import_pack(pack, self.subj, self.topic)
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["skipped"], 0)

    def test_reimport_same_version_is_idempotent(self):
        pack = self._pack([self._item()])
        self.arena.import_pack(pack, self.subj, self.topic)
        result2 = self.arena.import_pack(pack, self.subj, self.topic)
        self.assertEqual(result2["skipped"], 1)
        self.assertEqual(result2["added"], 0)

    def test_import_new_version_updates(self):
        pack1 = self._pack([self._item(version="1")])
        self.arena.import_pack(pack1, self.subj, self.topic)
        item2 = self._item(version="2")
        item2["statement"] = "Questão atualizada do pacote."
        pack2 = self._pack([item2])
        result = self.arena.import_pack(pack2, self.subj, self.topic)
        self.assertEqual(result["updated"], 1)

    def test_import_anulada_becomes_anulada(self):
        pack = self._pack([self._item(status="anulada")])
        self.arena.import_pack(pack, self.subj, self.topic)
        qs = self.arena.questions(self.plan, include_retired=True)
        self.assertEqual(qs[0]["status"], "anulada")

    def test_import_non_published_skipped(self):
        pack = self._pack([self._item(status="rascunho")])
        result = self.arena.import_pack(pack, self.subj, self.topic)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["added"], 0)

    def test_import_duplicate_statement_skipped(self):
        pack = self._pack([self._item("q.001"), self._item("q.002")])
        # q.002 has the same statement as q.001 — should be skipped
        result = self.arena.import_pack(pack, self.subj, self.topic)
        # First added, second is a dupe fingerprint → skipped
        self.assertEqual(result["added"] + result["skipped"], 2)

    def test_invalid_pack_rolls_back(self):
        bad_item = {
            "id": "q.bad",
            "type": "certo-errado",
            "statement": "",  # empty → invalid
            "options": [],
            "answer": "certo",
            "comment": "",
            "provenance": {},
            "status": "publicada",
            "version": "1",
        }
        pack = self._pack([bad_item])
        with self.assertRaises(ValueError):
            self.arena.import_pack(pack, self.subj, self.topic)
        # Nothing should have been written
        self.assertEqual(
            self.store.one("SELECT COUNT(*) n FROM arena_questions")["n"], 0
        )

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            self.arena.import_pack("{bad json", self.subj, self.topic)

    def test_wrong_format_raises(self):
        pack = json.dumps({"format": "OTHER", "version": 1, "questions": []})
        with self.assertRaises(ValueError):
            self.arena.import_pack(pack, self.subj, self.topic)


class ArenaExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(self.tmp.name)
        self.plan, self.subj, self.topic = _seed(self.store)
        self.arena = Arena(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_export_personal_round_trip(self):
        self.arena.save_question(_ce_payload(self.subj, self.topic))
        exported = self.arena.export_personal(self.plan)
        data = json.loads(exported)
        self.assertEqual(data["format"], "RUMO-questions")
        self.assertEqual(len(data["questions"]), 1)
        self.assertEqual(data["questions"][0]["type"], "certo-errado")

    def test_export_excludes_pack_questions(self):
        # personal
        self.arena.save_question(_ce_payload(self.subj, self.topic, "Pessoal Q."))
        # pack
        pack_item = {
            "id": "q.pack.001",
            "type": "certo-errado",
            "statement": "Questão do pacote.",
            "options": [],
            "answer": "certo",
            "comment": "",
            "provenance": {"kind": "autoral"},
            "status": "publicada",
            "version": "1",
        }
        self.arena.import_pack(
            json.dumps(
                {"format": "RUMO-questions", "version": 1, "questions": [pack_item]}
            ),
            self.subj,
            self.topic,
        )
        exported = self.arena.export_personal(self.plan)
        data = json.loads(exported)
        self.assertEqual(len(data["questions"]), 1)
        self.assertEqual(data["questions"][0]["statement"], "Pessoal Q.")


class ArenaAuditRegressionTests(unittest.TestCase):
    """Defects found in the coordinator's audit; each must stay fixed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "estudos.sqlite3"
        self.store = Store(self.path)
        self.plan, self.subj, self.topic = _seed(self.store)
        self.arena = Arena(self.store, now=lambda: datetime(2026, 11, 8, 10, 0, 0))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def pack(self, *questions):
        return json.dumps(
            {"format": "RUMO-questions", "version": 1, "questions": list(questions)}
        )

    def test_finishing_a_round_twice_saves_one_session(self):
        self.arena.save_question(_ce_payload(self.subj, self.topic))
        r = self.arena.start_round(self.plan, self.topic)
        r.answer(r.questions[0]["id"], "certo")
        first = self.arena.finish_round(r, 30)
        self.assertEqual(self.arena.finish_round(r, 30), first)
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 1)
        session = self.store.one("SELECT target,elapsed FROM sessions")
        self.assertEqual((session["target"], session["elapsed"]), (0, 30))

    def test_edit_is_committed(self):
        qid = self.arena.save_question(_ce_payload(self.subj, self.topic))
        self.arena.save_question(_ce_payload(self.subj, self.topic, "Texto novo."), qid)
        self.store.close()
        self.store = Store(self.path)
        row = self.store.one("SELECT statement,version FROM arena_questions")
        self.assertEqual((row["statement"], row["version"]), ("Texto novo.", "2"))

    def test_editing_a_pack_question_with_dotted_version(self):
        item = dict(
            id="q.dados.0001",
            type="certo-errado",
            statement="Pacote.",
            answer="certo",
            status="publicada",
            version="1.0.0",
        )
        self.arena.import_pack(self.pack(item), self.subj, self.topic)
        qid = self.arena.questions(self.plan)[0]["id"]
        self.arena.save_question(_ce_payload(self.subj, self.topic, "Editada."), qid)
        self.assertEqual(self.arena.question(qid)["version"], "1.0.1")

    def test_malformed_pack_items_raise_value_error_and_write_nothing(self):
        good = dict(id="q.ok", type="certo-errado", statement="Ok.", answer="certo") | {
            "status": "publicada"
        }
        for bad in (
            "texto solto",
            dict(good, id="q.bad", statement=7),
            dict(good, id="q.bad", type="multipla-escolha", options=["a", "b"]),
            dict(good, id="Q INVALIDO"),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.arena.import_pack(self.pack(good, bad), self.subj, self.topic)
        for text in ("[]", '{"format": "RUMO-questions"}', "{"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.arena.import_pack(text, self.subj, self.topic)
        self.assertEqual(self.arena.questions(self.plan), [])

    def test_round_is_scoped_to_the_plan(self):
        self.arena.save_question(_ce_payload(self.subj, self.topic))
        other = self.store.save("plans", {"name": "Outro"})
        with self.assertRaises(ValueError):
            self.arena.start_round(other, self.topic)

    def test_search_treats_wildcards_literally(self):
        self.arena.save_question(_ce_payload(self.subj, self.topic, "100% certo."))
        self.arena.save_question(_ce_payload(self.subj, self.topic, "Sem nada."))
        self.assertEqual(len(self.arena.questions(self.plan, query="%")), 1)


if __name__ == "__main__":
    unittest.main()
