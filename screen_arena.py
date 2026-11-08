"""Arena: local question bank, its panel and one round at a time.

The screen never touches SQL. It asks ``app.arena`` for the bank and for a
``Round``, and every finished round becomes an ordinary "Questões" session.
"""

import tkinter as tk
import time

from theme import number, percent
from ui import Chip, MotionButton
from ui_kit import (
    ActionMenu,
    Card,
    Row,
    Section,
    empty,
    label,
    palette,
    stat_row,
    wrapping,
)

import arena_ui

TYPING = (tk.Entry, tk.Text, tk.Spinbox)

HELP = (
    "A Arena usa as questões que você cria ou importa. Cada rodada vira uma "
    "sessão de estudo de Questões, com acertos e erros no histórico.\n\n"
    "Certo/Errado e múltipla escolha. Questões anuladas aparecem, mas não "
    "contam como acerto nem erro."
)


def render(app):
    """Panel: summary, subjects with questions and the ways to feed the bank."""
    summary = app.arena.summary(app.plan)
    topics = app.arena.topics(app.plan)
    top = tk.Frame(app.content, bg=app.bg)
    top.pack(fill="x", pady=(0, 14))
    stat_row(
        top,
        app,
        [
            (number(summary.get("questions", 0)), "questões"),
            (number(summary.get("answered", 0)), "respondidas"),
            (
                percent(summary.get("accuracy")),
                "de aproveitamento",
                "Acertos ÷ respostas dadas, sem contar as anuladas.",
            ),
            (
                number(summary.get("to_redo", 0)),
                "para refazer",
                "Questões cuja última tentativa foi um erro.",
            ),
        ],
    ).pack(side="left", anchor="n")
    ActionMenu(
        top,
        app,
        [
            ("Nova questão", lambda: arena_ui.edit_question(app)),
            ("Importar pacote", lambda: arena_ui.import_pack(app)),
            ("Banco de questões", lambda: arena_ui.question_bank(app)),
            None,
            ("Como funciona a Arena", lambda: _help(app)),
        ],
        text="Ações",
        icon="ellipsis",
        style="Accent.TButton",
    ).pack(side="right", anchor="n")

    if not summary.get("questions"):
        card = Card(app.content, app, padding=(24, 40))
        card.pack(fill="x")
        empty(
            card.body,
            app,
            "swords",
            "Nenhuma questão ainda",
            "Crie uma questão ou importe um pacote JSON com gabarito e comentário. "
            "As tentativas entram no seu histórico como qualquer sessão de Questões.",
            [
                ("Criar questão", lambda: arena_ui.edit_question(app), "plus"),
                ("Importar pacote", lambda: arena_ui.import_pack(app), "upload"),
            ],
        ).pack(fill="x")
        return
    if not topics:
        card = Card(app.content, app, padding=(24, 36))
        card.pack(fill="x")
        empty(
            card.body,
            app,
            "archive",
            "Nenhuma questão disponível",
            "Todas as questões estão retiradas. Reative-as no banco de questões "
            "ou crie uma nova.",
            [
                ("Abrir banco", lambda: arena_ui.question_bank(app), "list"),
                ("Criar questão", lambda: arena_ui.edit_question(app), "plus"),
            ],
        ).pack(fill="x")
        return

    Section(app.content, app, "Assuntos", count=len(topics)).pack(fill="x", pady=(4, 8))
    card = Card(app.content, app, padding=(14, 8))
    card.pack(fill="x")
    for topic in topics:
        topic_row(app, card.body, topic)


