"""Arena dialogs: question editor, package import and the question bank.

All data goes through ``app.arena``; the dialogs only compose widgets and show
the service's ``ValueError`` messages in the window itself.
"""

import math
import os
import tkinter as tk
from tkinter import filedialog, ttk

from theme import number
from ui import MotionButton, activate_popup
from ui_kit import ActionMenu, Row, empty, field, label, placeholder, status_line

KINDS = {"Certo/Errado": "certo-errado", "Múltipla escolha": "multipla-escolha"}
LETTERS = "abcdefghij"
BANK_PAGE = 30
MAX_PACK = 2 * 1024 * 1024


def edit_question(app, question=None, on_saved=None):
    """Create or edit one question; service errors stay in the window."""
    win = _window(app, "Editar questão" if question else "Nova questão", 780, 740)
    subjects = app.subject_map()
    subject_var = tk.StringVar(
        value=_label_for(subjects, (question or {}).get("subject_id"))
    )
    topics = app.topic_map(subjects.get(subject_var.get(), "")) if subjects else {}
    topic_var = tk.StringVar(value=_label_for(topics, (question or {}).get("topic_id")))
    kind_var = tk.StringVar(
        value=(
            "Múltipla escolha"
            if (question or {}).get("kind") == "multipla-escolha"
            else "Certo/Errado"
        )
    )
    answer_var = tk.StringVar()
    body, foot = _shell(win, app)

    label(
        body,
        app,
        "Questão avulsa, sem conta e sem rede. Ela entra na Arena deste plano.",
        size=9,
        tone="muted",
    ).pack(anchor="w", pady=(0, 12))

    pair = tk.Frame(body, bg=app.bg)
    pair.pack(fill="x", pady=(0, 10))
    subject_combo = _combo(
        app, _column(pair, app, "Matéria"), subject_var, sorted(subjects)
    )
    topic_box = _column(pair, app, "Assunto", last=True)
    topic_combo = _combo(app, topic_box, topic_var, sorted(topics))

    def change_subject(event=None):
        found = app.topic_map(subjects.get(subject_var.get(), ""))
        topic_combo.configure(values=sorted(found))
        topic_var.set("")

    subject_combo.bind("<<ComboboxSelected>>", change_subject)

    pair_kind = tk.Frame(body, bg=app.bg)
    pair_kind.pack(fill="x", pady=(0, 10))
    kind_combo = _combo(app, _column(pair_kind, app, "Tipo"), kind_var, list(KINDS))
    answer_combo = _combo(
        app, _column(pair_kind, app, "Gabarito", last=True), answer_var, []
    )
    kind_combo.bind("<<ComboboxSelected>>", lambda e: sync_kind())

    label(body, app, "Enunciado", size=9, tone="muted").pack(anchor="w", pady=(4, 2))
    statement = field(body, app, 5)
    statement.pack(fill="x", pady=(0, 10))

    options_slot = tk.Frame(body, bg=app.bg)
    options_slot.pack(fill="x")
    options_box = tk.Frame(options_slot, bg=app.bg)
    options_head = tk.Frame(options_box, bg=app.bg)
    options_head.pack(fill="x")
    label(options_head, app, "Alternativas", size=9, tone="muted").pack(side="left")
    add_option = MotionButton(
        options_head,
        text="Adicionar",
        icon="plus",
        style="Ghost.TButton",
        height=28,
        command=lambda: add_option_row(),
    )
    add_option.pack(side="right")
    options = tk.Frame(options_box, bg=app.bg)
    options.pack(fill="x", pady=(4, 0))
    rows = []

    label(body, app, "Comentário", size=9, tone="muted").pack(anchor="w", pady=(8, 2))
    comment = field(body, app, 3)
    comment.pack(fill="x", pady=(0, 10))

    label(body, app, "Fonte ou procedência", size=9, tone="muted").pack(anchor="w")
    source = field(body, app, width=40)
    source.pack(fill="x", pady=(2, 8))

    show_status = status_line(foot, app, side="left")
    MotionButton(
        foot, text="Salvar questão", style="Accent.TButton", command=lambda: save()
    ).pack(side="right")
    MotionButton(
        foot, text="Cancelar", style="Ghost.TButton", command=win.destroy
    ).pack(side="right", padx=(0, 8))

    def add_option_row(text=""):
        if len(rows) >= 10:
            return
        row = tk.Frame(options, bg=app.bg)
        row.pack(fill="x", pady=2)
        badge = label(row, app, "", size=9, weight="bold", tone="accent", width=2)
        badge.pack(side="left")
        entry = field(row, app, width=40)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if text:
            entry.insert(0, text)
        remove = MotionButton(
            row,
            icon="x",
            style="Ghost.TButton",
            height=26,
            command=lambda: remove_option(item),
        )
        remove.pack(side="right")
        item = {"row": row, "entry": entry, "badge": badge, "remove": remove}
        rows.append(item)
        _renumber(rows)
        refresh_answers()

    def remove_option(item):
        if len(rows) <= 2:
            return
        item["row"].destroy()
        rows.remove(item)
        _renumber(rows)
        refresh_answers()

    def refresh_answers():
        if kind_var.get() == "Múltipla escolha":
            values = [LETTERS[index].upper() for index in range(len(rows))]
        else:
            values = ["Certo", "Errado"]
        answer_combo.configure(values=values)
        if answer_var.get() not in values:
            answer_var.set(values[0] if values else "")
        add_option.configure(state="normal" if len(rows) < 10 else "disabled")

    def sync_kind():
        if kind_var.get() == "Múltipla escolha":
            if not rows:
                add_option_row()
                add_option_row()
            options_box.pack(fill="x", pady=(4, 8))
        else:
            options_box.pack_forget()
        refresh_answers()

    def save():
        try:
            payload = collect()
            app.arena.save_question(payload, question["id"] if question else None)
        except ValueError as exc:
            show_status(str(exc), "error")
            return
        win.destroy()
        if on_saved:
            on_saved()
        else:
            app.refresh()

    def collect():
        subject_id = subjects.get(subject_var.get())
        topic_id = app.topic_map(subject_id).get(topic_var.get())
        if not subject_id or not topic_id:
            raise ValueError("Escolha a matéria e o assunto.")
        text = statement.get("1.0", "end").strip()
        if not text:
            raise ValueError("Escreva o enunciado.")
        kind = KINDS[kind_var.get()]
        options_list = []
        answer = answer_var.get().strip().lower()
        if kind == "multipla-escolha":
            texts = [item["entry"].get().strip() for item in rows]
            if len(texts) < 2:
                raise ValueError("Acrescente pelo menos duas alternativas.")
            if any(not value for value in texts):
                raise ValueError("Preencha ou remova as alternativas vazias.")
            options_list = [
                {"id": LETTERS[index], "text": value}
                for index, value in enumerate(texts)
            ]
            if answer not in [option["id"] for option in options_list]:
                raise ValueError("Escolha o gabarito entre as alternativas.")
        elif answer not in ("certo", "errado"):
            raise ValueError("Escolha o gabarito.")
        return {
            "subject_id": subject_id,
            "topic_id": topic_id,
            "kind": kind,
            "statement": text,
            "options": options_list,
            "answer": answer,
            "comment": comment.get("1.0", "end").strip(),
            "source": source.get().strip(),
        }

    if question:
        statement.insert("1.0", question.get("statement", ""))
        comment.insert("1.0", question.get("comment", ""))
        source.insert(0, question.get("source", ""))
        if question.get("kind") == "multipla-escolha":
            for option in question.get("options") or []:
                add_option_row(option.get("text", ""))
            answer_var.set(str(question.get("answer", "")).upper())
        else:
            answer_var.set(str(question.get("answer", "")).capitalize())
    else:
        add_option_row()
        add_option_row()
    sync_kind()
    refresh_answers()
    activate_popup(win, focus=statement, modal=True)
    return win


