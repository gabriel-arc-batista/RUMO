/**
 * Servidor SIMULADO do modo exemplo. Roda neste navegador e reproduz as regras
 * de backend/migrations/001_sync.sql (idempotência por id, CAS por entidade,
 * correção, agenda SM-2 adaptada e XP por minuto) para que o site se comporte
 * igual com o serviço real. Não é usado quando o serviço está configurado.
 */
import { getAll, getMeta, openDb, write } from "../../lib/idb";
import type { Account, Auth, Backend } from "../backend";
import type { Envelope, ServerEvent } from "../contract";
import { EXAMPLE_ANSWERS, EXAMPLE_CATALOG } from "./catalog";

class ExampleError extends Error {
  constructor(public code: string) {
    super(code);
  }
}

interface EntityRow {
  revision: number;
  payload: Record<string, unknown>;
}
interface ScheduleRow {
  repetitions: number;
  interval: number;
  ease: number;
  reviewedAt: string;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const REQUIRED: Record<string, string[]> = {
  "reading.page": ["lesson_id", "version", "page", "pages", "read"],
  "reading.position": ["lesson_id", "version", "page", "pages"],
  "note.save": ["lesson_id", "version", "page", "text", "deleted"],
  "favorite.set": ["target_type", "target_id", "version", "favorite"],
  "arena.attempt": ["question_id", "version", "answer", "session_id"],
  "card.save": ["deck_id", "front", "back", "explanation", "source", "lesson_id", "question_id", "suspended", "deleted"],
  "card.review": ["card_id", "version", "rating", "session_id"],
  "study.session": ["plan_id", "subject_id", "topic_id", "day", "category", "elapsed", "lesson_id", "lesson_version"],
};
const CATEGORIES = ["Teoria", "Questões", "Revisão", "Simulado"];
const VERSION = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const FAVORITE_TYPES = ["lesson", "question", "card", "deck", "bookmark"];

function same(a: unknown, b: unknown) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export class ExampleServer {
  private offline = false;
  private dbPromise: Promise<IDBDatabase>;

  constructor(userId: string) {
    this.dbPromise = openDb(`rumo-exemplo-servidor:${userId}`);
  }

  setOffline(value: boolean) {
    this.offline = value;
  }

  private async network() {
    await sleep(220);
    if (this.offline) throw new TypeError("Failed to fetch (simulado)");
  }

  async pull(after: number): Promise<ServerEvent[]> {
    await this.network();
    const db = await this.dbPromise;
    const events = await getAll<ServerEvent>(db, "events");
    return events.filter((e) => e.sequence > after).sort((a, b) => a.sequence - b.sequence).slice(0, 200);
  }

  /** Mesmo cálculo de progress_summary() (004_frontend_catalog.sql): nível L pede 100×L XP. */
  async progressSummary() {
    await this.network();
    const db = await this.dbPromise;
    const entities = (await getMeta<Record<string, EntityRow>>(db, "entities")) ?? {};
    let xp = 0;
    let coins = 0;
    for (const [key, row] of Object.entries(entities)) {
      if (!key.startsWith("study.session|")) continue;
      const elapsed = Number(row.payload.elapsed) || 0;
      xp += Math.floor(elapsed / 60);
      coins += Math.floor(elapsed / 600);
    }
    let level = 1;
    while (50 * level * (level + 1) <= xp) level += 1;
    return { level, xp: xp - 50 * (level - 1) * level, xp_next: 100 * level, coins, look: null };
  }

  async push(batch: Envelope[]): Promise<{ id: string; sequence: number }[]> {
    await this.network();
    if (batch.length > 100) throw new ExampleError("invalid_event");
    const db = await this.dbPromise;
    const events = await getAll<ServerEvent>(db, "events");
    const entities = (await getMeta<Record<string, EntityRow>>(db, "entities")) ?? {};
    const schedules = (await getMeta<Record<string, ScheduleRow>>(db, "schedules")) ?? {};
    let sequence = (await getMeta<number>(db, "sequence")) ?? 0;
    const byId = new Map(events.map((e) => [e.id, e]));
    const accepted: { id: string; sequence: number }[] = [];
    const created: ServerEvent[] = [];

    for (const e of batch) {
      const old = byId.get(e.id);
      if (old) {
        const changed =
          old.device_id !== e.device_id || old.kind !== e.kind || old.entity_id !== e.entity_id ||
          old.base_revision !== e.base_revision || !same(old.payload, e.payload);
        if (changed) throw new ExampleError("event_mismatch");
        accepted.push({ id: e.id, sequence: old.sequence });
        continue;
      }
      const key = `${e.kind}|${e.entity_id}`;
      const revision = entities[key]?.revision ?? 0;
      if (revision !== e.base_revision) throw new ExampleError("revision_conflict");
      if ((e.kind === "arena.attempt" || e.kind === "card.review") && revision !== 0) throw new ExampleError("revision_conflict");
      const payload = e.payload as unknown as Record<string, unknown>;
      if (!REQUIRED[e.kind]?.every((field) => field in payload)) throw new ExampleError("invalid_event");
      // Mesmas regras de 001_sync.sql: versão opaca e favorito com identidade canônica.
      const version = payload.version;
      if ("version" in payload && !(e.kind === "favorite.set" && version === "") && (typeof version !== "string" || !VERSION.test(version))) {
        throw new ExampleError("invalid_event");
      }
      const result = this.evaluate(e, entities, schedules);
      sequence += 1;
      const stored: ServerEvent = {
        ...e,
        sequence,
        revision: revision + 1,
        received_at: new Date().toISOString(),
        result,
      } as ServerEvent;
      entities[key] = { revision: revision + 1, payload };
      byId.set(e.id, stored);
      created.push(stored);
      accepted.push({ id: e.id, sequence });
    }

    await write(db, ["events", "meta"], (tx) => {
      const store = tx.objectStore("events");
      for (const e of created) store.put(e);
      const meta = tx.objectStore("meta");
      meta.put(entities, "entities");
      meta.put(schedules, "schedules");
      meta.put(sequence, "sequence");
    });
    return accepted;
  }

  private evaluate(
    e: Envelope,
    entities: Record<string, EntityRow>,
    schedules: Record<string, ScheduleRow>,
  ): Record<string, unknown> | null {
    const catalog = EXAMPLE_CATALOG;
    switch (e.kind) {
      case "note.save": {
        // Exatamente uma origem: aula (página opcional) ou questão (página nula).
        const question = e.payload.question_id ?? null;
        if (Boolean(question) === Boolean(e.payload.lesson_id)) throw new ExampleError("invalid_event");
        if (question) {
          if (e.payload.page !== null) throw new ExampleError("invalid_event");
          if (!catalog.questions.some((q) => q.id === question && q.version === e.payload.version)) throw new ExampleError("content_unavailable");
          return null;
        }
        return this.lessonCheck(e.payload.lesson_id, e.payload.version, e.payload.page);
      }
      case "favorite.set": {
        const { target_type, target_id, version, favorite } = e.payload;
        if (!FAVORITE_TYPES.includes(target_type) || typeof favorite !== "boolean") throw new ExampleError("invalid_event");
        if (e.entity_id !== `${target_type}:${target_id}:${version}:favorite`) throw new ExampleError("invalid_event");
        return null;
      }
      case "reading.page":
      case "reading.position":
        return this.lessonCheck(e.payload.lesson_id, e.payload.version, e.payload.page);
      case "arena.attempt": {
        const q = catalog.questions.find((x) => x.id === e.payload.question_id && x.version === e.payload.version);
        if (!q) throw new ExampleError("content_unavailable");
        if (!q.options.some((o) => o.id === e.payload.answer)) throw new ExampleError("invalid_answer");
        const key = EXAMPLE_ANSWERS[q.id];
        const status = q.annulled ? "annulled" : key.answer === e.payload.answer ? "correct" : "incorrect";
        return { status, answer: key.answer, comment: key.comment };
      }
      case "card.save":
        if (!e.payload.front.trim() || !e.payload.back.trim()) throw new ExampleError("invalid_event");
        return null;
      case "card.review":
        return this.review(e.payload, entities, schedules);
      case "study.session":
        if (!CATEGORIES.includes(e.payload.category)) throw new ExampleError("invalid_event");
        if (e.payload.elapsed < 0 || e.payload.elapsed > 86_400) throw new ExampleError("invalid_event");
        if ((e.payload.lesson_id === null) !== (e.payload.lesson_version === null)) throw new ExampleError("invalid_event");
        return { xp: Math.floor(e.payload.elapsed / 60), coins: Math.floor(e.payload.elapsed / 600) };
      default:
        return null;
    }
  }

  private lessonCheck(lessonId: string | null, version: string, page: number | null) {
    const lesson = EXAMPLE_CATALOG.lessons.find((l) => l.id === lessonId && l.version === version);
    if (!lesson || !lesson.pages) throw new ExampleError("content_unavailable");
    if (page !== null && (page < 1 || page > lesson.pages)) throw new ExampleError("invalid_event");
    return null;
  }

  /** Mesma fórmula de 001_sync.sql (SM-2 adaptado, FLASHCARDS.md). */
  private review(
    p: { card_id: string; version: string; rating: number },
    entities: Record<string, EntityRow>,
    schedules: Record<string, ScheduleRow>,
  ) {
    const personal = entities[`card.save|${p.card_id}`];
    if (personal) {
      if (String(personal.revision) !== p.version) throw new ExampleError("content_unavailable");
      if (personal.payload.suspended || personal.payload.deleted) throw new ExampleError("card_suspended");
    } else if (!EXAMPLE_CATALOG.cards.some((c) => c.id === p.card_id && c.version === p.version)) {
      throw new ExampleError("content_unavailable");
    }
    const key = `${p.card_id}:${p.version}`;
    const previous =
      schedules[key] ??
      Object.entries(schedules)
        .filter(([k]) => k.startsWith(`${p.card_id}:`))
        .map(([, v]) => v)
        .sort((a, b) => b.reviewedAt.localeCompare(a.reviewedAt))[0];
    let n = previous?.repetitions ?? 0;
    const ease = previous?.ease ?? 2.5;
    const quality = [0, 1, 3, 4, 5][p.rating];
    let days: number;
    if (p.rating === 1) {
      n = 0;
      days = 1;
    } else {
      n += 1;
      days = n === 1 ? 1 : n === 2 ? 6 : Math.max(1, Math.floor((previous?.interval ?? 0) * ease + 0.5));
    }
    const nextEase = Math.round(Math.max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)) * 10_000) / 10_000;
    const now = new Date();
    schedules[key] = { repetitions: n, interval: days, ease: nextEase, reviewedAt: now.toISOString() };
    const due = new Date(now.getTime() + days * 86_400_000).toISOString();
    return { interval_days: days, repetitions: n, ease: nextEase, due_at: due };
  }
}

