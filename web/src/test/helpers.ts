import type { Backend } from "../service/backend";
import { EXAMPLE_CATALOG } from "../service/example/catalog";
import { ExampleServer } from "../service/example/server";
import type { SyncEngine, SyncSnapshot } from "../service/sync";

let counter = 0;

/** Backend de teste: o servidor simulado (mesmas regras do SQL) com rede controlável. */
export function testBackend(userId = `teste-${++counter}-${Date.now()}`) {
  const server = new ExampleServer(userId);
  let offline = false;
  const calls = { push: 0, pull: 0 };
  const backend: Backend = {
    mode: "exemplo",
    auth: {} as Backend["auth"],
    loadCatalog: async () => EXAMPLE_CATALOG,
    push: async (events) => {
      calls.push += 1;
      return server.push(events);
    },
    pull: async (after) => {
      calls.pull += 1;
      return server.pull(after);
    },
    progressSummary: () => server.progressSummary(),
  };
  return {
    backend,
    server,
    userId,
    calls,
    setOffline(value: boolean) {
      offline = value;
      server.setOffline(offline);
    },
  };
}

export function waitFor(engine: SyncEngine, predicate: (s: SyncSnapshot) => boolean, timeout = 4000): Promise<SyncSnapshot> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      off();
      reject(new Error(`tempo esgotado; estado ${engine.current.state}`));
    }, timeout);
    let off = () => {};
    // subscribe chama o ouvinte na hora: o cancelamento fica para depois.
    off = engine.subscribe((s) => {
      if (predicate(s)) {
        clearTimeout(timer);
        queueMicrotask(() => off());
        resolve(s);
      }
    });
  });
}

export const LESSON = EXAMPLE_CATALOG.lessons.find((l) => l.id === "exemplo.aula.juncoes")!;
