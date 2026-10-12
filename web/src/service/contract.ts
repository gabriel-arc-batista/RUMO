/**
 * Ponte com o contrato do Codex (shared/rumo-api.ts, docs/integration/CONTRACT.md).
 * Versões de conteúdo são strings opacas ("1.0.0"); nunca comparar como número.
 */
import type { Payloads as SharedPayloads, ProgressSummary, SyncState } from "@shared/rumo-api";

export type Payloads = SharedPayloads;
export type { ProgressSummary };
export type EventKind = keyof Payloads;

export type Envelope<K extends EventKind = EventKind> = {
  [P in K]: {
    id: string;
    device_id: string;
    kind: P;
    entity_id: string;
    base_revision: number;
    payload: Payloads[P];
  };
}[K];

export type ServerEvent<K extends EventKind = EventKind> = Envelope<K> & {
  sequence: number;
  revision: number;
  received_at: string;
  result?: Record<string, unknown> | null;
};

export type { SyncState };

/** Códigos de erro do contrato, mais os de transporte do próprio site. */
export type ErrorCode =
  | "unauthenticated"
  | "invalid_event"
  | "event_mismatch"
  | "revision_conflict"
  | "content_unavailable"
  | "invalid_answer"
  | "card_suspended"
  | "network"
  | "unknown";

export const ERROR_TEXT: Record<ErrorCode, string> = {
  unauthenticated: "Sua sessão terminou. Entre de novo para enviar o que ficou guardado.",
  invalid_event: "O serviço recusou este registro por estar incompleto.",
  event_mismatch: "Este registro já existe no serviço com outro conteúdo.",
  revision_conflict: "Isto foi alterado em outro dispositivo. Escolha qual versão manter.",
  content_unavailable: "Este conteúdo não está disponível no serviço.",
  invalid_answer: "Esta alternativa não existe nesta versão da questão.",
  card_suspended: "O cartão está suspenso ou foi excluído.",
  network: "Sem conexão com o serviço. Tudo fica guardado neste navegador.",
  unknown: "O serviço não respondeu como esperado.",
};

export function errorCode(error: unknown): ErrorCode {
  if (error && typeof error === "object" && "code" in error) {
    const code = String((error as { code: unknown }).code);
    const known = Object.keys(ERROR_TEXT).find((k) => code === k || code.includes(k));
    if (known) return known as ErrorCode;
  }
  if (error instanceof TypeError) return "network";
  return "unknown";
}

export type FavoriteType = "lesson" | "question" | "card" | "deck" | "bookmark";

/** Identidades de entidade iguais às do desktop (CAS compartilhado entre dispositivos). */
export const entity = {
  page: (lessonId: string, version: string, page: number) => `${lessonId}:${version}:page:${page}`,
  position: (lessonId: string, version: string) => `${lessonId}:${version}:position`,
  /** `${target_type}:${target_id}:${version}:favorite`; versão vazia = favorito global. */
  favorite: (type: FavoriteType, targetId: string, version = "") => `${type}:${targetId}:${version}:favorite`,
  /** Alvo do marcador de página (target_type "bookmark"). */
  bookmarkTarget: (lessonId: string, version: string, page: number) => `${lessonId}:${version}:page:${page}`,
};
