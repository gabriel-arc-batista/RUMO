/** IndexedDB mínimo com promessas. Cada conta usa um banco próprio. */
export type StoreName = "outbox" | "events" | "meta";

export function openDb(name: string): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      db.createObjectStore("outbox", { keyPath: "id" });
      db.createObjectStore("events", { keyPath: "sequence" });
      db.createObjectStore("meta");
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function done<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export function getAll<T>(db: IDBDatabase, store: StoreName): Promise<T[]> {
  return done(db.transaction(store).objectStore(store).getAll()) as Promise<T[]>;
}

export function getMeta<T>(db: IDBDatabase, key: string): Promise<T | undefined> {
  return done(db.transaction("meta").objectStore("meta").get(key)) as Promise<T | undefined>;
}

/** Grava vários registros numa única transação (tudo ou nada). */
export function write(
  db: IDBDatabase,
  stores: StoreName[],
  apply: (tx: IDBTransaction) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(stores, "readwrite");
    try {
      apply(tx);
    } catch (error) {
      tx.abort();
      reject(error);
      return;
    }
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

/** Une leitura de eventos, fila e cursor no mesmo snapshot entre abas. */
export async function readSnapshot(db: IDBDatabase) {
  const tx = db.transaction(["events", "outbox", "meta"], "readonly");
  const events = done(tx.objectStore("events").getAll());
  const outbox = done(tx.objectStore("outbox").getAll());
  const keys = done(tx.objectStore("meta").getAllKeys());
  const values = done(tx.objectStore("meta").getAll());
  const [e, o, k, v] = await Promise.all([events, outbox, keys, values]);
  return { events: e, outbox: o, meta: new Map(k.map((key, index) => [String(key), v[index]])) };
}
