import { attemptsFor, isFavorite, type AttemptState, type Projection } from "../../domain/projection";
import { studiedTopics, topicScope } from "../../domain/learning";
import type { Catalog, Question } from "../../domain/types";

export type Mode = "assunto" | "erros" | "favoritas" | "ineditas" | "estudados" | "aleatorias" | "simulado";

export const MODES: { value: Mode; label: string; hint: string }[] = [
  { value: "estudados", label: "Conteúdo estudado", hint: "Só questões cujos assuntos têm uma aula atual marcada integralmente como lida. Leitura não comprova domínio; assuntos sem esse registro ficam fora." },
  { value: "aleatorias", label: "Aleatórias", hint: "Questões dos filtros em ordem sorteada; pode incluir conteúdos ainda não estudados." },
  { value: "simulado", label: "Simulado", hint: "Inclui conteúdos ainda não estudados, respeitando os filtros escolhidos. Não exige concluir a trilha." },
  { value: "assunto", label: "Por assunto", hint: "Todas as questões dos filtros, na ordem do catálogo." },
  { value: "erros", label: "Revanche dos erros", hint: "Questões cuja última resposta foi errada." },
  { value: "ineditas", label: "Ainda não respondidas", hint: "Só o que você nunca respondeu." },
  { value: "favoritas", label: "Favoritas", hint: "Questões que você marcou com estrela." },
];

export interface Filters {
  subject: string;
  topic: string;
  exam: string;
  bank: string;
  year: string;
  mode: Mode;
}

export function readFilters(params: URLSearchParams): Filters {
  return {
    subject: params.get("materia") ?? "",
    topic: params.get("assunto") ?? "",
    exam: params.get("edital") ?? "",
    bank: params.get("banca") ?? "",
    year: params.get("ano") ?? "",
    mode: MODES.find((m) => m.value === params.get("modo"))?.value ?? "assunto",
  };
}

export function toParams(f: Filters): URLSearchParams {
  const p = new URLSearchParams();
  if (f.subject) p.set("materia", f.subject);
  if (f.topic) p.set("assunto", f.topic);
  if (f.exam) p.set("edital", f.exam);
  if (f.bank) p.set("banca", f.bank);
  if (f.year) p.set("ano", f.year);
  if (f.mode !== "assunto") p.set("modo", f.mode);
  return p;
}

export function lastAttempt(p: Projection | undefined, questionId: string): AttemptState | undefined {
  return p ? attemptsFor(p, questionId).at(-1) : undefined;
}

export function selectQuestions(catalog: Catalog, p: Projection | undefined, f: Filters): Question[] {
  const topicSubject = catalog.topics.find((t) => t.id === f.topic)?.subjectId;
  const studied = studiedTopics(catalog, p);
  const scope = f.topic ? topicScope(catalog, f.topic) : null;
  const result = catalog.questions.filter((q) => {
    if (f.subject && q.subjectId !== f.subject) return false;
    if (scope && !q.topicIds.some((id) => scope.has(id))) return false;
    if (!f.subject && f.topic && topicSubject && q.subjectId !== topicSubject) return false;
    if (f.exam && !q.examIds.includes(f.exam)) return false;
    if (f.bank && q.provenance.bank !== f.bank) return false;
    if (f.year && String(q.provenance.year ?? "") !== f.year) return false;
    if (f.mode === "estudados" && (!q.topicIds.length || !q.topicIds.every((id) => studied.has(id)))) return false;
    const last = lastAttempt(p, q.id);
    if (f.mode === "erros") return last?.result?.status === "incorrect";
    if (f.mode === "ineditas") return !last;
    if (f.mode === "favoritas") return p ? isFavorite(p, "question", q.id) : false;
    return true;
  });
  if (f.mode === "aleatorias" || f.mode === "simulado") {
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
  }
  return result;
}

/** Bancas e anos só aparecem como filtro quando o catálogo traz esses metadados. */
export function realMetadata(catalog: Catalog) {
  const banks = [...new Set(catalog.questions.map((q) => q.provenance.bank).filter(Boolean) as string[])].sort();
  const years = [...new Set(catalog.questions.map((q) => q.provenance.year).filter(Boolean) as number[])].sort((a, b) => b - a);
  return { banks, years };
}

export function plainStatement(q: Question): string {
  return q.statement
    .map((b) => (b.kind === "image" ? `[imagem: ${b.alt}]` : b.text))
    .join("\n\n")
    .trim();
}
