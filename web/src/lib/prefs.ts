/** Preferências deste navegador (conveniência local; nada aqui é sincronizado). */
export interface Prefs {
  motion: "system" | "reduce" | "full";
  rpgEffects: boolean;
  focus: boolean;
  paper: "natural" | "suave";
  arenaTimer: boolean;
}

export const DEFAULT_PREFS: Prefs = {
  motion: "system",
  rpgEffects: true,
  focus: false,
  paper: "suave",
  arenaTimer: true,
};

const KEY = "rumo.prefs.v1";

export function loadPrefs(): Prefs {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}

export function savePrefs(prefs: Prefs): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(prefs));
  } catch {
    /* navegação privada: segue só em memória */
  }
}

export function readLocal<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeLocal(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignora: conveniência local */
  }
}
