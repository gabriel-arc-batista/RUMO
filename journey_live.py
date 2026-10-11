"""Read-only view models built from existing records. No writes, no new rules.

Mission and review data already exist in the cycle, sessions and reviews tables;
these helpers only gather them for the screens.
"""

from datetime import timedelta

from journey import Mission, ReviewSummary, SubjectSkill
from learning import next_topic

# Mirrors the engine rule in docs/RUMO_BACKEND_CONTRACT.md: 20 answers on 3 dates.
MIN_ANSWERED = 20
MIN_DATES = 3


def last_next_step(store, plan, subject_id, topic_id):
    """'Onde parei': newest non-empty next step for the topic, else the subject."""
    order = " AND trim(next_step)<>'' ORDER BY day DESC, start_time DESC LIMIT 1"
    queries = (
        ("SELECT next_step FROM sessions WHERE plan_id=? AND topic_id=?", topic_id),
        ("SELECT next_step FROM sessions WHERE plan_id=? AND subject_id=?", subject_id),
    )
    for sql, value in queries:
        row = store.one(sql + order, (plan, value)) if value else None
        if row:
            return row["next_step"].strip()
    return ""


def last_studied(store, plan, subject_id):
    row = store.one(
        "SELECT MAX(day) day FROM sessions WHERE plan_id=? AND subject_id=? AND elapsed>0",
        (plan, subject_id),
    )
    return row["day"] if row else None


def mission(store, plan):
    cycle = store.current_cycle(plan)
    if not cycle:
        return None
    blocks = store.cycle_blocks(cycle)
    if cycle["position"] >= len(blocks):
        return None
    block = blocks[cycle["position"]]
    topic_id, topic = block["topic_id"], block["topic"]
    if not topic_id:
        suggestion = next_topic(store, block["subject_id"])
        if suggestion:
            topic_id, topic = suggestion["id"], suggestion["name"]
    return Mission(
        subject_id=block["subject_id"],
        subject=block["subject"],
        topic_id=topic_id,
        topic=topic,
        suggested_seconds=max(60, block["target"] - block["elapsed"]),
        block_id=block["id"],
        cycle_id=cycle["id"],
        lap=cycle["lap"],
        position=cycle["position"],
        block_count=len(blocks),
        block_elapsed=block["elapsed"],
        block_target=block["target"],
        category=block["category"] or "Teoria",
        next_step=last_next_step(store, plan, block["subject_id"], topic_id),
        last_studied=last_studied(store, plan, block["subject_id"]),
        reward_xp=None,
    )


def reviews(store, plan):
    today = store.today()
    week = today + timedelta(days=7)
    row = store.one(
        """SELECT
            COALESCE(SUM(r.due<?),0) overdue,
            COALESCE(SUM(r.due=?),0) today,
            COALESCE(SUM(r.due>? AND r.due<=?),0) upcoming
           FROM reviews r JOIN topics t ON t.id=r.topic_id
           JOIN subjects s ON s.id=t.subject_id
           WHERE s.plan_id=? AND r.state='Pendente'""",
        (today.isoformat(),) * 3 + (week.isoformat(), plan),
    )
    return ReviewSummary(row["overdue"], row["today"], row["upcoming"])


def answer_dates(store, plan):
    rows = store.rows(
        "SELECT subject_id, COUNT(DISTINCT day) n FROM sessions "
        "WHERE plan_id=? AND correct+wrong>0 GROUP BY subject_id",
        (plan,),
    )
    return {row["subject_id"]: row["n"] for row in rows}


def skills(store, plan):
    result = []
    dates = answer_dates(store, plan)
    for row in store.subject_stats(plan):
        answered = row["correct"] + row["wrong"]
        result.append(
            SubjectSkill(
                subject_id=row["id"],
                name=row["name"],
                effort_seconds=int(row["elapsed"]),
                answered=answered,
                correct=row["correct"],
                accuracy=row["correct"] / answered * 100 if answered else None,
                sample_ok=answered >= MIN_ANSWERED
                and dates.get(row["id"], 0) >= MIN_DATES,
                level=None,
                xp=None,
                xp_next=None,
                progress_source="pending",
            )
        )
    return result
