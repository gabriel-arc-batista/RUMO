"""Responsive native charts with clear units, restrained color and hover details."""

import math
import tkinter as tk
from ui import background_of, rounded
from core import duration, ratio, percentage
from theme import compact_duration, percent


def question_summary(app, stats, parent=None):
    host = parent or app.content
    canvas = tk.Canvas(
        host, height=195, bg=background_of(host) or app.surface, highlightthickness=0
    )
    canvas.pack(fill="x", pady=12)
    p = app.motion.palette

    def draw(event=None):
        canvas.delete("all")
        total = stats["correct"] + stats["wrong"] + stats["blank"]
        angle = 90
        canvas.create_oval(22, 25, 158, 161, outline=app.border, width=12)
        for value, color, label, index in zip(
            [stats["correct"], stats["wrong"], stats["blank"]],
            [p["success"], p["error"], p["faint"]],
            ["Acertos", "Erros", "Em branco"],
            range(3),
        ):
            extent = value / total * 360 if total else 0
            if extent:
                canvas.create_arc(
                    22,
                    25,
                    158,
                    161,
                    start=angle,
                    extent=extent,
                    style="arc",
                    outline=color,
                    width=12,
                )
                angle += extent
            y = 75 + index * 32
            canvas.create_oval(191, y - 4, 199, y + 4, fill=color, outline="")
            canvas.create_text(
                212,
                y,
                text=f"{label}  {value}"
                + (f"  ·  {value/total*100:.0f}%" if total else ""),
                anchor="w",
                fill=app.fg,
                font=("Inter", 10),
            )
        canvas.create_text(
            90, 85, text=str(total), fill=app.fg, font=("Inter", 22, "bold")
        )
        canvas.create_text(90, 113, text="questões", fill=app.muted, font=("Inter", 8))
        canvas.create_text(
            191,
            30,
            text=(
                percent(stats["rate"], 1) + " de acertos nas respondidas"
                if stats["rate"] is not None
                else "Nenhuma questão respondida neste filtro"
            ),
            anchor="w",
            fill=app.fg,
            font=("Inter", 12, "bold"),
        )
        canvas.create_text(
            22,
            183,
            text="Acertos ÷ (acertos + erros). Questões em branco ficam de fora da conta.",
            anchor="w",
            fill=app.muted,
            font=("Inter", 8),
            width=max(250, canvas.winfo_width() - 44),
        )

    canvas.bind("<Configure>", draw)
    app.motion.idle(canvas, draw)
    return canvas


TITLES = {
    "elapsed": "Horas líquidas",
    "target": "Horas planejadas",
    "questions": "Questões feitas",
    "score": "Pontuação",
    "rate": "Aproveitamento (%)",
    "correct": "Acertos",
    "wrong": "Erros",
}
EMPTY = (
    "Seu progresso começa com o primeiro registro.",
    "Registre uma sessão para acompanhar esta evolução.",
)


