import { ArrowLeft, Layers, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { EmptyState, ExampleTag, Loading } from "../../components/ui";
import { plural } from "../../lib/format";
import { useCatalog } from "../../service/store";
import { subjectName, topicName } from "../campo/lessons";
import { CardEditor } from "./CardEditor";
import { CardRow } from "./CardRow";
import { deckStats } from "./CardsHome";
import { PERSONAL_PREFIX, useCardViews } from "./useCards";

const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

export default function DeckView() {
  const { deckId = "" } = useParams();
  const catalog = useCatalog();
  const data = useCardViews();
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  if (!data) return <div className="page"><Loading /></div>;
  const deck = data.decks.find((d) => d.id === deckId);
  if (!deck) {
    return (
      <div className="page">
        <EmptyState title="Deck indisponível" action={<Link className="btn" to="/flashcards">Voltar aos flashcards</Link>}>
          Este deck não existe mais ou ainda não foi sincronizado.
        </EmptyState>
      </div>
    );
  }
  const stats = deckStats(data.views, deck);
  const cards = data.views.filter((v) => v.card.deckId === deck.id && (!q || fold(`${v.card.front} ${v.card.back}`).includes(fold(q))));

  return (
    <div className="page">
      <Link to="/flashcards" className="back-link">
        <ArrowLeft size={16} aria-hidden="true" /> Flashcards
      </Link>
      <div className="page-head">
        <div className="titles">
          <span className="row wrap">
            <h1>{deck.title}</h1>
            {deck.example && <ExampleTag />}
          </span>
          <p>
            {deck.subjectId ? subjectName(catalog, deck.subjectId) : "Geral"}
            {deck.topicId ? ` › ${topicName(catalog, deck.topicId)}` : ""} · {plural(stats.total, "cartão", "cartões")}
            {deck.description ? ` · ${deck.description}` : ""}
          </p>
        </div>
        <div className="row">
          {deck.personal && (
            <button type="button" className="btn" onClick={() => setCreating(true)}>
              <Plus size={16} aria-hidden="true" /> Novo cartão
            </button>
          )}
          {(stats.due > 0 || stats.fresh > 0) && (
            <Link to={`/flashcards/revisar?deck=${encodeURIComponent(deck.id)}${stats.due ? "" : "&novos=1"}`} className={`btn${stats.due ? " primary" : ""}`}>
              <Layers size={16} aria-hidden="true" /> {stats.due ? `Revisar ${stats.due}` : `Estudar ${Math.min(stats.fresh, 20)} novos`}
            </Link>
          )}
        </div>
      </div>

      {stats.total === 0 ? (
        <EmptyState title="Este deck ainda não tem cartões" action={deck.personal ? <button className="btn" type="button" onClick={() => setCreating(true)}>Criar o primeiro cartão</button> : undefined}>
          {deck.personal ? "Escreva perguntas curtas com uma resposta só." : "Quando o deck for publicado com cartões, eles aparecem aqui."}
        </EmptyState>
      ) : (
        <>
          <label className="search">
            <Search size={16} aria-hidden="true" />
            <span className="sr-only">Buscar neste deck</span>
            <input className="input" type="search" placeholder="Buscar neste deck" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          {cards.length ? (
            <ul className="list surface flush">
              {cards.map((v) => (
                <CardRow key={v.card.id} view={v} />
              ))}
            </ul>
          ) : (
            <EmptyState compact title="Nenhum cartão com esta busca" />
          )}
        </>
      )}
      {creating && (
        <CardEditor
          draft={{ deckId: deck.id.startsWith(PERSONAL_PREFIX) ? deck.id : undefined, subjectId: deck.subjectId, front: "", back: "", explanation: "", source: "", lessonId: null, questionId: null }}
          onClose={() => setCreating(false)}
        />
      )}
    </div>
  );
}
