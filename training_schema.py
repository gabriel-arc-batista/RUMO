"""Additive schema v6: local reading state of the Campo de Treinamento.

Only personal data lives here (position, bookmarks, notes, favorites, links
between canonical study sessions and lessons, metadata of imported files).
The public catalog and downloaded PDFs are files, never rows. Lesson and
version identifiers are the stable catalog IDs, so a renamed lesson or a new
PDF edition keeps its notes and progress.
"""

import re

TRAINING_TABLES = [
    "training_lessons",
    "training_positions",
    "training_bookmarks",
    "training_notes",
    "training_session_links",
    "training_personal",
]

TRAINING_SCHEMA = """
CREATE TABLE IF NOT EXISTS training_lessons(lesson_id TEXT PRIMARY KEY,favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1)),last_version TEXT,last_opened TEXT,completed_version TEXT,completed_day TEXT);
CREATE TABLE IF NOT EXISTS training_positions(lesson_id TEXT NOT NULL,version TEXT NOT NULL,page INTEGER NOT NULL CHECK(page>=1),pages INTEGER CHECK(pages IS NULL OR pages>=1),updated TEXT NOT NULL,PRIMARY KEY(lesson_id,version));
CREATE TABLE IF NOT EXISTS training_bookmarks(id TEXT PRIMARY KEY,lesson_id TEXT NOT NULL,version TEXT NOT NULL,page INTEGER NOT NULL CHECK(page>=1),label TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,UNIQUE(lesson_id,version,page));
CREATE TABLE IF NOT EXISTS training_notes(id TEXT PRIMARY KEY,lesson_id TEXT NOT NULL,version TEXT NOT NULL,page INTEGER CHECK(page IS NULL OR page>=1),text TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS training_session_links(session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,lesson_id TEXT NOT NULL,version TEXT);
CREATE TABLE IF NOT EXISTS training_personal(id TEXT PRIMARY KEY,title TEXT NOT NULL,subject TEXT NOT NULL DEFAULT '',topic TEXT NOT NULL DEFAULT '',sha256 TEXT NOT NULL,bytes INTEGER NOT NULL CHECK(bytes>0),filename TEXT NOT NULL,imported TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS training_notes_lesson ON training_notes(lesson_id,version);
CREATE INDEX IF NOT EXISTS training_links_lesson ON training_session_links(lesson_id);
PRAGMA user_version=6;
"""

# Catalog IDs are short, printable and path-safe (they also name cache folders).
ID = re.compile(r"[a-z0-9][a-z0-9._:-]{0,159}")
VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,39}")
SHA256 = re.compile(r"[0-9a-f]{64}")
MAX_TEXT = 20000


def valid_id(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))


def valid_version(value):
    return isinstance(value, str) and bool(VERSION.fullmatch(value))


def validate_training(tables):
    """Reject malformed training rows in a backup before anything is replaced."""
    sessions = {row["id"] for row in tables["sessions"]}

    def check(condition, message):
        if not condition:
            raise ValueError("Campo de Treinamento inválido no backup: " + message)

    for row in tables["training_lessons"]:
        check(valid_id(row["lesson_id"]), "aula")
        check(row["favorite"] in (0, 1), "favorito")
        for key in ("last_version", "completed_version"):
            check(row[key] is None or valid_version(row[key]), "versão")
    for table in ("training_positions", "training_bookmarks"):
        for row in tables[table]:
            check(valid_id(row["lesson_id"]) and valid_version(row["version"]), table)
            check(isinstance(row["page"], int) and 1 <= row["page"] <= 100000, "página")
    for row in tables["training_bookmarks"]:
        check(isinstance(row["label"], str) and len(row["label"]) <= 200, "marcador")
    for row in tables["training_notes"]:
        check(valid_id(row["lesson_id"]) and valid_version(row["version"]), "nota")
        check(
            row["page"] is None or (isinstance(row["page"], int) and row["page"] >= 1),
            "página da nota",
        )
        check(
            isinstance(row["text"], str) and 0 < len(row["text"]) <= MAX_TEXT,
            "texto da nota",
        )
    for row in tables["training_session_links"]:
        check(row["session_id"] in sessions, "sessão vinculada inexistente")
        check(valid_id(row["lesson_id"]), "aula vinculada")
        check(
            row["version"] is None or valid_version(row["version"]), "versão vinculada"
        )
    for row in tables["training_personal"]:
        check(valid_id(row["id"]), "material pessoal")
        check(
            isinstance(row["sha256"], str) and bool(SHA256.fullmatch(row["sha256"])),
            "hash",
        )
        check(isinstance(row["bytes"], int) and row["bytes"] > 0, "tamanho")
        check(
            isinstance(row["filename"], str)
            and re.fullmatch(r"[0-9a-f]{64}\.pdf", row["filename"]),
            "arquivo",
        )
        for key in ("title", "subject", "topic"):
            check(isinstance(row[key], str) and len(row[key]) <= 300, key)
