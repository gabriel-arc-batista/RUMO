"""Native RPG integration with synthetic data; never opens the personal database."""

import sys
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from ui import MotionButton
from core import Store, Clock
import app as app_module
from app import Form
from journey_backend import RPGJourney
import rpg_ui


def main():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "rpg-gui.sqlite3")
        plan = store.save("plans", {"name": "QA temporário"})
        subject = store.save(
            "subjects", {"plan_id": plan, "name": "Matemática", "color": "#D6B467"}
        )
        topic = store.save("topics", {"subject_id": subject, "name": "Frações"})
        store.set_pref("active_plan", plan)
        root = tk.Tk()
        errors = []
        root.report_callback_exception = lambda kind, value, trace: errors.append(
            str(value)
        )
        app = App(root, store)
        root.report_callback_exception = lambda kind, value, trace: errors.append(
            str(value)
        )
        assert isinstance(app.journey, RPGJourney), "Production must use real RPG data"
        root.update()
        assert app.journey.character(plan).xp == 0
        cycle = store.save("cycles", {"plan_id": plan, "name": "Ciclo QA", "active": 1})
        block = store.save(
            "blocks",
            {
                "cycle_id": cycle,
                "subject_id": subject,
                "topic_id": topic,
                "target": 1500,
                "sort": 0,
            },
        )
        captured = []

        class CaptureForm(Form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                captured.append(self)

        app_module.Form = CaptureForm
        current = [0.0]
        app.clock = Clock(store, lambda: current[0])
        mission = app.journey.mission(plan)
        small = app.start_mission(mission, reduced=True)
        small.vars["minutes"].set("3")
        small.submit()
        setup = captured[-1]
        assert setup.win.title() == "Iniciar estudo"
        setup.submit()
        assert app.clock.state["mission_id"]
        for _ in range(18):
            current[0] += 5
            app.clock.tick()
        app.clock.pause()
        current[0] += 600
        app.clock.tick()
        assert app.clock.state["elapsed"] == 90
        app.clock.resume()
        for _ in range(18):
            current[0] += 5
            app.clock.tick()
        app.finish_clock()
        saved_form = app.clock_form
        saved_form.widgets["next_step"].delete("1.0", "end")
        saved_form.widgets["next_step"].insert("1.0", "Divisão")
        saved_form.submit()
        root.update()
        assert app.clock.state is None, "Clock form did not finalize"
        assert app.journey.character(plan).xp == 3
        assert store.stats(plan)["count"] == 1
        assert store.current_cycle(plan)["position"] == 0
        assert store.cycle_blocks(store.current_cycle(plan))[0]["elapsed"] == 180
        assert store.one("SELECT mission_id FROM rpg_links")["mission_id"]
        review = store.save(
            "reviews",
            {
                "topic_id": topic,
                "due": "2026-01-01",
                "interval": 1,
                "state": "Pendente",
            },
        )
        encounter = app.session_form(store.rpg.review_fields(review))
        encounter.vars["elapsed_text"].set("00:01:00")
        encounter.vars["recall"].set("Não lembrei")
        encounter.submit()
        assert (
            store.one("SELECT state FROM reviews WHERE id=?", (review,))["state"]
            == "Concluída"
        )
        assert app.journey.character(plan).xp == 9
        for page in ("Início", "Jornada", "Revisões", "Simulados", "Histórico"):
            app.navigate(page)
            root.update()
        form = rpg_ui.difficulty_form(app)
        form.vars["topic"].set("1. Matemática · Frações")
        for key, value in {
            "description": "Confusão de denominadores",
            "why": "Somei diretamente",
            "remember": "Buscar denominador comum",
        }.items():
            form.widgets[key].insert("1.0", value)
        form.submit()
        root.update()
        assert len(store.rpg.difficulties(plan)) == 1, "Difficulty form did not save"
        form = rpg_ui.challenge_form(app)
        form.vars["name"].set("Prática de frações")
        form.vars["questions"].set("5")
        form.widgets["topics"].insert("1.0", "1. Matemática · Frações")
        form.submit()
        root.update()
        assert len(store.rpg.challenges(plan)) == 1, "Challenge form did not save"
        boss = store.rpg.create_challenge(plan, "Chefe QA", [topic], 5, kind="Chefe")
        app.start_challenge(
            next(c for c in app.journey.challenges(plan) if c.id == boss)
        )
        boss_form = captured[-1]
        boss_form.vars["elapsed_text"].set("00:02:00")
        boss_form.vars["correct"].set("3")
        boss_form.vars["wrong"].set("2")
        boss_form.widgets["results"].insert("1.0", "Matemática | 3 | 2 | 0")
        boss_form.submit()
        assert store.rpg.challenge(boss)[
            "completed"
        ], "Boss form did not save canonical results"
        assert store.stats(plan)["count"] == 3
        assert store.stats(plan)["total"] == 5
        assert app.journey.character(plan).xp == 16

        store.save_session(
            dict(
                plan_id=plan,
                subject_id=subject,
                topic_id=topic,
                day=store.today().isoformat(),
                category="Teoria",
                target=3000,
                elapsed=3000,
                correct=0,
                wrong=0,
                blank=0,
            )
        )
        before_xp = store.rpg.profile(plan)["xp"]
        preview = rpg_ui.purchase_preview(app, "backpack")

        def buttons(widget):
            for child in widget.winfo_children():
                if isinstance(child, MotionButton):
                    yield child
                yield from buttons(child)

        purchase = next(
            button for button in buttons(preview) if button.text == "Comprar e equipar"
        )
        with patch.object(app_module.messagebox, "askyesno", return_value=True):
            purchase.invoke()
        assert next(
            item for item in store.rpg.catalog(plan) if item["id"] == "backpack"
        )["equipped"]
        assert store.rpg.profile(plan)["xp"] == before_xp
        assert store.rpg.profile(plan)["coins"] == 0
        for create in (rpg_ui.difficulty_list, rpg_ui.challenge_list):
            create(app)
            root.update()
            for window in root.winfo_children():
                if isinstance(window, tk.Toplevel):
                    window.destroy()
        for key in (
            "rpg_show_character",
            "rpg_effects",
            "rpg_story",
            "rpg_reward_notifications",
        ):
            store.set_pref(key, False)
        for page in ("Início", "Jornada"):
            app.navigate(page)
            root.update()
        root.destroy()
        store.close()
        assert not errors, errors
    print("Native RPG integration passed with isolated synthetic data.")


if __name__ == "__main__":
    main()
