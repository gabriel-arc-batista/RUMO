"""Local question bank and training rounds of the Arena (no Tk).

A round is an ordinary "Questões" session of one topic: counts go to `sessions`
and attempts to `arena_attempts`, both inside `Store.save_session`'s
transaction. XP comes only from that session.
"""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from arena_schema import KINDS, MAX_TEXT, STATUSES
from training_schema import valid_id, valid_version

PACK = "RUMO-questions"
MAX_PACK = 2 * 1024 * 1024
LETTERS = "abcdefghij"
IN_PLAN = "JOIN topics t ON t.id=q.topic_id JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=?"
ANSWERED = "EXISTS(SELECT 1 FROM arena_attempts a WHERE a.question_id=q.id)"
LAST_ANSWER = (
    "(SELECT MAX(a.answered_at) FROM arena_attempts a WHERE a.question_id=q.id)"
)
WRONG_LAST = (
    "q.status='ativa' AND (SELECT a.correct FROM arena_attempts a WHERE "
    "a.question_id=q.id ORDER BY a.answered_at DESC, a.rowid DESC LIMIT 1)=0"
)
MODES = {
    "novas": (f"q.status!='retirada' AND NOT {ANSWERED}", "q.created"),
    "refazer": (WRONG_LAST, "q.created"),
    "todas": ("q.status!='retirada'", f"{LAST_ANSWER} ASC NULLS FIRST, q.created"),
}
COLUMNS = (
    "subject_id",
    "topic_id",
    "kind",
    "statement",
    "options",
    "answer",
    "comment",
    "source",
    "status",
    "version",
    "fingerprint",
    "updated",
)


def fingerprint(kind, statement):
    text = re.sub(r"\s+", " ", statement.casefold()).strip()
    return hashlib.sha256(f"{kind}\0{text}".encode()).hexdigest()


def _text(value):
    return isinstance(value, str) and len(value) <= MAX_TEXT


def validate(payload):
    """Return the question fields, normalized, or raise ValueError."""
    if not isinstance(payload, dict) or payload.get("kind") not in KINDS:
        raise ValueError("Tipo de questão inválido.")
    kind, answer = payload["kind"], payload.get("answer")
    statement, options = payload.get("statement"), payload.get("options") or []
    comment, source = payload.get("comment", ""), payload.get("source", "")
    if not _text(statement) or not statement.strip():
        raise ValueError("Escreva o enunciado.")
    if not _text(comment) or not _text(source):
        raise ValueError("Comentário ou fonte inválidos.")
    if kind == "certo-errado":
        if options or answer not in ("certo", "errado"):
            raise ValueError(
                "Certo ou errado não tem alternativas; o gabarito é certo ou errado."
            )
    else:
        options = _options(options)
        if answer not in {o["id"] for o in options}:
            raise ValueError("O gabarito deve ser uma das alternativas.")
    return dict(
        kind=kind,
        statement=statement,
        options=options,
        answer=answer,
        comment=comment,
        source=source,
    )


def _options(options):
    if not isinstance(options, list) or not 2 <= len(options) <= 10:
        raise ValueError("Use de 2 a 10 alternativas.")
    if not all(isinstance(o, dict) for o in options):
        raise ValueError("Alternativas inválidas.")
    ids = [o.get("id") for o in options]
    if len(set(ids)) != len(ids) or any(i not in LETTERS or not i for i in ids):
        raise ValueError("As alternativas usam letras únicas de a a j.")
    if not all(_text(o.get("text")) and o["text"].strip() for o in options):
        raise ValueError("Preencha o texto de todas as alternativas.")
    return [dict(id=o["id"], text=o["text"]) for o in options]


def _source(provenance):
    if not isinstance(provenance, dict):
        return ""
    keys = ("bank", "year", "exam_id", "rights", "source")
    parts = [provenance.get(k) for k in keys]
    if provenance.get("kind") == "autoral":
        parts.insert(0, "Autoral")
    return " · ".join(str(p) for p in parts if p)[:300]


