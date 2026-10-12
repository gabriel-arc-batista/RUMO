"""Shared building blocks for the reorganized screens.

Lists with hairlines instead of boxes, a segmented control instead of rows of
equal buttons, action menus next to the object they act on and quiet surfaces.
Everything reads the active palette; nothing here touches the database.
"""

import tkinter as tk
from tkinter import ttk

from theme import ICON
from ui import MotionButton, Tooltip, background_of, blend, glyph, rounded, ui_font


def palette(app):
    return app.motion.palette


def bg_of(parent, app):
    return background_of(parent) or app.bg


def label(parent, app, text, size=10, weight="normal", tone="fg", **kwargs):
    """tk.Label on the parent's own background, with a palette color role."""
    p = palette(app)
    return tk.Label(
        parent,
        text=text,
        bg=kwargs.pop("bg", bg_of(parent, app)),
        fg=p.get(tone, tone),
        font=ui_font(parent, size=size, weight=weight),
        anchor=kwargs.pop("anchor", "w"),
        justify=kwargs.pop("justify", "left"),
        **kwargs,
    )


def icon_label(parent, app, name, size=12, tone="muted", **kwargs):
    p = palette(app)
    return tk.Label(
        parent,
        text=glyph(parent, name),
        bg=kwargs.pop("bg", bg_of(parent, app)),
        fg=p.get(tone, tone),
        font=ui_font(parent, ICON, size),
        **kwargs,
    )


def wrapping(widget, margin=4, minimum=120):
    """Keep wraplength equal to the widget's real width; no clipped text."""

    def fit(event):
        width = max(minimum, event.width - margin)
        if int(float(widget.cget("wraplength") or 0)) != width:
            widget.configure(wraplength=width)

    widget.bind("<Configure>", fit, add="+")
    return widget


class Surface(tk.Frame):
    """A quiet region: one fill, no border. Elevation is declared once."""

    def __init__(self, parent, app, padding=(20, 18), tone="surface"):
        p = palette(app)
        super().__init__(parent, bg=p[tone], highlightthickness=0)
        self.body = tk.Frame(self, bg=p[tone])
        self.body.pack(fill="both", expand=True, padx=padding[0], pady=padding[1])
        self.body._panel = True


class Card(tk.Canvas):
    """Rounded quiet region: one fill, no outline. ``stretch`` fills the cell."""

    def __init__(
        self, parent, app, padding=(22, 20), tone="surface", stretch=False, radius=14
    ):
        p = palette(app)
        super().__init__(parent, bg=bg_of(parent, app), highlightthickness=0, height=60)
        self.app = app
        self.tone = tone
        self.padding = padding
        self.radius = radius
        self.stretch = stretch
        self.body = tk.Frame(self, bg=p[tone])
        self.body._panel = True
        self.window = self.create_window(
            padding[0], padding[1], window=self.body, anchor="nw"
        )
        self.bind("<Configure>", self.resize)
        self.body.bind("<Configure>", self.resize)

    def resize(self, event=None):
        px, py = self.padding
        width = max(1, self.winfo_width() - px * 2)
        if int(float(self.itemcget(self.window, "width"))) != width:
            self.itemconfigure(self.window, width=width)
        height = self.body.winfo_reqheight() + py * 2
        if self.winfo_reqheight() != height:
            self.configure(height=height)
        if self.stretch:
            height = max(height, self.winfo_height())
            body = max(1, height - py * 2)
            if int(float(self.itemcget(self.window, "height"))) != body:
                self.itemconfigure(self.window, height=body)
        self.delete("fill")
        fill = palette(self.app)[self.tone]
        rounded(
            self,
            0,
            0,
            self.winfo_width() - 1,
            height - 1,
            self.radius,
            fill=fill,
            outline=fill,
            tags="fill",
        )
        self.tag_lower("fill")


