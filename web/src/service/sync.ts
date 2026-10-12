/**
 * Fila de eventos do site (IndexedDB) e sincronização com o serviço.
 *
 * - Todo evento é gravado na fila antes da rede; o id nunca é regenerado.
 * - Envio em lotes de até 100. Se o serviço recusar o lote inteiro, os eventos
 *   são reenviados um a um para isolar o recusado sem perder os demais.
 * - `revision_conflict` nunca descarta a ação: ela fica em conflito até a
 *   pessoa escolher manter a versão do serviço ou reaplicar a sua.
 * - Eventos aceitos ficam na fila até voltarem no `pull`; só então saem.
 */
import { openDb, readSnapshot, write } from "../lib/idb";
import { uuid } from "../lib/ids";
import { project, revisionKey, type PendingEvent, type Projection } from "../domain/projection";
import type { Backend } from "./backend";
import { errorCode, ERROR_TEXT, type Envelope, type ErrorCode, type EventKind, type Payloads, type ServerEvent, type SyncState } from "./contract";

export type OutboxStatus = "pending" | "sent" | "conflict" | "rejected";

export interface OutboxItem extends PendingEvent {
  id: string;
  status: OutboxStatus;
  error: ErrorCode | null;
  tries: number;
  order?: number;
}

export interface SyncSnapshot {
  state: SyncState;
  pending: number;
  conflicts: OutboxItem[];
  rejected: OutboxItem[];
  lastSyncedAt: string | null;
  error: ErrorCode | null;
  message: string | null;
  projection: Projection;
  ready: boolean;
}

const PULL_PAGE = 200;

/** Ações sobre a mesma entidade formam uma cadeia (CAS): conflito em uma retém as seguintes. */
const chainKey = (i: OutboxItem) => `${i.envelope.kind}|${i.envelope.entity_id}`;

export class SyncEngine {
  private db!: IDBDatabase;
  private server: ServerEvent[] = [];
  private outbox: OutboxItem[] = [];
  private cursor = 0;
  private deviceId = "";
  private running: Promise<void> | null = null;
  private next: Promise<void> | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private listeners = new Set<(s: SyncSnapshot) => void>();
  private snapshot: SyncSnapshot;
  private stopped = false;
  private mutations: Promise<unknown> = Promise.resolve();

  constructor(
    private backend: Backend,
    private userId: string,
  ) {
    this.backend = backend.forAccount?.(userId) ?? backend;
    this.snapshot = {
      state: "pending",
      pending: 0,
      conflicts: [],
      rejected: [],
      lastSyncedAt: null,
      error: null,
      message: null,
      projection: project([], []),
      ready: false,
    };
  }

  async start() {
    try {
      await this.startStorage();
    } catch {
      if (!this.stopped) this.publish({ state: "error", error: "unknown", ready: true, message: "Não foi possível abrir o armazenamento deste navegador." });
    }
  }

  private async startStorage() {
    const db = await openDb(`rumo-site:${this.backend.mode}:${this.userId}`);
    if (this.stopped) return db.close();
    this.db = db;
    const stored = await this.reloadStored();
    this.deviceId = stored.meta.get("device_id") ?? uuid();
    const lastSyncedAt = stored.meta.get("last_synced_at") ?? null;
    if (this.stopped) return;
    await write(this.db, ["meta"], (tx) => tx.objectStore("meta").put(this.deviceId, "device_id"));
    // Abre já com o que este navegador guardou: funciona sem conexão.
    this.recompute();
    this.publish({ ready: true, lastSyncedAt });
    void this.sync();
  }

  private async reloadStored() {
    const stored = await readSnapshot(this.db);
    this.server = stored.events as ServerEvent[];
    this.outbox = (stored.outbox as OutboxItem[]).sort((a, b) => (a.order ?? 0) - (b.order ?? 0) || a.createdAt.localeCompare(b.createdAt) || a.envelope.base_revision - b.envelope.base_revision);
    this.cursor = stored.meta.get("cursor") ?? 0;
    this.recompute();
    return stored;
  }

