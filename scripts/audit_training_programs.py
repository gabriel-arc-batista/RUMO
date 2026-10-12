"""Extract and decompose the official programs of the nine selected TI profiles.

Usage: python scripts/audit_training_programs.py PDF_FOLDER

PDF_FOLDER holds the official PDFs named <exam_id>.pdf (download them from the
URLs in docs/campo-de-treinamento/programas-9-concursos.json). Output:
docs/campo-de-treinamento/auditoria/programas-extraidos.json.

Nothing here certifies coverage. Each profile is cut between explicit anchors of
its own role, so contents of other roles of the same selection stay out. An item
number is accepted only when it continues the official sequence (1 → 2, 2 → 2.1,
2.1 → 2.2 or 3); numbers inside laws, versions and dates are ignored. Disciplines
whose numbering does not close are kept whole and marked as pending review.
Requires pypdfium2 (also used by the reader).
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "campo-de-treinamento"
OUTPUT = PACKAGE / "auditoria" / "programas-extraidos.json"

# Role cuts: (start anchor, end anchor) pairs, in document order. Anchors are
# literal fragments checked by hand against the rendered pages.
CUTS = {
    "bb-2022-001-ti": [
        (
            "AGENTE DE TECNOLOGIA e AGENTE COMERCIAL",
            "ESCRITURÁRIO - NOME DE RELACIONAMENTO: AGENTE COMERCIAL",
        )
    ],
    "caixa-2024-tbn-ti": [
        (
            "CONHECIMENTOS BÁSICOS/TBN E TBN TI",
            "CONHECIMENTOS ESPECÍFICOS - TÉCNICO BANCÁRIO NOVO\n",
        ),
        ("CONHECIMENTOS ESPECÍFICOS - TÉCNICO BANCÁRIO NOVO - TI", "ANEXO V"),
    ],
    "ufabc-2023-tecnico-ti": [
        ("Química; Técnico de Tecnologia da Informação.", "CONHECIMENTOS ESPECÍFICOS"),
        ("Para o cargo: Técnico de Tecnologia da Informação.", "CONHECIMENTOS GERAIS"),
    ],
    "serpro-2023-tecnologia": [("14.2 CONHECIMENTOS", "MARCELO BATISTA DE NORONHA")],
    "dataprev-2024-desenvolvimento": [
        ("ANEXO I – CONTEÚDO PROGRAMÁTICO", "MODULO II"),
        ("PERFIL: 3. DESENVOLVIMENTO DE SOFTWARE", "PERFIL: 4."),
    ],
    "tse-2024-analista-ti": [
        ("CONHECIMENTOS BÁSICOS\nLÍNGUA PORTUGUESA", "CONHECIMENTOS ESPECÍFICOS"),
        ("CARGO 17: ANALISTA JUDICIÁRIO", "CARGO 18: ANALISTA JUDICIÁRIO"),
    ],
    "bacen-2024-ti": [
        ("CONHECIMENTOS BÁSICOS PARA TODOS OS CARGOS", "CONHECIMENTOS ESPECÍFICOS"),
        (
            "CARGO 2: ANALISTA – ÁREA: TECNOLOGIA DA INFORMAÇÃO",
            "MARCELO FORESTI DE MATHEUS COTA",
        ),
    ],
    "stn-2024-transformacao-digital": [
        (
            "CONHECIMENTOS GERAIS (COMUM A TODAS AS ÁREAS):",
            "ÁREA DE CONHECIMENTO: ECONÔMICO-FINANCEIRA",
        ),
        ("ÁREA DE CONHECIMENTO: TI – TRANSFORMAÇÃO DIGITAL", "ANEXO II"),
    ],
    "senado-2022-analise-sistemas": [
        ("BLOCO I – CONHECIMENTOS GERAIS", "BLOCO II – CONHECIMENTOS ESPECÍFICOS"),
        (
            "6. INFORMÁTICA LEGISLATIVA/SUBÁREA ANÁLISE DE SISTEMAS.",
            "7. INFORMÁTICA LEGISLATIVA/SUBÁREA ANÁLISE DE SUPORTE",
        ),
    ],
}
# Headings that differ from the package's discipline names.
HEADINGS = {
    "senado-2022-analise-sistemas": {
        "INFORMÁTICA LEGISLATIVA — ANÁLISE DE SISTEMAS": "6. INFORMÁTICA LEGISLATIVA/SUBÁREA ANÁLISE DE SISTEMAS.",
    },
    # The Caixa TI heading has no colon; the first item follows on the next line.
    "caixa-2024-tbn-ti": {
        "TECNOLOGIA DA INFORMAÇÃO": r"re:TECNOLOGIA DA INFORMAÇÃO\s*\n(?=1 - )",
    },
}
# A number may follow "palavra." ("alterações.17-") but never "3." (3.978, 3.9.X).
NUMBER = re.compile(
    r"(?<![\w,/º°ª§-])(?<!\d\.)(\d{1,2}(?:\.\d{1,2}){0,3})(?!\d)\.?\s*(?:[-–]\s*)?"
    r"(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç“\"]|\d{1,3}\s+[a-z])"
)
# Running headers, footers and page numbers that interrupt the program text.
NOISE = re.compile(
    r"^\s*(?:\d{1,3}|.*\|\s*CONCURSO PÚBLICO.*|SENADO FEDERAL|ENSINO SUPERIOR COMPLETO"
    r"|\d+(?:\.\d+)+\s+CONHECIMENTOS ESPECÍFICOS)\s*$",
    re.M,
)
ROMAN = re.compile(
    r"(?<![\w])(I|II|III|IV|V)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ ]{3,60}):"
)
BULLET = ""


def pages_of(pdf):
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return [doc[n].get_textpage().get_text_bounded() for n in range(len(doc))]
    finally:
        doc.close()


def cut(pages, anchors):
    """Concatenated role text with a page index for every character."""
    full = ""
    owner = []
    for number, text in enumerate(pages, 1):
        full += text + "\n"
        owner += [number] * (len(text) + 1)
    pieces = []
    position = 0
    for start, end in anchors:
        # Anchors are searched in order: a role name in an earlier vacancy table
        # must not be taken for the program heading.
        first = anchor(start).search(full, position)
        if not first:
            raise ValueError(f"Âncora não encontrada: {start!r}")
        last = anchor(end).search(full, first.end())
        if not last:
            raise ValueError(f"Âncora final não encontrada: {end!r}")
        pieces.append(
            (full[first.start() : last.start()], owner[first.start() : last.start()])
        )
        position = last.start()
    return pieces


def anchor(text):
    """Literal anchor; any run of whitespace matches any run of whitespace."""
    return re.compile(r"\s+".join(re.escape(part) for part in text.split()))


def clean(text):
    text = NOISE.sub("", text.replace("\r", ""))
    text = re.sub(r"-\n(?=[a-zà-ú])", "", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def heading_pattern(name, override):
    if override:
        if override.startswith("re:"):
            return re.compile(override[3:])
        return re.compile(re.escape(override))
    base = re.sub(r"\s*\(\d+\)$", "", name)
    words = [re.escape(w) for w in re.split(r"[\s—–-]+", base) if w]
    # Optional parenthetical before the colon, e.g. "(EXCETO PARA CARGO 18: ...)".
    return re.compile(
        r"\s*[–—-]?\s*".join(words) + r"(?:\s*\((?:[^()]|\([^()]*\)){0,300}\))?\s*:"
    )


def locate(exam, pieces):
    """Find each discipline heading inside the role text, in document order."""
    found = []
    for index, subject in enumerate(exam["subjects"]):
        override = HEADINGS.get(exam["id"], {}).get(subject["name"])
        pattern = heading_pattern(subject["name"], override)
        hit = None
        for piece_index, (text, owner) in enumerate(pieces):
            match = pattern.search(text)
            if match:
                hit = (piece_index, match.start(), match.end())
                break
        found.append((index, subject, hit))
    return found


SECTION = re.compile(
    r"(?:^|\n)\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 /()–—,.-]{4,160}?)\s*:"
)


def other_headings(text):
    """Upper-case headings that the package did not list (for the audit report)."""
    return [m.group(1).strip() for m in SECTION.finditer(text)]


def successor(path, candidate):
    """Is ``candidate`` the next number after ``path`` in a hierarchical list?"""
    parts = [int(x) for x in candidate.split(".")]
    if not path:
        return parts == [1]
    if parts == path + [1]:
        return True
    for depth in range(len(path), 0, -1):
        if parts == path[: depth - 1] + [path[depth - 1] + 1]:
            return True
    return False


def numbered(text, lenient=False):
    """Split by accepted numbers; ``lenient`` tolerates gaps of the original."""
    items = []
    path = []
    marks = []
    for match in NUMBER.finditer(text):
        number = match.group(1)
        accept = successor(path, number)
        if not accept and lenient and "." not in number and path:
            # Only a new top-level item that starts a sentence, with a capital
            # letter, may skip at most two numbers ("1. ... 3. ..." in the original).
            accept = (
                0 < int(number) - path[0] <= 3
                and text[: match.start()].rstrip().endswith(".")
                and text[match.end() : match.end() + 1].isupper()
            )
        if accept:
            path = [int(x) for x in number.split(".")]
            marks.append((match.start(), match.end(), number))
    for i, (start, end, number) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        items.append(dict(number=number, text=text[end:stop].strip(" .;,")))
    preface = text[: marks[0][0]].strip(" .;:,") if marks else text
    return items, preface


def unaccepted(text, items):
    """Numbers that look like item starts but break the sequence (for reviewers)."""
    accepted = {item["number"] for item in items}
    found = []
    for match in NUMBER.finditer(text):
        number = match.group(1)
        before = text[: match.start()].rstrip()
        after = text[match.end() : match.end() + 1]
        if number not in accepted and before.endswith(".") and after.isupper():
            found.append(number)
    return found


def bullets(text):
    parts = [p.strip(" ;.") for p in text.split(BULLET)]
    return [
        dict(number=f"m{i}", text=p) for i, p in enumerate((p for p in parts if p), 1)
    ]


RETIFICATION = re.compile(
    r"\s*\(((?:Retificad|Incluíd|Alterad|Acrescentad)[^()]*(?:\([^()]*\)[^()]*)*)\)\.?\s*$"
)


def split_note(text):
    """Separate a trailing '(Retificado por meio do Edital ...)' from the item."""
    match = RETIFICATION.search(text)
    return (
        (text[: match.start()].rstrip(" .;"), match.group(1)) if match else (text, None)
    )


def decompose(text):
    """Items with their official numbering when it can be trusted."""
    if BULLET in text:
        return bullets(text), "marcadores-sem-numero", ""
    groups = list(ROMAN.finditer(text))
    if groups:
        items = []
        for i, group in enumerate(groups):
            stop = groups[i + 1].start() if i + 1 < len(groups) else len(text)
            inner, _ = numbered(text[group.end() : stop])
            items += [
                dict(
                    item,
                    number=f"{group.group(1)}.{item['number']}",
                    group=group.group(2).strip(),
                )
                for item in inner
            ]
        return items, "numeracao-oficial-por-grupo", ""
    items, preface = numbered(text)
    if not items:
        return [], "bloco-sem-numeracao", preface
    loose, _ = numbered(text, lenient=True)
    if len(loose) > len(items):
        return loose, "numeracao-oficial-com-lacuna-no-original", preface
    return items, "numeracao-oficial", preface


def audit_exam(exam, pdf):
    pages = pages_of(pdf)
    pieces = cut(pages, CUTS[exam["id"]])
    located = locate(exam, pieces)
    starts = sorted((h[0], h[1], h[2], i) for i, _, h in located if h)
    disciplines = []
    for index, subject, hit in located:
        record = dict(
            id=subject["id"],
            name=subject["name"],
            source_pages=[],
            original_text="",
            items=[],
            decomposition="titulo-nao-localizado",
            review_status="pendente",
        )
        if hit:
            piece, begin, body = hit
            following = [s for s in starts if (s[0], s[1]) > (piece, begin)]
            same_piece = [s for s in following if s[0] == piece]
            stop = same_piece[0][1] if same_piece else len(pieces[piece][0])
            # Any other section heading (e.g. a discipline for other roles) also ends it.
            section = SECTION.search(pieces[piece][0], body, stop)
            if section:
                stop = section.start()
            raw = pieces[piece][0][body:stop]
            record["source_pages"] = sorted(set(pieces[piece][1][body:stop]))
            record["original_text"] = clean(raw)
            items, kind, preface = decompose(record["original_text"])
            record["decomposition"] = kind
            suspicious = unaccepted(record["original_text"], items) if items else []
            if (
                suspicious
                and kind.startswith("numeracao-oficial")
                and "grupo" not in kind
            ):
                record["numbers_not_accepted"] = suspicious
            if preface:
                record["preface"] = preface
            record["items"] = []
            for item in items:
                body, note = split_note(item["text"])
                entry = dict(
                    item, text=body, id=f"{subject['id']}:item:{item['number']}"
                )
                if note:
                    entry["retification_note"] = note
                    record["retification_note"] = note
                record["items"].append(entry)
        disciplines.append(record)
    unlisted = sorted(
        {h for text, _ in pieces for h in other_headings(text)}
        - {re.sub(r"\s*\(\d+\)$", "", d["name"]).upper() for d in disciplines}
    )
    return dict(
        exam_id=exam["id"],
        organization=exam["organization"],
        role=exam["role"],
        source_url=exam["source_url"],
        cut_anchors=CUTS[exam["id"]],
        pdf_pages=len(pages),
        disciplines=disciplines,
        headings_not_in_package=unlisted,
    )


def main(folder):
    programs = json.loads(
        (PACKAGE / "programas-9-concursos.json").read_text(encoding="utf-8")
    )
    exams = [audit_exam(e, Path(folder) / f"{e['id']}.pdf") for e in programs["exams"]]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            dict(
                schema_version=1,
                method=(
                    "Recorte por âncoras do cargo, títulos do pacote e numeração aceita somente "
                    "quando continua a sequência oficial. Extração automática: exige conferência "
                    "humana contra a página renderizada antes de qualquer cobertura."
                ),
                review_status="pendente-de-conferencia-humana",
                exams=exams,
            ),
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    for exam in exams:
        total = sum(len(d["items"]) for d in exam["disciplines"])
        missing = [
            d["name"]
            for d in exam["disciplines"]
            if d["decomposition"] == "titulo-nao-localizado"
        ]
        print(
            f"{exam['exam_id']}: {len(exam['disciplines'])} disciplinas, {total} itens; não localizadas: {missing}"
        )


if __name__ == "__main__":
    main(sys.argv[1])
