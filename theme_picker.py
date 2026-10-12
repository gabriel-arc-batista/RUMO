"""Theme gallery: each card previews the app in that theme's own colors."""

import tkinter as tk
from tkinter import ttk

from theme import FONT, THEMES, resolve_theme
from ui import MotionButton, blend, rounded, ui_font


class ThemeCard(tk.Canvas):
    def __init__(self, parent, app, name, current, on_pick):
        super().__init__(parent, height=128, width=320, bg=app.bg, highlightthickness=0)
        self.app = app
        self.name = name
        self.theme = THEMES[name]
        self.current = current
        self.hover = 0
        self.on_pick = on_pick
        self.configure(cursor="hand2", takefocus=True)
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Enter>", lambda e: self.transition(1))
        self.bind("<Leave>", lambda e: self.transition(0))
        self.bind("<Button-1>", lambda e: on_pick(name))
        self.bind("<Return>", lambda e: on_pick(name))
        self.bind("<space>", lambda e: on_pick(name))
        self.bind("<FocusIn>", lambda e: self.transition(1))
        self.bind("<FocusOut>", lambda e: self.transition(0))

    def transition(self, target):
        start = self.hover
        self.app.motion.animate(
            self, lambda t: self.set_hover(start + (target - start) * t), 200
        )

    def set_hover(self, value):
        self.hover = value
        self.draw()

    def draw(self):
        self.delete("all")
        t = self.theme["palette"]
        a = self.app.motion.palette
        w, h = self.winfo_width(), self.winfo_height()
        lift = 3 * self.hover
        ring = (
            a["accent"]
            if self.current
            else blend(a["border"], t["primary"], self.hover)
        )
        rounded(
            self,
            1,
            1 + 3 - lift,
            w - 3,
            h - 6,
            14,
            fill=t["bg"],
            outline=ring,
            width=2 if self.current or self.hover > 0.5 else 1,
        )
        y = 4 - lift
        # Miniature window: sidebar, card with text lines, gold button, companion color.
        rounded(
            self, 12, y + 12, 118, h - 30, 9, fill=t["surface"], outline=t["border"]
        )
        self.create_rectangle(13, y + 13, 40, y + h - 19, fill=t["sidebar"], outline="")
        for row, color in enumerate([t["primary"], t["muted"], t["muted"], t["muted"]]):
            self.create_rectangle(
                19,
                y + 22 + row * 12,
                34,
                y + 26 + row * 12,
                fill=color,
                outline="",
            )
        self.create_rectangle(48, y + 22, 112, y + 27, fill=t["fg"], outline="")
        self.create_rectangle(48, y + 33, 96, y + 37, fill=t["muted"], outline="")
        rounded(self, 48, y + 46, 62, 5, 2.5, fill=t["track"], outline="")
        rounded(self, 48, y + 46, 40, 5, 2.5, fill=t["primary"], outline="")
        rounded(self, 48, y + 58, 58, 5, 2.5, fill=t["track"], outline="")
        rounded(self, 48, y + 58, 30, 5, 2.5, fill=t["secondary"], outline="")
        rounded(self, 48, y + 72, 40, 16, 8, fill=t["primary"], outline="")
        self.create_oval(96, y + 74, 108, y + 86, fill=t["secondary"], outline="")
        x = 146
        self.create_text(
            x,
            y + 26,
            text=self.name,
            anchor="w",
            fill=t["fg"],
            font=ui_font(self, FONT, 12, "bold"),
        )
        self.create_text(
            x,
            y + 48,
            text=self.theme["about"],
            anchor="nw",
            width=max(80, w - x - 16),
            fill=t["muted"],
            font=ui_font(self, FONT, 9),
        )
        for index, key in enumerate(["bg", "primary", "secondary"]):
            cx = x + 8 + index * 22
            self.create_oval(
                cx - 7,
                y + h - 34,
                cx + 7,
                y + h - 20,
                fill=t[key],
                outline=t["strong"],
            )
        label = "Em uso" if self.current else ""
        self.create_text(
            w - 16,
            y + h - 27,
            text=label,
            anchor="e",
            fill=t["accent"] if self.current else t["muted"],
            font=ui_font(self, FONT, 8, "bold"),
        )


def open_theme_picker(app, reveal=True):
    preference = app.store.pref("theme", "Escuro")
    current = None if preference == "Sistema" else resolve_theme(preference)
    win = tk.Toplevel(app.root)
    win.title("Temas • RUMO")
    win.configure(bg=app.bg)
    win.transient(app.root)
    win.geometry(
        f"{min(1010, app.root.winfo_screenwidth() - 80)}x"
        f"{min(760, app.root.winfo_screenheight() - 120)}"
    )
    win.minsize(560, 480)
    head = ttk.Frame(win)
    head.pack(fill="x", padx=24, pady=(22, 4))
    ttk.Label(head, text="Temas", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        head,
        text="Cada tema combina três cores: o fundo, a cor principal e uma companheira. Clique para aplicar.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(2, 0))
    footer = ttk.Frame(win)
    footer.pack(side="bottom", fill="x", padx=24, pady=(0, 18))
    from app import Scroll

    area = Scroll(win)
    area.pack(fill="both", expand=True, padx=(24, 8), pady=12)
    area.canvas.configure(bg=app.bg)

    def pick(name):
        app.store.set_pref("theme", name)
        app.apply_theme()
        app.build_shell()
        app.refresh()
        app.motion.reveal(app.root)
        app.root.after(30, lambda: open_theme_picker(app, reveal=False))

    groups = []
    for title, dark in [("Escuros", True), ("Claros", False)]:
        ttk.Label(area.body, text=title, style="Heading.TLabel").pack(
            anchor="w", pady=(6, 8)
        )
        grid = ttk.Frame(area.body)
        grid.pack(fill="x", padx=(0, 12), pady=(0, 10))
        cards = [
            ThemeCard(grid, app, name, name == current, pick)
            for name, theme in THEMES.items()
            if theme["dark"] == dark
        ]
        groups.append((grid, cards))

    def reflow(event=None):
        width = area.body.winfo_width()
        columns = max(1, min(3, width // 300))
        for grid, cards in groups:
            if getattr(grid, "_columns", None) == columns:
                continue
            grid._columns = columns
            for column in range(3):
                grid.columnconfigure(
                    column,
                    weight=1 if column < columns else 0,
                    uniform="theme" if column < columns else "",
                )
            for index, card in enumerate(cards):
                column = index % columns
                card.grid(
                    row=index // columns,
                    column=column,
                    sticky="nsew",
                    padx=(0 if column == 0 else 6, 0 if column == columns - 1 else 6),
                    pady=(0, 10),
                )

    area.body.bind("<Configure>", reflow, add="+")
    app.motion.idle(area.body, reflow)
    MotionButton(
        footer,
        text="Seguir o sistema",
        icon="sun",
        style="Chip.TButton",
        selected=preference == "Sistema",
        command=lambda: pick("Sistema"),
    ).pack(side="left")
    ttk.Label(
        footer,
        text="Norte Dourado à noite, Aurora de dia",
        style="Muted.TLabel",
    ).pack(side="left", padx=10)
    MotionButton(footer, text="Fechar", command=win.destroy).pack(side="right")
    win.bind("<Escape>", lambda e: win.destroy())
    if reveal:
        app.motion.reveal(win)
    return win