  stop() {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.listeners.clear();
    this.db?.close();
  }

  subscribe(listener: (s: SyncSnapshot) => void) {
    this.listeners.add(listener);
    listener(this.snapshot);
    return () => void this.listeners.delete(listener);
  }

  get current() {
    return this.snapshot;
  }

  /** Revisão-base: a do serviço mais as ações ainda na fila para a mesma entidade. */
  private baseRevision(kind: EventKind, entityId: string) {
    const known = this.snapshot.projection.revisions.get(revisionKey(kind, entityId)) ?? 0;
    const queued = this.outbox.filter(
      (i) => i.envelope.kind === kind && i.envelope.entity_id === entityId && (i.status === "pending" || i.status === "sent"),
    ).length;
    return known + queued;
  }

  private mutate<T>(work: () => Promise<T>): Promise<T> {
    const operation = this.mutations.then(work);
    this.mutations = operation.catch(() => undefined);
    return operation;
  }

  enqueue<K extends EventKind>(kind: K, entityId: string, payload: Payloads[K], id = uuid()): Promise<string> {
    return this.mutate(() => this.enqueueStored(kind, entityId, payload, id));
  }

  private async enqueueStored<K extends EventKind>(kind: K, entityId: string, payload: Payloads[K], id: string, replacing?: string[]): Promise<string> {
    if (this.stopped || !this.db || !this.snapshot.ready) throw new Error("Fila indisponível.");
    await this.reloadStored();
    const previous = this.outbox.find((item) => item.id === id)?.envelope ?? this.server.find((item) => item.id === id);
    if (previous) {
      if (previous.kind !== kind || previous.entity_id !== entityId || JSON.stringify(previous.payload) !== JSON.stringify(payload)) throw Object.assign(new Error("Evento imutável"), { code: "event_mismatch" });
      return id;
    }
    const append = kind === "arena.attempt" || kind === "card.review";
    const envelope = { id, device_id: this.deviceId, kind, entity_id: entityId,
      base_revision: append ? 0 : this.baseRevision(kind, entityId), payload } as Envelope;
    const item: OutboxItem = { id, envelope, createdAt: new Date().toISOString(), status: "pending", error: null, tries: 0 };
    const superseded = replacing ?? this.outbox.filter((i) => i.status === "conflict" && chainKey(i) === chainKey(item)).map((i) => i.id);
    try {
      await write(this.db, ["outbox", "meta"], (tx) => {
        const meta = tx.objectStore("meta");
        const next = meta.get("outbox_order");
        next.onsuccess = () => {
          item.order = Number(next.result ?? 0) + 1;
          meta.put(item.order, "outbox_order");
          const outbox = tx.objectStore("outbox");
          superseded.forEach((old) => outbox.delete(old));
          outbox.put(item);
        };
      });
    } catch (error) {
      this.publish({ state: "error", error: "unknown", message: "Não foi possível guardar neste navegador. Verifique o espaço disponível." });
      throw error;
    }
    // Só eventos já duráveis entram na projeção e ficam disponíveis para a rede.
    this.outbox = this.outbox.filter((i) => !superseded.includes(i.id));
    this.outbox.push(item);
    this.recompute();
    this.schedule(350);
    return id;
  }

  /** Resolve a cadeia em uma transação, mantendo a última intenção local. */
  resolve(itemId: string, choice: "mine" | "theirs") {
    return this.mutate(async () => {
      const item = this.outbox.find((i) => i.id === itemId && i.status === "conflict");
      if (!item) return;
      const chain = this.outbox.filter((i) => i.status === "conflict" && chainKey(i) === chainKey(item));
      const ids = chain.map((i) => i.id);
      const last = chain.at(-1) ?? item;
      if (choice === "mine") {
        const e = last.envelope;
        await this.enqueueStored(e.kind, e.entity_id, e.payload as never, uuid(), ids);
      } else {
        await this.removeStored(ids);
        this.recompute();
      }
    });
  }

