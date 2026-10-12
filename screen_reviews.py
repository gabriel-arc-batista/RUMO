"""Revisões: what deserves attention today, as a list grouped by when it is due.

Same queries and actions as before (review state, clock, rescheduling, tasks);
only the organization changed. The review algorithm is untouched.
"""

import tkinter as tk
from datetime import date

from ui import MotionButton, Tooltip
from ui_kit import ActionMenu, Card, Row, Section, Segmented, dot, empty, label

VIEWS = ["Hoje", "Atrasadas", "Próximas", "Todas", "Concluídas"]
CONDITIONS = {
    "Todas": "",
    "Hoje": " AND r.state='Pendente' AND r.due=?",
    "Próximas": " AND r.state='Pendente' AND r.due>?",
    "Atrasadas": " AND r.state='Pendente' AND r.due<?",
    "Concluídas": " AND r.state='Concluída'",
}
PAGE = 30
HELP = (
    "Cada estudo registrado com intervalos de revisão cria uma série: a mesma "
    "matéria e assunto voltam nas datas escolhidas. Séries idênticas para o mesmo "
    "assunto, intervalo e data não se repetem; uma nova data base pode criar uma "
    "nova série.\n\nRevise tentando lembrar antes de abrir o material. Os avisos "
    "funcionam com o aplicativo aberto."
)


def counts(app, today):
    row = app.store.one(
        """SELECT SUM(r.state='Pendente' AND r.due<?) overdue,
        SUM(r.state='Pendente' AND r.due=?) today,
        SUM(r.state='Pendente' AND r.due>?) upcoming,
        SUM(r.state='Concluída') done, COUNT(*) total
        FROM reviews r JOIN topics t ON t.id=r.topic_id
        JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=?""",
        (today, today, today, app.plan),
    )
    return {key: row[key] or 0 for key in row.keys()}


def fetch(app, view, today, limit=500):
    # Only a fragment from the fixed CONDITIONS allowlist is concatenated; values are parameters.
    return app.store.rows(
        """SELECT r.*,t.name topic,t.subject_id,s.name subject,a.material,a.next_step
        FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id
        LEFT JOIN sessions a ON a.id=r.origin_id WHERE s.plan_id=?"""
        + CONDITIONS[view]
        + " ORDER BY CASE WHEN r.state='Pendente' THEN 0 ELSE 1 END,r.due LIMIT ?",
        [app.plan]
        + ([today] if view in ["Hoje", "Próximas", "Atrasadas"] else [])
        + [limit],
    )


def state_of(review, today):
    if review["state"] != "Pendente":
        return review["state"]
    if review["due"] < today:
        return "Atrasada"
    return "Hoje" if review["due"] == today else "Próxima"


def when(review, today):
    days = (date.fromisoformat(review["due"]) - date.fromisoformat(today)).days
    if days == 0:
        return "hoje"
    if days == 1:
        return "amanhã"
    if days == -1:
        return "ontem"
    if days < 0:
        return f"há {-days} dias"
    if days < 7:
        return f"em {days} dias"
    return date.fromisoformat(review["due"]).strftime("%d/%m")


def start_review(app, review, timer=True):
    """Open the clock (or the form) prefilled for this review, as before."""
    if review["state"] != "Pendente":
        raise ValueError("Esta revisão não está pendente.")
    values = app.store.rpg.review_fields(review["id"])
    values["material"] = review["material"] or ""
    return app.clock_setup(values) if timer else app.session_form(values)


def render(app):
    from app import Form, messagebox

    today = app.today().isoformat()
    view = app.store.pref("review_view", "Todas")
    if view not in VIEWS:
        view = "Todas"
    number = counts(app, today)
    top = tk.Frame(app.content, bg=app.bg)
    top.pack(fill="x", pady=(0, 14))

    def change(key):
        app.store.set_pref("review_view", key)
        app.review_limit = PAGE
        app.refresh()

    Segmented(
        top,
        app,
        [
            ("Hoje", "Hoje", number["today"] or ""),
            ("Atrasadas", "Atrasadas", number["overdue"] or ""),
            ("Próximas", "Próximas", number["upcoming"] or ""),
            ("Todas", "Todas"),
            ("Concluídas", "Concluídas"),
        ],
        view,
        change,
    ).pack(side="left")
    ActionMenu(
        top,
        app,
        [
            ("Nova tarefa opcional", app.task_form),
            ("Calendário de apoio", app.calendar),
            ("Avisos de hoje", app.notifications),
            None,
            (
                "Como as revisões são criadas",
                lambda: messagebox.showinfo("Revisões", HELP, parent=app.root),
            ),
        ],
        text="Mais",
        icon="ellipsis",
    ).pack(side="right")

    reviews = fetch(app, view, today)
    shown = reviews[: getattr(app, "review_limit", PAGE)]
    card = Card(app.content, app, padding=(14, 10))
    card.pack(fill="x")
    body = card.body
    if not reviews:
        studied = app.store.one(
            "SELECT COUNT(*) n FROM sessions WHERE plan_id=?", (app.plan,)
        )["n"]
        if not number["total"] and not studied:
            empty(
                body,
                app,
                "brain",
                "Revisões nascem dos seus estudos",
                "Ao registrar um estudo, escolha os intervalos (por exemplo 1, 7 e 30 dias). "
                "O assunto volta aqui na data certa para você tentar lembrar.",
                [("Registrar estudo", app.session_form, "plus")],
            ).pack(fill="x", pady=28)
        elif view in ("Hoje", "Atrasadas", "Todas") and not (
            number["today"] + number["overdue"]
        ):
            empty(
                body,
                app,
                "circle-check",
                "Tudo em dia",
                "Nenhuma revisão pendente para hoje."
                + (
                    f" {number['upcoming']} chegam nos próximos dias."
                    if number["upcoming"]
                    else ""
                ),
                (
                    [("Ver próximas", lambda: change("Próximas"))]
                    if number["upcoming"]
                    else []
                ),
            ).pack(fill="x", pady=28)
        else:
            empty(
                body,
                app,
                "filter-x",
                f"Nada em {view.lower()}",
                "Outras revisões continuam disponíveis nas demais visões.",
                [("Ver todas", lambda: change("Todas"))],
            ).pack(fill="x", pady=28)
    else:
        group = None
        for index, review in enumerate(shown):
            state = state_of(review, today)
            if view == "Todas" and state != group:
                group = state
                heading = {
                    "Atrasada": "Atrasadas",
                    "Hoje": "Hoje",
                    "Próxima": "Próximas",
                }.get(state, state + "s")
                label(body, app, heading, size=10, weight="bold", tone="muted").pack(
                    anchor="w", padx=10, pady=(14 if index else 6, 2)
                )
            review_row(app, body, review, state, today, Form, messagebox)
        if len(reviews) > len(shown):

            def more():
                app.review_limit = len(shown) + PAGE
                app.refresh()

            MotionButton(
                body,
                text=f"Mostrar mais ({len(reviews) - len(shown)})",
                style="Ghost.TButton",
                command=more,
            ).pack(anchor="w", pady=(8, 4))
    tasks_section(app, Form, messagebox)


