/**
 * Projeção local: aplica os eventos aceitos pelo serviço (em ordem de
 * sequência) e, por cima, os que ainda esperam na fila deste navegador.
 * Resultados (correção, agenda, XP) são lidos de `result`; nada é recalculado.
 */
import { entity, type Envelope, type EventKind, type FavoriteType, type Payloads, type ServerEvent } from "../service/contract";
import type { AttemptResult, ReviewResult, SessionResult } from "./types";

export type Origin = "server" | "pending";

export interface PageMark {
  read: boolean;
  origin: Origin;
}

export interface ReadingState {
  lessonId: string;
  version: string;
  pages: number;
  marks: Map<number, PageMark>;
  position: { page: number; at: string; origin: Origin } | null;
}

export interface NoteState {
  id: string;
  lessonId: string | null;
  questionId: string | null;
  version: string;
  page: number | null;
  text: string;
  deleted: boolean;
  at: string;
  origin: Origin;
}

export interface AttemptState {
  id: string;
  questionId: string;
  version: string;
  answer: string;
  sessionId: string;
  at: string;
  result: AttemptResult | null;
  origin: Origin;
}

export interface PersonalCardState {
  id: string;
  payload: Payloads["card.save"];
  at: string;
  origin: Origin;
}

export interface ReviewState {
  id: string;
  cardId: string;
  version: string;
  rating: number;
  sessionId: string;
  at: string;
  result: ReviewResult | null;
  origin: Origin;
}

export interface SessionState {
  id: string;
  payload: Payloads["study.session"];
  at: string;
  result: SessionResult | null;
  origin: Origin;
}

export interface Projection {
  /** Revisão conhecida no serviço por `${kind}|${entity}` (base do próximo evento). */
  revisions: Map<string, number>;
  reading: Map<string, ReadingState>;
  notes: Map<string, NoteState>;
  favorites: Map<string, { favorite: boolean; origin: Origin }>;
  attempts: Map<string, AttemptState>;
  cards: Map<string, PersonalCardState>;
  reviews: ReviewState[];
  sessions: Map<string, SessionState>;
}

export interface PendingEvent {
  envelope: Envelope;
  createdAt: string;
}

export const readingKey = (lessonId: string, version: string) => `${lessonId}@${version}`;
export const revisionKey = (kind: EventKind, entityId: string) => `${kind}|${entityId}`;

function emptyProjection(): Projection {
  return {
    revisions: new Map(),
    reading: new Map(),
    notes: new Map(),
    favorites: new Map(),
    attempts: new Map(),
    cards: new Map(),
    reviews: [],
    sessions: new Map(),
  };
}

function readingFor(p: Projection, lessonId: string, version: string, pages: number) {
  const key = readingKey(lessonId, version);
  let state = p.reading.get(key);
  if (!state) {
    state = { lessonId, version, pages, marks: new Map(), position: null };
    p.reading.set(key, state);
  }
  state.pages = pages || state.pages;
  return state;
}

function apply(p: Projection, e: Envelope, at: string, origin: Origin, result: unknown) {
  switch (e.kind) {
    case "reading.page": {
      const { lesson_id, version, page, pages, read } = e.payload;
      if (!lesson_id) break;
      readingFor(p, lesson_id, version, pages).marks.set(page, { read, origin });
      break;
    }
    case "reading.position": {
      const { lesson_id, version, page, pages } = e.payload;
      readingFor(p, lesson_id, version, pages).position = { page, at, origin };
      break;
    }
    case "note.save": {
      const { lesson_id, version, page, text, deleted } = e.payload;
      const questionId = e.payload.question_id ?? null;
      p.notes.set(e.entity_id, { id: e.entity_id, lessonId: lesson_id, questionId, version, page, text, deleted, at, origin });
      break;
    }
    case "favorite.set":
      p.favorites.set(e.entity_id, { favorite: e.payload.favorite, origin });
      break;
    case "arena.attempt": {
      const { question_id, version, answer, session_id } = e.payload;
      p.attempts.set(e.entity_id, {
        id: e.entity_id,
        questionId: question_id,
        version,
        answer,
        sessionId: session_id,
        at,
        result: (result as AttemptResult) ?? null,
        origin,
      });
      break;
    }
    case "card.save":
      p.cards.set(e.entity_id, { id: e.entity_id, payload: e.payload, at, origin });
      break;
    case "card.review": {
      const { card_id, version, rating, session_id } = e.payload;
      p.reviews.push({
        id: e.entity_id,
        cardId: card_id,
        version,
        rating,
        sessionId: session_id,
        at,
        result: (result as ReviewResult) ?? null,
        origin,
      });
      break;
    }
    case "study.session":
      p.sessions.set(e.entity_id, {
        id: e.entity_id,
        payload: e.payload,
        at,
        result: (result as SessionResult) ?? null,
        origin,
      });
      break;
  }
}

export function project(server: ServerEvent[], pending: PendingEvent[]): Projection {
  const p = emptyProjection();
  const ordered = [...server].sort((a, b) => a.sequence - b.sequence);
  for (const e of ordered) {
    p.revisions.set(revisionKey(e.kind, e.entity_id), e.revision);
    apply(p, e, e.received_at, "server", e.result ?? null);
  }
  const seen = new Set(ordered.map((e) => e.id));
  for (const item of pending) {
    if (!seen.has(item.envelope.id)) apply(p, item.envelope, item.createdAt, "pending", null);
  }
  return p;
}

/* ---------- Leituras derivadas usadas pelas telas ---------- */

export function readPages(state: ReadingState | undefined): number[] {
  if (!state) return [];
  return [...state.marks.entries()].filter(([, m]) => m.read).map(([page]) => page);
}

/** Concluída só quando todas as páginas 1..N estão marcadas (contrato). */
export function isComplete(state: ReadingState | undefined, pages: number | null): boolean {
  if (!state || !pages) return false;
  for (let page = 1; page <= pages; page += 1) {
    if (!state.marks.get(page)?.read) return false;
  }
  return true;
}

const DAY = 86_400_000;

/** Próximo vencimento: `received_at` + dias de `interval_days` (FLASHCARDS.md). */
export function scheduleFor(p: Projection, cardId: string, version: string) {
  const history = p.reviews.filter((r) => r.cardId === cardId);
  const reviews = history.filter((r) => r.version === version);
  const confirmed = reviews.filter((r) => r.origin === "server" && r.result);
  // O serviço herda a agenda anterior até a primeira revisão desta versão.
  const last = confirmed.at(-1) ?? history.filter((r) => r.origin === "server" && r.result).at(-1);
  const pending = reviews.some((r) => r.origin === "pending");
  if (!last) return { dueAt: null as string | null, reviews: reviews.length, pending, last: null };
  const result = last.result as ReviewResult & { due_at?: string };
  const due = result.due_at ?? new Date(new Date(last.at).getTime() + result.interval_days * DAY).toISOString();
  return { dueAt: due, reviews: reviews.length, pending, last };
}

export function attemptsFor(p: Projection, questionId: string): AttemptState[] {
  return [...p.attempts.values()]
    .filter((a) => a.questionId === questionId)
    .sort((a, b) => a.at.localeCompare(b.at));
}

/** Favorito pela identidade canônica (versão vazia = favorito global). */
export function isFavorite(p: Projection, type: FavoriteType, id: string, version = ""): boolean {
  return p.favorites.get(entity.favorite(type, id, version))?.favorite ?? false;
}
