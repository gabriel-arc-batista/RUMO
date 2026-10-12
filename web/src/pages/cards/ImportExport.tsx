import { Download, Upload } from "lucide-react";
import { useState, type ChangeEvent } from "react";
import { Dialog } from "../../components/ui";
import { uuid } from "../../lib/ids";
import { useRumo } from "../../service/store";
import type { CardView } from "./useCards";
import { PERSONAL_PREFIX } from "./useCards";

/** Formato documentado em docs/integration/FLASHCARDS.md. */
const FORMAT = "RUMO-personal-cards";
const MAX_BYTES = 2 * 1024 * 1024;
const MAX_CARDS = 1000;
const MAX_TEXT = 20000;

interface Draft {
  deck_id: string;
  front: string;
  back: string;
  explanation: string;
  source: string;
  lesson_id: string | null;
  question_id: string | null;
  keep: boolean;
}

export function exportCards(views: CardView[]) {
  const cards = views
    .filter((v) => v.card.personal)
    .map(({ card }) => ({
      id: card.id,
      revision: card.version,
      deck_id: card.deckId,
      front: card.front,
      back: card.back,
      explanation: card.explanation,
      source: card.source,
      lesson_id: card.lessonId,
      question_id: card.questionId,
      suspended: card.suspended,
      deleted: false,
    }));
  const blob = new Blob([JSON.stringify({ format: FORMAT, version: 1, cards }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `rumo-cartoes-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  return cards.length;
}

function text(value: unknown): string {
  return typeof value === "string" ? value.slice(0, MAX_TEXT) : "";
}

export function parseImport(raw: string): { drafts: Draft[]; skipped: number } {
  const data = JSON.parse(raw) as { format?: unknown; version?: unknown; cards?: unknown };
  if (data.format !== FORMAT || data.version !== 1 || !Array.isArray(data.cards)) {
    throw new Error("O arquivo não está no formato de cartões do RUMO (versão 1).");
  }
  if (data.cards.length > MAX_CARDS) throw new Error(`O arquivo tem mais de ${MAX_CARDS} cartões.`);
  let skipped = 0;
  const drafts: Draft[] = [];
  for (const item of data.cards as Record<string, unknown>[]) {
    const front = text(item?.front).trim();
    const back = text(item?.back).trim();
    if (!front || !back || item?.deleted === true) {
      skipped += 1;
      continue;
    }
    const deck = text(item.deck_id);
    drafts.push({
      // Metadados de id e revisão são descartados: cada importado é um cartão novo.
      deck_id: deck.startsWith(PERSONAL_PREFIX) ? deck : `${PERSONAL_PREFIX}geral`,
      front,
      back,
      explanation: text(item.explanation),
      source: text(item.source),
      lesson_id: text(item.lesson_id) || null,
      question_id: text(item.question_id) || null,
      keep: true,
    });
  }
  return { drafts, skipped };
}

export function ImportExportDialog({ views, onClose }: { views: CardView[]; onClose: () => void }) {
  const { enqueue, toast } = useRumo();
  const [drafts, setDrafts] = useState<Draft[] | null>(null);
  const [skipped, setSkipped] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const personal = views.filter((v) => v.card.personal).length;

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError("O arquivo passa de 2 MiB.");
      return;
    }
    try {
      const result = parseImport(await file.text());
      setDrafts(result.drafts);
      setSkipped(result.skipped);
    } catch (err) {
      setError(err instanceof SyntaxError ? "O arquivo não é um JSON válido." : (err as Error).message);
    }
  };

  const confirm = async () => {
    if (!drafts) return;
    setBusy(true);
    const chosen = drafts.filter((d) => d.keep);
    for (const d of chosen) {
      const { keep: _keep, ...payload } = d;
      await enqueue("card.save", uuid(), { ...payload, suspended: false, deleted: false });
    }
    setBusy(false);
    toast(`${chosen.length} ${chosen.length === 1 ? "cartão importado" : "cartões importados"}. Revisões e XP não são importados.`);
    onClose();
  };

  return (
    <Dialog title="Importar e exportar cartões" onClose={onClose} wide>
      <section className="stack">
        <h3>Exportar</h3>
        <p className="small muted">
          Baixa seus {personal} cartões pessoais em JSON (<code>{FORMAT}</code>, versão 1). Cartões de decks publicados e o histórico de revisões não entram.
        </p>
        <div>
          <button
            type="button"
            className="btn"
            disabled={!personal}
            onClick={() => {
              const n = exportCards(views);
              toast(`${n} ${n === 1 ? "cartão exportado" : "cartões exportados"}.`);
            }}
          >
            <Download size={16} aria-hidden="true" /> Exportar cartões pessoais
          </button>
        </div>
      </section>
      <hr className="divider" />
      <section className="stack">
        <h3>Importar</h3>
        <p className="small muted">Até 2 MiB e 1.000 cartões. Cada cartão importado vira um rascunho; confira e escolha quais criar.</p>
        <label className="btn" style={{ alignSelf: "flex-start" }}>
          <Upload size={16} aria-hidden="true" /> Escolher arquivo JSON
          <input type="file" accept="application/json,.json" className="sr-only" onChange={(e) => void onFile(e)} />
        </label>
        {error && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}
        {drafts && (
          <div className="stack">
            <p className="small">
              {drafts.length} {drafts.length === 1 ? "cartão encontrado" : "cartões encontrados"}
              {skipped ? ` · ${skipped} ignorado(s) sem frente/verso ou excluídos` : ""}.
            </p>
            <ul className="list surface flush import-list">
              {drafts.map((d, i) => (
                <li key={i} className="list-row">
                  <label className="check grow">
                    <input
                      type="checkbox"
                      checked={d.keep}
                      onChange={(e) => setDrafts(drafts.map((x, j) => (j === i ? { ...x, keep: e.target.checked } : x)))}
                    />
                    <span className="stack" style={{ gap: 2 }}>
                      <span className="title small">{d.front.slice(0, 120)}</span>
                      <span className="meta xs">{d.back.slice(0, 120)}</span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            <div className="dialog-actions">
              <button className="btn" type="button" onClick={() => setDrafts(null)}>
                Cancelar importação
              </button>
              <button className="btn primary" type="button" disabled={busy || !drafts.some((d) => d.keep)} onClick={() => void confirm()}>
                Criar {drafts.filter((d) => d.keep).length} cartões
              </button>
            </div>
          </div>
        )}
      </section>
    </Dialog>
  );
}
