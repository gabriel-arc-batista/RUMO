"""Native learning/cycle/library regression using only synthetic temporary data."""

import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from core import Store
from learning import create_starter_cycle
from pedagogy import save_graph
from ui import MotionButton


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def main():
    with tempfile.TemporaryDirectory() as folder:
        os.environ["RUMO_DATA"] = folder
        store = Store(Path(folder) / "test.sqlite3")
        plan = store.save("plans", {"name": "Trilha sintética de teste"})
        subject = store.save(
            "subjects", {"plan_id": plan, "name": "Dados", "color": "#D7B663"}
        )
        advanced = store.save(
            "topics", {"subject_id": subject, "name": "Consultas avançadas"}
        )
        basic = store.save("topics", {"subject_id": subject, "name": "Fundamentos SQL"})
        save_graph(store, plan, [dict(before=basic, after=advanced, kind="essential")])
        create_starter_cycle(store, plan)
        store.set_pref("active_plan", plan)
        root = tk.Tk()
        errors = []
        root.report_callback_exception = lambda kind, value, trace: errors.append(
            str(value)
        )
        app = App(root, store)
        try:
            app.navigate("Campo de Treinamento")
            root.update()
            buttons = [
                w
                for w in descendants(app.content)
                if isinstance(w, MotionButton)
                and w.cget("text") == "Consultar trilha de aprendizagem"
            ]
            assert len(buttons) == 1, "Library learning link missing"
            buttons[0].invoke()
            root.update()
            assert app.section == "Edital e assuntos"
            assert app.edital_selected == basic
            app.edital_selected = advanced
            app.navigate("Edital e assuntos")
            root.update()
            texts = []
            for widget in descendants(app.content):
                try:
                    texts.append(str(widget.cget("text")))
                except tk.TclError:
                    pass
            assert any("Você pode continuar livremente" in t for t in texts)
            starts = [
                w
                for w in descendants(app.content)
                if isinstance(w, MotionButton) and w.cget("text") == "Estudar agora"
            ]
            captured = []
            app.clock_setup = lambda data: captured.append(data)
            starts[0].invoke()
            assert captured[-1]["topic_id"] == advanced
            from pedagogy_ui import edit_dependencies
            from pedagogy import graph
            import app as app_module

            forms = []
            original_form = app_module.Form

            class CaptureForm(original_form):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    forms.append(self)

            app_module.Form = CaptureForm
            try:
                window = edit_dependencies(
                    app, store.one("SELECT * FROM topics WHERE id=?", (advanced,))
                )
                root.update()
                tree = next(
                    w for w in descendants(window) if isinstance(w, ttk.Treeview)
                )
                assert len(tree.get_children()) == 1
                tree.selection_set(tree.get_children()[0])
                next(
                    w
                    for w in descendants(window)
                    if isinstance(w, MotionButton)
                    and w.cget("text") == "Remover relação selecionada"
                ).invoke()
                assert graph(store, plan) == []
                next(
                    w
                    for w in descendants(window)
                    if isinstance(w, MotionButton)
                    and w.cget("text") == "Adicionar relação"
                ).invoke()
                root.update()
                form = forms[-1]
                form.vars["before"].set("Dados › Fundamentos SQL")
                form.vars["kind"].set("Essencial")
                form.submit()
                root.update()
                assert graph(store, plan)[0]["before"] == basic
                window.destroy()
            finally:
                app_module.Form = original_form
            assert store.stats(plan)["count"] == 0
            assert store.rpg.profile(plan)["xp"] == 0
            assert not errors, errors
            print("Native learning library/detail/access: passed, temporary data only")
        finally:
            app.close()


if __name__ == "__main__":
    main()
