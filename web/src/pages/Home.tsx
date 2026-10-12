import { BookOpen, Layers, Swords } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { EquippedItems, ExampleTag, Portrait, ProgressBar } from "../components/ui";
import { useCharacter } from "../service/useCharacter";
import { isComplete, readPages, type Projection, type ReadingState } from "../domain/projection";
import type { Catalog, Lesson } from "../domain/types";
import { plural } from "../lib/format";
import { useCatalog, useRumo } from "../service/store";
import { useCardViews } from "./cards/useCards";

function greeting(date = new Date()) {
  const h = date.getHours();
  return h < 5 ? "Boa noite" : h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite";
}

function topicName(catalog: Catalog, id: string | undefined) {
  return catalog.topics.find((t) => t.id === id)?.name;
}

const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();

/** Próximo bloco do ciclo do app e, se houver, a matéria/assunto equivalentes no catálogo. */
function cycleContext(catalog: Catalog, cycle: NonNullable<Projection["cycle"]> | null | undefined) {
  if (!cycle || !cycle.items.length) return null;
  const next = cycle.items[cycle.position] ?? cycle.items.find((i) => !i.done);
  if (!next) return { next: null, plan: cycle.plan_name, subjectId: undefined, topicId: undefined };
  const subject = catalog.subjects.find((s) => fold(s.name) === fold(next.subject));
  const topic = next.topic
    ? catalog.topics.find((t) => fold(t.name) === fold(next.topic!) && (!subject || t.subjectId === subject.id))
    : undefined;
  return { next, plan: cycle.plan_name, subjectId: subject?.id ?? topic?.subjectId, topicId: topic?.id };
}

interface Resume {
  lesson: Lesson;
  page: number;
  read: number;
  complete: boolean;
}

function ResumeRow({
  icon,
  title,
  detail,
  action,
  primary,
  to,
  example,
}: {
  icon: ReactNode;
  title: ReactNode;
  detail: ReactNode;
  action: string;
  primary?: boolean;
  to: string;
  example?: boolean;
}) {
  return (
    <li className="resume-row">
      <span className="resume-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="grow stack" style={{ gap: 2 }}>
        <span className="row wrap">
          <span className="title">{title}</span>
          {example && <ExampleTag />}
        </span>
        <span className="meta">{detail}</span>
      </div>
      <Link to={to} className={`btn${primary ? " primary" : ""}`}>
        {action}
      </Link>
    </li>
  );
}

