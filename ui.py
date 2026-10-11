"""Small native visual components. Animations run only during interactions.

Every component reads colors from the active palette (theme.py) through
``root._motion.palette``. Nothing here touches the database.
"""

import math
import re
import tkinter as tk
import time
import os
import ctypes
from tkinter import ttk
from tkinter import font as tkfont

from icons import ICONS
from theme import FONT, DISPLAY, ICON

PRIVATE_FONTS = ("Inter-*.ttf", "Poppins-Bold.ttf", "RUMO-Icons.ttf")
FALLBACK = dict(
    bg="#0E0E11",
    sidebar="#121215",
    surface="#18181C",
    raised="#1F1F24",
    hover="#25252B",
    border="#2A2A31",
    strong="#3B3B45",
    fg="#ECE8E0",
    muted="#A3A0A8",
    faint="#8A8792",
    accent="#D4B26A",
    tint="#2A2418",
    selected="#241F17",
    primary="#CBA65A",
    primary_hover="#DDBB72",
    primary_ink="#17130B",
    success="#72C493",
    success_bg="#18291F",
    error="#E58085",
    error_bg="#2F1C1F",
    info="#8EADDB",
    info_bg="#1A2232",
    warning="#E2AE62",
    warning_bg="#2E2416",
    track="#2C2C33",
)
TONES = {
    "neutral": ("raised", "muted"),
    "accent": ("tint", "accent"),
    "success": ("success_bg", "success"),
    "info": ("info_bg", "info"),
    "warning": ("warning_bg", "warning"),
    "error": ("error_bg", "error"),
    "demo": ("warning_bg", "warning"),
}


def load_fonts(root, assets):
    """Register bundled fonts for this process only; nothing is installed."""
    if getattr(root, "_fonts_loaded", False):
        return root._font_family
    if os.name == "nt":
        add = ctypes.windll.gdi32.AddFontResourceExW
        add.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        for pattern in PRIVATE_FONTS:
            for path in (assets / "fonts").glob(pattern):
                add(str(path), 0x10, None)
    else:
        try:
            import ctypes.util

            fc = ctypes.CDLL(ctypes.util.find_library("fontconfig"))
            fc.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            # Per file, not per directory: a directory cache keyed by its mtime
            # would keep serving an older RUMO-Icons.ttf after an update.
            for pattern in PRIVATE_FONTS:
                for path in (assets / "fonts").glob(pattern):
                    fc.FcConfigAppFontAddFile(None, str(path).encode())
        except (OSError, TypeError, AttributeError):
            pass
    families = set(tkfont.families(root))
    root._fonts_loaded = True
    root._icons_available = ICON in families
    root._font_family = "Inter" if "Inter" in families else "Segoe UI"
    return root._font_family


