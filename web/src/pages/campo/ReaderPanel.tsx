import { Bookmark, Layers, Pencil, Search, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Confirm, EmptyState } from "../../components/ui";
import type { NoteState } from "../../domain/projection";
import type { OutlineItem } from "../../domain/types";
import { searchPdf, type PDFDocumentProxy, type SearchHit } from "./pdf";

export type PanelTab = "indice" | "busca" | "notas" | "marcadores";

export function OutlinePanel({ outline, current, onGo }: { outline: OutlineItem[]; current: number; onGo: (page: number) => void }) {
  if (!outline.length) return <EmptyState compact title="Sem índice">Este PDF não traz índice. Use a busca ou a numeração das páginas.</EmptyState>;
  const active = [...outline].reverse().find((o) => o.page <= current)?.page;
  return (
    <ol className="outline">
      {outline.map((item) => (
        <li key={`${item.page}-${item.title}`}>
          <button type="button" aria-current={item.page === active ? "true" : undefined} onClick={() => onGo(item.page)}>
            <span className="grow">{item.title}</span>
            <span className="tabular faint">{item.page}</span>
          </button>
        </li>
      ))}
    </ol>
  );
}

export function SearchPanel({
  doc,
  query,
  setQuery,
  onGo,
}: {
  doc: PDFDocumentProxy;
  query: string;
  setQuery: (q: string) => void;
  onGo: (page: number) => void;
}) {
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const signal = { cancelled: false };
    if (query.trim().length < 2) {
      setHits(null);
      return;
    }
    setBusy(true);
    const t = window.setTimeout(() => {
      void searchPdf(doc, query, signal).then((h) => {
        if (!signal.cancelled) {
          setHits(h);
          setBusy(false);
        }
      });
    }, 300);
    return () => {
      signal.cancelled = true;
      window.clearTimeout(t);
    };
  }, [doc, query]);
  return (
    <div className="stack">
      <label className="search">
        <Search size={16} aria-hidden="true" />
        <span className="sr-only">Buscar no PDF</span>
        <input className="input" type="search" placeholder="Buscar no PDF" value={query} onChange={(e) => setQuery(e.target.value)} data-autofocus />
      </label>
      <p className="xs faint" aria-live="polite">
        {busy ? "Buscando…" : hits ? `${hits.length} ${hits.length === 1 ? "ocorrência" : "ocorrências"}` : "Digite pelo menos 2 letras. Acentos não importam."}
      </p>
      {hits && hits.length > 0 && (
        <ul className="hits">
          {hits.map((h, i) => (
            <li key={i}>
              <button type="button" onClick={() => onGo(h.page)}>
                <span className="xs faint">Página {h.page}</span>
                <span className="small">{h.snippet}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function NotesPanel({
  notes,
  current,
  onSave,
  onDelete,
  onCard,
  onGo,
}: {
  notes: NoteState[];
  current: number;
  onSave: (text: string, page: number | null, id?: string) => Promise<void>;
  onDelete: (note: NoteState) => Promise<void>;
  onCard: (note: NoteState) => void;
  onGo: (page: number) => void;
}) {
  const [text, setText] = useState("");
  const [link, setLink] = useState(true);
  const [editing, setEditing] = useState<NoteState | null>(null);
  const [removing, setRemoving] = useState<NoteState | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    await onSave(text.trim(), editing ? editing.page : link ? current : null, editing?.id);
    setText("");
    setEditing(null);
  };

  return (
    <div className="stack">
      <form className="stack" onSubmit={submit}>
        <label className="sr-only" htmlFor="nota-texto">
          {editing ? "Editar nota" : "Nova nota"}
        </label>
        <textarea
          id="nota-texto"
          className="textarea"
          placeholder={editing ? "Editar nota" : `Nota sobre a página ${current}…`}
          value={text}
          maxLength={20000}
          onChange={(e) => setText(e.target.value)}
        />
        {!editing && (
          <label className="check small">
            <input type="checkbox" checked={link} onChange={(e) => setLink(e.target.checked)} /> Ligar à página {current}
          </label>
        )}
        <div className="row">
          <button className="btn sm" type="submit" disabled={!text.trim()}>
            {editing ? "Salvar alteração" : "Salvar nota"}
          </button>
          {editing && (
            <button
              className="btn ghost sm"
              type="button"
              onClick={() => {
                setEditing(null);
                setText("");
              }}
            >
              Cancelar
            </button>
          )}
        </div>
      </form>
      {notes.length === 0 ? (
        <p className="small muted">Nenhuma nota nesta aula. Notas não alteram o PDF e aparecem no aplicativo depois da sincronização.</p>
      ) : (
        <ul className="notes">
          {notes.map((n) => (
            <li key={n.id} className="note">
              <p className="note-text">{n.text}</p>
              <div className="row">
                {n.page ? (
                  <button type="button" className="link-btn xs" onClick={() => onGo(n.page!)}>
                    Página {n.page}
                  </button>
                ) : (
                  <span className="xs faint">Aula toda</span>
                )}
                {n.origin === "pending" && <span className="xs faint">· enviando</span>}
                <span className="spacer" />
                <button type="button" className="icon-btn sm" aria-label="Criar flashcard desta nota" title="Criar flashcard" onClick={() => onCard(n)}>
                  <Layers size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="icon-btn sm"
                  aria-label="Editar nota"
                  onClick={() => {
                    setEditing(n);
                    setText(n.text);
                  }}
                >
                  <Pencil size={14} aria-hidden="true" />
                </button>
                <button type="button" className="icon-btn sm" aria-label="Excluir nota" onClick={() => setRemoving(n)}>
                  <Trash2 size={14} aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {removing && (
        <Confirm
          title="Excluir esta nota?"
          message={`A nota${removing.page ? ` da página ${removing.page}` : ""} “${removing.text.slice(0, 80)}${removing.text.length > 80 ? "…" : ""}” será excluída aqui e no aplicativo.`}
          confirmLabel="Excluir nota"
          onCancel={() => setRemoving(null)}
          onConfirm={() => {
            void onDelete(removing);
            setRemoving(null);
          }}
        />
      )}
    </div>
  );
}

export function BookmarksPanel({ pages, onGo }: { pages: number[]; onGo: (page: number) => void }) {
  if (!pages.length)
    return (
      <EmptyState compact icon={<Bookmark size={24} aria-hidden="true" />} title="Sem marcadores">
        Use o marcador na barra do leitor para guardar páginas importantes.
      </EmptyState>
    );
  return (
    <ol className="outline">
      {pages.map((page) => (
        <li key={page}>
          <button type="button" onClick={() => onGo(page)}>
            <Bookmark size={14} aria-hidden="true" /> <span className="grow">Página {page}</span>
          </button>
        </li>
      ))}
    </ol>
  );
}
