"""Small, shared security policies without GUI or database dependencies."""

import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from appearance import PREFERENCE as LOOK_PREFERENCE, validate_look
from theme import THEME_NAMES

MAX_TOPIC_DEPTH = 128


def csv_cell(value):
    """Keep user text literal when a CSV is opened in a spreadsheet."""
    if isinstance(value, str) and (
        value.lstrip().startswith(("=", "+", "-", "@"))
        or value.startswith(("\t", "\r", "\n"))
    ):
        return "'" + value
    return value


def web_url(value: str) -> str:
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        raise ValueError("Link inválido.")
    parsed = urlsplit(value)
    if (
        parsed.scheme.lower() not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Use um endereço http:// ou https:// sem credenciais.")
    return value


def directory_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_dir():
        raise ValueError("Escolha uma pasta existente.")
    return path.resolve()


def validate_preferences(rows: list[dict]) -> None:
    choices = {
        "theme": ("Escuro", "Claro", "Sistema", *THEME_NAMES),
        "daily_subjects": (2, 3),
        "review_view": ("Todas", "Hoje", "Próximas", "Atrasadas", "Concluídas"),
        "mock_chart": ("Desempenho", "Pontuação"),
        "syllabus_order": ("Aprendizagem", "Edital"),
        "time_format": ("24h", "12h"),
        "training_view": (
            "disponiveis",
            "baixadas",
            "andamento",
            "favoritas",
            "planejadas",
        ),
        "reader_panel": ("indice", "marcadores"),
    }
    ranges = {
        "retention": (1, 100),
        "block_minutes": (1, 600),
        "focus_minutes": (1, 180),
        "week_start": (0, 6),
        "streak_min_minutes": (0, 1440),
    }
    boolean = {
        "animations",
        "motivation",
        "notifications",
        "achievements",
        "night_achievement",
        "show_main_goal",
        "sound",
        "sidebar_visible",
        "create_guided_cycle",
        "rpg_show_character",
        "rpg_effects",
        "rpg_story",
        "rpg_reward_notifications",
        "reader_side",
        "reader_notes",
    }
    for row in rows:
        key, value = row["key"], json.loads(row["value"])
        if key in choices and value not in choices[key]:
            raise ValueError("Preferência inválida no backup.")
        if key in ranges and (
            type(value) is not int or not ranges[key][0] <= value <= ranges[key][1]
        ):
            raise ValueError("Limite de preferência inválido no backup.")
        if key in boolean and type(value) is not bool:
            raise ValueError("Preferência booleana inválida no backup.")
        if key in ("eligible_days", "review_intervals"):
            if (
                not isinstance(value, list)
                or len(value) > 32
                or any(type(x) is not int for x in value)
            ):
                raise ValueError("Lista de preferências inválida no backup.")
            lower, upper = (0, 6) if key == "eligible_days" else (1, 3650)
            if any(not lower <= x <= upper for x in value):
                raise ValueError("Intervalo de preferência inválido no backup.")
        if key.startswith("main_goal_") and (
            not isinstance(value, dict)
            or any(not isinstance(value.get(k), str) for k in ("name", "target"))
        ):
            raise ValueError("Meta principal inválida no backup.")
        if key.startswith("challenge_level_") and value not in (
            "Iniciante",
            "Intermediário",
            "Avançado",
        ):
            raise ValueError("Nível de desafio inválido no backup.")
        if key == LOOK_PREFERENCE and not validate_look(value):
            raise ValueError("Aparência do personagem inválida no backup.")
        if key.startswith("learning_graph_"):
            from pedagogy import validate_graph

            validate_graph(value)
        if key == "training_source":
            validate_training_source(value)
        if key == "training_exam" and (not isinstance(value, str) or len(value) > 160):
            raise ValueError("Edital-alvo inválido no backup.")
        if key == "timezone" and value != "Sistema":
            from zoneinfo import ZoneInfo

            ZoneInfo(value)


def validate_training_source(value) -> None:
    """Content source preference: no credentials, HTTPS only for remote."""
    if not isinstance(value, dict) or value.get("mode") not in (
        "none",
        "local",
        "remote",
    ):
        raise ValueError("Fonte de conteúdo inválida no backup.")
    hosts = value.get("allowed_hosts", [])
    if (
        not isinstance(hosts, list)
        or len(hosts) > 20
        or any(
            not isinstance(h, str)
            or not h
            or len(h) > 253
            or any(c in h for c in "/@:")
            for h in hosts
        )
    ):
        raise ValueError("Hosts da fonte de conteúdo inválidos no backup.")
    if value["mode"] == "remote":
        url = web_url(value.get("url", ""))
        if urlsplit(url).scheme != "https":
            raise ValueError("A fonte remota precisa usar HTTPS.")
    if not isinstance(value.get("path", ""), str) or len(value.get("path", "")) > 4096:
        raise ValueError("Pasta da fonte de conteúdo inválida no backup.")


def validate_relationships(tables: dict[str, list[dict]]) -> None:
    subjects = {r["id"]: r for r in tables["subjects"]}
    topics = {r["id"]: r for r in tables["topics"]}
    cycles = {r["id"]: r for r in tables["cycles"]}
    for topic in topics.values():
        seen = {topic["id"]}
        parent = topic["parent_id"]
        while parent:
            if (
                parent in seen
                or len(seen) >= MAX_TOPIC_DEPTH
                or topics[parent]["subject_id"] != topic["subject_id"]
            ):
                raise ValueError("Hierarquia de assuntos inválida ou profunda demais.")
            seen.add(parent)
            parent = topics[parent]["parent_id"]
    for block in tables["blocks"]:
        if (
            subjects[block["subject_id"]]["plan_id"]
            != cycles[block["cycle_id"]]["plan_id"]
        ):
            raise ValueError("Matéria do bloco fora do plano do ciclo.")
        if (
            block["topic_id"]
            and topics[block["topic_id"]]["subject_id"] != block["subject_id"]
        ):
            raise ValueError("Assunto do bloco fora da matéria.")
    for table in ("goals", "tasks"):
        for row in tables[table]:
            if (
                row["subject_id"]
                and subjects[row["subject_id"]]["plan_id"] != row["plan_id"]
            ):
                raise ValueError("Matéria fora do plano no backup.")
    for subject in subjects.values():
        if any(
            not isinstance(subject[k], (int, float))
            or not math.isfinite(subject[k])
            or subject[k] <= 0
            for k in ("weight", "difficulty")
        ):
            raise ValueError("Peso ou dificuldade inválida no backup.")
