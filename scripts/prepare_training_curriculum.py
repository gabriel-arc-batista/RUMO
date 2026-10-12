"""Build assets/training/curriculo.json from the editorial package.

Usage: python scripts/prepare_training_curriculum.py

Inputs (docs/campo-de-treinamento/): programas-9-concursos.json,
catalogo-aulas-planejadas.json and auditoria/programas-extraidos.json (made by
audit_training_programs.py). The output is planning, not published content:
every lesson stays "planejada", every link "candidato" and every program
decomposition "pendente de conferência". Counts are checked against the inputs.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "campo-de-treinamento"
OUTPUT = ROOT / "assets" / "training" / "curriculo.json"

# What was checked about later amendments of each edition (11/10/2026).
RETIFICATIONS = {
    "tse-2024-analista-ti": "Texto do arquivo consolidado até a 4ª retificação (RET_4); inclusões do Edital nº 3 identificadas nos itens. Retificações posteriores não conferidas.",
    "bacen-2024-ti": "Texto do arquivo consolidado até a 4ª retificação (RET_4); retificações dos Editais nº 2 e nº 4 identificadas nos itens. Retificações posteriores não conferidas.",
    "senado-2022-analise-sistemas": "Texto do edital retificado nº 2 (01/09/2022). Retificações posteriores não conferidas.",
}
DEFAULT_RETIFICATION = "Texto do edital de abertura indicado. Retificações posteriores ainda não conferidas."


def exams(programs, audit):
    extracted = {e["exam_id"]: e for e in audit["exams"]}
    result = []
    for exam in programs["exams"]:
        cut = extracted[exam["id"]]
        disciplines = []
        for record in cut["disciplines"]:
            disciplines.append(
                dict(
                    id=record["id"],
                    name=record["name"],
                    source_pages=record["source_pages"],
                    decomposition=record["decomposition"],
                    review_status="pendente",
                    items=[
                        dict(id=i["id"], number=i["number"], text=i["text"])
                        for i in record["items"]
                    ],
                    whole_text=record["original_text"] if not record["items"] else "",
                    notes=[
                        note
                        for note in (
                            record.get("retification_note"),
                            (
                                "Números fora da sequência oficial: "
                                + ", ".join(record["numbers_not_accepted"])
                                if record.get("numbers_not_accepted")
                                else None
                            ),
                            (
                                "A numeração do próprio edital tem lacunas."
                                if "lacuna" in record["decomposition"]
                                else None
                            ),
                            (
                                "Itens sem numeração oficial; a ordem dos marcadores serve só de referência."
                                if record["decomposition"] == "marcadores-sem-numero"
                                else None
                            ),
                        )
                        if note
                    ],
                )
            )
        result.append(
            dict(
                id=exam["id"],
                organization=exam["organization"],
                edition_year=exam["edition_year"],
                role=exam["role"],
                bank=exam["bank"],
                source_url=exam["source_url"],
                retifications=RETIFICATIONS.get(exam["id"], DEFAULT_RETIFICATION),
                editorial_level=exam["difficulty"],
                disciplines=disciplines,
            )
        )
    return result


def families(catalog):
    result = []
    for family in catalog["families"]:
        lessons = []
        for index, lesson in enumerate(family["suggested_lessons"], 1):
            lessons.append(
                dict(
                    id=lesson["id"],
                    topic_id=f"{family['id']}:assunto:{index:02d}",
                    title=lesson["title"],
                    status="planejada",
                )
            )
        result.append(
            dict(
                id=family["id"],
                name=family["name"],
                area=family["area"],
                coverage_status="nao-auditada",
                candidates=[
                    dict(
                        exam_id=c["exam_id"],
                        discipline_id=c["discipline_id"],
                        status=c["mapping_status"],
                    )
                    for c in family["source_candidates"]
                ],
                lessons=lessons,
            )
        )
    return result


def main():
    programs = json.loads(
        (PACKAGE / "programas-9-concursos.json").read_text(encoding="utf-8")
    )
    catalog = json.loads(
        (PACKAGE / "catalogo-aulas-planejadas.json").read_text(encoding="utf-8")
    )
    audit = json.loads(
        (PACKAGE / "auditoria" / "programas-extraidos.json").read_text(encoding="utf-8")
    )
    data = dict(
        schema_version=1,
        kind="planejamento",
        notice=(
            "Planejamento editorial: nenhuma aula abaixo existe como PDF. Programas extraídos "
            "automaticamente dos editais oficiais e pendentes de conferência humana."
        ),
        researched_at=programs["researched_at"],
        exams=exams(programs, audit),
        families=families(catalog),
    )
    total = sum(len(f["lessons"]) for f in data["families"])
    assert len(data["families"]) == 60 and total == 267, (len(data["families"]), total)
    assert sum(len(e["disciplines"]) for e in data["exams"]) == 80
    ids = [l["id"] for f in data["families"] for l in f["lessons"]] + [
        f["id"] for f in data["families"]
    ]
    assert len(ids) == len(set(ids)), "IDs repetidos no planejamento"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    items = sum(len(d["items"]) for e in data["exams"] for d in e["disciplines"])
    print(
        f"{len(data['exams'])} editais, 80 disciplinas, {items} itens; 60 famílias, {total} aulas planejadas"
    )


if __name__ == "__main__":
    main()