def topic_row(app, parent, topic):
    unanswered = int(topic.get("unanswered") or 0)
    to_redo = int(topic.get("to_redo") or 0)

    def train(mode=None):
        mode = mode or ("novas" if unanswered else "todas")
        try:
            started = app.arena.start_round(
                app.plan, topic["topic_id"], mode=mode, limit=10
            )
        except ValueError as exc:
            app.notify(str(exc), title="Arena", icon="info", tone="info")
            return
        play(app, started)

    detail = " · ".join(
        [
            topic.get("subject", ""),
            f"{number(topic.get('total', 0))} questões",
            f"{number(unanswered)} novas",
            f"{number(to_redo)} para refazer",
        ]
    )
    row = Row(parent, app, topic.get("topic", ""), detail, on_open=train, pady=9)
    row.pack(fill="x")
    if to_redo:
        redo = MotionButton(
            row.trail,
            text="Refazer erros",
            icon="rotate-ccw",
            style="Ghost.TButton",
            height=32,
            command=lambda: train("refazer"),
        )
        redo.pack(side="right", padx=(10, 0))
    start = MotionButton(
        row.trail,
        text="Treinar",
        icon="play",
        height=32,
        command=train,
    )
    start.pack(side="right", padx=(10, 0))
    row.refresh_bindings()


def play(app, round_):
    """Replace the page with the round; returns the view for tests and focus."""
    for child in app.content.winfo_children():
        child.destroy()
    view = RoundView(app, round_)
    view.pack(fill="both", expand=True)
    view.focus_set()
    return view