def blend(a, b, fraction):
    channels = [
        round(int(a[i : i + 2], 16) * (1 - fraction) + int(b[i : i + 2], 16) * fraction)
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def palette_of(widget):
    motion = getattr(widget.winfo_toplevel()._root(), "_motion", None)
    return motion.palette if motion and motion.palette else FALLBACK


def ui_font(widget, family=FONT, size=10, weight="normal"):
    """Shared named fonts: one Tcl font per style instead of one per widget."""
    root = widget.winfo_toplevel()._root()
    cache = root.__dict__.setdefault("_ui_fonts", {})
    key = (family, size, weight)
    if key not in cache:
        cache[key] = tkfont.Font(root, family=family, size=size, weight=weight)
    return cache[key]


def glyph(widget, name):
    """Icon character when the private icon font is available, else empty."""
    root = widget.winfo_toplevel()._root()
    return ICONS.get(name, "") if getattr(root, "_icons_available", False) else ""


def background_of(parent):
    try:
        return ttk.Style(parent).lookup(parent.cget("style") or "TFrame", "background")
    except tk.TclError:
        return parent.cget("bg")


LOOK_CACHE = 72


def load_image(app, relative, factor=1):
    """PhotoImages are cached on the app so Tk keeps a reference.

    Appearance layers use a bounded LRU: browsing looks in the customizer must
    not keep every combination in memory. Recently drawn layers stay alive.
    """
    cache = app.__dict__.setdefault("images", {})
    key = relative if factor == 1 else f"{relative}@{factor}"
    if key in cache:
        if "/look/" in key:
            cache[key] = cache.pop(key)
        return cache[key]
    if factor == 1:
        image = tk.PhotoImage(file=str(app.assets / relative))
    else:
        image = load_image(app, relative).subsample(factor)
    cache[key] = image
    looks = [k for k in cache if "/look/" in k]
    for old in looks[: max(0, len(looks) - LOOK_CACHE)]:
        cache.pop(old, None)
    return image


def look_layers(app, look, view):
    """Appearance PNG paths for ``look`` (full body or bust), in drawing order."""
    from appearance import layers

    back, front = layers(look)
    folder = f"character/look/{view}/"
    if not (app.assets / folder).exists():
        return [], ["character/base.png"] if view == "full" else []
    return [folder + n + ".png" for n in back], [folder + n + ".png" for n in front]


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

    def later(self, widget, milliseconds, callback, channel="later"):
        """One cancellable delayed callback per widget/channel."""
        self.watch(widget)
        key = (widget, channel)

        def run():
            self.jobs.pop(key, None)
            if widget.winfo_exists():
                callback()

        previous = self.jobs.pop(key, None)
        if previous:
            self.root.after_cancel(previous)
        self.jobs[key] = self.root.after(milliseconds, run)

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
                self.jobs[key] = self.root.after(16, step)

        step()

    def reveal(self, window):
        # Let geometry settle through the event loop; synchronous idle draining
        # can wait indefinitely with Xft/Tk 8.6 while opening a complex page.
        self.later(window, 10, lambda: self._reveal(window), "reveal")

    def _reveal(self, window):
        try:
            window.attributes("-alpha", 0 if self.enabled and os.name == "nt" else 1)
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
            # The window manager may not have applied the geometry yet; never
            # lock a size smaller than the content needs (clipped footers).
            width = max(window.winfo_width(), window.winfo_reqwidth())
            height = max(window.winfo_height(), window.winfo_reqheight())
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

            if os.name == "nt":
                self.animate(window, paint, 380)
            else:
                # Xwayland compositors may leave alpha-animated Tk dialogs blank.
                # Keep native windows opaque and settle their position once.
                paint(1)
            window.bind(
                "<Destroy>",
                lambda e: self.cancel(window) if e.widget == window else None,
                add="+",
            )
        except tk.TclError:
            try:
                window.attributes("-alpha", 1)
            except tk.TclError:
                pass


def activate_popup(window, focus=None, modal=True):
    """Grab only after mapping; creating a Toplevel does not make it viewable."""
    previous = window.grab_current()
    root = window._root()
    motion = getattr(root, "_motion", None)

    def ready():
        try:
            if not window.winfo_exists():
                return
            if not window.winfo_viewable():
                if motion:
                    motion.later(window, 20, ready, "popup-ready")
                else:
                    window.after(20, ready)
                return
            if modal:
                window.grab_set()
            if focus is not None and focus.winfo_exists():
                focus.focus_set()
        except tk.TclError:
            # Closing a parent while the popup is mapping is a normal cancellation.
            return

    def restore(event):
        if event.widget != window or previous is None:
            return
        try:
            if previous.winfo_exists() and previous.winfo_viewable():
                previous.grab_set()
        except tk.TclError:
            pass

    window.bind("<Destroy>", restore, add="+")
    if motion:
        motion.later(window, 10, ready, "popup-ready")
    else:
        window.after(10, ready)


def pointer_inside(widget):
    try:
        x, y = widget.winfo_pointerxy()
        left, top = widget.winfo_rootx(), widget.winfo_rooty()
        return (
            left <= x < left + widget.winfo_width()
            and top <= y < top + widget.winfo_height()
        )
    except tk.TclError:
        return False


class Hover:
    """Finite hover transition for a widget tree, without child flicker.

    ``paint(value)`` receives 0..1. Leaving into a child keeps the hover.
    """

    def __init__(self, app, widget, paint, milliseconds=200, tree=True):
        self.app, self.widget, self.paint = app, widget, paint
        self.milliseconds = milliseconds
        self.value = 0.0
        self.target = 0
        self.watch(widget, tree)

    def watch(self, widget, tree=True):
        widget.bind("<Enter>", lambda e: self.go(1), add="+")
        widget.bind("<Leave>", self.leave, add="+")
        if tree:
            for child in widget.winfo_children():
                self.watch(child)

    def leave(self, event=None):
        self.app.motion.later(
            self.widget,
            40,
            lambda: None if pointer_inside(self.widget) else self.go(0),
            "hover-check",
        )

    def go(self, target):
        if target == self.target or not self.widget.winfo_exists():
            return
        self.target = target
        start = self.value

        def step(t):
            self.value = start + (target - start) * t
            self.paint(self.value)

        self.app.motion.animate(self.widget, step, self.milliseconds, "hover")


def hover_card(app, frame, base, over, border=None, border_over=None):
    """Animate a tk.Frame card: background of the frame and same-colored children."""
    painted = []

    def collect(widget):
        try:
            if widget.cget("bg") == base and not getattr(widget, "static_bg", False):
                painted.append(widget)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            collect(child)

    collect(frame)

    def paint(value):
        color = blend(base, over, value)
        for widget in painted:
            if widget.winfo_exists():
                widget.configure(bg=color)
        if border and frame.winfo_exists():
            frame.configure(highlightbackground=blend(border, border_over, value))

    return Hover(app, frame, paint)


NUMBER = re.compile(r"\d[\d.]*(?:,\d+)?")


def count_text(text, fraction):
    """'1.097' at 0.5 -> '549': numbers in a label count up during an entrance."""
    if fraction >= 1:
        return text

    def scale(match):
        raw = match.group(0)
        decimals = len(raw.split(",")[1]) if "," in raw else 0
        value = float(raw.replace(".", "").replace(",", ".")) * fraction
        shown = f"{value:,.{decimals}f}"
        return shown.replace(",", "§").replace(".", ",").replace("§", ".")

    return NUMBER.sub(scale, text)


class Tooltip:
    """Delayed hint; one pending timer per hover, removed on leave/destroy."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.pending = None
        self.popup = None
        widget.bind("<Enter>", self.enter, add="+")
        widget.bind("<Leave>", self.leave, add="+")
        widget.bind("<Destroy>", self.leave, add="+")

    def enter(self, event):
        self.leave()
        self.pending = self.widget.after(450, self.show)

    def show(self):
        self.pending = None
        if not self.widget.winfo_exists() or not self.text:
            return
        p = palette_of(self.widget)
        self.popup = tk.Toplevel(self.widget)
        self.popup.overrideredirect(True)
        self.popup.configure(bg=p["strong"])
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.popup.geometry(f"+{x}+{y}")
        tk.Label(
            self.popup,
            text=self.text,
            bg=p["raised"],
            fg=p["fg"],
            padx=10,
            pady=6,
            justify="left",
            wraplength=360,
            font=ui_font(self.widget, size=9),
        ).pack(padx=1, pady=1)
        motion = getattr(self.widget.winfo_toplevel()._root(), "_motion", None)
        if motion and motion.enabled:
            popup = self.popup
            try:
                popup.attributes("-alpha", 0)
                motion.animate(
                    popup,
                    lambda t: (
                        popup.attributes("-alpha", t) if popup.winfo_exists() else None
                    ),
                    140,
                )
            except tk.TclError:
                pass

    def leave(self, event=None):
        if self.pending:
            try:
                self.widget.after_cancel(self.pending)
            except tk.TclError:
                pass
            self.pending = None
        if self.popup:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
            self.popup = None


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


def tabular(canvas, x, y, text, font, fill, tags=()):
    """Draw digits in fixed cells so a running clock does not jitter."""
    cell = max(font.measure(str(n)) for n in range(10))
    colon = font.measure(":")
    widths = [colon if char == ":" else cell for char in text]
    left = x - sum(widths) / 2
    for char, width in zip(text, widths):
        canvas.create_text(
            left + width / 2, y, text=char, font=font, fill=fill, tags=tags
        )
        left += width


class MotionButton(tk.Canvas):
    """Rounded vector button with variants, optional icon and keyboard focus.

    Roles: Accent.TButton (primary), TButton (secondary), Ghost.TButton,
    Danger.TButton, Nav.TButton and Chip.TButton (compact, selectable).
    """

    def __init__(self, parent, **kwargs):
        self.motion = getattr(parent.winfo_toplevel()._root(), "_motion", None)
        self.role = kwargs.pop("style", "TButton")
        self.text = kwargs.pop("text", "")
        self.icon = kwargs.pop("icon", None)
        self.command = kwargs.pop("command", None)
        width = kwargs.pop("width", None)
        self.disabled = kwargs.pop("state", "normal") == "disabled"
        self.selected = kwargs.pop("selected", False)
        self.hover = 0
        self.press = 0
        self.focused = False
        compact = self.role == "Chip.TButton"
        self.font = ui_font(
            parent,
            size=9 if compact else 10,
            weight="bold" if self.role == "Accent.TButton" else "normal",
        )
        self.icon_font = ui_font(parent, ICON, 10 if compact else 12)
        self.surround = background_of(parent) or palette_of(parent)["bg"]
        height = kwargs.pop("height", 30 if compact else 38)
        icon_text = glyph(parent, self.icon) if self.icon else ""
        if width is None:
            label = self.font.measure(self.text) if self.text else 0
            extra = (
                (self.icon_font.measure(icon_text) + (8 if label else 0))
                if icon_text
                else 0
            )
            requested = (
                max(height, label + extra + (24 if compact else 32))
                if (label or extra)
                else height
            )
        else:
            requested = max(40, int(width) * 8 + 16)
        super().__init__(
            parent,
            width=requested,
            height=height,
            bg=self.surround,
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

    def palette(self):
        return self.motion.palette if self.motion and self.motion.palette else FALLBACK

    def colors(self):
        p = self.palette()
        base = self.surround
        if self.role == "Accent.TButton":
            return p["primary"], p["primary_hover"], p["primary_ink"]
        if self.role == "Nav.TButton":
            return (
                p["selected"] if self.selected else base,
                p["selected"] if self.selected else p["hover"],
                p["accent"] if self.selected else p["muted"],
            )
        if self.role == "Ghost.TButton":
            return base, p["hover"], p["muted"]
        if self.role == "Danger.TButton":
            return base, p["error_bg"], p["error"]
        if self.role == "Chip.TButton" and self.selected:
            return p["tint"], p["tint"], p["accent"]
        return p["raised"], p["hover"], p["fg"]

    def border(self):
        p = self.palette()
        if self.focused:
            return p["accent"]
        if self.role in ("TButton", "Chip.TButton"):
            return p["accent"] if self.selected else p["border"]
        return self.current

    def paint(self, color):
        self.current = color
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4:
            return
        p = self.palette()
        inset = 1 + self.press
        radius = h / 2 if self.role == "Chip.TButton" else 8
        raised = self.role in ("Accent.TButton", "TButton", "Chip.TButton")
        lift = self.hover * (1 - self.press) if raised and not self.disabled else 0
        if lift > 0.05:
            # Soft shadow under a button that rises 1 px on hover.
            rounded(
                self,
                inset,
                inset + 1,
                max(1, w - inset * 2 - 1),
                h - inset * 2 - 1,
                radius,
                fill=blend(self.surround, "#000000", 0.35 * lift),
                outline="",
            )
        rounded(
            self,
            inset,
            inset - lift,
            max(1, w - inset * 2 - 1),
            h - inset * 2 - 1,
            radius,
            fill=self.current,
            outline=self.border(),
            width=2 if self.focused else 1,
        )
        ink = self.colors()[2]
        if self.disabled:
            ink = p["faint"]
        elif self.hover > 0.5 and self.role in ("Nav.TButton", "Ghost.TButton"):
            ink = p["accent"] if self.selected else p["fg"]
        icon = glyph(self, self.icon) if self.icon else ""
        nav = self.role == "Nav.TButton"
        grow = getattr(self, "indicator", 1)
        if nav and self.selected and grow > 0.02:
            bar = (h - 18) * grow
            rounded(
                self,
                inset + 3,
                h / 2 - bar / 2,
                3,
                bar,
                1.5,
                fill=p["accent"],
                outline="",
            )
        label_width = self.font.measure(self.text) if self.text else 0
        icon_width = self.icon_font.measure(icon) if icon else 0
        gap = 10 if nav else 8
        total = icon_width + (gap if icon and self.text else 0) + label_width
        x = 18 + 3 * self.hover if nav else (w - total) / 2
        y = h / 2 + self.press * 0.5 - lift
        if icon:
            self.create_text(x, y, text=icon, anchor="w", fill=ink, font=self.icon_font)
            x += icon_width + (gap if self.text else 0)
        if self.text:
            self.create_text(x, y, text=self.text, anchor="w", fill=ink, font=self.font)

    def configure(self, cnf=None, **kwargs):
        changed = False
        for name in ["text", "command", "icon"]:
            if name in kwargs:
                value = kwargs.pop(name)
                if getattr(self, name) != value:
                    setattr(self, name, value)
                    changed = True
        if "state" in kwargs:
            disabled = kwargs.pop("state") == "disabled"
            if disabled != self.disabled:
                self.disabled = disabled
                self.configure(cursor="arrow" if disabled else "hand2")
                changed = True
        result = super().configure(cnf, **kwargs)
        if changed:
            self.draw()
        return result

    config = configure

    def cget(self, key):
        if key in ["text", "command", "icon"]:
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
        if not self.press:
            return
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
        if start.lower() == target.lower() and start_hover == int(hover):
            if self.motion:
                self.motion.cancel(self)
            return

        def paint(t):
            self.hover = start_hover + (int(hover) - start_hover) * t
            self.paint(blend(start, target, t))

        if self.motion:
            self.motion.animate(self, paint, 180)
        else:
            paint(1)

    def select(self, selected):
        if self.selected == selected:
            return
        self.selected = selected
        self.current = self.colors()[0]
        if selected and self.role == "Nav.TButton" and self.motion:
            self.indicator = 0
            self.motion.animate(
                self,
                lambda t: (setattr(self, "indicator", t), self.draw()),
                260,
                channel="indicator",
            )
        self.draw()

    def cleanup(self, event):
        if event.widget != self:
            return
        if self.motion:
            self.motion.cancel(self)


class Chip(tk.Canvas):
    """Small status label. Tone colors always come with text or an icon."""

    def __init__(self, parent, text, tone="neutral", icon=None, tip=None, bg=None):
        p = palette_of(parent)
        self.font = ui_font(parent, size=8, weight="bold")
        self.icon_font = ui_font(parent, ICON, 9)
        self.text = text
        self.icon = glyph(parent, icon) if icon else ""
        self.tone = tone
        width = (
            self.font.measure(text)
            + (self.icon_font.measure(self.icon) + 6 if self.icon else 0)
            + 20
        )
        super().__init__(
            parent,
            width=width,
            height=22,
            bg=bg or background_of(parent) or p["bg"],
            highlightthickness=0,
        )
        self.bind("<Configure>", lambda e: self.draw())
        if tip:
            Tooltip(self, tip)

    def draw(self):
        self.delete("all")
        p = palette_of(self)
        fill, ink = (p[key] for key in TONES.get(self.tone, TONES["neutral"]))
        w = self.winfo_width()
        rounded(self, 0, 0, w - 1, 21, 10.5, fill=fill, outline="")
        x = 10
        if self.icon:
            self.create_text(
                x, 11, text=self.icon, anchor="w", fill=ink, font=self.icon_font
            )
            x += self.icon_font.measure(self.icon) + 6
        self.create_text(x, 11, text=self.text, anchor="w", fill=ink, font=self.font)


def demo_chip(parent, tip=None, bg=None):
    return Chip(
        parent,
        "DEMONSTRAÇÃO",
        tone="demo",
        icon="eye",
        bg=bg,
        tip=tip
        or "Valores fictícios para avaliar o visual. Nada aqui é salvo ou conta como ganho.",
    )


class ProgressBar(tk.Canvas):
    """Thin bar with a finite fill animation on first paint."""

    def __init__(self, parent, app, value, tone="accent", height=6, bg=None):
        super().__init__(
            parent,
            height=height,
            bg=bg or background_of(parent) or app.surface,
            highlightthickness=0,
        )
        self.app = app
        self.value = max(0, min(100, value or 0))
        self.tone = tone
        self.thickness = height
        self.phase = 0 if app.motion.enabled else 1
        self.bind("<Configure>", self.draw)
        if self.phase < 1:
            app.motion.idle(
                self,
                lambda: app.motion.animate(
                    self, lambda t: self.set_phase(t), 520, channel="fill"
                ),
            )

    def set_phase(self, value):
        self.phase = value
        self.draw()

    def draw(self, event=None):
        self.delete("all")
        p = self.app.motion.palette
        w = self.winfo_width()
        h = self.thickness
        rounded(self, 0, 0, w, h, h / 2, fill=p["track"], outline="")
        if self.value:
            color = p["primary"] if self.tone == "accent" else p[self.tone]
            rounded(
                self,
                0,
                0,
                max(h, w * self.value / 100 * self.phase),
                h,
                h / 2,
                fill=color,
                outline="",
            )


class ThinProgress(ProgressBar):
    """Compatibility name used by edital and challenges."""

    def __init__(self, parent, app, value):
        super().__init__(parent, app, value)


class Ring(tk.Canvas):
    """Circular progress with a short center label."""

    def __init__(
        self,
        parent,
        app,
        value,
        size=92,
        thickness=7,
        center="",
        caption="",
        tone="accent",
        bg=None,
    ):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=bg or background_of(parent) or app.surface,
            highlightthickness=0,
        )
        self.app = app
        self.value = max(0, min(100, value or 0))
        self.size, self.thickness = size, thickness
        self.center, self.caption, self.tone = center, caption, tone
        self.phase = 0 if app.motion.enabled else 1
        self.bind("<Configure>", lambda e: self.draw())
        if self.phase < 1:
            app.motion.idle(
                self,
                lambda: app.motion.animate(
                    self, lambda t: self.set_phase(t), 640, channel="fill"
                ),
            )

    def set_phase(self, value):
        self.phase = value
        self.draw()

    def draw(self):
        self.delete("all")
        p = self.app.motion.palette
        s, t = self.size, self.thickness
        box = (t / 2 + 1, t / 2 + 1, s - t / 2 - 1, s - t / 2 - 1)
        self.create_oval(*box, outline=p["track"], width=t)
        extent = self.value * 3.6 * self.phase
        if extent > 0.5:
            self.create_arc(
                *box,
                start=90,
                extent=-min(359.9, extent),
                style="arc",
                outline=p["primary"] if self.tone == "accent" else p[self.tone],
                width=t,
            )
        offset = 8 if self.caption else 0
        self.create_text(
            s / 2,
            s / 2 - offset,
            text=self.center,
            fill=p["fg"],
            font=ui_font(self, size=12 if s >= 80 else 10, weight="bold"),
        )
        if self.caption:
            self.create_text(
                s / 2,
                s / 2 + 12,
                text=self.caption,
                fill=p["muted"],
                font=ui_font(self, size=8),
            )


class MetricCard(tk.Canvas):
    def __init__(self, parent, app, title, value, subtitle, index, icon=None):
        super().__init__(parent, height=108, width=180, bg=app.bg, highlightthickness=0)
        self.app = app
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.icon = glyph(self, icon) if icon else ""
        self.measure = ui_font(self, size=19, weight="bold")
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
            self, lambda t: self.set_hover(start + (target - start) * t), 180
        )

    def set_hover(self, value):
        self.hover = value
        self.draw()

    def draw(self):
        a = self.app
        p = a.motion.palette
        width = self.winfo_width() - 2
        self.delete("all")
        offset = round(10 * (1 - self.intro))
        rounded(
            self,
            1,
            1,
            width,
            104,
            12,
            fill=a.surface,
            outline=blend(a.border, p["strong"], self.hover),
            width=1,
        )
        x = 18
        if self.icon:
            rounded(self, 16, 16, 28, 28, 8, fill=p["tint"], outline="")
            self.create_text(
                30,
                30,
                text=self.icon,
                fill=blend(p["tint"], p["accent"], self.intro),
                font=ui_font(self, ICON, 11),
            )
            x = 54
        self.create_text(
            x,
            30 + offset,
            text=self.title,
            anchor="w",
            fill=blend(a.surface, a.muted, self.intro),
            font=ui_font(self, size=8, weight="bold"),
        )
        size = min(
            19,
            max(
                11,
                int(19 * max(1, width - 36) / max(1, self.measure.measure(self.value))),
            ),
        )
        self.create_text(
            18,
            64 + offset,
            text=count_text(self.value, self.intro),
            anchor="w",
            fill=blend(a.surface, a.fg, self.intro),
            font=ui_font(self, size=size, weight="bold"),
        )
        self.create_text(
            18,
            89 + offset,
            text=self.subtitle,
            anchor="w",
            width=max(120, width - 34),
            justify="left",
            fill=blend(a.surface, a.muted, self.intro),
            font=ui_font(self, size=9),
        )


class ClockButton(MotionButton):
    """Persistent study clock pill. Shows state with icon and text, not only color."""

    def __init__(self, parent, **kwargs):
        self.active = False
        self.running = False
        self.display = ""
        self.subject = ""
        super().__init__(
            parent, text="Foco", icon="timer", height=38, style="Clock", **kwargs
        )
        self.time_font = ui_font(parent, size=11, weight="bold")
        self.resize()

    def colors(self):
        p = self.palette()
        if self.active:
            return p["tint"], blend(p["tint"], p["accent"], 0.18), p["accent"]
        return p["raised"], p["hover"], p["fg"]

    def border(self):
        p = self.palette()
        if self.focused:
            return p["accent"]
        return blend(p["tint"], p["accent"], 0.45) if self.active else p["border"]

    def resize(self):
        if self.active:
            cell = max(self.time_font.measure(str(n)) for n in range(10))
            width = 44 + cell * 6 + self.time_font.measure("::")
            width += min(150, self.font.measure(self.subject)) + 22
        else:
            width = 44 + self.font.measure("Iniciar foco") + 12
        super().configure(width=width)

    def set_session(self, active, running, display="", subject=""):
        changed = (active, running) != (self.active, self.running)
        subject_changed = subject != self.subject
        self.active, self.running = active, running
        self.subject = subject
        if changed or subject_changed:
            self.current = self.colors()[0]
            self.resize()
            self.draw()
        if display != self.display:
            self.display = display
            self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        p = self.palette()
        inset = 1 + self.press
        rounded(
            self,
            inset,
            inset,
            w - inset * 2 - 1,
            h - inset * 2 - 1,
            (h - 2) / 2,
            fill=self.current,
            outline=self.border(),
            width=2 if self.focused else 1,
        )
        ink = self.colors()[2]
        y = h / 2
        if not self.active:
            self.create_text(
                18,
                y,
                text=glyph(self, "timer"),
                anchor="w",
                fill=p["accent"],
                font=self.icon_font,
            )
            self.create_text(
                42, y, text="Iniciar foco", anchor="w", fill=ink, font=self.font
            )
            return
        icon = "play" if self.running else "pause"
        self.create_text(
            16, y, text=glyph(self, icon), anchor="w", fill=ink, font=self.icon_font
        )
        cell = max(self.time_font.measure(str(n)) for n in range(10))
        span = cell * 6 + self.time_font.measure("::")
        tabular(
            self, 40 + span / 2, y, self.display or "--:--:--", self.time_font, p["fg"]
        )
        subject = self.subject
        room = w - (40 + span + 12) - 14
        while subject and self.font.measure(subject) > room:
            subject = subject[:-2] + "…" if len(subject) > 2 else ""
        self.create_text(
            40 + span + 12, y, text=subject, anchor="w", fill=p["muted"], font=self.font
        )


class Panel(tk.Canvas):
    """Card surface. ``tone='hero'`` adds a restrained gold edge for primary areas."""

    def __init__(
        self, parent, app, padding=(20, 18), tone="surface", bg=None, stretch=False
    ):
        self.stretch = stretch
        super().__init__(
            parent,
            bg=bg or background_of(parent) or app.bg,
            highlightthickness=0,
            height=100,
        )
        self.app = app
        self.tone = tone
        self.padding = padding
        self.body = ttk.Frame(self, style="Panel.TFrame", padding=0)
        self.body._panel = True
        self.window = self.create_window(
            padding[0], padding[1], window=self.body, anchor="nw"
        )
        self.hover = 0
        self.bind("<Configure>", self.resize)
        self.body.bind("<Configure>", self.resize)
        Hover(app, self, self.set_hover, 220, tree=False)
        self.body.bind("<Enter>", lambda e: self.event_generate("<Enter>"), add="+")

    def set_hover(self, value):
        self.hover = value
        self.resize()

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
            # Let the body fill the stretched card so bottom-packed actions align.
            body_height = max(1, height - py * 2)
            if int(float(self.itemcget(self.window, "height"))) != body_height:
                self.itemconfigure(self.window, height=body_height)
        self.delete("border")
        p = self.app.motion.palette
        rest = (
            blend(self.app.border, p["accent"], 0.38)
            if self.tone == "hero"
            else self.app.border
        )
        lit = (
            blend(self.app.border, p["accent"], 0.7)
            if self.tone == "hero"
            else p["strong"]
        )
        outline = blend(rest, lit, self.hover)
        rounded(
            self,
            1,
            1,
            self.winfo_width() - 2,
            height - 2,
            14,
            fill=self.app.surface,
            outline=outline,
            width=1,
            tags="border",
        )
        if self.tone == "hero":
            self.create_line(
                24,
                1,
                min(96, self.winfo_width() - 24),
                1,
                fill=p["accent"],
                width=2,
                tags="border",
            )
        self.tag_lower("border")


class Columns(ttk.Frame):
    """Side-by-side columns that stack below ``breakpoint`` pixels of width."""

    def __init__(self, parent, app, weights=(1, 1), gap=16, breakpoint=940):
        panel = getattr(parent, "_panel", False)
        style = "Panel.TFrame" if panel else "TFrame"
        super().__init__(parent, style=style)
        self.weights, self.gap, self.breakpoint = weights, gap, breakpoint
        self.cols = []
        for _ in weights:
            column = ttk.Frame(self, style=style)
            column._panel = panel
            self.cols.append(column)
        self.stacked = None
        self.bind("<Configure>", self.reflow)
        app.motion.idle(self, self.reflow)

    def reflow(self, event=None):
        stacked = self.winfo_width() < self.breakpoint
        if stacked == self.stacked:
            return
        self.stacked = stacked
        last = len(self.cols) - 1
        for index, weight in enumerate(self.weights):
            self.columnconfigure(
                index, weight=(1 if index == 0 else 0) if stacked else weight
            )
        for index, column in enumerate(self.cols):
            # Always pass both paddings: grid keeps options from earlier calls.
            if stacked:
                column.grid(
                    row=index,
                    column=0,
                    sticky="nsew",
                    padx=0,
                    pady=(0, 0 if index == last else self.gap),
                )
            else:
                half = self.gap / 2
                column.grid(
                    row=0,
                    column=index,
                    sticky="nsew",
                    padx=(0 if index == 0 else half, 0 if index == last else half),
                    pady=0,
                )
        self.rowconfigure(0, weight=1)


class SectionHeader(ttk.Frame):
    """Heading row with optional icon, chip and right-side action."""

    def __init__(self, parent, app, text, icon=None, action=None, chip=None):
        panel = getattr(parent, "_panel", False)
        super().__init__(parent, style="Panel.TFrame" if panel else "TFrame")
        p = app.motion.palette
        if icon and glyph(self, icon):
            ttk.Label(
                self,
                text=glyph(self, icon),
                font=ui_font(self, ICON, 12),
                foreground=p["accent"],
                style="Panel.TLabel" if panel else "TLabel",
            ).pack(side="left", padx=(0, 8))
        ttk.Label(
            self,
            text=text,
            style="PanelHeading.TLabel" if panel else "Heading.TLabel",
        ).pack(side="left")
        if chip is not None:
            chip(self).pack(side="left", padx=(10, 0))
        if action:
            label, command, *rest = action
            MotionButton(
                self,
                text=label,
                icon=rest[0] if rest else "chevron-right",
                style="Ghost.TButton",
                height=30,
                command=command,
            ).pack(side="right")


class EmptyState(ttk.Frame):
    """Explains what is missing and offers the next action."""

    def __init__(self, parent, app, icon, title, text, actions=()):
        panel = getattr(parent, "_panel", False)
        style = "Panel.TFrame" if panel else "TFrame"
        super().__init__(parent, style=style)
        p = app.motion.palette
        if glyph(self, icon):
            ttk.Label(
                self,
                text=glyph(self, icon),
                font=ui_font(self, ICON, 20),
                foreground=p["faint"],
                style="Panel.TLabel" if panel else "TLabel",
            ).pack(pady=(8, 6))
        ttk.Label(
            self, text=title, style="PanelHeading.TLabel" if panel else "Heading.TLabel"
        ).pack()
        label = ttk.Label(
            self,
            text=text,
            style="PanelMuted.TLabel" if panel else "Muted.TLabel",
            justify="center",
            wraplength=420,
        )
        label.pack(pady=(4, 10))
        row = ttk.Frame(self, style=style)
        row.pack(pady=(0, 6))
        for index, (name, command, *rest) in enumerate(actions):
            MotionButton(
                row,
                text=name,
                icon=rest[0] if rest else None,
                style="Accent.TButton" if index == 0 else "TButton",
                command=command,
            ).pack(side="left", padx=4)


class Toast:
    """Brief confirmation over the content column; closes by itself."""

    def __init__(self, app, host, top=12):
        self.app = app
        self.host = host
        self.top = top
        self.frame = None

    def show(self, title, text="", icon="circle-check", tone="success", seconds=5):
        self.close()
        p = self.app.motion.palette
        frame = tk.Frame(
            self.host,
            bg=p["raised"],
            highlightthickness=1,
            highlightbackground=p["strong"],
        )
        self.frame = frame
        color = p.get(tone, p["accent"])
        if glyph(frame, icon):
            tk.Label(
                frame,
                text=glyph(frame, icon),
                bg=p["raised"],
                fg=color,
                font=ui_font(frame, ICON, 14),
            ).grid(row=0, column=0, rowspan=2, sticky="n", padx=(14, 10), pady=12)
        tk.Label(
            frame,
            text=title,
            bg=p["raised"],
            fg=p["fg"],
            font=ui_font(frame, size=10, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(12, 0), padx=(0, 6))
        if text:
            tk.Label(
                frame,
                text=text,
                bg=p["raised"],
                fg=p["muted"],
                font=ui_font(frame, size=9),
                anchor="w",
                justify="left",
                wraplength=300,
            ).grid(row=1, column=1, sticky="w", pady=(2, 12), padx=(0, 6))
        close = tk.Label(
            frame,
            text=glyph(frame, "x") or "×",
            bg=p["raised"],
            fg=p["faint"],
            cursor="hand2",
            font=ui_font(frame, ICON, 11),
        )
        close.grid(row=0, column=2, sticky="ne", padx=(4, 10), pady=10)
        close.bind("<Button-1>", lambda e: self.close())

        def slide(t):
            if frame.winfo_exists():
                frame.place(
                    relx=1, x=-28, y=self.top + round(14 * (1 - t)), anchor="ne"
                )

        self.app.motion.animate(frame, slide, 240)
        self.app.motion.later(frame, seconds * 1000, self.close, "toast")

    def close(self):
        if self.frame is not None and self.frame.winfo_exists():
            self.frame.destroy()
        self.frame = None


HELD = (
    "rusty_sword",
    "training_sword",
    "steel_sword",
    "veteran_blade",
    "precision_bow",
    "wood_staff",
    "crystal_staff",
)
EQUIPMENT_LAYERS = {
    "lantern": (["eq-lantern-glow"], ["eq-lantern"]),
    "backpack": (["eq-backpack-back"], ["eq-backpack"]),
    "scarf": ([], ["eq-scarf"]),
    "compass": ([], ["eq-compass"]),
    "spyglass": ([], ["eq-spyglass"]),
}
# Mounts go behind the traveler; clothing, armor and weapons are separate slots.
for _item in (
    "travel_tunic",
    "rogue_cloak",
    "scholar_book",
    "arcane_robe",
    "star_robe",
    "explorer_coat",
    "leather_armor",
    "chain_armor",
    "plate_armor",
    "walking_boots",
    "expedition_boots",
    "memory_helm",
    "explorer_hood",
    "memory_shield",
    "rusty_sword",
    "training_sword",
    "steel_sword",
    "veteran_blade",
    "precision_bow",
    "wood_staff",
    "crystal_staff",
):
    EQUIPMENT_LAYERS[_item] = ([], ["eq-" + _item])
# Held items sit behind the body: the hand, in the chosen skin, covers the grip.
for _item in HELD:
    EQUIPMENT_LAYERS[_item] = (["eq-" + _item], [])
EQUIPMENT_LAYERS["lantern"] = (["eq-lantern-glow", "eq-lantern"], [])
for _item in ("pack_mule", "trail_horse", "sky_griffin"):
    EQUIPMENT_LAYERS[_item] = (["eq-" + _item], [])
FRONT_ORDER = [
    "pack_mule",
    "trail_horse",
    "sky_griffin",
    "backpack",
    "travel_tunic",
    "rogue_cloak",
    "scholar_book",
    "arcane_robe",
    "star_robe",
    "explorer_coat",
    "leather_armor",
    "chain_armor",
    "plate_armor",
    "walking_boots",
    "expedition_boots",
    "memory_helm",
    "explorer_hood",
    "scarf",
    "compass",
    "rusty_sword",
    "training_sword",
    "steel_sword",
    "veteran_blade",
    "precision_bow",
    "wood_staff",
    "crystal_staff",
    "spyglass",
    "lantern",
    "memory_shield",
]


class CharacterView(tk.Canvas):
    """Composites pre-rendered PNG layers; equipment is decorative only."""

    def __init__(self, parent, app, equipped=(), backdrop=True, bg=None, look=None):
        super().__init__(
            parent,
            width=300,
            height=320,
            bg=bg or background_of(parent) or app.surface,
            highlightthickness=0,
        )
        self.app = app
        self.look = look
        self.backdrop = backdrop and app.store.pref("rpg_effects", True)
        self.equipped = set(equipped)
        self.bind("<Configure>", lambda e: self.draw())

    def set_equipped(self, equipped):
        self.equipped = set(equipped)
        self.draw()

    def draw(self):
        self.delete("all")
        p = self.app.motion.palette
        w, h = self.winfo_width(), self.winfo_height()
        cx, cy = w / 2, h / 2 + 4
        if self.backdrop:
            # Compass rose: the RUMO motif, drawn as thin rings and bearings.
            outer = max(60, min(w, h) / 2 - 22)
            for radius, color in [(outer, p["border"]), (outer - 28, p["track"])]:
                self.create_oval(
                    cx - radius, cy - radius, cx + radius, cy + radius, outline=color
                )
            for angle in range(0, 360, 15):
                long = angle % 90 == 0
                inner = outer - (14 if long else 6)
                rad = math.radians(angle)
                self.create_line(
                    cx + inner * math.sin(rad),
                    cy - inner * math.cos(rad),
                    cx + outer * math.sin(rad),
                    cy - outer * math.cos(rad),
                    fill=p["accent"] if long else p["strong"],
                    width=1,
                )
            self.create_text(
                cx,
                cy - outer - 11,
                text="N",
                fill=p["accent"],
                font=ui_font(self, DISPLAY, 9, "bold"),
            )
        look = self.look or self.app.character_look()
        back, front = look_layers(self.app, look, "full")
        layers = []
        for item in FRONT_ORDER:
            if item in self.equipped:
                layers += [f"character/{n}.png" for n in EQUIPMENT_LAYERS[item][0]]
        layers += back + front
        for item in FRONT_ORDER:
            if item in self.equipped:
                layers += [f"character/{n}.png" for n in EQUIPMENT_LAYERS[item][1]]
        self._layer_images = []
        for path in layers:
            if "glow" in path and not self.app.store.pref("rpg_effects", True):
                continue
            image = load_image(self.app, path)
            self._layer_images.append(image)
            self.create_image(cx, cy, image=image)


class Portrait(tk.Canvas):
    """Circular bust made of the appearance layers (264 px source).

    Sizes that divide 264 (88, 44, 132) are reduced by Tk's integer subsample.
    """

    def __init__(self, parent, app, size=88, look=None, bg=None, ring=True):
        self.surround = bg or background_of(parent) or app.surface
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=self.surround,
            highlightthickness=0,
        )
        self.app, self.size, self.look, self.ring = app, size, look, ring
        self.static_bg = True  # the circular mask is baked in this color
        self.bind("<Configure>", lambda e: self.draw())

    def set_look(self, look):
        self.look = look
        self.draw()

    def mask(self):
        """Opaque corners in the background color, transparent inside the circle."""
        cache = self.app.__dict__.setdefault("images", {})
        key = f"ring-{self.size}-{self.surround}"
        if key not in cache:
            size = self.size
            image = tk.PhotoImage(width=size, height=size)
            image.put(self.surround, to=(0, 0, size, size))
            radius = size / 2 - 1
            for y in range(size):
                dy = y + 0.5 - size / 2
                if abs(dy) > radius:
                    continue
                dx = (radius * radius - dy * dy) ** 0.5
                for x in range(int(size / 2 - dx + 0.5), int(size / 2 + dx + 0.5)):
                    image.transparency_set(x, y, True)
            cache[key] = image
        return cache[key]

    def draw(self):
        self.delete("all")
        p = self.app.motion.palette
        size = self.size
        factor = max(1, round(264 / size))
        look = self.look or self.app.character_look()
        back, front = look_layers(self.app, look, "bust")
        disc = blend(p["surface"], p["primary"], 0.16)
        if self.ring:
            self.create_oval(1, 1, size - 1, size - 1, fill=disc, outline="")
        else:
            rounded(self, 0, 0, size, size, 16, fill=disc, outline="")
        self._layer_images = []
        for path in back + front:
            image = load_image(self.app, path, factor)
            self._layer_images.append(image)
            self.create_image(size / 2, size / 2, image=image)
        if self.ring:
            self.create_image(size / 2, size / 2, image=self.mask())
            self.create_oval(1, 1, size - 2, size - 2, outline=p["primary"], width=2)


class FocusDial(tk.Canvas):
    def __init__(self, parent, app):
        super().__init__(parent, width=380, height=300, bg=app.bg, highlightthickness=0)
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
        h = self.winfo_height()
        p = self.app.motion.palette
        cx, cy = w / 2, h / 2
        radius = min(132, h / 2 - 12)
        for minute in range(60):
            rad = math.radians(minute * 6)
            long = minute % 5 == 0
            outer = radius + 10
            inner = outer - (6 if long else 3)
            self.create_line(
                cx + inner * math.sin(rad),
                cy - inner * math.cos(rad),
                cx + outer * math.sin(rad),
                cy - outer * math.cos(rad),
                fill=p["strong"] if long else p["border"],
            )
        box = (cx - radius, cy - radius, cx + radius, cy + radius)
        self.create_oval(*box, outline=p["track"], width=10)
        if self.progress > 0:
            self.create_arc(
                *box,
                start=90,
                extent=-min(359.9, max(0.1, self.progress) * 3.6),
                style="arc",
                outline=p["primary"] if self.running else p["muted"],
                width=10,
            )
        state = "EM FOCO" if self.running else "PAUSADO"
        icon = glyph(self, "play" if self.running else "pause")
        color = p["accent"] if self.running else p["muted"]
        words = ui_font(self, size=9, weight="bold")
        icons = ui_font(self, ICON, 10)
        span = words.measure(state) + (icons.measure(icon) + 6 if icon else 0)
        x = cx - span / 2
        if icon:
            self.create_text(x, cy - 46, text=icon, anchor="w", fill=color, font=icons)
            x += icons.measure(icon) + 6
        self.create_text(x, cy - 46, text=state, anchor="w", fill=color, font=words)
        tabular(
            self,
            cx,
            cy,
            self.text or "00:00:00",
            ui_font(self, size=34, weight="bold"),
            p["fg"],
        )
        self.create_text(
            cx,
            cy + 46,
            text=f"{self.progress:.0f}% do tempo previsto",
            fill=p["muted"],
            font=ui_font(self, size=9),
        )
