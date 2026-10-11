"""Responsive native charts with clear units, restrained color and hover details."""

import math
import tkinter as tk
from ui import rounded
from core import duration, ratio, percentage


def question_summary(app, stats):
    canvas = tk.Canvas(app.content, height=195, bg=app.surface, highlightthickness=0)
    canvas.pack(fill="x", pady=12)

    def draw(event=None):
        canvas.delete("all")
        total = stats["correct"] + stats["wrong"] + stats["blank"]
        angle = 90
        canvas.create_oval(22, 25, 158, 161, outline=app.border, width=12)
        for value, color, label, index in zip(
            [stats["correct"], stats["wrong"], stats["blank"]],
            [app.motion.palette["accent"], app.motion.palette["error"], "#959DA9"],
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
                + (f"  •  {value/total*100:.0f}%" if total else ""),
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
            text=percentage(stats["rate"]) + " de acertos",
            anchor="w",
            fill=app.fg,
            font=("Inter", 12, "bold"),
        )
        canvas.create_text(
            22,
            183,
            text="Aproveitamento = acertos ÷ respostas. Brancos ficam separados.",
            anchor="w",
            fill=app.muted,
            font=("Inter", 8),
            width=max(250, canvas.winfo_width() - 44),
        )

    canvas.bind("<Configure>", draw)
    app.motion.idle(canvas, draw)
    return canvas


def bars(app, rows, metric="elapsed", performance=False):
    canvas = tk.Canvas(app.content, height=290, bg=app.surface, highlightthickness=0)
    canvas.pack(fill="x", pady=10)
    phase = [0 if app.motion.enabled else 1]
    shown = rows[-60:]

    def draw(event=None):
        canvas.delete("all")
        width = max(240, canvas.winfo_width())
        left = 52
        right = 54 if performance else 24
        top = 38
        bottom = 232
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
            left,
            16,
            text={
                "elapsed": "Tempo líquido",
                "target": "Tempo planejado",
                "questions": "Questões apresentadas",
                "score": "Pontuação",
                "correct": "Acertos",
                "wrong": "Erros",
            }.get(metric, metric)
            + " • "
            + unit,
            anchor="w",
            fill=app.muted,
            font=("Inter", 9),
        )
        if performance:
            canvas.create_text(
                width - right,
                16,
                text="● Acerto (%)",
                anchor="e",
                fill=app.motion.palette["success"],
                font=("Inter", 8),
            )
        if not shown or not any(values):
            canvas.create_text(
                width / 2,
                118,
                text="Seu progresso começa com o primeiro registro.",
                fill=app.fg,
                font=("Inter", 11),
                width=width - 48,
            )
            canvas.create_text(
                width / 2,
                170,
                text="Registre uma sessão para acompanhar esta evolução.",
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
                    277,
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
                    label[5:] if len(label) == 10 and label[4] == "-" else label[-10:]
                )
                canvas.create_text(
                    x, 250, text=label, fill=app.muted, font=("Inter", 8)
                )
            if count <= 8:
                canvas.create_text(
                    x,
                    min(y, baseline) - 12,
                    text=f"{v:g}",
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
                            fill=app.motion.palette["success"],
                            width=2.5,
                        )
                    canvas.create_oval(
                        x - 3,
                        yy - 3,
                        x + 3,
                        yy + 3,
                        fill=app.motion.palette["success"],
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


def distribution(app, rows):
    shown = sorted(
        (r for r in rows if r["elapsed"] > 0), key=lambda r: r["elapsed"], reverse=True
    )[:15]
    canvas = tk.Canvas(
        app.content,
        height=max(100, len(shown) * 54 + 24),
        bg=app.surface,
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
                text=f"{duration(row['elapsed'])} • {row['elapsed']/total*100:.0f}%",
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
