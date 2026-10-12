import { CloudOff, RefreshCw } from "lucide-react";
import { describeEvent, remoteDescription } from "../domain/describe";
import { relativeDay } from "../lib/format";
import { ERROR_TEXT } from "../service/contract";
import { useRumo } from "../service/store";
import { Dialog } from "./ui";

export function syncLabel(state: string | undefined, pending: number): string {
  switch (state) {
    case "offline":
      return pending ? `Sem conexão · ${pending} guardado${pending > 1 ? "s" : ""}` : "Sem conexão";
    case "syncing":
      return "Sincronizando…";
    case "pending":
      return `${pending} para enviar`;
    case "synced":
      return "Sincronizado";
    case "conflict":
      return "Conflito para resolver";
    case "error":
      return "Falha ao sincronizar";
    default:
      return "Preparando…";
  }
}

export function SyncPill({ onOpen }: { onOpen: () => void }) {
  const { sync } = useRumo();
  const state = sync?.state ?? "pending";
  return (
    <button
      type="button"
      className="sync-pill"
      data-state={state}
      onClick={onOpen}
      aria-label={`Sincronização: ${syncLabel(state, sync?.pending ?? 0)}. Abrir detalhes.`}
    >
      {state === "syncing" ? <span className="spinner" aria-hidden="true" /> : state === "offline" ? <CloudOff size={14} aria-hidden="true" /> : <span className="dot" aria-hidden="true" />}
      <span className="desktop-only">{syncLabel(state, sync?.pending ?? 0)}</span>
    </button>
  );
}

export function SyncPanel({ onClose }: { onClose: () => void }) {
  const { sync, syncNow, resolveConflict, dismiss, catalog, backend } = useRumo();
  const cat = catalog.status === "ready" ? catalog.catalog : null;
  if (!sync) return null;
  return (
    <Dialog
      title="Sincronização"
      onClose={onClose}
      wide
      actions={
        <>
          <button className="btn" type="button" onClick={onClose}>
            Fechar
          </button>
          <button className="btn primary" type="button" onClick={() => void syncNow()} disabled={sync.state === "syncing"}>
            <RefreshCw size={16} aria-hidden="true" /> Sincronizar agora
          </button>
        </>
      }
    >
      <div className="stack">
        <p>
          <strong>{syncLabel(sync.state, sync.pending)}</strong>
          {sync.lastSyncedAt && <span className="muted"> · última sincronização {relativeDay(sync.lastSyncedAt)}, às {new Date(sync.lastSyncedAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>}
        </p>
        {sync.message && <div className="notice warning">{sync.message}</div>}
        <p className="small muted">
          {backend.mode === "exemplo"
            ? "Modo exemplo: o “serviço” é simulado neste navegador. Nada é enviado para fora."
            : "Leituras, notas, favoritos, respostas da Arena, cartões pessoais, revisões e sessões explícitas são enviados à sua conta. Ações feitas sem conexão ficam guardadas neste navegador até serem aceitas pelo serviço."}
        </p>
        {sync.pending > 0 && (
          <p className="small">
            {sync.pending} {sync.pending === 1 ? "ação aguarda" : "ações aguardam"} confirmação do serviço. Elas continuam valendo neste navegador.
          </p>
        )}
      </div>

      {sync.conflicts.length > 0 && (
        <section className="stack" aria-labelledby="conflitos">
          <h3 id="conflitos">Conflitos</h3>
          <p className="small muted">Isto mudou em outro dispositivo depois da sua ação. Escolha o que fica; nada é descartado sem a sua escolha.</p>
          <ul className="list surface flush">
            {sync.conflicts.map((item) => (
              <li key={item.id} className="list-row" style={{ flexWrap: "wrap" }}>
                <div className="grow stack" style={{ gap: 2 }}>
                  <span className="title">Sua ação: {describeEvent(item.envelope, cat)}</span>
                  <span className="meta">{remoteDescription(item.envelope, sync.projection)}</span>
                </div>
                <div className="row">
                  <button className="btn sm" type="button" onClick={() => void resolveConflict(item.id, "theirs")}>
                    Manter a do serviço
                  </button>
                  <button className="btn sm" type="button" onClick={() => void resolveConflict(item.id, "mine")}>
                    Aplicar a minha
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {sync.rejected.length > 0 && (
        <section className="stack" aria-labelledby="recusadas">
          <h3 id="recusadas">Recusadas pelo serviço</h3>
          <ul className="list surface flush">
            {sync.rejected.map((item) => (
              <li key={item.id} className="list-row" style={{ flexWrap: "wrap" }}>
                <div className="grow stack" style={{ gap: 2 }}>
                  <span className="title">{describeEvent(item.envelope, cat)}</span>
                  <span className="meta">{item.error ? ERROR_TEXT[item.error] : ""}</span>
                </div>
                <button className="btn sm" type="button" onClick={() => void dismiss(item.id)}>
                  Remover da fila
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Dialog>
  );
}
