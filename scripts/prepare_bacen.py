"""Build reproducible structured content from the official opening notice PDF.
Development-only pypdf dependency; no PDF parsing in the desktop runtime.
"""

import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader

assets = Path(__file__).resolve().parents[1] / "assets"
pdf = assets / "BACEN-2024-edital-abertura.pdf"
text = "\n".join(p.extract_text() for p in PdfReader(pdf).pages[32:36])
text = re.sub(r"\n\s*\d{2}\s*\n", "\n", text)
text = re.sub(r"\s+", " ", text)
common = text.split("CONHECIMENTOS BÁSICOS PARA TODOS OS CARGOS", 1)[1].split(
    "CONHECIMENTOS ESPECÍFICOS", 1
)[0]
ti = text.split("CARGO 1: ANALISTA - ÁREA 1 - TECNOLOGIA DA INFORMAÇÃO", 1)[1].split(
    "CARGO 2: ANALISTA - ÁREA 2 - ECONOMIA E FINANÇAS", 1
)[0]
econ = text.split("CARGO 2: ANALISTA - ÁREA 2 - ECONOMIA E FINANÇAS", 1)[1].split(
    "MARCELO FORESTI", 1
)[0]
header = re.compile(
    r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s/–()\-]+?)\s*\((\d+|SOMENTE PARA A PROVA DISCURSIVA)\)\s*:"
)


def parse(section):
    matches = list(header.finditer(section))
    rows = []
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        content = section[
            m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(section)
        ].strip()
        if name == "FUNDAMENTOS DE MACROECONOMIA E MICROECONOMIA":
            pieces = [
                (
                    "Macroeconomia",
                    content.split("I MACROECONOMIA:", 1)[1].split(
                        "II MICROECONOMIA:", 1
                    )[0],
                ),
                ("Microeconomia", content.split("II MICROECONOMIA:", 1)[1]),
            ]
        else:
            pieces = [("", content)]
        for prefix, body in pieces:
            numbers = list(
                re.finditer(
                    r"(?<!\S)(\d+(?:\.\d+)*)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç])", body
                )
            )
            top = {}
            for j, n in enumerate(numbers):
                number = n.group(1)
                item = (
                    body[
                        n.end() : (
                            numbers[j + 1].start()
                            if j + 1 < len(numbers)
                            else len(body)
                        )
                    ]
                    .strip()
                    .rstrip(".")
                )
                if not item:
                    continue
                label = (prefix + " — " if prefix else "") + number + " " + item
                parent_number = number.rsplit(".", 1)[0] if "." in number else None
                parent = top.get(parent_number, "")
                rows.append({"materia": name.title(), "assunto": label, "pai": parent})
                top[number] = label
            if not numbers:
                rows.append(
                    {"materia": name.title(), "assunto": body.rstrip("."), "pai": ""}
                )
    return rows


basics = parse(common)
areas = {
    "Tecnologia da Informação": basics + parse(ti),
    "Economia e Finanças": basics + parse(econ),
}
data = {
    "source": "https://bcb.gov.br/content/acessoinformacao/analista_2024/Edital-n-1-de-Abertura-do-concurso.pdf",
    "notice": "Edital nº 1 – BCB, de 15 de janeiro de 2024",
    "section": "18 — Objetos de avaliação",
    "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
    "note": "Edital de abertura histórico; não é um edital novo nem consolidação de retificações. Numeração e texto preservados; quebras do PDF normalizadas.",
    "areas": areas,
}
(assets / "bacen2024.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
)
for name, rows in areas.items():
    print(name, len(rows), "assuntos", len({r["materia"] for r in rows}), "matérias")
