"""Generate the identified TEST catalog used to validate the Campo de Treinamento.

Usage: python scripts/make_test_lesson.py [OUTPUT_FOLDER]
Default output: tests/fixtures/campo-teste/

Writes catalog.json (kind "teste") and two versions of a small PDF with a text
layer, an outline (table of contents), a diagram and code, so the reader can be
checked for search, index, zoom, notes and updates. The PDF says on every page
that it is test material and not a lesson. Standard library only.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "tests" / "fixtures" / "campo-teste"
WIDTH, HEIGHT = 595, 842


def escape(text):
    data = text.encode("cp1252")
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def page_stream(title, lines, number, total, version, extra=b""):
    out = [b"0.97 0.96 0.93 rg 0 0 595 842 re f"]
    out.append(b"0.78 0.67 0.43 rg 0 806 595 36 re f")
    out.append(
        b"BT /F2 10 Tf 0.07 0.07 0.07 rg 40 820 Td ("
        + escape("MATERIAL DE TESTE DO RUMO — NÃO É UMA AULA")
        + b") Tj ET"
    )
    out.append(b"BT /F2 20 Tf 0.1 0.1 0.1 rg 40 760 Td (" + escape(title) + b") Tj ET")
    y = 730
    for font, size, text in lines:
        out.append(
            b"BT /%s %d Tf 0.15 0.15 0.15 rg 40 %d Td (" % (font.encode(), size, y)
            + escape(text)
            + b") Tj ET"
        )
        y -= size + 8
    out.append(extra)
    footer = f"Versão {version} · página {number} de {total} · gerado por scripts/make_test_lesson.py"
    out.append(b"BT /F1 8 Tf 0.4 0.4 0.4 rg 40 30 Td (" + escape(footer) + b") Tj ET")
    return b"\n".join(out)


DIAGRAM = b"""
0.2 0.4 0.7 RG 2 w 60 420 160 70 re S 330 420 160 70 re S
BT /F1 12 Tf 0.1 0.1 0.1 rg 95 450 Td (Tabela A) Tj ET
BT /F1 12 Tf 0.1 0.1 0.1 rg 365 450 Td (Tabela B) Tj ET
0.78 0.55 0.2 RG 220 455 m 330 455 l S 320 462 m 330 455 l 320 448 l S
"""


def pages(version):
    changed = (
        "Esta é a versão 2: o texto da página 2 mudou." if version == "2.0.0" else ""
    )
    content = [
        (
            "Leitor: página de abertura",
            [
                (
                    "F1",
                    12,
                    "Este PDF valida o Campo de Treinamento: download, leitura e notas.",
                ),
                (
                    "F1",
                    12,
                    "Ele não ensina conteúdo de concurso e não conta como cobertura.",
                ),
                ("F1", 12, "Palavra para testar a busca: relacional."),
            ],
            b"",
        ),
        (
            "Seção 1: diagrama",
            [
                ("F1", 12, "O desenho abaixo não deve ser invertido pelo modo escuro."),
                ("F1", 12, changed or "Duas tabelas e uma relação entre elas."),
            ],
            DIAGRAM,
        ),
        (
            "Seção 2: código",
            [
                ("F3", 11, "SELECT a.nome, b.total"),
                ("F3", 11, "FROM tabela_a a"),
                ("F3", 11, "JOIN tabela_b b ON b.a_id = a.id;"),
                ("F1", 12, "O código deve continuar legível em qualquer zoom."),
            ],
            b"",
        ),
        (
            "Seção 3: página final",
            [
                ("F1", 12, "Última página. Use-a para testar a retomada de leitura."),
                ("F1", 12, "Outra ocorrência para a busca: relacional."),
            ],
            b"",
        ),
    ]
    return [
        page_stream(t, l, i + 1, len(content), version, e)
        for i, (t, l, e) in enumerate(content)
    ]


def build_pdf(version):
    streams = pages(version)
    objects = []

    def add(body):
        objects.append(body)
        return len(objects)

    catalog = add(None)
    pages_id = add(None)
    fonts = [
        add(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
        ),
        add(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
        ),
        add(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"
        ),
    ]
    resources = b"<< /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >>" % tuple(fonts)
    page_ids = []
    for stream in streams:
        content = add(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )
        page_ids.append(
            add(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] /Resources %s /Contents %d 0 R >>"
                % (pages_id, WIDTH, HEIGHT, resources, content)
            )
        )
    outline = add(None)
    titles = [
        "Abertura",
        "Seção 1: diagrama",
        "Seção 2: código",
        "Seção 3: página final",
    ]
    entries = list(range(len(objects) + 1, len(objects) + 1 + len(titles)))
    for index, (title, page) in enumerate(zip(titles, page_ids)):
        links = b""
        if index > 0:
            links += b" /Prev %d 0 R" % entries[index - 1]
        if index < len(titles) - 1:
            links += b" /Next %d 0 R" % entries[index + 1]
        add(
            b"<< /Title ("
            + escape(title)
            + b") /Parent %d 0 R /Dest [%d 0 R /XYZ 0 842 null]%s >>"
            % (outline, page, links)
        )
    objects[outline - 1] = (
        b"<< /Type /Outlines /First %d 0 R /Last %d 0 R /Count %d >>"
        % (
            entries[0],
            entries[-1],
            len(titles),
        )
    )
    objects[pages_id - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(b"%d 0 R" % p for p in page_ids),
        len(page_ids),
    )
    objects[catalog - 1] = (
        b"<< /Type /Catalog /Pages %d 0 R /Outlines %d 0 R /PageMode /UseOutlines >>"
        % (
            pages_id,
            outline,
        )
    )
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog,
        xref,
    )
    return bytes(out)


def resource(lesson_id, version, path, data):
    return dict(
        id=lesson_id + ":pdf",
        version=version,
        url=path,
        media_type="application/pdf",
        bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        license="Somente para testes do RUMO",
        page_count=4,
        published_at="2026-10-11",
    )


def catalog(lesson_id, version, path, data):
    return dict(
        schema_version=1,
        catalog_id="rumo-teste-leitor",
        catalog_version=version,
        generated_at="2026-10-11",
        kind="teste",
        notice="Catálogo de TESTE para validar download e leitor. Não é conteúdo de estudo.",
        subjects=[dict(id="teste.campo", name="Material de teste")],
        topics=[
            dict(
                id="teste.campo:leitor",
                subject_id="teste.campo",
                name="Validação do leitor",
                suggested_prerequisite_topic_ids=[],
            )
        ],
        lessons=[
            dict(
                id=lesson_id,
                primary_topic_id="teste.campo:leitor",
                additional_topic_ids=[],
                title="[TESTE] Validação do leitor do RUMO",
                content_version=version,
                publication_status="teste",
                summary="PDF gerado automaticamente para testar o fluxo. Não é uma aula.",
                objectives=[
                    "Conferir download, hash e leitura offline",
                    "Conferir busca, índice, zoom, favoritos e notas",
                ],
                authors=["Gerador automatizado do RUMO"],
                review=dict(status="pendente", reviewer=None, reviewed_at=None),
                resource=resource(lesson_id, version, path, data),
                license="Somente para testes do RUMO",
                sources=[],
                coverage_links=[],
                changes="Versão 2 altera a página 2." if version == "2.0.0" else "",
            )
        ],
    )


def main(folder):
    folder = Path(folder)
    (folder / "arquivos").mkdir(parents=True, exist_ok=True)
    lesson_id = "teste.campo:leitor:aula:01"
    for version in ("1.0.0", "2.0.0"):
        data = build_pdf(version)
        name = f"arquivos/leitor-teste-{version}.pdf"
        (folder / name).write_bytes(data)
        (folder / f"catalog-{version}.json").write_text(
            json.dumps(
                catalog(lesson_id, version, name, data), ensure_ascii=False, indent=1
            ),
            encoding="utf-8",
        )
    (folder / "catalog.json").write_text(
        (folder / "catalog-1.0.0.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    print("Catálogo de teste em", folder)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
