import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from core import Store
from security import csv_cell, directory_path, web_url


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.store = Store(self.folder / "study.sqlite3")
        self.plan = self.store.save("plans", {"name": "Teste"})
        self.subject = self.store.save(
            "subjects", {"plan_id": self.plan, "name": "Matéria", "color": "#D6B467"}
        )
        self.topic = self.store.save(
            "topics", {"subject_id": self.subject, "name": "Assunto"}
        )

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def write_backup(self, data):
        path = self.folder / "input.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_retention_never_deletes_other_databases(self):
        unrelated = self.folder / "important.sqlite3"
        unrelated.write_bytes(b"keep")
        previous = self.folder / "pre-v1.4.0.sqlite3"
        previous.write_bytes(b"keep backup")
        self.store.set_pref("backup_folder", str(self.folder))
        self.store.set_pref("retention", 1)
        first = self.store.auto_backup(True)
        second = self.store.auto_backup(True)
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())
        self.assertEqual(unrelated.read_bytes(), b"keep")
        self.assertTrue(previous.exists())
        self.assertTrue(self.store.path.exists())

    def test_backup_cannot_redirect_destination(self):
        data = self.store.snapshot()
        data["tables"]["preferences"].append(
            {"key": "backup_folder", "value": json.dumps(str(self.folder / "foreign"))}
        )
        chosen = self.folder / "chosen"
        self.store.set_pref("backup_folder", str(chosen))
        self.store.restore(self.write_backup(data))
        self.assertEqual(self.store.pref("backup_folder"), str(chosen))
        self.assertFalse((self.folder / "foreign").exists())

    def test_sqlite_trigger_is_rejected_without_changing_data(self):
        path = self.store.auto_backup(True)
        connection = sqlite3.connect(path)
        connection.execute(
            "CREATE TRIGGER malicious AFTER INSERT ON plans BEGIN DELETE FROM topics; END"
        )
        connection.close()
        with self.assertRaises(ValueError):
            self.store.restore(path)
        self.assertIsNotNone(
            self.store.one("SELECT id FROM topics WHERE id=?", (self.topic,))
        )

    def test_sqlite_view_is_rejected(self):
        path = self.store.auto_backup(True)
        connection = sqlite3.connect(path)
        connection.execute("CREATE VIEW unexpected AS SELECT * FROM plans")
        connection.close()
        with self.assertRaises(ValueError):
            self.store.validate_backup(path)

    def test_oversized_json_rejected_before_loading(self):
        path = self.folder / "big.json"
        with path.open("wb") as stream:
            stream.truncate(20 * 1024 * 1024 + 1)
        with self.assertRaises(ValueError):
            self.store.validate_backup(path)

    def test_malformed_goal_and_focus_preferences_rejected(self):
        for key, value in [
            ("main_goal_x", []),
            ("focus_minutes", 0),
            ("show_main_goal", "yes"),
        ]:
            with self.subTest(key=key):
                data = self.store.snapshot()
                data["tables"]["preferences"].append(
                    {"key": key, "value": json.dumps(value)}
                )
                with self.assertRaises(ValueError):
                    self.store.validate_backup(self.write_backup(data))

    def test_circular_topic_update_rejected_atomically(self):
        child = self.store.save(
            "topics",
            {"subject_id": self.subject, "parent_id": self.topic, "name": "Filho"},
        )
        with self.assertRaises(ValueError):
            self.store.save("topics", {"id": self.topic, "parent_id": child})
        self.assertIsNone(
            self.store.one("SELECT parent_id FROM topics WHERE id=?", (self.topic,))[
                "parent_id"
            ]
        )

    def test_parent_with_children_cannot_change_subject(self):
        self.store.save(
            "topics",
            {"subject_id": self.subject, "parent_id": self.topic, "name": "Filho"},
        )
        other = self.store.save(
            "subjects", {"plan_id": self.plan, "name": "Outra", "color": "#D6B467"}
        )
        with self.assertRaises(ValueError):
            self.store.save("topics", {"id": self.topic, "subject_id": other})

    def test_block_from_another_plan_rejected_in_backup(self):
        other = self.store.save("plans", {"name": "Outro plano"})
        cycle = self.store.save("cycles", {"plan_id": other, "name": "Ciclo"})
        self.store.save(
            "blocks",
            {"cycle_id": cycle, "subject_id": self.subject, "target": 1500, "sort": 0},
        )
        with self.assertRaises(ValueError):
            self.store.validate_backup(self.write_backup(self.store.snapshot()))

    def test_untrusted_subject_filter_cannot_change_sql(self):
        attack = "x' OR 1=1; DROP TABLE topics; --"
        self.assertEqual(self.store.sessions(self.plan, {"subject_id": attack}), [])
        self.assertEqual(
            self.store.stats(self.plan, {"subject_id": attack})["elapsed"], 0
        )
        self.assertEqual(self.store.grouped(self.plan, {"subject_id": attack}), [])
        self.store.export_csv(
            self.folder / "filter.csv", self.plan, {"subject_id": attack}
        )
        self.assertIsNotNone(
            self.store.one("SELECT id FROM topics WHERE id=?", (self.topic,))
        )

    def test_csv_formula_payloads_are_literal(self):
        for value in [
            '=WEBSERVICE("https://example.com")',
            " +cmd",
            "@SUM(A1)",
            "\t=1",
            "-1+2",
        ]:
            self.assertEqual(csv_cell(value), "'" + value)
        self.assertEqual(csv_cell(42), 42)
        self.assertEqual(csv_cell("Observação normal"), "Observação normal")

    def test_csv_export_escapes_notes(self):
        self.store.save_session(
            {
                "plan_id": self.plan,
                "subject_id": self.subject,
                "topic_id": self.topic,
                "day": "2026-10-11",
                "category": "Teoria",
                "target": 1500,
                "elapsed": 1500,
                "notes": "=1+1",
            }
        )
        path = self.folder / "export.csv"
        self.store.export_csv(path, self.plan)
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter=";"))
        self.assertEqual(rows[0]["observacoes"], "'=1+1")

    def test_web_links_reject_commands_credentials_and_controls(self):
        for url in [
            "file:///C:/Windows/system32/cmd.exe",
            "javascript:alert(1)",
            "https://user:pass@example.com",
            "https://example.com\n",
            "https://",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                web_url(url)
        self.assertEqual(
            web_url("https://example.com/path"), "https://example.com/path"
        )

    def test_open_folder_does_not_accept_a_program(self):
        program = self.folder / "malicious.exe"
        program.write_bytes(b"not executable")
        with self.assertRaises(ValueError):
            directory_path(program)
        self.assertEqual(directory_path(self.folder), self.folder.resolve())

    def test_backup_restores_valid_parent_created_after_child(self):
        parent = self.store.save(
            "topics", {"subject_id": self.subject, "name": "Pai criado depois"}
        )
        self.store.save("topics", {"id": self.topic, "parent_id": parent})
        path = self.write_backup(self.store.snapshot())
        self.store.restore(path)
        self.assertEqual(
            self.store.one("SELECT parent_id FROM topics WHERE id=?", (self.topic,))[
                "parent_id"
            ],
            parent,
        )
