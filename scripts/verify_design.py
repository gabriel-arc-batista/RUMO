"""Check native animation lifecycle, reduced motion and repeated navigation."""

import json
import sys
import tempfile
import time
import tkinter as tk
from tkinter import font as tkfont
import gc
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App, SECTIONS
from core import Store
from ui_kit import Card, Stat


def pump(root, seconds=0.75):
    finish = time.monotonic() + seconds
    while time.monotonic() < finish:
        root.update()
        time.sleep(0.01)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
    root = tk.Tk()
    app = App(root, Store(Path(folder) / "design.sqlite3"))
    errors = []
    root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
    pump(root)
    assert float(root.attributes("-alpha")) == 1
    assert tkfont.Font(root, family="Inter").actual("family") == "Inter"
    # Current surfaces are quiet cards; numbers use text stats, without a
    # decorative entrance animation. Validate the actual rendered structure.
    app.navigate("Início")
    pump(root)
    cards = [w for w in descendants(app.content) if isinstance(w, Card)]
    stats = [w for w in descendants(app.content) if isinstance(w, Stat)]
    assert cards
    empty_text = next(
        w
        for w in descendants(app.content)
        if isinstance(w, tk.Label)
        and str(w.cget("text")).startswith("Nenhum estudo registrado ainda.")
    )
    assert empty_text.winfo_reqwidth() <= empty_text.master.winfo_width()
    subject = app.store.one(
        "SELECT id FROM subjects WHERE plan_id=? LIMIT 1", (app.plan,)
    )
    topic = app.store.one(
        "SELECT id FROM topics WHERE subject_id=? LIMIT 1", (subject["id"],)
    )
    app.store.save_session(
        dict(
            plan_id=app.plan,
            subject_id=subject["id"],
            topic_id=topic["id"],
            day=app.today().isoformat(),
            category="Teoria",
            target=60,
            elapsed=60,
            correct=0,
            wrong=0,
            blank=0,
        )
    )
    app.refresh()
    pump(root)
    cards = [w for w in descendants(app.content) if isinstance(w, Card)]
    stats = [w for w in descendants(app.content) if isinstance(w, Stat)]
    assert cards and stats
    assert all(w.winfo_width() > 1 and w.body.winfo_width() > 1 for w in cards)
    for stat in stats:
        for text in stat.winfo_children():
            assert text.winfo_reqwidth() <= stat.winfo_width(), (
                text.cget("text"),
                stat.winfo_width(),
            )
    assert app.sidebar.winfo_ismapped() and app.sidebar.winfo_width() == 224
    assert app.scroll.winfo_x() >= 224
    app.toggle_sidebar()
    pump(root)
    assert not app.sidebar.winfo_ismapped()
    app.toggle_sidebar()
    pump(root)
    assert app.sidebar.winfo_ismapped()
    button = app.floating
    button.event_generate("<Leave>")
    pump(root)
    resting = button.current
    button.event_generate("<Enter>")
    assert button in app.motion.jobs
    pump(root)
    assert button.current != resting and button not in app.motion.jobs
    button.event_generate("<Leave>")
    pump(root)
    assert button.current.lower() == resting.lower()
    card = cards[0]
    fill = card.itemcget(card.find_withtag("fill")[0], "fill")
    card.event_generate("<Enter>")
    pump(root)
    assert card.itemcget(card.find_withtag("fill")[0], "fill") == fill
    assert card not in app.motion.jobs
    card.event_generate("<Leave>")
    pump(root)
    assert card.itemcget(card.find_withtag("fill")[0], "fill") == fill
    app.open_clock()
    pump(root)
    win = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
    assert float(win.attributes("-alpha")) == 1
    win.destroy()
    subject = app.store.one(
        "SELECT * FROM subjects WHERE plan_id=? LIMIT 1", (app.plan,)
    )
    topic = app.store.one(
        "SELECT * FROM topics WHERE subject_id=? LIMIT 1", (subject["id"],)
    )
    app.clock.start(
        {
            "plan_id": app.plan,
            "subject_id": subject["id"],
            "topic_id": topic["id"],
            "category": "Teoria",
            "target": 1800,
            "day": app.today().isoformat(),
            "start_time": "10:00",
        },
        "Timer",
    )
    app.open_clock()
    clock = app.clock_win
    root.update_idletasks()
    pump(root, 0.08)
    first_y = clock.winfo_y()
    first_alpha = float(clock.attributes("-alpha"))
    assert 0 < first_alpha <= 1
    if sys.platform.startswith("linux"):
        assert first_alpha == 1  # Linux native windows remain opaque.
    pump(root)
    assert float(clock.attributes("-alpha")) == 1
    app.clock.discard()
    clock.destroy()
    pump(root)
    # Destroy a window during its fade and ensure callbacks are removed.
    app.open_clock()
    win = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
    win.destroy()
    pump(root)
    # Warm both lazy screen content and shared image caches before measuring
    # repeated navigation; the account screen also opens its owned workspace.
    for _ in range(2):
        for section in SECTIONS:
            app.navigate(section)
            root.update()
    gc.collect()
    before = psutil.Process().memory_info().rss
    for _ in range(4):
        for section in SECTIONS:
            app.navigate(section)
            root.update()
    pump(root)
    gc.collect()
    growth = psutil.Process().memory_info().rss - before
    assert growth < 5 * 1024**2, growth
    # Several page changes before processing idle callbacks must be safe too.
    for section in SECTIONS:
        app.navigate(section)
    pump(root)
    app.store.set_pref("animations", False)
    app.apply_theme()
    app.build_shell()
    app.refresh()
    pump(root)
    button = app.floating
    button.event_generate("<Enter>")
    assert (
        button.current.lower() == button.colors()[1].lower()
        and button not in app.motion.jobs
    )
    app.open_clock()
    win = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
    assert float(win.attributes("-alpha")) == 1
    win.destroy()
    pump(root)
    assert not app.motion.jobs and not errors, (app.motion.jobs, errors)
    report = {
        "hover_transitions": True,
        "quiet_cards_stable_hover": True,
        "window_reveal_completed": True,
        "destroy_during_animation": True,
        "inter_loaded": True,
        "current_cards_and_stats_rendered": True,
        "persistent_collapsible_sidebar": True,
        "clock_reveal_completed": True,
        "navigation_memory_growth_mb": round(growth / 1024**2, 2),
        "rapid_navigation": True,
        "empty_metric_text_fits": True,
        "reduced_motion": True,
        "idle_animation_callbacks": 0,
        "errors": errors,
    }
    (Path(__file__).resolve().parents[1] / "validation/design-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))
    app.store.close()
    root.destroy()