def bars(
    app,
    rows,
    metric="elapsed",
    performance=False,
    parent=None,
    title=None,
    empty=EMPTY,
    height=290,
):
    """Bar chart of ``metric`` per row; ``performance`` adds the accuracy line.

    ``title`` names the measure with its unit in Portuguese; ``empty`` is the
    (headline, hint) shown when there is nothing to plot.
    """
    host = parent or app.content
    surface = background_of(host) or app.surface
    canvas = tk.Canvas(host, height=height, bg=surface, highlightthickness=0)
    canvas.pack(fill="x", pady=10)
    line = app.motion.palette.get("secondary", app.motion.palette["info"])
    phase = [0 if app.motion.enabled else 1]
    shown = rows[-60:]

    def draw(event=None):
        canvas.delete("all")
        width = max(240, canvas.winfo_width())
        left = 52
        right = 54 if performance else 24
        top = 38
        bottom = height - 58
        plot = width - left - right

        def value(r):
            return (
                r[metric] / 3600
                if metric in ["elapsed", "target"]
                else (
                    r["correct"] + r["wrong"] + r["blank"]
                    if metric == "questions"
                    else r.get(metric, 0)
                )
            )

        values = [value(r) for r in shown]
        maximum = max(values + [1])
        minimum = min(values + [0])
        span = maximum - minimum
        if maximum > 1:
            maximum = math.ceil(maximum / 4) * 4
            span = maximum - minimum
        unit = (
            "h"
            if metric in ["elapsed", "target"]
            else "questões" if metric in ["questions", "correct", "wrong"] else "pontos"
        )
        color = (
            app.motion.palette["error"]
            if metric == "wrong"
            else app.motion.palette["accent"]
        )
        canvas.create_text(
            left - 40,
            16,
            text=title or TITLES.get(metric, unit.capitalize()),
            anchor="w",
            fill=app.muted,
            font=("Inter", 9),
        )
        if performance:
            canvas.create_line(
                width - right - 120, 16, width - right - 104, 16, fill=line, width=2.5
            )
            canvas.create_text(
                width - right - 98,
                16,
                text="acertos (%)",
                anchor="w",
                fill=app.muted,
                font=("Inter", 8),
            )
        if not shown or not any(values):
            canvas.create_text(
                width / 2,
                height / 2 - 26,
                text=empty[0],
                fill=app.fg,
                font=("Inter", 11),
                width=width - 48,
            )
            canvas.create_text(
                width / 2,
                height / 2 + 4,
                text=empty[1],
                fill=app.muted,
                font=("Inter", 9),
                width=width - 48,
            )
            return
        for i in range(5):
            y = bottom - (bottom - top) * i / 4
            canvas.create_line(left, y, width - right, y, fill=app.border, dash=(2, 5))
            number = minimum + span * i / 4
            canvas.create_text(
                left - 12,
                y,
                text=f"{number:g}",
                anchor="e",
                fill=app.muted,
                font=("Inter", 8),
            )
            if performance:
                canvas.create_text(
                    width - right + 10,
                    y,
                    text=f"{i*25}%",
                    anchor="w",
                    fill=app.muted,
                    font=("Inter", 7),
                )
        count = len(shown)
        cell = plot / count
        baseline = bottom + (bottom - top) * minimum / span
        previous = None
        for i, (row, v) in enumerate(zip(shown, values)):
            x = left + (i + 0.5) * cell
            y = baseline - (bottom - top) * v / span * phase[0]
            bar_width = min(32, cell * 0.55)
            tag = f"bar{i}"
            rounded(
                canvas,
                x - bar_width / 2,
                min(y, baseline),
                bar_width,
                max(2, abs(y - baseline)),
                min(5, bar_width / 3),
                fill=color,
                outline="",
                tags=(tag,),
            )

            def hover(event, r=row):
                canvas.delete("hover")
                text = f"{r['label']}  •  {duration(r['elapsed'])}  •  {r['correct']+r['wrong']} respondidas  •  {percentage(ratio(r['correct'],r['wrong']))}"
                canvas.create_text(
                    width / 2,
                    height - 13,
                    text=text,
                    width=width - 32,
                    fill=app.fg,
                    font=("Inter", 8),
                    tags="hover",
                )

            canvas.tag_bind(tag, "<Enter>", hover)
            canvas.tag_bind(tag, "<Leave>", lambda e: canvas.delete("hover"))
            if count <= 10 or i % max(1, math.ceil(count / 8)) == 0:
                label = str(row["label"])
                label = (
                    f"{label[8:10]}/{label[5:7]}"
                    if len(label) == 10 and label[4] == "-"
                    else label[-10:]
                )
                canvas.create_text(
                    x, bottom + 18, text=label, fill=app.muted, font=("Inter", 8)
                )
            if count <= 8:
                canvas.create_text(
                    x,
                    min(y, baseline) - 12,
                    text=(
                        compact_duration(v * 3600)
                        if metric in ["elapsed", "target"]
                        else (
                            f"{v:.0f}%"
                            if metric == "rate"
                            else f"{v:g}".replace(".", ",")
                        )
                    ),
                    fill=app.fg,
                    font=("Inter", 8),
                )
            if performance:
                rate = ratio(row["correct"], row["wrong"])
                if rate is None:
                    previous = None
                else:
                    yy = bottom - (bottom - top) * rate / 100
                    if previous:
                        canvas.create_line(
                            *previous,
                            x,
                            yy,
                            fill=line,
                            width=2.5,
                        )
                    canvas.create_oval(
                        x - 3,
                        yy - 3,
                        x + 3,
                        yy + 3,
                        fill=line,
                        outline="",
                    )
                    previous = (x, yy)

    canvas.bind("<Configure>", draw)
    app.motion.idle(
        canvas,
        lambda: app.motion.animate(
            canvas, lambda t: (phase.__setitem__(0, t), draw()), 360
        ),
    )
    return canvas


def distribution(app, rows, parent=None, limit=15):
    shown = sorted(
        (r for r in rows if r["elapsed"] > 0), key=lambda r: r["elapsed"], reverse=True
    )[:limit]
    host = parent or app.content
    canvas = tk.Canvas(
        host,
        height=max(100, len(shown) * 54 + 24),
        bg=background_of(host) or app.surface,
        highlightthickness=0,
    )
    canvas.pack(fill="x", pady=10)
    total = sum(r["elapsed"] for r in rows)
    maximum = max([r["elapsed"] for r in shown] + [1])

    def draw(event=None):
        canvas.delete("all")
        w = max(260, canvas.winfo_width())
        for i, row in enumerate(shown):
            y = 12 + i * 54
            label = row["label"]
            canvas.create_text(
                14,
                y,
                text=label[: int(max(20, (w - 170) / 8))],
                anchor="nw",
                fill=app.fg,
                font=("Inter", 9),
            )
            canvas.create_text(
                w - 14,
                y,
                text=f"{compact_duration(row['elapsed'])} · {row['elapsed']/total*100:.0f}%",
                anchor="ne",
                fill=app.muted,
                font=("Inter", 8),
            )
            rounded(canvas, 14, y + 28, w - 28, 6, 3, fill=app.border, outline="")
            item = rounded(
                canvas,
                14,
                y + 28,
                max(6, (w - 28) * row["elapsed"] / maximum),
                6,
                3,
                fill=app.motion.palette["accent"],
                outline="",
            )
            canvas.tag_bind(
                item, "<Button-1>", lambda e, name=label: app.open_subject_name(name)
            )
        if not shown:
            canvas.create_text(
                w / 2,
                50,
                text="Estude uma matéria para ver a distribuição do seu tempo.",
                fill=app.muted,
                font=("Inter", 9),
                width=w - 40,
            )

    canvas.bind("<Configure>", draw)
    app.motion.idle(canvas, draw)
    return canvas
