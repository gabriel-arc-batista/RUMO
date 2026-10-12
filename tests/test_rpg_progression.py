"""Equipment rewards preserve real effort, old inventory and backup compatibility."""

import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from core import Store, SCHEMA, TABLES
from backups import validate_backup
from rpg_schema import CATALOG, RPG_SCHEMA
from training_schema import TRAINING_SCHEMA
from rpg_progression import GEAR
from journey_backend import RPGJourney


class EquipmentProgressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / "study.sqlite3")
        self.plan = self.store.save("plans", {"name": "Plano de teste"})
        self.subject = self.store.save(
            "subjects", {"plan_id": self.plan, "name": "Matemática", "color": "#D6B467"}
        )
        self.topic = self.store.save(
            "topics", {"subject_id": self.subject, "name": "Frações"}
        )
        self.rpg = self.store.rpg

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def study(self, context=None, **kw):
        values = dict(
            plan_id=self.plan,
            subject_id=self.subject,
            topic_id=self.topic,
            day=self.store.today().isoformat(),
            category="Teoria",
            target=1500,
            elapsed=600,
            correct=0,
            wrong=0,
            blank=0,
        )
        values.update(kw)
        return self.store.save_session(values, context=context)

    def owned(self):
        return {item["id"] for item in self.rpg.catalog(self.plan) if item["owned"]}

    def test_level_one_has_only_rags_and_old_weapon_and_restart_is_idempotent(self):
        self.assertEqual(self.owned(), {"rags", "rusty_sword"})
        hero = RPGJourney(self.store).character(self.plan)
        self.assertEqual((hero.level, hero.xp, hero.coins), (1, 0, 0))
        self.assertEqual(set(hero.equipped), {"rags", "rusty_sword"})
        self.rpg.sync()
        self.rpg.sync()
        path = self.store.path
        self.store.db.close()
        self.store = Store(path)
        self.rpg = self.store.rpg
        self.assertEqual(self.owned(), {"rags", "rusty_sword"})
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 0)

    def test_level_rewards_are_free_and_dont_auto_replace_player_equipment(self):
        self.study(elapsed=6000)
        self.assertTrue(
            {"travel_tunic", "training_sword", "walking_boots"} <= self.owned()
        )
        names = self.rpg.consume_equipment_rewards(self.plan)
        self.assertIn("Túnica de viagem", names)
        self.rpg.sync()
        self.assertEqual(self.rpg.consume_equipment_rewards(self.plan), [])
        before = self.rpg.profile(self.plan)
        self.rpg.buy(self.plan, "training_sword")
        self.rpg.equip(self.plan, "training_sword")
        self.assertEqual(
            self.rpg.equipment_action(self.plan, "training_sword"), "practice"
        )
        self.assertEqual(self.rpg.profile(self.plan)["xp"], before["xp"])
        self.assertEqual(self.rpg.profile(self.plan)["coins"], before["coins"])
        equipped = self.store.rows(
            "SELECT item_id FROM rpg_inventory WHERE equipped=1 AND slot='arma'"
        )
        self.assertEqual([r["item_id"] for r in equipped], ["training_sword"])
        self.assertEqual(before["xp"], 100)
        self.assertEqual(before["coins"], 10)

    def test_locked_reward_cannot_be_bought_even_with_coins_and_level(self):
        self.study(elapsed=180000)
        with self.assertRaises(ValueError):
            self.rpg.buy(self.plan, "plate_armor")
        with self.assertRaises(ValueError):
            self.rpg.equipment_action(self.plan, "sky_griffin")
        self.assertNotIn("plate_armor", self.owned())

    def test_guardian_uses_real_review_completion_not_accuracy(self):
        origin = self.study(elapsed=18000)
        for i in range(2):
            rid = self.store.save(
                "reviews",
                dict(
                    topic_id=self.topic,
                    origin_id=origin,
                    due=(self.store.today() - timedelta(days=i + 1)).isoformat(),
                    interval=i + 1,
                ),
            )
            self.study(
                category="Revisão",
                review_id=rid,
                correct=0,
                wrong=4,
                context={"recall": "Não lembrei"},
            )
        guardian = next(
            p for p in self.rpg.progression(self.plan) if p["id"] == "guardiao"
        )
        self.assertEqual((guardian["value"], guardian["rank"]), (2, 1))
        self.assertIn("leather_armor", self.owned())
        self.assertIn("memory_shield", self.owned())

    def test_parallel_paths_count_wrong_answers_and_distinct_recall_dates(self):
        self.study(elapsed=18000)
        second = self.store.save(
            "topics", dict(subject_id=self.subject, name="Geometria")
        )
        for i in range(3):
            self.study(
                topic_id=second,
                correct=0,
                wrong=5,
                day=(self.store.today() - timedelta(days=i * 4)).isoformat(),
                context={"recall": "Não lembrei"},
            )
        self.study(topic_id=second, context={"recall": "Parcial"})
        paths = {p["id"]: p for p in self.rpg.progression(self.plan)}
        self.assertEqual(paths["arcanista"]["value"], 3)
        self.assertEqual(paths["arcanista"]["rank"], 1)
        self.assertEqual(paths["duelista"]["rank"], 1)
        self.assertEqual(paths["cartografo"]["rank"], 1)
        self.assertTrue({"arcane_robe", "wood_staff", "explorer_coat"} <= self.owned())

    def test_mounts_use_nonconsecutive_days_and_survive_corrections(self):
        ids = []
        for i in range(7):
            ids.append(
                self.study(
                    elapsed=18000 if i == 0 else 60,
                    day=(self.store.today() - timedelta(days=i * 3)).isoformat(),
                )
            )
        self.assertIn("pack_mule", self.owned())
        self.assertNotIn(
            "trail_horse", self.owned()
        )  # level 3 is below the horse's level 5
        self.study(elapsed=42000)
        self.assertIn("trail_horse", self.owned())
        self.rpg.equip(self.plan, "trail_horse")
        for row in self.store.rows("SELECT id FROM sessions"):
            self.store.delete_session(row["id"])
        self.assertIn("trail_horse", self.owned())
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 0)
        self.assertEqual(self.rpg.equipment_action(self.plan, "trail_horse"), "route")

    def test_all_catalog_items_have_a_purpose_and_old_prices_are_preserved(self):
        self.assertEqual(len(CATALOG), 38)
        for key, item in CATALOG.items():
            self.assertTrue(item["purpose"], key)
            self.assertTrue(item["action"], key)
        self.assertEqual(CATALOG["backpack"]["price"], 5)
        self.assertEqual(CATALOG["explorador"]["price"], 10)
        self.assertEqual(CATALOG["lantern"]["slot"], "mão")

    def test_schema_four_migrates_constraint_and_preserves_equipment_and_backup(self):
        old = RPG_SCHEMA.replace(
            ",'roupa','cabeça','pés','arma','escudo','montaria'", ""
        ).replace("user_version=5", "user_version=4")
        path = self.root / "old4.sqlite3"
        db = sqlite3.connect(path)
        db.executescript(SCHEMA.replace(RPG_SCHEMA, old).replace(TRAINING_SCHEMA, ""))
        db.execute("INSERT INTO plans(id,name) VALUES('p','Antigo')")
        db.execute(
            "INSERT INTO rpg_inventory VALUES('p','backpack','costas',5,1,'2026-01-01')"
        )
        db.commit()
        db.close()
        upgraded = Store(path)
        try:
            self.assertEqual(
                upgraded.db.execute("PRAGMA user_version").fetchone()[0], 6
            )
            self.assertEqual(
                upgraded.one(
                    "SELECT equipped FROM rpg_inventory WHERE item_id='backpack'"
                )["equipped"],
                1,
            )
            self.assertEqual(upgraded.rpg.profile("p")["xp"], 0)
            self.assertEqual(upgraded.rpg.profile("p")["correction_credit"], 5)
            self.assertTrue(list(self.root.glob("pre-equipment-*.sqlite3")))
            upgraded.rpg.equip("p", "rusty_sword")
            self.assertFalse(upgraded.db.execute("pragma foreign_key_check").fetchall())
        finally:
            upgraded.db.close()

    def test_v4_json_and_v5_backup_preserve_actual_rewards_and_new_slots(self):
        self.study(elapsed=6000)
        self.rpg.buy(self.plan, "backpack")
        self.rpg.equip(self.plan, "backpack")
        data = self.store.snapshot()
        data["version"] = 4
        data["tables"]["rpg_inventory"] = [
            r for r in data["tables"]["rpg_inventory"] if r["item_id"] not in GEAR
        ]
        path = self.root / "v4.json"
        path.write_text(json.dumps(data))
        normalized = validate_backup(path, SCHEMA, TABLES)
        self.assertEqual(normalized["version"], 6)
        self.store.restore(path)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 100)
        self.assertIn("training_sword", self.owned())
        self.rpg.equip(self.plan, "training_sword")
        current = self.store.snapshot()
        path.write_text(json.dumps(current))
        self.store.restore(path)
        self.assertEqual(
            self.rpg.equipment_action(self.plan, "training_sword"), "practice"
        )
        forged = copy.deepcopy(current)
        next(
            r
            for r in forged["tables"]["rpg_inventory"]
            if r["item_id"] == "training_sword"
        )["price"] = 99
        path.write_text(json.dumps(forged))
        with self.assertRaises(ValueError):
            self.store.restore(path)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 100)

    def test_old_unenrolled_studies_dont_unlock_classes_or_equipment(self):
        sid = self.study(elapsed=6000, wrong=100)
        with self.store.db:
            self.store.db.execute("DELETE FROM rpg_sources")
            self.store.db.execute("DELETE FROM rpg_inventory")
        self.rpg.sync()
        self.assertEqual(self.owned(), {"rags", "rusty_sword"})
        self.assertEqual(
            next(p for p in self.rpg.progression(self.plan) if p["id"] == "duelista")[
                "value"
            ],
            0,
        )
        self.rpg.enroll_history(self.plan, [sid])
        self.assertIn("travel_tunic", self.owned())

    def test_ladino_requires_enrolled_practice_and_counts_each_difficulty_once(self):
        self.study(elapsed=18000)
        difficulty = self.rpg.save_difficulty(
            self.plan,
            self.topic,
            "Erro de sinal",
            "Esqueci a regra",
            "Conferir o sinal",
        )
        get = lambda: next(
            p for p in self.rpg.progression(self.plan) if p["id"] == "ladino"
        )
        self.assertEqual(get()["value"], 0)
        first = self.study(context={"difficulty_id": difficulty})
        second = self.study(context={"difficulty_id": difficulty})
        self.assertEqual((get()["value"], get()["rank"]), (1, 1))
        self.assertIn("rogue_cloak", self.owned())
        self.rpg.equip(self.plan, "rogue_cloak")
        self.assertEqual(self.rpg.equipment_action(self.plan, "rogue_cloak"), "revenge")
        self.store.delete_session(first)
        self.store.delete_session(second)
        self.assertEqual(get()["value"], 0)
        self.assertIn("rogue_cloak", self.owned())

    def test_erudito_requires_study_and_real_notes_without_extra_xp(self):
        self.store.save("topics", dict(id=self.topic, notes="Minha explicação"))
        get = lambda: next(
            p for p in self.rpg.progression(self.plan) if p["id"] == "erudito"
        )
        self.assertEqual(get()["value"], 0)
        self.study(elapsed=18000)
        self.assertEqual(get()["value"], 1)
        other = self.store.save(
            "topics", dict(subject_id=self.subject, name="Geometria")
        )
        sid = self.study(topic_id=other, notes=" \t\n\r ")
        self.assertEqual(get()["value"], 1)
        before = self.rpg.profile(self.plan)["xp"]
        self.store.save(
            "topics", dict(id=other, notes="Exemplo explicado com minhas palavras")
        )
        self.assertEqual((get()["value"], get()["rank"]), (2, 1))
        self.assertIn("scholar_book", self.owned())
        self.rpg.equip(self.plan, "scholar_book")
        self.assertEqual(self.rpg.equipment_action(self.plan, "scholar_book"), "notes")
        self.assertEqual(self.rpg.profile(self.plan)["xp"], before)
        self.study(topic_id=other, notes="Outro exemplo")
        self.assertEqual(get()["value"], 2)
        with self.store.db:
            self.store.db.execute("DELETE FROM rpg_sources WHERE session_id=?", (sid,))
        self.rpg.sync()
        self.assertEqual(
            get()["value"], 2
        )  # another enrolled study exists in that topic

    def test_all_six_paths_are_typed_independent_and_old_paladin_id_is_preserved(self):
        rows = RPGJourney(self.store).progression(self.plan)
        self.assertEqual(
            {r.name for r in rows},
            {"Paladino", "Guerreiro", "Mago", "Cartógrafo", "Ladino", "Erudito"},
        )
        self.assertEqual(next(r for r in rows if r.name == "Paladino").id, "guardiao")
        self.assertTrue(all(r.value == 0 and r.rank == "Iniciante" for r in rows))