class Section(tk.Frame):
    """Heading that needs no box: title, optional count, help and actions."""

    def __init__(self, parent, app, title, count=None, help_text=None, size=13):
        super().__init__(parent, bg=bg_of(parent, app))
        self.app = app
        label(self, app, title, size=size, weight="bold").pack(side="left")
        if count is not None:
            label(self, app, str(count), size=size, tone="faint").pack(
                side="left", padx=(8, 0)
            )
        if help_text:
            help_button(self, app, title, help_text).pack(side="left", padx=(4, 0))
        self.actions = tk.Frame(self, bg=bg_of(parent, app))
        self.actions.pack(side="right")

    def action(self, text, command, icon=None, style="Ghost.TButton", **kwargs):
        button = MotionButton(
            self.actions,
            text=text,
            icon=icon,
            style=style,
            height=kwargs.pop("height", 32),
            command=command,
            **kwargs,
        )
        button.pack(side="right", padx=(6, 0))
        return button

    def menu(self, text, items, icon="ellipsis"):
        button = ActionMenu(self.actions, self.app, items, text=text, icon=icon)
        button.pack(side="right", padx=(6, 0))
        return button


def help_button(parent, app, title, text):
    """Small question mark: the explanation is there when wanted, not on screen."""
    from app import messagebox

    button = MotionButton(
        parent,
        icon="circle-help",
        style="Ghost.TButton",
        height=28,
        command=lambda: messagebox.showinfo(title, text, parent=app.root),
    )
    Tooltip(button, "Como funciona")
    return button


class ActionMenu(MotionButton):
    """Button that opens a short native menu of related actions.

    ``items``: (label, command) pairs; ``None`` draws a separator. A third
    element ``"danger"`` paints the entry in the error color.
    """

    def __init__(self, parent, app, items, text="", icon="ellipsis", **kwargs):
        self.app = app
        self.items = items
        kwargs.setdefault("style", "Ghost.TButton" if not text else "TButton")
        kwargs.setdefault("height", 32)
        super().__init__(parent, text=text, icon=icon, command=self.open, **kwargs)
        if not text:
            Tooltip(self, "Mais ações")

    def open(self):
        p = palette(self.app)
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=p["raised"],
            fg=p["fg"],
            activebackground=p["selected"],
            activeforeground=p["accent"],
            disabledforeground=p["faint"],
            bd=1,
            relief="flat",
            font=ui_font(self, size=10),
        )
        for item in self.items:
            if item is None:
                menu.add_separator()
                continue
            name, command, *tone = item
            menu.add_command(
                label="  " + name + "  ",
                command=command,
                foreground=p["error"] if tone and tone[0] == "danger" else p["fg"],
            )
        try:
            menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        finally:
            menu.grab_release()


class Segmented(tk.Canvas):
    """One control for mutually exclusive views: Hoje · Atrasadas · Próximas."""

    def __init__(self, parent, app, options, value, command, height=34):
        self.app = app
        self.options = list(options)
        self.value = value
        self.command = command
        self.font = ui_font(parent, size=10)
        self.bold = ui_font(parent, size=10, weight="bold")
        self.count_font = ui_font(parent, size=9)
        self.hover = None
        self.focused = False
        widths = [self.measure(option) for option in self.options]
        super().__init__(
            parent,
            width=sum(widths) + 6,
            height=height,
            bg=bg_of(parent, app),
            highlightthickness=0,
            takefocus=True,
            cursor="hand2",
        )
        self.widths = widths
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", lambda e: self.set_hover(None))
        self.bind("<Button-1>", self.on_click)
        self.bind("<Left>", lambda e: self.step(-1))
        self.bind("<Right>", lambda e: self.step(1))
        self.bind("<FocusIn>", lambda e: self.set_focus(True))
        self.bind("<FocusOut>", lambda e: self.set_focus(False))

    def measure(self, option):
        key, text, *count = option
        width = self.bold.measure(text) + 28
        if count and count[0] not in (None, ""):
            width += self.count_font.measure(str(count[0])) + 8
        return width

    def index_at(self, x):
        left = 3
        for index, width in enumerate(self.widths):
            if left <= x < left + width:
                return index
            left += width
        return None

    def on_motion(self, event):
        self.set_hover(self.index_at(event.x))

    def set_hover(self, index):
        if index != self.hover:
            self.hover = index
            self.draw()

    def set_focus(self, value):
        self.focused = value
        self.draw()

    def on_click(self, event):
        index = self.index_at(event.x)
        if index is not None:
            self.choose(self.options[index][0])

    def step(self, direction):
        keys = [option[0] for option in self.options]
        index = keys.index(self.value) if self.value in keys else 0
        self.choose(keys[(index + direction) % len(keys)])

    def choose(self, key):
        if key == self.value:
            return
        self.value = key
        self.draw()
        self.command(key)

    def draw(self):
        self.delete("all")
        p = palette(self.app)
        h = self.winfo_height()
        total = sum(self.widths) + 6
        rounded(
            self,
            0,
            0,
            total - 1,
            h - 1,
            (h - 1) / 2,
            fill=p["raised"],
            outline=p["accent"] if self.focused else p["border"],
        )
        left = 3
        for index, (option, width) in enumerate(zip(self.options, self.widths)):
            key, text, *count = option
            selected = key == self.value
            if selected or index == self.hover:
                rounded(
                    self,
                    left,
                    3,
                    width,
                    h - 7,
                    (h - 7) / 2,
                    fill=p["tint"] if selected else p["hover"],
                    outline="",
                )
            ink = (
                p["accent"]
                if selected
                else (p["fg"] if index == self.hover else p["muted"])
            )
            font = self.bold if selected else self.font
            x = left + 14
            self.create_text(x, h / 2, text=text, anchor="w", fill=ink, font=font)
            if count and count[0] not in (None, ""):
                x += font.measure(text) + 7
                self.create_text(
                    x,
                    h / 2,
                    text=str(count[0]),
                    anchor="w",
                    fill=p["accent"] if selected else p["faint"],
                    font=self.count_font,
                )
            left += width


