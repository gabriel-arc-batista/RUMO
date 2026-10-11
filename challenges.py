"""Transparent, plan-isolated challenges derived from saved study records."""

from datetime import timedelta
from tkinter import ttk
from ui import Panel, MotionButton, ThinProgress

LEVELS = {"Iniciante": (3, 30), "Intermediário": (7, 100), "Avançado": (12, 200)}
CATALOG = [
    (
        "Primeiro impulso",
        "sessions",
        (1, 4, 8),
        "sessões",
        "Registre sessões com pelo menos 15 minutos líquidos.",
        "Comece com um bloco curto, sem distrações.",
    ),
    (
        "Reserva de foco",
        "minutes",
        (60, 240, 480),
        "minutos",
        "Some tempo líquido de estudo nesta semana.",
        "Pausas não contam: respeite seu descanso.",
    ),
    (
        "Questão por questão",
        "questions",
        (15, 60, 150),
        "questões",
        "Resolva e registre acertos ou erros; brancos não contam.",
        "Corrija os erros antes de aumentar a quantidade.",
    ),
    (
        "Memória em dia",
        "reviews",
        (1, 3, 6),
        "revisões",
        "Conclua revisões com sessão vinculada nesta semana.",
        "Abra Revisões e recupere um conteúdo antigo.",
    ),
    (
        "Ritmo possível",
        "days",
        (2, 4, 5),
        "dias",
        "Estude por pelo menos 15 minutos em dias diferentes.",
        "Distribua o esforço. Mais tempo não substitui descanso.",
    ),
    (
        "Conectando matérias",
        "subjects",
        (2, 3, 5),
        "matérias",
        "Estude matérias diferentes com tempo líquido positivo.",
        "Alterne uma matéria forte com uma que precisa de atenção.",
    ),
    (
        "Caderno vivo",
        "notes",
        (1, 3, 6),
        "assuntos",
        "Mantenha observações não vazias em assuntos deste plano (total acumulado).",
        "Anote uma dúvida, um exemplo ou o motivo de um erro.",
    ),
    (
        "Base bem construída",
        "topics",
        (2, 5, 10),
        "assuntos",
        "Estude assuntos distintos em sessões de teoria nesta semana.",
        "Explique o assunto com suas palavras antes de avançar.",
    ),
]


def metrics(store, plan, today):
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    args = (plan, start.isoformat(), end.isoformat())
    rows = store.rows(
        "SELECT * FROM sessions WHERE plan_id=? AND day BETWEEN ? AND ?", args
    )
    daily = {
        r["label"]: r["elapsed"]
        for r in store.time_by_day(
            plan, {"from": start.isoformat(), "to": end.isoformat()}
        )
    }
    return dict(
        sessions=sum(r["elapsed"] >= 900 for r in rows),
        minutes=int(sum(daily.values())) // 60,
        questions=sum(r["correct"] + r["wrong"] for r in rows),
        days=sum(seconds >= 900 for seconds in daily.values()),
        subjects=len(
            {r["subject_id"] for r in rows if r["subject_id"] and r["elapsed"] > 0}
        ),
        topics=len(
            {
                r["topic_id"]
                for r in rows
                if r["topic_id"] and r["category"] == "Teoria" and r["elapsed"] > 0
            }
        ),
        reviews=store.one(
            """SELECT COUNT(*) n FROM reviews r JOIN sessions s ON s.id=r.completed_id
                    WHERE s.plan_id=? AND s.day BETWEEN ? AND ? AND r.state='Concluída' """,
            args,
        )["n"],
        notes=store.one(
            """SELECT COUNT(*) n FROM topics t JOIN subjects s ON s.id=t.subject_id
                    WHERE s.plan_id=? AND s.archived=0 AND t.archived=0 AND trim(t.notes)<>'' """,
            (plan,),
        )["n"],
    )


