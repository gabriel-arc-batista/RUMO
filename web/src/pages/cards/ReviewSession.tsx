import { ArrowLeft, Eye, Layers } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { StudyTimer, useStudyTimer } from "../../components/StudyTimer";
import { Confirm, EmptyState, ExampleTag, Loading, ProgressBar } from "../../components/ui";
import { cardClassification, sessionSubject } from "../../domain/practice";
import type { ReviewResult } from "../../domain/types";
import { plural } from "../../lib/format";
import { SingleAction } from "../../lib/singleAction";
import { useCatalog, useRumo } from "../../service/store";
import { studiedTopics, topicScope } from "../../domain/learning";
import { useCardViews, type CardView } from "./useCards";

const RATINGS = [
  { value: 1, label: "Errei", hint: "não lembrei", key: "1" },
  { value: 2, label: "Difícil", hint: "com esforço", key: "2" },
  { value: 3, label: "Bom", hint: "lembrei", key: "3" },
  { value: 4, label: "Fácil", hint: "na hora", key: "4" },
] as const;

const SESSION_SIZE = 20;

export default function ReviewSession() {
  const data = useCardViews();
  const [params] = useSearchParams();
  const catalog = useCatalog();
  const { sync } = useRumo();
  if (!data) return <div className="page"><Loading /></div>;
  const deckSubject = (deckId: string) => data.decks.find((d) => d.id === deckId)?.subjectId ?? null;
  const studied = studiedTopics(catalog, sync?.projection);
  const scope = params.get("assunto") ? topicScope(catalog, params.get("assunto")!) : null;
  const views = data.views.filter((view) => {
    const c = cardClassification(view.card, catalog, data.decks);
    if (params.get("materia") && c.subjectId !== params.get("materia")) return false;
    if (scope && !c.topicIds.some((id) => scope.has(id))) return false;
    return params.get("estudados") !== "1" || (c.topicIds.length > 0 && c.topicIds.every((id) => studied.has(id)));
  });
  return <Review key={params.toString()} views={views} deckId={params.get("deck")} fresh={params.get("novos") === "1"} deckSubject={deckSubject} />;
}

