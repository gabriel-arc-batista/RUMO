import json
import os
import stat
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import token_store
from core import Store
from learning import create_starter_cycle
from desktop_sync import (
    FEATURE_KEY,
    capture_profile_and_cycle,
    note_server_features,
    character_snapshot,
    cycle_snapshot,
    service_for,
    workspace_for,
)
from pdf_reader import page_ranges, parse_ranges


class ProfileCycleTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "study.sqlite3")
        self.plan = self.store.save("plans", dict(name="Plano de exemplo"))
        self.subject = self.store.save(
            "subjects", dict(plan_id=self.plan, name="Bancos de dados", color="#D6B467")
        )
        self.topic = self.store.save(
            "topics", dict(subject_id=self.subject, name="Normalização")
        )
        self.workspace = workspace_for(self.store)
        self.service = service_for(self.store)

    def tearDown(self):
        self.workspace.close()
        self.store.close()
        self.folder.cleanup()

    def queued(self, kind):
        return [
            e
            for e in (
                json.loads(r[0])
                for r in self.workspace.db.execute("SELECT envelope FROM outbox")
            )
            if e["kind"] == kind
        ]

    def test_snapshots_contain_only_shareable_fields(self):
        profile = character_snapshot(self.store, self.plan)
        self.assertEqual(set(profile), {"name", "look", "equipped"})
        self.assertTrue(all(isinstance(v, str) for v in profile["look"].values()))
        create_starter_cycle(self.store, self.plan, minutes=45)
        cycle = cycle_snapshot(self.store, self.plan)
        self.assertEqual(cycle["plan_name"], "Plano de exemplo")
        self.assertTrue(cycle["items"])
        item = cycle["items"][0]
        self.assertEqual(
            set(item), {"subject", "topic", "category", "target_minutes", "done"}
        )
        self.assertEqual(item["target_minutes"], 45)

    def test_no_queue_without_account_and_only_on_change(self):
        capture_profile_and_cycle(self.store, self.plan)
        self.assertEqual(self.queued("profile.character"), [])
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        # Serviço sem a migração 009: nada é enfileirado (não trava a fila).
        capture_profile_and_cycle(self.store, self.plan)
        self.assertEqual(self.queued("profile.character"), [])

        class Old:
            def progress_summary(self):
                return {"level": 1, "look": None}

        class New:
            def progress_summary(self):
                return {"level": 1, "look": None, "victories": 0}

        self.assertFalse(note_server_features(self.workspace, Old()))
        self.assertTrue(note_server_features(self.workspace, New()))
        self.assertEqual(self.workspace._meta(FEATURE_KEY), "1")
        capture_profile_and_cycle(self.store, self.plan)
        capture_profile_and_cycle(self.store, self.plan)
        self.assertEqual(len(self.queued("profile.character")), 1)
        self.assertEqual(len(self.queued("cycle.snapshot")), 1)
        with self.store.db:
            self.store.db.execute(
                "INSERT INTO rpg_characters VALUES(?,?) ON CONFLICT(plan_id) DO UPDATE SET name=excluded.name",
                (self.plan, "Exploradora"),
            )
        capture_profile_and_cycle(self.store, self.plan)
        profiles = self.queued("profile.character")
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[-1]["payload"]["name"], "Exploradora")
        self.assertEqual(profiles[-1]["base_revision"], 1)

    def test_carry_reading_is_explicit_and_preserves_old_version(self):
        self.service.read_page("aula", "1.0.0", 1, 4, True)
        self.service.read_page("aula", "1.0.0", 2, 4, True)
        self.assertEqual(self.service.reading_versions("aula"), {"1.0.0": [1, 2]})
        self.assertEqual(self.service.reading("aula", "2.0.0", 5)["read_pages"], [])
        marked = self.service.carry_reading("aula", "2.0.0", 5, [2, 7])
        self.assertEqual(marked, [2])
        self.assertEqual(self.service.reading("aula", "2.0.0", 5)["read_pages"], [2])
        self.assertEqual(self.service.reading("aula", "1.0.0", 4)["read_pages"], [1, 2])
        self.assertEqual(self.service.carry_reading("aula", "2.0.0", 5, [2]), [])


class RangeTests(unittest.TestCase):
    def test_ranges_round_trip_and_limits(self):
        self.assertEqual(page_ranges([1, 2, 3, 5, 7, 8]), "1-3, 5, 7-8")
        self.assertEqual(parse_ranges("1-3, 5; 7-8", 10), [1, 2, 3, 5, 7, 8])
        for bad in ("", "0-2", "3-1", "1-99", "a", "1-2-3"):
            with self.assertRaises(ValueError):
                parse_ranges(bad, 10)


class TokenStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "study-sync-login.json"

    def tearDown(self):
        self.folder.cleanup()

    def test_round_trip_never_stores_plain_text_on_windows(self):
        token_store.save(self.path, "refresh-token-de-teste")
        self.assertEqual(token_store.load(self.path), "refresh-token-de-teste")
        body = self.path.read_text()
        if sys.platform == "win32":
            self.assertNotIn("refresh-token-de-teste", body)
        else:
            self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        token_store.clear(self.path)
        self.assertIsNone(token_store.load(self.path))
        token_store.clear(self.path)

    def test_rejects_invalid_or_foreign_files(self):
        with self.assertRaises(ValueError):
            token_store.save(self.path, "")
        self.path.write_text("not json")
        self.assertIsNone(token_store.load(self.path))
        self.path.write_text(json.dumps({"v": 99, "token": "x"}))
        self.assertIsNone(token_store.load(self.path))


if __name__ == "__main__":
    unittest.main()