def _next_version(version):
    bumped = re.sub(r"\d+$", lambda m: str(int(m[0]) + 1), version)
    return bumped if bumped != version else version + ".1"


def _decode(row):
    return dict(row, options=json.loads(row["options"]))


def _pack_item(item, number):
    """Validated pack entry, or None when it is not publishable here."""
    if not isinstance(item, dict):
        raise ValueError(f"Questão {number} do pacote inválida.")
    status = item.get("status")
    if status not in ("publicada", "anulada") or item.get("type") == "discursiva-curta":
        return None
    version = str(item.get("version", "1"))
    if not valid_id(item.get("id")) or not valid_version(version):
        raise ValueError(f"Questão {number} do pacote sem identificação válida.")
    payload = dict(
        kind=item.get("type"),
        statement=item.get("statement"),
        options=item.get("options"),
        answer=item.get("answer"),
        comment=item.get("comment", ""),
        source=_source(item.get("provenance")),
    )
    try:
        fields = validate(payload)
    except ValueError as exc:
        raise ValueError(f"Questão {number} do pacote: {exc}") from exc
    status = "ativa" if status == "publicada" else "anulada"
    return dict(id=item["id"], version=version, status=status, fields=fields)


@dataclass
class Round:
    plan_id: str
    subject_id: str
    topic_id: str
    questions: tuple
    now: object = field(default=datetime.now, repr=False)
    attempts: dict = field(default_factory=dict, init=False, repr=False)
    session_id: str | None = field(default=None, init=False)

    def answer(self, question_id, choice):
        if question_id in self.attempts:
            raise ValueError("Esta questão já foi respondida nesta rodada.")
        q = next((q for q in self.questions if q["id"] == question_id), None)
        if q is None:
            raise ValueError("Questão fora desta rodada.")
        if q["kind"] == "certo-errado":
            valid = ("certo", "errado")
        else:
            valid = [o["id"] for o in q["options"]]
        if choice not in valid:
            raise ValueError("Resposta inválida.")
        correct = None if q["status"] == "anulada" else choice == q["answer"]
        self.attempts[question_id] = dict(
            question_id=question_id,
            question_version=q["version"],
            answer=choice,
            correct=correct,
            answered_at=self.now().isoformat(timespec="seconds"),
        )
        return dict(correct=correct, expected=q["answer"], comment=q["comment"])

    @property
    def done(self):
        return len(self.attempts) == len(self.questions)

    @property
    def counts(self):
        """(hits, misses); annulled questions count as neither."""
        results = [a["correct"] for a in self.attempts.values()]
        return results.count(True), results.count(False)


