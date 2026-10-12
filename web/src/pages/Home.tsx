import { BookOpen, Layers, Swords } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ExampleTag, Portrait, ProgressBar } from "../components/ui";
import { isComplete, readPages, type ReadingState } from "../domain/projection";
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
  const topicId = resume?.lesson.topicIds[0] ?? attemptTopic;
  const topicQuestions = topicId ? catalog.questions.filter((q) => q.topicIds.includes(topicId)) : [];

  const due = cards?.views.filter((v) => v.status === "vencido").length ?? 0;
  const fresh = cards?.views.filter((v) => v.status === "novo").length ?? 0;
  const firstAvailable = catalog.lessons.find((l) => l.status === "disponivel");

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
  } else if (resume) {
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

  if (topicId && topicQuestions.length) {
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
          <Portrait size={88} />
          <div className="stack" style={{ gap: 4, alignItems: "center", textAlign: "center" }}>
            <span className="name">Viajante</span>
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
          <Link to="/conta" className="btn ghost sm">
            Ver progresso
          </Link>
        </aside>
      </div>
    </div>
  );
}