def review_row(app, parent, review, state, today, Form, messagebox):
    tone = {
        "Atrasada": "error",
        "Hoje": "accent",
        "Próxima": "secondary",
        "Concluída": "success",
    }.get(state, "faint")
    retake = " · ".join(
        part
        for part in [review["material"] or "", review["next_step"] or ""]
        if part.strip()
    )
    days = review["interval"]
    detail = (
        review["subject"] + f" · revisão de {days} {'dia' if days == 1 else 'dias'}"
    )
    if retake:
        detail += " · retomar: " + retake
    row = Row(parent, app, review["topic"], detail, separator=True, pady=9)
    row.pack(fill="x")
    dot(row.lead, app, tone).pack(pady=(5, 0), padx=(0, 12))
    pending = review["state"] == "Pendente"

    def reschedule():
        Form(
            app,
            "Reagendar revisão",
            [("due", "Nova data (AAAA-MM-DD)", "entry")],
            lambda v: app.update_review_date(review["id"], v["due"]),
            review,
        )

    def mark(new_state):
        if messagebox.askyesno(
            "Estado da revisão",
            f"Marcar como {new_state.lower()}? Isso não registra tempo de estudo.",
            parent=app.root,
        ):
            app.store.save("reviews", {"id": review["id"], "state": new_state})
            app.refresh()

    items = (
        [
            ("Registrar revisão sem relógio", lambda: start_review(app, review, False)),
            ("Reagendar", reschedule),
            None,
            ("Concluir sem registrar estudo", lambda: mark("Concluída")),
            ("Cancelar revisão", lambda: mark("Cancelada"), "danger"),
        ]
        if pending
        else [("Reabrir", lambda: mark("Pendente"))]
    )
    ActionMenu(row.trail, app, items).pack(side="right", padx=(6, 0))
    if pending:
        start = MotionButton(
            row.trail,
            text="Revisar",
            icon="play",
            height=32,
            command=lambda: start_review(app, review),
        )
        start.pack(side="right", padx=(10, 0))
        Tooltip(start, "Abre o relógio com matéria e assunto desta revisão.")
    label(
        row.trail,
        app,
        when(review, today),
        size=9,
        tone=tone if state == "Atrasada" else "muted",
    ).pack(side="right")
    row.refresh_bindings()
    return row


def tasks_section(app, Form, messagebox):
    tasks = app.store.rows(
        "SELECT * FROM tasks WHERE plan_id=? ORDER BY state='Concluída',due IS NULL,due,name",
        (app.plan,),
    )
    if not tasks:
        return
    section = Section(app.content, app, "Tarefas opcionais", count=len(tasks))
    section.pack(fill="x", pady=(28, 8))
    section.action("Nova tarefa", app.task_form, icon="plus")
    card = Card(app.content, app, padding=(14, 8))
    card.pack(fill="x")
    for task in tasks:
        done = task["state"] == "Concluída"
        row = Row(
            card.body,
            app,
            task["name"],
            (task["state"] + (" · prazo " + task["due"] if task["due"] else "")),
            pady=8,
        )
        row.pack(fill="x")
        dot(row.lead, app, "success" if done else "faint").pack(
            pady=(5, 0), padx=(0, 12)
        )
        ActionMenu(
            row.trail,
            app,
            [
                ("Editar tarefa", lambda t=task: app.task_form(t)),
                ("Excluir tarefa", lambda t=task: app.delete_task(t["id"]), "danger"),
            ],
        ).pack(side="right")
        row.refresh_bindings()
