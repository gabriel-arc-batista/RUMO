/**
 * Retrato do personagem com as mesmas camadas do app (appearance.layers):
 * pacote CC0 de N. Erebus, em assets/character/look/bust.
 * A aparência só aparece aqui quando o serviço a fornecer; até lá, a padrão.
 */
export interface Look {
  face: string;
  skin: string;
  hair: string;
  hair_color: string;
  eyes: string;
  iris: string;
  eye_color: string;
  brows: string;
  nose: string;
  mouth: string;
  beard: string;
}

export const DEFAULT_LOOK: Look = {
  face: "rosto-1",
  skin: "morena-clara",
  hair: "curto",
  hair_color: "castanho-escuro",
  eyes: "amendoado",
  iris: "iris-1",
  eye_color: "castanho",
  brows: "naturais",
  nose: "nariz-1",
  mouth: "boca-1",
  beard: "nenhuma",
};

const BACK_STYLES = new Set(["baguncado", "cacheado", "crespo", "ondulado", "longo", "franja"]);

export function portraitLayers(look: Look = DEFAULT_LOOK): string[] {
  const back = BACK_STYLES.has(look.hair) ? [`hairback-${look.hair}-${look.hair_color}`] : [];
  const front = [
    `head-${look.face}-${look.skin}`,
    "eyeball",
    `iris-${look.iris}-${look.eye_color}`,
    `eyes-${look.eyes}-${look.skin}`,
    `brows-${look.brows}-${look.hair_color}`,
    `nose-${look.nose}`,
    `mouth-${look.mouth}`,
  ];
  if (look.beard !== "nenhuma") front.push(`beard-${look.beard}-${look.hair_color}`);
  if (look.hair !== "careca") front.push(`hair-${look.hair}-${look.hair_color}`);
  return [...back, ...front].map((name) => `/character/bust/${name}.png`);
}
