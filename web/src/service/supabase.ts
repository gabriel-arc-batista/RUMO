/**
 * Serviço real: Supabase Auth + RPC versionada (docs/integration/CONTRACT.md).
 * O site nunca grava em tabelas privadas: só `push_events`/`pull_events` com o
 * token do usuário e a chave pública. Não há service_role no frontend.
 */
import { createClient, type Session, type SupabaseClient } from "@supabase/supabase-js";
import { RumoApi, RumoApiError, validatePublicKey } from "@shared/rumo-api";
import { parseStatement } from "../domain/blocks";
import type { Card, Catalog, Deck, Exam, Lesson, Question, Subject, Topic } from "../domain/types";
import type { Account, Auth, Backend } from "./backend";
import type { Envelope, ServerEvent } from "./contract";

import { collectPages } from "./pagination";

type Row = Record<string, unknown>;

const str = (v: unknown, fallback = "") => (typeof v === "string" ? v : fallback);
const num = (v: unknown, fallback = 0) => (typeof v === "number" ? v : Number(v) || fallback);
const list = <T = string>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);

function toAccount(session: Session | null): Account | null {
  return session ? { userId: session.user.id, email: session.user.email ?? "" } : null;
}

class SupabaseAuth implements Auth {
  private session: Session | null = null;
  private recovery = false;
  private ready: Promise<void>;

  constructor(private client: SupabaseClient) {
    this.ready = client.auth.getSession().then(({ data }) => {
      this.session = data.session;
    });
    client.auth.onAuthStateChange((event, session) => {
      this.session = session;
      if (event === "PASSWORD_RECOVERY") this.recovery = true;
    });
  }

  token = () => this.session?.access_token ?? null;

  tokenFor = (userId: string) => {
    if (this.session?.user.id !== userId) throw new RumoApiError("unauthenticated", 401, "Entre na sua conta.");
    return this.session.access_token;
  };

  async current() {
    await this.ready;
    return toAccount(this.session);
  }

  onChange(listener: (account: Account | null) => void) {
    const { data } = this.client.auth.onAuthStateChange((_e, session) => listener(toAccount(session)));
    return () => data.subscription.unsubscribe();
  }

  async signIn(email: string, password: string) {
    const { error } = await this.client.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }

