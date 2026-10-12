import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { isComplete, readingKey, readPages, scheduleFor } from "../domain/projection";
import { getAll, getMeta, openDb, write } from "../lib/idb";
import { createExampleBackend } from "../service/example/server";
import { entity } from "../service/contract";
import { SyncEngine } from "../service/sync";
import { LESSON, testBackend, waitFor } from "./helpers";

const page = (n: number, read = true) => ({
  lesson_id: LESSON.id,
  version: LESSON.version,
  page: n,
  pages: LESSON.pages!,
  read,
});

async function engineFor(t: ReturnType<typeof testBackend>, device = "a") {
  const e = new SyncEngine(t.backend, `${t.userId}-${device}`);
  await e.start();
  await waitFor(e, (s) => s.ready && s.state !== "syncing");
  return e;
}

describe("fila e sincronização", () => {
  beforeEach(() => {
    // navigator.onLine do jsdom é true; a queda é simulada no backend.
  });

  it("guarda a ação offline e envia ao reconectar, sem duplicar", async () => {
    const t = testBackend();
    t.setOffline(true);
    const e = await engineFor(t);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 1), page(1));
    await e.sync();
    expect(e.current.state).toBe("offline");
    expect(e.current.pending).toBe(1);
    // A tela já mostra a marcação, mesmo sem confirmação do serviço.
    const reading = e.current.projection.reading.get(readingKey(LESSON.id, LESSON.version));
    expect(reading?.marks.get(1)).toEqual({ read: true, origin: "pending" });

    t.setOffline(false);
    await e.sync();
    await waitFor(e, (st) => st.state === "synced" && st.pending === 0);
    // Reenviar o mesmo lote não cria um segundo evento no serviço.
    const events = await t.server.pull(0);
    expect(events).toHaveLength(1);
    e.stop();
  });

  it("reenvio após fechar o navegador no meio é idempotente", async () => {
    const t = testBackend();
    const first = await engineFor(t);
    const id = await first.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 2), page(2));
    await first.sync();
    first.stop();
    // Simula o mesmo evento chegando de novo (ex.: resposta perdida antes do pull).
    const again = await t.server.push([(await t.server.pull(0))[0]]);
    expect(again[0].id).toBe(id);
    expect(await t.server.pull(0)).toHaveLength(1);
    const reopened = await engineFor(t);
    const reading = reopened.current.projection.reading.get(readingKey(LESSON.id, LESSON.version));
    expect(readPages(reading)).toEqual([2]);
    reopened.stop();
  });

  it("conflito entre dispositivos espera escolha explícita", async () => {
    const t = testBackend();
    const a = await engineFor(t, "a");
    const b = await engineFor(t, "b");
    const ent = entity.page(LESSON.id, LESSON.version, 3);
    await a.enqueue("reading.page", ent, page(3, true));
    await a.sync();
    // B ainda não viu a marcação de A e desmarca a mesma página com revisão antiga.
    t.setOffline(true);
    await b.enqueue("reading.page", ent, page(3, false));
    t.setOffline(false);
    await b.sync();
    expect(b.current.state).toBe("conflict");
    expect(b.current.conflicts).toHaveLength(1);
    // A projeção de B já mostra a versão do serviço (lida) enquanto o conflito existe.
    const before = b.current.projection.reading.get(readingKey(LESSON.id, LESSON.version));
    expect(before?.marks.get(3)?.read).toBe(true);

    await b.resolve(b.current.conflicts[0].id, "mine");
    await b.sync();
    await waitFor(b, (st) => st.state === "synced");
    const after = b.current.projection.reading.get(readingKey(LESSON.id, LESSON.version));
    expect(after?.marks.get(3)?.read).toBe(false);
    a.stop();
    b.stop();
  });

  it("conflito retém a cadeia e a resolução aplica a última intenção local", async () => {
    const t = testBackend();
    const a = await engineFor(t, "a");
    const b = await engineFor(t, "b");
    const ent = entity.page(LESSON.id, LESSON.version, 6);
    await a.enqueue("reading.page", ent, page(6, true));
    await a.sync();
    t.setOffline(true);
    // Em B, sem saber de A: marca e depois desmarca a mesma página.
    await b.enqueue("reading.page", ent, page(6, true));
    await b.enqueue("reading.page", ent, page(6, false));
    t.setOffline(false);
    await b.sync();
    await waitFor(b, (s) => s.state === "conflict");
    expect(b.current.conflicts).toHaveLength(1);
    expect((b.current.conflicts[0].envelope.payload as { read: boolean }).read).toBe(false);
    // Nada da cadeia foi aceito antes da escolha.
    expect((await t.server.pull(0)).filter((e) => e.entity_id === ent)).toHaveLength(1);
    await b.resolve(b.current.conflicts[0].id, "mine");
    await b.sync();
    await waitFor(b, (s) => s.state === "synced");
    const reading = b.current.projection.reading.get(readingKey(LESSON.id, LESSON.version));
    expect(reading?.marks.get(6)?.read).toBe(false);
    a.stop();
    b.stop();
  });

  it("um evento recusado não impede os demais do lote", async () => {
    const t = testBackend();
    const e = await engineFor(t);
    t.setOffline(true);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 4), page(4));
    // Página inexistente: o serviço recusa este, mas aceita o anterior.
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 99), page(99));
    t.setOffline(false);
    await e.sync();
    expect(e.current.rejected).toHaveLength(1);
    expect(e.current.rejected[0].error).toBe("invalid_event");
    expect((await t.server.pull(0)).map((x) => (x.payload as { page: number }).page)).toEqual([4]);
    e.stop();
  });

  it("aula só conclui com todas as páginas, incluindo a última; desmarcar recalcula", async () => {
    const t = testBackend();
    const e = await engineFor(t);
    const pages = LESSON.pages!;
    for (let n = 1; n < pages; n += 1) await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, n), page(n));
    // Posição na última página não é prova de leitura.
    await e.enqueue("reading.position", entity.position(LESSON.id, LESSON.version), {
      lesson_id: LESSON.id,
      version: LESSON.version,
      page: pages,
      pages,
    });
    await e.sync();
    const key = readingKey(LESSON.id, LESSON.version);
    expect(isComplete(e.current.projection.reading.get(key), pages)).toBe(false);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, pages), page(pages));
    await e.sync();
    expect(isComplete(e.current.projection.reading.get(key), pages)).toBe(true);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 5), page(5, false));
    await e.sync();
    expect(isComplete(e.current.projection.reading.get(key), pages)).toBe(false);
    e.stop();
  });

  it("favorito e marcador usam a identidade canônica do contrato", async () => {
    const t = testBackend();
    const e = await engineFor(t);
    await e.enqueue("favorite.set", entity.favorite("lesson", LESSON.id, ""), {
      target_type: "lesson",
      target_id: LESSON.id,
      version: "",
      favorite: true,
    });
    const target = entity.bookmarkTarget(LESSON.id, LESSON.version, 7);
    await e.enqueue("favorite.set", entity.favorite("bookmark", target, LESSON.version), {
      target_type: "bookmark",
      target_id: target,
      version: LESSON.version,
      favorite: true,
    });
    // Identidade fora do padrão é recusada (como no SQL).
    await e.enqueue("favorite.set", `lesson:${LESSON.id}`, { target_type: "lesson", target_id: LESSON.id, version: "", favorite: true });
    await e.sync();
    expect(e.current.rejected).toHaveLength(1);
    expect(e.current.projection.favorites.get(`lesson:${LESSON.id}::favorite`)?.favorite).toBe(true);
    expect(e.current.projection.favorites.get(`bookmark:${target}:${LESSON.version}:favorite`)?.favorite).toBe(true);
    e.stop();
  });
  it("falha na gravação nunca envia nem projeta uma ação não durável", async () => {
    const t = testBackend();
    const e = await engineFor(t);
    const original = IDBObjectStore.prototype.put;
    const failed = vi.spyOn(IDBObjectStore.prototype, "put").mockImplementation(function (this: IDBObjectStore, value: unknown, key?: IDBValidKey) {
      const result = original.call(this, value, key);
      if (this.name === "outbox") this.transaction.abort();
      return result;
    });
    const saving = e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 1), page(1));
    expect(e.current.pending).toBe(0);
    const syncing = e.sync();
    await expect(saving).rejects.toBeNull();
    await syncing;
    failed.mockRestore();
    expect(t.calls.push).toBe(0);
    expect(e.current.pending).toBe(0);
    expect(e.current.projection.reading.size).toBe(0);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 1), page(1));
    await e.sync();
    expect(await t.server.pull(0)).toHaveLength(1);
    e.stop();
  });

  it("enqueue concorrente preserva CAS e a ordem mesmo no mesmo milissegundo", async () => {
    const t = testBackend();
    t.setOffline(true);
    const e = await engineFor(t);
    const stamp = vi.spyOn(Date.prototype, "toISOString").mockReturnValue("2026-10-12T12:00:00.000Z");
    const ent = entity.page(LESSON.id, LESSON.version, 1);
    await Promise.all([e.enqueue("reading.page", ent, page(1, true)), e.enqueue("reading.page", ent, page(1, false))]);
    stamp.mockRestore();
    e.stop();
    const reopened = await engineFor(t);
    expect(reopened.current.projection.reading.get(readingKey(LESSON.id, LESSON.version))?.marks.get(1)?.read).toBe(false);
    t.setOffline(false);
    await reopened.sync();
    expect((await t.server.pull(0)).map((item) => item.base_revision)).toEqual([0, 1]);
    expect(reopened.current.conflicts).toHaveLength(0);
    reopened.stop();
  });

  it("falha ao guardar resolução mantém a cadeia de conflito até após reabrir", async () => {
    const t = testBackend();
    const a = await engineFor(t, "a");
    const b = await engineFor(t, "b");
    const ent = entity.page(LESSON.id, LESSON.version, 1);
    await a.enqueue("reading.page", ent, page(1, true));
    await a.sync();
    await b.enqueue("reading.page", ent, page(1, false));
    await b.sync();
    const original = IDBObjectStore.prototype.put;
    const failed = vi.spyOn(IDBObjectStore.prototype, "put").mockImplementation(function (this: IDBObjectStore, value: unknown, key?: IDBValidKey) {
      const result = original.call(this, value, key);
      if (this.name === "outbox" && (value as { status?: string }).status === "pending") this.transaction.abort();
      return result;
    });
    await expect(b.resolve(b.current.conflicts[0].id, "mine")).rejects.toBeNull();
    failed.mockRestore();
    expect(b.current.conflicts).toHaveLength(1);
    b.stop();
    const reopened = await engineFor(t, "b");
    expect(reopened.current.conflicts).toHaveLength(1);
    await reopened.resolve(reopened.current.conflicts[0].id, "mine");
    await reopened.sync();
    expect(reopened.current.projection.reading.get(readingKey(LESSON.id, LESSON.version))?.marks.get(1)?.read).toBe(false);
    a.stop();
    reopened.stop();
  });

  it("fila de A não usa as credenciais de B depois de trocar a conta", async () => {
    const backend = createExampleBackend();
    await backend.auth.signIn("conta-a@exemplo.dev", "senha-exemplo-123");
    const account = (await backend.auth.current())!;
    const e = new SyncEngine(backend, account.userId);
    await e.start();
    await e.sync();
    backend.simulateOffline!(true);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 1), page(1));
    await backend.auth.signIn("conta-b@exemplo.dev", "senha-exemplo-123");
    backend.simulateOffline!(false);
    await e.sync();
    expect(e.current.error).toBe("unauthenticated");
    expect(await backend.pull(0)).toHaveLength(0);
    await backend.auth.signIn("conta-a@exemplo.dev", "senha-exemplo-123");
    await e.sync();
    expect(await backend.pull(0)).toHaveLength(1);
    e.stop();
  });

  it("aceitação inválida preserva a fila para reenvio", async () => {
    const t = testBackend();
    const e = await engineFor(t);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 1), page(1));
    const real = t.backend.push;
    t.backend.push = async () => [];
    await e.sync();
    expect(e.current.pending).toBe(1);
    expect(e.current.state).toBe("error");
    t.backend.push = real;
    await e.sync();
    expect(await t.server.pull(0)).toHaveLength(1);
    e.stop();
  });

  it("write aborta tudo quando o callback lança depois de uma escrita", async () => {
    const db = await openDb(`teste-atomic-${Date.now()}`);
    await expect(write(db, ["meta"], (tx) => {
      tx.objectStore("meta").put("temporary", "cursor");
      throw new Error("test failure");
    })).rejects.toThrow("test failure");
    expect(await getMeta(db, "cursor")).toBeUndefined();
    db.close();
  });

  it("um pull fora de ordem não confirma eventos nem cursor", async () => {
    const t = testBackend();
    const e = await engineFor(t);
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 1), page(1));
    await e.enqueue("reading.page", entity.page(LESSON.id, LESSON.version, 2), page(2));
    const real = t.backend.pull;
    t.backend.pull = async (after) => (await real(after)).reverse();
    await e.sync();
    expect(e.current.state).toBe("error");
    const db = await openDb(`rumo-site:exemplo:${t.userId}-a`);
    expect(await getMeta(db, "cursor")).toBeUndefined();
    expect(await getAll(db, "events")).toHaveLength(0);
    db.close();
    t.backend.pull = real;
    await e.sync();
    expect(e.current.pending).toBe(0);
    e.stop();
  });

  it("outra aba relê eventos e cursor juntos antes de enviar", async () => {
    const t = testBackend();
    const a = await engineFor(t);
    const b = await engineFor(t);
    const ent = entity.page(LESSON.id, LESSON.version, 1);
    await a.enqueue("reading.page", ent, page(1, true));
    await a.sync();
    await b.sync();
    expect(b.current.projection.reading.get(readingKey(LESSON.id, LESSON.version))?.marks.get(1)?.read).toBe(true);
    await b.enqueue("reading.page", ent, page(1, false));
    await b.sync();
    await a.sync();
    expect(a.current.projection.reading.get(readingKey(LESSON.id, LESSON.version))?.marks.get(1)?.read).toBe(false);
    expect(a.current.conflicts).toHaveLength(0);
    a.stop();
    b.stop();
  });

});


it("preserva a agenda confirmada ao mudar a versão do cartão", () => {
  const projection = { reviews: [{ cardId: "card", version: "1", origin: "server", at: "2026-10-12T12:00:00Z", result: { interval_days: 3, due_at: "2026-10-15T12:00:00Z" } }] } as unknown as Parameters<typeof scheduleFor>[0];
  expect(scheduleFor(projection, "card", "2").dueAt).toBe("2026-10-15T12:00:00Z");
});
