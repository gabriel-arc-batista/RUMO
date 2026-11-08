"""Flashcards: baralho próprio, agenda offline e rodadas; tudo via ``app.cards``.

A revisão acontece no próprio ``app.content``: frente → "Mostrar resposta" →
verso e explicação → Errei / Difícil / Bom / Fácil. Os atalhos 1–4 ficarão
ligados à raiz só durante a rodada e saem ao encerrá-la ou destruir a tela.
"""

import os
import uuid
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk

from theme import number
from ui import MotionButton, Tooltip, activate_popup
from ui_kit import (
    ActionMenu,
    Card,
    Row,
    dot,
    empty,
    field,
    label,
    palette,
    placeholder,
    stat_row,
    status_line,
    wrapping,
)

PAGE = 30
MAX_FILE = 2 * 1024 * 1024
RATINGS = (
    ("Errei", 1),
    ("Difícil", 2),
    ("Bom", 3),
    ("Fácil", 4),
)
TONES = {1: "error", 2: "warning", 3: "accent", 4: "success"}
KEYS = ("<space>", "<Key-1>", "<Key-2>", "<Key-3>", "<Key-4>", "<Escape>")
TYPING = (tk.Entry, tk.Text, tk.Spinbox)


def render(app):
    state = app.cards_state = getattr(app, "cards_state", None) or {}
    state.setdefault("limit", PAGE)
    state.setdefault("query", "")
    app.cards_limit = state["limit"]
    app.cards_query = state["query"]
    stats = app.cards.stats()

    top = tk.Frame(app.content, bg=app.bg)
    top.pack(fill="x", pady=(0, 14))
    stat_row(
        top,
        app,
        [
            (number(stats["total"]), "cartões"),
            (number(stats["due"]), "para hoje"),
            (number(stats["reviewed_today"]), "revisados hoje"),
        ],
    ).pack(side="left")
    review_button = MotionButton(
        top,
        text="Revisar agora" + (f" ({number(stats['due'])})" if stats["due"] else ""),
        style="Accent.TButton",
        command=lambda: review_round(app),
        state="normal" if stats["due"] else "disabled",
    )
    review_button.pack(side="right")
    if not stats["due"]:
        Tooltip(review_button, "Tudo revisado por enquanto.")
    ActionMenu(
        top,
        app,
        [
            ("Novo cartão", lambda: open_editor(app)),
            ("Exportar", lambda: export_cards(app)),
            ("Importar", lambda: import_cards(app)),
        ],
        text="Mais",
        icon="ellipsis",
    ).pack(side="right", padx=(10, 0))

    bar = tk.Frame(app.content, bg=app.bg)
    bar.pack(fill="x", pady=(0, 10))
    search_var = tk.StringVar(value=state["query"])
    entry = ttk.Entry(bar, textvariable=search_var, width=34, style="Field.TEntry")
    entry.pack(side="left")
    placeholder(entry, app, "Buscar frente ou verso")

    listing = Card(app.content, app, padding=(14, 10))
    listing.pack(fill="x")
    body = listing.body

    def draw_list():
        for child in body.winfo_children():
            child.destroy()
        state["query"] = search_var.get().strip()
        app.cards_query = state["query"]
        app.cards_limit = state["limit"]
        cards = app.cards.list(query=state["query"])
        shown = cards[: app.cards_limit]
        if not cards:
            if state["query"]:
                empty(
                    body,
                    app,
                    "filter-x",
                    "Nenhum cartão nesta busca",
                    "A busca olha a frente e o verso. Outros cartões continuam disponíveis.",
                    [("Limpar busca", lambda: search_var.set(""), "x")],
                ).pack(fill="x", pady=24)
            else:
                empty(
                    body,
                    app,
                    "library",
                    "Nenhum cartão ainda",
                    "Escreva o que quer lembrar: frente, verso e quando quiser explicação. "
                    "Sem conta e sem envio: os cartões ficam neste computador.",
                    [("Criar cartão", lambda: open_editor(app), "plus")],
                ).pack(fill="x", pady=24)
            return
        for card in shown:
            _card_row(app, body, card)
        if len(cards) > len(shown):

            def more():
                state["limit"] = len(shown) + PAGE
                app.cards_limit = state["limit"]
                draw_list()

            MotionButton(
                body,
                text=f"Mostrar mais ({len(cards) - len(shown)})",
                style="Ghost.TButton",
                command=more,
            ).pack(anchor="w", pady=(8, 4))

    search_var.trace_add("write", lambda *_: draw_list())
    draw_list()


