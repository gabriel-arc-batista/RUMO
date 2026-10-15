import { describe, expect, it, vi } from "vitest";
import { SingleAction } from "../lib/singleAction";

describe("respostas repetidas", () => {
  it("mouse e teclado concorrentes gravam uma revisão e um avanço", async () => {
    const gate = new SingleAction();
    const save = vi.fn(async () => {});
    await Promise.all([gate.run("card", save), gate.run("card", save), gate.run("card", save)]);
    await gate.run("card", save);
    expect(save).toHaveBeenCalledTimes(1);
    await gate.run("other-card", save);
    expect(save).toHaveBeenCalledTimes(2);
  });
  it("falha permite tentar de novo com o mesmo UUID", async () => {
    const gate = new SingleAction();
    let original = "";
    await expect(gate.run("attempt", async (id) => { original = id; throw Error("storage"); })).rejects.toThrow();
    await gate.run("attempt", async (id) => { expect(id).toBe(original); });
  });
});
