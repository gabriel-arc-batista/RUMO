import { Fragment, createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { Catalog } from "../domain/types";
import { loadPrefs, savePrefs, type Prefs } from "../lib/prefs";
import type { Account, Backend } from "./backend";
import type { EventKind, Payloads, ProgressSummary } from "./contract";
import { SyncEngine, type SyncSnapshot } from "./sync";

export interface Toast {
  id: number;
  text: string;
  tone?: "info" | "rpg" | "error";
}

type CatalogState =
  | { status: "loading" }
  | { status: "ready"; catalog: Catalog }
  | { status: "error"; message: string };

interface RumoContext {
  backend: Backend;
  account: Account | null;
  authReady: boolean;
  catalog: CatalogState;
  reloadCatalog: () => void;
  sync: SyncSnapshot | null;
  /** Nível e XP da conta (progress_summary); null até a primeira resposta. */
  progress: ProgressSummary | null;
  online: boolean;
  enqueue: <K extends EventKind>(kind: K, entityId: string, payload: Payloads[K], id?: string) => Promise<string>;
  syncNow: () => Promise<void>;
  resolveConflict: (id: string, choice: "mine" | "theirs") => Promise<void>;
  dismiss: (id: string) => Promise<void>;
  prefs: Prefs;
  setPrefs: (patch: Partial<Prefs>) => void;
  toasts: Toast[];
  toast: (text: string, tone?: Toast["tone"]) => void;
  closeToast: (id: number) => void;
}

const Ctx = createContext<RumoContext | null>(null);

export function RumoProvider({ backend, children }: { backend: Backend; children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [catalog, setCatalog] = useState<CatalogState>({ status: "loading" });
  const [sync, setSync] = useState<SyncSnapshot | null>(null);
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  const [prefs, setPrefsState] = useState<Prefs>(loadPrefs);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const engine = useRef<SyncEngine | null>(null);
  const toastId = useRef(0);

  useEffect(() => {
    let alive = true;
    void backend.auth.current().then((a) => {
      if (!alive) return;
      setAccount(a);
      setAuthReady(true);
    });
    const off = backend.auth.onChange((a) => setAccount(a));
    return () => {
      alive = false;
      off();
    };
  }, [backend]);

  const reloadCatalog = useCallback(() => {
    setCatalog({ status: "loading" });
    backend
      .loadCatalog()
      .then((c) => setCatalog({ status: "ready", catalog: c }))
      .catch((e: unknown) =>
        setCatalog({ status: "error", message: e instanceof Error ? e.message : "Falha ao carregar o catálogo." }),
      );
  }, [backend]);

  // O catálogo do serviço exige conta; o de exemplo abre direto.
  useEffect(() => {
    if (backend.mode === "exemplo" || account) reloadCatalog();
  }, [backend, account?.userId, reloadCatalog]);

  useEffect(() => {
    if (!account) {
      setSync(null);
      return;
    }
    const e = new SyncEngine(backend, account.userId);
    engine.current = e;
    const off = e.subscribe(setSync);
    void e.start();
    return () => {
      off();
      e.stop();
      engine.current = null;
    };
  }, [backend, account?.userId]);

  // Progresso do personagem: relido depois de cada sincronização concluída.
  const lastSynced = sync?.lastSyncedAt;
  useEffect(() => {
    if (!account) {
      setProgress(null);
      return;
    }
    let alive = true;
    setProgress(null);
    (backend.forAccount?.(account.userId) ?? backend)
      .progressSummary()
      .then((s) => alive && setProgress(s))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [backend, account?.userId, lastSynced]);

  useEffect(() => {
    const up = () => {
      setOnline(true);
      engine.current?.schedule(0);
    };
    const down = () => setOnline(false);
    const visible = () => {
      if (document.visibilityState === "visible") engine.current?.schedule(0);
    };
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    document.addEventListener("visibilitychange", visible);
    // Busca alterações de outros dispositivos de tempos em tempos, só com a aba visível.
    const poll = window.setInterval(() => {
      if (document.visibilityState === "visible") engine.current?.schedule(0);
    }, 120_000);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
      document.removeEventListener("visibilitychange", visible);
      window.clearInterval(poll);
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (prefs.motion === "system") root.removeAttribute("data-motion");
    else root.setAttribute("data-motion", prefs.motion);
  }, [prefs.motion]);

  const setPrefs = useCallback((patch: Partial<Prefs>) => {
    setPrefsState((p) => {
      const next = { ...p, ...patch };
      savePrefs(next);
      return next;
    });
  }, []);

  const closeToast = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const toast = useCallback(
    (text: string, tone: Toast["tone"] = "info") => {
      toastId.current += 1;
      const id = toastId.current;
      setToasts((t) => [...t.slice(-2), { id, text, tone }]);
      window.setTimeout(() => closeToast(id), 5000);
    },
    [closeToast],
  );

  const enqueue = useCallback(
    async <K extends EventKind>(kind: K, entityId: string, payload: Payloads[K], id?: string) => {
      if (!engine.current) throw new Error("Entre na sua conta para salvar.");
      return engine.current.enqueue(kind, entityId, payload, id);
    },
    [],
  );

  const value: RumoContext = {
    backend,
    account,
    authReady,
    catalog,
    reloadCatalog,
    sync,
    progress,
    online,
    enqueue,
    syncNow: async () => engine.current?.sync(),
    resolveConflict: async (id, choice) => engine.current?.resolve(id, choice),
    dismiss: async (id) => engine.current?.dismiss(id),
    prefs,
    setPrefs,
    toasts,
    toast,
    closeToast,
  };
  return <Ctx.Provider value={value}><Fragment key={account?.userId ?? "signed-out"}>{children}</Fragment></Ctx.Provider>;
}

export function useRumo(): RumoContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRumo fora do RumoProvider");
  return ctx;
}

/** Catálogo pronto (as telas que dependem dele usam <CatalogGate>). */
export function useCatalog(): Catalog {
  const { catalog } = useRumo();
  if (catalog.status !== "ready") throw new Error("Catálogo ainda não carregado");
  return catalog.catalog;
}