def _card_row(app, parent, card):
    today = app.today()
    due = card.get("due")
    detail = (
        card["deck_id"]
        + " · "
        + _when(due, today)
        + (" · suspensa" if card.get("suspended") else "")
    )
    row = Row(parent, app, card["front"], detail, on_open=None, pady=9)
    row.pack(fill="x")
    dot_tone = (
        "accent" if due and datetime.fromisoformat(due).date() <= today else "faint"
    )
    dot(row.lead, app, dot_tone).pack(pady=(5, 0), padx=(0, 12))
    suspended = bool(card.get("suspended"))
    ActionMenu(
        row.trail,
        app,
        [
            ("Editar", lambda: open_editor(app, card)),
            ("Ativar" if suspended else "Suspender", lambda: _suspended(app, card)),
            None,
            ("Excluir", lambda: discard(app, card), "danger"),
        ],
    ).pack(side="right", padx=(6, 0))
    row.refresh_bindings()
    return row


def _suspended(app, card):
    app.cards.suspend(card["id"], not card.get("suspended"))
    app.refresh()


def discard(app, card):
    from app import messagebox

    if messagebox.askyesno(
        "Excluir cartão",
        "Marcar como excluído? Ele sai do baralho e das rodadas; as revisões "
        "anteriores continuam no histórico.",
        parent=app.root,
    ):
        app.cards.delete(card["id"])
        app.refresh()


def _when(due, today):
    if not due:
        return "novo"
    day = datetime.fromisoformat(due).astimezone().date()
    days = (day - today).days
    if days < 0:
        return "há " + str(-days) + (" dia" if days == -1 else " dias")
    if days == 0:
        return "para hoje"
    if days == 1:
        return "amanhã"
    if days < 7:
        return f"em {days} dias"
    return day.strftime("%d/%m")


# Rodada de revisão ----------------------------------------------------


def review_round(app):
    cards = app.cards.due()
    if not cards:
        return
    for child in app.content.winfo_children():
        child.destroy()
    state = app.cards_state = dict(
        cards=cards,
        index=0,
        counts={1: 0, 2: 0, 3: 0, 4: 0},
        round_id="cards-" + uuid.uuid4().hex,
        phase="front",
        keys=[],
    )
    frame = tk.Frame(app.content, bg=app.bg)
    frame.pack(fill="x")
    state["frame"] = frame

    head = tk.Frame(frame, bg=app.bg)
    head.pack(fill="x")
    label(head, app, "Rodada de revisão", size=12, weight="bold").pack(side="left")
    MotionButton(
        head,
        text="Encerrar",
        style="Ghost.TButton",
        height=32,
        command=lambda: enclose(app),
    ).pack(side="right")
    progress = label(head, app, _progress(state), size=9, tone="muted")
    progress.pack(side="right", padx=(0, 12))

    box = Card(frame, app, padding=(22, 20))
    box.pack(fill="x", pady=(10, 0))
    question = wrapping(label(box.body, app, "", size=15, weight="bold"))
    question.pack(fill="x")
    answer_box = tk.Frame(box.body, bg=palette(app)["surface"])
    answer = wrapping(label(answer_box, app, "", size=13))
    answer.pack(fill="x")
    explanation = wrapping(label(answer_box, app, "", size=10, tone="muted"))

    foot = tk.Frame(frame, bg=app.bg)
    foot.pack(fill="x", pady=(10, 0))
    rate_bar = tk.Frame(foot, bg=app.bg)
    rate_bar.pack(side="left")
    show = MotionButton(
        foot,
        text="Mostrar resposta",
        style="Accent.TButton",
        command=lambda: reveal(app),
    )
    show.pack(side="right")

    state.update(
        question=question,
        answer_box=answer_box,
        answer=answer,
        explanation=explanation,
        progress=progress,
        rate_bar=rate_bar,
        show=show,
    )
    state["keys"] = [
        (seq, str(app.root.bind(seq, _handler(app), add="+"))) for seq in KEYS
    ]
    frame.bind(
        "<Destroy>", lambda e: release_keys(app) if e.widget is frame else None, add="+"
    )
    show_card(app)
    return frame