def import_pack(app, on_done=None):
    """Pick a JSON pack, choose where it lands and show the counters."""
    path = filedialog.askopenfilename(
        parent=app.root,
        title="Importar pacote de questões",
        filetypes=[("Pacote RUMO (JSON)", "*.json"), ("Todos os arquivos", "*.*")],
    )
    if not path:
        return None
    win = _window(app, "Importar pacote", 620, 380)
    subjects = app.subject_map()
    subject_var = tk.StringVar(value=next(iter(subjects), ""))
    topics = app.topic_map(subjects.get(subject_var.get(), "")) if subjects else {}
    topic_var = tk.StringVar(value=next(iter(topics), ""))
    body, foot = _shell(win, app)
    label(body, app, os.path.basename(path), size=12, weight="bold").pack(anchor="w")
    label(
        body,
        app,
        "O arquivo não é alterado. Questões já existentes com a mesma versão "
        "ficam como estão.",
        size=9,
        tone="muted",
    ).pack(anchor="w", pady=(2, 12))
    pair = tk.Frame(body, bg=app.bg)
    pair.pack(fill="x", pady=(0, 10))
    subject_combo = _combo(
        app, _column(pair, app, "Matéria"), subject_var, sorted(subjects)
    )
    topic_box = _column(pair, app, "Assunto", last=True)
    topic_combo = _combo(app, topic_box, topic_var, sorted(topics))

    def change_subject(event=None):
        found = app.topic_map(subjects.get(subject_var.get(), ""))
        topic_combo.configure(values=sorted(found))
        topic_var.set(next(iter(found), ""))

    subject_combo.bind("<<ComboboxSelected>>", change_subject)
    show_status = status_line(body, app)

    def run():
        subject_id = subjects.get(subject_var.get())
        topic_id = app.topic_map(subject_id).get(topic_var.get())
        if not subject_id or not topic_id:
            show_status("Escolha a matéria e o assunto.", "error")
            return
        try:
            text = _read_pack(path)
            result = app.arena.import_pack(text, subject_id, topic_id)
        except ValueError as exc:
            show_status(str(exc), "error")
            return
        except OSError as exc:
            show_status("Não foi possível ler o arquivo: " + str(exc), "error")
            return
        show_status(
            f"{number(result.get('added', 0))} adicionadas · "
            f"{number(result.get('updated', 0))} atualizadas · "
            f"{number(result.get('skipped', 0))} ignoradas.",
            "success",
        )
        import_button.configure(state="disabled")
        cancel_button.configure(text="Fechar")
        if on_done:
            on_done()
        else:
            app.refresh()

    import_button = MotionButton(
        foot, text="Importar", style="Accent.TButton", command=run
    )
    import_button.pack(side="right")
    cancel_button = MotionButton(
        foot, text="Cancelar", style="Ghost.TButton", command=win.destroy
    )
    cancel_button.pack(side="right", padx=(0, 8))
    activate_popup(win, focus=import_button, modal=True)
    return win


