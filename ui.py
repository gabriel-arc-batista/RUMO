"""Small native visual components. Animations run only during interactions."""

import tkinter as tk
import time
import os
import ctypes
from tkinter import ttk
from tkinter import font as tkfont


def load_fonts(root, assets):
    if os.name == "nt" and not getattr(root, "_fonts_loaded", False):
        add = ctypes.windll.gdi32.AddFontResourceExW
        add.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        for path in (assets / "fonts").glob("Inter-*.ttf"):
            add(str(path), 0x10, None)
        root._fonts_loaded = True
    return "Inter" if "Inter" in tkfont.families(root) else "Bahnschrift"


def blend(a, b, fraction):
    channels = [
        round(int(a[i : i + 2], 16) * (1 - fraction) + int(b[i : i + 2], 16) * fraction)
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{channel:02x}" for channel in channels)


class Motion:
    def __init__(self, root):
        self.root = root
        self.enabled = True
        self.jobs = {}
        self.palette = {}
        self.free_styles = []
        self.style_count = 0

    def watch(self, widget):
        if getattr(widget, "_motion_watched", False):
            return
        widget._motion_watched = True
        widget.bind(
            "<Destroy>",
            lambda e: self.cancel(widget) if e.widget == widget else None,
            add="+",
        )

    def idle(self, widget, callback, channel="idle"):
        self.watch(widget)
        key = (widget, channel)

        def run():
            self.jobs.pop(key, None)
            if widget.winfo_exists():
                callback()

        previous = self.jobs.pop(key, None)
        if previous:
            self.root.after_cancel(previous)
        self.jobs[key] = self.root.after_idle(run)

    def cancel(self, widget):
        for key in list(self.jobs):
            if key == widget or isinstance(key, tuple) and key[0] == widget:
                try:
                    self.root.after_cancel(self.jobs.pop(key))
                except tk.TclError:
                    pass

    def animate(self, widget, paint, milliseconds=280, channel=None):
        self.watch(widget)
        key = widget if channel is None else (widget, channel)
        previous = self.jobs.pop(key, None)
        if previous:
            try:
                self.root.after_cancel(previous)
            except tk.TclError:
                pass
        start = time.monotonic()

        def step():
            self.jobs.pop(key, None)
            if not widget.winfo_exists():
                return
            t = (
                min(1, (time.monotonic() - start) * 1000 / milliseconds)
                if self.enabled
                else 1
            )
            paint(1 - (1 - t) ** 3)
            if t < 1:
                self.jobs[key] = self.root.after(25, step)

        step()

    def reveal(self, window):
        try:
            window.attributes("-alpha", 0 if self.enabled else 1)
            window.update_idletasks()
            if os.name == "nt":
                get_parent = ctypes.windll.user32.GetParent
                get_parent.argtypes = [ctypes.c_void_p]
                get_parent.restype = ctypes.c_void_p
                hwnd = get_parent(window.winfo_id())
                set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
                set_attribute.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_uint,
                    ctypes.c_void_p,
                    ctypes.c_uint,
                ]
                for attribute, color in [
                    (35, self.palette.get("bg", "#090909")),
                    (36, self.palette.get("fg", "#EDEDED")),
                    (34, self.palette.get("border", "#303033")),
                ]:
                    value = ctypes.c_uint(
                        int(color[1:3], 16)
                        | (int(color[3:5], 16) << 8)
                        | (int(color[5:7], 16) << 16)
                    )
                    set_attribute(hwnd, attribute, ctypes.byref(value), 4)
            width, height = window.winfo_width(), window.winfo_height()
            if window != self.root:
                x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
                y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
                x = max(0, min(x, window.winfo_screenwidth() - width - 10))
                y = max(0, min(y, window.winfo_screenheight() - height - 65))
            else:
                x, y = window.winfo_x(), window.winfo_y()

            def paint(t):
                window.attributes("-alpha", t)
                if window != self.root:
                    window.geometry(f"{width}x{height}+{x}+{y+round(24*(1-t))}")

            self.animate(window, paint, 380)
            window.bind(
                "<Destroy>",
                lambda e: self.cancel(window) if e.widget == window else None,
                add="+",
            )
        except tk.TclError:
            pass


