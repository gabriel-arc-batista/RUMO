import { describe, expect, it } from "vitest";
import { parseStatement } from "../domain/blocks";
import { parseImport } from "../pages/cards/ImportExport";

describe("enunciado", () => {
  it("separa texto, código, fórmula e imagem segura", () => {
    const blocks = parseStatement("Veja:\n\n```sql\nSELECT 1;\n```\n\n$$T(n) = 2T(n/2)$$\n\n![diagrama](https://exemplo.org/a.png)\n\n![x](javascript:alert(1))");
    expect(blocks.map((b) => b.kind)).toEqual(["text", "code", "formula", "image", "text"]);
    expect(blocks[1]).toMatchObject({ kind: "code", lang: "sql", text: "SELECT 1;" });
  });
});

describe("importação de cartões", () => {
  const file = (cards: unknown[]) => JSON.stringify({ format: "RUMO-personal-cards", version: 1, cards });

  it("gera rascunhos novos sem id/revisão e ignora cartões incompletos", () => {
    const { drafts, skipped } = parseImport(
      file([
        { id: "x", revision: 3, deck_id: "pessoal:subject.bancos-dados", front: "F", back: "V" },
        { front: "", back: "sem frente" },
        { front: "excluído", back: "v", deleted: true },
      ]),
    );
    expect(drafts).toHaveLength(1);
    expect(drafts[0]).not.toHaveProperty("id");
    expect(drafts[0].deck_id).toBe("pessoal:subject.bancos-dados");
    expect(skipped).toBe(2);
  });

  it("recusa formato desconhecido e excesso de cartões", () => {
    expect(() => parseImport(JSON.stringify({ format: "outro", version: 1, cards: [] }))).toThrow();
    expect(() => parseImport(file(Array.from({ length: 1001 }, () => ({ front: "a", back: "b" }))))).toThrow(/1000/);
  });

  it("decks de terceiros viram deck pessoal geral", () => {
    const { drafts } = parseImport(file([{ deck_id: "publicado.x", front: "a", back: "b" }]));
    expect(drafts[0].deck_id).toBe("pessoal:geral");
  });
});

describe("configuração do serviço", () => {
  it("recusa chave secreta ou service_role antes de criar o cliente", async () => {
    const { createSupabaseBackend } = await import("../service/supabase");
    expect(() => createSupabaseBackend("https://exemplo.supabase.co", "sb_secret_abc")).toThrow(/chave pública/);
    const role = btoa(JSON.stringify({ role: "service_role" })).replace(/=+$/, "");
    expect(() => createSupabaseBackend("https://exemplo.supabase.co", `x.${role}.y`)).toThrow(/chave pública/);
  });
});