  async dismiss(itemId: string) {
    await this.remove([itemId]);
    this.recompute();
  }

  schedule(delay = 0) {
    if (this.stopped) return;
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.sync(), delay);
  }

  /** Resolve depois de uma rodada que começou após esta chamada (nada fica para trás). */
  sync(): Promise<void> {
    if (this.stopped || !this.db) return Promise.resolve();
    if (this.running) {
      if (!this.next) {
        this.next = this.running.then(() => {
          this.next = null;
          return this.sync();
        });
      }
      return this.next;
    }
    this.running = this.run().finally(() => {
      this.running = null;
    });
    return this.running;
  }

  private async run() {
    if (typeof navigator !== "undefined" && navigator.onLine === false) {
      this.publish({ state: "offline", error: "network", message: ERROR_TEXT.network });
      return;
    }
    this.publish({ state: "syncing", error: null, message: null });
    try {
      await this.mutate(() => this.reloadStored());
      if (this.stopped) return;
      await this.pushAll();
      if (this.stopped) return;
      await this.pullAll();
      if (this.stopped) return;
      const now = new Date().toISOString();
      await write(this.db, ["meta"], (tx) => tx.objectStore("meta").put(now, "last_synced_at"));
      this.publish({ lastSyncedAt: now });
      this.settle();
    } catch (error) {
      const code = errorCode(error);
      this.publish({
        state: code === "network" ? "offline" : "error",
        error: code,
        message: ERROR_TEXT[code],
      });
    }
  }

  private async pushAll() {
    const blocked = new Set(this.outbox.filter((i) => i.status === "conflict").map(chainKey));
    const ready = this.outbox.filter((i) => i.status === "pending" || i.status === "sent");
    for (let start = 0; start < ready.length; start += 100) {
      if (this.stopped) return;
      const batch = ready.slice(start, start + 100);
      if (batch.some((i) => blocked.has(chainKey(i)))) {
        await this.isolate(batch, blocked);
        continue;
      }
      try {
        this.validateAccepted(await this.backend.push(batch.map((i) => i.envelope)), batch);
        await this.mark(batch, "sent", null);
      } catch (error) {
        const code = errorCode(error);
        if (code === "network" || code === "unauthenticated" || code === "unknown") throw error;
        await this.isolate(batch, blocked);
      }
    }
  }

  /**
   * Lote recusado por inteiro: reenviar um a um preserva os aceitáveis. Depois de
   * um conflito, as ações seguintes da mesma entidade ficam retidas com ele (a ordem
   * das intenções da pessoa nunca se inverte).
   */
  private async isolate(batch: OutboxItem[], blocked: Set<string>) {
    for (const item of batch) {
      if (this.stopped) return;
      if (blocked.has(chainKey(item))) {
        await this.mark([item], "conflict", "revision_conflict");
        continue;
      }
      try {
        this.validateAccepted(await this.backend.push([item.envelope]), [item]);
        await this.mark([item], "sent", null);
      } catch (error) {
        const code = errorCode(error);
        if (code === "network" || code === "unauthenticated" || code === "unknown") throw error;
        if (code === "revision_conflict") blocked.add(chainKey(item));
        await this.mark([item], code === "revision_conflict" ? "conflict" : "rejected", code);
      }
    }
  }

  private async pullAll() {
    for (;;) {
      if (this.stopped) return;
      const page = await this.backend.pull(this.cursor);
      if (this.stopped) return;
      let after = this.cursor;
      if (!Array.isArray(page) || page.length > PULL_PAGE) throw new Error("Resposta inválida");
      for (const event of page) {
        if (!event || !Number.isSafeInteger(event.sequence) || event.sequence <= after || !Number.isSafeInteger(event.revision) || event.revision < 1) throw new Error("Resposta inválida");
        after = event.sequence;
      }
      if (!page.length) break;
      const ids = new Set(page.map((e) => e.id));
      const done = this.outbox.filter((i) => ids.has(i.id)).map((i) => i.id);
      const next = page[page.length - 1].sequence;
      const known = new Set(this.server.map((event) => event.id));
      const merged = [...this.server, ...page.filter((event) => !known.has(event.id))];
      // Valida a aplicação antes de confirmar o cursor durável.
      project(merged, this.outbox.filter((item) => !done.includes(item.id) && (item.status === "pending" || item.status === "sent")));
      // Eventos e cursor na mesma transação: o cursor só avança com o que foi gravado.
      await write(this.db, ["events", "outbox", "meta"], (tx) => {
        const events = tx.objectStore("events");
        page.forEach((e) => events.put(e));
        const outbox = tx.objectStore("outbox");
        done.forEach((id) => outbox.delete(id));
        const meta = tx.objectStore("meta");
        const current = meta.get("cursor");
        current.onsuccess = () => meta.put(Math.max(next, Number(current.result ?? 0)), "cursor");
      });
      await this.mutate(() => this.reloadStored());
      if (page.length < PULL_PAGE) break;
    }
  }

  private validateAccepted(accepted: { id: string; sequence: number }[], items: OutboxItem[]) {
    const ids = new Set(items.map((item) => item.id));
    if (!Array.isArray(accepted) || accepted.length !== ids.size || new Set(accepted.map((item) => item?.id)).size !== ids.size
      || accepted.some((item) => !item || !ids.has(item.id) || !Number.isSafeInteger(item.sequence) || item.sequence < 1)) throw new Error("Resposta inválida");
  }

  private mark(items: OutboxItem[], status: OutboxStatus, error: ErrorCode | null) {
    return this.mutate(async () => {
      if (this.stopped) return;
      const ids = new Set(items.map((item) => item.id));
      const updated = this.outbox.filter((item) => ids.has(item.id)).map((item) => ({ ...item, status, error, tries: item.tries + 1 }));
      await write(this.db, ["outbox"], (tx) => {
        const store = tx.objectStore("outbox");
        updated.forEach((item) => {
          const current = store.get(item.id);
          current.onsuccess = () => { if (current.result) store.put({ ...current.result, status, error, tries: current.result.tries + 1 }); };
        });
      });
      await this.reloadStored();
    });
  }

  private remove(ids: string[]) {
    return this.mutate(() => this.removeStored(ids));
  }

  private async removeStored(ids: string[]) {
    await write(this.db, ["outbox"], (tx) => ids.forEach((id) => tx.objectStore("outbox").delete(id)));
    this.outbox = this.outbox.filter((i) => !ids.includes(i.id));
  }

  private settle() {
    const conflicts = this.outbox.some((i) => i.status === "conflict");
    const waiting = this.outbox.some((i) => i.status === "pending" || i.status === "sent");
    this.publish({ state: conflicts ? "conflict" : waiting ? "pending" : "synced", error: null, message: null });
  }

  private recompute() {
    const active = this.outbox.filter((i) => i.status === "pending" || i.status === "sent");
    const projection = project(this.server, active);
    // Um conflito por entidade, representado pela última ação local da cadeia.
    const byChain = new Map<string, OutboxItem>();
    for (const i of this.outbox.filter((x) => x.status === "conflict").sort((a, b) => (a.order ?? 0) - (b.order ?? 0) || a.createdAt.localeCompare(b.createdAt) || a.envelope.base_revision - b.envelope.base_revision)) {
      byChain.set(chainKey(i), i);
    }
    const conflicts = [...byChain.values()];
    const rejected = this.outbox.filter((i) => i.status === "rejected");
    const pending = active.length;
    let state = this.snapshot.state;
    if (state === "synced" && pending) state = "pending";
    if (conflicts.length && state !== "syncing") state = "conflict";
    this.publish({ projection, conflicts, rejected, pending, state });
  }

  private publish(patch: Partial<SyncSnapshot>) {
    this.snapshot = { ...this.snapshot, ...patch };
    this.listeners.forEach((l) => l(this.snapshot));
  }
}
