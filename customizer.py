"""Character creator: appearance options with a live portrait and full-body preview.

Appearance is purely visual: it never changes XP, metrics or rewards. The look
is saved as one preference (``appearance.PREFERENCE``) only when confirmed.
"""

import random
import tkinter as tk
from tkinter import ttk, messagebox

import appearance as A
from ui import (
    Hover,
    MotionButton,
    Portrait,
    Tooltip,
    blend,
    ui_font,
    load_image,
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


class AssetChoice(tk.Canvas):
    """A small real-asset thumbnail, retained only while its category is visible."""

    def __init__(self, parent, app, field, key, label, selected, command):
        super().__init__(
            parent,
            width=116,
            height=122,
            bg=app.bg,
            highlightthickness=0,
            cursor="hand2",
            takefocus=True,
        )
        self.app, self.selected, self.command = app, selected, command
        self.image = load_image(app, f"character/look/thumbnails/{field}-{key}.png")
        self.label = label
        Tooltip(self, label)
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Return>", lambda e: command())
        self.bind("<space>", lambda e: command())
        self.bind("<FocusIn>", lambda e: self.draw())
        self.bind("<FocusOut>", lambda e: self.draw())
        self.draw()

    def select(self, selected):
        self.selected = selected
        self.draw()

    def draw(self):
        self.delete("all")
        p = self.app.motion.palette
        color = (
            p["accent"] if self.selected or self.focus_get() == self else p["border"]
        )
        self.create_rectangle(
            2, 2, 114, 120, outline=color, width=2 if self.selected else 1
        )
        self.create_image(58, 48, image=self.image)
        self.create_text(
            58,
            104,
            text=self.label,
            width=108,
            fill=p["fg"],
            font=ui_font(self, size=9),
            justify="center",
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
    ttk.Label(stage, text="Retrato • N. Erebus • CC0", style="Muted.TLabel").pack(
        pady=(0, 12)
    )
    info = tk.Label(
        stage,
        text=(
            "Este conjunto contém retratos.\nEquipamentos e montarias continuam\nno inventário, sem sobreposição visual."
        ),
        bg=p["surface"],
        fg=p["muted"],
        font=ui_font(stage, size=9),
        wraplength=260,
        justify="center",
    )
    info.pack(padx=18, pady=16)
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

    editor = ttk.Frame(main)
    editor.grid(row=0, column=1, sticky="nsew")
    ttk.Label(editor, text="Nome do personagem", style="Heading.TLabel").pack(
        anchor="w"
    )
    profile = app.store.one(
        "SELECT name FROM rpg_characters WHERE plan_id=?", (app.plan,)
    )
    name = tk.StringVar(value=profile["name"] if profile else "Viajante")
    entry = ttk.Entry(editor, textvariable=name)
    entry.pack(fill="x", pady=(6, 14))
    categories = ttk.Combobox(
        editor, state="readonly", values=[label for _, label, _ in A.FIELDS]
    )
    categories.current(0)
    categories.pack(fill="x", pady=(0, 12))
    scroll = Scroll(editor)
    scroll.pack(fill="both", expand=True)
    scroll.canvas.configure(bg=app.bg)
    body = scroll.body
    controls = {}
    win.character_categories = categories
    win.character_name = name

    def refresh():
        portrait.set_look(dict(draft))
        summary.configure(text=A.describe(draft))
        for field, widgets in controls.items():
            for key, widget in widgets.items():
                widget.select(key == draft[field])

    def choose(field, key):
        draft[field] = key
        if field == "sex":
            draft["face"] = "rosto-4" if key == "feminino" else "rosto-1"
        refresh()

    def show_category(event=None):
        # Destroy the previous grid and its PhotoImage references; only the
        # active category is loaded, never the complete catalogue.
        for child in body.winfo_children():
            child.destroy()
        controls.clear()
        field, label, options = A.FIELDS[categories.current()]
        ttk.Label(body, text=label, style="Heading.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        row = ttk.Frame(body)
        row.pack(fill="x")
        widgets = {}
        for option in options:
            key, title = option[:2]
            command = lambda f=field, k=key: choose(f, k)
            if field in COLOR_FIELDS:
                widget = Swatch(
                    row,
                    app,
                    option[COLOR_FIELDS[field]],
                    title,
                    key == draft[field],
                    command,
                    app.bg,
                )
            else:
                widget = AssetChoice(
                    row, app, field, key, title, key == draft[field], command
                )
            widgets[key] = widget
        flow(row, list(widgets.values()))
        controls[field] = widgets
        scroll.canvas.yview_moveto(0)

    categories.bind("<<ComboboxSelected>>", show_category)
    show_category()

    def randomize():
        for field, _, options in A.FIELDS:
            draft[field] = random.choice(A.ids(options))
        refresh()

    def reset():
        draft.update(A.DEFAULT)
        refresh()

    def save():
        from character_profile import save_character

        try:
            save_character(app.store, app.plan, dict(draft), name.get())
        except ValueError as error:
            messagebox.showerror("Confira o personagem", str(error), parent=win)
            return
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

    def release_images(event):
        if event.widget is win:
            # Visible widgets retain their own layers. Discard unused editor
            # images immediately instead of leaving an idle cache behind.
            for key in list(app.images):
                if "/look/" in key:
                    app.images.pop(key, None)
            app.customizer_win = None

    win.bind("<Destroy>", release_images, add="+")
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Control-Return>", lambda e: save())
    app.motion.reveal(win)
    return win