function Review({
  views,
  deckId,
  fresh,
  deckSubject,
}: {
  views: CardView[];
  deckId: string | null;
  fresh: boolean;
  deckSubject: (deckId: string) => string | null;
}) {
  const { enqueue, sync, prefs, toast } = useRumo();
  const navigate = useNavigate();
  // Fila fixada ao abrir: vencidos primeiro (os mais antigos antes); novos só se pedidos.
  const [queue] = useState(() => {
    const eligible = views.filter((v) => !v.unsynced && v.status !== "suspenso" && (!deckId || v.card.deckId === deckId));
    const due = eligible.filter((v) => v.status === "vencido").sort((a, b) => (a.dueAt ?? "").localeCompare(b.dueAt ?? ""));
    const news = fresh || !due.length ? eligible.filter((v) => v.status === "novo") : [];
    return [...due, ...news].slice(0, SESSION_SIZE).map((v) => v.card);
  });
  const skippedUnsynced = views.filter((v) => v.unsynced && (!deckId || v.card.deckId === deckId)).length;
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [done, setDone] = useState<{ cardId: string; reviewId: string; rating: number }[]>([]);
  const [ending, setEnding] = useState(false);
  const [finished, setFinished] = useState(false);
  const timer = useStudyTimer(`revisao.${deckId ?? "todos"}`);
  const actions = useRef(new SingleAction());
  const revealRef = useRef<HTMLButtonElement>(null);
  const backRef = useRef<HTMLDivElement>(null);
  const card = queue[index];
  const subjectId = sessionSubject(queue.map((c) => deckSubject(c.deckId)));

  const rate = useCallback(
    async (rating: 1 | 2 | 3 | 4) => {
      if (!card || !revealed) return;
      try {
        await actions.current.run(`${timer.sessionId}:${card.id}:${index}`, async (reviewId) => {
          await enqueue("card.review", reviewId, { card_id: card.id, version: card.version, rating, session_id: timer.sessionId }, reviewId);
          setDone((d) => [...d, { cardId: card.id, reviewId, rating }]);
          setRevealed(false);
          if (index + 1 < queue.length) setIndex(index + 1);
          else setFinished(true);
        });
      } catch {
        toast("Não foi possível guardar a revisão. Avalie novamente para tentar salvar.", "error");
      }
    },
    [card, revealed, enqueue, toast, timer.sessionId, index, queue.length],
  );

  useEffect(() => {
    if (revealed) backRef.current?.focus();
    else revealRef.current?.focus();
  }, [revealed, index]);

  // Teclado: Espaço/Enter revela; 1–4 avaliam (só depois de revelar).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement).tagName) || finished) return;
      if (!revealed && (e.key === " " || e.key === "Enter") && (e.target as HTMLElement).tagName !== "BUTTON") {
        e.preventDefault();
        setRevealed(true);
      } else if (revealed && ["1", "2", "3", "4"].includes(e.key)) {
        e.preventDefault();
        void rate(Number(e.key) as 1 | 2 | 3 | 4);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [revealed, rate, finished]);

  const lastResult = useMemo(() => {
    const last = done.at(-1);
    if (!last || !sync) return null;
    const review = sync.projection.reviews.find((r) => r.id === last.reviewId);
    return review?.result ? (review.result as ReviewResult) : null;
  }, [done, sync]);

  if (!queue.length) {
    return (
      <div className="page">
        <EmptyState
          icon={<Layers size={28} aria-hidden="true" />}
          title="Nada para revisar agora"
          action={
            <Link to="/flashcards" className="btn">
              Voltar aos flashcards
            </Link>
          }
        >
          {skippedUnsynced
            ? `${plural(skippedUnsynced, "cartão novo aguarda", "cartões novos aguardam")} sincronização antes de entrar nas revisões.`
            : "Os cartões voltam quando o serviço os agenda. Enquanto isso, a Arena e o Campo estão abertos."}
        </EmptyState>
      </div>
    );
  }

  if (finished) {
    const count = (r: number) => done.filter((d) => d.rating === r).length;
    return (
      <div className="page">
        <div className="page-head">
          <div className="titles">
            <h1>Rodada concluída</h1>
            <p>{plural(done.length, "cartão revisado", "cartões revisados")}. Cada um volta na data que o serviço calcular.</p>
          </div>
        </div>
        <section className="surface stack">
          <div className="stat-row">
            {RATINGS.map((r) => (
              <div className="stat" key={r.value}>
                <span className="value">{count(r.value)}</span>
                <span className="label">{r.label}</span>
              </div>
            ))}
          </div>
          {timer.elapsed >= 60 && (
            <div className="stack" style={{ gap: 6 }}>
              <span className="small">Registrar o tempo desta revisão (opcional):</span>
              <StudyTimer timer={timer} category="Revisão" subjectId={subjectId} topicId={null} />
            </div>
          )}
        </section>
        <div className="row">
          <Link to="/flashcards" className="btn primary">
            Voltar aos flashcards
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page review-page">
      <h1 className="sr-only">Revisão de flashcards</h1>
      <div className="arena-bar">
        <button type="button" className="btn ghost sm" onClick={() => (done.length ? setEnding(true) : navigate("/flashcards"))}>
          <ArrowLeft size={16} aria-hidden="true" /> Encerrar
        </button>
        <div className="grow stack" style={{ gap: 4 }}>
          <span className="small muted tabular">
            Cartão {index + 1} de {queue.length}
          </span>
          <ProgressBar value={index} max={queue.length} label="Progresso da rodada" />
        </div>
        <div data-decor>
          <StudyTimer timer={timer} category="Revisão" subjectId={subjectId} topicId={null} compact />
        </div>
      </div>

      <article className="flashcard surface" aria-live="polite">
        <div className="row wrap" style={{ justifyContent: "space-between" }}>
          <span className="xs muted">{card.personal ? "Cartão pessoal" : "Deck publicado"}</span>
          {card.example && <ExampleTag />}
        </div>
        <div className="card-face">
          <h2 className="sr-only">Frente</h2>
          <p className="card-question">{card.front}</p>
        </div>

        {!revealed ? (
          <div className="stack" style={{ alignItems: "center" }}>
            <button ref={revealRef} type="button" className="btn primary lg" onClick={() => setRevealed(true)}>
              <Eye size={18} aria-hidden="true" /> Mostrar resposta
            </button>
            <span className="xs faint">
              ou tecle <kbd className="kbd">Espaço</kbd>
            </span>
          </div>
        ) : (
          <>
            <div ref={backRef} tabIndex={-1} className="card-back">
              <h2 className="sr-only">Verso</h2>
              <p className="card-answer">{card.back}</p>
              {card.explanation && <p className="muted">{card.explanation}</p>}
              {card.source && <p className="xs faint">Referência: {card.source}</p>}
            </div>
            <div className="stack" style={{ gap: "var(--s2)" }}>
              <p className="small muted" id="avaliacao-ajuda">
                Como foi lembrar? Sua avaliação ajuda o serviço a decidir quando este cartão volta.
              </p>
              <div className="ratings" role="group" aria-describedby="avaliacao-ajuda">
                {RATINGS.map((r) => (
                  <button key={r.value} type="button" className={`btn rating r${r.value}`} onClick={() => void rate(r.value)}>
                    <span>{r.label}</span>
                    <span className="rating-hint">{r.hint}</span>
                    <kbd className="kbd" aria-hidden="true">
                      {r.key}
                    </kbd>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </article>
      {lastResult && (
        <p className="xs faint" role="status">
          Cartão anterior: volta em {plural(lastResult.interval_days, "dia", "dias")}{prefs.rpgEffects ? ". Memória reforçada." : "."}
        </p>
      )}
      {ending && (
        <Confirm
          title="Encerrar a rodada agora?"
          message={`${plural(done.length, "avaliação já está salva", "avaliações já estão salvas")}. Os cartões que faltam continuam esperando, sem pressa.`}
          confirmLabel="Encerrar rodada"
          onCancel={() => setEnding(false)}
          onConfirm={() => {
            setEnding(false);
            setFinished(true);
          }}
        />
      )}
    </div>
  );
}
