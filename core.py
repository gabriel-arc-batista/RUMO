"""Local domain and persistence. Runtime uses only the Python standard library."""

import csv
import io
import json
import math
import os
import re
import sqlite3
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from security import csv_cell
from rpg_schema import RPG_SCHEMA, RPG_TABLES

COLORS = ["#D6B467", "#B6914A", "#E8CC91", "#A78956", "#F1DEAD", "#786541"]
TABLES = [
    "preferences",
    "plans",
    "subjects",
    "topics",
    "materials",
    "cycles",
    "blocks",
    "decisions",
    "sessions",
    "reviews",
    "tasks",
    "goals",
    "mock_results",
    "active",
] + RPG_TABLES
SCHEMA = """
CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT DEFAULT '',exam_date TEXT,archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),name TEXT NOT NULL,color TEXT NOT NULL,weight REAL DEFAULT 1 CHECK(weight>0),difficulty REAL DEFAULT 1 CHECK(difficulty>0),archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS topics(id TEXT PRIMARY KEY,subject_id TEXT NOT NULL REFERENCES subjects(id),parent_id TEXT REFERENCES topics(id),name TEXT NOT NULL,done INTEGER DEFAULT 0,archived INTEGER DEFAULT 0,notes TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS materials(id TEXT PRIMARY KEY,topic_id TEXT NOT NULL REFERENCES topics(id),name TEXT NOT NULL,url TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS cycles(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),name TEXT NOT NULL,position INTEGER DEFAULT 0,lap INTEGER DEFAULT 1,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS blocks(id TEXT PRIMARY KEY,cycle_id TEXT NOT NULL REFERENCES cycles(id),subject_id TEXT NOT NULL REFERENCES subjects(id),topic_id TEXT REFERENCES topics(id),target INTEGER NOT NULL CHECK(target>0),category TEXT DEFAULT 'Teoria',sort INTEGER NOT NULL,archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,block_id TEXT NOT NULL REFERENCES blocks(id),lap INTEGER NOT NULL,state TEXT NOT NULL,reason TEXT DEFAULT '',UNIQUE(block_id,lap));
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),subject_id TEXT REFERENCES subjects(id),topic_id TEXT REFERENCES topics(id),day TEXT NOT NULL,start_time TEXT DEFAULT '',category TEXT NOT NULL,target INTEGER NOT NULL CHECK(target>=0),elapsed INTEGER NOT NULL CHECK(elapsed>=0),correct INTEGER DEFAULT 0 CHECK(correct>=0),wrong INTEGER DEFAULT 0 CHECK(wrong>=0),blank INTEGER DEFAULT 0 CHECK(blank>=0),pages INTEGER,video INTEGER,material TEXT DEFAULT '',url TEXT DEFAULT '',next_step TEXT DEFAULT '',notes TEXT DEFAULT '',block_id TEXT REFERENCES blocks(id),lap INTEGER,review_id TEXT,mock_name TEXT,mock_format TEXT,score_correct REAL DEFAULT 1,score_wrong REAL DEFAULT 0,score_blank REAL DEFAULT 0,segments TEXT DEFAULT '[]');
CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,topic_id TEXT NOT NULL REFERENCES topics(id),origin_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,due TEXT NOT NULL,interval INTEGER NOT NULL,state TEXT DEFAULT 'Pendente',completed_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,UNIQUE(topic_id,due,interval));
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),subject_id TEXT REFERENCES subjects(id),name TEXT NOT NULL,due TEXT,state TEXT DEFAULT 'Pendente');
CREATE TABLE IF NOT EXISTS goals(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),subject_id TEXT REFERENCES subjects(id),hours REAL NOT NULL CHECK(hours>=0),questions INTEGER NOT NULL CHECK(questions>=0));
CREATE TABLE IF NOT EXISTS mock_results(id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,subject_id TEXT NOT NULL REFERENCES subjects(id),correct INTEGER NOT NULL CHECK(correct>=0),wrong INTEGER NOT NULL CHECK(wrong>=0),blank INTEGER NOT NULL CHECK(blank>=0),weight REAL DEFAULT 1 CHECK(weight>0),UNIQUE(session_id,subject_id));
CREATE TABLE IF NOT EXISTS active(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_sessions_plan_day ON sessions(plan_id,day);
CREATE INDEX IF NOT EXISTS ix_sessions_topic ON sessions(topic_id);
CREATE INDEX IF NOT EXISTS ix_sessions_block ON sessions(block_id,lap);
CREATE INDEX IF NOT EXISTS ix_topics_subject ON topics(subject_id);
CREATE INDEX IF NOT EXISTS ix_reviews_due ON reviews(due,state);
ALTER TABLE sessions ADD COLUMN pauses TEXT NOT NULL DEFAULT '[]';
PRAGMA user_version=3;
""" + RPG_SCHEMA


def uid():
    return uuid.uuid4().hex


def data_dir():
    override = os.environ.get("RUMO_DATA")
    if override:
        return Path(override)
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share"))
    target = base / "RUMO"
    from storage import migrate_existing_data

    migrate_existing_data(base, target, SCHEMA, TABLES)
    return target


def duration(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}"


