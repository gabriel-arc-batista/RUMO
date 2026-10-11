import json
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Store, Clock, ratio, parse_duration, duration, SCHEMA


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.sqlite3")
        self.p = self.store.save("plans", {"name": "BACEN"})
        self.s = self.store.save(
            "subjects",
            {"name": "Banco de dados", "plan_id": self.p, "color": "#5B8CFF"},
        )
        self.t = self.store.save(
            "topics", {"name": "Normalização", "subject_id": self.s}
        )

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def session(self, **kwargs):
        return dict(
            {
                "plan_id": self.p,
                "subject_id": self.s,
                "topic_id": self.t,
                "day": date.today().isoformat(),
                "category": "Teoria",
                "target": 3600,
                "elapsed": 2700,
                "correct": 15,
                "wrong": 5,
                "blank": 0,
            },
            **kwargs,
        )

    def cycle(self):
        cid = self.store.save("cycles", {"plan_id": self.p, "name": "ABC"})
        ids = []
        for i, target in enumerate([3600, 2700, 1800]):
            sid = (
                self.s
                if i == 0
                else self.store.save(
                    "subjects",
                    {"plan_id": self.p, "name": chr(65 + i), "color": "#9B7BFF"},
                )
            )
            ids.append(
                self.store.save(
                    "blocks",
                    {"cycle_id": cid, "subject_id": sid, "target": target, "sort": i},
                )
            )
        return self.store.current_cycle(self.p), ids

    def test_persistence_and_edit_delete(self):
        sid = self.store.save_session(self.session())
        self.assertEqual(self.store.stats(self.p)["rate"], 75)
        self.store.db.close()
        self.store = Store(Path(self.tmp.name) / "test.sqlite3")
        self.assertEqual(self.store.stats(self.p)["elapsed"], 2700)
        self.store.save_session(self.session(id=sid, correct=16, wrong=4))
        self.assertEqual(self.store.stats(self.p)["rate"], 80)
        self.store.delete_session(sid)
        self.assertEqual(self.store.stats(self.p)["elapsed"], 0)

    def test_theory_no_questions(self):
        self.store.save_session(self.session(correct=0, wrong=0))
        self.assertIsNone(self.store.stats(self.p)["rate"])

    def test_negative_and_total_rejected(self):
        for changes in [
            {"elapsed": -1},
            {"correct": -1},
            {"wrong": 1.5},
            {"total": 19},
            {"pages": -1},
            {"category": "invalid"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.store.save_session(self.session(**changes))
        self.assertEqual(self.store.stats(self.p)["count"], 0)

    def test_weighted_ratio(self):
        self.store.save_session(self.session(correct=9, wrong=1))
        self.store.save_session(self.session(correct=1, wrong=99))
        self.assertAlmostEqual(self.store.stats(self.p)["rate"], 1000 / 110)

    def test_cycle_partial_excess_and_explicit_decisions(self):
        cycle, blocks = self.cycle()
        ids = [
            self.store.save_session(
                self.session(elapsed=x * 60, block_id=blocks[0], lap=1)
            )
            for x in [25, 20, 15]
        ]
        self.assertEqual(self.store.cycle_blocks(cycle)[0]["elapsed"], 3600)
        self.assertEqual(self.store.current_cycle(self.p)["position"], 0)
        self.store.decide(cycle, blocks[0], "Concluído")
        self.assertEqual(self.store.current_cycle(self.p)["position"], 1)
        self.assertEqual(
            self.store.one("SELECT done FROM topics WHERE id=?", (self.t,))["done"], 0
        )
        self.store.save_session(
            self.session(id=ids[-1], elapsed=25 * 60, block_id=blocks[0], lap=1)
        )
        blocks_data = self.store.cycle_blocks(cycle)
        self.assertEqual(blocks_data[0]["elapsed"], 4200)
        self.assertEqual(blocks_data[1]["elapsed"], 0)
        self.store.decide(cycle, blocks[1], "Adiado", "retomar depois")
        self.assertEqual(self.store.cycle_blocks(cycle)[1]["elapsed"], 0)
        self.store.delete_session(ids[0])
        self.assertEqual(self.store.current_cycle(self.p)["position"], 2)

    def test_cycle_incompatible_subject(self):
        c, blocks = self.cycle()
        with self.assertRaises(ValueError):
            self.store.save_session(self.session(block_id=blocks[1], lap=1))

    def test_review_series_and_completion(self):
        sid = self.store.save_session(self.session(), [1, 7, 30, 60, 120], True)
        self.store.save_session(self.session(), [1, 7, 30, 60, 120])
        reviews = self.store.rows("SELECT * FROM reviews ORDER BY interval")
        self.assertEqual(len(reviews), 5)
        self.assertEqual(
            reviews[0]["due"], (date.today() + timedelta(days=1)).isoformat()
        )
        done = self.store.save_session(
            self.session(category="Revisão", review_id=reviews[0]["id"])
        )
        self.assertEqual(
            self.store.one("SELECT state FROM reviews WHERE id=?", (reviews[0]["id"],))[
                "state"
            ],
            "Concluída",
        )
        self.store.delete_session(done)
        self.assertEqual(
            self.store.one("SELECT state FROM reviews WHERE id=?", (reviews[0]["id"],))[
                "state"
            ],
            "Pendente",
        )

    def test_mock_single_count_and_distribution(self):
        r = {"subject_id": self.s, "correct": 70, "wrong": 20, "blank": 10, "weight": 1}
        sid = self.store.save_session(
            self.session(
                category="Simulado",
                correct=70,
                wrong=20,
                blank=10,
                mock_name="Teste",
                score_correct=1,
                score_wrong=1,
                score_blank=0,
            ),
            results=[r],
        )
        stats = self.store.stats(self.p)
        self.assertEqual(stats["total"], 100)
        self.assertEqual(stats["elapsed"], 2700)
        self.assertEqual(stats["presented_rate"], 70)
        self.assertAlmostEqual(stats["rate"], 70 / 90 * 100)
        by_subject = self.store.subject_stats(self.p)[0]
        self.assertEqual(by_subject["correct"], 70)
        from app import App

        app = object.__new__(App)
        app.store = self.store
        self.assertEqual(
            app.mock_score(self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))),
            50,
        )

    def test_mock_invalid_results_atomic(self):
        with self.assertRaises(ValueError):
            self.store.save_session(
                self.session(category="Simulado"),
                results=[{"subject_id": self.s, "correct": 14, "wrong": 5, "blank": 0}],
            )
        self.assertEqual(self.store.stats(self.p)["count"], 0)

    def test_parent_progress_leaves_only(self):
        child = self.store.save(
            "topics",
            {"subject_id": self.s, "parent_id": self.t, "name": "3FN", "done": 1},
        )
        self.assertEqual(self.store.progress(self.p), {"total": 1, "done": 1})
        self.store.save("topics", {"id": child, "done": 0})
        self.assertEqual(self.store.progress(self.p)["done"], 0)

    def test_plan_isolation_and_filters(self):
        self.store.save_session(self.session())
        other = self.store.save("plans", {"name": "Outro"})
        self.assertEqual(self.store.stats(other)["elapsed"], 0)
        self.assertEqual(self.store.stats(self.p, {"category": "Questões"})["count"], 0)
        self.assertEqual(
            self.store.stats(self.p, {"subject_id": self.s, "topic_id": self.t})[
                "count"
            ],
            1,
        )
        with self.assertRaises(ValueError):
            self.store.save_session(self.session(plan_id=other))

    def test_midnight_segments_and_manual_questions(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        self.store.save_session(
            self.session(
                day=yesterday.isoformat(),
                elapsed=2700,
                segments=json.dumps(
                    [
                        {"day": yesterday.isoformat(), "seconds": 900},
                        {"day": today.isoformat(), "seconds": 1800},
                    ]
                ),
            )
        )
        now = self.store.stats(
            self.p, {"from": today.isoformat(), "to": today.isoformat()}
        )
        self.assertEqual(now["elapsed"], 1800)
        self.assertEqual(now["total"], 0)
        rows = self.store.grouped(self.p)
        self.assertEqual([r["elapsed"] for r in rows], [900, 1800])
        self.assertEqual(rows[0]["correct"], 15)
        self.assertEqual(rows[1]["correct"], 0)

    def test_backup_restore_and_invalid_preserves_data(self):
        cycle, blocks = self.cycle()
        self.store.save_session(self.session(block_id=blocks[0], lap=1), [1, 7], True)
        self.store.set_pref("theme", "Claro")
        backup = Path(self.tmp.name) / "backup.json"
        self.store.export(backup)
        self.store.save_session(self.session())
        self.assertEqual(self.store.stats(self.p)["count"], 2)
        self.store.restore(backup)
        self.assertEqual(self.store.stats(self.p)["count"], 1)
        self.assertEqual(self.store.pref("theme"), "Claro")
        self.assertEqual(len(self.store.rows("SELECT * FROM reviews")), 2)
        data = json.loads(backup.read_text(encoding="utf-8"))
        data["tables"]["sessions"][0]["elapsed"] = -1
        backup.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises((ValueError, sqlite3.Error)):
            self.store.restore(backup)
        self.assertEqual(self.store.stats(self.p)["elapsed"], 2700)

    def test_backup_foreign_key_rejected(self):
        self.store.save_session(self.session())
        path = Path(self.tmp.name) / "bad.json"
        self.store.export(path)
        data = json.loads(path.read_text())
        data["tables"]["sessions"][0]["plan_id"] = "missing"
        path.write_text(json.dumps(data))
        with self.assertRaises((ValueError, sqlite3.Error)):
            self.store.restore(path)
        self.assertEqual(self.store.stats(self.p)["count"], 1)

    def test_consistent_sqlite_backup(self):
        self.store.save_session(self.session())
        path = self.store.auto_backup(True)
        c = sqlite3.connect(path)
        try:
            self.assertEqual(
                c.execute("SELECT SUM(elapsed) FROM sessions").fetchone()[0], 2700
            )
        finally:
            c.close()

    def test_import_three_levels_and_duplicate(self):
        rows = [
            {"materia": "A", "assunto": "Pai"},
            {"materia": "A", "pai": "Pai", "assunto": "Filho"},
            {"materia": "A", "pai": "Filho", "assunto": "Neto"},
        ]
        self.store.import_topics(self.p, rows)
        self.store.import_topics(self.p, rows)
        topics = self.store.rows(
            "SELECT * FROM topics WHERE subject_id IN(SELECT id FROM subjects WHERE name='A')"
        )
        self.assertEqual(len(topics), 3)
        self.assertIsNotNone(topics[-1]["parent_id"])

    def test_clock_pause_recovery_suspend_and_expiration(self):
        now = [0]
        clock = Clock(self.store, lambda: now[0])
        clock.start(self.session(target=30), "Timer")
        now[0] = 5
        clock.tick()
        self.assertEqual(clock.state["elapsed"], 5)
        clock.pause()
        now[0] = 305
        clock.tick()
        self.assertEqual(clock.state["elapsed"], 5)
        clock.resume()
        now[0] = 310
        clock.tick()
        self.assertEqual(clock.state["elapsed"], 10)
        recovered = Clock(self.store, lambda: now[0])
        self.assertFalse(recovered.state["running"])
        self.assertEqual(recovered.state["elapsed"], 10)
        recovered.resume()
        now[0] = 1000
        recovered.tick()
        self.assertFalse(recovered.state["running"])
        self.assertEqual(recovered.state["elapsed"], 10)
        recovered.add(1)
        self.assertEqual(recovered.state["target"], 90)
        recovered.state["target"] = 15
        recovered.resume()
        now[0] = 1005
        self.assertTrue(recovered.tick())
        self.assertEqual(recovered.state["elapsed"], 15)
        self.assertEqual(self.store.stats(self.p)["count"], 0)

    def test_clock_finalize_idempotence(self):
        clock = Clock(self.store)
        clock.start(self.session())
        clock.pause()
        token = clock.state["id"]
        self.store.save_session(self.session(id=token), finish_active=True)
        self.store.save_session(self.session(id=token), finish_active=True)
        self.assertEqual(self.store.stats(self.p)["count"], 1)
        self.assertIsNone(self.store.one("SELECT * FROM active"))

    def test_duration(self):
        self.assertEqual(parse_duration("01:02:03"), 3723)
        self.assertEqual(duration(3723), "01:02:03")
        for value in ["-1:00:00", "00:60:00", "5", "1:1:1:1"]:
            with self.assertRaises(ValueError):
                parse_duration(value)

    def test_bacen_dataset_and_import(self):
        assets = Path(__file__).resolve().parents[1] / "assets"
        data = json.loads((assets / "bacen2024.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["areas"]), 2)
        self.store.import_topics(self.p, data["areas"]["Tecnologia da Informação"])
        self.assertEqual(len(self.store.rows("SELECT id FROM topics")), 131)
        self.assertGreater(self.store.progress(self.p)["total"], 90)

    def test_generation_weights(self):
        self.store.save(
            "subjects",
            {"plan_id": self.p, "name": "Prioritária", "color": "#9B7BFF", "weight": 3},
        )
        rows = self.store.generate_cycle(self.p, 30, 240)
        self.assertEqual(len(rows), 8)
        self.assertGreater(
            sum(r["subject"] == "Prioritária" for r in rows),
            sum(r["subject"] == "Banco de dados" for r in rows),
        )

    def test_reorder_preserves_active_block(self):
        cycle, blocks = self.cycle()
        self.store.reorder_cycle(cycle, list(reversed(blocks)))
        current = self.store.current_cycle(self.p)
        self.assertEqual(current["position"], 2)
        self.assertEqual(
            self.store.cycle_blocks(current)[current["position"]]["id"], blocks[0]
        )

    def test_mock_filter_uses_actual_distribution(self):
        other = self.store.save(
            "subjects", {"plan_id": self.p, "name": "Outra", "color": "#9B7BFF"}
        )
        results = [
            {"subject_id": self.s, "correct": 7, "wrong": 2, "blank": 1},
            {"subject_id": other, "correct": 63, "wrong": 18, "blank": 9},
        ]
        self.store.save_session(
            self.session(
                category="Simulado",
                subject_id=None,
                topic_id=None,
                correct=70,
                wrong=20,
                blank=10,
            ),
            results=results,
        )
        selected = self.store.stats(self.p, {"subject_id": self.s})
        self.assertEqual(selected["total"], 10)
        self.assertEqual(selected["elapsed"], 0)
        grouped = self.store.grouped(self.p, group="subject")
        self.assertEqual(sum(r["correct"] for r in grouped), 70)
        self.assertEqual(sum(r["elapsed"] for r in grouped), 2700)
        self.assertEqual(self.store.stats(self.p)["total"], 100)

    def test_sqlite_restore_supported(self):
        self.store.save_session(self.session())
        path = self.store.auto_backup(True)
        self.store.save_session(self.session())
        self.store.restore(path)
        self.assertEqual(self.store.stats(self.p)["count"], 1)

    def test_pending_review_date_policy(self):
        sid = self.store.save_session(self.session(), [1, 7])
        old = self.store.rows("SELECT * FROM reviews ORDER BY interval")
        changed = (date.today() - timedelta(days=2)).isoformat()
        self.store.save_session(self.session(id=sid, day=changed), shift_pending=False)
        self.assertEqual(
            self.store.rows("SELECT * FROM reviews ORDER BY interval")[0]["due"],
            old[0]["due"],
        )
        self.store.save_session(self.session(id=sid, day=date.today().isoformat()))
        self.assertEqual(
            self.store.rows("SELECT * FROM reviews ORDER BY interval")[0]["due"],
            (date.fromisoformat(old[0]["due"]) + timedelta(days=2)).isoformat(),
        )

    def test_future_database_migration_protected(self):
        path = Path(self.tmp.name) / "future.sqlite3"
        c = sqlite3.connect(path)
        c.execute("PRAGMA user_version=99")
        c.close()
        with self.assertRaises(ValueError):
            Store(path)
        c = sqlite3.connect(path)
        try:
            self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 99)
        finally:
            c.close()

    def test_timezone_and_invalid_segments(self):
        self.store.set_pref("timezone", "America/Fortaleza")
        clock = Clock(self.store)
        self.assertEqual(clock.local_now().utcoffset(), timedelta(hours=-3))
        with self.assertRaises(ValueError):
            self.store.save_session(self.session(segments="not JSON"))

    def test_schema_one_migration_preserves_data(self):
        path = Path(self.tmp.name) / "old.sqlite3"
        c = sqlite3.connect(path)
        old_schema = (
            SCHEMA.replace(
                "ALTER TABLE sessions ADD COLUMN pauses TEXT NOT NULL DEFAULT '[]';", ""
            )
            .replace("user_version=3", "user_version=1")
            .replace(",notes TEXT NOT NULL DEFAULT ''", "")
        )
        c.executescript(old_schema)
        c.execute("INSERT INTO plans(id,name) VALUES('p','Preservado')")
        c.commit()
        c.close()
        upgraded = Store(path)
        try:
            self.assertEqual(
                upgraded.one("SELECT name FROM plans")["name"], "Preservado"
            )
            self.assertEqual(
                upgraded.db.execute("PRAGMA user_version").fetchone()[0], 3
            )
            self.assertIn(
                "pauses",
                [r[1] for r in upgraded.db.execute("PRAGMA table_info(sessions)")],
            )
        finally:
            upgraded.db.close()

    def test_backup_invalid_preferences_and_active_relations(self):
        path = Path(self.tmp.name) / "bad-pref.json"
        self.store.set_pref("retention", 7)
        self.store.export(path)
        data = json.loads(path.read_text())
        data["tables"]["preferences"][0]["value"] = "-1"
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.store.restore(path)
        self.assertEqual(self.store.pref("retention"), 7)


if __name__ == "__main__":
    unittest.main()
