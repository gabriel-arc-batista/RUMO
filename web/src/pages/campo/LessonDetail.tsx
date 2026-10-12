import { ArrowLeft, BookOpen, CheckCircle2, ExternalLink, Star, Swords } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { EmptyState, ExampleTag, ProgressBar } from "../../components/ui";
import { shortDate } from "../../lib/format";
import { useCatalog, useRumo } from "../../service/store";
import { favoriteEntity, lessonPath, lessonProgress, subjectName, topicName } from "./lessons";

const REVIEW_TEXT = {
  aprovada: "Revisão aprovada",
  pendente: "Revisão pendente",
  em_revisao: "Em revisão",
};

export default function LessonDetail() {
  const { lessonId = "" } = useParams();
  const catalog = useCatalog();
  const { sync, enqueue } = useRumo();
  const lesson = catalog.lessons.find((l) => l.id === lessonId);
  if (!lesson) {
    return (
      <div className="page">
        <EmptyState
          title="Aula indisponível"
          action={
            <Link className="btn" to="/campo">
              Voltar ao Campo
            </Link>
          }
        >
          Esta aula não está no catálogo atual. Ela pode ter sido retirada ou o endereço mudou.
        </EmptyState>
      </div>
    );
  }
  const progress = lessonProgress(sync?.projection, lesson);
  const planned = lesson.status === "planejada";
  const related = catalog.lessons.filter(
    (l) => l.id !== lesson.id && (l.topicIds.some((t) => lesson.topicIds.includes(t)) || lesson.prerequisiteTopicIds.some((t) => l.topicIds.includes(t))),
  );
  const notes = sync ? [...sync.projection.notes.values()].filter((n) => n.lessonId === lesson.id && n.version === lesson.version && !n.deleted) : [];
  const questions = catalog.questions.filter((q) => q.topicIds.some((t) => lesson.topicIds.includes(t)));
  const readerPath = `${lessonPath(lesson)}/ler`;

  return (
    <div className="page">
      <Link to="/campo" className="back-link">
        <ArrowLeft size={16} aria-hidden="true" /> Campo de Treinamento
      </Link>

      <div className="lesson-head">
        <div className="stack" style={{ gap: "var(--s2)" }}>
          <p className="small muted">
            {subjectName(catalog, lesson.subjectId)} › {lesson.topicIds.map((t) => topicName(catalog, t)).join(", ")}
          </p>
          <h1 className="lesson-h1">{lesson.title}</h1>
          <div className="row wrap">
            {planned ? <span className="tag">Planejada: PDF ainda não publicado</span> : <span className="tag info">Disponível</span>}
            {lesson.example && <ExampleTag />}
            <span className="tag">{lesson.versionLabel}</span>
            <span className={`tag${lesson.review.status === "aprovada" ? " success" : ""}`}>
              {REVIEW_TEXT[lesson.review.status]}
              {lesson.review.reviewer ? ` por ${lesson.review.reviewer}` : ""}
              {lesson.review.reviewedAt ? ` em ${shortDate(lesson.review.reviewedAt)}` : ""}
            </span>
          </div>
          {lesson.summary && <p className="muted">{lesson.summary}</p>}
        </div>

        <div className="lesson-actions">
          {!planned && (
            <Link to={progress.position ? `${readerPath}?pagina=${progress.position}` : readerPath} className="btn primary lg">
              <BookOpen size={18} aria-hidden="true" />
              {progress.position ? `Continuar da página ${progress.position}` : "Começar leitura"}
            </Link>
          )}
          <button
            type="button"
            className="btn"
            aria-pressed={progress.favorite}
            onClick={() =>
              void enqueue("favorite.set", favoriteEntity("lesson", lesson.id, ""), {
                target_type: "lesson",
                target_id: lesson.id,
                version: "",
                favorite: !progress.favorite,
              })
            }
          >
            <Star size={16} aria-hidden="true" fill={progress.favorite ? "currentColor" : "none"} />
            {progress.favorite ? "Favorita" : "Favoritar"}
          </button>
        </div>
      </div>

      {!planned && lesson.pages && (
        <section className="surface stack" aria-labelledby="progresso-aula">
          <h2 id="progresso-aula" className="row" style={{ fontSize: "var(--text-md)" }}>
            {progress.complete ? (
              <>
                <CheckCircle2 size={18} className="success-ic" aria-hidden="true" /> Aula concluída
              </>
            ) : (
              "Leitura"
            )}
          </h2>
          <p className="tabular">
            <strong>
              {progress.read} de {progress.pages} páginas
            </strong>{" "}
            marcadas como lidas
            {progress.position ? <span className="muted"> · você parou na página {progress.position}</span> : null}
          </p>
          <ProgressBar value={progress.read} max={progress.pages} label="Páginas marcadas como lidas" />
          <p className="xs faint">A aula só conta como concluída com todas as páginas marcadas, incluindo a última. Abrir ou rolar não marca leitura.</p>
        </section>
      )}

      <div className="detail-grid">
        <section className="section" aria-labelledby="objetivos">
          <h2 id="objetivos">Objetivos</h2>
          {lesson.objectives.length ? (
            <ul className="bullets">
              {lesson.objectives.map((o) => (
                <li key={o}>{o}</li>
              ))}
            </ul>
          ) : (
            <p className="muted small">O catálogo ainda não informa objetivos para esta aula.</p>
          )}

          <h2 id="prereq">Pré-requisitos sugeridos</h2>
          {lesson.prerequisiteTopicIds.length ? (
            <ul className="bullets">
              {lesson.prerequisiteTopicIds.map((t) => (
                <li key={t}>{topicName(catalog, t)}</li>
              ))}
            </ul>
          ) : (
            <p className="muted small">Nenhum. Dá para começar por aqui.</p>
          )}
          <p className="xs faint">Sugestões de ordem, não bloqueios: todas as aulas ficam abertas.</p>

          <h2 id="fontes">Fontes</h2>
          {lesson.sources.length ? (
            <ul className="bullets">
              {lesson.sources.map((s) => (
                <li key={s.title}>
                  {s.url ? (
                    <a href={s.url} target="_blank" rel="noopener noreferrer">
                      {s.title} <ExternalLink size={12} aria-label="(abre em nova aba)" />
                    </a>
                  ) : (
                    s.title
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">Fontes ainda não informadas.</p>
          )}
        </section>

        <aside className="stack" style={{ gap: "var(--s5)" }}>
          <section className="section" aria-labelledby="relacionados">
            <h2 id="relacionados">Assuntos relacionados</h2>
            {related.length ? (
              <ul className="list surface flush">
                {related.map((l) => (
                  <li key={l.id}>
                    <Link to={lessonPath(l)} className="list-row">
                      <span className="grow stack" style={{ gap: 2 }}>
                        <span className="title lesson-title">{l.title}</span>
                        <span className="meta">
                          {topicName(catalog, l.topicIds[0])} · {l.status === "planejada" ? "planejada" : "disponível"}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small">Nenhuma outra aula ligada a estes assuntos.</p>
            )}
          </section>

          {questions.length > 0 && (
            <section className="section" aria-labelledby="praticar">
              <h2 id="praticar">Praticar</h2>
              <Link to={`/arena/sessao?assunto=${encodeURIComponent(lesson.topicIds[0])}`} className="btn">
                <Swords size={16} aria-hidden="true" /> {questions.length} {questions.length === 1 ? "questão" : "questões"} deste assunto
              </Link>
            </section>
          )}

          <section className="section" aria-labelledby="notas-aula">
            <h2 id="notas-aula">Suas notas</h2>
            {notes.length ? (
              <ul className="list surface flush">
                {notes.map((n) => (
                  <li key={n.id}>
                    <Link to={`${readerPath}?pagina=${n.page ?? 1}&painel=notas`} className="list-row">
                      <span className="grow stack" style={{ gap: 2 }}>
                        <span className="note-text">{n.text}</span>
                        <span className="meta">{n.page ? `Página ${n.page}` : "Aula toda"}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small">{planned ? "Notas ficam disponíveis quando o PDF for publicado." : "Escreva notas no leitor; elas aparecem aqui e no aplicativo."}</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
