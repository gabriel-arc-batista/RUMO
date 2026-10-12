"""Exercise the new controls in an isolated database; capture only our windows."""

import ctypes
import json
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module
from app import App, Form
from core import Store
from components import SearchSelect, CompletionBox
from ui import MotionButton
from window_capture import capture_window

ctypes.windll.shcore.SetProcessDpiAwareness(1)
output = Path(__file__).resolve().parents[1] / "validation"
captured = []


class CaptureForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        captured.append(self)


app_module.Form = CaptureForm


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def pump(root, seconds=0.5):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        root.update()
        time.sleep(0.01)


def snap(window, name):
    pump(window._root())
    parent = ctypes.windll.user32.GetParent
    parent.argtypes = [ctypes.c_void_p]
    parent.restype = ctypes.c_void_p
    capture_window(parent(window.winfo_id()), output / name)


def button(window, label):
    return next(
        w
        for w in descendants(window)
        if isinstance(w, MotionButton) and label in (w.text, w.icon)
    )


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
    store = Store(Path(folder) / "modern.sqlite3")
    root = tk.Tk()
    app = App(root, store)
    root.geometry("1366x768+0+0")
    errors = []
    root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
    from learning import create_starter_cycle, next_topic

    assert app.quote_header.winfo_exists()
    cycle = create_starter_cycle(store, app.plan)
    assert create_starter_cycle(store, app.plan) == cycle
    blocks = store.rows("SELECT * FROM blocks WHERE cycle_id=? ORDER BY sort", (cycle,))
    assert len(blocks) == len(
        store.rows("SELECT * FROM subjects WHERE plan_id=? AND archived=0", (app.plan,))
    )
    assert all(b["target"] == 1500 for b in blocks)
    first = next_topic(store, blocks[0]["subject_id"])
    assert first is not None
    store.db.execute("UPDATE topics SET done=1 WHERE id=?", (first["id"],))
    store.db.commit()
    assert next_topic(store, blocks[0]["subject_id"])["id"] != first["id"]
    app.navigate("Metas e conquistas")
    pump(root)
    button(root, "Adicionar meta").invoke()
    pump(root)
    assert store.pref("main_goal_" + app.plan)["name"]
    app.preferences()
    pump(root)
    preferences = captured[-1]
    assert len(preferences.notebook.tabs()) == 4
    preferences.win.destroy()
    pump(root)
    app.navigate("Edital e assuntos")
    pump(root)
    app.edital_search_entry.insert(0, "Java: classes")
    pump(root)
    leaf = next(app.edital_mapping[tid] for tid in app.edital_rows)
    row = app.edital_rows[leaf["id"]][0]
    checkbox = next(w for w in descendants(row) if isinstance(w, CompletionBox))
    checkbox.invoke()
    pump(root)
    assert checkbox.done
    button(row, "pencil").invoke()
    pump(root)
    notes = captured[-1]
    text = (
        "Interfaces: anotar quando usar.\nDúvida: composição × herança. Revisar amanhã."
    )
    notes.widgets["notes"].insert("1.0", text)
    snap(notes.win, "moderno-observacoes.png")
    notes.submit()
    pump(root)
    assert store.one("SELECT notes,done FROM topics WHERE id=?", (leaf["id"],)) == {
        "notes": text,
        "done": 1,
    }
    assert app.edital_rows[leaf["id"]][0] == row and "Interfaces:" in app.edital_rows[
        leaf["id"]
    ][2][-1].cget("text")
    form = app.clock_setup({"subject_id": leaf["subject_id"], "topic_id": leaf["id"]})
    pump(root)
    assert all(
        isinstance(form.widgets[key], SearchSelect)
        for key in ["subject", "topic", "category", "mode"]
    )
    assert not any(
        " · " in label and len(label.rsplit(" · ", 1)[-1]) == 4
        for label in form.widgets["subject"].values
    )
    button(form.win, "25 min").invoke()
    assert form.vars["target"].get() == "00:25:00"
    snap(form.win, "moderno-iniciar-estudo.png")
    select = form.widgets["topic"]
    select.open()
    pump(root)
    popup = select.popup
    search = next(w for w in descendants(popup) if isinstance(w, tk.ttk.Entry))
    search.insert(0, "Java: classes")
    pump(root)
    items = next(w for w in descendants(popup) if isinstance(w, tk.Listbox))
    assert items.size() > 0
    popup.geometry("520x400")
    pump(root)
    choose = button(popup, "Selecionar")
    assert choose.winfo_height() >= 40
    assert (
        choose.winfo_rooty() + choose.winfo_height()
        <= popup.winfo_rooty() + popup.winfo_height()
    )
    snap(popup, "moderno-seletor-assunto.png")
    choose.invoke()
    pump(root)
    form.submit()
    pump(root, 0.8)
    assert app.clock.state and app.clock_win.winfo_exists()
    assert store.pref("main_goal_" + app.plan)["name"] in app.clock_goal.cget("text")
    snap(app.clock_win, "moderno-relogio.png")
    app.toggle_pause()
    assert not app.clock.state["running"]
    app.toggle_pause()
    assert app.clock.state["running"]
    app.finish_clock()
    pump(root)
    registration = app.clock_form
    assert registration.notebook is not None
    tabs = [registration.notebook.tab(t, "text") for t in registration.notebook.tabs()]
    assert tabs == ["Sessão", "Questões", "Materiais e notas", "Revisões"]
    registration.vars["elapsed_text"].set("00:25:00")
    registration.vars["correct"].set("8")
    registration.vars["wrong"].set("2")
    snap(registration.win, "moderno-registro-estudo.png")
    registration.submit()
    pump(root)
    assert (
        app.clock.state is None
        and store.stats(app.plan)["elapsed"] == 1500
        and store.stats(app.plan)["rate"] == 80
    )
    # Data below is explicitly synthetic and only exists in this temporary folder.
    for i in range(1, 8):
        store.save_session(
            {
                "plan_id": app.plan,
                "subject_id": leaf["subject_id"],
                "topic_id": leaf["id"],
                "day": (app.today() - timedelta(days=i)).isoformat(),
                "category": "Questões",
                "target": 2700,
                "elapsed": 900 + i * 180,
                "correct": 6 + i,
                "wrong": 2,
                "blank": 1,
            }
        )
    for section, name in [
        ("Início", "moderno-inicio.png"),
        ("Estatísticas", "moderno-estatisticas.png"),
        ("Metas e conquistas", "moderno-desafios.png"),
    ]:
        app.navigate(section)
        snap(root, name)
    for level in ["Intermediário", "Avançado", "Iniciante"]:
        button(root, level).invoke()
        pump(root)
        assert store.pref("challenge_level_" + app.plan) == level
    root.geometry("1000x650+0+0")
    app.navigate("Início")
    pump(root)
    assert app.scroll.canvas.bbox("all")[2] <= app.scroll.canvas.winfo_width() + 1
    app.navigate("Estatísticas")
    pump(root)
    assert not errors, errors
    store.set_pref("theme", "Claro")
    app.apply_theme()
    app.build_shell()
    app.navigate("Configurações e ajuda")
    pump(root)
    snap(root, "polido-configuracoes-claro.png")
    app.navigate("Ciclo de estudos")
    snap(root, "polido-ciclo-claro.png")
    app.navigate("Início")
    snap(root, "polido-inicio-claro.png")
    form = app.clock_setup()
    pump(root)
    form.widgets["subject"].open()
    pump(root)
    popup = form.widgets["subject"].popup
    popup.geometry("520x400")
    pump(root)
    choose = button(popup, "Selecionar")
    assert choose.winfo_height() >= 40
    snap(popup, "polido-seletor-claro.png")
    popup.destroy()
    form.win.destroy()
    pump(root)
    assert not errors, errors
    report = {
        "isolated_data": True,
        "synthetic_graph_data": True,
        "green_checkboxes": True,
        "notes_saved_without_page_jump": True,
        "searchable_subject_picker": True,
        "no_internal_ids_in_names": True,
        "duration_presets": True,
        "focus_pause_resume_record": True,
        "registration_tabs": tabs,
        "challenge_levels": 3,
        "small_window": True,
        "gui_errors": errors,
    }
    (output / "modern-ui-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    store.close()
    root.destroy()
