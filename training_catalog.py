"""Public lesson catalog: contract and validation (no Tk, no network).

A catalog is accepted only when every rule passes; otherwise the previous valid
catalog stays active. Planned lessons never carry a resource; a published lesson
needs an approved review by an identified reviewer and a valid PDF resource.
Fixture catalogs (``kind: "teste"``) exist to validate the infrastructure and
are always shown as test material, never as study content or coverage.
"""

import re
from datetime import date
from urllib.parse import urlsplit

from training_schema import SHA256, valid_id, valid_version

SCHEMA_VERSION = 1
PUBLICATION = ("planejada", "rascunho", "em_revisao", "publicada", "arquivada", "teste")
REVIEW = ("pendente", "aprovada", "reprovada")
KINDS = ("publicado", "teste")
MAX_LESSONS = 20000
MAX_PDF_BYTES = 200 * 1024 * 1024
MAX_TEXT = 4000
PATH = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\.pdf")


class CatalogError(ValueError):
    """The catalog was rejected; the message says which rule failed."""


def need(condition, message):
    if not condition:
        raise CatalogError(message)


def text(value, field, limit=MAX_TEXT, required=True):
    if value is None and not required:
        return ""
    need(
        isinstance(value, str) and (value.strip() or not required),
        f"{field}: texto obrigatório.",
    )
    need(
        len(value) <= limit and not any(ord(c) < 32 and c not in "\n\t" for c in value),
        f"{field}: texto inválido.",
    )
    return value


def texts(values, field, limit=60):
    need(isinstance(values, list) and len(values) <= limit, f"{field}: lista inválida.")
    return [text(v, field, 600) for v in values]


def ids(values, field, known):
    need(isinstance(values, list) and len(values) <= 200, f"{field}: lista inválida.")
    for value in values:
        need(
            valid_id(value) and value in known,
            f"{field}: referência desconhecida {value!r}.",
        )
    return list(values)


def iso_day(value, field):
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise CatalogError(f"{field}: data AAAA-MM-DD obrigatória.") from None
    return value


def resource_url(value, base_is_local, allowed_hosts):
    """HTTPS on an approved host, or a relative path inside a local catalog folder."""
    need(isinstance(value, str) and len(value) <= 2000, "recurso: URL inválida.")
    if base_is_local and PATH.fullmatch(value) and ".." not in value.split("/"):
        return value
    parts = urlsplit(value)
    need(parts.scheme == "https" and parts.hostname, "recurso: use HTTPS.")
    need(not parts.username and not parts.password, "recurso: URL com credenciais.")
    need(
        parts.hostname.lower() in allowed_hosts,
        f"recurso: host não aprovado ({parts.hostname}).",
    )
    return value


def validate_resource(raw, base_is_local, allowed_hosts):
    need(isinstance(raw, dict), "recurso: objeto obrigatório.")
    need(valid_id(raw.get("id")), "recurso: id inválido.")
    need(valid_version(raw.get("version")), "recurso: versão inválida.")
    need(
        raw.get("media_type") == "application/pdf", "recurso: somente application/pdf."
    )
    size = raw.get("bytes")
    need(type(size) is int and 0 < size <= MAX_PDF_BYTES, "recurso: tamanho inválido.")
    need(
        isinstance(raw.get("sha256"), str) and SHA256.fullmatch(raw["sha256"]),
        "recurso: sha256 inválido.",
    )
    pages = raw.get("page_count")
    need(
        pages is None or (type(pages) is int and 0 < pages <= 100000),
        "recurso: páginas inválidas.",
    )
    return dict(
        id=raw["id"],
        version=raw["version"],
        url=resource_url(raw.get("url"), base_is_local, allowed_hosts),
        media_type="application/pdf",
        bytes=size,
        sha256=raw["sha256"],
        license=text(raw.get("license"), "recurso: licença", 200),
        page_count=pages,
        published_at=(
            iso_day(raw["published_at"], "recurso: publicação")
            if raw.get("published_at")
            else None
        ),
    )


def validate_review(raw):
    raw = raw or {}
    need(
        isinstance(raw, dict) and raw.get("status", "pendente") in REVIEW,
        "revisão: estado inválido.",
    )
    review = dict(
        status=raw.get("status", "pendente"),
        reviewer=raw.get("reviewer"),
        reviewed_at=raw.get("reviewed_at"),
    )
    if review["status"] == "aprovada":
        text(review["reviewer"], "revisão: responsável", 200)
        iso_day(review["reviewed_at"], "revisão: data")
    return review


def validate_sources(raw):
    need(isinstance(raw, list) and len(raw) <= 100, "fontes: lista inválida.")
    sources = []
    for item in raw:
        need(isinstance(item, dict), "fontes: item inválido.")
        url = item.get("url")
        if url:
            parts = urlsplit(url)
            need(
                parts.scheme in ("http", "https") and parts.hostname,
                "fontes: URL inválida.",
            )
        sources.append(
            dict(
                title=text(item.get("title"), "fontes: título", 400),
                url=url or None,
                accessed_at=(
                    iso_day(item["accessed_at"], "fontes: consulta")
                    if item.get("accessed_at")
                    else None
                ),
            )
        )
    return sources