def render(app):
    pref = "challenge_level_" + app.plan
    level = app.store.pref(pref, "Iniciante")
    if level not in LEVELS:
        level = "Iniciante"
    index = list(LEVELS).index(level)
    values = metrics(app.store, app.plan, app.today())
    start = app.today() - timedelta(days=app.today().weekday())
    panel = Panel(app.content, app)
    panel.pack(fill="x", pady=(12, 16))
    ttk.Label(
        panel.body, text="Sua jornada de estudo", style="PanelHeading.TLabel"
    ).pack(anchor="w")
    ttk.Label(
        panel.body,
        text=f"Semana de {start:%d/%m} a {start+timedelta(days=6):%d/%m} • escolha um ritmo sustentável",
        style="PanelMuted.TLabel",
    ).pack(anchor="w", pady=(4, 12))
    row = ttk.Frame(panel.body, style="Panel.TFrame")
    row.pack(fill="x")

    def change(name):
        app.store.set_pref(pref, name)
        app.refresh()

    for name in LEVELS:
        MotionButton(
            row,
            text=name,
            style="Accent.TButton" if name == level else "TButton",
            command=lambda n=name: change(n),
        ).pack(side="left", padx=(0, 8))
    completed = sum(values[key] >= targets[index] for _, key, targets, *_ in CATALOG)
    ttk.Label(
        panel.body,
        text=f"{completed} de 8 desafios • {completed*50} pontos de jornada",
        style="Panel.TLabel",
    ).pack(anchor="w", pady=(14, 8))
    ThinProgress(panel.body, app, completed / 8 * 100).pack(fill="x")

    def adopt():
        hours, questions = LEVELS[level]
        goal = app.store.one(
            "SELECT id FROM goals WHERE plan_id=? AND subject_id IS NULL LIMIT 1",
            (app.plan,),
        )
        app.store.save(
            "goals",
            dict(
                plan_id=app.plan,
                subject_id=None,
                hours=hours,
                questions=questions,
                **({"id": goal["id"]} if goal else {}),
            ),
        )
        app.refresh()

    hours, questions = LEVELS[level]
    app.toolbar([(f"Usar meta do nível: {hours} h / {questions} questões", adopt)])
    app.note(
        "24 desafios em três níveis. Os pontos são locais e recalculados pelos registros; corrigir ou excluir estudos atualiza o progresso. Observações são acumuladas; os outros desafios recomeçam na segunda-feira."
    )
    for name, key, targets, unit, rule, tip in CATALOG:
        target = targets[index]
        actual = values[key]
        done = actual >= target
        card = Panel(app.content, app)
        card.pack(fill="x", pady=(6, 4))
        header = ttk.Frame(card.body, style="Panel.TFrame")
        header.pack(fill="x")
        ttk.Label(
            header,
            text=("✓  " if done else "◇  ") + name,
            style="PanelHeading.TLabel",
            foreground=app.motion.palette["success"] if done else app.fg,
        ).pack(side="left")
        ttk.Label(
            header,
            text=f"{min(actual,target)}/{target} {unit} • 50 pts",
            style="PanelMuted.TLabel",
        ).pack(side="right")
        ttk.Label(
            card.body, text=rule + " " + tip, style="PanelMuted.TLabel", wraplength=720
        ).pack(anchor="w", pady=(8, 10))
        ThinProgress(card.body, app, min(100, actual / target * 100)).pack(fill="x")

        def choose(n=name, k=key, t=target, u=unit):
            app.store.set_pref(
                "main_goal_" + app.plan,
                {
                    "name": n,
                    "key": k,
                    "target": f"{t} {({'sessões':'sessão','dias':'dia','assuntos':'assunto','questões':'questão'}.get(u,u) if t==1 else u)}",
                    "level": level,
                },
            )
            app.refresh()

        principal = app.store.pref("main_goal_" + app.plan, {})
        MotionButton(
            card.body,
            text=(
                "Minha meta principal"
                if principal.get("key") == key and principal.get("level") == level
                else "Adicionar meta"
            ),
            style=(
                "Accent.TButton"
                if principal.get("key") == key and principal.get("level") == level
                else "TButton"
            ),
            command=choose,
        ).pack(anchor="w", pady=(10, 0))
