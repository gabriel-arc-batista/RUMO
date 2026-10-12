import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { PDFDocumentProxy } from "pdfjs-dist";
import type { OutlineItem } from "../../domain/types";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export type { PDFDocumentProxy };
export { pdfjs };

/** Devolve a tarefa de carregamento (destroy() libera o worker). Sem XFA nem scripts. */
export function openPdf(url: string) {
  return pdfjs.getDocument({ url, enableXfa: false });
}

/** Índice do próprio PDF (outline), com o número da página resolvido. */
export async function readOutline(doc: PDFDocumentProxy): Promise<OutlineItem[]> {
  const items = (await doc.getOutline()) ?? [];
  const result: OutlineItem[] = [];
  for (const item of items) {
    try {
      const dest = typeof item.dest === "string" ? await doc.getDestination(item.dest) : item.dest;
      if (!dest) continue;
      const index = await doc.getPageIndex(dest[0] as never);
      result.push({ title: item.title, page: index + 1 });
    } catch {
      /* destino inválido: ignora o item */
    }
  }
  return result;
}

const textCache = new WeakMap<PDFDocumentProxy, Map<number, string>>();

export async function pageText(doc: PDFDocumentProxy, page: number): Promise<string> {
  let cache = textCache.get(doc);
  if (!cache) {
    cache = new Map();
    textCache.set(doc, cache);
  }
  const hit = cache.get(page);
  if (hit !== undefined) return hit;
  const content = await (await doc.getPage(page)).getTextContent();
  const text = content.items.map((i) => ("str" in i ? i.str : "")).join(" ").replace(/\s+/g, " ");
  cache.set(page, text);
  return text;
}

export interface SearchHit {
  page: number;
  snippet: string;
}

const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

/** Busca sem diferenciar acentos nem maiúsculas. */
export async function searchPdf(doc: PDFDocumentProxy, query: string, signal: { cancelled: boolean }): Promise<SearchHit[]> {
  const needle = fold(query.trim());
  if (needle.length < 2) return [];
  const hits: SearchHit[] = [];
  for (let page = 1; page <= doc.numPages; page += 1) {
    if (signal.cancelled) break;
    const text = await pageText(doc, page);
    const folded = fold(text);
    let from = 0;
    for (;;) {
      const at = folded.indexOf(needle, from);
      if (at < 0) break;
      const start = Math.max(0, at - 40);
      hits.push({ page, snippet: `${start > 0 ? "…" : ""}${text.slice(start, at + needle.length + 60).trim()}…` });
      from = at + needle.length;
      if (hits.length > 200) return hits;
    }
  }
  return hits;
}
