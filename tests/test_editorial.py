import copy
import tempfile
import unittest
from pathlib import Path

from editorial import Editorial


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.editor = Editorial(
            Path(self.tmp.name) / "editor.db", {"sql.select": "dados"}
        )
        # Synthetic test data only, never shipped as a real exam question.
        self.item = dict(
            id="test.1",
            version="1",
            statement="EXEMPLO SINTÉTICO DE TESTE",
            subject_id="dados",
            topic_ids=["sql.select"],
            exam_ids=["test"],
            type="certo_errado",
            options=[dict(id="c", text="Certo"), dict(id="e", text="Errado")],
            answer="c",
            comment="Comentário sintético.",
            provenance=dict(
                kind="autoral",
                source_url="https://example.org/test",
                rights="Fixture sintética de teste",
            ),
        )

    def tearDown(self):
        self.editor.close()
        self.tmp.cleanup()

    def test_import_never_publishes_and_normalized_duplicates_are_reported(self):
        duplicate = dict(
            self.item, id="test.2", statement=" exemplo SINTÉTICO de TESTE "
        )
        result = self.editor.import_batch([self.item, duplicate], "Editor")
        self.assertEqual(result["added"], ["test.1"])
        self.assertEqual(result["duplicates"][0]["existing"], "test.1")
        self.assertEqual(self.editor.items()[0]["status"], "draft")
        with self.assertRaises(ValueError):
            self.editor.prepare(["test.1"], "Editor")

    def test_correction_invalidates_review_and_prepare_is_atomic(self):
        self.editor.import_batch([self.item], "Editor")
        self.editor.approve("test.1", "Revisor")
        self.editor.correct(dict(self.item, answer="e"), "Editor")
        self.assertIsNone(self.editor.items()[0]["review"])
        self.editor.approve("test.1", "Revisor")
        with self.assertRaises(ValueError):
            self.editor.prepare(["test.1", "missing"], "Editor")
        self.assertEqual(self.editor.items()[0]["status"], "approved")
        manifest = self.editor.prepare(["test.1"], "Editor")
        self.assertFalse(manifest["published"])
        self.assertEqual(manifest["questions"][0]["answer"], "e")
        withdrawal = self.editor.withdraw("test.1", "Revisor", "Gabarito incorreto")
        self.assertFalse(withdrawal["applied"])
        self.assertEqual(self.editor.items()[0]["status"], "withdrawn")
        self.assertGreater(
            self.editor.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 3
        )

    def test_new_version_preserves_identifier_and_previous_edition(self):
        self.editor.import_batch([self.item], "Editor")
        self.editor.approve("test.1", "Revisor")
        first = self.editor.prepare(["test.1"], "Editor")
        self.assertEqual(
            self.editor.prepare(["test.1"], "Editor")["questions"], first["questions"]
        )
        with self.assertRaises(ValueError):
            self.editor.correct(dict(self.item, answer="e"), "Editor")
        self.editor.correct(dict(self.item, version="2", answer="e"), "Editor")
        self.editor.approve("test.1", "Revisor")
        second = self.editor.prepare(["test.1"], "Editor")
        self.assertEqual(second["questions"][0]["id"], "test.1")
        self.assertEqual(
            self.editor.db.execute("SELECT COUNT(*) FROM editions").fetchone()[0], 2
        )

    def test_rejects_a_personal_database_without_modifying_its_tables(self):
        import sqlite3

        path = Path(self.tmp.name) / "personal.db"
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE sessions(id TEXT)")
        db.close()
        with self.assertRaises(ValueError):
            Editorial(path, {})
        db = sqlite3.connect(path)
        self.assertEqual(
            db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),
            [("sessions",)],
        )
        db.close()

    def test_invalid_classification_rights_and_key_roll_back_whole_batch(self):
        for patch in (
            dict(topic_ids=["unknown"]),
            dict(answer="z"),
            dict(provenance={}),
        ):
            bad = copy.deepcopy(self.item)
            bad.update(patch, id="bad", statement="Outra fixture")
            with self.assertRaises(ValueError):
                self.editor.import_batch([self.item, bad], "Editor")
            self.assertEqual(self.editor.items(), [])