class MotionButton(tk.Canvas):
    """Rounded vector button; redraws this control only, with keyboard focus."""

    def __init__(self, parent, **kwargs):
        self.motion = getattr(parent.winfo_toplevel()._root(), "_motion", None)
        self.role = kwargs.pop("style", "TButton")
        self.text = kwargs.pop("text", "")
        self.command = kwargs.pop("command", None)
        width = kwargs.pop("width", None)
        self.disabled = kwargs.pop("state", "normal") == "disabled"
        self.selected = False
        self.hover = 0
        self.press = 0
        self.focused = False
        self.font = tkfont.Font(parent, family="Inter", size=9)
        requested = (
            max(64, self.font.measure(self.text) + 32)
            if width is None
            else max(40, int(width) * 8 + 16)
        )
        try:
            bg = ttk.Style(parent).lookup(
                parent.cget("style") or "TFrame", "background"
            )
        except tk.TclError:
            bg = parent.cget("bg")
        height = kwargs.pop("height", 40)
        super().__init__(
            parent,
            width=requested,
            height=height,
            bg=bg or "#090909",
            highlightthickness=0,
            takefocus=True,
            cursor="hand2",
            **kwargs,
        )
        self.current = self.colors()[0]
        self.bind("<Enter>", lambda e: self.transition(True), add="+")
        self.bind("<Leave>", lambda e: self.transition(False), add="+")
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Return>", lambda e: self.invoke())
        self.bind("<space>", lambda e: self.invoke())
        self.bind("<FocusIn>", lambda e: self.set_focus(True))
        self.bind("<FocusOut>", lambda e: self.set_focus(False))
        self.bind("<Destroy>", self.cleanup, add="+")

    def colors(self):
        p = (
            self.motion.palette
            if self.motion
            else dict(
                bg="#090909",
                surface="#151515",
                hover="#302719",
                selected="#2C2416",
                accent="#D6B467",
                fg="#F4F0E8",
                muted="#A6A199",
            )
        )
        if self.role == "Accent.TButton":
            return "#D6B467", "#F2D28B", "#17130A"
        if self.role == "Nav.TButton":
            return (
                (p["selected"] if self.selected else p["bg"]),
                p["hover"],
                (p["accent"] if self.selected else p["muted"]),
            )
        return p["surface"], p["hover"], p["fg"]

    def paint(self, color):
        self.current = color
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        inset = 2 + self.press * 2
        y = 3 - 2 * self.hover + self.press * 2
        p = self.motion.palette if self.motion else {}
        border = (
            p.get("accent", "#D6B467") if self.focused else p.get("border", "#303033")
        )
        if self.role == "Nav.TButton" and not self.focused:
            border = self.current
        rounded(
            self,
            inset,
            y,
            max(1, w - inset * 2),
            h - 6,
            8,
            fill=self.current,
            outline=border,
            width=1,
        )
        if self.role == "Nav.TButton" and self.selected:
            self.create_line(5, 12, 5, h - 12, fill=p.get("accent", "#D6B467"), width=3)
        color = self.colors()[2] if not self.disabled else "#817A6B"
        x = 18 if self.role == "Nav.TButton" else w / 2
        self.create_text(
            x,
            h / 2 - 2 * self.hover + self.press * 2,
            text=self.text,
            anchor="w" if self.role == "Nav.TButton" else "center",
            fill=color,
            font=self.font,
        )

    def configure(self, cnf=None, **kwargs):
        changed = False
        for name in ["text", "command"]:
            if name in kwargs:
                value = kwargs.pop(name)
                if getattr(self, name) != value:
                    setattr(self, name, value)
                    changed = True
        if "state" in kwargs:
            disabled = kwargs.pop("state") == "disabled"
            if disabled != self.disabled:
                self.disabled = disabled
                changed = True
        result = super().configure(cnf, **kwargs)
        if changed:
            self.draw()
        return result

    config = configure

    def cget(self, key):
        if key in ["text", "command"]:
            return getattr(self, key)
        if key == "state":
            return "disabled" if self.disabled else "normal"
        return super().cget(key)

    def set_focus(self, value):
        self.focused = value
        self.draw()

    def on_press(self, event):
        if self.disabled:
            return
        self.focus_set()
        self.press = 1
        self.draw()

    def on_release(self, event):
        self.press = 0
        self.draw()
        if 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()

    def invoke(self):
        if not self.disabled and self.command:
            return self.command()

    def transition(self, hover):
        if self.disabled:
            return
        start = self.current
        target = self.colors()[1 if hover else 0]
        start_hover = self.hover
        if start.lower() == target.lower():
            if self.motion:
                self.motion.cancel(self)
            return

        def paint(t):
            self.hover = start_hover + (int(hover) - start_hover) * t
            self.paint(blend(start, target, t))

        if self.motion:
            self.motion.animate(self, paint)
        else:
            paint(1)

    def select(self, selected):
        if self.selected == selected:
            return
        self.selected = selected
        self.transition(False)

    def cleanup(self, event):
        if event.widget != self:
            return
        if self.motion:
            self.motion.cancel(self)


