import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import SCHEMA, TABLES, Store, data_dir
from storage import migrate_existing_data, migration_lock


class StorageMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source = self.base / "previous-installation"
        self.original = Store(self.source / "estudos.sqlite3")
        self.plan = self.original.save("plans", {"name": "Plano pessoal"})
        self.original.set_pref("theme", "Claro")
        self.original.set_pref("backup_folder", str(self.source / "backups"))
        self.target = self.base / "RUMO"

    def tearDown(self):
        self.original.db.close()
        self.tmp.cleanup()

    def test_schema_discovery_preserves_original_ids_settings_and_wal(self):
        migrate_existing_data(self.base, self.target, SCHEMA, TABLES)
        copied = Store(self.target / "estudos.sqlite3")
        try:
            self.assertEqual(
                copied.one("SELECT name FROM plans WHERE id=?", (self.plan,))["name"],
                "Plano pessoal",
            )
            self.assertEqual(copied.pref("theme"), "Claro")
            self.assertEqual(copied.pref("backup_folder"), str(self.target / "backups"))
            self.assertEqual(
                self.original.pref("backup_folder"), str(self.source / "backups")
            )
            self.assertIsNotNone(
                self.original.one("SELECT id FROM plans WHERE id=?", (self.plan,))
            )
            copied.save("plans", {"id": self.plan, "name": "Depois"})
        finally:
            copied.db.close()
        migrate_existing_data(self.base, self.target, SCHEMA, TABLES)
        copied = Store(self.target / "estudos.sqlite3")
        self.assertEqual(
            copied.one("SELECT name FROM plans WHERE id=?", (self.plan,))["name"],
            "Depois",
        )
        copied.db.close()

    def test_running_previous_application_blocks_migration(self):
        with migration_lock(self.source):
            with self.assertRaises(ValueError):
                migrate_existing_data(self.base, self.target, SCHEMA, TABLES)
        self.assertFalse((self.target / "estudos.sqlite3").exists())

    def test_ambiguous_sources_are_never_silently_selected(self):
        other = Store(self.base / "other" / "estudos.sqlite3")
        other.db.close()
        with self.assertRaises(ValueError):
            migrate_existing_data(self.base, self.target, SCHEMA, TABLES)
        self.assertFalse((self.target / "estudos.sqlite3").exists())

    def test_invalid_previous_data_does_not_silently_create_an_empty_database(self):
        self.original.db.execute("CREATE VIEW unexpected AS SELECT * FROM plans")
        self.original.db.commit()
        with self.assertRaises(ValueError):
            migrate_existing_data(self.base, self.target, SCHEMA, TABLES)
        self.assertFalse((self.target / "estudos.sqlite3").exists())
        self.assertIsNotNone(
            self.original.one("SELECT id FROM plans WHERE id=?", (self.plan,))
        )

    def test_override_skips_automatic_import(self):
        isolated = self.base / "isolated"
        with patch.dict(
            "os.environ", {"LOCALAPPDATA": str(self.base), "RUMO_DATA": str(isolated)}
        ):
            self.assertEqual(data_dir(), isolated)
        self.assertFalse(self.target.exists())

    def test_old_json_brand_is_not_required_but_structure_is_validated(self):
        snapshot = self.original.snapshot()
        snapshot["format"] = "previous-brand"
        path = self.base / "backup.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        recovered = self.original.validate_backup(path)
        self.assertEqual(recovered["tables"]["plans"][0]["id"], self.plan)
        snapshot["tables"]["plans"][0]["extra"] = "invalid"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.original.validate_backup(path)

    def test_unrelated_database_and_symlink_are_ignored(self):
        self.original.db.close()
        self.source.rename(self.base / "outside")
        # A symbolic link must not cause a database to be imported from elsewhere.
        real = self.base / "outside"
        self.original = Store(real / "estudos.sqlite3")
        with tempfile.TemporaryDirectory() as root:
            local = Path(root)
            try:
                (local / "linked").symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("Symlinks unavailable on this platform")
            migrate_existing_data(local, local / "RUMO", SCHEMA, TABLES)
            self.assertFalse((local / "RUMO" / "estudos.sqlite3").exists())
