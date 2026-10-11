"""Regression for unmapped selectors/dialogs and gear actions with isolated data."""

import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as application
from core import Store
from ui import MotionButton
import rpg_ui


def main():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "dialogs.sqlite3")
        plan = store.save("plans", {"name": "QA formulários"})
        subject = store.save(
            "subjects", {"plan_id": plan, "name": "Matemática", "color": "#CDAA5C"}
        )
        topic = store.save("topics", {"subject_id": subject, "name": "Frações"})
        store.set_pref("active_plan", plan)
        root = tk.Tk()
        app = application.App(root, store)
        errors = []
        root.report_callback_exception = lambda kind, value, tb: errors.append(
            str(value)
        )
        captured = []

        class Capture(application.Form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                captured.append(self)

        def pump(seconds=0.12):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                root.update()
                time.sleep(0.005)

        def buttons(widget):
            for child in widget.winfo_children():
                if isinstance(child, MotionButton):
                    yield child
                yield from buttons(child)

        try:
            with patch.object(application, "Form", Capture):
                # No study yet: explanation, save disabled, selector still opens safely.
                empty = rpg_ui.challenge_form(app)
                assert empty.save_button.cget("state") == "disabled"
                empty.widgets["kind"].open()  # deliberately BEFORE parent has mapped
                pump()
                assert empty.widgets["kind"].popup.winfo_viewable()
                empty.win.destroy()
                pump()
                store.save_session(
                    dict(
                        plan_id=plan,
                        subject_id=subject,
                        topic_id=topic,
                        day=store.today().isoformat(),
                        category="Teoria",
                        target=6000,
                        elapsed=6000,
                        correct=0,
                        wrong=0,
                        blank=0,
                    )
                )
                for theme in ("Escuro", "Claro"):
                    store.set_pref("theme", theme)
                    app.apply_theme()
                    app.build_shell()
                    pump()
                    for animations in (True, False):
                        store.set_pref("animations", animations)
                        app.motion.enabled = animations
                        for create, key in (
                            (app.task_form, "state"),
                            (app.goal_form, "subject"),
                            (lambda: rpg_ui.challenge_form(app), "kind"),
                        ):
                            create()
                            form = captured[-1]
                            form.widgets[key].open()  # old code raised 'grab failed'
                            pump()
                            popup = form.widgets[key].popup
                            assert popup.winfo_viewable()
                            assert (
                                float(form.win.attributes("-alpha")) == 1
                                if sys.platform.startswith("linux")
                                else True
                            )
                            assert root.grab_current() == popup
                            popup.destroy()
                            form.win.destroy()
                            pump()

                        def close_confirmation():
                            target = next(
                                w
                                for w in root.winfo_children()
                                if isinstance(w, tk.Toplevel)
                                and w.title() == "Confirmação QA"
                            )
                            next(b for b in buttons(target) if b.text == "OK").invoke()

                        root.after(80, close_confirmation)
                        assert (
                            application.messagebox.showinfo(
                                "Confirmação QA", "Janela nativa visível.", parent=root
                            )
                            is True
                        )
                        pump()
                # Submit through the actual multi-topic picker, not a text injection.
                form = rpg_ui.challenge_form(app)
                form.vars["name"].set("Masmorra da regressão")
                form.vars["questions"].set("5")
                next(
                    b
                    for b in buttons(form.win)
                    if b.text == "Escolher assuntos estudados"
                ).invoke()
                pump()
                selector = next(
                    w for w in form.win.winfo_children() if isinstance(w, tk.Toplevel)
                )

                def trees(w):
                    from tkinter import ttk

                    for c in w.winfo_children():
                        if isinstance(c, ttk.Treeview):
                            yield c
                        yield from trees(c)

                tree = next(trees(selector))
                tree.selection_set(tree.get_children()[0])
                next(
                    b
                    for b in buttons(selector)
                    if b.text == "Usar assuntos selecionados"
                ).invoke()
                form.submit()
                pump()
                assert len(store.rpg.challenges(plan)) == 1
                # Every gear category reflows; starter shortcuts never save a study on click.
                app.navigate("Jornada")
                pump()
                for kind in ("Roupas", "Armaduras", "Armas", "Montarias", "Acessórios"):
                    next(b for b in buttons(app.content) if b.text == kind).invoke()
                    pump()
                before = store.stats(plan)["count"]
                preview = rpg_ui.purchase_preview(app, "rusty_sword")
                pump()
                next(
                    b for b in buttons(preview) if b.text == "Praticar questões"
                ).invoke()
                pump()
                practice = captured[-1]
                practice.widgets["topic"].open()
                pump()
                practice.widgets["topic"].popup.destroy()
                practice.submit()
                pump()
                setup = captured[-1]
                assert setup.win.title() == "Iniciar estudo"
                assert setup.vars["category"].get() == "Questões"
                setup.win.destroy()
                pump()
                assert store.stats(plan)["count"] == before
                assert app.clock.state is None
                before_xp = store.rpg.profile(plan)["xp"]
                rpg_ui.study_action(app, "notes")
                topic_form = captured[-1]
                topic_form.widgets["topic"].open()
                pump()
                topic_form.widgets["topic"].popup.destroy()
                topic_form.submit()
                pump()
                notebook = captured[-1]
                assert notebook.win.title() == "Meu caderno de estudo"
                notebook.widgets["notes"].insert(
                    "1.0", "Frações: escrevi minha explicação e um exemplo."
                )
                notebook.submit()
                pump()
                erudito = next(
                    p for p in store.rpg.progression(plan) if p["id"] == "erudito"
                )
                assert erudito["value"] == 1
                assert store.rpg.profile(plan)["xp"] == before_xp
                assert store.stats(plan)["count"] == before
                assert not errors, errors
                print(
                    "Native dialogs passed: early selector, modal confirmation, empty/new dungeon, all gear tabs and old-weapon shortcut and real Erudito notebook; both themes and animation settings."
                )
        finally:
            root.destroy()
            store.db.close()


if __name__ == "__main__":
    main()