def rounded(canvas, x, y, box_width, box_height, radius=16, **kwargs):
    r = radius
    w, h = box_width, box_height
    r = max(0, min(r, w / 2, h / 2))
    return canvas.create_polygon(
        x + r,
        y,
        x + w - r,
        y,
        x + w,
        y,
        x + w,
        y + r,
        x + w,
        y + h - r,
        x + w,
        y + h,
        x + w - r,
        y + h,
        x + r,
        y + h,
        x,
        y + h,
        x,
        y + h - r,
        x,
        y + r,
        x,
        y,
        smooth=True,
        splinesteps=24,
        **kwargs,
    )


class MetricCard(tk.Canvas):
    def __init__(self, parent, app, title, value, subtitle, index):
        super().__init__(parent, height=118, width=180, bg=app.bg, highlightthickness=0)
        self.app = app
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.measure = tkfont.Font(self, family="Inter", size=23, weight="bold")
        self.accent = app.motion.palette.get("accent", "#D6B467")
        self.hover = 0
        self.intro = 0
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Enter>", lambda e: self.transition(1))
        self.bind("<Leave>", lambda e: self.transition(0))
        self.bind("<Destroy>", lambda e: app.motion.cancel(self), add="+")
        app.motion.idle(
            self,
            lambda: app.motion.animate(
                self, self.set_intro, 440 + index * 60, channel="entrance"
            ),
        )

    def set_intro(self, value):
        self.intro = value
        self.draw()

    def transition(self, target):
        start = self.hover
        self.app.motion.animate(
            self, lambda t: self.set_hover(start + (target - start) * t)
        )

    def set_hover(self, value):
        self.hover = value
        self.draw()

    def draw(self):
        a = self.app
        width = self.winfo_width() - 2
        self.delete("all")
        lift = 6 * self.hover
        offset = round(12 * (1 - self.intro))
        rounded(
            self,
            1,
            8 - lift,
            width,
            106,
            12,
            fill=blend(a.surface, a.motion.palette["hover"], self.hover * 0.6),
            outline=a.border,
            width=1,
        )
        self.create_text(
            18,
            25 + offset - lift,
            text=self.title,
            anchor="w",
            fill=blend(a.surface, a.muted, self.intro),
            font=("Inter", 8),
        )
        size = min(
            23,
            max(
                11,
                int(23 * max(1, width - 42) / max(1, self.measure.measure(self.value))),
            ),
        )
        self.create_text(
            18,
            58 + offset - lift,
            text=self.value,
            anchor="w",
            fill=blend(a.surface, a.fg, self.intro),
            font=("Inter", size, "bold"),
        )
        self.create_text(
            18,
            92 + offset - lift,
            text=self.subtitle,
            anchor="w",
            width=max(120, width - 34),
            justify="left",
            fill=blend(a.surface, a.muted, self.intro),
            font=("Inter", 8),
        )