  async signUp(email: string, password: string) {
    const { data, error } = await this.client.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${location.origin}/conta` },
    });
    if (error) throw error;
    return { needsConfirmation: !data.session };
  }

  async signOut() {
    const { error } = await this.client.auth.signOut();
    if (error) throw error;
  }

  async requestReset(email: string) {
    const { error } = await this.client.auth.resetPasswordForEmail(email, {
      redirectTo: `${location.origin}/conta/nova-senha`,
    });
    if (error) throw error;
  }

  async updatePassword(password: string) {
    const { error } = await this.client.auth.updateUser({ password });
    if (error) throw error;
    this.recovery = false;
  }

  isRecovery() {
    return this.recovery || location.hash.includes("type=recovery");
  }
}

async function optionalTable(client: SupabaseClient, table: string): Promise<Row[]> {
  return collectPages<Row>((from, to) => client.from(table).select("*").order("id").range(from, to));
}

const version = (v: unknown) => (v == null ? "" : String(v));

/**
 * PDF da aula: `pdf_url` (publicada e revisada) ou, só para conteúdo de EXEMPLO,
 * `resource.url` — o SQL não deixa exemplo usar `pdf_url` sem revisão aprovada.
 */
function lessonPdf(r: Row): string | null {
  const url = str(r.pdf_url) || (r.example === true ? str((r.resource as Row | null)?.url) : "");
  if (!url) return null;
  try {
    const parsed = new URL(url, location.origin);
    const local = ["localhost", "127.0.0.1"].includes(parsed.hostname);
    return parsed.protocol === "https:" || (local && parsed.protocol === "http:") ? parsed.href : null;
  } catch {
    return null;
  }
}

function mapLesson(r: Row): Lesson {
  const pdfUrl = lessonPdf(r);
  const v = version(r.version);
  return {
    id: str(r.id),
    version: v,
    versionLabel: str(r.version_label) || `versão ${v}`,
    title: str(r.title),
    summary: str(r.summary),
    subjectId: str(r.subject_id, "sem-materia"),
    topicIds: list(r.topic_ids),
    examIds: list(r.exam_ids),
    // Só "publicada" com PDF abre no leitor; o resto é planejado (004_frontend_catalog.sql).
    status: (r.status === "publicada" || r.example === true) && pdfUrl ? "disponivel" : "planejada",
    objectives: list(r.objectives),
    prerequisiteTopicIds: list(r.prerequisite_topic_ids),
    sources: list(r.sources),
    review: mapReview(r.review),
    pages: r.pages == null ? null : num(r.pages),
    pdfUrl,
    outline: list(r.outline),
    example: r.example === true,
  };
}

function mapReview(raw: unknown): Lesson["review"] {
  const r = (raw ?? {}) as Record<string, unknown>;
  const status = r.status === "aprovada" || r.status === "em_revisao" ? r.status : "pendente";
  return { status, reviewer: str(r.reviewer) || null, reviewedAt: str(r.reviewed_at) || null };
}

function mapQuestion(r: Row): Question {
  const raw = (r.options ?? {}) as Record<string, string>;
  const options = Object.entries(raw).map(([id, text]) => ({ id, text: String(text) }));
  const p = (r.provenance ?? {}) as Record<string, unknown>;
  const year = Number(p.year);
  return {
    id: str(r.id),
    version: version(r.version),
    type: r.type === "certo-errado" ? "certo_errado" : "multipla_escolha",
    statement: parseStatement(str(r.prompt)),
    options,
    subjectId: str(r.subject_id, "sem-materia"),
    topicIds: list(r.topic_ids),
    examIds: list(r.exam_ids),
    provenance: {
      kind: p.kind === "banca" ? "banca" : "autoral",
      label: str(p.label) || [str(p.bank), str(p.year)].filter(Boolean).join(" · ") || "Procedência no catálogo",
      bank: str(p.bank) || undefined,
      year: Number.isFinite(year) && year > 0 ? year : undefined,
    },
    annulled: r.annulled === true,
    example: r.example === true,
  };
}

function mapCard(r: Row): Card {
  return {
    id: str(r.id),
    version: version(r.version),
    deckId: str(r.deck_id, "publicados"),
    front: str(r.front),
    back: str(r.back),
    explanation: str(r.explanation),
    source: str(r.source),
    lessonId: str(r.lesson_id) || null,
    questionId: str(r.question_id) || null,
    suspended: false,
    deleted: false,
    personal: false,
    example: r.example === true,
  };
}

/**
 * Versões são opacas: a mais recente de cada id é a de maior `catalog_revision`
 * (ordem editorial do servidor, 006_catalog_order.sql). Antigas ficam no histórico.
 */
function latest<T extends { id: string }>(rows: Row[], map: (r: Row) => T): T[] {
  const byId = new Map<string, { rev: number; item: T }>();
  for (const row of rows) {
    const item = map(row);
    const rev = num(row.catalog_revision, 0);
    const current = byId.get(item.id);
    if (!current || rev >= current.rev) byId.set(item.id, { rev, item });
  }
  return [...byId.values()].map((x) => x.item);
}

export function createSupabaseBackend(url: string, publicKey: string): Backend {
  // Falha cedo: chaves sb_secret_/service_role nunca podem chegar ao navegador.
  validatePublicKey(publicKey);
  let auth: SupabaseAuth;
  // Valida também a origem antes que Auth possa abrir uma conexão.
  const api = new RumoApi(url, publicKey, () => auth.token());
  const client = createClient(url, publicKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  auth = new SupabaseAuth(client);

  const backend: Backend = {
    mode: "servico",
    auth,
    async loadCatalog(): Promise<Catalog> {
      const [lessons, questions, cards, subjects, topics, exams, decks] = await Promise.all([
        collectPages<Row>((from, to) => client.from("rumo_lessons").select("*").order("catalog_revision").range(from, to)),
        collectPages<Row>((from, to) => client.from("rumo_questions").select("*").order("catalog_revision").range(from, to)),
        collectPages<Row>((from, to) => client.from("rumo_cards").select("*").order("catalog_revision").range(from, to)),
        optionalTable(client, "rumo_subjects"),
        optionalTable(client, "rumo_topics"),
        optionalTable(client, "rumo_exams"),
        optionalTable(client, "rumo_decks"),
      ]);
      const mappedCards = latest(cards, mapCard);
      const mappedDecks: Deck[] = latest(decks, (d) => ({
        id: str(d.id),
        title: str(d.title),
        description: str(d.source),
        subjectId: str(d.subject_id) || null,
        topicId: str(d.topic_id) || list<string>(d.topic_ids)[0] || null,
        personal: false,
        example: d.example === true,
      }));
      if (!mappedDecks.length && mappedCards.length) {
        mappedDecks.push({
          id: "publicados",
          title: "Cartões publicados",
          description: "",
          subjectId: null,
          topicId: null,
          personal: false,
          example: false,
        });
      }
      return {
        example: false,
        subjects: subjects.map((s) => ({ id: str(s.id), name: str(s.name) }) as Subject),
        topics: topics.map(
          (t) => ({ id: str(t.id), subjectId: str(t.subject_id), parentId: str(t.parent_id) || null, name: str(t.name) }) as Topic,
        ),
        exams: exams.map((e) => ({ id: str(e.id), name: str(e.name) }) as Exam),
        lessons: latest(lessons, mapLesson),
        questions: latest(questions, mapQuestion),
        decks: mappedDecks,
        cards: mappedCards,
      };
    },
    push: (events: Envelope[]) => api.pushEvents(events),
    pull: (after: number) => api.pullEvents(after) as Promise<ServerEvent[]>,
    progressSummary: () => api.progressSummary(),
  };
  backend.forAccount = (userId) => {
    const bound = new RumoApi(url, publicKey, () => auth.tokenFor(userId));
    return { ...backend, push: (events) => bound.pushEvents(events),
      pull: (after) => bound.pullEvents(after) as Promise<ServerEvent[]>,
      progressSummary: () => bound.progressSummary() };
  };
  return backend;
}