def _handler(app):
    def on_key(event):
        # Root-level keys reach text fields too; typing must never rate a card.
        if isinstance(event.widget, TYPING):
            return
        if event.keysym == "space":
            reveal(app)
        elif event.keysym in ("1", "2", "3", "4"):
            rate(app, int(event.keysym))
        elif event.keysym == "Escape":
            enclose(app)

    return on_key


def release_keys(app):
    state = getattr(app, "cards_state", None)
    if not state:
        return
    for seq, funcid in state.get("keys", ()):
        try:
            app.root.unbind(seq, funcid)
        except tk.TclError:
            pass
    state["keys"] = []


def _progress(state):
    return f"{state['index'] + 1}/{len(state['cards'])}"


def show_card(app):
    state = app.cards_state
    card = state["cards"][state["index"]]
    state["phase"] = "front"
    state["question"].configure(text=card["front"])
    state["answer_box"].pack_forget()
    state["progress"].configure(text=_progress(state))
    state["show"].configure(state="normal")
    _rate_buttons(app, {rating: name for name, rating in RATINGS}, "disabled")


def reveal(app):
    state = getattr(app, "cards_state", None)
    if not state or state.get("phase") != "front":
        return
    card = state["cards"][state["index"]]
    state["phase"] = "back"
    state["answer"].configure(text=card["back"])
    if card.get("explanation"):
        state["explanation"].configure(text=card["explanation"])
        state["explanation"].pack(fill="x", pady=(8, 0))
    else:
        state["explanation"].pack_forget()
    state["answer_box"].pack(fill="x", pady=(12, 0))
    state["show"].configure(state="disabled")
    labels = {}
    for name, rating in RATINGS:
        interval = app.cards.preview(card["id"], rating)["interval"]
        labels[rating] = f"{name} · " + (
            "amanhã" if interval == 1 else f"em {interval} dias"
        )
    _rate_buttons(app, labels, "normal")


def _rate_buttons(app, labels, state_name):
    """Rebuilt each time: a MotionButton keeps the width of its first text."""
    state = app.cards_state
    for child in state["rate_bar"].winfo_children():
        child.destroy()
    state["rates"] = {}
    for rating, text in labels.items():
        button = MotionButton(
            state["rate_bar"],
            text=text,
            style="TButton",
            state=state_name,
            command=lambda r=rating: rate(app, r),
        )
        button.pack(side="left", padx=(0, 8))
        state["rates"][rating] = button


def rate(app, rating):
    state = getattr(app, "cards_state", None)
    if not state or state.get("phase") != "back":
        return
    card = state["cards"][state["index"]]
    try:
        app.cards.review(card["id"], rating, state["round_id"])
    except ValueError as exc:
        app.notify(str(exc), "Revisão", "triangle-alert", "error")
        return
    state["counts"][rating] += 1
    state["index"] += 1
    state["phase"] = "next"
    if state["index"] >= len(state["cards"]):
        finish_round(app)
    else:
        show_card(app)


def enclose(app):
    """Encerra a rodada antes do fim; revisões já registradas continuam valendo."""
    state = getattr(app, "cards_state", None)
    if not state or not state.get("frame"):
        return
    release_keys(app)
    frame = state["frame"]
    del state["frame"]
    if frame.winfo_exists():
        frame.destroy()
    app.refresh()


def finish_round(app):
    state = getattr(app, "cards_state", None)
    if not state:
        return
    release_keys(app)
    frame = state.pop("frame", None)
    if frame is not None and frame.winfo_exists():
        frame.destroy()
    state["phase"] = "done"
    counts, total = state["counts"], sum(state["counts"].values())
    panel = tk.Frame(app.content, bg=app.bg)
    panel.pack(fill="x")
    label(panel, app, "Rodada concluída", size=13, weight="bold").pack(anchor="w")
    stat_row(
        panel,
        app,
        [
            (str(total), "revisados"),
            (str(counts[2]), "difícil"),
            (str(counts[3]), "bom"),
            (str(counts[4]), "fácil"),
        ],
    ).pack(anchor="w", pady=(10, 14))
    MotionButton(
        panel, text="Voltar ao painel", style="Accent.TButton", command=app.refresh
    ).pack(anchor="w")


# Editor ---------------------------------------------------------------