class ClockButton(MotionButton):
    """Small circular clock. Active/paused state is drawn without widening it."""

    def __init__(self, parent, **kwargs):
        self.active = False
        self.running = False
        super().__init__(parent, width=5, height=56, style="Accent.TButton", **kwargs)
        self.configure(width=56)

    def set_session(self, active, running):
        if (active, running) != (self.active, self.running):
            self.active, self.running = active, running
            self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        cx = w / 2
        cy = h / 2 - 2 * self.hover
        self.create_oval(
            cx - 26,
            cy - 26,
            cx + 26,
            cy + 26,
            fill=self.current,
            outline="#F2D28B" if self.focused else self.current,
            width=2,
        )
        color = "#17130A"
        self.create_oval(cx - 11, cy - 11, cx + 11, cy + 11, outline=color, width=2)
        self.create_line(cx, cy - 7, cx, cy, cx + 6, cy + 3, fill=color, width=2)
        if self.active:
            self.create_oval(
                cx + 13,
                cy + 12,
                cx + 25,
                cy + 24,
                fill="#151515",
                outline=self.current,
                width=2,
            )
            if self.running:
                self.create_polygon(
                    cx + 18,
                    cy + 15,
                    cx + 18,
                    cy + 21,
                    cx + 22,
                    cy + 18,
                    fill=self.current,
                )
            else:
                for x in [cx + 18, cx + 21]:
                    self.create_line(
                        x, cy + 15, x, cy + 21, fill=self.current, width=1.5
                    )


class ThinProgress(tk.Canvas):
    def __init__(self, parent, app, value):
        super().__init__(parent, height=6, bg=app.surface, highlightthickness=0)
        self.app = app
        self.value = max(0, min(100, value))
        self.bind("<Configure>", self.draw)

    def draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        rounded(self, 0, 0, w, 6, 3, fill=self.app.border, outline="")
        if self.value:
            rounded(
                self,
                0,
                0,
                max(3, w * self.value / 100),
                6,
                3,
                fill=self.app.motion.palette["accent"],
                outline="",
            )


class Panel(tk.Canvas):
    def __init__(self, parent, app):
        super().__init__(parent, bg=app.bg, highlightthickness=0, height=100)
        self.app = app
        self.body = ttk.Frame(self, style="Panel.TFrame", padding=0)
        self.body._panel = True
        self.window = self.create_window(17, 15, window=self.body, anchor="nw")
        self.bind("<Configure>", self.resize)
        self.body.bind("<Configure>", self.resize)

    def resize(self, event=None):
        width = max(1, self.winfo_width() - 34)
        self.itemconfigure(self.window, width=width)
        height = self.body.winfo_reqheight() + 30
        if self.winfo_reqheight() != height:
            self.configure(height=height)
        self.delete("border")
        rounded(
            self,
            1,
            1,
            self.winfo_width() - 2,
            height - 2,
            16,
            fill=self.app.surface,
            outline=self.app.border,
            width=1.2,
            tags="border",
        )
        self.tag_lower("border")


class FocusDial(tk.Canvas):
    def __init__(self, parent, app):
        super().__init__(parent, width=450, height=288, bg=app.bg, highlightthickness=0)
        self.app = app
        self.progress = 0
        self.text = ""
        self.running = False
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Destroy>", lambda e: app.motion.cancel(self), add="+")

    def configure(self, cnf=None, **kwargs):
        if "text" in kwargs:
            text = kwargs.pop("text")
            if text != self.text:
                self.text = text
                self.draw()
        return super().configure(cnf, **kwargs)

    def update_progress(self, value, running):
        changed = self.running != running
        self.running = running
        start = self.progress
        if abs(value - start) < 0.001:
            if changed:
                self.draw()
            return
        self.app.motion.animate(
            self, lambda t: self.set_progress(start + (value - start) * t), 220
        )

    def set_progress(self, value):
        self.progress = value
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        a = self.app
        cx = w / 2
        cy = 142
        radius = 118
        self.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=a.border,
            width=7,
        )
        if self.progress > 0:
            self.create_arc(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                start=90,
                extent=-max(0.1, self.progress) * 3.6,
                style="arc",
                outline=a.motion.palette["accent"],
                width=7,
            )
        self.create_text(
            cx,
            92,
            text="EM FOCO" if self.running else "PAUSA PARA RESPIRAR",
            fill=a.motion.palette["accent"],
            font=("Inter", 8, "bold"),
        )
        self.create_text(cx, 139, text=self.text, fill=a.fg, font=("Inter", 29))
        self.create_text(
            cx,
            181,
            text=f"{self.progress:.0f}% da sessão",
            fill=a.muted,
            font=("Inter", 9),
        )
