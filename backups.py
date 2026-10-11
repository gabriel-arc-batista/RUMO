"""Validate untrusted backups in isolation before restoring local data."""

import json
import math
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from security import validate_preferences, validate_relationships


def validate_backup(path, schema, tables):
    data = read_backup(Path(path), tables)
    if (
        not isinstance(data.get("format"), str)
        or not 1 <= len(data["format"]) <= 64
        or data.get("version") not in [1, 2, 3]
        or set(data.get("tables", {})) != set(tables)
    ):
        raise ValueError("Formato ou versão de backup inválidos.")
    if data["version"] == 1:
        for row in data["tables"]["sessions"]:
            row.setdefault("pauses", "[]")
        data["version"] = 2
    if data["version"] == 2:
        for row in data["tables"]["topics"]:
            row.setdefault("notes", "")
        data["version"] = 3
    test = sqlite3.connect(":memory:")
    test.execute("PRAGMA foreign_keys=ON")
    test.executescript(schema)
    test.execute("BEGIN")
    test.execute("PRAGMA defer_foreign_keys=ON")
    try:
        for table in tables:
            columns = [r[1] for r in test.execute(f"PRAGMA table_info({table})")]
            for row in data["tables"][table]:
                if set(row) != set(columns):
                    raise ValueError("Campos de backup inválidos.")
                for flag in ("done", "archived", "active"):
                    if flag in row and (
                        type(row[flag]) not in (int, bool) or row[flag] not in (0, 1)
                    ):
                        raise ValueError("Indicador de estado inválido no backup.")
                test.execute(
                    f"INSERT INTO {table} ({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                    [row[c] for c in columns],
                )
        if test.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Relações inválidas.")
        subjects = {row["id"]: row for row in data["tables"]["subjects"]}
        topics = {row["id"]: row for row in data["tables"]["topics"]}
        for row in data["tables"]["sessions"]:
            _validate_backup_session(row, subjects, topics)
        validate_preferences(data["tables"]["preferences"])
        validate_relationships(data["tables"])
        for row in data["tables"]["active"]:
            active = json.loads(row["value"])
            if not isinstance(active, dict) or not {
                "id",
                "plan_id",
                "subject_id",
                "topic_id",
                "category",
                "target",
                "elapsed",
                "mode",
                "running",
                "segments",
            } <= set(active):
                raise ValueError("Rascunho inválido no backup.")
            if (
                type(active.get("running")) is not bool
                or type(active.get("target")) is not int
                or active["target"] < 0
                or not isinstance(active.get("segments"), list)
            ):
                raise ValueError("Rascunho inválido no backup.")
            if (
                active["mode"] not in ["Timer", "Cronômetro"]
                or not isinstance(active["elapsed"], (int, float))
                or not math.isfinite(active["elapsed"])
                or active["elapsed"] < 0
                or active["target"] < 0
            ):
                raise ValueError("Tempo de rascunho inválido.")
            if not any(p["id"] == active["plan_id"] for p in data["tables"]["plans"]):
                raise ValueError("Plano do rascunho inexistente.")
            subject = next(
                (
                    s
                    for s in data["tables"]["subjects"]
                    if s["id"] == active["subject_id"]
                ),
                None,
            )
            topic = next(
                (t for t in data["tables"]["topics"] if t["id"] == active["topic_id"]),
                None,
            )
            if (
                not subject
                or not topic
                or subject["plan_id"] != active["plan_id"]
                or topic["subject_id"] != subject["id"]
            ):
                raise ValueError("Vínculos do rascunho inválidos.")
        for row in data["tables"]["reviews"]:
            date.fromisoformat(row["due"])
        for row in data["tables"]["tasks"]:
            if row["due"]:
                date.fromisoformat(row["due"])
        for row in data["tables"]["plans"]:
            if row["exam_date"]:
                date.fromisoformat(row["exam_date"])
        counts = Counter(
            b["cycle_id"] for b in data["tables"]["blocks"] if not b["archived"]
        )
        for cycle in data["tables"]["cycles"]:
            count = counts[cycle["id"]]
            if not 0 <= cycle["position"] <= count or cycle["lap"] < 1:
                raise ValueError("Posição ou volta inválida no ciclo.")
        totals = defaultdict(Counter)
        for result in data["tables"]["mock_results"]:
            totals[result["session_id"]].update(
                {k: result[k] for k in ("correct", "wrong", "blank")}
            )
        for session in data["tables"]["sessions"]:
            if session["id"] in totals and any(
                totals[session["id"]][k] != session[k]
                for k in ("correct", "wrong", "blank")
            ):
                raise ValueError("Totais de simulado inconsistentes no backup.")
    finally:
        test.close()
    return data


