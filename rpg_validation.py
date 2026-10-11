"""Validate RPG backup links and deterministic rewards before restoring."""

from datetime import date
import json
from rpg_schema import CATALOG


def validate_rpg(tables):
    sessions = {r["id"]: r for r in tables["sessions"]}
    topics = {r["id"]: r for r in tables["topics"]}
    subjects = {r["id"]: r for r in tables["subjects"]}
    reviews = {r["id"]: r for r in tables["reviews"]}
    blocks = {r["id"]: r for r in tables["blocks"]}
    cycles = {r["id"]: r for r in tables["cycles"]}
    missions = {r["id"]: r for r in tables["rpg_missions"]}
    difficulties = {r["id"]: r for r in tables["rpg_difficulties"]}
    challenges = {r["id"]: r for r in tables["rpg_challenges"]}
    sources = {r["id"]: r for r in tables["rpg_sources"]}
    links = {r["session_id"]: r for r in tables["rpg_links"]}
    challenge_topics = {}
    for row in tables["rpg_challenge_topics"]:
        challenge_topics.setdefault(row["challenge_id"], set()).add(row["topic_id"])
        if (
            subjects[topics[row["topic_id"]]["subject_id"]]["plan_id"]
            != challenges[row["challenge_id"]]["plan_id"]
        ):
            raise ValueError("Assunto de desafio fora do plano.")
    for table in ("rpg_difficulties", "rpg_missions"):
        for row in tables[table]:
            if (
                topics[row["topic_id"]]["subject_id"] != row["subject_id"]
                or subjects[row["subject_id"]]["plan_id"] != row["plan_id"]
            ):
                raise ValueError("Atividade RPG fora da matéria ou plano.")
            date.fromisoformat(row["created_day"])
            if table == "rpg_difficulties":
                for key in ("description", "why", "remember"):
                    if (
                        not isinstance(row[key], str)
                        or not row[key].strip()
                        or len(row[key]) > 4000
                    ):
                        raise ValueError("Descrição de dificuldade inválida.")
                if (
                    row["session_id"]
                    and sessions[row["session_id"]]["plan_id"] != row["plan_id"]
                ):
                    raise ValueError("Origem da dificuldade fora do plano.")
                if row["session_id"]:
                    origin = sessions[row["session_id"]]
                    allowed = {
                        r["subject_id"]
                        for r in tables["mock_results"]
                        if r["session_id"] == origin["id"]
                    }
                    if origin["subject_id"]:
                        allowed.add(origin["subject_id"])
                    if row["subject_id"] not in allowed or (
                        origin["topic_id"] and origin["topic_id"] != row["topic_id"]
                    ):
                        raise ValueError(
                            "Origem da dificuldade fora da matéria ou assunto."
                        )
            else:
                for key in ("target", "small_target"):
                    if row[key] is not None and (
                        type(row[key]) is not int or not 60 <= row[key] <= 86400
                    ):
                        raise ValueError("Duração de missão inválida.")
                if row["block_id"]:
                    block = blocks[row["block_id"]]
                    if (
                        block["subject_id"] != row["subject_id"]
                        or (block["topic_id"] and block["topic_id"] != row["topic_id"])
                        or cycles[block["cycle_id"]]["plan_id"] != row["plan_id"]
                        or type(row["lap"]) is not int
                        or row["lap"] < 1
                    ):
                        raise ValueError("Missão fora do bloco ou volta.")
                if (
                    row["review_id"]
                    and reviews[row["review_id"]]["topic_id"] != row["topic_id"]
                ):
                    raise ValueError("Missão fora da revisão.")
                if (
                    row["difficulty_id"]
                    and difficulties[row["difficulty_id"]]["topic_id"]
                    != row["topic_id"]
                ):
                    raise ValueError("Missão fora da dificuldade.")
    for row in challenges.values():
        date.fromisoformat(row["created_day"])
        if (
            not isinstance(row["name"], str)
            or not row["name"].strip()
            or len(row["name"]) > 120
            or not challenge_topics.get(row["id"])
        ):
            raise ValueError("Nome ou assuntos de desafio inválidos.")
        if type(row["questions"]) is not int or not 1 <= row["questions"] <= 10000:
            raise ValueError("Quantidade de questões inválida.")
        if row["time_limit"] is not None and (
            type(row["time_limit"]) is not int or not 1 <= row["time_limit"] <= 86400
        ):
            raise ValueError("Tempo de desafio inválido.")
    contexts = [(sessions[row["session_id"]], row) for row in links.values()]
    for draft in tables["active"]:
        activity = json.loads(draft["value"])
        context = {
            key: activity.get(key)
            for key in ("mission_id", "difficulty_id", "challenge_id", "recall")
        }
        if any(context.values()):
            if context["recall"] not in (None, "Lembrei", "Parcial", "Não lembrei"):
                raise ValueError("Autoavaliação do relógio inválida.")
            for key, mapping in (
                ("mission_id", missions),
                ("difficulty_id", difficulties),
                ("challenge_id", challenges),
            ):
                if context[key] and context[key] not in mapping:
                    raise ValueError("Origem RPG do relógio não existe.")
            activity = dict(activity)
            for key in ("id", "block_id", "lap", "review_id"):
                activity.setdefault(key, None)
            contexts.append((activity, context))
    for session, row in contexts:
        for key, mapping in [("mission_id", missions), ("difficulty_id", difficulties)]:
            if row[key] and any(
                mapping[row[key]][k] != session[k]
                for k in ("plan_id", "subject_id", "topic_id")
            ):
                raise ValueError("Vínculo RPG incompatível com o estudo.")
        if row["mission_id"]:
            mission = missions[row["mission_id"]]
            if mission["block_id"] and (
                mission["block_id"] != session["block_id"]
                or mission["lap"] != session["lap"]
            ):
                raise ValueError("Estudo fora do bloco da missão.")
            if mission["review_id"] and mission["review_id"] != session["review_id"]:
                raise ValueError("Estudo fora da revisão da missão.")
        if row["challenge_id"]:
            challenge = challenges[row["challenge_id"]]
            if challenge["plan_id"] != session["plan_id"] or (
                challenge["kind"] == "Chefe" and session["category"] != "Simulado"
            ):
                raise ValueError("Estudo fora do desafio.")
            if (
                session["category"] != "Simulado"
                and session["topic_id"] not in challenge_topics[challenge["id"]]
            ):
                raise ValueError("Assunto fora da masmorra.")
            allowed = {
                topics[t]["subject_id"] for t in challenge_topics[challenge["id"]]
            }
            if session["subject_id"] and session["subject_id"] not in allowed:
                raise ValueError("Matéria fora do desafio.")
            for result in tables["mock_results"]:
                if (
                    result["session_id"] == session["id"]
                    and result["subject_id"] not in allowed
                ):
                    raise ValueError("Resultado por matéria fora do desafio.")
    expected = {}
    for row in sources.values():
        if row["session_id"]:
            kind, activity = "session", sessions[row["session_id"]]
            plan, subject, xp = (
                activity["plan_id"],
                activity["subject_id"],
                activity["elapsed"] // 60,
            )
        elif row["review_id"]:
            kind, activity = "review", reviews[row["review_id"]]
            subject = topics[activity["topic_id"]]["subject_id"]
            plan = subjects[subject]["plan_id"]
            xp = 5 if activity["state"] == "Concluída" else 0
        else:
            kind, activity = "challenge", challenges[row["challenge_id"]]
            plan, subject = activity["plan_id"], None
            records = [
                sessions[key]
                for key, link in links.items()
                if link["challenge_id"] == activity["id"]
            ]
            total = sum(s["correct"] + s["wrong"] + s["blank"] for s in records)
            xp = 5 if records and total >= activity["questions"] else 0
        if row["id"] != kind + ":" + activity["id"]:
            raise ValueError("Identificador de recompensa inválido.")
        expected[row["id"]] = (plan, subject, xp, xp // 10)
    if {r["source_id"] for r in tables["rpg_rewards"]} != set(expected):
        raise ValueError("Lançamentos de recompensa incompletos.")
    for row in tables["rpg_rewards"]:
        if (
            type(row["xp"]) is not int
            or type(row["coins"]) is not int
            or tuple(row[k] for k in ("plan_id", "subject_id", "xp", "coins"))
            != expected[row["source_id"]]
        ):
            raise ValueError("Recompensa não corresponde ao esforço registrado.")
    for row in tables["rpg_inventory"]:
        item = CATALOG.get(row["item_id"])
        if (
            not item
            or row["slot"] != item["slot"]
            or type(row["price"]) is not int
            or row["price"] != item["price"]
            or type(row["equipped"]) not in (int, bool)
            or row["equipped"] not in (0, 1)
        ):
            raise ValueError("Item ou preço decorativo inválido.")
        date.fromisoformat(row["acquired_day"])
    for row in tables["rpg_characters"]:
        if (
            not isinstance(row["name"], str)
            or not row["name"].strip()
            or len(row["name"]) > 60
        ):
            raise ValueError("Nome de personagem inválido.")
    for row in tables["rpg_story"]:
        if type(row["chapter"]) is not int or not 1 <= row["chapter"] <= 4:
            raise ValueError("Capítulo inválido.")
        date.fromisoformat(row["unlocked_day"])
