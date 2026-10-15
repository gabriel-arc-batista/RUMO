import { expect, it } from "vitest";
import { collectPages } from "../service/pagination";

it("carrega mais de mil questões, inclusive com limite menor no servidor", async () => {
  const bank = Array.from({ length: 1237 }, (_, id) => ({ id }));
  const got = await collectPages(async (from, to) => ({ data: bank.slice(from, Math.min(to + 1, from + 100)), error: null }));
  expect(got).toEqual(bank);
  expect(new Set(got.map((q) => q.id)).size).toBe(1237);
});
it("uma falha intermediária recusa catálogo parcial", async () => {
  await expect(collectPages(async (from) => from ? { data: null, error: Error("offline") } : { data: [1], error: null })).rejects.toThrow("offline");
});
