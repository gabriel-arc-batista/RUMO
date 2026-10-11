"""Production JourneyProvider: typed frontend contracts backed by real RPG data."""

import journey_live
from journey import (
    Achievement,
    Challenge,
    Chapter,
    Character,
    Equipment,
    Mission,
    ReducedMission,
    Reward,
    SubjectSkill,
    StudyPath,
)
from rpg import level_for


class RPGJourney:
    def __init__(self, store):
        self.store = store
        self.engine = store.rpg

    def mission(self, plan):
        row = self.engine.recommended_mission(plan)
        if row is None:
            return None
        cycle = self.store.current_cycle(plan)
        blocks = self.store.cycle_blocks(cycle) if cycle else []
        block = next((b for b in blocks if b["id"] == row["block_id"]), None)
        return Mission(
            subject_id=row["subject_id"],
            subject=row["subject"],
            topic_id=row["topic_id"],
            topic=row["topic"],
            suggested_seconds=row["suggested_seconds"],
            block_id=row["block_id"],
            cycle_id=cycle["id"] if block else None,
            lap=row["lap"],
            position=cycle["position"] if block else None,
            block_count=len(blocks),
            block_elapsed=block["elapsed"] if block else row["elapsed"],
            block_target=block["target"] if block else row["target"],
            category=block["category"] if block else "Teoria",
            next_step=row["next_step"],
            last_studied=journey_live.last_studied(self.store, plan, row["subject_id"]),
            reward_xp=row["suggested_seconds"] // 60,
            completed=row["completed"],
            source="real",
        )

    def mission_fields(self, plan, mission, minutes=None):
        current = self.engine.recommended_mission(plan, mission.topic_id)
        if (
            not current
            or current["block_id"] != mission.block_id
            or current["lap"] != mission.lap
        ):
            raise ValueError("O ciclo mudou. Atualize a missão antes de começar.")
        if minutes is not None:
            self.engine.small_mission(current["id"], minutes)
        else:
            self.engine.continue_mission(current["id"])
        return self.engine.mission_fields(current["id"])

    def reduced(self, mission):
        minutes = max(1, min(5, mission.suggested_seconds // 60))
        return ReducedMission(minutes=minutes, questions=0)

    def reviews(self, plan):
        return journey_live.reviews(self.store, plan)

    def character(self, plan):
        row = self.engine.profile(plan)
        items = self.engine.catalog(plan)
        title = next(
            (i["name"] for i in items if i["equipped"] and i["slot"] == "Título"),
            (
                "Aprendiz · caminhos livres"
                if row["level"] == 1
                else "Viajante · caminhos livres"
            ),
        )
        current, _, _ = self.store.streak(plan)
        return Character(
            name=row["name"],
            title=title,
            level=row["level"],
            xp=row["level_xp"],
            xp_next=row["next_level_xp"],
            coins=row["coins"],
            equipped=tuple(i["id"] for i in items if i["equipped"]),
            streak_days=current,
            source="real",
        )

    def skills(self, plan):
        result = []
        for row in self.engine.profile(plan)["skills"]:
            level = row["level"]
            floor = 50 * (level - 1) * level
            result.append(
                SubjectSkill(
                    subject_id=row["id"],
                    name=row["name"],
                    effort_seconds=int(row["elapsed"]),
                    answered=row["answered"],
                    correct=row["correct"],
                    accuracy=row["performance"],
                    sample_ok=row["performance"] is not None,
                    level=level,
                    xp=row["xp"] - floor,
                    xp_next=100 * level,
                    progress_source="real",
                )
            )
        return result

    def equipment(self, plan):
        return [
            Equipment(
                id=row["id"],
                name=row["name"],
                slot=row["slot"],
                description=row["preview"],
                unlocked=row["owned"],
                equipped=row["equipped"],
                unlock_hint=row["requirement"],
                kind=row["kind"],
                purpose=row["purpose"],
                acquisition=row["acquisition"],
                available=row["available"],
                action=row["action"],
                source="real",
            )
            for row in self.engine.catalog(plan)
        ]

    def progression(self, plan):
        return [
            StudyPath(
                id=row["id"],
                name=row["name"],
                rank=row["rank_name"],
                value=row["value"],
                target=row["target"],
                unit=row["unit"],
                purpose=row["purpose"],
                action=row["action"],
            )
            for row in self.engine.progression(plan)
        ]

    def buy_equipment(self, plan, item_id):
        self.engine.buy(plan, item_id)

    def toggle_equipment(self, plan, item_id):
        row = next((i for i in self.engine.catalog(plan) if i["id"] == item_id), None)
        if not row or not row["owned"]:
            raise ValueError("Compre ou desbloqueie o item antes de equipar.")
        if row["equipped"]:
            with self.store.db:
                self.store.db.execute(
                    "UPDATE rpg_inventory SET equipped=0 WHERE plan_id=? AND item_id=?",
                    (plan, item_id),
                )
        else:
            self.engine.equip(plan, item_id)

    def achievements(self, plan):
        counted = self.store.one(
            "SELECT COUNT(*) n FROM rpg_sources e JOIN sessions s ON s.id=e.session_id WHERE s.plan_id=? AND s.elapsed>0",
            (plan,),
        )["n"]
        reviewed = self.store.one(
            "SELECT COUNT(*) n FROM rpg_rewards r JOIN rpg_sources e ON e.id=r.source_id WHERE r.plan_id=? AND e.review_id IS NOT NULL AND r.xp>0",
            (plan,),
        )["n"]
        practiced = self.store.one(
            "SELECT COUNT(DISTINCT l.difficulty_id) n FROM rpg_links l JOIN sessions s ON s.id=l.session_id WHERE s.plan_id=? AND (s.elapsed>0 OR s.correct+s.wrong>0)",
            (plan,),
        )["n"]
        bosses = sum(
            c["completed"] and c["kind"] == "Chefe"
            for c in self.engine.challenges(plan)
        )
        return [
            Achievement(
                "first-study",
                "Primeiro passo",
                "Registrar estudo com tempo líquido.",
                min(counted, 1),
                1,
                "footprints",
                "real",
            ),
            Achievement(
                "encounters",
                "Memória em prática",
                "Realizar revisões, mesmo atrasadas ou com dificuldade.",
                reviewed,
                5,
                "brain",
                "real",
            ),
            Achievement(
                "difficulties",
                "Construindo pontes",
                "Trabalhar dificuldades descritas por você.",
                practiced,
                3,
                "swords",
                "real",
            ),
            Achievement(
                "bosses",
                "Encontro com o guardião",
                "Registrar um chefe por meio de simulado real.",
                bosses,
                1,
                "crown",
                "real",
            ),
        ]

    def chapters(self, plan):
        rows = self.engine.story(plan)
        current = max((r["chapter"] for r in rows if r["unlocked"]), default=None)
        return [
            Chapter(
                r["chapter"],
                r["title"],
                r["text"],
                (
                    "current"
                    if r["chapter"] == current
                    else "done" if r["unlocked"] else "locked"
                ),
                r["requirement"],
                "real",
            )
            for r in rows
        ]

    def challenges(self, plan):
        result = []
        for row in self.engine.challenges(plan):
            names = {
                self.store.one(
                    "SELECT name FROM subjects WHERE id=?", (t["subject_id"],)
                )["name"]
                for t in row["topics"]
            }
            detail = f"{row['total']}/{row['questions']} questões registradas · {row['source'] or 'Material externo escolhido por você'}"
            if row["time_exceeded"]:
                detail += " · Tempo sugerido ultrapassado, sem penalidade"
            result.append(
                Challenge(
                    id=row["id"],
                    kind="chefe" if row["kind"] == "Chefe" else "masmorra",
                    title=row["name"],
                    detail=detail,
                    questions=row["questions"],
                    minutes=(row["time_limit"] or 0) // 60,
                    subjects=tuple(sorted(names)),
                    available=True,
                    source="real",
                )
            )
        return result

    def reward_for(self, session, subject):
        rows = self.engine.reward_details(session.get("id"))
        if not rows:
            return None
        return Reward(
            seconds=session["elapsed"],
            questions=session.get("correct", 0)
            + session.get("wrong", 0)
            + session.get("blank", 0),
            subject=subject,
            xp=sum(r["xp"] for r in rows),
            coins=sum(r["coins"] for r in rows),
            source="real",
        )
