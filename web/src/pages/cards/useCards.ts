import { useMemo } from "react";
import { scheduleFor, type Projection } from "../../domain/projection";
import type { Card, Catalog, Deck } from "../../domain/types";
import { useRumo } from "../../service/store";

export const PERSONAL_PREFIX = "pessoal:";

export interface CardView {
  card: Card;
  dueAt: string | null;
  reviews: number;
  reviewPending: boolean;
  /** Cartão pessoal ainda não aceito pelo serviço: não pode ser revisado. */
  unsynced: boolean;
  status: "novo" | "vencido" | "agendado" | "suspenso";
}

/** Cartões pessoais vêm da projeção; a versão é a revisão aceita pelo serviço (contrato). */
export function personalCards(p: Projection): { card: Card; unsynced: boolean }[] {
  return [...p.cards.values()]
    .filter((c) => !c.payload.deleted)
    .map((c) => {
      const revision = p.revisions.get(`card.save|${c.id}`) ?? 0;
      return {
        unsynced: c.origin === "pending",
        card: {
          id: c.id,
          version: String(revision),
          deckId: c.payload.deck_id,
          front: c.payload.front,
          back: c.payload.back,
          explanation: c.payload.explanation,
          source: c.payload.source,
          lessonId: c.payload.lesson_id,
          questionId: c.payload.question_id,
          suspended: c.payload.suspended,
          deleted: false,
          personal: true,
          example: false,
        },
      };
    });
}

export function personalDecks(catalog: Catalog, cards: Card[]): Deck[] {
  const ids = new Set(cards.filter((c) => c.personal).map((c) => c.deckId));
  return [...ids].map((id) => {
    const subjectId = id.slice(PERSONAL_PREFIX.length);
    const subject = catalog.subjects.find((s) => s.id === subjectId);
    return {
      id,
      title: subject ? `Meus cartões — ${subject.name}` : "Meus cartões",
      description: "Cartões criados por você.",
      subjectId: subject?.id ?? null,
      topicId: null,
      personal: true,
      example: false,
    };
  });
}

export function buildViews(catalog: Catalog, p: Projection, now = Date.now()): { views: CardView[]; decks: Deck[] } {
  const personal = personalCards(p);
  const all = [...catalog.cards.map((card) => ({ card, unsynced: false })), ...personal];
  const views = all.map(({ card, unsynced }) => {
    const s = scheduleFor(p, card.id, card.version);
    const lastResult = s.last?.result as { due_at?: string } | null | undefined;
    const dueAt = lastResult?.due_at ?? s.dueAt;
    let status: CardView["status"] = "agendado";
    if (card.suspended) status = "suspenso";
    else if (!dueAt && !s.reviews) status = "novo";
    else if (dueAt && new Date(dueAt).getTime() <= now && !s.pending) status = "vencido";
    return { card, dueAt, reviews: s.reviews, reviewPending: s.pending, unsynced, status };
  });
  const decks = [...catalog.decks, ...personalDecks(catalog, all.map((a) => a.card))];
  return { views, decks };
}

export function useCardViews() {
  const { catalog, sync } = useRumo();
  return useMemo(() => {
    if (catalog.status !== "ready" || !sync) return null;
    return buildViews(catalog.catalog, sync.projection);
  }, [catalog, sync]);
}

export function useDueCount(): number {
  const data = useCardViews();
  return data ? data.views.filter((v) => v.status === "vencido").length : 0;
}