export function Home() {
  const catalog = useCatalog();
  const { sync, progress } = useRumo();
  const character = useCharacter();
  const cards = useCardViews();
  const p = sync?.projection;

  // Última aula: a posição de leitura mais recente (independente das páginas marcadas).
  let resume: Resume | null = null;
  if (p) {
    // Prefere a aula aberta mais recente que ainda não foi concluída.
    const candidates = [...p.reading.values()]
      .filter((r) => r.position)
      .sort((a, b) => (b.position!.at > a.position!.at ? 1 : -1))
      .map((r) => ({ r, lesson: catalog.lessons.find((l) => l.id === r.lessonId && l.version === r.version) }))
      .filter((x) => x.lesson) as { r: ReadingState; lesson: Lesson }[];
    const pick = candidates.find((x) => !isComplete(x.r, x.lesson.pages)) ?? candidates[0];
    if (pick)
      resume = {
        lesson: pick.lesson,
        page: pick.r.position!.page,
        read: readPages(pick.r).length,
        complete: isComplete(pick.r, pick.lesson.pages),
      };
  }

  // Assunto atual: o da última aula aberta ou, sem ela, o da última resposta na Arena.
  const lastAttempt = p ? [...p.attempts.values()].sort((a, b) => (b.at > a.at ? 1 : -1))[0] : undefined;
  const attemptTopic = lastAttempt && catalog.questions.find((q) => q.id === lastAttempt.questionId)?.topicIds[0];
  // O ciclo do app dá contexto (sem impor agenda): se o próximo bloco existe no catálogo, ele orienta.
  const ctx = p ? cycleContext(catalog, p.cycle) : null;
  const inProgress = resume && !resume.complete;
  const topicId = ctx?.topicId ?? resume?.lesson.topicIds[0] ?? attemptTopic;
  const topicQuestions = topicId ? catalog.questions.filter((q) => q.topicIds.includes(topicId)) : [];

  const due = cards?.views.filter((v) => v.status === "vencido").length ?? 0;
  const fresh = cards?.views.filter((v) => v.status === "novo").length ?? 0;
  const cycleLesson = ctx?.subjectId
    ? catalog.lessons.find(
        (l) => l.status === "disponivel" && l.subjectId === ctx.subjectId && (!ctx.topicId || l.topicIds.includes(ctx.topicId)),
      )
    : undefined;
  const firstAvailable = cycleLesson ?? catalog.lessons.find((l) => l.status === "disponivel");

  const rows: ReactNode[] = [];
  let gold = true;
  const takeGold = () => {
    const g = gold;
    gold = false;
    return g;
  };

  if (resume && !resume.complete) {
    rows.push(
      <ResumeRow
        key="aula"
        icon={<BookOpen size={20} />}
        title={resume.lesson.title}
        detail={`Parou na página ${resume.page} · ${resume.read} de ${resume.lesson.pages} páginas marcadas como lidas`}
        action="Continuar leitura"
        primary={takeGold()}
        to={`/campo/aula/${encodeURIComponent(resume.lesson.id)}/ler?pagina=${resume.page}`}
        example={resume.lesson.example}
      />,
    );
  } else if (resume && !cycleLesson) {
    rows.push(
      <ResumeRow
        key="aula"
        icon={<BookOpen size={20} />}
        title={`Aula concluída: ${resume.lesson.title}`}
        detail={`Todas as ${resume.lesson.pages} páginas marcadas. Escolha a próxima no Campo de Treinamento.`}
        action="Escolher a próxima aula"
        primary={takeGold()}
        to="/campo"
        example={resume.lesson.example}
      />,
    );
  } else if (cycleLesson && !inProgress) {
    rows.push(
      <ResumeRow
        key="aula"
        icon={<BookOpen size={20} />}
        title={cycleLesson.title}
        detail={ctx?.topicId ? "Aula do assunto que vem agora no seu ciclo." : "Aula da matéria que vem agora no seu ciclo."}
        action="Abrir aula"
        primary={takeGold()}
        to={`/campo/aula/${encodeURIComponent(cycleLesson.id)}`}
        example={cycleLesson.example}
      />,
    );
  } else if (firstAvailable) {
    rows.push(
      <ResumeRow
        key="aula"
        icon={<BookOpen size={20} />}
        title="Comece pelo Campo de Treinamento"
        detail={`${plural(catalog.lessons.filter((l) => l.status === "disponivel").length, "aula disponível", "aulas disponíveis")} para ler no site.`}
        action="Ver aulas"
        primary={takeGold()}
        to="/campo"
      />,
    );
  }

  // Ciclo só com matéria (sem assunto): sugere as questões da matéria inteira.
  const cycleSubjectQuestions =
    ctx?.subjectId && !ctx.topicId ? catalog.questions.filter((q) => q.subjectId === ctx.subjectId) : [];
  if (cycleSubjectQuestions.length) {
    rows.push(
      <ResumeRow
        key="arena"
        icon={<Swords size={20} />}
        title={`Questões de ${catalog.subjects.find((s) => s.id === ctx!.subjectId)?.name}`}
        detail={`${plural(cycleSubjectQuestions.length, "questão", "questões")} da matéria que vem agora no seu ciclo.`}
        action="Resolver questões"
        primary={takeGold()}
        to={`/arena/sessao?materia=${encodeURIComponent(ctx!.subjectId!)}`}
        example={cycleSubjectQuestions.some((q) => q.example)}
      />,
    );
  } else if (topicId && topicQuestions.length) {
    rows.push(
      <ResumeRow
        key="arena"
        icon={<Swords size={20} />}
        title={`Questões de ${topicName(catalog, topicId) ?? "o assunto atual"}`}
        detail={`${plural(topicQuestions.length, "questão", "questões")} deste assunto na Arena.`}
        action="Resolver questões"
        primary={takeGold()}
        to={`/arena/sessao?assunto=${encodeURIComponent(topicId)}`}
        example={topicQuestions.some((q) => q.example)}
      />,
    );
  } else if (catalog.questions.length) {
    rows.push(
      <ResumeRow
        key="arena"
        icon={<Swords size={20} />}
        title="Arena"
        detail="Escolha uma matéria e um assunto para resolver questões."
        action="Abrir a Arena"
        primary={takeGold()}
        to="/arena"
      />,
    );
  }

  if (cards) {
    rows.push(
      <ResumeRow
        key="cards"
        icon={<Layers size={20} />}
        title={due ? `${plural(due, "cartão", "cartões")} para revisar` : "Revisões em dia"}
        detail={
          due
            ? "Uma rodada curta já ajuda. Revise no seu ritmo, sem pressa de zerar."
            : fresh
              ? `Nada vencido agora. Há ${plural(fresh, "cartão novo", "cartões novos")} se quiser adiantar.`
              : "Nada vencido agora. Crie cartões a partir de notas ou erros da Arena."
        }
        action={due ? "Revisar agora" : "Ver flashcards"}
        primary={due ? takeGold() : false}
        to={due ? "/flashcards/revisar" : "/flashcards"}
      />,
    );
  }

  return (
    <div className="page">
      <div className="home">
        <section className="stack" style={{ gap: "var(--s5)" }} aria-labelledby="titulo-inicio">
          <div className="page-head">
            <div className="titles">
              <h1 id="titulo-inicio">{greeting()}</h1>
              <p>{new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</p>
            </div>
          </div>

          {ctx?.next && (
            <p className="cycle-line">
              <span className="muted">No ciclo do aplicativo{ctx.plan ? ` (${ctx.plan})` : ""}, agora:</span>{" "}
              <strong>{ctx.next.subject}</strong>
              {ctx.next.topic ? ` — ${ctx.next.topic}` : ""}
              <span className="muted">
                {" "}
                · {ctx.next.target_minutes} min de {ctx.next.category.toLowerCase()}
              </span>
            </p>
          )}

          {sync && sync.conflicts.length > 0 && (
            <p className="notice warning">Há {plural(sync.conflicts.length, "alteração", "alterações")} em conflito com outro dispositivo. Abra a sincronização no topo para escolher o que fica.</p>
          )}

          {!resume && !firstAvailable && !catalog.questions.length && (
            <p className="notice">
              Ainda não há aulas nem questões publicadas no catálogo. Quando houver conteúdo revisado, ele aparece aqui. Enquanto isso, seus cartões pessoais já funcionam.
            </p>
          )}

          <div className="section">
            <h2 className="sr-only">Retomar</h2>
            <ul className="resume surface flush">{rows}</ul>
          </div>
          {catalog.example && (
            <p className="small faint">
              O conteúdo marcado como EXEMPLO serve para testar o site. Não é aula, questão ou deck revisado.
            </p>
          )}
        </section>

        <aside className="home-character surface" data-decor aria-label="Seu viajante">
          <Portrait size={88} look={character.look} />
          <div className="stack" style={{ gap: 4, alignItems: "center", textAlign: "center" }}>
            <span className="name">{character.name}</span>
            <span className="small muted">{progress ? `Nível ${progress.level}` : "Progresso ao sincronizar"}</span>
          </div>
          {progress && (
            <div className="stack" style={{ gap: 6, width: "100%" }}>
              <ProgressBar value={progress.xp} max={progress.xp_next} label={`XP no nível ${progress.level}`} />
              <span className="xs muted tabular" style={{ textAlign: "center" }}>
                {progress.xp} de {progress.xp_next} XP para o nível {progress.level + 1}
              </span>
            </div>
          )}
          <EquippedItems ids={character.equipped} />
          {progress?.victories ? (
            <span className="xs muted">
              {progress.victories} {progress.victories === 1 ? "vitória" : "vitórias"} na Arena
            </span>
          ) : null}
          <Link to="/conta" className="btn ghost sm">
            Ver progresso
          </Link>
        </aside>
      </div>
    </div>
  );
}
