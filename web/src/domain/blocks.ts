import type { Block } from "./types";

/**
 * Converte o enunciado em texto do catálogo em blocos legíveis:
 * ```código```, $$fórmula$$ e ![descrição](https://imagem) em linhas próprias.
 * Imagens só por HTTPS ou caminho do próprio site.
 */
export function parseStatement(text: string): Block[] {
  const blocks: Block[] = [];
  const pattern = /```([\w+-]*)\n([\s\S]*?)```|\$\$([\s\S]+?)\$\$|!\[([^\]]*)\]\(([^)\s]+)\)/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    pushText(blocks, text.slice(last, match.index));
    if (match[2] !== undefined) blocks.push({ kind: "code", lang: match[1] || undefined, text: match[2].replace(/\n$/, "") });
    else if (match[3] !== undefined) blocks.push({ kind: "formula", text: match[3].trim() });
    else if (safeImage(match[5])) blocks.push({ kind: "image", alt: match[4], src: match[5] });
    last = (match.index ?? 0) + match[0].length;
  }
  pushText(blocks, text.slice(last));
  return blocks;
}

function pushText(blocks: Block[], text: string) {
  for (const paragraph of text.split(/\n{2,}/)) {
    const clean = paragraph.trim();
    if (clean) blocks.push({ kind: "text", text: clean });
  }
}

function safeImage(src: string): boolean {
  return src.startsWith("/") || /^https:\/\//.test(src);
}