def question_bank(app, topic_id=None):
    """Paginated bank with search, edit, annul/reactivate and retire."""
    from app import messagebox

    win = _window(app, "Banco de questões", 940, 660)
    subjects = app.subject_map()
    names = {rid: name for name, rid in subjects.items()}
    query_var = tk.StringVar()
    state = {"page": 0}
    body, foot = _shell(win, app)

    head = tk.Frame(body, bg=app.bg)
    head.pack(fill="x", pady=(0, 8))
    search = field(head, app, width=44)
    search.pack(side="left", fill="x", expand=True)
    placeholder(search, app, "Buscar no enunciado")
    MotionButton(
        head,
        text="Nova questão",
        icon="plus",
        style="Accent.TButton",
        command=lambda: edit_question(app, on_saved=reload),
    ).pack(side="right", padx=(8, 0))

    listing = _ScrollList(body, app)
    listing.pack(fill="both", expand=True)
    show_status = status_line(body, app)
    pager = tk.Frame(foot, bg=app.bg)
    pager.pack(side="left")
    previous = MotionButton(
        pager, text="Anterior", icon="chevron-left", style="Ghost.TButton"
    )
    previous.pack(side="left")
    page_label = label(pager, app, "", size=9, tone="muted")
    page_label.pack(side="left", padx=10)
    following = MotionButton(
        pager, text="Próxima", icon="arrow-right", style="Ghost.TButton"
    )
    following.pack(side="left")
    MotionButton(foot, text="Fechar", style="TButton", command=win.destroy).pack(
        side="right"
    )

    def reload():
        rows = app.arena.questions(
            app.plan,
            topic_id=topic_id,
            query=query_var.get().strip(),
            include_retired=True,
        )
        pages = max(1, math.ceil(len(rows) / BANK_PAGE))
        state["page"] = max(0, min(state["page"], pages - 1))
        start = state["page"] * BANK_PAGE
        for child in listing.body.winfo_children():
            child.destroy()
        if not rows:
            empty(
                listing.body,
                app,
                "search",
                "Nenhuma questão encontrada",
                "Ajuste a busca, crie uma questão ou importe um pacote.",
                [],
            ).pack(fill="x", pady=30)
        for item in rows[start : start + BANK_PAGE]:
            question_row(listing.body, item)
        listing.canvas.yview_moveto(0)
        page_label.configure(text=f"{state['page'] + 1} de {pages}")
        previous.configure(state="normal" if state["page"] else "disabled")
        following.configure(state="normal" if state["page"] + 1 < pages else "disabled")

    def question_row(parent, item):
        title = " ".join(str(item.get("statement", "")).split())
        if len(title) > 140:
            title = title[:137].rstrip() + "…"
        subject = _truncate(names.get(item.get("subject_id"), ""), 50)
        topic = _truncate(
            _label_for(app.topic_map(item.get("subject_id")), item.get("topic_id")),
            50,
        )
        detail = " · ".join(
            part
            for part in (
                subject,
                topic,
                (
                    "Certo/Errado"
                    if item.get("kind") == "certo-errado"
                    else "Múltipla escolha"
                ),
                item.get("status", ""),
            )
            if part
        )
        row = Row(parent, app, title, detail, pady=8)
        row.pack(fill="x")
        MotionButton(
            row.trail,
            text="Editar",
            height=30,
            command=lambda: edit_question(app, item, on_saved=reload),
        ).pack(side="right", padx=(8, 0))
        ActionMenu(
            row.trail,
            app,
            [
                *(
                    [("Anular", lambda: set_status(item, "anulada"))]
                    if item.get("status") == "ativa"
                    else [("Reativar", lambda: set_status(item, "ativa"))]
                ),
                None,
                *(
                    [("Retirar do banco", lambda: retire(item), "danger")]
                    if item.get("status") != "retirada"
                    else []
                ),
            ],
        ).pack(side="right")
        row.refresh_bindings()

    def set_status(item, status):
        try:
            app.arena.set_status(item["id"], status)
        except ValueError as exc:
            show_status(str(exc), "error")
            return
        reload()

    def retire(item):
        if messagebox.askyesno(
            "Retirar questão",
            "Ela deixa de aparecer nas rodadas. O histórico de tentativas continua.",
            parent=win,
        ):
            set_status(item, "retirada")

    def move(step):
        state["page"] += step
        reload()

    previous.configure(command=lambda: move(-1))
    following.configure(command=lambda: move(1))
    search.bind("<KeyRelease>", lambda e: (state.update(page=0), reload()))
    reload()
    activate_popup(win, modal=True)
    return win


