import { ArrowLeft, Check, CircleSlash, Clock, Layers, NotebookPen, RotateCcw, Star, Swords, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { StudyTimer, useStudyTimer } from "../../components/StudyTimer";
import { Confirm, EmptyState, ExampleTag, ProgressBar } from "../../components/ui";
import { attemptsFor, isFavorite, type AttemptState } from "../../domain/projection";
import { practiceStatistics, sessionSubject } from "../../domain/practice";
import type { Question } from "../../domain/types";
import { compactDuration, plural } from "../../lib/format";
import { uuid } from "../../lib/ids";
import { SingleAction } from "../../lib/singleAction";
import { entity } from "../../service/contract";
import { useCatalog, useRumo } from "../../service/store";
import { CardEditor, type CardDraft } from "../cards/CardEditor";
import { subjectName, topicName } from "../campo/lessons";
import { plainStatement, readFilters, selectQuestions, toParams } from "./arena";
import { Options, Statement } from "./QuestionView";

/** Cada combinação de filtros é uma sessão nova (revanche inclusive). */
export default function ArenaSessionRoute() {
  const location = useLocation();
  return <ArenaSession key={location.key} />;
}

function ArenaSession() {
  const catalog = useCatalog();
  const { sync, enqueue, prefs, online, toast } = useRumo();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const filters = readFilters(params);
  const p = sync?.projection;

  // A lista é fixada ao entrar: responder não tira a questão da sessão.
  const [ids] = useState(() => selectQuestions(catalog, p, filters).map((q) => q.id));
  const questions = useMemo(() => ids.map((id) => catalog.questions.find((q) => q.id === id)).filter(Boolean) as Question[], [ids, catalog]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [attemptIds, setAttemptIds] = useState<Record<string, string>>({});
  const [finished, setFinished] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [cardDraft, setCardDraft] = useState<CardDraft | null>(null);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const timer = useStudyTimer(`arena.${params.toString()}`);
  const sessionStart = useRef(timer.sessionId);
  const actions = useRef(new SingleAction());
  const confirmRef = useRef<HTMLButtonElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  const question = questions[index];
  const attempt: AttemptState | null = question && attemptIds[question.id] ? (p?.attempts.get(attemptIds[question.id]) ?? null) : null;
  const history = question && p ? attemptsFor(p, question.id).filter((a) => a.id !== attemptIds[question.id]) : [];

  useEffect(() => {
    if (attempt?.result) resultRef.current?.focus();
  }, [attempt?.result]);

  if (!questions.length) {
    return (
      <div className="page">
        <EmptyState
          icon={<Swords size={28} aria-hidden="true" />}
          title="Nenhuma questão para esta sessão"
          action={
            <Link className="btn" to={`/arena?${toParams(filters).toString()}`}>
              Ajustar filtros
            </Link>
          }
        >
          {filters.mode === "erros" ? "Você não tem erros pendentes nestes filtros. Bom sinal." : "Os filtros escolhidos não têm questões no catálogo."}
        </EmptyState>
      </div>
    );
  }

  const confirm = async () => {
    if (!selected || !question) return;
    try {
      await actions.current.run(`${timer.sessionId}:${question.id}`, async (id) => {
        await enqueue(
          "arena.attempt", id,
          { question_id: question.id, version: question.version, answer: selected, session_id: timer.sessionId }, id,
        );
        setAttemptIds((m) => ({ ...m, [question.id]: id }));
      });
    } catch {
      toast("Não foi possível guardar a resposta. Tente confirmar novamente.", "error");
    }
  };

  const next = () => {
    setSelected(null);
    setNoteOpen(false);
    if (index + 1 < questions.length) setIndex(index + 1);
    else setFinished(true);
  };

  const favorite = question && p ? isFavorite(p, "question", question.id) : false;
  const toggleFavorite = () =>
    void enqueue("favorite.set", entity.favorite("question", question.id, ""), {
      target_type: "question",
      target_id: question.id,
      version: "",
      favorite: !favorite,
    });

  const questionNotes = p && question ? [...p.notes.values()].filter((n) => n.questionId === question.id && !n.deleted) : [];
  const saveNote = async () => {
    if (!noteText.trim()) return;
    await enqueue("note.save", uuid(), { lesson_id: null, question_id: question.id, version: question.version, page: null, text: noteText.trim(), deleted: false });
    setNoteText("");
    setNoteOpen(false);
  };

  const errorDraft = (q: Question, a: AttemptState): CardDraft => {
    const key = q.options.find((o) => o.id === a.result?.answer);
    return {
      subjectId: q.subjectId,
      front: plainStatement(q).slice(0, 1200),
      back: key ? `${q.type === "certo_errado" ? "" : `${key.id.toUpperCase()}) `}${key.text}` : "",
      explanation: a.result?.comment ?? "",
      source: q.provenance.label,
      lessonId: null,
      questionId: q.id,
    };
  };

  const sessionAttempts = Object.values(attemptIds)
    .map((id) => p?.attempts.get(id))
    .filter(Boolean) as AttemptState[];

  if (finished) {
    return (
      <Summary
        attempts={sessionAttempts}
        total={questions.length}
        questions={questions}
        timer={<StudyTimer timer={timer} category={filters.mode === "simulado" ? "Simulado" : "Questões"} subjectId={sessionSubject(questions.map((q) => q.subjectId))} topicId={filters.topic || null} />}
        registered={p?.sessions.get(sessionStart.current)?.payload.elapsed ?? null}
        elapsed={timer.elapsed}
        onCard={(q, a) => setCardDraft(errorDraft(q, a))}
        cardDraft={cardDraft}
        closeCard={() => setCardDraft(null)}
        filters={toParams(filters).toString()}
      />
    );
  }

  const status = attempt?.result?.status;
  return (
    <div className="page arena-page">
      <h1 className="sr-only">
        Arena: questão {index + 1} de {questions.length}
      </h1>
      <div className="arena-bar">
        <button type="button" className="btn ghost sm" onClick={() => (sessionAttempts.length ? setLeaving(true) : navigate("/arena"))}>
          <ArrowLeft size={16} aria-hidden="true" /> Sair
        </button>
        <div className="grow stack" style={{ gap: 4 }}>
          <span className="small muted tabular">
            Questão {index + 1} de {questions.length}
          </span>
          <ProgressBar value={index + (attempt ? 1 : 0)} max={questions.length} label="Progresso da sessão" />
        </div>
        {prefs.arenaTimer && (
          <div data-decor>
            <StudyTimer timer={timer} category={filters.mode === "simulado" ? "Simulado" : "Questões"} subjectId={sessionSubject(questions.map((q) => q.subjectId))} topicId={filters.topic || null} compact />
          </div>
        )}
      </div>

      <article className="question surface" aria-labelledby="enunciado">
        <header className="row wrap question-meta">
          <span className="small muted">
            {subjectName(catalog, question.subjectId)} › {question.topicIds.map((t) => topicName(catalog, t)).join(", ")}
          </span>
          <span className="spacer" />
          {question.example && <ExampleTag />}
          {question.annulled && <span className="tag warning">Anulada</span>}
          <span className="tag">{question.type === "certo_errado" ? "Certo ou errado" : "Múltipla escolha"}</span>
          <button type="button" className="icon-btn sm" aria-pressed={favorite} onClick={toggleFavorite} aria-label={favorite ? "Remover questão das favoritas" : "Favoritar questão"}>
            <Star size={16} aria-hidden="true" fill={favorite ? "currentColor" : "none"} />
          </button>
        </header>
        <h2 id="enunciado" className="sr-only">
          Enunciado
        </h2>
        <Statement blocks={question.statement} />
        <p className="xs faint">
          {question.provenance.label}
          {question.provenance.bank ? ` · ${question.provenance.bank}` : ""}
          {question.provenance.year ? ` · ${question.provenance.year}` : ""} · versão {question.version}
        </p>

        <Options question={question} selected={selected} onSelect={setSelected} attempt={attempt} locked={Boolean(attempt)} />

        {!attempt && (
          <div className="row wrap confirm-row">
            <span className="small muted grow">{selected ? "Confira e confirme. A resposta só é registrada ao confirmar." : "Escolha uma alternativa."}</span>
            <button ref={confirmRef} type="button" className="btn primary lg" disabled={!selected} onClick={() => void confirm()}>
              Confirmar resposta
            </button>
          </div>
        )}

        {attempt && (
          <div ref={resultRef} tabIndex={-1} className={`result ${status ?? "pending"}`} role="status" aria-live="polite">
            {!status ? (
              <p className="row">
                <Clock size={18} aria-hidden="true" />
                {online && sync?.state !== "offline"
                  ? "Resposta registrada. Aguardando a correção do serviço…"
                  : "Resposta guardada neste navegador. A correção aparece quando a conexão voltar; você pode seguir para a próxima."}
              </p>
            ) : (
              <>
                <p className="result-title row">
                  {status === "correct" ? <Check size={20} aria-hidden="true" /> : status === "annulled" ? <CircleSlash size={20} aria-hidden="true" /> : <X size={20} aria-hidden="true" />}
                  {status === "correct" ? "Você acertou." : status === "annulled" ? "Questão anulada: não conta como acerto nem erro." : "Não foi desta vez."}
                  {prefs.rpgEffects && status === "correct" && (
                    <span className="rpg-line">
                      {history.some((h) => h.version === question.version && h.result?.status === "correct")
                        ? "Golpe certeiro."
                        : "Vitória: primeira vez que você vence esta questão."}
                    </span>
                  )}
                  {prefs.rpgEffects && status === "incorrect" && <span className="rpg-line">Todo erro aqui é treino para a prova.</span>}
                </p>
                {attempt.result?.comment ? (
                  <div className="comment">
                    <h3>Explicação</h3>
                    <p>{attempt.result.comment}</p>
                  </div>
                ) : (
                  <p className="small muted">O serviço ainda não envia gabarito e explicação para esta questão.</p>
                )}
              </>
            )}
            {history.length > 0 && (
              <p className="xs faint">
                Respostas anteriores: {history.map((h) => (h.result?.status === "correct" ? "acerto" : h.result?.status === "incorrect" ? "erro" : h.result ? "anulada" : "pendente")).join(", ")}.
              </p>
            )}
            <div className="row wrap">
              {status === "incorrect" && (
                <button type="button" className="btn" onClick={() => setCardDraft(errorDraft(question, attempt))}>
                  <Layers size={16} aria-hidden="true" /> Criar flashcard do erro
                </button>
              )}
              <button type="button" className="btn ghost" onClick={() => setNoteOpen((o) => !o)} aria-expanded={noteOpen}>
                <NotebookPen size={16} aria-hidden="true" /> Anotação{questionNotes.length ? ` (${questionNotes.length})` : ""}
              </button>
              <span className="spacer" />
              <button type="button" className="btn primary" onClick={next}>
                {index + 1 < questions.length ? "Próxima questão" : "Ver resultado da sessão"}
              </button>
            </div>
            {noteOpen && (
              <div className="stack">
                {questionNotes.map((n) => (
                  <p key={n.id} className="note-text small">
                    {n.text}
                  </p>
                ))}
                <label className="sr-only" htmlFor="nota-questao">
                  Anotação sobre a questão
                </label>
                <textarea id="nota-questao" className="textarea" placeholder="O que vale lembrar desta questão?" value={noteText} onChange={(e) => setNoteText(e.target.value)} />
                <div>
                  <button type="button" className="btn sm" disabled={!noteText.trim()} onClick={() => void saveNote()}>
                    Salvar anotação
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </article>

      {leaving && (
        <Confirm
          title="Encerrar a sessão agora?"
          message={`As ${sessionAttempts.length} respostas confirmadas já estão salvas. O tempo do cronômetro (${compactDuration(timer.elapsed)}) só entra no histórico se você registrar no resumo.`}
          confirmLabel="Ver resumo e encerrar"
          onCancel={() => setLeaving(false)}
          onConfirm={() => {
            setLeaving(false);
            setFinished(true);
          }}
        />
      )}
      {cardDraft && <CardEditor draft={cardDraft} title="Criar flashcard do erro" onClose={() => setCardDraft(null)} />}
    </div>
  );
}

function Summary({
  attempts,
  total,
  questions,
  timer,
  registered,
  elapsed,
  onCard,
  cardDraft,
  closeCard,
  filters,
}: {
  attempts: AttemptState[];
  total: number;
  questions: Question[];
  timer: React.ReactNode;
  registered: number | null;
  elapsed: number;
  onCard: (q: Question, a: AttemptState) => void;
  cardDraft: CardDraft | null;
  closeCard: () => void;
  filters: string;
}) {
  const catalog = useCatalog();
  const stats = practiceStatistics(attempts.map((a) => {
    const q = questions.find((q) => q.id === a.questionId);
    return { id: a.id, subjectId: q?.subjectId ?? null, topicIds: q?.topicIds ?? [], outcome: a.result?.status ?? "pending" };
  }));
  const correct = attempts.filter((a) => a.result?.status === "correct").length;
  const wrong = attempts.filter((a) => a.result?.status === "incorrect");
  const annulled = attempts.filter((a) => a.result?.status === "annulled").length;
  const waiting = attempts.filter((a) => !a.result).length;
  return (
    <div className="page">
      <div className="page-head">
        <div className="titles">
          <h1>Resultado da sessão</h1>
          <p>
            {plural(attempts.length, "questão respondida", "questões respondidas")} de {total} selecionadas.
          </p>
        </div>
      </div>
      <section className="surface stack" aria-label="Números da sessão">
        <div className="stat-row">
          <div className="stat">
            <span className="value">{attempts.length}</span>
            <span className="label">respondidas</span>
          </div>
          <div className="stat">
            <span className="value">{correct}</span>
            <span className="label">acertos</span>
          </div>
          <div className="stat">
            <span className="value">{wrong.length}</span>
            <span className="label">erros</span>
          </div>
          {annulled > 0 && (
            <div className="stat">
              <span className="value">{annulled}</span>
              <span className="label">anuladas</span>
            </div>
          )}
          {waiting > 0 && (
            <div className="stat">
              <span className="value">{waiting}</span>
              <span className="label">aguardando correção</span>
            </div>
          )}
          <div className="stat">
            <span className="value">{registered !== null ? compactDuration(registered) : "—"}</span>
            <span className="label">tempo registrado</span>
          </div>
        </div>
        {stats.subjects.size > 1 && (
          <table>
            <caption>Resultados por matéria</caption>
            <thead><tr><th scope="col">Matéria</th><th scope="col">Acertos</th><th scope="col">Erros</th><th scope="col">Pendentes</th></tr></thead>
            <tbody>{[...stats.subjects].map(([id, count]) => <tr key={id}><th scope="row">{catalog.subjects.find((s) => s.id === id)?.name ?? "Sem classificação"}</th><td>{count.correct}</td><td>{count.incorrect}</td><td>{count.pending}</td></tr>)}</tbody>
          </table>
        )}
        <p className="small muted">
          Isto descreve esta sessão, não o seu domínio do assunto. Com poucas questões, um número alto ou baixo diz pouco; o histórico ao longo dos dias diz mais.
        </p>
        {registered === null && (
          <div className="stack" style={{ gap: 6 }}>
            <span className="small">{elapsed >= 60 ? "O tempo cronometrado ainda não foi registrado:" : "Nenhum tempo cronometrado nesta sessão (registrar é opcional)."}</span>
            {elapsed >= 60 && timer}
          </div>
        )}
      </section>

      {wrong.length > 0 && (
        <section className="section" aria-labelledby="erros-sessao">
          <h2 id="erros-sessao">Para revisar</h2>
          <ul className="list surface flush">
            {wrong.map((a) => {
              const q = questions.find((x) => x.id === a.questionId);
              if (!q) return null;
              return (
                <li key={a.id} className="list-row" style={{ flexWrap: "wrap" }}>
                  <span className="grow small">{plainStatement(q).slice(0, 160)}…</span>
                  <button type="button" className="btn sm" onClick={() => onCard(q, a)}>
                    <Layers size={14} aria-hidden="true" /> Criar flashcard
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <div className="row wrap">
        <Link to="/arena" className="btn">
          Voltar à Arena
        </Link>
        {wrong.length > 0 && (
          <Link to={`/arena/sessao?${new URLSearchParams({ ...Object.fromEntries(new URLSearchParams(filters)), modo: "erros" }).toString()}`} className="btn primary">
            <RotateCcw size={16} aria-hidden="true" /> Revanche dos erros
          </Link>
        )}
      </div>
      {cardDraft && <CardEditor draft={cardDraft} title="Criar flashcard do erro" onClose={closeCard} />}
    </div>
  );
}
