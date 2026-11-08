"""Additive schema v7: local question bank and answer attempts of the Arena.

Questions belong to a local subject/topic, so every Arena round is an ordinary
"Questões" session. Attempts are written inside the session transaction and
cascade with it; the session keeps being the only source of counts and XP.
"""

import json

ARENA_TABLES = ["arena_questions", "arena_attempts"]

KINDS = ("certo-errado", "multipla-escolha")
STATUSES = ("ativa", "anulada", "retirada")
ORIGINS = ("pessoal", "pacote")
MAX_TEXT = 20000

ARENA_SCHEMA = """
CREATE TABLE IF NOT EXISTS arena_questions(id TEXT PRIMARY KEY,subject_id TEXT NOT NULL REFERENCES subjects(id),topic_id TEXT NOT NULL REFERENCES topics(id),kind TEXT NOT NULL CHECK(kind IN ('certo-errado','multipla-escolha')),statement TEXT NOT NULL,options TEXT NOT NULL DEFAULT '[]',answer TEXT NOT NULL,comment TEXT NOT NULL DEFAULT '',origin TEXT NOT NULL CHECK(origin IN ('pessoal','pacote')),source TEXT NOT NULL DEFAULT '',external_id TEXT,version TEXT NOT NULL DEFAULT '1',status TEXT NOT NULL DEFAULT 'ativa' CHECK(status IN ('ativa','anulada','retirada')),fingerprint TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL,UNIQUE(external_id,version));
CREATE TABLE IF NOT EXISTS arena_attempts(id TEXT PRIMARY KEY,question_id TEXT NOT NULL REFERENCES arena_questions(id),question_version TEXT NOT NULL,answer TEXT NOT NULL,correct INTEGER CHECK(correct IS NULL OR correct IN (0,1)),answered_at TEXT NOT NULL,session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS arena_questions_topic ON arena_questions(topic_id,status);
CREATE INDEX IF NOT EXISTS arena_attempts_question ON arena_attempts(question_id,answered_at);
CREATE INDEX IF NOT EXISTS arena_attempts_session ON arena_attempts(session_id);
PRAGMA user_version=7;
"""


def insert_attempts(db, session_id, attempts):
    """Record a round's attempts inside the caller's transaction; idempotent.

    Each attempt is {question_id, question_version, answer, correct, answered_at};
    `correct` is None for an annulled question. The id is derived from the
    session, so saving the same round twice never duplicates attempts.
    """
    for a in attempts:
        if a["correct"] not in (True, False, None) or not a["answer"]:
            raise ValueError("Tentativa da Arena inválida.")
        db.execute(
            "INSERT OR IGNORE INTO arena_attempts VALUES(?,?,?,?,?,?,?)",
            (
                f"{session_id}:{a['question_id']}",
                a["question_id"],
                a["question_version"],
                a["answer"],
                None if a["correct"] is None else int(a["correct"]),
                a["answered_at"],
                session_id,
            ),
        )


def validate_arena(tables):
    """Reject malformed Arena rows in a backup before anything is replaced."""

    def check(condition, message):
        if not condition:
            raise ValueError("Arena inválida no backup: " + message)

    for row in tables["arena_questions"]:
        check(
            all(
                isinstance(row[k], str) and len(row[k]) <= MAX_TEXT
                for k in ("statement", "answer", "comment", "source")
            ),
            "texto",
        )
        check(row["statement"].strip() != "" and row["answer"] != "", "enunciado")
        options = json.loads(row["options"])
        check(isinstance(options, list) and len(options) <= 10, "alternativas")
    for row in tables["arena_attempts"]:
        check(row["correct"] in (None, 0, 1), "resultado")
        check(
            isinstance(row["answer"], str) and 0 < len(row["answer"]) <= 40, "resposta"
        )
