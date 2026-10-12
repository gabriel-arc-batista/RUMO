"""Real Tk integration checks and reproducible screenshots in an isolated database."""

import json
import os
import sys
import tempfile
import time
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module
from app import App, SECTIONS, Form
from unittest.mock import patch
from core import Store, uid
from window_capture import capture_window
import psutil

out = Path(__file__).resolve().parents[1] / "validation"
out.mkdir(exist_ok=True)
if os.name == "nt":
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
store = Store(Path(tmp.name) / "gui.sqlite3")
root = tk.Tk()
app = App(root, store)
errors = []
captured = []


class CaptureForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        captured.append(self)


app_module.Form = CaptureForm
root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
root.geometry("1366x768+0+0")


def pump():
    finish = time.monotonic() + 0.7
    while time.monotonic() < finish:
        root.update()
        time.sleep(0.02)


def native_snap(window, path):
    get_parent = ctypes.windll.user32.GetParent
    get_parent.argtypes = [ctypes.c_void_p]
    get_parent.restype = ctypes.c_void_p
    capture_window(get_parent(window.winfo_id()), path)


def snap(name):
    pump()
    native_snap(root, out / name)


def form(title):
    windows = [
        w
        for w in root.winfo_children()
        if isinstance(w, tk.Toplevel) and w.title() == title
    ]
    assert windows, title
    return windows[-1]


def descendants(widget):
    for w in widget.winfo_children():
        yield w
        yield from descendants(w)


def click(label, window=root):
    buttons = [
        w
        for w in descendants(window)
        if isinstance(w, (tk.ttk.Button, app_module.MotionButton))
        and w.cget("text") == label
    ]
    assert buttons, label
    buttons[-1].invoke()
    pump()


pump()
snap("inicio-vazio-escuro.png")
# Open form through the same button used by users, create new entities in form.
click("Registrar")
win = form("Registro de estudo")
entries = [w for w in descendants(win) if isinstance(w, tk.ttk.Entry)]
# Use returned form to exercise the callback itself and all data validation.
win.destroy()
f = app.session_form()
for key, value in {
    "subject": "Banco de dados",
    "topic": "Normalização",
    "elapsed_text": "00:45:00",
    "correct": "15",
    "wrong": "5",
    "pages": "10",
    "schedule": True,
    "theory": True,
}.items():
    f.vars[key].set(value)
f.submit()
pump()
assert not f.win.winfo_exists(), f.error.cget("text")
s = store.stats(app.plan)
assert s["elapsed"] == 2700 and s["rate"] == 75 and s["total"] == 20
r = store.sessions(app.plan)[0]
f = app.session_form(editing=r)
f.vars["correct"].set("16")
f.vars["wrong"].set("4")
f.submit()
pump()
assert store.stats(app.plan)["rate"] == 80
# A rejected registration must not leak newly typed entities into the database.
f = app.session_form()
f.vars["subject"].set("Não deve existir")
f.vars["topic"].set("Inválido")
f.vars["elapsed_text"].set("-1:00:00")
f.submit()
pump()
assert f.win.winfo_exists() and not store.one(
    "SELECT id FROM subjects WHERE name='Não deve existir'"
)
f.win.destroy()
# Real management forms, generator preview, review actions, preferences and calendar.
app.subject_form()
f = captured[-1]
f.vars["name"].set("Matéria extra")
f.vars["weight"].set("2")
f.submit()
pump()
assert not f.win.winfo_exists()
extra = store.one("SELECT * FROM subjects WHERE name='Matéria extra'")
app.topic_form()
f = captured[-1]
f.vars["subject"].set(app.label_for(app.subject_map(), extra["id"]))
f.vars["name"].set("Assunto extra")
f.submit()
pump()
assert not f.win.winfo_exists()
with patch.object(app_module.messagebox, "askokcancel", return_value=True):
    app.generate_cycle()
    f = captured[-1]
    f.vars["total"].set("180")
    f.submit()
    pump()
    assert not f.win.winfo_exists()
generated = store.current_cycle(app.plan)
assert store.cycle_blocks(generated)
app.task_form()
f = captured[-1]
f.vars["name"].set("Revisar erros")
f.vars["due"].set(r["day"])
f.submit()
pump()
assert not f.win.winfo_exists()
review = store.one("SELECT * FROM reviews ORDER BY due LIMIT 1")
app.update_review_date(review["id"], r["day"])
assert (
    store.one("SELECT due FROM reviews WHERE id=?", (review["id"],))["due"] == r["day"]
)
app.calendar()
pump()
calendar_window = next(
    w
    for w in root.winfo_children()
    if isinstance(w, tk.Toplevel) and w.title().startswith("Calendário")
)
calendar_combo = next(
    w for w in descendants(calendar_window) if isinstance(w, tk.ttk.Combobox)
)
click("Mini calendário", calendar_window)
mini_window = next(
    w
    for w in calendar_window.winfo_children()
    if isinstance(w, tk.Toplevel) and w.title() == "Mini calendário"
)
click("Mês ›", mini_window)
mini_window.destroy()
for view in ["Mês", "Lista", "Semana"]:
    calendar_combo.set(view)
    calendar_combo.event_generate("<<ComboboxSelected>>")
    pump()
    assert not errors, errors
target_day = next(
    w.calendar_day
    for w in descendants(calendar_window)
    if getattr(w, "calendar_day", None) and w.calendar_day != r["day"]
)
target_card = next(
    w
    for w in descendants(calendar_window)
    if getattr(w, "calendar_day", None) == target_day
)
review_label = next(
    w
    for w in descendants(calendar_window)
    if getattr(w, "calendar_event_id", None) == review["id"]
)
calendar_window.lift()
pump()
target_x = target_card.winfo_rootx() + 12
target_y = target_card.winfo_rooty() + 30
with patch.object(app_module.messagebox, "askyesno", return_value=True):
    review_label.event_generate("<ButtonPress-1>", x=3, y=3)
    review_label.event_generate(
        "<ButtonRelease-1>", x=3, y=3, rootx=target_x, rooty=target_y
    )
    pump()
