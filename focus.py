"""Focus mode window: subject, topic, time and controls first; nothing else competes.

Clock rules stay in core.Clock. This module only lays out the window and wires
the existing App callbacks (toggle_pause, finish_clock, discard_clock).
"""

import tkinter as tk
from tkinter import ttk

from ui import Chip, FocusDial, MotionButton, Tooltip


def open_focus(app):
    p = app.motion.palette
    backdrop = tk.Toplevel(app.root)
    backdrop.overrideredirect(True)
    backdrop.configure(bg="#000000")
    backdrop.attributes("-alpha", 0)

    def position_backdrop(event=None):
        if event is None or event.widget == app.root:
            backdrop.geometry(
                f"{app.root.winfo_width()}x{app.root.winfo_height()}+{app.root.winfo_rootx()}+{app.root.winfo_rooty()}"
            )

    position_backdrop()
    backdrop.lift()
    app.motion.animate(backdrop, lambda t: backdrop.attributes("-alpha", t * 0.65), 320)
    tracking = app.root.bind("<Configure>", position_backdrop, add="+")
    win = tk.Toplevel(app.root)
    app.clock_win = win
    win.title("Modo foco • RUMO")
    win.geometry("680x660")
    win.minsize(560, 600)
    win.configure(bg=app.bg)
    win.transient(app.root)

    def close_backdrop(event):
        if event.widget != win:
            return
        app.motion.cancel(backdrop)
        app.root.unbind("<Configure>", tracking)
        if backdrop.winfo_exists():
            backdrop.destroy()

    win.bind("<Destroy>", close_backdrop, add="+")
    backdrop.bind("<Button-1>", lambda e: win.destroy())
    state = app.clock.state
    subject = app.store.one(
        "SELECT name FROM subjects WHERE id=?", (state["subject_id"],)
    )
    topic = app.store.one("SELECT name FROM topics WHERE id=?", (state["topic_id"],))
    context = app.focus_context or {}

    bar = ttk.Frame(win)
    bar.pack(fill="x", padx=20, pady=(16, 0))
    reduced = context.get("reduced")
    if reduced:
        Chip(
            bar,
            f"HOJE ESTÁ DIFÍCIL • {reduced.minutes} MIN"
            + (f" + {reduced.questions} QUESTÕES" if reduced.questions else ""),
            tone="success",
            icon="leaf",
            tip="Versão curta da missão. O restante do bloco continua no ciclo.",
        ).pack(side="left")
    elif state.get("block_id"):
        Chip(bar, "MISSÃO DO CICLO", tone="accent", icon="compass").pack(side="left")
    else:
        Chip(bar, "ESTUDO LIVRE", icon="timer").pack(side="left")
    collapse = MotionButton(
        bar, icon="chevron-down", style="Ghost.TButton", command=win.destroy
    )
    collapse.pack(side="right")
    Tooltip(collapse, "Recolher. O relógio continua no topo da janela principal.")
    full = MotionButton(
        bar,
        icon="maximize",
        style="Ghost.TButton",
        command=lambda: win.attributes(
            "-fullscreen", not win.attributes("-fullscreen")
        ),
    )
    full.pack(side="right")
    Tooltip(full, "Tela cheia (Esc para sair)")

    ttk.Label(win, text=subject["name"], style="Title.TLabel").pack(pady=(18, 2))
    topic_label = ttk.Label(
        win,
        text=topic["name"],
        style="Muted.TLabel",
        justify="center",
        wraplength=560,
        font=(app.font_family, 11),
    )
    topic_label.pack(padx=40)
    app.clock_label = FocusDial(win, app)
    app.clock_label.configure(height=284)
    app.clock_label.pack(fill="x", pady=(4, 0))
    app.clock_info = ttk.Label(win, text="", style="Muted.TLabel", justify="center")
    app.clock_info.pack(pady=(0, 4))
    app.clock_goal = ttk.Label(
        win,
        text=app.main_goal_text(state["plan_id"]),
        style="Muted.TLabel",
        font=(app.font_family, 9),
        wraplength=560,
        justify="center",
    )
    app.clock_goal.pack(pady=(0, 14))

    controls = ttk.Frame(win)
    controls.pack()
    app.pause_button = MotionButton(
        controls,
        text="Pausar",
        icon="pause",
        height=46,
        width=16,
        command=app.toggle_pause,
    )
    app.pause_button.pack(side="left", padx=6)
    MotionButton(
        controls,
        text="Finalizar e registrar",
        icon="check",
        style="Accent.TButton",
        height=46,
        command=app.finish_clock,
    ).pack(side="left", padx=6)

    extra = ttk.Frame(win)
    extra.pack(pady=(14, 0))
    ttk.Label(extra, text="Adicionar tempo", style="Muted.TLabel").pack(
        side="left", padx=(0, 8)
    )
    for minutes in [1, 5, 15]:
        MotionButton(
            extra,
            text=f"+{minutes} min",
            style="Chip.TButton",
            command=lambda m=minutes: app.clock.add(m),
        ).pack(side="left", padx=3)

    footer = ttk.Frame(win)
    footer.pack(side="bottom", fill="x", padx=20, pady=16)
    MotionButton(
        footer,
        text="Descartar sessão",
        icon="trash-2",
        style="Danger.TButton",
        height=34,
        command=app.discard_clock,
    ).pack(side="left")
    hint = ttk.Label(
        footer,
        text="Pausas não entram no tempo líquido • Ctrl+R volta aqui",
        style="Muted.TLabel",
        font=(app.font_family, 9),
    )
    hint.pack(side="right")
    win.bind("<Escape>", lambda e: win.attributes("-fullscreen", False))
    win.bind("<space>", lambda e: app.toggle_pause() if e.widget == win else None)
    app.update_clock_ui()
    app.motion.reveal(win)
    return win
