/**
 * Modelo de apresentação do site. Os eventos e seus payloads seguem
 * shared/rumo-api.ts (contrato do Codex); estes tipos descrevem o catálogo e a
 * projeção local do que o serviço devolveu. Nada aqui calcula correção,
 * agenda de revisão ou recompensa: esses valores chegam prontos do serviço.
 */
export type Id = string;

export interface Subject {
  id: Id;
  name: string;
}

export interface Topic {
  id: Id;
  subjectId: Id;
  parentId: Id | null;
  name: string;
}

export interface Exam {
  id: Id;
  name: string;
}

export interface SourceRef {
  title: string;
  url?: string;
}

export interface ReviewInfo {
  status: "aprovada" | "pendente" | "em_revisao";
  reviewer: string | null;
  reviewedAt: string | null;
}

export interface OutlineItem {
  title: string;
  page: number;
}

export type LessonStatus = "disponivel" | "planejada";

export interface Lesson {
  id: Id;
  /** Versão opaca do conteúdo ("1.0.0"). */
  version: string;
  versionLabel: string;
  title: string;
  summary: string;
  subjectId: Id;
  topicIds: Id[];
  examIds: Id[];
  status: LessonStatus;
  objectives: string[];
  prerequisiteTopicIds: Id[];
  sources: SourceRef[];
  review: ReviewInfo;
  pages: number | null;
  pdfUrl: string | null;
  outline: OutlineItem[];
  example: boolean;
}

export type Block =
  | { kind: "text"; text: string }
  | { kind: "code"; text: string; lang?: string }
  | { kind: "formula"; text: string }
  | { kind: "image"; src: string; alt: string };

export type QuestionType = "multipla_escolha" | "certo_errado";

export interface Question {
  id: Id;
  version: string;
  type: QuestionType;
  statement: Block[];
  options: { id: string; text: string }[];
  subjectId: Id;
  topicIds: Id[];
  examIds: Id[];
  provenance: { kind: "autoral" | "banca"; label: string; bank?: string; year?: number };
  annulled: boolean;
  example: boolean;
}

export interface Deck {
  id: Id;
  title: string;
  description: string;
  subjectId: Id | null;
  topicId: Id | null;
  personal: boolean;
  example: boolean;
}

export interface Card {
  id: Id;
  /** Publicado: versão editorial. Pessoal: revisão CAS do card.save ("1", "2"…). */
  version: string;
  deckId: Id;
  front: string;
  back: string;
  explanation: string;
  source: string;
  lessonId: Id | null;
  questionId: Id | null;
  suspended: boolean;
  deleted: boolean;
  personal: boolean;
  example: boolean;
}

export interface Catalog {
  example: boolean;
  subjects: Subject[];
  topics: Topic[];
  exams: Exam[];
  lessons: Lesson[];
  questions: Question[];
  decks: Deck[];
  cards: Card[];
}

/** Resultado de uma tentativa, como o serviço devolve em `result`. */
export interface AttemptResult {
  status: "correct" | "incorrect" | "annulled";
  answer?: string;
  comment?: string;
}

/** Resultado de uma revisão de cartão (FLASHCARDS.md). */
export interface ReviewResult {
  interval_days: number;
  repetitions: number;
  ease: number;
}

export interface SessionResult {
  xp: number;
  coins: number;
}