class RoundView(tk.Frame):
    """One round rendered inside the page: question, correction and clock."""

    def __init__(self, app, round_):
        super().__init__(app.content, bg=app.bg)
        self.app = app
        self.round = round_
        self.index = 0
        self.answered = False
        self.finished = False
        self.last_result = None
        self.started = time.monotonic()
        self._timer = None
        self._binds = []
        self._choices = []
        self._ce_buttons = []
        self._build_header()
        self.statement = wrapping(
            label(self, app, "", size=12, justify="left", anchor="w"), margin=8
        )
        self.statement.pack(fill="x", pady=(6, 14))
        self.choices = tk.Frame(self, bg=app.bg)
        self.choices.pack(fill="x")
        self.feedback = tk.Frame(self, bg=app.bg)
        self.feedback.pack(fill="x", pady=(14, 0))
        self._build_footer()
        self._bind_keys()
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._tick()
        self._render_question()

    def _build_header(self):
        head = tk.Frame(self, bg=self.app.bg)
        head.pack(fill="x", pady=(0, 8))
        self.elapsed = label(head, self.app, "00:00", size=10, tone="muted")
        self.elapsed.pack(side="right")
        self.progress = label(head, self.app, "", size=10, tone="muted")
        self.progress.pack(side="right", padx=(0, 16))
        self.title = label(head, self.app, self._title(), size=12, weight="bold")
        self.title.pack(side="left")

    def _build_footer(self):
        foot = tk.Frame(self, bg=self.app.bg)
        foot.pack(fill="x", pady=(20, 0))
        MotionButton(
            foot,
            text="Encerrar",
            icon="x",
            style="Ghost.TButton",
            command=self.finish,
        ).pack(side="left")
        self.next_button = MotionButton(
            foot,
            text="Próxima",
            icon="arrow-right",
            style="Accent.TButton",
            state="disabled",
            command=self.advance,
        )
        self.next_button.pack(side="right")

    def _title(self):
        subjects = self.app.subject_map()
        subject = next(
            (name for name, rid in subjects.items() if rid == self.round.subject_id),
            "",
        )
        topics = self.app.topic_map(self.round.subject_id) if subject else {}
        topic = next(
            (name for name, rid in topics.items() if rid == self.round.topic_id),
            "",
        )
        title = " › ".join(part for part in (subject, topic) if part) or "Arena"
        if len(title) > 80:
            title = title[:79].rstrip() + "…"
        return title

    def _render_question(self):
        for widget in self.choices.winfo_children() + self.feedback.winfo_children():
            widget.destroy()
        self._choices = []
        self._ce_buttons = []
        self.answered = False
        self.last_result = None
        self.next_button.configure(
            text="Concluir" if self._last() else "Próxima", state="disabled"
        )
        question = self.current
        self.progress.configure(text=f"{self.index + 1}/{len(self.round.questions)}")
        self.statement.configure(text=question.get("statement", ""))
        if question.get("status") == "anulada":
            Chip(self.choices, text="Anulada", tone="warning").pack(anchor="w")
        if question.get("kind") == "certo-errado":
            self._build_certo_errado()
        else:
            self._build_options()
        self.focus_set()

    def _build_certo_errado(self):
        row = tk.Frame(self.choices, bg=self.app.bg)
        row.pack(fill="x", pady=(10, 0))
        for text, choice, icon in (
            ("Certo", "certo", "check"),
            ("Errado", "errado", "x"),
        ):
            button = MotionButton(
                row,
                text=text,
                icon=icon,
                height=38,
                command=lambda value=choice: self.answer(value),
            )
            button.pack(side="left", padx=(0, 8))
            self._ce_buttons.append(button)

    def _build_options(self):
        for option in self.current.get("options") or []:
            self._choices.append(self._option(option["id"], option["text"]))

    def _option(self, letter, text):
        p = palette(self.app)
        frame = tk.Frame(
            self.choices,
            bg=p["raised"],
            cursor="hand2",
            takefocus=True,
            highlightthickness=1,
            highlightbackground=p["border"],
        )
        frame.pack(fill="x", pady=3)
        inner = tk.Frame(frame, bg=p["raised"])
        inner.pack(fill="x", padx=12, pady=8)
        badge = label(
            inner, self.app, letter.upper(), size=10, weight="bold", tone="accent"
        )
        badge.pack(side="left", padx=(0, 12))
        body = wrapping(label(inner, self.app, text, size=10, justify="left"), margin=8)
        body.pack(side="left", fill="x", expand=True)
        parts = (frame, inner, badge, body)
        for widget in parts:
            widget.bind("<Button-1>", lambda e, value=letter: self.answer(value))
        frame.bind("<Return>", lambda e, value=letter: self.answer(value))
        frame.bind("<space>", lambda e, value=letter: self.answer(value))
        return {"id": letter, "parts": parts}

    @property
    def current(self):
        return self.round.questions[self.index]

    def _last(self):
        return self.index + 1 >= len(self.round.questions)

    def answer(self, choice):
        if self.answered or self.finished:
            return
        question = self.current
        try:
            result = self.round.answer(question["id"], choice)
        except ValueError as exc:
            self.app.notify(str(exc), title="Arena", icon="info", tone="info")
            return
        self.answered = True
        self.last_result = result
        self._show_result(question, choice, result)
        self.next_button.configure(state="normal")
        self.next_button.focus_set()

    def _show_result(self, question, choice, result):
        p = palette(self.app)
        correct = result.get("correct")
        if correct is None:
            tone, title = "muted", "Questão anulada"
            detail = "Esta questão foi anulada e não conta como acerto nem erro."
        elif correct:
            tone, title = "success", "Certo"
            detail = "Você respondeu: " + _choice_text(question, choice)
        else:
            tone, title = "error", "Errado"
            detail = "Você respondeu: " + _choice_text(question, choice)
        if correct is not None:
            expected = _choice_text(question, result.get("expected"))
            detail += " · Gabarito: " + (expected or "anulada")
        label(self.feedback, self.app, title, size=11, weight="bold", tone=tone).pack(
            anchor="w"
        )
        label(self.feedback, self.app, detail, size=9, tone="muted").pack(
            anchor="w", pady=(2, 0)
        )
        comment = (result.get("comment") or "").strip()
        if comment:
            note = wrapping(
                label(self.feedback, self.app, comment, size=10, tone="muted"),
                margin=8,
            )
            note.pack(fill="x", pady=(6, 0))
        if correct is not None:
            self._paint_choices(question, choice, result.get("expected"))
        for button in self._ce_buttons:
            button.configure(state="disabled")

    def _paint_choices(self, question, choice, expected):
        p = palette(self.app)
        colors = {"correct": p["success_bg"], "wrong": p["error_bg"]}
        for item in self._choices:
            tone = None
            if item["id"] == expected:
                tone = "correct"
            elif item["id"] == choice:
                tone = "wrong"
            color = colors.get(tone, p["raised"])
            border = (
                p["success"]
                if tone == "correct"
                else p["error"] if tone == "wrong" else p["border"]
            )
            for widget in item["parts"]:
                widget.configure(bg=color)
            item["parts"][0].configure(highlightbackground=border)
            ink = p["success"] if tone == "correct" else p["error"] if tone else p["fg"]
            for widget in item["parts"][2:]:
                widget.configure(fg=ink if tone else widget.cget("fg"))

    def advance(self):
        if self.finished or not self.answered:
            return
        if self._last():
            self.finish()
            return
        self.index += 1
        self._render_question()

    def finish(self):
        if self.finished:
            return
        self.finished = True
        self._cancel_timer()
        self._unbind()
        seconds = max(0, int(time.monotonic() - self.started))
        try:
            session_id = self.app.arena.finish_round(self.round, seconds)
        except ValueError as exc:
            self.app.notify(str(exc), title="Arena", icon="info", tone="info")
            self.app.refresh()
            return
        if session_id:
            self.app.after_arena_session(session_id)
        else:
            self.app.notify(
                "Nada respondido — nenhuma sessão foi registrada.",
                title="Rodada encerrada",
                icon="info",
                tone="info",
            )
        self.app.refresh()

    def _tick(self):
        self._timer = self.after(1000, self._tick)
        elapsed = max(0, int(time.monotonic() - self.started))
        minutes, seconds = divmod(elapsed, 60)
        self.elapsed.configure(text=f"{minutes:02d}:{seconds:02d}")

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        self._cancel_timer()
        self._unbind()

    def _cancel_timer(self):
        if self._timer is not None:
            try:
                self.after_cancel(self._timer)
            except tk.TclError:
                pass
            self._timer = None

    def _bind_keys(self):
        sequences = [f"<Key-{digit}>" for digit in range(1, 10)] + [
            "<Key-c>",
            "<Key-C>",
            "<Key-e>",
            "<Key-E>",
        ]
        for sequence in sequences:
            funcid = self.app.root.bind(sequence, self._on_key, add="+")
            self._binds.append((sequence, funcid))
        self.bind("<Return>", self._on_return)
        self.bind("<KP_Enter>", self._on_return)

    def _unbind(self):
        for sequence, funcid in self._binds:
            try:
                self.app.root.unbind(sequence, funcid)
            except tk.TclError:
                pass
        self._binds = []

    def _on_return(self, event):
        if self.answered:
            self.advance()
        return "break"

    def _on_key(self, event):
        # Root-level keys reach text fields too; typing must never answer.
        if self.finished or self.answered or isinstance(event.widget, TYPING):
            return
        question = self.current
        key = event.keysym.lower()
        if question.get("kind") == "certo-errado":
            if key == "c":
                self.answer("certo")
            elif key == "e":
                self.answer("errado")
            elif key == "1":
                self.answer("certo")
            elif key == "2":
                self.answer("errado")
            return
        if len(key) == 1 and key.isdigit():
            options = question.get("options") or []
            position = int(key) - 1
            if 0 <= position < len(options):
                self.answer(options[position]["id"])

    def destroy(self):
        self._cancel_timer()
        self._unbind()
        super().destroy()


def _choice_text(question, choice):
    if not choice:
        return ""
    if question.get("kind") == "certo-errado":
        return choice.capitalize()
    for option in question.get("options") or []:
        if option["id"] == choice:
            return option["id"].upper() + " — " + option["text"]
    return str(choice).upper()


def _help(app):
    from app import messagebox

    messagebox.showinfo("Arena", HELP, parent=app.root)
