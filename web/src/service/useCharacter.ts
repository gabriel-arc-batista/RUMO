import { lookFrom, type Look } from "../domain/character";
import { useRumo } from "./store";

export interface CharacterInfo {
  name: string;
  look: Look;
  equipped: string[];
  /** true quando a aparência veio do aplicativo (sincronizada). */
  synced: boolean;
}

/** Personagem para exibir: o perfil enviado pelo app, ou o viajante padrão. */
export function useCharacter(): CharacterInfo {
  const { sync, progress } = useRumo();
  const profile = sync?.projection.profile ?? null;
  const name = profile?.name || progress?.name || "Viajante";
  const raw = profile?.look ?? progress?.look ?? null;
  const equipped = profile?.equipped ?? progress?.equipped ?? [];
  return { name, look: lookFrom(raw), equipped, synced: Boolean(raw) };
}
