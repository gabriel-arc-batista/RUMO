import { expect, it } from "vitest";
import { practiceStatistics, sessionSubject } from "../domain/practice";

it("sessão mista não usa a primeira disciplina e cada resposta conta uma vez", () => {
  const a = { id: "1", subjectId: "dados", topicIds: ["sql"], outcome: "correct" as const };
  const b = { id: "2", subjectId: "redes", topicIds: ["dns", "dns"], outcome: "incorrect" as const };
  const result = practiceStatistics([a, b, a]);
  expect(result.subjects.get("dados")?.correct).toBe(1);
  expect(result.subjects.get("redes")?.incorrect).toBe(1);
  expect(result.topics.get("dns")?.answered).toBe(1);
  expect(sessionSubject(["dados", "redes"])).toBe("misto");
  expect(sessionSubject(["dados", "dados"])).toBe("dados");
  expect(sessionSubject(["dados", null])).toBe("misto");
});
it("revisar não cria acertos de questão nem conclusão de teoria", () => {
  const result = practiceStatistics([{ id: "r", subjectId: "s", topicIds: ["t"], outcome: "review" }]);
  expect(result.topics.get("t")?.correct).toBe(0);
  expect(result.topics.get("t")?.review).toBe(1);
});
