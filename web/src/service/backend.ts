import type { Catalog } from "../domain/types";
import type { Envelope, ProgressSummary, ServerEvent } from "./contract";

export interface Account {
  userId: string;
  email: string;
}

export interface Auth {
  current(): Promise<Account | null>;
  onChange(listener: (account: Account | null) => void): () => void;
  signIn(email: string, password: string): Promise<void>;
  signUp(email: string, password: string): Promise<{ needsConfirmation: boolean }>;
  signOut(): Promise<void>;
  requestReset(email: string): Promise<void>;
  updatePassword(password: string): Promise<void>;
  /** true quando a página foi aberta pelo link de redefinição de senha. */
  isRecovery(): boolean;
}

/**
 * O que o site precisa do serviço. Duas implementações: `servico` (Supabase,
 * contrato do Codex) e `exemplo` (servidor simulado neste navegador, com dados
 * identificados, para desenvolver enquanto o serviço não está publicado).
 */
export interface Backend {
  mode: "servico" | "exemplo";
  auth: Auth;
  /** Captura a identidade da conta antes de usar qualquer token. */
  forAccount?: (userId: string) => Backend;
  loadCatalog(): Promise<Catalog>;
  push(events: Envelope[]): Promise<{ id: string; sequence: number }[]>;
  pull(afterSequence: number): Promise<ServerEvent[]>;
  /** Nível e XP derivados das sessões no serviço (progress_summary). */
  progressSummary(): Promise<ProgressSummary>;
  /** Só no modo exemplo: simula queda de conexão para testar os estados. */
  simulateOffline?: (offline: boolean) => void;
  isSimulatedOffline?: () => boolean;
}
