"""Offline RPG rules derived from canonical study activities, never demo data."""

import json
import math
import uuid
from datetime import date

from rpg_schema import CATALOG, STORY
from rpg_progression import metrics, paths, requirement

RECALL = ("Lembrei", "Parcial", "Não lembrei")
STATES = ("Aberta", "Em prática", "Superada pelo usuário")
CONTEXT_KEYS = ("mission_id", "difficulty_id", "challenge_id", "recall")


def identifier():
    return uuid.uuid4().hex


def text(value, label, required=False, maximum=4000):
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (required and not value.strip())
    ):
        raise ValueError(f"{label}: texto inválido.")
    return value.strip()


def positive(value, label, maximum=100000):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{label}: informe um inteiro positivo até {maximum}.")
    return value


def level_for(xp):
    # Level 1 starts at zero. L -> L+1 costs 100*L XP.
    level = (1 + math.isqrt(1 + 8 * (xp // 100))) // 2
    level = max(1, level)
    while 50 * level * (level + 1) <= xp:
        level += 1
    return level


class RPGService:
    def __init__(self, store):
        self.store = store
        self.db = store.db
        self._new_equipment = {}

    def _plan(self, plan):
        row = self.store.one("SELECT * FROM plans WHERE id=?", (plan,))
        if not row:
            raise ValueError("Plano inexistente.")
        return row

    def _topic(self, topic, plan=None):
        row = self.store.one(
            "SELECT t.*,s.plan_id,s.name subject FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE t.id=?",
            (topic,),
        )
        if not row or (plan is not None and row["plan_id"] != plan):
            raise ValueError("Assunto inexistente ou fora do plano.")
        return row

    def _row(self, table, key):
        if table not in ("rpg_missions", "rpg_difficulties", "rpg_challenges"):
            raise ValueError("Tipo de atividade inválido.")
        row = self.store.one(f"SELECT * FROM {table} WHERE id=?", (key,))
        if not row:
            raise ValueError("Atividade inexistente.")
        return row

    def _enroll(self, kind, key):
        columns = {
            "session": "session_id",
            "review": "review_id",
            "challenge": "challenge_id",
        }
        column = columns[kind]
        self.db.execute(
            f"INSERT OR IGNORE INTO rpg_sources(id,{column}) VALUES(?,?)",
            (kind + ":" + key, key),
        )

    def session_saved(self, session_id, is_new, context=None):
        if is_new:
            self._enroll("session", session_id)
        if not is_new:
            prior = self.store.one(
                "SELECT * FROM rpg_links WHERE session_id=?", (session_id,)
            )
            if prior:
                try:
                    self._attach(session_id, {key: prior[key] for key in CONTEXT_KEYS})
                except ValueError:
                    # A correction can change the subject; preserve the study and
                    # difficulty, but remove associations that no longer fit.
                    self._attach(session_id, {key: None for key in CONTEXT_KEYS})
        if context:
            self._attach(session_id, context)
        session = self.store.one("SELECT * FROM sessions WHERE id=?", (session_id,))
        eligible = self.store.one(
            "SELECT id FROM rpg_sources WHERE session_id=?", (session_id,)
        )
        if session["review_id"] and eligible:
            self._enroll("review", session["review_id"])
        self.sync_in_transaction()

    def review_changed(self, review_id, previous_state):
        row = self.store.one("SELECT state FROM reviews WHERE id=?", (review_id,))
        if row and row["state"] == "Concluída" and previous_state != "Concluída":
            self._enroll("review", review_id)
        self.sync_in_transaction()

    def _attach(self, session_id, context):
        if not isinstance(context, dict) or set(context) - set(CONTEXT_KEYS):
            raise ValueError("Contexto de estudo inválido.")
        session = self.store.one("SELECT * FROM sessions WHERE id=?", (session_id,))
        old = (
            self.store.one("SELECT * FROM rpg_links WHERE session_id=?", (session_id,))
            or {}
        )
        values = {key: context.get(key, old.get(key)) for key in CONTEXT_KEYS}
        if values["recall"] is not None and values["recall"] not in RECALL:
            raise ValueError("Autoavaliação de lembrança inválida.")
        for field, table in [
            ("mission_id", "rpg_missions"),
            ("difficulty_id", "rpg_difficulties"),
        ]:
            if not values[field]:
                continue
            row = self._row(table, values[field])
            if any(row[k] != session[k] for k in ("plan_id", "subject_id", "topic_id")):
                raise ValueError("Missão ou dificuldade fora do estudo escolhido.")
            if field == "mission_id":
                if row["block_id"] and (
                    row["block_id"] != session["block_id"]
                    or row["lap"] != session["lap"]
                ):
                    raise ValueError(
                        "Missão incompatível com o bloco ou volta do ciclo."
                    )
                if row["review_id"] and row["review_id"] != session["review_id"]:
                    raise ValueError("Missão incompatível com a revisão.")
                if row["difficulty_id"]:
                    if (
                        values["difficulty_id"]
                        and values["difficulty_id"] != row["difficulty_id"]
                    ):
                        raise ValueError("Dificuldade incompatível com a missão.")
                    values["difficulty_id"] = row["difficulty_id"]
        if values["challenge_id"]:
            challenge = self._row("rpg_challenges", values["challenge_id"])
            if challenge["plan_id"] != session["plan_id"]:
                raise ValueError("Desafio fora do plano.")
            if challenge["kind"] == "Chefe" and session["category"] != "Simulado":
                raise ValueError("Um chefe deve usar um simulado real.")
            if challenge["kind"] == "Masmorra" and session["category"] not in (
                "Questões",
                "Revisão",
                "Simulado",
            ):
                raise ValueError(
                    "A masmorra precisa de prática de questões ou revisão."
                )
            topics = self.store.rows(
                "SELECT t.id,t.subject_id FROM rpg_challenge_topics c JOIN topics t ON t.id=c.topic_id WHERE c.challenge_id=?",
                (challenge["id"],),
            )
            if session["category"] != "Simulado" and session["topic_id"] not in {
                t["id"] for t in topics
            }:
                raise ValueError("Assunto fora do desafio.")
            allowed = {t["subject_id"] for t in topics}
            results = self.store.rows(
                "SELECT subject_id FROM mock_results WHERE session_id=?", (session_id,)
            )
            if results and any(r["subject_id"] not in allowed for r in results):
                raise ValueError("O simulado inclui matérias fora do desafio.")
            if session["subject_id"] and session["subject_id"] not in allowed:
                raise ValueError("Matéria fora do desafio.")
        self.db.execute(
            "INSERT INTO rpg_links(session_id,mission_id,difficulty_id,challenge_id,recall) VALUES(?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET mission_id=excluded.mission_id,difficulty_id=excluded.difficulty_id,challenge_id=excluded.challenge_id,recall=excluded.recall",
            (session_id, *(values[k] for k in CONTEXT_KEYS)),
        )
        if values["difficulty_id"] and (
            session["elapsed"] > 0 or session["correct"] + session["wrong"] > 0
        ):
            self.db.execute(
                "UPDATE rpg_difficulties SET state='Em prática' WHERE id=? AND state='Aberta'",
                (values["difficulty_id"],),
            )

    def attach_session(self, session_id, context):
        if not self.store.one("SELECT id FROM sessions WHERE id=?", (session_id,)):
            raise ValueError("Estudo inexistente.")
        with self.db:
            self._attach(session_id, context)
            self.sync_in_transaction()

    def _reward(self, source, plan, subject, xp, explanation):
        self.db.execute(
            "INSERT INTO rpg_rewards VALUES(?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET plan_id=excluded.plan_id,subject_id=excluded.subject_id,xp=excluded.xp,coins=excluded.coins,explanation=excluded.explanation",
            (source, plan, subject, xp, xp // 10, explanation),
        )

    def sync_in_transaction(self):
        self._new_equipment = {}
        self.db.execute("DELETE FROM rpg_rewards")
        for source in self.store.rows("SELECT * FROM rpg_sources"):
            if source["session_id"]:
                session = self.store.one(
                    "SELECT * FROM sessions WHERE id=?", (source["session_id"],)
                )
                xp = session["elapsed"] // 60
                self._reward(
                    source["id"],
                    session["plan_id"],
                    session["subject_id"],
                    xp,
                    f"{session['elapsed']} segundos líquidos ÷ 60, arredondados para baixo = {xp} XP. Pausas, acertos e quantidade de questões não multiplicam XP. {xp // 10} moedas (XP desta atividade ÷ 10).",
                )
            elif source["review_id"]:
                review = self.store.one(
                    "SELECT r.*,t.subject_id,s.plan_id FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id WHERE r.id=?",
                    (source["review_id"],),
                )
                xp = 5 if review["state"] == "Concluída" else 0
                self._reward(
                    source["id"],
                    review["plan_id"],
                    review["subject_id"],
                    xp,
                    f"Revisão realizada: {xp} XP de participação, uma vez por revisão. A data de vencimento e o resultado não alteram a recompensa; o tempo pertence apenas à sessão.",
                )
            else:
                challenge = self._row("rpg_challenges", source["challenge_id"])
                progress = self.challenge(challenge["id"])
                xp = 5 if progress["completed"] else 0
                self._reward(
                    source["id"],
                    challenge["plan_id"],
                    None,
                    xp,
                    f"Desafio realizado: {xp} XP de participação, uma vez por desafio. Notas não multiplicam XP; duração e questões continuam somente nos estudos originais.",
                )
        for mission in self.store.rows(
            "SELECT id,state FROM rpg_missions WHERE state!='Arquivada'"
        ):
            state = "Concluída" if self.mission(mission["id"])["completed"] else "Ativa"
            self.db.execute(
                "UPDATE rpg_missions SET state=? WHERE id=?", (state, mission["id"])
            )
        for plan in self.store.rows("SELECT id FROM plans"):
            self._sync_story(plan["id"])
            self._sync_equipment(plan["id"])

    def sync(self):
        with self.db:
            self.sync_in_transaction()

    def profile(self, plan):
        self._plan(plan)
        totals = self.store.one(
            "SELECT COALESCE(SUM(xp),0) xp,COALESCE(SUM(coins),0) earned FROM rpg_rewards WHERE plan_id=?",
            (plan,),
        )
        spent = self.store.one(
            "SELECT COALESCE(SUM(price),0) total FROM rpg_inventory WHERE plan_id=?",
            (plan,),
        )["total"]
        level = level_for(totals["xp"])
        floor = 50 * (level - 1) * level
        ceiling = 50 * level * (level + 1)
        name = self.store.one(
            "SELECT name FROM rpg_characters WHERE plan_id=?", (plan,)
        )
        skills = []
        for subject in self.store.subject_stats(plan):
            xp = self.store.one(
                "SELECT COALESCE(SUM(xp),0) xp FROM rpg_rewards WHERE plan_id=? AND subject_id=?",
                (plan, subject["id"]),
            )["xp"]
            count = self.store.one(
                "SELECT COUNT(DISTINCT s.day) n FROM sessions s LEFT JOIN mock_results m ON m.session_id=s.id WHERE s.plan_id=? AND ((m.subject_id=? AND m.correct+m.wrong>0) OR (s.subject_id=? AND s.correct+s.wrong>0 AND NOT EXISTS(SELECT 1 FROM mock_results r WHERE r.session_id=s.id)))",
                (plan, subject["id"], subject["id"]),
            )["n"]
            answered = subject["correct"] + subject["wrong"]
            sufficient = answered >= 20 and count >= 3
            skills.append(
                dict(
                    subject,
                    xp=xp,
                    level=level_for(xp),
                    performance=(
                        round(100 * subject["correct"] / answered, 1)
                        if sufficient
                        else None
                    ),
                    evidence_days=count,
                    answered=answered,
                    evidence_label=(
                        "Aproveitamento observado; não comprova domínio"
                        if sufficient
                        else "Dados insuficientes"
                    ),
                )
            )
        return {
            "name": name["name"] if name else "Viajante",
            "xp": totals["xp"],
            "level": level,
            "level_xp": totals["xp"] - floor,
            "next_level_xp": ceiling - floor,
            "next_level_at": ceiling,
            "coins": max(0, totals["earned"] - spent),
            "earned_coins": totals["earned"],
            "spent_coins": spent,
            "correction_credit": max(0, spent - totals["earned"]),
            "skills": skills,
            "explanation": "1 XP por minuto líquido completo; 5 XP por revisão ou desafio realizado. Acertos não são requisito. Cada origem conta uma vez. Correções recalculam recompensas sem apagar itens.",
        }

    def rename_character(self, plan, name):
        self._plan(plan)
        name = text(name, "Nome", True, 60)
        with self.db:
            self.db.execute(
                "INSERT INTO rpg_characters VALUES(?,?) ON CONFLICT(plan_id) DO UPDATE SET name=excluded.name",
                (plan, name),
            )

    def reward_details(self, session_id):
        return self.store.rows(
            "SELECT r.* FROM rpg_rewards r JOIN rpg_sources e ON e.id=r.source_id WHERE e.session_id=? OR e.review_id IN (SELECT id FROM reviews WHERE completed_id=?)",
            (session_id, session_id),
        )

    def retroactive_preview(self, plan):
        self._plan(plan)
        rows = self.store.rows(
            "SELECT s.* FROM sessions s WHERE s.plan_id=? AND NOT EXISTS(SELECT 1 FROM rpg_sources e WHERE e.session_id=s.id) ORDER BY s.day,s.id",
            (plan,),
        )
        return {
            "sessions": rows,
            "xp": sum(r["elapsed"] // 60 for r in rows),
            "coins": sum((r["elapsed"] // 60) // 10 for r in rows),
        }

    def enroll_history(self, plan, session_ids):
        self._plan(plan)
        if not isinstance(session_ids, (list, tuple)) or len(session_ids) != len(
            set(session_ids)
        ):
            raise ValueError("Selecione registros distintos na prévia.")
        rows = []
        for sid in session_ids:
            row = self.store.one(
                "SELECT * FROM sessions WHERE id=? AND plan_id=?", (sid, plan)
            )
            if not row:
                raise ValueError("Estudo fora do plano.")
            rows.append(row)
        with self.db:
            for row in rows:
                self._enroll("session", row["id"])
            self.sync_in_transaction()
        return self.profile(plan)

    def recommended_mission(self, plan, topic_id=None):
        self._plan(plan)
        cycle = self.store.current_cycle(plan)
        blocks = self.store.cycle_blocks(cycle) if cycle else []
        block = (
            blocks[cycle["position"]]
            if cycle and cycle["position"] < len(blocks)
            else None
        )
        if not topic_id and block and not block["topic_id"]:
            choice = self.store.one(
                "SELECT topic_id FROM rpg_missions WHERE block_id=? AND lap=? AND kind='Estudo' AND state!='Arquivada' ORDER BY rowid DESC LIMIT 1",
                (block["id"], cycle["lap"]),
            )
            if choice:
                topic_id = choice["topic_id"]
        if topic_id:
            topic = self._topic(topic_id, plan)
            if block and (
                topic["subject_id"] != block["subject_id"]
                or (block["topic_id"] and block["topic_id"] != topic_id)
            ):
                raise ValueError("Escolha um assunto da matéria do próximo bloco.")
        elif block:
            if block["topic_id"]:
                topic = self._topic(block["topic_id"], plan)
            else:
                from learning import next_topic

                topic = next_topic(self.store, block["subject_id"])
        else:
            topic = self.store.one(
                "SELECT t.* FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND s.archived=0 AND t.archived=0 AND NOT EXISTS(SELECT 1 FROM topics child WHERE child.parent_id=t.id AND child.archived=0) ORDER BY t.done,t.rowid LIMIT 1",
                (plan,),
            )
        if not topic:
            return None
        query = "SELECT id FROM rpg_missions WHERE plan_id=? AND topic_id=? AND kind='Estudo' AND state!='Arquivada'"
        args = [plan, topic["id"]]
        if block:
            query += " AND block_id=? AND lap=?"
            args.extend([block["id"], cycle["lap"]])
        else:
            query += " AND block_id IS NULL AND state='Ativa'"
        previous = self.store.one(query + " ORDER BY rowid DESC LIMIT 1", args)
        if previous:
            return self.mission(previous["id"])
        if block and block["elapsed"] >= block["target"]:
            return None
        last = self.store.one(
            "SELECT next_step FROM sessions WHERE plan_id=? AND topic_id=? ORDER BY day DESC,start_time DESC,rowid DESC LIMIT 1",
            (plan, topic["id"]),
        )
        target = (
            max(60, block["target"] - block["elapsed"])
            if block
            else int(self.store.pref("focus_minutes", 25)) * 60
        )
        with self.db:
            mid = self.store.put(
                "rpg_missions",
                {
                    "plan_id": plan,
                    "subject_id": topic["subject_id"],
                    "topic_id": topic["id"],
                    "block_id": block["id"] if block else None,
                    "lap": cycle["lap"] if block else None,
                    "kind": "Estudo",
                    "target": target,
                    "next_step": (last["next_step"] if last else "")
                    or topic.get("notes", "")
                    or "Abra o material e registre onde continuar.",
                    "created_day": self.store.today().isoformat(),
                },
            )
        return self.mission(mid)

    def mission(self, mission_id):
        row = self._row("rpg_missions", mission_id)
        topic = self._topic(row["topic_id"], row["plan_id"])
        progress = self.store.one(
            "SELECT COALESCE(SUM(s.elapsed),0) elapsed,COUNT(*) sessions FROM rpg_links l JOIN sessions s ON s.id=l.session_id WHERE l.mission_id=? AND s.plan_id=? AND s.subject_id=? AND s.topic_id=?",
            (mission_id, row["plan_id"], row["subject_id"], row["topic_id"]),
        )
        remaining = max(0, row["target"] - progress["elapsed"])
        if row["block_id"]:
            block = self.store.one(
                "SELECT target FROM blocks WHERE id=?", (row["block_id"],)
            )
            total = self.store.one(
                "SELECT COALESCE(SUM(elapsed),0) elapsed FROM sessions WHERE block_id=? AND lap=?",
                (row["block_id"], row["lap"]),
            )
            remaining = min(remaining, max(0, block["target"] - total["elapsed"]))
        last = self.store.one(
            "SELECT s.next_step FROM sessions s JOIN rpg_links l ON l.session_id=s.id WHERE l.mission_id=? ORDER BY s.day DESC,s.rowid DESC LIMIT 1",
            (mission_id,),
        )
        return dict(
            row,
            subject=topic["subject"],
            topic=topic["name"],
            elapsed=progress["elapsed"],
            sessions=progress["sessions"],
            remaining=remaining,
            suggested_seconds=(
                min(row["small_target"] or row["target"], remaining) if remaining else 0
            ),
            next_step=(
                last["next_step"] if last and last["next_step"] else row["next_step"]
            ),
            completed=remaining == 0,
        )

    def missions(self, plan):
        return [
            self.mission(r["id"])
            for r in self.store.rows(
                "SELECT id FROM rpg_missions WHERE plan_id=? ORDER BY rowid DESC",
                (plan,),
            )
        ]

    def small_mission(self, mission_id, minutes=5):
        minutes = positive(minutes, "Minutos", 180)
        self._row("rpg_missions", mission_id)
        with self.db:
            self.db.execute(
                "UPDATE rpg_missions SET small_target=? WHERE id=?",
                (minutes * 60, mission_id),
            )
        return self.mission(mission_id)

    def continue_mission(self, mission_id):
        self._row("rpg_missions", mission_id)
        with self.db:
            self.db.execute(
                "UPDATE rpg_missions SET small_target=NULL WHERE id=?", (mission_id,)
            )
        return self.mission(mission_id)

    def mission_fields(self, mission_id):
        mission = self.mission(mission_id)
        if mission["completed"] or mission["state"] == "Arquivada":
            raise ValueError(
                "Esta missão já terminou. Conclua o bloco explicitamente ou escolha outra missão."
            )
        category = "Revisão" if mission["kind"] != "Estudo" else "Teoria"
        if mission["block_id"]:
            category = self.store.one(
                "SELECT category FROM blocks WHERE id=?", (mission["block_id"],)
            )["category"]
        return {
            "plan_id": mission["plan_id"],
            "subject_id": mission["subject_id"],
            "topic_id": mission["topic_id"],
            "category": category,
            "target": max(60, mission["suggested_seconds"]),
            "next_step": mission["next_step"],
            "block_id": mission["block_id"],
            "lap": mission["lap"],
            "review_id": mission["review_id"],
            "mission_id": mission_id,
            "difficulty_id": mission["difficulty_id"],
        }

    def save_difficulty(
        self,
        plan_id,
        topic_id,
        description,
        why,
        remember,
        source="",
        session_id=None,
        difficulty_id=None,
    ):
        self._plan(plan_id)
        topic = self._topic(topic_id, plan_id)
        if session_id:
            session = self.store.one("SELECT * FROM sessions WHERE id=?", (session_id,))
            if not session or session["plan_id"] != plan_id:
                raise ValueError("Estudo fora do plano.")
            results = self.store.rows(
                "SELECT subject_id FROM mock_results WHERE session_id=?", (session_id,)
            )
            allowed = {r["subject_id"] for r in results}
            if session["subject_id"]:
                allowed.add(session["subject_id"])
            if topic["subject_id"] not in allowed or (
                session["topic_id"] and session["topic_id"] != topic_id
            ):
                raise ValueError(
                    "Dificuldade incompatível com a matéria ou assunto do estudo."
                )
        values = {
            "plan_id": plan_id,
            "subject_id": topic["subject_id"],
            "topic_id": topic_id,
            "session_id": session_id,
            "description": text(description, "Descrição", True),
            "why": text(why, "Por que errei?", True),
            "remember": text(remember, "O que lembrar?", True),
            "source": text(source, "Referência"),
            "created_day": self.store.today().isoformat(),
        }
        if difficulty_id:
            previous = self._row("rpg_difficulties", difficulty_id)
            if any(
                previous[k] != values[k] for k in ("plan_id", "subject_id", "topic_id")
            ):
                raise ValueError(
                    "A dificuldade não pode ser movida para outro assunto."
                )
            values.update(id=difficulty_id, created_day=previous["created_day"])
        with self.db:
            return self.store.put("rpg_difficulties", values)

    def difficulties(self, plan):
        return self.store.rows(
            "SELECT d.*,t.name topic,s.name subject FROM rpg_difficulties d JOIN topics t ON t.id=d.topic_id JOIN subjects s ON s.id=d.subject_id WHERE d.plan_id=? ORDER BY d.created_day DESC,d.rowid DESC",
            (plan,),
        )

    def set_difficulty_state(self, difficulty_id, state):
        self._row("rpg_difficulties", difficulty_id)
        if state not in STATES:
            raise ValueError("Estado de dificuldade inválido.")
        with self.db:
            self.db.execute(
                "UPDATE rpg_difficulties SET state=? WHERE id=?", (state, difficulty_id)
            )
            self.sync_in_transaction()

    def difficulty_evidence(self, difficulty_id):
        self._row("rpg_difficulties", difficulty_id)
        rows = self.store.rows(
            "SELECT s.*,l.recall FROM rpg_links l JOIN sessions s ON s.id=l.session_id JOIN rpg_difficulties d ON d.id=l.difficulty_id WHERE l.difficulty_id=? AND s.plan_id=d.plan_id AND s.topic_id=d.topic_id AND s.subject_id=d.subject_id AND (s.elapsed>0 OR s.correct+s.wrong>0) ORDER BY s.day,s.id",
            (difficulty_id,),
        )
        by_day = {}
        for row in rows:
            answered = row["correct"] + row["wrong"]
            positive_result = (
                answered >= 5 and row["correct"] / answered >= 0.7
            ) or row["recall"] == "Lembrei"
            by_day.setdefault(row["day"], []).append(positive_result)
        days = [date.fromisoformat(day) for day in sorted(by_day)]
        spaced = []
        for day in days:
            if not spaced or (day - spaced[-1]).days >= 2:
                spaced.append(day)
        evidence = len(spaced) >= 3 and (spaced[-1] - spaced[0]).days >= 7
        recent = [all(by_day[d.isoformat()]) for d in spaced[-2:]]
        suggestion = evidence and len(recent) == 2 and all(recent)
        return {
            "encounters": rows,
            "separate_days": len(days),
            "spaced_days": len(spaced),
            "suggest_overcome": suggestion,
            "explanation": "Sugestão: pelo menos 3 dias de prática separados por 2 dias e abrangendo 7 dias; nos 2 últimos encontros, ao menos 5 questões com 70% ou autoavaliação 'Lembrei'. Autoavaliação não é nota objetiva. Só você marca a dificuldade como superada.",
        }

    def revenge_mission(self, difficulty_id, minutes=15):
        difficulty = self._row("rpg_difficulties", difficulty_id)
        positive(minutes, "Minutos", 180)
        previous = self.store.one(
            "SELECT id FROM rpg_missions WHERE difficulty_id=? AND state='Ativa' ORDER BY rowid DESC LIMIT 1",
            (difficulty_id,),
        )
        if previous:
            return self.mission(previous["id"])
        with self.db:
            review = self.store.one(
                "SELECT id FROM reviews WHERE topic_id=? AND state='Pendente' ORDER BY due LIMIT 1",
                (difficulty["topic_id"],),
            )
            if not review:
                today = self.store.today().isoformat()
                self.db.execute(
                    "INSERT OR IGNORE INTO reviews(id,topic_id,origin_id,due,interval) VALUES(?,?,?,?,1)",
                    (
                        identifier(),
                        difficulty["topic_id"],
                        difficulty["session_id"],
                        today,
                    ),
                )
                review = self.store.one(
                    "SELECT id FROM reviews WHERE topic_id=? AND due=? AND interval=1",
                    (difficulty["topic_id"], today),
                )
            mid = self.store.put(
                "rpg_missions",
                {
                    "plan_id": difficulty["plan_id"],
                    "subject_id": difficulty["subject_id"],
                    "topic_id": difficulty["topic_id"],
                    "review_id": review["id"],
                    "difficulty_id": difficulty_id,
                    "kind": "Revanche",
                    "target": minutes * 60,
                    "next_step": "Antes de consultar, tente explicar. Confira: "
                    + difficulty["remember"]
                    + ". Depois pratique questões do seu material, se fizer sentido.",
                    "created_day": self.store.today().isoformat(),
                },
            )
        return self.mission(mid)

    def review_fields(self, review_id):
        row = self.store.one(
            "SELECT r.*,t.subject_id,s.plan_id FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id WHERE r.id=?",
            (review_id,),
        )
        if not row or row["state"] != "Pendente":
            raise ValueError("Escolha uma revisão pendente.")
        previous = self.store.one(
            "SELECT id FROM rpg_missions WHERE review_id=? AND kind='Encontro' AND state='Ativa' LIMIT 1",
            (review_id,),
        )
        if previous:
            return self.mission_fields(previous["id"])
        with self.db:
            mid = self.store.put(
                "rpg_missions",
                {
                    "plan_id": row["plan_id"],
                    "subject_id": row["subject_id"],
                    "topic_id": row["topic_id"],
                    "review_id": review_id,
                    "kind": "Encontro",
                    "target": 15 * 60,
                    "next_step": "Tente lembrar ou explicar antes de consultar. Confira o material e registre sua autoavaliação; questões são opcionais.",
                    "created_day": self.store.today().isoformat(),
                },
            )
        return self.mission_fields(mid)

    def create_challenge(
        self,
        plan_id,
        name,
        topic_ids,
        questions=20,
        time_limit=None,
        source="",
        kind="Masmorra",
    ):
        self._plan(plan_id)
        if kind not in ("Masmorra", "Chefe"):
            raise ValueError("Tipo de desafio inválido.")
        positive(questions, "Questões", 10000)
        if time_limit is not None:
            positive(time_limit, "Tempo", 86400)
        if (
            not isinstance(topic_ids, (list, tuple))
            or not topic_ids
            or len(topic_ids) > 100
            or len(set(topic_ids)) != len(topic_ids)
        ):
            raise ValueError("Selecione de 1 a 100 assuntos distintos já estudados.")
        for topic_id in topic_ids:
            self._topic(topic_id, plan_id)
            if not self.store.one(
                "SELECT id FROM sessions WHERE plan_id=? AND topic_id=? AND (elapsed>0 OR correct+wrong>0) LIMIT 1",
                (plan_id, topic_id),
            ):
                raise ValueError("O desafio só pode agrupar assuntos já estudados.")
        with self.db:
            cid = self.store.put(
                "rpg_challenges",
                {
                    "plan_id": plan_id,
                    "name": text(name, "Nome", True, 120),
                    "kind": kind,
                    "questions": questions,
                    "time_limit": time_limit,
                    "source": text(source, "Origem do material"),
                    "created_day": self.store.today().isoformat(),
                },
            )
            for topic_id in topic_ids:
                self.db.execute(
                    "INSERT INTO rpg_challenge_topics VALUES(?,?)", (cid, topic_id)
                )
            self._enroll("challenge", cid)
            self.sync_in_transaction()
        return cid

    def challenge(self, challenge_id):
        row = self._row("rpg_challenges", challenge_id)
        stats = self.store.one(
            "SELECT COALESCE(SUM(s.correct),0) correct,COALESCE(SUM(s.wrong),0) wrong,COALESCE(SUM(s.blank),0) blank,COALESCE(SUM(s.elapsed),0) elapsed,COUNT(*) sessions FROM rpg_links l JOIN sessions s ON s.id=l.session_id WHERE l.challenge_id=? AND s.plan_id=?",
            (challenge_id, row["plan_id"]),
        )
        total = stats["correct"] + stats["wrong"] + stats["blank"]
        return dict(
            row,
            **stats,
            total=total,
            completed=stats["sessions"] > 0 and total >= row["questions"],
            topics=self.store.rows(
                "SELECT t.id,t.name,t.subject_id FROM rpg_challenge_topics c JOIN topics t ON t.id=c.topic_id WHERE c.challenge_id=?",
                (challenge_id,),
            ),
            time_exceeded=row["time_limit"] is not None
            and stats["elapsed"] > row["time_limit"],
        )

    def challenges(self, plan):
        return [
            self.challenge(r["id"])
            for r in self.store.rows(
                "SELECT id FROM rpg_challenges WHERE plan_id=? ORDER BY rowid DESC",
                (plan,),
            )
        ]

    def challenge_fields(self, challenge_id):
        challenge = self.challenge(challenge_id)
        topic = self._topic(challenge["topics"][0]["id"], challenge["plan_id"])
        fields = {
            "plan_id": challenge["plan_id"],
            "challenge_id": challenge_id,
            "target": challenge["time_limit"] or 25 * 60,
            "material": challenge["source"],
            "category": "Simulado" if challenge["kind"] == "Chefe" else "Questões",
            "next_step": "Faça as questões do material escolhido e registre os resultados uma única vez.",
        }
        if challenge["kind"] == "Chefe":
            fields.update(
                mock_name=challenge["name"],
                mock_format="Múltipla escolha",
                score_wrong=0,
            )
        else:
            fields.update(subject_id=topic["subject_id"], topic_id=topic["id"])
        return fields

    def progression(self, plan):
        self._plan(plan)
        return paths(metrics(self.store, plan))

    def _sync_equipment(self, plan):
        progress = metrics(self.store, plan)
        xp = self.store.one(
            "SELECT COALESCE(SUM(xp),0) xp FROM rpg_rewards WHERE plan_id=?", (plan,)
        )["xp"]
        level = level_for(xp)
        for key, item in CATALOG.items():
            if item.get("acquisition") != "reward" or level < item["level"]:
                continue
            rule = item.get("rule")
            if rule and progress[rule[0]] < rule[1]:
                continue
            equipped = bool(item.get("starter")) and not self.store.one(
                "SELECT item_id FROM rpg_inventory WHERE plan_id=? AND slot=? AND equipped=1",
                (plan, item["slot"]),
            )
            inserted = self.db.execute(
                "INSERT OR IGNORE INTO rpg_inventory VALUES(?,?,?,?,?,?)",
                (
                    plan,
                    key,
                    item["slot"],
                    0,
                    int(equipped),
                    self.store.today().isoformat(),
                ),
            )
            if inserted.rowcount and not item.get("starter"):
                self._new_equipment.setdefault(plan, []).append(key)

    def consume_equipment_rewards(self, plan):
        keys = self._new_equipment.pop(plan, [])
        return [
            CATALOG[key]["name"]
            for key in keys
            if self.store.one(
                "SELECT item_id FROM rpg_inventory WHERE plan_id=? AND item_id=?",
                (plan, key),
            )
        ]

    def catalog(self, plan):
        self._plan(plan)
        with self.db:
            self._sync_equipment(plan)
        profile = self.profile(plan)
        progress = metrics(self.store, plan)
        owned = {
            r["item_id"]: r
            for r in self.store.rows(
                "SELECT * FROM rpg_inventory WHERE plan_id=?", (plan,)
            )
        }
        return [
            dict(
                item,
                id=key,
                owned=key in owned,
                equipped=bool(owned.get(key, {}).get("equipped")),
                available=profile["level"] >= item["level"]
                and (
                    not item.get("rule") or progress[item["rule"][0]] >= item["rule"][1]
                ),
                affordable=profile["coins"] >= item["price"],
                requirement=requirement(item),
            )
            for key, item in CATALOG.items()
        ]

    def buy(self, plan, item_id):
        self._plan(plan)
        if item_id not in CATALOG:
            raise ValueError("Item inexistente.")
        item = CATALOG[item_id]
        with self.db:
            if self.store.one(
                "SELECT item_id FROM rpg_inventory WHERE plan_id=? AND item_id=?",
                (plan, item_id),
            ):
                return
            if item.get("acquisition") == "reward":
                self._sync_equipment(plan)
                if not self.store.one(
                    "SELECT item_id FROM rpg_inventory WHERE plan_id=? AND item_id=?",
                    (plan, item_id),
                ):
                    raise ValueError(
                        "Esta recompensa exige o nível e o marco de estudo indicados; não pode ser comprada."
                    )
                return
            profile = self.profile(plan)
            if profile["level"] < item["level"] or profile["coins"] < item["price"]:
                raise ValueError(
                    "Nível ou saldo insuficiente. Correções nunca criam saldo negativo."
                )
            self.db.execute(
                "INSERT INTO rpg_inventory VALUES(?,?,?,?,0,?)",
                (
                    plan,
                    item_id,
                    item["slot"],
                    item["price"],
                    self.store.today().isoformat(),
                ),
            )

    def equip(self, plan, item_id):
        self._plan(plan)
        item = self.store.one(
            "SELECT * FROM rpg_inventory WHERE plan_id=? AND item_id=?", (plan, item_id)
        )
        if not item:
            raise ValueError("Adquira o item antes de equipar.")
        with self.db:
            self.db.execute(
                "UPDATE rpg_inventory SET equipped=0 WHERE plan_id=? AND slot=?",
                (plan, item["slot"]),
            )
            self.db.execute(
                "UPDATE rpg_inventory SET equipped=1 WHERE plan_id=? AND item_id=?",
                (plan, item_id),
            )

    def equipment_action(self, plan, item_id):
        self._plan(plan)
        item = CATALOG.get(item_id)
        owned = self.store.one(
            "SELECT equipped FROM rpg_inventory WHERE plan_id=? AND item_id=?",
            (plan, item_id),
        )
        if not item or not owned or not owned["equipped"]:
            raise ValueError("Conquiste e equipe o item para usar seu atalho.")
        return item["action"]

    def _sync_story(self, plan):
        first = (
            self.store.one(
                "SELECT COUNT(*) n FROM rpg_sources e JOIN sessions s ON s.id=e.session_id WHERE s.plan_id=? AND s.elapsed>0",
                (plan,),
            )["n"]
            > 0
        )
        review = (
            self.store.one(
                "SELECT COUNT(*) n FROM rpg_rewards r JOIN rpg_sources e ON e.id=r.source_id WHERE r.plan_id=? AND e.review_id IS NOT NULL AND r.xp>0",
                (plan,),
            )["n"]
            > 0
        )
        difficulty = (
            self.store.one(
                "SELECT COUNT(*) n FROM rpg_links l JOIN sessions s ON s.id=l.session_id JOIN rpg_sources e ON e.session_id=s.id WHERE s.plan_id=? AND l.difficulty_id IS NOT NULL AND (s.elapsed>0 OR s.correct+s.wrong>0)",
                (plan,),
            )["n"]
            > 0
        )
        lap = (
            self.store.one(
                "SELECT COUNT(*) n FROM cycles c WHERE c.plan_id=? AND EXISTS(SELECT 1 FROM decisions d JOIN blocks b ON b.id=d.block_id WHERE b.cycle_id=c.id AND d.state='Concluído' AND EXISTS(SELECT 1 FROM rpg_sources e JOIN sessions s ON s.id=e.session_id WHERE s.block_id=b.id AND s.lap=d.lap AND s.elapsed>0) AND NOT EXISTS(SELECT 1 FROM blocks x WHERE x.cycle_id=c.id AND x.archived=0 AND NOT EXISTS(SELECT 1 FROM decisions y WHERE y.block_id=x.id AND y.lap=d.lap AND y.state='Concluído')))",
                (plan,),
            )["n"]
            > 0
        )
        for chapter, achieved in enumerate((first, review, difficulty, lap), 1):
            existing = self.store.one(
                "SELECT chapter FROM rpg_story WHERE plan_id=? AND chapter=?",
                (plan, chapter),
            )
            if not achieved and not existing:
                break
            if achieved:
                self.db.execute(
                    "INSERT OR IGNORE INTO rpg_story VALUES(?,?,?)",
                    (plan, chapter, self.store.today().isoformat()),
                )

    def story(self, plan):
        self._plan(plan)
        chapters = {
            r["chapter"]: r["unlocked_day"]
            for r in self.store.rows("SELECT * FROM rpg_story WHERE plan_id=?", (plan,))
        }
        return [
            {
                "chapter": i,
                "title": title,
                "text": body,
                "requirement": requirement,
                "unlocked": i in chapters,
                "unlocked_day": chapters.get(i),
            }
            for i, (title, body, requirement) in enumerate(STORY, 1)
        ]