class Arena:
    def __init__(self, store, now=None):
        # The Store's clock decides the study day, like every other session.
        self.store, self.now = store, now or store.local_now

    # Bank

    def questions(self, plan_id, topic_id=None, query="", include_retired=False):
        sql, args = f"SELECT q.* FROM arena_questions q {IN_PLAN}", [plan_id]
        if topic_id:
            sql, args = sql + " AND q.topic_id=?", args + [topic_id]
        if not include_retired:
            sql += " AND q.status!='retirada'"
        if query.strip():
            escaped = re.sub(r"([\\%_])", r"\\\1", query.strip())
            sql += " AND q.statement LIKE ? ESCAPE '\\'"
            args.append(f"%{escaped}%")
        rows = self.store.rows(sql + " ORDER BY q.created", args)
        return [_decode(r) for r in rows]

    def question(self, question_id):
        row = self.store.one("SELECT * FROM arena_questions WHERE id=?", (question_id,))
        return _decode(row) if row else None

    def save_question(self, payload, question_id=None):
        """Create or edit a question; an edit raises its version."""
        fields = validate(payload)
        subject, topic = payload.get("subject_id"), payload.get("topic_id")
        self._check_topic(subject, topic)
        old = self.question(question_id) if question_id else None
        if question_id and not old:
            raise ValueError("Questão não encontrada.")
        row = self._row(fields, subject, topic)
        if self._duplicate(topic, row["fingerprint"], question_id):
            raise ValueError("Questão repetida neste assunto.")
        with self.store.db:
            if not old:
                return self._insert(row, "pessoal")
            row.update(status=old["status"], version=_next_version(old["version"]))
            self._update(question_id, row)
        return question_id

    def set_status(self, question_id, status):
        if status not in STATUSES:
            raise ValueError("Situação da questão inválida.")
        with self.store.db:
            changed = self.store.db.execute(
                "UPDATE arena_questions SET status=?,updated=? WHERE id=?",
                (status, self._stamp(), question_id),
            ).rowcount
        if not changed:
            raise ValueError("Questão não encontrada.")

    def import_pack(self, text, subject_id, topic_id):
        """Validate the whole pack first, then write it in one transaction."""
        if len(text.encode("utf-8")) > MAX_PACK:
            raise ValueError("O pacote passa de 2 MB.")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("O arquivo não é um JSON válido.") from exc
        if (
            not isinstance(data, dict)
            or data.get("format") != PACK
            or data.get("version") != 1
        ):
            raise ValueError("Este arquivo não é um pacote de questões do RUMO.")
        items = data.get("questions")
        if not isinstance(items, list) or len(items) > 1000:
            raise ValueError("O pacote deve ter até 1000 questões.")
        self._check_topic(subject_id, topic_id)
        parsed = [_pack_item(item, n) for n, item in enumerate(items, 1)]
        counts = dict(added=0, updated=0, skipped=0)
        with self.store.db:
            for item in parsed:
                result = self._merge(item, subject_id, topic_id) if item else "skipped"
                counts[result] += 1
        return counts

    def export_personal(self, plan_id):
        rows = self.store.rows(
            f"SELECT q.* FROM arena_questions q {IN_PLAN} AND q.origin='pessoal' "
            "ORDER BY q.created",
            (plan_id,),
        )
        questions = [
            dict(
                id=r["id"],
                type=r["kind"],
                statement=r["statement"],
                options=json.loads(r["options"]),
                answer=r["answer"],
                comment=r["comment"],
                provenance=dict(kind="autoral", source=r["source"]),
                status="publicada" if r["status"] == "ativa" else r["status"],
                version=r["version"],
            )
            for r in rows
        ]
        pack = dict(format=PACK, version=1, questions=questions)
        return json.dumps(pack, ensure_ascii=False, indent=2)

    # Training

    def topics(self, plan_id):
        return self.store.rows(
            f"""SELECT s.id subject_id,s.name subject,t.id topic_id,t.name topic,
            COUNT(*) total,
            SUM(CASE WHEN {ANSWERED} THEN 0 ELSE 1 END) unanswered,
            SUM(CASE WHEN {WRONG_LAST} THEN 1 ELSE 0 END) to_redo
            FROM arena_questions q {IN_PLAN} AND q.status!='retirada'
            GROUP BY t.id ORDER BY s.name,t.name""",
            (plan_id,),
        )

    def start_round(self, plan_id, topic_id, mode="novas", limit=10):
        if mode not in MODES:
            raise ValueError("Modo de treino inválido.")
        where, order = MODES[mode]
        rows = self.store.rows(
            f"SELECT q.* FROM arena_questions q {IN_PLAN} AND q.topic_id=? "
            f"AND {where} ORDER BY {order} LIMIT ?",
            (plan_id, topic_id, limit),
        )
        if not rows:
            raise ValueError("Não há questões para treinar neste modo.")
        questions = tuple(_decode(r) for r in rows)
        return Round(plan_id, rows[0]["subject_id"], topic_id, questions, self.now)

    def finish_round(self, round_, elapsed):
        """Save the round once as a session; None when nothing was answered."""
        if type(elapsed) is not int or elapsed < 0:
            raise ValueError("Tempo da rodada inválido.")
        if round_.session_id or not round_.attempts:
            return round_.session_id
        correct, wrong = round_.counts
        values = dict(
            plan_id=round_.plan_id,
            subject_id=round_.subject_id,
            topic_id=round_.topic_id,
            day=self.now().date().isoformat(),
            category="Questões",
            elapsed=elapsed,
            correct=correct,
            wrong=wrong,
            blank=0,
        )
        context = {"arena_attempts": list(round_.attempts.values())}
        round_.session_id = self.store.save_session(values, context=context)
        return round_.session_id

    def summary(self, plan_id):
        bank = self.store.one(
            f"""SELECT COUNT(*) questions,
            COALESCE(SUM(CASE WHEN {ANSWERED} THEN 1 ELSE 0 END),0) answered,
            COALESCE(SUM(CASE WHEN {WRONG_LAST} THEN 1 ELSE 0 END),0) to_redo
            FROM arena_questions q {IN_PLAN} AND q.status!='retirada'""",
            (plan_id,),
        )
        tally = self.store.one(
            f"""SELECT COALESCE(SUM(a.correct=1),0) correct,
            COALESCE(SUM(a.correct=0),0) wrong
            FROM arena_attempts a JOIN arena_questions q ON q.id=a.question_id
            {IN_PLAN} AND q.status!='retirada'""",
            (plan_id,),
        )
        answers = tally["correct"] + tally["wrong"]
        accuracy = round(tally["correct"] / answers * 100, 2) if answers else None
        return dict(bank, **tally, accuracy=accuracy)

    # Persistence helpers

    def _stamp(self):
        return self.now().isoformat(timespec="seconds")

    def _check_topic(self, subject_id, topic_id):
        topic = self.store.one("SELECT subject_id FROM topics WHERE id=?", (topic_id,))
        if not topic or topic["subject_id"] != subject_id:
            raise ValueError("O assunto não pertence à matéria escolhida.")

    def _duplicate(self, topic_id, print_, exclude=None):
        return self.store.one(
            "SELECT 1 FROM arena_questions WHERE topic_id=? AND fingerprint=? "
            "AND id IS NOT ?",
            (topic_id, print_, exclude),
        )

    def _row(self, fields, subject_id, topic_id, status="ativa", version="1"):
        return dict(
            fields,
            options=json.dumps(fields["options"], ensure_ascii=False),
            subject_id=subject_id,
            topic_id=topic_id,
            status=status,
            version=version,
            fingerprint=fingerprint(fields["kind"], fields["statement"]),
            updated=self._stamp(),
        )

    def _insert(self, row, origin, external_id=None):
        qid = uuid.uuid4().hex
        self.store.db.execute(
            f"INSERT INTO arena_questions(id,origin,external_id,created,"
            f"{','.join(COLUMNS)}) VALUES({','.join('?' * (len(COLUMNS) + 4))})",
            [qid, origin, external_id, row["updated"], *(row[c] for c in COLUMNS)],
        )
        return qid

    def _update(self, question_id, row):
        self.store.db.execute(
            f"UPDATE arena_questions SET {','.join(c + '=?' for c in COLUMNS)} "
            "WHERE id=?",
            [*(row[c] for c in COLUMNS), question_id],
        )

    def _merge(self, item, subject_id, topic_id):
        """Add, update (new version) or skip one validated pack item."""
        row = self._row(
            item["fields"], subject_id, topic_id, item["status"], item["version"]
        )
        old = self.store.one(
            "SELECT id,version FROM arena_questions WHERE external_id=?", (item["id"],)
        )
        if old:
            if old["version"] == item["version"]:
                return "skipped"
            self._update(old["id"], row)
            return "updated"
        if self._duplicate(topic_id, row["fingerprint"]):
            return "skipped"
        self._insert(row, "pacote", item["id"])
        return "added"