def parse_duration(value):
    parts = str(value).strip().split(":")
    if len(parts) != 3 or any(not x.isdigit() for x in parts):
        raise ValueError("Use horas:minutos:segundos, por exemplo 00:45:00.")
    h, m, s = map(int, parts)
    if m > 59 or s > 59 or h > 1000:
        raise ValueError("Minutos e segundos devem estar entre 0 e 59.")
    return h * 3600 + m * 60 + s


def ratio(correct, wrong, blank=0, presented=False):
    total = correct + wrong + (blank if presented else 0)
    return correct / total * 100 if total else None


def percentage(value):
    return "Sem questões" if value is None else f"{value:.1f}%"


class Store:
    def __init__(self, path=None):
        self.path = Path(path or data_dir() / "estudos.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 5:
            self.db.close()
            raise ValueError(
                "A base foi criada por uma versão mais nova do RUMO — Estudos. Atualize o aplicativo."
            )
        self.db.execute("PRAGMA trusted_schema=OFF")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA cache_size=-2048")
        if version == 0:
            self.db.executescript(SCHEMA)
        elif version == 1:
            with self.db:
                self.db.execute(
                    "ALTER TABLE sessions ADD COLUMN pauses TEXT NOT NULL DEFAULT '[]'"
                )
                self.db.execute("PRAGMA user_version=2")
        if version in (1, 2):
            with self.db:
                if "notes" not in {
                    r[1] for r in self.db.execute("PRAGMA table_info(topics)")
                }:
                    self.db.execute(
                        "ALTER TABLE topics ADD COLUMN notes TEXT NOT NULL DEFAULT ''"
                    )
                self.db.execute("PRAGMA user_version=3")

        if version in (1, 2, 3):
            # A consistent pre-upgrade copy is retained outside the source tree.
            backup = self.path.parent / (
                "pre-rpg-" + datetime.now().strftime("%Y%m%d-%H%M%S%f") + ".sqlite3"
            )
            destination = sqlite3.connect(backup)
            try:
                self.db.backup(destination)
            finally:
                destination.close()
            try:
                self.db.executescript("BEGIN IMMEDIATE;" + RPG_SCHEMA + "COMMIT;")
            except Exception:
                self.db.rollback()
                raise
        if version == 4:
            from rpg_schema import INVENTORY_V5_MIGRATION

            backup = self.path.parent / (
                "pre-equipment-"
                + datetime.now().strftime("%Y%m%d-%H%M%S%f")
                + ".sqlite3"
            )
            destination = sqlite3.connect(backup)
            try:
                self.db.backup(destination)
            finally:
                destination.close()
            try:
                self.db.executescript(
                    "BEGIN IMMEDIATE;" + INVENTORY_V5_MIGRATION + "COMMIT;"
                )
            except Exception:
                self.db.rollback()
                self.db.close()
                raise
        from rpg import RPGService

        self.rpg = RPGService(self)
        self.rpg.sync()

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def one(self, sql, args=()):
        r = self.db.execute(sql, args).fetchone()
        return dict(r) if r else None

    def pref(self, key, default=None):
        r = self.one("SELECT value FROM preferences WHERE key=?", (key,))
        return json.loads(r["value"]) if r else default

    def set_pref(self, key, value):
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO preferences VALUES(?,?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def local_now(self):
        zone = self.pref("timezone", "Sistema")
        if zone == "Sistema":
            return datetime.now().astimezone()
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(zone))

    def today(self):
        return self.local_now().date()

    def put(self, table, values):
        if table not in TABLES:
            raise ValueError("Tabela inválida.")
        columns = {r[1] for r in self.db.execute(f"PRAGMA table_info({table})")}
        if not values or not set(values) <= columns:
            raise ValueError("Campos inválidos.")
        values = dict(values)
        values.setdefault("id", uid())
        if table == "topics":
            self.validate_topic(values)
        keys = list(values)
        if self.one(f"SELECT id FROM {table} WHERE id=?", (values["id"],)):
            changed = [k for k in keys if k != "id"]
            if changed:
                self.db.execute(
                    f"UPDATE {table} SET {','.join(k+'=?' for k in changed)} WHERE id=?",
                    [values[k] for k in changed] + [values["id"]],
                )
            return values["id"]
        updates = ",".join(f"{k}=excluded.{k}" for k in keys if k != "id")
        sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES({','.join('?' for k in keys)}) ON CONFLICT(id) DO UPDATE SET {updates}"
        self.db.execute(sql, [values[k] for k in keys])
        return values["id"]

    def validate_topic(self, values):
        from security import MAX_TOPIC_DEPTH

        current = self.one("SELECT * FROM topics WHERE id=?", (values["id"],)) or {}
        topic = dict(current, **values)
        subject = topic.get("subject_id")
        parent = topic.get("parent_id")
        seen = {topic["id"]}
        while parent:
            row = self.one(
                "SELECT subject_id,parent_id FROM topics WHERE id=?", (parent,)
            )
            if (
                not row
                or row["subject_id"] != subject
                or parent in seen
                or len(seen) >= MAX_TOPIC_DEPTH
            ):
                raise ValueError(
                    "O pai deve ser da mesma matéria, sem ciclos e com até 128 níveis."
                )
            seen.add(parent)
            parent = row["parent_id"]
        if current and current["subject_id"] != subject:
            if self.one(
                "SELECT id FROM topics WHERE parent_id=? LIMIT 1", (topic["id"],)
            ):
                raise ValueError("Assunto com subassuntos não pode mudar de matéria.")
            if self.one(
                "SELECT id FROM sessions WHERE topic_id=? LIMIT 1", (topic["id"],)
            ):
                raise ValueError("Assunto com histórico não pode mudar de matéria.")

    def save(self, table, values):
        old = (
            self.one("SELECT state FROM reviews WHERE id=?", (values.get("id", ""),))
            if table == "reviews"
            else None
        )
        with self.db:
            key = self.put(table, values)
            if table == "reviews":
                self.rpg.review_changed(key, old["state"] if old else None)
            return key

    def progress(self, plan):
        return self.one(
            """SELECT COUNT(*) total,COALESCE(SUM(t.done),0) done FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND s.archived=0 AND t.archived=0 AND NOT EXISTS(SELECT 1 FROM topics ch WHERE ch.parent_id=t.id AND ch.archived=0)""",
            (plan,),
        )

    def validate_session(self, v):
        v = dict(v)
        date.fromisoformat(v["day"])
        if v.get("start_time"):
            datetime.strptime(v["start_time"], "%H:%M")
        for k in ["target", "elapsed", "correct", "wrong", "blank"]:
            x = v.get(k, 0)
            if isinstance(x, bool) or not isinstance(x, int) or x < 0:
                raise ValueError("Duração e questões devem ser inteiros não negativos.")
            v[k] = x
        for k in ["pages", "video"]:
            if v.get(k) is not None and (not isinstance(v[k], int) or v[k] < 0):
                raise ValueError("Páginas e videoaulas não podem ser negativas.")
        if v["category"] not in ["Teoria", "Questões", "Revisão", "Simulado"]:
            raise ValueError("Categoria inválida.")
        segments = json.loads(v.get("segments", "[]"))
        if not isinstance(segments, list):
            raise ValueError("Segmentos de tempo inválidos.")
        for segment in segments:
            date.fromisoformat(segment["day"])
            if (
                not isinstance(segment.get("seconds"), (int, float))
                or not math.isfinite(segment["seconds"])
                or segment["seconds"] < 0
            ):
                raise ValueError("Segmento de tempo inválido.")
        if (
            v.get("total") is not None
            and v.pop("total") != v["correct"] + v["wrong"] + v["blank"]
        ):
            raise ValueError("Total deve ser igual a acertos + erros + brancos.")
        if v["category"] != "Simulado" and (
            not v.get("subject_id") or not v.get("topic_id")
        ):
            raise ValueError("Escolha uma matéria e um assunto específico.")
        if v.get("subject_id"):
            s = self.one("SELECT * FROM subjects WHERE id=?", (v["subject_id"],))
            if not s or s["plan_id"] != v["plan_id"]:
                raise ValueError("A matéria não pertence ao plano.")
        if v.get("topic_id"):
            t = self.one("SELECT * FROM topics WHERE id=?", (v["topic_id"],))
            if not t or t["subject_id"] != v["subject_id"]:
                raise ValueError("O assunto não pertence à matéria.")
        if v.get("block_id"):
            b = self.one(
                "SELECT b.*,c.plan_id FROM blocks b JOIN cycles c ON c.id=b.cycle_id WHERE b.id=?",
                (v["block_id"],),
            )
            if (
                not b
                or b["plan_id"] != v["plan_id"]
                or b["subject_id"] != v["subject_id"]
                or (b["topic_id"] and b["topic_id"] != v["topic_id"])
            ):
                raise ValueError("A sessão não é compatível com o bloco do ciclo.")
        if v.get("review_id"):
            r = self.one("SELECT topic_id FROM reviews WHERE id=?", (v["review_id"],))
            if not r or r["topic_id"] != v.get("topic_id"):
                raise ValueError("A revisão não pertence a este assunto.")
        return v

    def save_session(
        self,
        values,
        intervals=(),
        theory_done=False,
        results=(),
        finish_active=False,
        base=None,
        shift_pending=True,
        context=None,
    ):
        v = self.validate_session(values)
        base = date.fromisoformat(base or v["day"])
        intervals = sorted(set(int(x) for x in intervals))
        if any(x <= 0 or x > 36500 for x in intervals):
            raise ValueError("Intervalos de revisão devem ser positivos.")
        results = list(results)
        if results:
            for r in results:
                if (
                    any(
                        not isinstance(r[k], int) or r[k] < 0
                        for k in ["correct", "wrong", "blank"]
                    )
                    or not math.isfinite(r.get("weight", 1))
                    or r.get("weight", 1) <= 0
                ):
                    raise ValueError("Resultado por matéria inválido.")
                s = self.one(
                    "SELECT plan_id FROM subjects WHERE id=?", (r["subject_id"],)
                )
                if not s or s["plan_id"] != v["plan_id"]:
                    raise ValueError("Matéria do simulado fora do plano.")
            if len({r["subject_id"] for r in results}) != len(results) or any(
                sum(r[k] for r in results) != v[k]
                for k in ["correct", "wrong", "blank"]
            ):
                raise ValueError(
                    "A divisão por matéria deve somar os resultados gerais, sem repetir matérias."
                )
        for k in ["score_correct", "score_wrong", "score_blank"]:
            if k in v and not math.isfinite(v[k]):
                raise ValueError("Pontuação inválida.")
        old = self.one("SELECT * FROM sessions WHERE id=?", (v.get("id", ""),))
        with self.db:
            sid = self.put("sessions", v)
            if shift_pending and old and old["day"] != v["day"]:
                delta = (
                    date.fromisoformat(v["day"]) - date.fromisoformat(old["day"])
                ).days
                for r in self.rows(
                    "SELECT * FROM reviews WHERE origin_id=? AND state='Pendente'",
                    (sid,),
                ):
                    due = (
                        date.fromisoformat(r["due"]) + timedelta(days=delta)
                    ).isoformat()
                    self.db.execute(
                        "UPDATE reviews SET due=? WHERE id=?", (due, r["id"])
                    )
            if theory_done and v.get("topic_id"):
                self.db.execute("UPDATE topics SET done=1 WHERE id=?", (v["topic_id"],))
            for days in intervals:
                if v.get("topic_id"):
                    self.db.execute(
                        "INSERT OR IGNORE INTO reviews(id,topic_id,origin_id,due,interval) VALUES(?,?,?,?,?)",
                        (
                            uid(),
                            v["topic_id"],
                            sid,
                            (base + timedelta(days=days)).isoformat(),
                            days,
                        ),
                    )
            if v.get("review_id"):
                self.db.execute(
                    "UPDATE reviews SET state='Concluída',completed_id=? WHERE id=?",
                    (sid, v["review_id"]),
                )
            self.db.execute("DELETE FROM mock_results WHERE session_id=?", (sid,))
            for r in results:
                self.put("mock_results", dict(r, session_id=sid))
            if old and old["review_id"] and old["review_id"] != v.get("review_id"):
                self.db.execute(
                    "UPDATE reviews SET state='Pendente',completed_id=NULL WHERE id=? AND completed_id=?",
                    (old["review_id"], sid),
                )
            if finish_active:
                self.db.execute("DELETE FROM active")
            self.rpg.session_saved(sid, old is None, context)
        return sid

    def delete_session(self, sid):
        with self.db:
            self.db.execute(
                "UPDATE reviews SET state='Pendente',completed_id=NULL WHERE completed_id=?",
                (sid,),
            )
            self.db.execute(
                "DELETE FROM reviews WHERE origin_id=? AND state='Pendente'", (sid,)
            )
            self.db.execute("DELETE FROM sessions WHERE id=?", (sid,))
            self.rpg.sync_in_transaction()

    def filters(self, plan, f=None):
        f = f or {}
        clauses = ["s.plan_id=?"]
        args = [plan]
        for key, col, op in [
            ("from", "day", ">="),
            ("to", "day", "<="),
            ("subject_id", "subject_id", "="),
            ("topic_id", "topic_id", "="),
            ("category", "category", "="),
        ]:
            if f.get(key):
                clauses.append(f"s.{col}{op}?")
                args.append(f[key])
        if f.get("search"):
            clauses.append(
                "(s.material LIKE ? OR s.notes LIKE ? OR COALESCE(t.name,'') LIKE ? OR COALESCE(s.mock_name,'') LIKE ?)"
            )
            args.extend(["%" + f["search"] + "%"] * 4)
        return " AND ".join(clauses), args

    def source(self, f=None):
        """Subject-filtered mock results carry no invented per-subject duration."""
        sid = (f or {}).get("subject_id")
        if not sid:
            return "sessions"
        columns = [r[1] for r in self.db.execute("PRAGMA table_info(sessions)")]
        expressions = []
        for k in columns:
            if k in ["correct", "wrong", "blank", "subject_id"]:
                expr = f"CASE WHEN m.id IS NOT NULL THEN m.{k} ELSE a.{k} END"
            elif k in ["elapsed", "target"]:
                expr = f"CASE WHEN m.id IS NOT NULL THEN 0 ELSE a.{k} END"
            elif k == "segments":
                expr = "CASE WHEN m.id IS NOT NULL THEN '[]' ELSE a.segments END"
            elif k in ["pages", "video"]:
                expr = f"CASE WHEN m.id IS NOT NULL THEN NULL ELSE a.{k} END"
            else:
                expr = "a." + k
            expressions.append(expr + " AS " + k)
        return f"(SELECT {','.join(expressions)} FROM sessions a LEFT JOIN mock_results m ON m.session_id=a.id AND m.subject_id=?)"

    @staticmethod
    def source_args(filters, args):
        subject = (filters or {}).get("subject_id")
        return ([subject] if subject else []) + list(args)

    def sessions(self, plan, f=None, limit=200, offset=0):
        where, args = self.filters(plan, f)
        return self.rows(
            f"""SELECT s.*,d.name subject,t.name topic FROM {self.source(f)} s LEFT JOIN subjects d ON d.id=s.subject_id LEFT JOIN topics t ON t.id=s.topic_id WHERE {where} ORDER BY day DESC,start_time DESC,id DESC LIMIT ? OFFSET ?""",
            self.source_args(f, args) + [limit, offset],
        )

    def stats(self, plan, f=None):
        where, args = self.filters(plan, f)
        r = self.one(
            f"""SELECT COALESCE(SUM(elapsed),0) elapsed,COALESCE(SUM(target),0) target,COALESCE(SUM(correct),0) correct,COALESCE(SUM(wrong),0) wrong,COALESCE(SUM(blank),0) blank,SUM(pages) pages,SUM(video) video,COUNT(DISTINCT CASE WHEN elapsed>0 THEN day END) days,MIN(day) first,MAX(day) last,COUNT(*) count,COALESCE(SUM(CASE WHEN pages IS NOT NULL AND elapsed>0 THEN elapsed END),0) page_time FROM {self.source(f)} s LEFT JOIN topics t ON t.id=s.topic_id WHERE {where}""",
            self.source_args(f, args),
        )
        r["total"] = r["correct"] + r["wrong"] + r["blank"]
        r["rate"] = ratio(r["correct"], r["wrong"])
        r["presented_rate"] = ratio(r["correct"], r["wrong"], r["blank"], True)
        f = f or {}
        begin = f.get("from") or r["first"] or self.today().isoformat()
        end = f.get("to") or self.today().isoformat()
        r["period_days"] = max(
            1, (date.fromisoformat(end) - date.fromisoformat(begin)).days + 1
        )
        r["average"] = r["elapsed"] / r["days"] if r["days"] else 0
        r["pages_hour"] = (
            (r["pages"] or 0) / (r["page_time"] / 3600) if r["page_time"] else None
        )
        # Segments allocate measured time by day, while manual questions keep
        # their assigned session date. Period-filtered time uses this same source.
        daily = self.time_by_day(plan, f)
        r["elapsed"] = int(round(sum(x["elapsed"] for x in daily)))
        r["days"] = sum(x["elapsed"] > 0 for x in daily)
        if not f.get("from") and daily:
            begin = min(begin, daily[0]["label"])
            r["period_days"] = max(
                1, (date.fromisoformat(end) - date.fromisoformat(begin)).days + 1
            )
        r["average"] = r["elapsed"] / r["days"] if r["days"] else 0
        return r

    def time_by_day(self, plan, f=None):
        f = f or {}
        no_date = {k: v for k, v in f.items() if k not in ["from", "to"]}
        where, args = self.filters(plan, no_date)
        conditions = []
        parameters = list(args)
        if f.get("from"):
            conditions.append("label>=?")
            parameters.append(f["from"])
        if f.get("to"):
            conditions.append("label<=?")
            parameters.append(f["to"])
        suffix = " WHERE " + " AND ".join(conditions) if conditions else ""
        return self.rows(
            f"""WITH filtered AS (
          SELECT s.* FROM {self.source(f)} s LEFT JOIN topics t ON t.id=s.topic_id WHERE {where}
        ), pieces AS (
          SELECT day label,elapsed FROM filtered WHERE json_array_length(segments)=0
          UNION ALL
          SELECT json_extract(j.value,'$.day') label,
          CASE WHEN (SELECT SUM(json_extract(v.value,'$.seconds')) FROM json_each(s.segments) v)>0
          THEN json_extract(j.value,'$.seconds')*s.elapsed/(SELECT SUM(json_extract(v.value,'$.seconds')) FROM json_each(s.segments) v)
          ELSE 0 END elapsed
          FROM filtered s,json_each(s.segments) j WHERE json_array_length(s.segments)>0
        ) SELECT label,SUM(elapsed) elapsed FROM pieces {suffix} GROUP BY label ORDER BY label""",
            self.source_args(f, parameters),
        )

    def grouped(self, plan, f=None, group="day"):
        if group == "subject" and not (f or {}).get("subject_id"):
            result = []
            for subject in self.rows(
                "SELECT id,name FROM subjects WHERE plan_id=? ORDER BY name", (plan,)
            ):
                selected = dict(f or {}, subject_id=subject["id"])
                s = self.stats(plan, selected)
                if s["count"]:
                    result.append(
                        {
                            "label": subject["name"],
                            **{
                                k: s[k]
                                for k in [
                                    "elapsed",
                                    "target",
                                    "correct",
                                    "wrong",
                                    "blank",
                                ]
                            },
                        }
                    )
            where, args = self.filters(plan, f)
            other = self.one(
                f"""SELECT COALESCE(SUM(s.elapsed),0) elapsed,COALESCE(SUM(s.target),0) target,COALESCE(SUM(s.correct),0) correct,COALESCE(SUM(s.wrong),0) wrong,COALESCE(SUM(s.blank),0) blank,COUNT(*) count FROM sessions s LEFT JOIN topics t ON t.id=s.topic_id WHERE {where} AND s.subject_id IS NULL""",
                args,
            )
            if other["count"]:
                # General durations are real; split questions are already in the
                # subject rows, so only unassigned questions enter this bucket.
                unassigned = self.one(
                    f"""SELECT COALESCE(SUM(s.correct),0) correct,COALESCE(SUM(s.wrong),0) wrong,COALESCE(SUM(s.blank),0) blank FROM sessions s LEFT JOIN topics t ON t.id=s.topic_id WHERE {where} AND s.subject_id IS NULL AND NOT EXISTS(SELECT 1 FROM mock_results r WHERE r.session_id=s.id)""",
                    args,
                )
                result.append(
                    {
                        "label": "Simulados — tempo geral / questões sem divisão",
                        "elapsed": other["elapsed"],
                        "target": other["target"],
                        **unassigned,
                    }
                )
            return result
        where, args = self.filters(plan, f)
        expression = {
            "day": "s.day",
            "week": "strftime('%Y-%W',s.day)",
            "month": "substr(s.day,1,7)",
            "subject": "COALESCE(d.name,'Simulados — sem matéria')",
            "category": "s.category",
            "topic": "COALESCE(t.name,s.mock_name,'Sem assunto')",
        }[group]
        rows = self.rows(
            f"""SELECT {expression} label,SUM(s.elapsed) elapsed,SUM(s.target) target,SUM(s.correct) correct,SUM(s.wrong) wrong,SUM(s.blank) blank FROM {self.source(f)} s LEFT JOIN subjects d ON d.id=s.subject_id LEFT JOIN topics t ON t.id=s.topic_id WHERE {where} GROUP BY {expression} ORDER BY label""",
            self.source_args(f, args),
        )
        if group in ["day", "week", "month"]:
            times = {}
            for r in self.time_by_day(plan, f):
                key = r["label"]
                if group == "month":
                    key = key[:7]
                if group == "week":
                    key = date.fromisoformat(key).strftime("%Y-%W")
                times[key] = times.get(key, 0) + r["elapsed"]
            mapping = {r["label"]: r for r in rows}
            for key, elapsed in times.items():
                mapping.setdefault(
                    key,
                    {"label": key, "target": 0, "correct": 0, "wrong": 0, "blank": 0},
                )["elapsed"] = elapsed
            for key, r in mapping.items():
                r["elapsed"] = times.get(key, 0)
            rows = [mapping[k] for k in sorted(mapping)]
        return rows

    def subject_stats(self, plan):
        return self.rows(
            """SELECT d.id,d.name,d.color,COALESCE(a.elapsed,0) elapsed,COALESCE(a.correct,0)+COALESCE(m.correct,0) correct,COALESCE(a.wrong,0)+COALESCE(m.wrong,0) wrong,COALESCE(a.blank,0)+COALESCE(m.blank,0) blank FROM subjects d LEFT JOIN (SELECT subject_id,SUM(elapsed) elapsed,SUM(correct) correct,SUM(wrong) wrong,SUM(blank) blank FROM sessions WHERE category!='Simulado' OR NOT EXISTS(SELECT 1 FROM mock_results WHERE session_id=sessions.id) GROUP BY subject_id) a ON a.subject_id=d.id LEFT JOIN (SELECT r.subject_id,SUM(r.correct) correct,SUM(r.wrong) wrong,SUM(r.blank) blank FROM mock_results r JOIN sessions s ON s.id=r.session_id WHERE s.plan_id=? GROUP BY r.subject_id) m ON m.subject_id=d.id WHERE d.plan_id=? ORDER BY d.name""",
            (plan, plan),
        )

    def streak(self, plan):
        threshold = max(1, int(self.pref("streak_min_minutes", 0) * 60))
        days = [
            date.fromisoformat(r["label"])
            for r in self.time_by_day(plan)
            if r["elapsed"] >= threshold
        ]
        best = run = 0
        previous = None
        for d in days:
            run = run + 1 if previous and (d - previous).days == 1 else 1
            best = max(best, run)
            previous = d
        current = 0
        today = self.today()
        if days and days[-1] in [today, today - timedelta(days=1)]:
            d = days[-1]
            pool = set(days)
            while d in pool:
                current += 1
                d -= timedelta(days=1)
        return current, best, days

    def current_cycle(self, plan):
        return self.one(
            "SELECT * FROM cycles WHERE plan_id=? AND active=1 ORDER BY rowid DESC LIMIT 1",
            (plan,),
        )

    def cycle_blocks(self, cycle):
        return self.rows(
            """SELECT b.*,s.name subject,t.name topic,COALESCE(a.elapsed,0) elapsed,d.state,d.reason FROM blocks b JOIN subjects s ON s.id=b.subject_id LEFT JOIN topics t ON t.id=b.topic_id LEFT JOIN (SELECT block_id,SUM(elapsed) elapsed FROM sessions WHERE lap=? GROUP BY block_id) a ON a.block_id=b.id LEFT JOIN decisions d ON d.block_id=b.id AND d.lap=? WHERE b.cycle_id=? AND b.archived=0 ORDER BY b.sort,b.rowid""",
            (cycle["lap"], cycle["lap"], cycle["id"]),
        )

    def decide(self, cycle, block, state, reason=""):
        if state not in ["Concluído", "Adiado", "Retomar"]:
            raise ValueError("Decisão inválida.")
        with self.db:
            if state == "Retomar":
                self.db.execute(
                    "DELETE FROM decisions WHERE block_id=? AND lap=?",
                    (block, cycle["lap"]),
                )
            else:
                self.db.execute(
                    "INSERT INTO decisions VALUES(?,?,?,?,?) ON CONFLICT(block_id,lap) DO UPDATE SET state=excluded.state,reason=excluded.reason",
                    (uid(), block, cycle["lap"], state, reason),
                )
            blocks = self.cycle_blocks(cycle)
            pending = [i for i, b in enumerate(blocks) if not b["state"]]
            self.db.execute(
                "UPDATE cycles SET position=? WHERE id=?",
                (pending[0] if pending else len(blocks), cycle["id"]),
            )
            self.rpg.sync_in_transaction()

    def generate_cycle(self, plan, block_minutes=45, total_minutes=360):
        subjects = self.rows(
            "SELECT * FROM subjects WHERE plan_id=? AND archived=0 ORDER BY name",
            (plan,),
        )
        if (
            not subjects
            or not 1 <= block_minutes <= 600
            or not block_minutes <= total_minutes <= 10080
        ):
            raise ValueError("Cadastre matérias e use durações positivas.")
        count = max(len(subjects), round(total_minutes / block_minutes))
        scores = [s["weight"] * s["difficulty"] for s in subjects]
        if len(subjects) > 200 or count > 500:
            raise ValueError(
                "Para manter o aplicativo leve, gere até 500 blocos e 200 matérias por ciclo."
            )
        allocated = [0] * len(subjects)
        preview = []
        for step in range(count):
            choice = max(
                range(len(subjects)),
                key=lambda i: scores[i] * (step + 1) / sum(scores) - allocated[i],
            )
            allocated[choice] += 1
            preview.append(
                dict(
                    subject_id=subjects[choice]["id"],
                    subject=subjects[choice]["name"],
                    target=block_minutes * 60,
                    category="Teoria",
                )
            )
        return preview

    def import_topics(self, plan, rows):
        if not rows or len(rows) > 10000:
            raise ValueError("Importe entre 1 e 10.000 assuntos por vez.")
        for r in rows:
            if (
                not isinstance(r, dict)
                or not str(r.get("materia", "")).strip()
                or not str(r.get("assunto", "")).strip()
            ):
                raise ValueError("Cada linha precisa de materia e assunto.")
            if r.get("pai") and r["pai"].strip() == r["assunto"].strip():
                raise ValueError("Assunto e pai devem ser diferentes.")
        with self.db:
            for r in rows:
                subject = self.one(
                    "SELECT id FROM subjects WHERE plan_id=? AND name=? AND archived=0",
                    (plan, r["materia"].strip()),
                )
                sid = (
                    subject["id"]
                    if subject
                    else self.put(
                        "subjects",
                        {
                            "plan_id": plan,
                            "name": r["materia"].strip(),
                            "color": COLORS[
                                len(
                                    self.rows(
                                        "SELECT id FROM subjects WHERE plan_id=?",
                                        (plan,),
                                    )
                                )
                                % len(COLORS)
                            ],
                        },
                    )
                )
                parent = None
                if r.get("pai"):
                    existing = self.one(
                        "SELECT id FROM topics WHERE subject_id=? AND name=?",
                        (sid, r["pai"].strip()),
                    )
                    parent = (
                        existing["id"]
                        if existing
                        else self.put(
                            "topics", {"subject_id": sid, "name": r["pai"].strip()}
                        )
                    )
                for name in [r["assunto"]]:
                    existing = self.one(
                        "SELECT id FROM topics WHERE subject_id=? AND name=? AND parent_id IS ?",
                        (sid, name.strip(), parent),
                    )
                    parent = (
                        existing["id"]
                        if existing
                        else self.put(
                            "topics",
                            {
                                "subject_id": sid,
                                "parent_id": parent,
                                "name": name.strip(),
                            },
                        )
                    )

    def snapshot(self):
        return {
            "format": "RUMO",
            "version": 5,
            "created": datetime.now().isoformat(),
            "tables": {t: self.rows(f"SELECT * FROM {t}") for t in TABLES},
        }

    def export(self, path):
        Path(path).write_text(
            json.dumps(self.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def validate_backup(self, path):
        from backups import validate_backup

        return validate_backup(path, SCHEMA, TABLES)

    def reorder_cycle(self, cycle, ids):
        blocks = self.cycle_blocks(cycle)
        if set(ids) != {b["id"] for b in blocks} or len(ids) != len(blocks):
            raise ValueError("Ordem de blocos inválida.")
        current = (
            blocks[cycle["position"]]["id"] if cycle["position"] < len(blocks) else None
        )
        with self.db:
            for i, bid in enumerate(ids):
                self.db.execute("UPDATE blocks SET sort=? WHERE id=?", (i, bid))
            self.db.execute(
                "UPDATE cycles SET position=? WHERE id=?",
                (ids.index(current) if current else len(ids), cycle["id"]),
            )

    def restore(self, path):
        data = self.validate_backup(path)
        # A backup restores studies, never a foreign storage destination.
        destination = self.pref("backup_folder")
        data["tables"]["preferences"] = [
            r for r in data["tables"]["preferences"] if r["key"] != "backup_folder"
        ]
        if destination:
            data["tables"]["preferences"].append(
                {"key": "backup_folder", "value": json.dumps(destination)}
            )
        self.auto_backup(force=True)
        with self.db:
            if not self.db.in_transaction:
                self.db.execute("BEGIN")
            self.db.execute("PRAGMA defer_foreign_keys=ON")
            for t in reversed(TABLES):
                self.db.execute(f"DELETE FROM {t}")
            for t in TABLES:
                for row in data["tables"][t]:
                    keys = list(row)
                    self.db.execute(
                        f"INSERT INTO {t} ({','.join(keys)}) VALUES({','.join('?' for _ in keys)})",
                        list(row.values()),
                    )
            self.rpg.sync_in_transaction()
        return data

    def auto_backup(self, force=False):
        folder = Path(self.pref("backup_folder", str(self.path.parent / "backups")))
        folder.mkdir(parents=True, exist_ok=True)
        today = self.today().isoformat()
        if not force and list(folder.glob(f"RUMO-{today}-*.sqlite3")):
            return
        target = folder / f'RUMO-{today}-{datetime.now().strftime("%H%M%S%f")}.sqlite3'
        dest = sqlite3.connect(target)
        try:
            self.db.backup(dest)
        finally:
            dest.close()
        copies = sorted(
            p
            for p in folder.glob("RUMO-*.sqlite3")
            if re.fullmatch(r"RUMO-\d{4}-\d{2}-\d{2}-\d{12}\.sqlite3", p.name)
        )
        retention = max(1, int(self.pref("retention", 7)))
        for old in copies[:-retention]:
            old.unlink()
        return target

    def export_csv(self, path, plan, f=None):
        where, args = self.filters(plan, f)
        cursor = self.db.execute(
            f"""SELECT s.day data,COALESCE(d.name,'Simulado sem matéria') materia,COALESCE(t.name,s.mock_name,'') assunto,s.category categoria,s.target tempo_previsto_segundos,s.elapsed tempo_liquido_segundos,s.correct acertos,s.wrong erros,s.blank brancos,s.material material,s.notes observacoes FROM {self.source(f)} s LEFT JOIN subjects d ON d.id=s.subject_id LEFT JOIN topics t ON t.id=s.topic_id WHERE {where} ORDER BY s.day""",
            self.source_args(f, args),
        )
        with open(path, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow([c[0] for c in cursor.description])
            writer.writerows(tuple(csv_cell(value) for value in row) for row in cursor)


class Clock:
    def __init__(self, store, monotonic=time.monotonic):
        self.store = store
        self.now = monotonic
        self.last = self.now()
        self.checkpoint = self.last
        r = store.one("SELECT value FROM active WHERE id=1")
        self.state = json.loads(r["value"]) if r else None
        if self.state:
            self.state.setdefault("pauses", [])
            if self.state["running"]:
                self.state["pauses"].append(
                    {
                        "at": self.local_now().isoformat(),
                        "event": "Recuperação após interrupção",
                        "elapsed": self.state["elapsed"],
                    }
                )
            self.state["running"] = False
            self.persist()

    def start(self, fields, mode="Cronômetro"):
        if self.state:
            raise ValueError(
                "Já existe uma sessão ativa. Recupere ou descarte primeiro."
            )
        self.state = dict(
            fields,
            id=uid(),
            mode=mode,
            elapsed=0.0,
            running=True,
            segments=[],
            pauses=[],
        )
        self.last = self.now()
        self.checkpoint = self.last
        self.persist()

    def tick(self):
        now = self.now()
        delta = now - self.last
        self.last = now
        expired = False
        if self.state and self.state["running"]:
            if delta < 0 or delta > 10:
                self.state["running"] = False
                self.state["notice"] = (
                    "Pausa automática: suspensão ou interrupção detectada."
                )
                self.state["pauses"].append(
                    {
                        "at": self.local_now().isoformat(),
                        "event": "Pausa por suspensão / interrupção",
                        "elapsed": self.state["elapsed"],
                    }
                )
            else:
                if self.state["mode"] == "Timer":
                    delta = min(
                        delta, max(0, self.state["target"] - self.state["elapsed"])
                    )
                self.state["elapsed"] += delta
                if delta > 0:
                    day = self.local_now().date().isoformat()
                    segments = self.state["segments"]
                    if segments and segments[-1]["day"] == day:
                        segments[-1]["seconds"] += delta
                    else:
                        segments.append({"day": day, "seconds": delta})
                if (
                    self.state["mode"] == "Timer"
                    and self.state["elapsed"] >= self.state["target"]
                ):
                    self.state["running"] = False
                    expired = True
                    self.state["pauses"].append(
                        {
                            "at": self.local_now().isoformat(),
                            "event": "Timer concluído",
                            "elapsed": self.state["elapsed"],
                        }
                    )
            if now - self.checkpoint >= 5 or not self.state["running"]:
                self.persist()
                self.checkpoint = now
        return expired

    def local_now(self):
        return self.store.local_now()

    def pause(self):
        self.tick()
        if self.state:
            if self.state["running"]:
                self.state["pauses"].append(
                    {
                        "at": self.local_now().isoformat(),
                        "event": "Pausa manual",
                        "elapsed": self.state["elapsed"],
                    }
                )
            self.state["running"] = False
            self.persist()

    def resume(self):
        if self.state:
            if (
                self.state["mode"] == "Timer"
                and self.state["elapsed"] >= self.state["target"]
            ):
                raise ValueError("Acrescente tempo ou finalize o timer.")
            self.last = self.now()
            self.state["running"] = True
            self.persist()

    def add(self, minutes):
        if self.state:
            self.state["target"] += minutes * 60
            self.persist()

    def persist(self):
        with self.store.db:
            if self.state:
                self.store.db.execute(
                    "INSERT OR REPLACE INTO active VALUES(1,?)",
                    (json.dumps(self.state, ensure_ascii=False),),
                )
            else:
                self.store.db.execute("DELETE FROM active")

    def discard(self):
        self.state = None
        self.persist()
