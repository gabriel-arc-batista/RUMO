"""Transparent, plan-isolated challenges derived from saved study records."""

from datetime import timedelta

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