assert (
    store.one("SELECT due FROM reviews WHERE id=?", (review["id"],))["due"]
    == target_day
), {
    "expected": target_day,
    "actual": store.one("SELECT due FROM reviews WHERE id=?", (review["id"],)),
    "target_xy": (target_x, target_y),
    "under_pointer": str(calendar_window.winfo_containing(target_x, target_y)),
    "calendar_geometry": calendar_window.geometry(),
}
native_snap(calendar_window, out / "calendario-escuro.png")
calendar_window.destroy()
app.preferences()
f = captured[-1]
f.vars["daily_subjects"].set("2")
f.vars["timezone"].set("America/Fortaleza")
f.submit()
pump()
assert store.pref("daily_subjects") == 2 and not f.win.winfo_exists()
stats_csv = Path(tmp.name) / "statistics.csv"
with patch.object(
    app_module.filedialog, "asksaveasfilename", return_value=str(stats_csv)
):
    app.export_stats_csv()
assert "tempo_liquido_segundos" in stats_csv.read_text(encoding="utf-8-sig")
root.after(
    180,
    lambda: click(
        "OK",
        next(
            w
            for w in root.winfo_children()
            if isinstance(w, tk.Toplevel) and w.title() == "Teste de aviso"
        ),
    ),
)
app_module.messagebox.showinfo(
    "Teste de aviso", "Aviso local com tema escuro.", parent=root
)
pump()
# Structured historical BACEN data and no fabricated study sessions.
data = json.loads(
    (Path(__file__).resolve().parents[1] / "assets/bacen2024.json").read_text(
        encoding="utf-8"
    )
)
store.import_topics(app.plan, data["areas"]["Tecnologia da Informação"])
cycle = store.save("cycles", {"plan_id": app.plan, "name": "BACEN — RUMO"})
for i, s in enumerate(
    store.rows(
        "SELECT * FROM subjects WHERE plan_id=? ORDER BY name LIMIT 5", (app.plan,)
    )
):
    store.save(
        "blocks", {"cycle_id": cycle, "subject_id": s["id"], "target": 2700, "sort": i}
    )
store.save("goals", {"plan_id": app.plan, "hours": 10, "questions": 100})
store.save_session(
    {
        "plan_id": app.plan,
        "subject_id": None,
        "topic_id": None,
        "day": r["day"],
        "category": "Simulado",
        "target": 7200,
        "elapsed": 5400,
        "correct": 70,
        "wrong": 20,
        "blank": 10,
        "mock_name": "Simulado de validação",
        "mock_format": "Certo/Errado",
        "score_correct": 1,
        "score_wrong": 1,
        "score_blank": 0,
    }
)

memory = []
for theme in ["Escuro", "Claro"]:
    store.set_pref("theme", theme)
    app.apply_theme()
    app.build_shell()
    for section in SECTIONS:
        app.navigate(section)
        pump()
        memory.append(psutil.Process().memory_info().rss / 1024**2)
        snap(f"{SECTIONS.index(section):02d}-{theme.lower()}.png")
        assert not errors, errors

store.set_pref("theme", "Escuro")
app.apply_theme()
app.build_shell()
app.navigate("Início")
pump()
app.clock.start(
    {
        "plan_id": app.plan,
        "subject_id": r["subject_id"],
        "topic_id": r["topic_id"],
        "category": "Teoria",
        "target": 1800,
        "day": r["day"],
        "start_time": "10:00",
    },
    "Timer",
)
app.open_clock()
pump()
clockwin = app.clock_win
native_snap(clockwin, out / "relogio-escuro.png")
app.clock.pause()
app.clock.add(5)
assert app.clock.state["target"] == 2100
origin_plan = app.plan
app.plan = next(
    p["id"]
    for p in store.rows("SELECT id FROM plans WHERE archived=0")
    if p["id"] != origin_plan
)
app.finish_clock()
pump()
app.clock_form.vars["elapsed_text"].set("00:00:10")
app.clock_form.submit()
pump()
assert app.clock.state is None
app.plan = origin_plan
assert store.stats(app.plan)["count"] == 3
app.navigate("Histórico")
root.geometry("1000x650")
pump()
snap("janela-menor.png")
# Backup roundtrip with UI-created records and relationships.
backup = Path(tmp.name) / "backup.json"
store.export(backup)
count = store.stats(app.plan)["count"]
store.delete_session(r["id"])
store.restore(backup)
assert store.stats(app.plan)["count"] == count
store.close()
reopened = Store(Path(tmp.name) / "gui.sqlite3")
assert reopened.stats(app.plan)["count"] == count
reopened.db.close()
report = {
    "gui_errors": errors,
    "themes": ["Escuro", "Claro"],
    "pages": len(SECTIONS),
    "resolution": "1366x768; 1000x650",
    "memory_mb_min": round(min(memory), 1),
    "memory_mb_max": round(max(memory), 1),
    "flows": [
        "manual create with new subject/topic",
        "edit questions",
        "invalid form rolls back new entities",
        "subject/topic forms",
        "cycle generation with preview",
        "task form",
        "review reschedule",
        "weekly/monthly/list calendar",
        "preferences and timezone",
        "themed dialog",
        "clock pause/add/finalize",
        "all sections both themes",
        "JSON restore",
        "restart persistence",
    ],
    "isolated_data": True,
}
(out / "gui-report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False))
root.destroy()
tmp.cleanup()
