import json
import tempfile
import unittest
from pathlib import Path

from core import Store, uid
from journey_demo import PreviewJourney
from learning import create_starter_cycle
from theme import (
    DARK,
    LIGHT,
    THEMES,
    compact_duration,
    contrast,
    number,
    percent,
    resolve_theme,
)

TEXT = ["fg", "muted", "faint", "accent", "success", "error", "info", "warning"]


class ThemeTests(unittest.TestCase):
    def test_text_tokens_meet_wcag_aa_on_reading_surfaces(self):
        for palette in (theme["palette"] for theme in THEMES.values()):
            for fg in TEXT:
                for bg in ("bg", "surface", "raised", "sidebar"):
                    self.assertGreaterEqual(
                        contrast(palette[fg], palette[bg]), 4.5, (fg, bg)
                    )
            for fg, bg in [
                ("primary_ink", "primary"),
                ("primary_ink", "primary_hover"),
                ("accent", "tint"),
                ("accent", "selected"),
                ("success", "success_bg"),
                ("error", "error_bg"),
                ("info", "info_bg"),
                ("warning", "warning_bg"),
            ]:
                self.assertGreaterEqual(contrast(palette[fg], palette[bg]), 4.5)

    def test_every_theme_defines_the_same_roles(self):
        self.assertEqual(set(DARK), set(LIGHT))
        for theme in THEMES.values():
            self.assertEqual(set(theme["palette"]), set(DARK))

    def test_theme_preferences_resolve_with_legacy_values(self):
        self.assertEqual(resolve_theme("Escuro"), "Norte Dourado")
        self.assertEqual(resolve_theme("Claro"), "Aurora")
        self.assertEqual(resolve_theme("Sistema", system_dark=False), "Aurora")
        self.assertEqual(resolve_theme("Alto-Mar"), "Alto-Mar")
        self.assertEqual(resolve_theme("inexistente"), "Norte Dourado")

    def test_brazilian_formatting(self):
        self.assertEqual(number(1097), "1.097")
        self.assertEqual(percent(69.04, 1), "69,0%")
        self.assertEqual(percent(None), "—")
        self.assertEqual(compact_duration(149754), "41h 35min")
        self.assertEqual(compact_duration(1500), "25 min")


class PreviewJourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "study.db")
        self.plan = self.store.put("plans", {"name": "Plano"})
        self.subject = self.store.put(
            "subjects",
            {"plan_id": self.plan, "name": "Bancos De Dados", "color": "#D6B467"},
        )
        self.topic = self.store.put(
            "topics", {"subject_id": self.subject, "name": "2 Modelos relacionais"}
        )
        self.journey = PreviewJourney(self.store)

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def snapshot(self):
        tables = self.store.snapshot()["tables"]
        return json.dumps(tables, sort_keys=True, default=str)

    def test_no_cycle_means_no_mission(self):
        self.assertIsNone(self.journey.mission(self.plan))

    def test_mission_reads_next_block_topic_and_where_i_stopped(self):
        create_starter_cycle(self.store, self.plan)
        session = self.store.validate_session(
            dict(
                id=uid(),
                plan_id=self.plan,
                subject_id=self.subject,
                topic_id=self.topic,
                day=self.store.today().isoformat(),
                start_time="09:00",
                category="Teoria",
                target=1500,
                elapsed=600,
                correct=0,
                wrong=0,
                blank=0,
                total=0,
                material="",
                url="",
                pages=None,
                video=None,
                next_step="Revisar chaves estrangeiras",
                notes="",
                block_id=None,
                lap=None,
                review_id=None,
                segments="[]",
                pauses="[]",
            )
        )
        self.store.save_session(session, [], False, [], False, session["day"], True)
        mission = self.journey.mission(self.plan)
        self.assertEqual(mission.subject_id, self.subject)
        self.assertEqual(mission.topic_id, self.topic)
        self.assertEqual(mission.next_step, "Revisar chaves estrangeiras")
        self.assertEqual(mission.suggested_seconds, 1500)
        self.assertIsNone(mission.reward_xp)
        reduced = self.journey.reduced(mission)
        self.assertEqual((reduced.minutes, reduced.questions), (10, 2))

    def test_preview_never_writes_and_never_invents_rewards(self):
        create_starter_cycle(self.store, self.plan)
        before = self.snapshot()
        changes = self.store.db.total_changes
        self.journey.mission(self.plan)
        self.journey.reviews(self.plan)
        self.journey.character(self.plan)
        self.journey.skills(self.plan)
        self.journey.equipment(self.plan)
        self.journey.toggle_equipment(self.plan, "spyglass")
        self.journey.achievements(self.plan)
        self.journey.chapters(self.plan)
        self.journey.challenges(self.plan)
        self.assertIsNone(self.journey.reward_for({"elapsed": 1500}, "Bancos"))
        self.assertEqual(changes, self.store.db.total_changes)
        self.assertEqual(before, self.snapshot())

    def test_demo_values_are_labelled_and_skills_keep_real_effort(self):
        self.assertEqual(self.journey.character(self.plan).source, "demo")
        for item in self.journey.equipment(self.plan):
            self.assertEqual(item.source, "demo")
        skill = self.journey.skills(self.plan)[0]
        self.assertEqual(skill.progress_source, "demo")
        self.assertEqual((skill.effort_seconds, skill.answered), (0, 0))
        self.assertFalse(skill.sample_ok)

    def test_locked_equipment_cannot_be_toggled(self):
        self.journey.toggle_equipment(self.plan, "lantern")
        self.assertNotIn("lantern", self.journey.character(self.plan).equipped)