class Row(tk.Frame):
    """List row: leading mark, title and detail, trailing slot; hover and select.

    Rows are separated by a hairline, never boxed. ``on_open`` runs on click,
    Return and double click.
    """

    def __init__(
        self,
        parent,
        app,
        title,
        detail="",
        on_open=None,
        selected=False,
        separator=True,
        pady=10,
    ):
        p = palette(app)
        self.app = app
        self.base = bg_of(parent, app)
        self.selected = selected
        self.on_open = on_open
        super().__init__(
            parent,
            bg=self.base,
            cursor="hand2" if on_open else "",
            takefocus=bool(on_open),
            highlightthickness=1 if on_open else 0,
            highlightbackground=self.base,
            highlightcolor=p["accent"],
        )
        if on_open:
            self.bind("<Return>", lambda e: on_open())
            self.bind("<space>", lambda e: on_open())
        self.line = tk.Frame(self, height=1, bg=p["border"] if separator else self.base)
        self.line.pack(side="bottom", fill="x")
        self.inner = tk.Frame(self, bg=self.base)
        self.inner.pack(fill="x", padx=10, pady=pady)
        self.lead = tk.Frame(self.inner, bg=self.base)
        self.lead.pack(side="left", anchor="n")
        self.trail = tk.Frame(self.inner, bg=self.base)
        self.trail.pack(side="right", anchor="center")
        self.texts = tk.Frame(self.inner, bg=self.base)
        self.texts.pack(side="left", fill="x", expand=True)
        self.title = wrapping(label(self.texts, app, title, size=10))
        self.title.pack(fill="x")
        self.detail = None
        if detail:
            self.detail = wrapping(label(self.texts, app, detail, size=9, tone="muted"))
            self.detail.pack(fill="x", pady=(2, 0))
        self.bind_all_children()
        self.paint(p["selected"] if selected else self.base)

    def bind_all_children(self):
        for widget in self.paintable():
            widget.bind("<Enter>", lambda e: self.hover(True), add="+")
            widget.bind("<Leave>", lambda e: self.hover(False), add="+")
            if self.on_open:
                widget.bind("<Button-1>", lambda e: self.on_open(), add="+")

    def paintable(self):
        widgets = [self, self.inner]

        def walk(holder):
            widgets.append(holder)
            for child in holder.winfo_children():
                if isinstance(child, tk.Frame):
                    walk(child)
                elif isinstance(child, tk.Label):
                    widgets.append(child)

        for holder in (self.lead, self.texts, self.trail):
            walk(holder)
        return widgets

    def refresh_bindings(self):
        """Call after adding widgets to lead/trail so they share hover and paint."""
        self.bind_all_children()
        self.paint(self._color)

    def hover(self, inside):
        from ui import pointer_inside

        p = palette(self.app)
        if not inside and pointer_inside(self):
            return
        if self.selected:
            target = p["selected"]
        else:
            target = p["hover"] if inside else self.base
        self.paint(target)

    def paint(self, color):
        self._color = color
        if int(self.cget("highlightthickness")):
            self.configure(highlightbackground=color)
        for widget in self.paintable():
            if isinstance(widget, (tk.Label, tk.Frame)) and widget is not self.line:
                try:
                    widget.configure(bg=color)
                except tk.TclError:
                    pass
        for widget in self.trail.winfo_children() + self.lead.winfo_children():
            if isinstance(widget, MotionButton):
                widget.surround = color
                widget.configure(bg=color)
                if widget.role == "Ghost.TButton":
                    widget.current = color if not widget.hover else widget.current
                widget.draw()

    def select(self, value):
        self.selected = value
        p = palette(self.app)
        self.paint(p["selected"] if value else self.base)


