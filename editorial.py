"""Offline editorial workspace. No content is uploaded or published implicitly.

Separate SQLite file chosen by the editor; never opens the learner's database.
Prepared exports are manifests requiring the existing trusted publication process.
"""

import hashlib
import json
import sqlite3
import unicodedata
from datetime import datetime, timezone


def fingerprint(item):
    text = " ".join(
        unicodedata.normalize("NFKC", item.get("statement", "")).casefold().split()
    )
    if not text:
        raise ValueError("Enunciado obrigatório.")
    return hashlib.sha256(text.encode()).hexdigest()


def validate_question(item, taxonomy):
    if not isinstance(item, dict):
        raise ValueError("Questão inválida.")
    for key in ("id", "version", "statement", "subject_id", "answer", "comment"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError("Campo obrigatório: " + key)
    if len(json.dumps(item, ensure_ascii=False)) > 100000:
        raise ValueError("Questão grande demais.")
    if item.get("type") not in ("certo_errado", "multipla_escolha"):
        raise ValueError("Tipo de questão inválido.")
    topics = item.get("topic_ids")
    if (
        not isinstance(topics, list)
        or not topics
        or any(not isinstance(t, str) or not t for t in topics)
        or len(topics) != len(set(topics))
    ):
        raise ValueError("Informe assuntos sem repetições.")
    if any(taxonomy.get(t) != item["subject_id"] for t in topics):
        raise ValueError("Classificação incompatível com a taxonomia.")
    if not isinstance(item.get("exam_ids"), list) or not item["exam_ids"]:
        raise ValueError("Concurso obrigatório.")
    options = item.get("options", [])
    if not isinstance(options, list) or not 2 <= len(options) <= 10:
        raise ValueError("Informe de duas a dez alternativas.")
    ids = [
        o.get("id")
        for o in options
        if isinstance(o, dict) and isinstance(o.get("text"), str) and o["text"].strip()
    ]
    if (
        len(ids) != len(options)
        or any(not isinstance(i, str) or not i for i in ids)
        or len(set(ids)) != len(ids)
        or item["answer"] not in ids
    ):
        raise ValueError("Alternativas ou gabarito inválidos.")
    source = item.get("provenance", {})
    if not isinstance(source, dict) or source.get("kind") not in ("autoral", "banca"):
        raise ValueError("Origem verificável obrigatória.")
    if any(
        not isinstance(source.get(k), str) or not source[k].strip()
        for k in ("source_url", "rights")
    ):
        raise ValueError("Referência e direitos de uso obrigatórios.")
    from security import web_url

    web_url(source["source_url"])
    if source["kind"] == "banca" and (
        not source.get("bank") or type(source.get("year")) is not int
    ):
        raise ValueError("Questão de banca exige banca e ano verificados.")


class Editorial:
    def __init__(self, path, taxonomy):
        self.taxonomy = dict(taxonomy)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        tables = {
            r[0]
            for r in self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if tables - {"drafts", "editions", "audit", "sqlite_sequence"}:
            self.db.close()
            raise ValueError(
                "Escolha um workspace editorial separado; esta base pertence a outro domínio."
            )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS editions(id TEXT NOT NULL,version TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(id,version))"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS drafts(id TEXT PRIMARY KEY,body TEXT NOT NULL,fingerprint TEXT NOT NULL UNIQUE,status TEXT NOT NULL,review TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS audit(sequence INTEGER PRIMARY KEY, item_id TEXT NOT NULL, action TEXT NOT NULL,actor TEXT NOT NULL,at TEXT NOT NULL)"
        )

    def close(self):
        self.db.close()

    def _audit(self, item_id, action, actor):
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("Identifique o editor responsável.")
        self.db.execute(
            "INSERT INTO audit(item_id,action,actor,at) VALUES(?,?,?,?)",
            (item_id, action, actor, datetime.now(timezone.utc).isoformat()),
        )

    def import_batch(self, items, actor):
        if not isinstance(items, list) or not 1 <= len(items) <= 1000:
            raise ValueError("Importe de 1 a 1.000 questões por lote.")
        added, duplicates = [], []
        with self.db:
            for item in items:
                validate_question(item, self.taxonomy)
                digest = fingerprint(item)
                existing = self.db.execute(
                    "SELECT id FROM drafts WHERE id=? OR fingerprint=?",
                    (item["id"], digest),
                ).fetchone()
                if existing:
                    duplicates.append(dict(id=item["id"], existing=existing["id"]))
                    continue
                self.db.execute(
                    "INSERT INTO drafts VALUES(?,?,?,'draft',NULL)",
                    (item["id"], json.dumps(item, ensure_ascii=False), digest),
                )
                self._audit(item["id"], "import", actor)
                added.append(item["id"])
        return dict(added=added, duplicates=duplicates)

    def items(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM drafts ORDER BY rowid")]

    def correct(self, item, actor):
        validate_question(item, self.taxonomy)
        with self.db:
            row = self.db.execute(
                "SELECT status,body FROM drafts WHERE id=?", (item["id"],)
            ).fetchone()
            if not row:
                raise ValueError("Questão desconhecida.")
            if self.db.execute(
                "SELECT 1 FROM editions WHERE id=? AND version=?",
                (item["id"], item["version"]),
            ).fetchone():
                raise ValueError(
                    "Preserve o ID e crie uma nova versão para corrigir conteúdo já preparado."
                )
            self.db.execute(
                "UPDATE drafts SET body=?,fingerprint=?,status='draft',review=NULL WHERE id=?",
                (json.dumps(item, ensure_ascii=False), fingerprint(item), item["id"]),
            )
            self._audit(item["id"], "correct", actor)

    def approve(self, item_id, actor):
        with self.db:
            row = self.db.execute(
                "SELECT * FROM drafts WHERE id=?", (item_id,)
            ).fetchone()
            if not row or row["status"] not in ("draft", "approved"):
                raise ValueError("Rascunho indisponível para revisão.")
            validate_question(json.loads(row["body"]), self.taxonomy)
            review = dict(
                status="aprovada",
                reviewer=actor,
                reviewed_at=datetime.now(timezone.utc).isoformat(),
            )
            self.db.execute(
                "UPDATE drafts SET status='approved',review=? WHERE id=?",
                (json.dumps(review), item_id),
            )
            self._audit(item_id, "approve-answer-metadata-rights", actor)

    def prepare(self, ids, actor):
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Selecione um lote sem IDs repetidos.")
        result = []
        with self.db:
            for item_id in ids:
                row = self.db.execute(
                    "SELECT * FROM drafts WHERE id=?", (item_id,)
                ).fetchone()
                if not row or row["status"] not in ("approved", "prepared"):
                    raise ValueError("Todo o lote precisa de aprovação editorial.")
                item = json.loads(row["body"])
                validate_question(item, self.taxonomy)
                item.update(status="publicada", review=json.loads(row["review"]))
                result.append(item)
                self.db.execute(
                    "INSERT OR IGNORE INTO editions VALUES(?,?,?)",
                    (item_id, item["version"], json.dumps(item, ensure_ascii=False)),
                )
                self.db.execute(
                    "UPDATE drafts SET status='prepared' WHERE id=?", (item_id,)
                )
                self._audit(item_id, "prepare-publication", actor)
        return dict(format="rumo-editorial-v1", published=False, questions=result)

    def withdraw(self, item_id, actor, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Informe o motivo da retirada.")
        with self.db:
            row = self.db.execute(
                "SELECT body FROM drafts WHERE id=?", (item_id,)
            ).fetchone()
            if not row:
                raise ValueError("Questão desconhecida.")
            self.db.execute(
                "UPDATE drafts SET status='withdrawn' WHERE id=?", (item_id,)
            )
            self._audit(item_id, "withdraw: " + reason, actor)
        return dict(
            id=item_id,
            version=json.loads(row["body"])["version"],
            action="withdraw",
            applied=False,
            reason=reason,
        )
