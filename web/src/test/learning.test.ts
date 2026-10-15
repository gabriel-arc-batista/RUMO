import { expect, it } from "vitest";
import { studiedTopics, topicScope } from "../domain/learning";
import { project } from "../domain/projection";
import type { Catalog } from "../domain/types";
import { readFilters, selectQuestions } from "../pages/arena/arena";

function setup() {
  const catalog = {
    lessons: [{ id: "l", version: "2", status: "disponivel", pages: 2, topicIds: ["known"] }],
    topics: [{ id: "known", parentId: "root", subjectId: "s" }, { id: "unknown", parentId: null, subjectId: "s" }],
    questions: [
      { id: "1", subjectId: "s", topicIds: ["known"], provenance: {} },
      { id: "2", subjectId: "s", topicIds: ["known", "unknown"], provenance: {} },
      { id: "3", subjectId: "s", topicIds: [], provenance: {} },
    ],
  } as unknown as Catalog;
  const p = project([], []);
  p.reading.set("l@2", { lessonId: "l", version: "2", pages: 2, position: null, marks: new Map([[1, { read: true, origin: "server" }], [2, { read: true, origin: "pending" }]]) });
  return { catalog, p };
}

it("prática direcionada nunca mistura um segundo assunto desconhecido", () => {
  const { catalog, p } = setup();
  expect(selectQuestions(catalog, p, readFilters(new URLSearchParams("modo=estudados"))).map((q) => q.id)).toEqual(["1"]);
  p.reading.get("l@2")!.marks.get(2)!.read = false;
  expect(studiedTopics(catalog, p).size).toBe(0);
});
it("retomada e versões antigas não contam como leitura concluída", () => {
  const { catalog, p } = setup();
  p.reading.set("l@1", p.reading.get("l@2")!);
  p.reading.delete("l@2");
  expect(studiedTopics(catalog, p).size).toBe(0);
});
it("assunto pai inclui subassuntos e simulado pode incluir todo o conteúdo", () => {
  const { catalog, p } = setup();
  expect(topicScope(catalog, "root").has("known")).toBe(true);
  const result = selectQuestions(catalog, p, readFilters(new URLSearchParams("modo=simulado")));
  expect(new Set(result.map((q) => q.id)).size).toBe(3);
  expect(catalog.questions.map((q) => q.id)).toEqual(["1", "2", "3"]);
});