def open_editor(app, card=None, on_saved=None):
    win = tk.Toplevel(app.root)
    win.title("Editar cartão" if card else "Novo cartão")
    win.configure(bg=app.bg)
    win.geometry("620x620")
    win.minsize(480, 420)
    win.transient(app.root)

    foot = tk.Frame(win, bg=app.bg)
    foot.pack(side="bottom", fill="x", padx=18, pady=12)
    body = tk.Frame(win, bg=app.bg)
    body.pack(fill="both", expand=True, padx=18, pady=(16, 0))
    status = status_line(body, app)

    label(body, app, "Baralho", size=9, tone="muted").pack(anchor="w")
    deck_var = tk.StringVar(value=(card or {}).get("deck_id", "pessoal"))
    deck = field(body, app, width=28, textvariable=deck_var)
    deck.pack(anchor="w", pady=(2, 0))

    label(body, app, "Frente", size=9, tone="muted").pack(anchor="w", pady=(10, 2))
    front = field(body, app)
    front.pack(fill="x")

    label(body, app, "Verso", size=9, tone="muted").pack(anchor="w", pady=(8, 2))
    back = field(body, app, 3)
    back.pack(fill="x")
    label(body, app, "Explicação (opcional)", size=9, tone="muted").pack(
        anchor="w", pady=(10, 2)
    )
    extra = field(body, app, 3)
    extra.pack(fill="x")
    label(body, app, "Fonte (opcional)", size=9, tone="muted").pack(
        anchor="w", pady=(10, 2)
    )
    source = field(body, app)
    source.pack(fill="x")
    if card:
        front.insert(0, card["front"])
        back.insert("1.0", card["back"])
        extra.insert("1.0", card.get("explanation", ""))
        source.insert(0, card.get("source", ""))

    MotionButton(
        foot, text="Salvar cartão", style="Accent.TButton", command=lambda: save()
    ).pack(side="right")
    MotionButton(
        foot, text="Cancelar", style="Ghost.TButton", command=win.destroy
    ).pack(side="right", padx=(0, 8))

    def save():
        front_text = front.get().strip()
        back_text = back.get("1.0", "end").strip()
        deck_text = deck_var.get().strip()
        if not front_text or not back_text:
            status("Escreva a frente e o verso.")
            return
        if not deck_text:
            status("Dê um nome ao baralho.")
            return
        try:
            app.cards.save(
                front_text,
                back_text,
                deck_id=deck_text,
                explanation=extra.get("1.0", "end").strip(),
                source=source.get().strip(),
                card_id=card["id"] if card else None,
            )
        except ValueError as exc:
            status(str(exc))
            return
        win.destroy()
        (on_saved() if on_saved else app.refresh())

    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.bind("<Escape>", lambda e: win.destroy())
    activate_popup(win, focus=front, modal=True)
    return win


# Exportar e importar --------------------------------------------------


def export_cards(app):
    path = filedialog.asksaveasfilename(
        parent=app.root,
        title="Exportar cartões",
        defaultextension=".json",
        filetypes=[("Cartões RUMO (JSON)", "*.json")],
    )
    if not path:
        return
    text = app.cards.export()
    temp = path + ".tmp"
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temp, path)
    except OSError as exc:
        app.notify(f"Não foi possível salvar o arquivo: {exc}", "Exportar cartões")
        return
    app.notify("Cartões exportados.", "Exportar cartões", "circle-check", "success")


def import_cards(app):
    path = filedialog.askopenfilename(
        parent=app.root,
        title="Importar cartões",
        filetypes=[("Cartões RUMO (JSON)", "*.json"), ("Todos os arquivos", "*.*")],
    )
    if not path:
        return
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read(MAX_FILE + 1)
        if len(text) > MAX_FILE:
            raise ValueError("O arquivo passa de 2 MB.")
    except (OSError, UnicodeDecodeError) as exc:
        app.notify(f"Não foi possível ler o arquivo: {exc}", "Importar cartões")
        return
    from app import messagebox

    if not messagebox.askyesno(
        "Importar cartões",
        "Importar os cartões deste arquivo para o baralho pessoal? "
        "Eles ficam salvos neste computador.",
        parent=app.root,
    ):
        return
    try:
        count = app.cards.import_cards(text)
    except ValueError as exc:
        app.notify(str(exc), "Importar cartões", "triangle-alert", "error")
        return
    app.notify(
        f"{count} cartões importados.", "Importar cartões", "circle-check", "success"
    )
    app.refresh()


# Peças comuns ---------------------------------------------------------
