// Gera PDFs de EXEMPLO (não são aulas) para o modo exemplo do site:
// texto pesquisável, índice (outline), diagrama vetorial e faixa de aviso em toda página.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "pdf");

// WinAnsi cobre os acentos do português nas mesmas posições do Latin-1.
function pdfText(text) {
  let s = "";
  for (const ch of text) {
    const code = ch.codePointAt(0);
    if (ch === "(" || ch === ")" || ch === "\\") s += "\\" + ch;
    else if (code === 0x2014) s += "\\227";
    else if (code === 0x2013) s += "\\226";
    else if (code === 0x201c) s += "\\223";
    else if (code === 0x201d) s += "\\224";
    else if (code === 0x2022) s += "\\225";
    else if (code < 128) s += ch;
    else if (code < 256) s += "\\" + code.toString(8).padStart(3, "0");
    else s += "?";
  }
  return s;
}

function wrap(text, max) {
  const lines = [];
  let line = "";
  for (const word of text.split(" ")) {
    if ((line + " " + word).trim().length > max) {
      lines.push(line.trim());
      line = word;
    } else line += " " + word;
  }
  if (line.trim()) lines.push(line.trim());
  return lines;
}

function pageStream({ title, paragraphs, code, diagram, pageNo, total, docTitle }) {
  const ops = [];
  const text = (font, size, x, y, value, rgb = "0.12 0.11 0.10") =>
    ops.push(`BT ${rgb} rg /${font} ${size} Tf ${x} ${y} Td (${pdfText(value)}) Tj ET`);
  // Faixa de aviso.
  ops.push("0.79 0.67 0.43 rg 0 806 595 36 re f");
  text("F2", 9, 48, 820, "MATERIAL DE EXEMPLO DO SITE RUMO — NÃO É UMA AULA", "0.10 0.08 0.04");
  text("F1", 9, 430, 820, `${docTitle}`.slice(0, 32), "0.10 0.08 0.04");
  let y = 760;
  text("F2", 20, 48, y, title);
  y -= 30;
  for (const p of paragraphs) {
    for (const line of wrap(p, 88)) {
      text("F1", 11, 48, y, line);
      y -= 16;
    }
    y -= 10;
  }
  if (code) {
    const lines = code.split("\n");
    ops.push(`0.93 0.91 0.86 rg 44 ${y - lines.length * 14 - 8} 507 ${lines.length * 14 + 16} re f`);
    y -= 8;
    for (const line of lines) {
      text("F3", 10, 56, y, line);
      y -= 14;
    }
    y -= 18;
  }
  if (diagram) {
    // Duas tabelas e uma relação: cores próprias que não devem ser invertidas no modo escuro.
    const top = y - 30;
    ops.push("0.23 0.39 0.59 RG 1.5 w");
    ops.push(`70 ${top - 90} 170 90 re S 355 ${top - 90} 170 90 re S`);
    ops.push(`0.79 0.67 0.43 RG 2 w 240 ${top - 45} m 355 ${top - 45} l S`);
    ops.push(`0.79 0.67 0.43 rg 355 ${top - 45} m 345 ${top - 40} l 345 ${top - 50} l f`);
    text("F2", 11, 82, top - 22, diagram[0]);
    text("F2", 11, 367, top - 22, diagram[1]);
    text("F1", 10, 82, top - 42, "id (PK)");
    text("F1", 10, 82, top - 58, "nome");
    text("F1", 10, 367, top - 42, "id (PK)");
    text("F1", 10, 367, top - 58, `${diagram[0].toLowerCase()}_id (FK)`);
    text("F1", 9, 250, top - 38, "1 : N", "0.45 0.36 0.16");
    y = top - 120;
  }
  text("F1", 9, 48, 36, `Página ${pageNo} de ${total}`, "0.45 0.43 0.40");
  return ops.join("\n");
}

function buildPdf(doc) {
  const objects = [];
  const add = (body) => {
    objects.push(body);
    return objects.length;
  };
  const catalogId = add(null);
  const pagesId = add(null);
  const outlinesId = add(null);
  const f1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
  const f2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
  const f3 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>");
  const pageIds = [];
  doc.pages.forEach((page, index) => {
    const stream = pageStream({ ...page, pageNo: index + 1, total: doc.pages.length, docTitle: doc.title });
    const contentId = add(`<< /Length ${Buffer.byteLength(stream, "latin1")} >>\nstream\n${stream}\nendstream`);
    pageIds.push(
      add(
        `<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 595 842] /Contents ${contentId} 0 R ` +
          `/Resources << /Font << /F1 ${f1} 0 R /F2 ${f2} 0 R /F3 ${f3} 0 R >> >> >>`,
      ),
    );
  });
  const sections = doc.pages.map((p, i) => ({ title: p.title, page: i })).filter((p) => p.title && doc.outline.includes(p.page));
  const itemIds = sections.map(() => add(null));
  sections.forEach((s, i) => {
    const prev = i > 0 ? ` /Prev ${itemIds[i - 1]} 0 R` : "";
    const next = i < sections.length - 1 ? ` /Next ${itemIds[i + 1]} 0 R` : "";
    objects[itemIds[i] - 1] =
      `<< /Title (${pdfText(s.title)}) /Parent ${outlinesId} 0 R${prev}${next} /Dest [${pageIds[s.page]} 0 R /XYZ 0 842 0] >>`;
  });
  objects[outlinesId - 1] = itemIds.length
    ? `<< /Type /Outlines /First ${itemIds[0]} 0 R /Last ${itemIds.at(-1)} 0 R /Count ${itemIds.length} >>`
    : "<< /Type /Outlines /Count 0 >>";
  objects[pagesId - 1] = `<< /Type /Pages /Kids [${pageIds.map((id) => `${id} 0 R`).join(" ")}] /Count ${pageIds.length} >>`;
  objects[catalogId - 1] = `<< /Type /Catalog /Pages ${pagesId} 0 R /Outlines ${outlinesId} 0 R /PageMode /UseOutlines >>`;
  const info = add(`<< /Title (${pdfText(doc.title)}) /Producer (RUMO site - exemplo) >>`);

  let body = "%PDF-1.4\n%\xE2\xE3\xCF\xD3\n";
  const offsets = [];
  objects.forEach((obj, i) => {
    offsets.push(Buffer.byteLength(body, "latin1"));
    body += `${i + 1} 0 obj\n${obj}\nendobj\n`;
  });
  const xref = Buffer.byteLength(body, "latin1");
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  body += offsets.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`).join("");
  body += `trailer\n<< /Size ${objects.length + 1} /Root ${catalogId} 0 R /Info ${info} 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(body, "latin1");
}

