import { BookOpen, CheckCircle2, Search, Star } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { EmptyState, ExampleTag, ProgressBar, Segmented } from "../../components/ui";
import type { Catalog, Lesson } from "../../domain/types";
import { plural } from "../../lib/format";
import { useCatalog, useRumo } from "../../service/store";
import { favoriteEntity, lessonPath, lessonProgress, subjectName, topicName, type LessonProgress } from "./lessons";

type View = "todas" | "andamento" | "favoritas" | "planejadas";

const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

function matches(catalog: Catalog, lesson: Lesson, query: string) {
  if (!query) return true;
  const hay = fold(
    [lesson.title, lesson.summary, subjectName(catalog, lesson.subjectId), ...lesson.topicIds.map((t) => topicName(catalog, t))].join(" "),
  );
  return fold(query)
    .split(/\s+/)
    .every((word) => hay.includes(word));
}

export default function Library() {
  const catalog = useCatalog();
  const { sync, enqueue } = useRumo();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const exam = params.get("edital") ?? "";
  const view = (params.get("ver") as View) || "todas";
  const p = sync?.projection;

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const withProgress = useMemo(
    () => catalog.lessons.map((lesson) => ({ lesson, progress: lessonProgress(p, lesson) })),
    [catalog, p],
  );
  const base = withProgress.filter(({ lesson }) => (!exam || lesson.examIds.includes(exam)) && matches(catalog, lesson, query));
  const counts = {
    todas: base.filter((x) => x.lesson.status === "disponivel").length,
    andamento: base.filter((x) => x.progress.started && !x.progress.complete).length,
    favoritas: base.filter((x) => x.progress.favorite).length,
    planejadas: base.filter((x) => x.lesson.status === "planejada").length,
  };
  const shown = base.filter(({ lesson, progress }) => {
    if (view === "andamento") return progress.started && !progress.complete;
    if (view === "favoritas") return progress.favorite;
    if (view === "planejadas") return lesson.status === "planejada";
    return lesson.status === "disponivel";
  });

  // Matéria → assunto → aulas, na ordem do catálogo.
  const groups = new Map<string, Map<string, typeof shown>>();
  for (const item of shown) {
    const subject = item.lesson.subjectId;
    const topic = item.lesson.topicIds[0] ?? "";
    if (!groups.has(subject)) groups.set(subject, new Map());
    const topics = groups.get(subject)!;
    if (!topics.has(topic)) topics.set(topic, []);
    topics.get(topic)!.push(item);
  }

  const toggleFavorite = (lesson: Lesson, favorite: boolean) =>
    void enqueue("favorite.set", favoriteEntity("lesson", lesson.id, ""), {
      target_type: "lesson",
      target_id: lesson.id,
      version: "",
      favorite,
    });

  const filtered = Boolean(query || exam);
  const emptyCatalog = catalog.lessons.length === 0;

  return (
    <div className="page">
      <div className="page-head">
        <div className="titles">
          <h1>Campo de Treinamento</h1>
          <p>Aulas em PDF para ler e marcar página por página.</p>
        </div>
      </div>

      {emptyCatalog ? (
        <EmptyState icon={<BookOpen size={28} aria-hidden="true" />} title="Ainda não há aulas publicadas">
          Quando houver aulas revisadas no catálogo, elas aparecem aqui. Aulas planejadas também aparecem, identificadas como planejadas.
        </EmptyState>
      ) : (
        <>
          <div className="filters">
            <label className="search grow">
              <Search size={16} aria-hidden="true" />
              <span className="sr-only">Buscar aula, matéria ou assunto</span>
              <input className="input" type="search" placeholder="Buscar aula, matéria ou assunto" value={query} onChange={(e) => set("q", e.target.value)} />
            </label>
            <label className="field-inline">
              <span className="sr-only">Edital-alvo</span>
              <select className="select" value={exam} onChange={(e) => set("edital", e.target.value)} aria-label="Filtrar pelo edital-alvo">
                <option value="">Todos os editais</option>
                {catalog.exams.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Segmented<View>
            label="Mostrar"
            value={view}
            onChange={(v) => set("ver", v === "todas" ? "" : v)}
            options={[
              { value: "todas", label: "Disponíveis", count: counts.todas },
              { value: "andamento", label: "Em andamento", count: counts.andamento },
              { value: "favoritas", label: "Favoritas", count: counts.favoritas },
              { value: "planejadas", label: "Planejadas", count: counts.planejadas },
            ]}
          />

          {shown.length === 0 ? (
            <EmptyState
              compact
              title={
                filtered
                  ? "Nenhuma aula com estes filtros"
                  : view === "andamento"
                    ? "Nenhuma aula em andamento"
                    : view === "favoritas"
                      ? "Nenhuma aula favorita"
                      : view === "planejadas"
                        ? "Nenhuma aula planejada"
                        : "Nenhuma aula disponível"
              }
              action={
                filtered ? (
                  <button className="btn" type="button" onClick={() => setParams(view === "todas" ? {} : { ver: view }, { replace: true })}>
                    Limpar busca e edital
                  </button>
                ) : undefined
              }
            >
              {!filtered && view === "andamento" && "Ao abrir uma aula e marcar páginas, ela aparece aqui."}
              {!filtered && view === "favoritas" && "Use a estrela de uma aula para encontrá-la depressa."}
            </EmptyState>
          ) : (
            <div className="stack" style={{ gap: "var(--s5)" }}>
              {[...groups.entries()].map(([subjectId, topics]) => (
                <section key={subjectId} className="section" aria-labelledby={`m-${subjectId}`}>
                  <div className="section-head">
                    <h2 id={`m-${subjectId}`}>{subjectName(catalog, subjectId)}</h2>
                  </div>
                  <div className="surface flush">
                    {[...topics.entries()].map(([topicId, items]) => (
                      <div key={topicId} className="topic-group">
                        <h3 className="topic-title">{topicName(catalog, topicId)}</h3>
                        <ul className="list">
                          {items.map(({ lesson, progress }) => (
                            <LessonRow key={lesson.id} lesson={lesson} progress={progress} onFavorite={toggleFavorite} />
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
          <p className="small faint">
            {plural(catalog.lessons.filter((l) => l.status === "disponivel").length, "aula disponível", "aulas disponíveis")} ·{" "}
            {plural(catalog.lessons.filter((l) => l.status === "planejada").length, "planejada", "planejadas")}. Planejadas ainda não têm PDF publicado.
          </p>
        </>
      )}
    </div>
  );
}

function LessonRow({
  lesson,
  progress,
  onFavorite,
}: {
  lesson: Lesson;
  progress: LessonProgress;
  onFavorite: (lesson: Lesson, favorite: boolean) => void;
}) {
  const planned = lesson.status === "planejada";
  return (
    <li className="lesson-row">
      <Link to={lessonPath(lesson)} className="list-row grow">
        <div className="grow stack" style={{ gap: 4 }}>
          <span className="title lesson-title">{lesson.title}</span>
          <span className="row wrap meta">
            {planned ? (
              <span className="tag">Planejada</span>
            ) : progress.complete ? (
              <span className="tag success">
                <CheckCircle2 size={12} aria-hidden="true" /> Concluída
              </span>
            ) : progress.read ? (
              <span className="tabular">
                {progress.read} de {progress.pages} páginas lidas
              </span>
            ) : (
              <span>{lesson.pages ? `${lesson.pages} páginas` : "PDF"}</span>
            )}
            {lesson.example && <ExampleTag />}
          </span>
          {!planned && progress.read > 0 && !progress.complete && (
            <ProgressBar value={progress.read} max={progress.pages} label={`${progress.read} de ${progress.pages} páginas marcadas como lidas`} />
          )}
        </div>
      </Link>
      <button
        type="button"
        className="icon-btn"
        aria-pressed={progress.favorite}
        aria-label={progress.favorite ? `Remover “${lesson.title}” das favoritas` : `Favoritar “${lesson.title}”`}
        onClick={() => onFavorite(lesson, !progress.favorite)}
      >
        <Star size={18} aria-hidden="true" fill={progress.favorite ? "currentColor" : "none"} />
      </button>
    </li>
  );
}
