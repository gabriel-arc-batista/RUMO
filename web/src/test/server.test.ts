import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { uuid } from "../lib/ids";
import type { Envelope } from "../service/contract";
import { testBackend } from "./helpers";

const device = uuid();
const attempt = (question: string, answer: string): Envelope => {
  const id = uuid();
  return {
    id,
    device_id: device,
    kind: "arena.attempt",
    entity_id: id,
    base_revision: 0,
    payload: { question_id: question, version: "1.0.0", answer, session_id: uuid() },
  };
};
const review = (card: string, rating: 1 | 2 | 3 | 4): Envelope => {
  const id = uuid();
  return {
    id,
    device_id: device,
    kind: "card.review",
    entity_id: id,
    base_revision: 0,
    payload: { card_id: card, version: "1.0.0", rating, session_id: uuid() },
  };
};

describe("servidor de exemplo segue as regras do serviço", () => {
  it("corrige pela chave privada e devolve gabarito e explicação", async () => {
    const { server } = testBackend();
    await server.push([attempt("exemplo.q.left-join", "c"), attempt("exemplo.q.left-join", "d"), attempt("exemplo.q.anulada", "certo")]);
    const results = (await server.pull(0)).map((e) => e.result);
    expect(results.map((r) => r?.status)).toEqual(["correct", "incorrect", "annulled"]);
    expect(results[1]?.answer).toBe("c");
    expect(String(results[1]?.comment)).toContain("Total: 8");
  });

  it("recusa alternativa inexistente", async () => {
    const { server } = testBackend();
    await expect(server.push([attempt("exemplo.q.fk", "z")])).rejects.toMatchObject({ code: "invalid_answer" });
  });

  it("agenda SM-2 adaptado como FLASHCARDS.md: 1, 6, 15 dias; Errei volta em 1", async () => {
    const { server } = testBackend();
    const card = "exemplo.c.inner";
    for (const rating of [3, 3, 3, 1] as const) await server.push([review(card, rating)]);
    const results = (await server.pull(0)).map((e) => e.result as { interval_days: number; repetitions: number });
    expect(results.map((r) => r.interval_days)).toEqual([1, 6, 15, 1]);
    expect(results[3].repetitions).toBe(0);
  });

  it("o mesmo evento reenviado não conta duas revisões", async () => {
    const { server } = testBackend();
    const event = review("exemplo.c.left", 4);
    await server.push([event]);
    await server.push([event]);
    expect(await server.pull(0)).toHaveLength(1);
    await expect(server.push([{ ...event, payload: { ...event.payload, rating: 1 } } as Envelope])).rejects.toMatchObject({ code: "event_mismatch" });
  });

  it("XP vem do tempo líquido da sessão e o nível segue a regra do app", async () => {
    const { server } = testBackend();
    const id = uuid();
    await server.push([
      {
        id,
        device_id: device,
        kind: "study.session",
        entity_id: id,
        base_revision: 0,
        payload: { plan_id: "site", subject_id: "subject.bancos-dados", topic_id: null, day: "2026-10-12", category: "Questões", elapsed: 9000, lesson_id: null, lesson_version: null },
      },
    ]);
    const [event] = await server.pull(0);
    expect(event.result).toEqual({ xp: 150, coins: 15 });
    expect(await server.progressSummary()).toEqual({ level: 2, xp: 50, xp_next: 200, coins: 15, look: null });
  });
});
