import { describe, expect, it } from "vitest";
import { lookFrom, DEFAULT_LOOK } from "../domain/character";
import { project } from "../domain/projection";
import { pageRanges, parseRanges } from "../lib/ranges";
import type { ServerEvent } from "../service/contract";

describe("intervalos de páginas (mesma regra do app)", () => {
  it("ida e volta e limites", () => {
    expect(pageRanges([5, 1, 2, 3, 7, 8])).toBe("1-3, 5, 7-8");
    expect(parseRanges("1-3, 5; 7-8", 10)).toEqual([1, 2, 3, 5, 7, 8]);
    for (const bad of ["", "0-2", "3-1", "1-99", "a", "1-2-3"]) expect(() => parseRanges(bad, 10)).toThrow();
  });
});

describe("aparência vinda do app", () => {
  it("usa só valores seguros e completa com o padrão", () => {
    const look = lookFrom({ hair: "longo", skin: "../../x", unknown: "y" });
    expect(look.hair).toBe("longo");
    expect(look.skin).toBe(DEFAULT_LOOK.skin);
    expect(lookFrom(null)).toEqual(DEFAULT_LOOK);
  });
});

describe("projeção de perfil e ciclo", () => {
  it("guarda o último perfil e ciclo recebidos", () => {
    const base = { device_id: "d", base_revision: 0, received_at: "2026-10-12T10:00:00Z" };
    const events = [
      { ...base, id: "1", sequence: 1, revision: 1, kind: "profile.character", entity_id: "profile:character", payload: { name: "Ana", look: {}, equipped: [] } },
      { ...base, id: "2", sequence: 2, revision: 1, kind: "cycle.snapshot", entity_id: "cycle:current", payload: { plan_name: "P", position: 0, items: [] } },
    ] as unknown as ServerEvent[];
    const p = project(events, []);
    expect(p.profile?.name).toBe("Ana");
    expect(p.cycle?.plan_name).toBe("P");
  });
});
