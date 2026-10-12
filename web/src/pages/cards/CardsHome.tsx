import { ArrowUpDown, Layers, MoreHorizontal, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { EmptyState, ExampleTag, Loading, Menu, Segmented } from "../../components/ui";
import type { Catalog, Deck } from "../../domain/types";
import { plural } from "../../lib/format";
import { useCatalog } from "../../service/store";
import { subjectName, topicName } from "../campo/lessons";
import { CardEditor } from "./CardEditor";
import { CardRow } from "./CardRow";
import { ImportExportDialog } from "./ImportExport";
import { useCardViews, type CardView } from "./useCards";

type View = "decks" | "todos" | "pessoais" | "suspensos";

const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

export function deckStats(views: CardView[], deck: Deck) {
  const own = views.filter((v) => v.card.deckId === deck.id);
  return {
    total: own.length,
    due: own.filter((v) => v.status === "vencido").length,
    fresh: own.filter((v) => v.status === "novo").length,
  };
}

function deckMatches(catalog: Catalog, deck: Deck, subject: string, topic: string) {
  if (subject && deck.subjectId !== subject) return false;
  if (topic && deck.topicId !== topic) return false;
  void catalog;
  return true;
}

export default function CardsHome() {
  const catalog = useCatalog();
  const data = useCardViews();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const view = (params.get("ver") as View) || "decks";
  const q = params.get("q") ?? "";
  const subject = params.get("materia") ?? "";
  const topic = params.get("assunto") ?? "";
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === "materia") next.delete("assunto");
    setParams(next, { replace: true });
  };

  const decks = data?.decks ?? [];
  const views = data?.views ?? [];
  const deckById = useMemo(() => new Map(decks.map((d) => [d.id, d])), [decks]);
  const filteredCards = views.filter((v) => {
    const deck = deckById.get(v.card.deckId);
    if (subject && deck?.subjectId !== subject) return false;
    if (topic && deck?.topicId !== topic) return false;
    if (q && !fold(`${v.card.front} ${v.card.back}`).includes(fold(q))) return false;
    if (view === "pessoais") return v.card.personal;
    if (view === "suspensos") return v.status === "suspenso";
    return true;
  });
  const shownDecks = decks.filter((d) => deckMatches(catalog, d, subject, topic) && (!q || fold(d.title).includes(fold(q))));
  const due = views.filter((v) => v.status === "vencido").length;
  const fresh = views.filter((v) => v.status === "novo").length;

  if (!data) return <div className="page"><Loading /></div>;

  return (
    <div className="page">
      <div className="page-head">
        <div className="titles">
          <h1>Flashcards</h1>
          <p>Revisão espaçada: cada cartão volta quando está perto de ser esquecido.</p>
        </div>
        <div className="row">
          <button type="button" className="btn" onClick={() => setCreating(true)}>
            <Plus size={16} aria-hidden="true" /> Novo cartão
          </button>
          <Menu
            label="Mais ações"
            icon={<MoreHorizontal size={18} aria-hidden="true" />}
            items={[{ label: "Importar ou exportar", icon: <ArrowUpDown size={14} aria-hidden="true" />, onSelect: () => setImporting(true) }]}
          />
        </div>
      </div>

      <section className="review-banner surface" aria-labelledby="revisoes-hoje">
        <div className="grow stack" style={{ gap: 4 }}>
          <h2 id="revisoes-hoje">{due ? `${plural(due, "cartão", "cartões")} para revisar` : "Nada vencido agora"}</h2>
          <p className="small muted">
            {due > 50
              ? "Acumulou um pouco, e tudo bem. Uma rodada de 20 já ajuda; o resto continua esperando sem pressa."
              : due
                ? "Uma rodada curta mantém a memória viva."
                : fresh
                  ? `Se quiser adiantar, há ${plural(fresh, "cartão novo", "cartões novos")}.`
                  : "Crie cartões a partir de notas do leitor ou de erros da Arena."}
          </p>
        </div>
        {due > 0 ? (
          <Link to="/flashcards/revisar" className="btn primary lg">
            <Layers size={18} aria-hidden="true" /> Revisar {due > 20 ? "20 agora" : "agora"}
          </Link>
        ) : (
          fresh > 0 && (
            <Link to="/flashcards/revisar?novos=1" className="btn">
              Estudar cartões novos
            </Link>
          )
        )}
      </section>

      <div className="filters">
        <label className="search grow">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Buscar cartões ou decks</span>
          <input className="input" type="search" placeholder="Buscar cartões ou decks" value={q} onChange={(e) => set("q", e.target.value)} />
        </label>
        <select className="select" aria-label="Matéria" value={subject} onChange={(e) => set("materia", e.target.value)}>
          <option value="">Todas as matérias</option>
          {catalog.subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select className="select" aria-label="Assunto" value={topic} onChange={(e) => set("assunto", e.target.value)}>
          <option value="">Todos os assuntos</option>
          {catalog.topics
            .filter((t) => !subject || t.subjectId === subject)
            .map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
        </select>
      </div>

      <Segmented<View>
        label="Mostrar"
        value={view}
        onChange={(v) => set("ver", v === "decks" ? "" : v)}
        options={[
          { value: "decks", label: "Decks", count: shownDecks.length },
          { value: "todos", label: "Todos os cartões" },
          { value: "pessoais", label: "Pessoais", count: views.filter((v) => v.card.personal).length },
          { value: "suspensos", label: "Suspensos", count: views.filter((v) => v.status === "suspenso").length },
        ]}
      />

      {view === "decks" ? (
        shownDecks.length ? (
          <ul className="list surface flush">
            {shownDecks.map((deck) => {
              const s = deckStats(views, deck);
              return (
                <li key={deck.id}>
                  <Link to={`/flashcards/deck/${encodeURIComponent(deck.id)}`} className="list-row">
                    <div className="grow stack" style={{ gap: 4 }}>
                      <span className="row wrap">
                        <span className="title">{deck.title}</span>
                        {deck.example && <ExampleTag />}
                        {deck.personal && <span className="tag">Pessoal</span>}
                      </span>
                      <span className="meta">
                        {deck.subjectId ? subjectName(catalog, deck.subjectId) : "Geral"}
                        {deck.topicId ? ` › ${topicName(catalog, deck.topicId)}` : ""} · {s.total ? plural(s.total, "cartão", "cartões") : "sem cartões ainda"}
                      </span>
                    </div>
                    {s.due > 0 && <span className="tag gold">{s.due} para revisar</span>}
                    {!s.due && s.fresh > 0 && <span className="tag info">{s.fresh} novos</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : (
          <EmptyState compact title={q || subject || topic ? "Nenhum deck com estes filtros" : "Ainda não há decks"}>
            {q || subject || topic ? "Limpe a busca ou escolha outra matéria." : "Decks publicados aparecem aqui. Seus cartões pessoais formam decks por matéria."}
          </EmptyState>
        )
      ) : filteredCards.length ? (
        <ul className="list surface flush">
          {filteredCards.map((v) => (
            <CardRow key={v.card.id} view={v} deckTitle={deckById.get(v.card.deckId)?.title} />
          ))}
        </ul>
      ) : (
        <EmptyState compact title={view === "suspensos" ? "Nenhum cartão suspenso" : view === "pessoais" ? "Você ainda não criou cartões" : "Nenhum cartão com estes filtros"}>
          {view === "pessoais" && "Use “Novo cartão”, uma nota do leitor ou um erro da Arena."}
        </EmptyState>
      )}

      {creating && (
        <CardEditor
          draft={{ subjectId: subject || null, front: "", back: "", explanation: "", source: "", lessonId: null, questionId: null }}
          onClose={() => setCreating(false)}
        />
      )}
      {importing && <ImportExportDialog views={views} onClose={() => setImporting(false)} />}
    </div>
  );
}