class _ScrollList(tk.Frame):
    """Vertical list with a native scrollbar; no global wheel binding."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=app.bg)
        self.canvas = tk.Canvas(self, bg=app.bg, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=app.bg)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._window, width=e.width),
        )


def _window(app, title, width, height):
    win = tk.Toplevel(app.root)
    win.title(title)
    win.configure(bg=app.bg)
    win.geometry(f"{width}x{height}")
    win.minsize(520, 380)
    win.transient(app.root)
    return win


def _shell(win, app):
    foot = tk.Frame(win, bg=app.bg)
    foot.pack(side="bottom", fill="x", padx=18, pady=12)
    body = tk.Frame(win, bg=app.bg)
    body.pack(fill="both", expand=True, padx=18, pady=(16, 0))
    return body, foot


def _truncate(text, max_len=50):
    clean = " ".join(str(text or "").split())
    if len(clean) > max_len:
        return clean[: max_len - 1].rstrip() + "…"
    return clean


def _column(parent, app, title, last=False):
    box = tk.Frame(parent, bg=app.bg)
    box.pack(side="left", fill="x", expand=True, padx=(0, 0 if last else 12))
    label(box, app, title, size=9, tone="muted").pack(anchor="w")
    return box


def _combo(app, parent, variable, values):
    combo = ttk.Combobox(parent, textvariable=variable, values=list(values))
    combo.configure(state="readonly")
    combo.pack(fill="x", pady=(2, 0))
    return combo


def _renumber(rows):
    for index, item in enumerate(rows):
        item["badge"].configure(text=LETTERS[index].upper())


def _read_pack(path):
    if os.path.getsize(path) > MAX_PACK:
        raise ValueError("O pacote passa de 2 MB.")
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError:
        raise ValueError("O arquivo não está em UTF-8.") from None


def _label_for(mapping, value):
    return next((name for name, rid in mapping.items() if rid == value), "")