def validate_coverage(raw):
    need(isinstance(raw, list) and len(raw) <= 500, "cobertura: lista inválida.")
    links = []
    for item in raw:
        need(
            isinstance(item, dict) and isinstance(item.get("exam_id"), str),
            "cobertura: item inválido.",
        )
        links.append(
            dict(
                exam_id=item["exam_id"],
                item_id=item.get("item_id"),
                discipline_id=item.get("discipline_id"),
                depth=text(
                    item.get("depth"), "cobertura: profundidade", 200, required=False
                ),
                status=text(
                    item.get("status") or "nao-auditada", "cobertura: estado", 60
                ),
                note=text(
                    item.get("note"), "cobertura: observação", 600, required=False
                ),
            )
        )
    return links


def validate_lesson(raw, kind, topics, base_is_local, allowed_hosts):
    need(isinstance(raw, dict) and valid_id(raw.get("id")), "aula: id inválido.")
    lid = raw["id"]
    status = raw.get("publication_status")
    need(status in PUBLICATION, f"{lid}: estado de publicação inválido.")
    need(
        status != "teste" or kind == "teste",
        f"{lid}: material de teste só em catálogo de teste.",
    )
    need(
        valid_version(raw.get("content_version")),
        f"{lid}: versão de conteúdo inválida.",
    )
    need(
        raw.get("primary_topic_id") in topics, f"{lid}: assunto principal desconhecido."
    )
    review = validate_review(raw.get("review"))
    resource = raw.get("resource")
    if status in ("publicada", "teste"):
        need(resource is not None, f"{lid}: aula disponível sem recurso PDF.")
        resource = validate_resource(resource, base_is_local, allowed_hosts)
    else:
        # Planned or draft lessons never point to a file (no fictitious URLs).
        need(resource is None, f"{lid}: só aulas publicadas têm recurso.")
    if status == "publicada":
        need(review["status"] == "aprovada", f"{lid}: publicada sem revisão aprovada.")
    return dict(
        id=lid,
        title=text(raw.get("title"), f"{lid}: título", 300),
        primary_topic_id=raw["primary_topic_id"],
        additional_topic_ids=ids(
            raw.get("additional_topic_ids", []), f"{lid}: assuntos", topics
        ),
        content_version=raw["content_version"],
        publication_status=status,
        summary=text(raw.get("summary"), f"{lid}: resumo", required=False),
        objectives=texts(raw.get("objectives", []), f"{lid}: objetivos"),
        prerequisite_lesson_ids=list(raw.get("prerequisite_lesson_ids", [])),
        authors=texts(raw.get("authors", []), f"{lid}: autores", 20),
        review=review,
        resource=resource,
        license=text(raw.get("license"), f"{lid}: licença", 200, required=False),
        sources=validate_sources(raw.get("sources", [])),
        coverage_links=validate_coverage(raw.get("coverage_links", [])),
        changes=text(raw.get("changes"), f"{lid}: mudanças", required=False),
    )


def validate_catalog(data, base_is_local=False, allowed_hosts=()):
    """Return a normalized catalog or raise CatalogError. Pure function."""
    hosts = {h.lower() for h in allowed_hosts}
    need(isinstance(data, dict), "Catálogo: objeto JSON esperado.")
    need(
        data.get("schema_version") == SCHEMA_VERSION,
        "Catálogo: versão de esquema incompatível.",
    )
    need(valid_id(data.get("catalog_id")), "Catálogo: id inválido.")
    need(valid_version(data.get("catalog_version")), "Catálogo: versão inválida.")
    kind = data.get("kind", "publicado")
    need(kind in KINDS, "Catálogo: tipo inválido.")
    subjects, topics, lessons = (
        data.get("subjects"),
        data.get("topics"),
        data.get("lessons"),
    )
    need(
        all(isinstance(x, list) for x in (subjects, topics, lessons)),
        "Catálogo: listas obrigatórias.",
    )
    need(len(lessons) <= MAX_LESSONS, "Catálogo: aulas demais.")
    seen = set()

    def unique(value):
        need(
            valid_id(value) and value not in seen,
            f"Catálogo: id repetido ou inválido {value!r}.",
        )
        seen.add(value)
        return value

    subject_map = {
        unique(s.get("id")): dict(id=s["id"], name=text(s.get("name"), "matéria", 200))
        for s in subjects
        if isinstance(s, dict)
    }
    need(len(subject_map) == len(subjects), "Catálogo: matéria inválida.")
    topic_map = {}
    for t in topics:
        need(
            isinstance(t, dict) and t.get("subject_id") in subject_map,
            "Catálogo: assunto sem matéria.",
        )
        topic_map[unique(t.get("id"))] = dict(
            id=t["id"],
            subject_id=t["subject_id"],
            name=text(t.get("name"), "assunto", 300),
        )
    for t in topics:
        topic_map[t["id"]]["suggested_prerequisite_topic_ids"] = ids(
            t.get("suggested_prerequisite_topic_ids", []), "pré-requisitos", topic_map
        )
    lesson_list = [
        validate_lesson(raw, kind, topic_map, base_is_local, hosts) for raw in lessons
    ]
    for lesson in lesson_list:
        unique(lesson["id"])
    known = {lesson["id"] for lesson in lesson_list}
    for lesson in lesson_list:
        ids(
            lesson["prerequisite_lesson_ids"],
            f"{lesson['id']}: aulas pré-requisito",
            known,
        )
    return dict(
        schema_version=SCHEMA_VERSION,
        catalog_id=data["catalog_id"],
        catalog_version=data["catalog_version"],
        generated_at=data.get("generated_at"),
        kind=kind,
        notice=text(data.get("notice"), "aviso", required=False),
        subjects=list(subject_map.values()),
        topics=list(topic_map.values()),
        lessons=lesson_list,
    )