const relational = [
  "O modelo relacional organiza os dados em relações, apresentadas como tabelas. Cada linha é uma tupla e cada coluna é um atributo com um domínio de valores possíveis.",
  "Uma chave candidata identifica cada tupla de forma única e mínima. A chave primária é a candidata escolhida; as demais permanecem como chaves alternativas.",
  "A chave estrangeira referencia uma chave candidata de outra relação. A integridade referencial exige que cada valor da chave estrangeira exista na relação referenciada ou seja nulo, quando isso for permitido.",
  "A álgebra relacional define operações como seleção, projeção, junção, união e diferença. Consultas SQL podem ser entendidas como composições dessas operações.",
  "Este texto existe para exercitar o leitor do site: paginação, zoom, busca, índice, notas e a marcação manual “Li esta página”. Ele não substitui uma aula revisada.",
];
const sectionsRel = [
  "Abertura",
  "Relações, tuplas e atributos",
  "Domínios e valores nulos",
  "Chaves candidatas e primária",
  "Chaves estrangeiras",
  "Integridade referencial",
  "Diagrama: duas relações",
  "Cardinalidade 1:N",
  "Álgebra relacional: seleção",
  "Álgebra relacional: projeção",
  "Junções",
  "Exemplo em SQL",
  "Visões",
  "Restrições de integridade",
  "Índices e chaves",
  "Dependências funcionais",
  "Rumo à normalização",
  "Erros comuns",
  "Resumo",
  "Página final",
];
const relationalDoc = {
  title: "Exemplo: modelo relacional",
  outline: [0, 1, 3, 4, 6, 8, 10, 11, 15, 18, 19],
  pages: sectionsRel.map((title, i) => ({
    title,
    paragraphs: [relational[i % relational.length], relational[(i + 2) % relational.length]],
    diagram: i === 6 ? ["Cliente", "Pedido"] : null,
    code:
      i === 11
        ? "SELECT c.nome, COUNT(p.id) AS pedidos\nFROM cliente c\nLEFT JOIN pedido p ON p.cliente_id = c.id\nGROUP BY c.nome;"
        : null,
  })),
};

const sqlText = [
  "A junção interna devolve apenas as combinações que satisfazem a condição. Linhas sem correspondência ficam de fora do resultado.",
  "A junção externa à esquerda preserva todas as linhas da tabela à esquerda; as colunas da direita sem correspondência aparecem como nulas.",
  "Uma autojunção relaciona a tabela com ela mesma, por exemplo funcionários e seus gestores. Apelidos diferentes deixam a consulta legível.",
  "Material de exemplo do site RUMO para testar títulos longos e a leitura de código. Não é uma aula.",
];
const sqlDoc = {
  title: "Exemplo: junções em SQL",
  outline: [0, 2, 5, 8, 11],
  pages: Array.from({ length: 12 }, (_, i) => ({
    title: ["Abertura", "Junção interna", "Junção externa", "Exemplo", "Autojunção", "Exercício guiado"][Math.floor(i / 2)] + (i % 2 ? " (cont.)" : ""),
    paragraphs: [sqlText[i % sqlText.length], sqlText[(i + 1) % sqlText.length]],
    code: i === 3 ? "SELECT f.nome, g.nome AS gestor\nFROM funcionario f\nLEFT JOIN funcionario g ON g.id = f.gestor_id;" : null,
    diagram: i === 7 ? ["Funcionario", "Gestor"] : null,
  })),
};
sqlDoc.pages[0].title = "Abertura";
sqlDoc.pages[11].title = "Página final";

mkdirSync(out, { recursive: true });
writeFileSync(join(out, "exemplo-modelo-relacional.pdf"), buildPdf(relationalDoc));
writeFileSync(join(out, "exemplo-juncoes-sql.pdf"), buildPdf(sqlDoc));
console.log("PDFs de exemplo gerados em web/public/pdf");