const ACCOUNT_KEY = "rumo.exemplo.conta";

class ExampleAuth implements Auth {
  private listeners = new Set<(a: Account | null) => void>();

  private read(): Account | null {
    try {
      const raw = localStorage.getItem(ACCOUNT_KEY);
      return raw ? (JSON.parse(raw) as Account) : null;
    } catch {
      return null;
    }
  }

  private set(account: Account | null) {
    try {
      if (account) localStorage.setItem(ACCOUNT_KEY, JSON.stringify(account));
      else localStorage.removeItem(ACCOUNT_KEY);
    } catch {
      /* sem armazenamento: conta só nesta aba */
    }
    this.listeners.forEach((l) => l(account));
  }

  async current() {
    return this.read();
  }

  onChange(listener: (a: Account | null) => void) {
    this.listeners.add(listener);
    return () => void this.listeners.delete(listener);
  }

  async signIn(email: string, password: string) {
    await sleep(300);
    if (password.length < 8) throw Object.assign(new Error("Senha incorreta."), { code: "invalid_credentials" });
    const userId = `exemplo-${email.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
    this.set({ userId, email: email.trim() });
  }

  async signUp(email: string, password: string) {
    await this.signIn(email, password);
    return { needsConfirmation: false };
  }

  async signOut() {
    this.set(null);
  }

  async requestReset() {
    await sleep(300);
  }

  async updatePassword() {
    await sleep(300);
  }

  isRecovery() {
    return location.pathname.endsWith("/nova-senha");
  }
}

export function createExampleBackend(): Backend {
  const auth = new ExampleAuth();
  const servers = new Map<string, ExampleServer>();
  const KEY = "rumo.exemplo.offline";
  let offline = (() => {
    try {
      return sessionStorage.getItem(KEY) === "1";
    } catch {
      return false;
    }
  })();
  const server = async (expectedUser?: string) => {
    const account = await auth.current();
    if (!account || (expectedUser && account.userId !== expectedUser)) throw new ExampleError("unauthenticated");
    let s = servers.get(account.userId);
    if (!s) {
      s = new ExampleServer(account.userId);
      servers.set(account.userId, s);
    }
    s.setOffline(offline);
    return s;
  };
  const backend: Backend = {
    mode: "exemplo",
    auth,
    async loadCatalog() {
      await sleep(250);
      return EXAMPLE_CATALOG;
    },
    push: async (events) => (await server()).push(events),
    pull: async (after) => (await server()).pull(after),
    progressSummary: async () => (await server()).progressSummary(),
    simulateOffline(value) {
      offline = value;
      try {
        sessionStorage.setItem(KEY, value ? "1" : "0");
      } catch {
        /* só nesta página */
      }
      servers.forEach((s) => s.setOffline(value));
    },
    isSimulatedOffline: () => offline,
  };
  backend.forAccount = (userId) => ({ ...backend,
    push: async (events) => (await server(userId)).push(events),
    pull: async (after) => (await server(userId)).pull(after),
    progressSummary: async () => (await server(userId)).progressSummary(),
  });
  return backend;
}
