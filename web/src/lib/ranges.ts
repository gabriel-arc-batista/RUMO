/** [1,2,3,5] → "1-3, 5". */
export function pageRanges(pages: number[]): string {
  const sorted = [...new Set(pages)].sort((a, b) => a - b);
  const parts: string[] = [];
  let start: number | null = null;
  let prev = 0;
  for (const page of sorted) {
    if (start === null) start = prev = page;
    else if (page === prev + 1) prev = page;
    else {
      parts.push(start === prev ? `${start}` : `${start}-${prev}`);
      start = prev = page;
    }
  }
  if (start !== null) parts.push(start === prev ? `${start}` : `${start}-${prev}`);
  return parts.join(", ");
}

/** "1-3, 5" → [1,2,3,5]; recusa páginas fora de 1..limit (mesma regra do app). */
export function parseRanges(text: string, limit: number): number[] {
  const chosen = new Set<number>();
  for (const raw of text.replace(/;/g, ",").split(",")) {
    const part = raw.trim();
    if (!part) continue;
    const bounds = part.split("-").map((b) => b.trim());
    if (bounds.length > 2 || !bounds.every((b) => /^\d+$/.test(b))) throw new Error(`Intervalo inválido: ${part}`);
    const first = Number(bounds[0]);
    const last = Number(bounds[bounds.length - 1]);
    if (!(first >= 1 && first <= last && last <= limit)) throw new Error(`Páginas fora desta versão (1 a ${limit}): ${part}`);
    for (let p = first; p <= last; p += 1) chosen.add(p);
  }
  if (!chosen.size) throw new Error("Informe ao menos uma página.");
  return [...chosen].sort((a, b) => a - b);
}