def dot(parent, app, tone, size=10):
    """Small filled status mark; always paired with a word, never alone."""
    p = palette(app)
    canvas = tk.Canvas(
        parent, width=size, height=size, bg=bg_of(parent, app), highlightthickness=0
    )
    canvas.create_oval(1, 1, size - 1, size - 1, fill=p.get(tone, tone), outline="")
    return canvas


class Stat(tk.Frame):
    """Number with its label underneath; groups of these replace metric cards."""

    def __init__(self, parent, app, value, caption, tip=None, size=17, tone="fg"):
        super().__init__(parent, bg=bg_of(parent, app))
        label(self, app, value, size=size, weight="bold", tone=tone).pack(anchor="w")
        label(self, app, caption, size=9, tone="muted").pack(anchor="w", pady=(1, 0))
        if tip:
            Tooltip(self, tip)


def stat_row(parent, app, stats, gap=36):
    """A line of stats aligned left. ``stats``: (value, caption[, tip]) tuples."""
    row = tk.Frame(parent, bg=bg_of(parent, app))
    for index, (value, caption, *tip) in enumerate(stats):
        Stat(row, app, value, caption, tip[0] if tip else None).pack(
            side="left", padx=(0 if index == 0 else gap, 0)
        )
    return row


def empty(parent, app, icon, title, text, actions=(), width=440):
    """Empty state that teaches: what is missing and the one action that fixes it."""
    p = palette(app)
    box = tk.Frame(parent, bg=bg_of(parent, app))
    if glyph(box, icon):
        icon_label(box, app, icon, size=22, tone="faint").pack(pady=(4, 8))
    label(box, app, title, size=12, weight="bold", anchor="center").pack()
    message = label(
        box,
        app,
        text,
        size=10,
        tone="muted",
        wraplength=width,
        justify="center",
        anchor="center",
    )
    message.pack(fill="x", pady=(4, 12))
    message.bind(
        "<Configure>",
        lambda e: message.configure(wraplength=max(160, min(width, e.width - 24))),
        add="+",
    )
    row = tk.Frame(box, bg=bg_of(parent, app))
    row.pack()
    for index, (name, command, *icon_name) in enumerate(actions):
        MotionButton(
            row,
            text=name,
            icon=icon_name[0] if icon_name else None,
            style="Accent.TButton" if index == 0 else "Ghost.TButton",
            command=command,
        ).pack(side="left", padx=4)
    return box


def placeholder(entry, app, text):
    """Hint inside an empty entry; hidden as soon as there is text or focus."""
    p = palette(app)
    hint = tk.Label(
        entry,
        text=text,
        bg=p["raised"],
        fg=p["faint"],
        font=ui_font(entry, size=10),
        cursor="xterm",
    )

    def update(*args):
        if entry.get() or entry.focus_get() == entry:
            hint.place_forget()
        else:
            hint.place(x=12, rely=0.5, anchor="w")

    hint.bind("<Button-1>", lambda e: entry.focus_set())
    entry.bind("<FocusIn>", update, add="+")
    entry.bind("<FocusOut>", update, add="+")
    entry.bind("<KeyRelease>", update, add="+")
    update()
    return update


def blend_with(app, role, toward, fraction):
    p = palette(app)
    return blend(p[role], p[toward], fraction)
