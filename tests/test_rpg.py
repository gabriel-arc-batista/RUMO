import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from core import Clock, SCHEMA, TABLES, Store
from rpg_schema import RPG_SCHEMA, RPG_TABLES
from rpg import level_for


class RPGTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "estudos.sqlite3")
        self.plan = self.store.save("plans", {"name": "Meu estudo real"})
        self.subject = self.store.save(
            "subjects", {"plan_id": self.plan, "name": "Matemática", "color": "#D6B467"}
        )
        self.topic = self.store.save(
            "topics", {"subject_id": self.subject, "name": "Frações"}
        )
        self.rpg = self.store.rpg

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def fields(self, **overrides):
        result = dict(
            plan_id=self.plan,
            subject_id=self.subject,
            topic_id=self.topic,
            day=self.store.today().isoformat(),
            category="Teoria",
            target=1500,
            elapsed=300,
            correct=0,
            wrong=0,
            blank=0,
        )
        result.update(overrides)
        return result

    def session(self, context=None, **overrides):
        return self.store.save_session(self.fields(**overrides), context=context)

    def cycle(self):
        cycle = self.store.save(
            "cycles", {"plan_id": self.plan, "name": "Ciclo", "active": 1}
        )
        block = self.store.save(
            "blocks",
            {
                "cycle_id": cycle,
                "subject_id": self.subject,
                "topic_id": self.topic,
                "target": 1500,
                "sort": 0,
            },
        )
        return self.store.current_cycle(self.plan), block

    def test_empty_profile_and_deterministic_level_boundaries(self):
        profile = self.rpg.profile(self.plan)
        self.assertEqual((profile["xp"], profile["level"], profile["coins"]), (0, 1, 0))
        self.assertEqual(profile["skills"][0]["evidence_label"], "Dados insuficientes")
        self.assertEqual(
            [level_for(x) for x in [0, 99, 100, 299, 300, 600]], [1, 1, 2, 2, 3, 4]
        )
        self.assertFalse(any(r["unlocked"] for r in self.rpg.story(self.plan)))

    def test_time_xp_not_correctness_or_question_volume_and_restart_idempotent(self):
        sid = self.session(elapsed=125, correct=0, wrong=100)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 2)
        self.assertEqual(self.rpg.profile(self.plan)["skills"][0]["xp"], 2)
        self.store.save_session(self.fields(id=sid, elapsed=125, correct=1000, wrong=0))
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 2)
        self.store.db.close()
        self.store = Store(self.root / "estudos.sqlite3")
        self.rpg = self.store.rpg
        self.rpg.sync()
        self.rpg.sync()
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 2)
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM rpg_rewards")["n"], 1)
        self.assertIn("125", self.rpg.reward_details(sid)[0]["explanation"])

    def test_partial_mission_hard_day_pause_and_clock_recovery_keep_cycle(self):
        cycle, block = self.cycle()
        mission = self.rpg.recommended_mission(self.plan)
        self.rpg.small_mission(mission["id"], 5)
        initial = self.rpg.mission_fields(mission["id"])
        self.assertEqual(initial["target"], 300)
        current = [0.0]
        clock = Clock(self.store, lambda: current[0])
        fields = self.fields(block_id=block, lap=1)
        clock.start(dict(fields, mission_id=mission["id"]), "Timer")
        for _ in range(30):
            current[0] += 5
            clock.tick()
        clock.pause()
        current[0] += 600
        clock.tick()
        self.assertEqual(clock.state["elapsed"], 150)
        resumed = Clock(self.store, lambda: current[0])
        self.assertFalse(resumed.state["running"])
        self.assertEqual(resumed.state["mission_id"], mission["id"])
        resumed.resume()
        for _ in range(30):
            current[0] += 5
            resumed.tick()
        sid = self.session(
            context={"mission_id": mission["id"]},
            block_id=block,
            lap=1,
            elapsed=300,
            next_step="Praticar divisão",
        )
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 5)
        progress = self.rpg.mission(mission["id"])
        self.assertFalse(progress["completed"])
        self.assertEqual(
            (progress["elapsed"], progress["remaining"], progress["next_step"]),
            (300, 1200, "Praticar divisão"),
        )
        self.assertEqual(self.store.current_cycle(self.plan)["position"], 0)
        self.assertEqual(self.store.current_cycle(self.plan)["lap"], 1)
        self.assertIsNone(self.store.one("SELECT * FROM decisions"))
        self.assertEqual(self.rpg.recommended_mission(self.plan)["id"], mission["id"])
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 1)
        self.rpg.continue_mission(mission["id"])
        self.assertEqual(self.rpg.mission_fields(mission["id"])["target"], 1200)
        self.store.delete_session(sid)
        self.assertEqual(self.rpg.mission(mission["id"])["elapsed"], 0)

    def test_complete_mission_never_creates_another_study_or_decides_block(self):
        cycle, block = self.cycle()
        mission = self.rpg.recommended_mission(self.plan)
        self.session(
            context={"mission_id": mission["id"]}, block_id=block, lap=1, elapsed=1500
        )
        self.assertTrue(self.rpg.mission(mission["id"])["completed"])
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 1)
        self.assertIsNone(self.store.one("SELECT * FROM decisions"))
        with self.assertRaises(ValueError):
            self.rpg.mission_fields(mission["id"])

    def test_edits_and_deletes_recompute_xp_without_removing_purchases(self):
        sid = self.session(elapsed=6000)
        self.rpg.buy(self.plan, "livro")
        self.rpg.buy(self.plan, "livro")
        self.rpg.equip(self.plan, "livro")
        self.assertEqual(self.rpg.profile(self.plan)["coins"], 5)
        self.store.save_session(self.fields(id=sid, elapsed=60))
        profile = self.rpg.profile(self.plan)
        self.assertEqual(
            (profile["xp"], profile["coins"], profile["correction_credit"]), (1, 0, 5)
        )
        self.assertTrue(
            next(r for r in self.rpg.catalog(self.plan) if r["id"] == "livro")[
                "equipped"
            ]
        )
        with self.assertRaises(ValueError):
            self.rpg.buy(self.plan, "bussola")
        self.store.delete_session(sid)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 0)
        self.assertEqual(
            self.store.one("SELECT COUNT(*) n FROM rpg_inventory WHERE price>0")["n"], 1
        )
        self.session(elapsed=6000)
        self.assertEqual(self.rpg.profile(self.plan)["coins"], 5)

    def test_equipment_is_decorative_and_one_per_slot(self):
        self.session(elapsed=12000)
        before = self.rpg.profile(self.plan)["xp"]
        self.rpg.buy(self.plan, "viajante")
        self.rpg.buy(self.plan, "explorador")
        self.rpg.equip(self.plan, "viajante")
        self.rpg.equip(self.plan, "explorador")
        self.assertEqual(
            self.store.one(
                "SELECT COUNT(*) n FROM rpg_inventory WHERE equipped=1 AND slot='Título'"
            )["n"],
            1,
        )
        self.assertEqual(self.rpg.profile(self.plan)["xp"], before)

    def test_late_review_reward_and_reopen_are_non_punitive_and_not_duplicated(self):
        origin = self.session()
        rid = self.store.save(
            "reviews",
            {
                "topic_id": self.topic,
                "origin_id": origin,
                "due": "2020-01-01",
                "interval": 7,
            },
        )
        fields = self.rpg.review_fields(rid)
        self.session(
            context={"mission_id": fields["mission_id"], "recall": "Não lembrei"},
            elapsed=600,
            category="Revisão",
            review_id=rid,
        )
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 20)
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM reviews")["n"], 1)
        self.store.save("reviews", {"id": rid, "state": "Concluída"})
        self.rpg.sync()
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 20)
        self.store.save("reviews", {"id": rid, "state": "Pendente"})
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 15)
        self.store.save("reviews", {"id": rid, "state": "Concluída"})
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 20)

    def test_errors_are_manual_and_separated_encounters_only_suggest_overcoming(self):
        sid = self.session(wrong=100)
        self.assertEqual(self.rpg.difficulties(self.plan), [])
        did = self.rpg.save_difficulty(
            self.plan,
            self.topic,
            "Troquei numerador",
            "Li rápido",
            "Identificar o todo",
            session_id=sid,
        )
        mission = self.rpg.revenge_mission(did)
        self.assertEqual(self.rpg.revenge_mission(did)["id"], mission["id"])
        for delta in (8, 4, 0):
            self.session(
                context={"difficulty_id": did, "recall": "Lembrei"},
                day=(self.store.today() - timedelta(days=delta)).isoformat(),
                elapsed=300,
                category="Revisão",
                correct=0,
                wrong=0,
            )
        evidence = self.rpg.difficulty_evidence(did)
        self.assertTrue(evidence["suggest_overcome"])
        self.assertEqual(self.rpg.difficulties(self.plan)[0]["state"], "Em prática")
        self.rpg.set_difficulty_state(did, "Superada pelo usuário")
        self.assertEqual(
            self.rpg.difficulties(self.plan)[0]["state"], "Superada pelo usuário"
        )
        self.assertIsNone(self.rpg.profile(self.plan)["skills"][0]["performance"])

    def test_immediate_repetitions_do_not_suggest_mastery(self):
        did = self.rpg.save_difficulty(
            self.plan, self.topic, "Erro", "Motivo", "Lembrança"
        )
        for _ in range(4):
            self.session(
                context={"difficulty_id": did, "recall": "Lembrei"},
                elapsed=60,
                correct=10,
            )
        self.assertFalse(self.rpg.difficulty_evidence(did)["suggest_overcome"])

    def test_performance_needs_questions_on_separate_days_not_time_or_self_rating(self):
        for delta in (8, 4, 0):
            self.session(
                context={"recall": "Lembrei"},
                day=(self.store.today() - timedelta(days=delta)).isoformat(),
                elapsed=3600,
                correct=0,
            )
        self.assertIsNone(self.rpg.profile(self.plan)["skills"][0]["performance"])
        for delta in (8, 4, 0):
            self.session(
                day=(self.store.today() - timedelta(days=delta)).isoformat(),
                elapsed=60,
                correct=7,
                wrong=3,
            )
        skill = self.rpg.profile(self.plan)["skills"][0]
        self.assertEqual(skill["performance"], 70)
        self.assertIn("não comprova", skill["evidence_label"])

    def test_challenge_only_studied_topics_and_boss_has_single_canonical_mock(self):
        with self.assertRaises(ValueError):
            self.rpg.create_challenge(self.plan, "Teste", [self.topic])
        self.session()
        cid = self.rpg.create_challenge(
            self.plan,
            "Chefe",
            [self.topic],
            questions=10,
            time_limit=300,
            kind="Chefe",
            source="Livro, prova 1",
        )
        initial = self.rpg.challenge_fields(cid)
        self.assertEqual(initial["category"], "Simulado")
        sid = self.store.save_session(
            self.fields(
                subject_id=None,
                topic_id=None,
                category="Simulado",
                elapsed=600,
                correct=6,
                wrong=3,
                blank=1,
                mock_name="Chefe",
            ),
            results=[dict(subject_id=self.subject, correct=6, wrong=3, blank=1)],
            context={"challenge_id": cid},
        )
        progress = self.rpg.challenge(cid)
        self.assertTrue(progress["completed"])
        self.assertTrue(progress["time_exceeded"])
        self.assertEqual(self.store.stats(self.plan)["elapsed"], 900)
        self.assertEqual(self.store.stats(self.plan)["total"], 10)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 20)
        self.assertEqual(self.rpg.profile(self.plan)["skills"][0]["xp"], 5)
        self.rpg.attach_session(sid, {"challenge_id": cid})
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 20)
        self.store.delete_session(sid)
        self.assertFalse(self.rpg.challenge(cid)["completed"])
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 5)

    def test_dungeon_topics_are_validated_and_linking_does_not_duplicate_time(self):
        self.session()
        cid = self.rpg.create_challenge(self.plan, "Prática", [self.topic], questions=8)
        sid = self.session(
            context={"challenge_id": cid},
            category="Questões",
            elapsed=600,
            correct=0,
            wrong=8,
        )
        self.assertEqual(self.rpg.challenge(cid)["total"], 8)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 20)
        self.assertEqual(self.store.stats(self.plan)["count"], 2)
        self.store.save_session(
            self.fields(id=sid, category="Questões", elapsed=120, wrong=2)
        )
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 7)
        self.assertFalse(self.rpg.challenge(cid)["completed"])

    def test_invalid_context_rolls_back_entire_study(self):
        cycle, block = self.cycle()
        mission = self.rpg.recommended_mission(self.plan)
        with self.assertRaises(ValueError):
            self.session(context={"mission_id": mission["id"]}, block_id=block, lap=2)
        self.assertEqual(self.store.stats(self.plan)["count"], 0)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 0)

    def test_subject_correction_detaches_invalid_mission_but_keeps_study(self):
        cycle, block = self.cycle()
        mission = self.rpg.recommended_mission(self.plan)
        sid = self.session(context={"mission_id": mission["id"]}, block_id=block, lap=1)
        other = self.store.save(
            "subjects", {"plan_id": self.plan, "name": "Português", "color": "#D6B467"}
        )
        topic = self.store.save("topics", {"subject_id": other, "name": "Verbos"})
        self.store.save_session(
            self.fields(
                id=sid,
                subject_id=other,
                topic_id=topic,
                block_id=None,
                lap=None,
                elapsed=600,
            )
        )
        self.assertEqual(self.rpg.mission(mission["id"])["elapsed"], 0)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 10)
        self.assertEqual(self.rpg.profile(self.plan)["skills"][1]["xp"], 10)
        path = self.root / "edited.json"
        self.store.export(path)
        self.store.validate_backup(path)

    def test_story_uses_useful_milestones_without_a_streak(self):
        cycle, block = self.cycle()
        sid = self.session(block_id=block, lap=1, elapsed=1500, day="2020-01-01")
        rid = self.store.save(
            "reviews",
            {
                "topic_id": self.topic,
                "origin_id": sid,
                "due": "2020-01-02",
                "interval": 1,
            },
        )
        self.session(category="Revisão", review_id=rid, day="2021-01-01")
        did = self.rpg.save_difficulty(
            self.plan,
            self.topic,
            "Dúvida",
            "Ainda confundo",
            "Comparar exemplos",
            session_id=sid,
        )
        self.session(context={"difficulty_id": did}, day="2022-01-01")
        self.store.decide(cycle, block, "Concluído")
        self.assertTrue(all(c["unlocked"] for c in self.rpg.story(self.plan)))
        self.store.delete_session(sid)
        self.assertTrue(all(c["unlocked"] for c in self.rpg.story(self.plan)))

    def test_full_rpg_backup_restore_preserves_inventory_links_and_no_double_rewards(
        self,
    ):
        sid = self.session(elapsed=6000)
        self.rpg.buy(self.plan, "livro")
        self.rpg.equip(self.plan, "livro")
        did = self.rpg.save_difficulty(
            self.plan, self.topic, "Erro", "Motivo", "Lembrança", session_id=sid
        )
        mission = self.rpg.revenge_mission(did)
        self.session(
            context={
                "mission_id": mission["id"],
                "difficulty_id": did,
                "recall": "Parcial",
            },
            review_id=mission["review_id"],
            category="Revisão",
            elapsed=120,
        )
        before = self.rpg.profile(self.plan)
        backup = self.root / "backup.json"
        self.store.export(backup)
        self.session(elapsed=600)
        self.store.restore(backup)
        self.assertEqual(self.rpg.profile(self.plan), before)
        self.rpg.sync()
        self.assertEqual(self.rpg.profile(self.plan), before)
        self.assertEqual(len(self.rpg.difficulties(self.plan)), 1)
        self.assertTrue(
            next(r for r in self.rpg.catalog(self.plan) if r["id"] == "livro")[
                "equipped"
            ]
        )

    def test_forged_reward_and_cross_plan_backup_rejected_without_data_loss(self):
        sid = self.session()
        data = self.store.snapshot()
        data["tables"]["rpg_rewards"][0]["xp"] = 999999
        path = self.root / "forged.json"
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.store.restore(path)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 5)
        self.assertIsNotNone(
            self.store.one("SELECT id FROM sessions WHERE id=?", (sid,))
        )

    def test_legacy_json_versions_restore_without_automatic_rewards(self):
        self.session()
        for version in (1, 2, 3):
            with self.subTest(version=version):
                data = self.store.snapshot()
                data["version"] = version
                for name in RPG_TABLES:
                    data["tables"].pop(name)
                if version <= 2:
                    for row in data["tables"]["topics"]:
                        row.pop("notes")
                if version == 1:
                    for row in data["tables"]["sessions"]:
                        row.pop("pauses")
                path = self.root / f"legacy{version}.json"
                path.write_text(json.dumps(data))
                self.store.restore(path)
                self.assertEqual(self.store.stats(self.plan)["count"], 1)
                self.assertEqual(self.rpg.profile(self.plan)["xp"], 0)
        preview = self.rpg.retroactive_preview(self.plan)
        self.assertEqual((preview["xp"], len(preview["sessions"])), (5, 1))
        ids = [s["id"] for s in preview["sessions"]]
        self.rpg.enroll_history(self.plan, ids)
        self.rpg.enroll_history(self.plan, ids)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 5)

    def test_schema_three_migration_preserves_old_studies_and_keeps_upgrade_backup(
        self,
    ):
        path = self.root / "legacy.sqlite3"
        connection = sqlite3.connect(path)
        connection.executescript(SCHEMA.replace(RPG_SCHEMA, ""))
        connection.execute("INSERT INTO plans(id,name) VALUES('p','Histórico')")
        connection.execute(
            "INSERT INTO subjects(id,plan_id,name,color) VALUES('s','p','TI','#D6B467')"
        )
        connection.execute(
            "INSERT INTO topics(id,subject_id,name) VALUES('t','s','SQL')"
        )
        connection.execute(
            "INSERT INTO sessions(id,plan_id,subject_id,topic_id,day,category,target,elapsed) VALUES('old','p','s','t','2020-01-01','Teoria',1200,1200)"
        )
        connection.commit()
        connection.close()
        upgraded = Store(path)
        try:
            self.assertEqual(
                upgraded.db.execute("PRAGMA user_version").fetchone()[0], 5
            )
            self.assertEqual(upgraded.stats("p")["elapsed"], 1200)
            self.assertEqual(upgraded.rpg.profile("p")["xp"], 0)
            self.assertTrue(list(self.root.glob("pre-rpg-*.sqlite3")))
            upgraded.export(self.root / "migrated.json")
            upgraded.validate_backup(self.root / "migrated.json")
        finally:
            upgraded.db.close()

    def test_display_preferences_validate_boolean_types(self):
        self.store.set_pref("rpg_show_character", False)
        self.store.set_pref("rpg_effects", False)
        self.store.set_pref("rpg_story", False)
        self.store.set_pref("rpg_reward_notifications", False)
        self.session(elapsed=600)
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 10)
        path = self.root / "prefs.json"
        self.store.export(path)
        self.store.validate_backup(path)
        data = self.store.snapshot()
        data["tables"]["preferences"][0]["value"] = '"false"'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.store.validate_backup(path)

    def test_production_adapter_has_no_demo_profile_and_real_receipt(self):
        from journey_backend import RPGJourney

        journey = RPGJourney(self.store)
        hero = journey.character(self.plan)
        self.assertEqual(
            (hero.source, hero.level, hero.xp, hero.coins), ("real", 1, 0, 0)
        )
        mission = journey.mission(self.plan)
        fields = journey.mission_fields(self.plan, mission, minutes=3)
        self.assertEqual(fields["target"], 180)
        self.assertIn("mission_id", fields)
        sid = self.session(context={"mission_id": fields["mission_id"]}, elapsed=180)
        reward = journey.reward_for(dict(id=sid, elapsed=180), "Matemática")
        self.assertEqual((reward.source, reward.xp), ("real", 3))
        self.assertTrue(
            all(item.source == "real" for item in journey.equipment(self.plan))
        )
        self.assertEqual(journey.challenges(self.plan), [])

    def test_recommended_mission_rejects_other_topic_of_fixed_block(self):
        self.cycle()
        other = self.store.save("topics", {"subject_id": self.subject, "name": "Outro"})
        with self.assertRaises(ValueError):
            self.rpg.recommended_mission(self.plan, other)

    def test_already_studied_block_does_not_invent_extra_mission_time(self):
        cycle, block = self.cycle()
        self.session(block_id=block, lap=1, elapsed=1500)
        self.assertIsNone(self.rpg.recommended_mission(self.plan))
        current = self.store.current_cycle(self.plan)
        self.assertEqual((current["position"], current["lap"]), (0, 1))

    def test_editing_unenrolled_historical_review_does_not_grant_retroactive_xp(self):
        rid = self.store.save(
            "reviews",
            {
                "topic_id": self.topic,
                "due": self.store.today().isoformat(),
                "interval": 1,
                "state": "Pendente",
            },
        )
        sid = self.session(category="Revisão", review_id=rid, elapsed=300)
        with self.store.db:
            self.store.db.execute("DELETE FROM rpg_sources")
            self.rpg.sync_in_transaction()
        self.store.save_session(
            self.fields(id=sid, category="Revisão", review_id=rid, elapsed=600)
        )
        self.assertEqual(self.rpg.profile(self.plan)["xp"], 0)
        self.assertEqual(len(self.rpg.retroactive_preview(self.plan)["sessions"]), 1)

    def test_active_mission_backup_validates_context_and_recovers_paused(self):
        mission = self.rpg.recommended_mission(self.plan)
        clock = Clock(self.store, lambda: 0)
        clock.start(dict(self.fields(), **{"mission_id": mission["id"]}), "Timer")
        snapshot = self.store.snapshot()
        forged = json.loads(json.dumps(snapshot))
        state = json.loads(forged["tables"]["active"][0]["value"])
        state["mission_id"] = "missing"
        forged["tables"]["active"][0]["value"] = json.dumps(state)
        from backups import validate_backup

        path = self.root / "active.json"
        path.write_text(json.dumps(forged), encoding="utf-8")
        with self.assertRaises(ValueError):
            validate_backup(path, SCHEMA, TABLES)
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        validated = validate_backup(path, SCHEMA, TABLES)
        self.assertEqual(validated["version"], 5)
        recovered = Clock(self.store, lambda: 10)
        self.assertFalse(recovered.state["running"])
        self.assertEqual(recovered.state["mission_id"], mission["id"])

    def test_selected_topic_is_retained_and_other_canonical_time_completes_block(self):
        cycle, block = self.cycle()
        with self.store.db:
            self.store.db.execute(
                "UPDATE blocks SET topic_id=NULL WHERE id=?", (block,)
            )
        other = self.store.save(
            "topics", {"subject_id": self.subject, "name": "Divisão"}
        )
        mission = self.rpg.recommended_mission(self.plan, other)
        self.assertEqual(self.rpg.recommended_mission(self.plan)["id"], mission["id"])
        self.session(block_id=block, lap=1, elapsed=1500)
        self.assertTrue(self.rpg.mission(mission["id"])["completed"])
        self.assertEqual(self.rpg.mission(mission["id"])["remaining"], 0)
        self.assertEqual(self.store.current_cycle(self.plan)["position"], 0)
