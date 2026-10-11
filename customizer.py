"""Character creator: appearance options with a live portrait and full-body preview.

Appearance is purely visual: it never changes XP, metrics or rewards. The look
is saved as one preference (``appearance.PREFERENCE``) only when confirmed.
"""

import random
import tkinter as tk
from tkinter import ttk

import appearance as A
from ui import (
    CharacterView,
    Hover,
    MotionButton,
    Portrait,
    Tooltip,
    blend,
    ui_font,
)

COLOR_FIELDS = {"skin": 2, "hair_color": 2, "eye_color": 3}


class Swatch(tk.Canvas):
    """Round color choice; the selected one gets a gold ring and a check."""

    def __init__(self, parent, app, color, label, selected, command, bg):
        super().__init__(
            parent, width=38, height=38, bg=bg, highlightthickness=0, cursor="hand2"
        )
        self.app, self.color, self.selected, self.hover = app, color, selected, 0
        self.command = command
        self.configure(takefocus=True)
        Tooltip(self, label)
        Hover(app, self, self.set_hover, 160, tree=False)
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Return>", lambda e: command())
        self.bind("<space>", lambda e: command())
        self.bind("<Configure>", lambda e: self.draw())

    def set_hover(self, value):
        self.hover = value
        self.draw()

    def select(self, selected):
        self.selected = selected
        self.draw()

    def draw(self):
        self.delete("all")
        p = self.app.motion.palette
        grow = 1.5 * self.hover
        ring = (
            p["accent"]
            if self.selected
            else blend(p["border"], p["strong"], self.hover)
        )
        self.create_oval(
            2, 2, 36, 36, outline=ring, width=2.4 if self.selected else 1.2
        )
        self.create_oval(
            7 - grow, 7 - grow, 31 + grow, 31 + grow, fill=self.color, outline=""
        )
        if self.selected:
            self.create_oval(25, 25, 36, 36, fill=p["primary"], outline=p["surface"])
            self.create_line(
                27.5, 30.5, 29.8, 32.8, 33.6, 28, fill=p["primary_ink"], width=1.6
            )


def flow(frame, widgets, gap=6):
    """Wrap widgets into rows that fit the frame width (no shared columns)."""
    cached = [0]

    def place(event=None):
        width = frame.winfo_width()
        if width < 10 or width == cached[0]:
            return
        cached[0] = width
        x = y = line = 0
        for widget in widgets:
            w, h = widget.winfo_reqwidth(), widget.winfo_reqheight()
            if x and x + w > width:
                x, y = 0, y + line + gap
                line = 0
            widget.place(x=x, y=y)
            x += w + gap
            line = max(line, h)
        frame.configure(height=y + line)

    frame.configure(height=max(w.winfo_reqheight() for w in widgets))
    frame.bind("<Configure>", place)


def open_customizer(app):
    existing = getattr(app, "customizer_win", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return existing
    from app import Scroll

    p = app.motion.palette
    draft = dict(app.character_look())
    win = tk.Toplevel(app.root)
    app.customizer_win = win
    win.title("Seu viajante • RUMO")
    win.configure(bg=app.bg)
    win.transient(app.root)
    win.geometry("1060x730")
    win.minsize(900, 620)
    head = ttk.Frame(win)
    head.pack(fill="x", padx=24, pady=(20, 10))
    ttk.Label(head, text="Seu viajante", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        head,
        text="A aparência é só visual: não muda XP, métricas nem recompensas.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    main = ttk.Frame(win)
    main.pack(fill="both", expand=True, padx=24)
    main.columnconfigure(1, weight=1)
    main.rowconfigure(0, weight=1)
    stage = tk.Frame(
        main, bg=p["surface"], highlightthickness=1, highlightbackground=p["border"]
    )
    stage.grid(row=0, column=0, sticky="ns", padx=(0, 18))
    portrait = Portrait(stage, app, 264, look=draft, bg=p["surface"], ring=False)
    portrait.pack(padx=18, pady=(18, 8))
    equipped = ()
    try:
        equipped = app.journey.character(app.plan).equipped
    except Exception:
        equipped = ()
    figure = CharacterView(
        stage, app, equipped, backdrop=False, bg=p["surface"], look=draft
    )
    figure.configure(width=264, height=300)
    figure.pack(padx=18)
    summary = tk.Label(
        stage,
        text=A.describe(draft),
        bg=p["surface"],
        fg=p["muted"],
        font=ui_font(stage, size=9),
        wraplength=260,
        justify="center",
    )
    summary.pack(padx=18, pady=(4, 16))

    scroll = Scroll(main)
    scroll.grid(row=0, column=1, sticky="nsew")
    scroll.canvas.configure(bg=app.bg)
    body = scroll.body
    controls = {}

    def refresh():
        portrait.set_look(dict(draft))
        figure.look = dict(draft)
        figure.draw()
        summary.configure(text=A.describe(draft))
        for field, widgets in controls.items():
            for key, widget in widgets.items():
                widget.select(key == draft[field])

    def choose(field, key):
        draft[field] = key
        refresh()

    for field, label, options in A.FIELDS:
        section = ttk.Frame(body)
        section.pack(fill="x", pady=(0, 16))
        ttk.Label(section, text=label, style="Heading.TLabel").pack(anchor="w")
        row = ttk.Frame(section)
        row.pack(fill="x", pady=(8, 0))
        widgets = {}
        for option in options:
            key, name = option[0], option[1]
            if field in COLOR_FIELDS:
                widget = Swatch(
                    row,
                    app,
                    option[COLOR_FIELDS[field]],
                    name,
                    key == draft[field],
                    lambda f=field, k=key: choose(f, k),
                    app.bg,
                )
            else:
                widget = MotionButton(
                    row,
                    text=name,
                    style="Chip.TButton",
                    selected=key == draft[field],
                    height=32,
                    command=lambda f=field, k=key: choose(f, k),
                )
            widgets[key] = widget
        flow(row, list(widgets.values()))
        controls[field] = widgets

    def randomize():
        for field, _, options in A.FIELDS:
            draft[field] = random.choice(A.ids(options))
        refresh()

    def reset():
        draft.update(A.DEFAULT)
        refresh()

    def save():
        app.store.set_pref(A.PREFERENCE, dict(draft))
        win.destroy()
        app.refresh()
        app.toast.show("Aparência salva", A.describe(draft), "sparkles", "success")

    footer = ttk.Frame(win)
    footer.pack(fill="x", padx=24, pady=16)
    MotionButton(footer, text="Aleatório", icon="sparkles", command=randomize).pack(
        side="left"
    )
    MotionButton(
        footer,
        text="Restaurar padrão",
        icon="rotate-ccw",
        style="Ghost.TButton",
        command=reset,
    ).pack(side="left", padx=8)
    MotionButton(
        footer,
        text="Salvar aparência",
        icon="check",
        style="Accent.TButton",
        command=save,
    ).pack(side="right")
    MotionButton(footer, text="Cancelar", command=win.destroy).pack(
        side="right", padx=8
    )
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Control-Return>", lambda e: save())
    app.motion.reveal(win)
    return win
