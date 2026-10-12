import { useState, type FormEvent } from "react";
import { Dialog } from "../../components/ui";
import { uuid } from "../../lib/ids";
import { useCatalog, useRumo } from "../../service/store";
import { PERSONAL_PREFIX } from "./useCards";

export interface CardDraft {
  id?: string;
  deckId?: string;
  subjectId?: string | null;
  front: string;
  back: string;
  explanation: string;
  source: string;
  lessonId: string | null;
  questionId: string | null;
  suspended?: boolean;
}

/**
 * Rascunho editável de cartão pessoal. Nada é salvo até "Salvar cartão";
 * a frente e o verso precisam estar preenchidos (contrato card.save).
 */
export function CardEditor({ draft, title, onClose }: { draft: CardDraft; title?: string; onClose: (saved: boolean) => void }) {
  const catalog = useCatalog();
  const { enqueue, toast } = useRumo();
  const initialDeck = draft.deckId ?? `${PERSONAL_PREFIX}${draft.subjectId ?? "geral"}`;
  const [deck, setDeck] = useState(initialDeck);
  const [front, setFront] = useState(draft.front);
  const [back, setBack] = useState(draft.back);
  const [explanation, setExplanation] = useState(draft.explanation);
  const [source, setSource] = useState(draft.source);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (!front.trim() || !back.trim()) return;
    setBusy(true);
    try {
      await enqueue("card.save", draft.id ?? uuid(), {
        deck_id: deck,
        front: front.trim(),
        back: back.trim(),
        explanation: explanation.trim(),
        source: source.trim(),
        lesson_id: draft.lessonId,
        question_id: draft.questionId,
        suspended: draft.suspended ?? false,
        deleted: false,
      });
      toast(draft.id ? "Cartão atualizado." : "Cartão criado. Ele entra nas revisões depois de sincronizar.");
      onClose(true);
    } finally {
      setBusy(false);
    }
  };

  const decks = [
    { id: `${PERSONAL_PREFIX}geral`, label: "Meus cartões — Geral" },
    ...catalog.subjects.map((s) => ({ id: `${PERSONAL_PREFIX}${s.id}`, label: `Meus cartões — ${s.name}` })),
  ];

  return (
    <Dialog title={title ?? (draft.id ? "Editar cartão" : "Novo cartão")} onClose={() => onClose(false)} wide>
      <form className="stack" onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="card-deck">Deck</label>
          <select id="card-deck" className="select" value={deck} onChange={(e) => setDeck(e.target.value)}>
            {decks.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="card-front">Frente (pergunta)</label>
          <textarea
            id="card-front"
            className="textarea"
            value={front}
            maxLength={20000}
            aria-invalid={tried && !front.trim()}
            aria-describedby={tried && !front.trim() ? "front-erro" : undefined}
            onChange={(e) => setFront(e.target.value)}
            data-autofocus
          />
          {tried && !front.trim() && (
            <span className="error-text" id="front-erro">
              Escreva a pergunta da frente.
            </span>
          )}
        </div>
        <div className="field">
          <label htmlFor="card-back">Verso (resposta)</label>
          <textarea
            id="card-back"
            className="textarea"
            value={back}
            maxLength={20000}
            aria-invalid={tried && !back.trim()}
            onChange={(e) => setBack(e.target.value)}
          />
          {tried && !back.trim() && <span className="error-text">Escreva a resposta do verso.</span>}
        </div>
        <div className="field">
          <label htmlFor="card-exp">Explicação (opcional)</label>
          <textarea id="card-exp" className="textarea" style={{ minHeight: 64 }} value={explanation} maxLength={20000} onChange={(e) => setExplanation(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="card-src">Referência (opcional)</label>
          <input id="card-src" className="input" value={source} maxLength={2000} onChange={(e) => setSource(e.target.value)} />
        </div>
        <div className="dialog-actions">
          <button className="btn" type="button" onClick={() => onClose(false)}>
            Descartar rascunho
          </button>
          <button className="btn primary" type="submit" disabled={busy}>
            Salvar cartão
          </button>
        </div>
      </form>
    </Dialog>
  );
}