def _validate_backup_session(row, subjects, topics):
    date.fromisoformat(row["day"])
    if row["start_time"]:
        datetime.strptime(row["start_time"], "%H:%M")
    for key in ("target", "elapsed", "correct", "wrong", "blank", "pages", "video"):
        if row[key] is not None and (type(row[key]) is not int or row[key] < 0):
            raise ValueError("Valor numérico inválido no backup.")
    for key in ("score_correct", "score_wrong", "score_blank"):
        if not isinstance(row[key], (int, float)) or not math.isfinite(row[key]):
            raise ValueError("Pontuação inválida no backup.")
    if row["category"] not in ["Teoria", "Questões", "Revisão", "Simulado"]:
        raise ValueError("Categoria inválida no backup.")
    if row["subject_id"] and subjects[row["subject_id"]]["plan_id"] != row["plan_id"]:
        raise ValueError("Plano inconsistente no backup.")
    if row["topic_id"] and topics[row["topic_id"]]["subject_id"] != row["subject_id"]:
        raise ValueError("Assunto inconsistente no backup.")
    if row["category"] != "Simulado" and (not row["subject_id"] or not row["topic_id"]):
        raise ValueError("Matéria ou assunto ausente no backup.")
    segments = json.loads(row["segments"])
    if not isinstance(segments, list):
        raise ValueError("Segmentos inválidos no backup.")
    for segment in segments:
        date.fromisoformat(segment["day"])
        if (
            not isinstance(segment.get("seconds"), (int, float))
            or not math.isfinite(segment["seconds"])
            or segment["seconds"] < 0
        ):
            raise ValueError("Tempo inválido no backup.")
    if not isinstance(json.loads(row["pauses"]), list):
        raise ValueError("Pausas inválidas no backup.")


def read_backup(path, tables):
    """Read only ordinary SQLite tables; bound external input and query time."""
    sqlite_file = path.suffix.lower() in (".sqlite3", ".db")
    maximum = (100 if sqlite_file else 20) * 1024 * 1024
    if path.stat().st_size > maximum:
        raise ValueError(
            "Backup acima do limite: 20 MB para JSON ou 100 MB para SQLite."
        )
    if sqlite_file:
        reader = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        reader.row_factory = sqlite3.Row
        deadline = time.monotonic() + 5
        reader.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        try:
            reader.execute("PRAGMA trusted_schema=OFF")
            reader.execute("PRAGMA query_only=ON")
            objects = {
                r["name"]: r["type"]
                for r in reader.execute("SELECT name,type FROM sqlite_master")
            }
            if any(objects.get(t) != "table" for t in tables) or any(
                v in ("view", "trigger") for v in objects.values()
            ):
                raise ValueError(
                    "Backup SQLite com objetos executáveis ou tabelas inválidas."
                )
            if reader.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Backup SQLite corrompido.")
            data = {
                "format": "RUMO",
                "version": reader.execute("PRAGMA user_version").fetchone()[0],
                "tables": {
                    t: [
                        dict(r)
                        for r in reader.execute(f"SELECT * FROM {t} LIMIT 100001")
                    ]
                    for t in tables
                },
            }
        finally:
            reader.close()
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("tables"), dict):
        raise ValueError("Estrutura de backup inválida.")
    rows = data["tables"].values()
    if (
        any(not isinstance(group, list) for group in rows)
        or sum(len(group) for group in rows) > 100000
    ):
        raise ValueError("Backup inválido ou acima de 100 mil registros.")
    text_size = 0
    for group in rows:
        for row in group:
            if not isinstance(row, dict) or any(not isinstance(k, str) for k in row):
                raise ValueError("Registro de backup inválido.")
            for value in row.values():
                if value is not None and type(value) not in (str, int, float, bool):
                    raise ValueError("Tipo de campo inválido no backup.")
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("Número não finito no backup.")
                if isinstance(value, str):
                    text_size += len(value)
                    if len(value) > 1024 * 1024 or text_size > 20 * 1024 * 1024:
                        raise ValueError("Conteúdo textual do backup acima do limite.")
    return data
