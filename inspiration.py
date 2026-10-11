"""One sourced excerpt per local date, stable across reopening and leap years."""

import json
from functools import lru_cache
from datetime import date
from tkinter import ttk
from ui import Panel, MotionButton


@lru_cache(maxsize=1)
def corpus(path):
    quotes = json.loads(path.read_text(encoding="utf-8"))
    if len(quotes) != 150:
        raise ValueError("A coleção diária deve conter 150 frases.")
    return quotes


def daily(path, today):
    quotes = corpus(path)
    index = (today - date(2026, 1, 1)).days % len(quotes)
    return index, quotes[index]


def header(app, parent, path):
    _, quote = daily(path, app.today())
    area = ttk.Frame(parent, padding=(0, 6))
    area.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
    MotionButton(
        area,
        text="Fonte da frase",
        height=32,
        command=lambda: app.open_link(quote["source"]),
    ).pack(side="right", padx=(12, 0))
    text = ttk.Frame(area)
    text.pack(side="left", fill="x", expand=True)
    label = ttk.Label(
        text,
        text="“" + quote["text"] + "”",
        font=("Inter", 10, "bold"),
        wraplength=1000,
        justify="left",
    )
    label.pack(fill="x")
    label.bind(
        "<Configure>",
        lambda e: (
            label.configure(wraplength=max(100, e.width - 8))
            if int(label.cget("wraplength")) != max(100, e.width - 8)
            else None
        ),
    )
    ttk.Label(
        text,
        text=quote["author"] + " • " + quote["reference"],
        style="Muted.TLabel",
        font=("Inter", 8),
        wraplength=900,
    ).pack(anchor="w", pady=(3, 0))
    return area


def render(app, path, parent=None):
    index, quote = daily(path, app.today())
    panel = Panel(parent or app.content, app)
    panel.pack(fill="x", pady=(12, 0))
    header = ttk.Frame(panel.body, style="Panel.TFrame")
    header.pack(fill="x")
    ttk.Label(
        header,
        text=f"Pensamento do dia • {index+1}/150",
        style="PanelMuted.TLabel",
        font=("Inter", 8),
    ).pack(side="left")
    MotionButton(
        header, text="Fonte", height=30, command=lambda: app.open_link(quote["source"])
    ).pack(side="right")
    label = ttk.Label(
        panel.body,
        text="“" + quote["text"] + "”",
        style="Panel.TLabel",
        font=("Inter", 12),
        wraplength=850,
        justify="left",
    )
    label.pack(fill="x", pady=(8, 10))
    label.bind(
        "<Configure>",
        lambda e: (
            label.configure(wraplength=max(100, e.width - 8))
            if int(label.cget("wraplength")) != max(100, e.width - 8)
            else None
        ),
    )
    for text in [quote["author"] + " • " + quote["reference"], quote["kind"]]:
        detail = ttk.Label(
            panel.body,
            text=text,
            style="PanelMuted.TLabel",
            font=("Inter", 8),
            wraplength=350,
        )
        detail.pack(fill="x", pady=(3, 0))
        detail.bind(
            "<Configure>",
            lambda e, w=detail: (
                w.configure(wraplength=max(100, e.width - 8))
                if int(w.cget("wraplength")) != max(100, e.width - 8)
                else None
            ),
        )
