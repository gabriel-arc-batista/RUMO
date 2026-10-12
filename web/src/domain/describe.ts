import type { Envelope } from "../service/contract";
import type { Projection } from "./projection";
import { readingKey } from "./projection";
import type { Catalog } from "./types";

/** Descrição legível de uma ação da fila (painel de sincronização e conflitos). */
export function describeEvent(e: Envelope, catalog: Catalog | null): string {
  const lessonTitle = (id: string | null) => catalog?.lessons.find((l) => l.id === id)?.title ?? "aula";
  switch (e.kind) {
    case "reading.page":
      return `Página ${e.payload.page} ${e.payload.read ? "marcada como lida" : "desmarcada"} — ${lessonTitle(e.payload.lesson_id)}`;
    case "reading.position":
      return `Posição de leitura na página ${e.payload.page} — ${lessonTitle(e.payload.lesson_id)}`;
    case "note.save":
      if (e.payload.question_id) return e.payload.deleted ? "Exclusão de anotação de questão" : "Anotação de questão";
      return `${e.payload.deleted ? "Exclusão de nota" : "Nota"}${e.payload.page ? ` da página ${e.payload.page}` : ""} — ${lessonTitle(e.payload.lesson_id)}`;
    case "favorite.set":
      return e.payload.favorite ? "Favorito adicionado" : "Favorito removido";
    case "arena.attempt":
      return "Resposta da Arena";
    case "card.save":
      return e.payload.deleted ? "Exclusão de cartão" : e.payload.suspended ? "Cartão suspenso" : `Cartão “${e.payload.front.slice(0, 48)}”`;
    case "card.review":
      return "Revisão de cartão";
    case "study.session":
      return `Sessão de estudo (${Math.round(e.payload.elapsed / 60)} min)`;
    case "profile.character":
      return "Aparência do personagem";
    case "cycle.snapshot":
      return "Ciclo de estudos do aplicativo";
  }
}

/** O que o serviço tem hoje para a mesma entidade, para comparar num conflito. */
export function remoteDescription(e: Envelope, p: Projection): string {
  switch (e.kind) {
    case "reading.page": {
      const mark = p.reading.get(readingKey(e.payload.lesson_id, e.payload.version))?.marks.get(e.payload.page);
      return mark ? (mark.read ? "No serviço: página marcada como lida." : "No serviço: página não marcada.") : "No serviço: sem marcação.";
    }
    case "reading.position": {
      const pos = p.reading.get(readingKey(e.payload.lesson_id, e.payload.version))?.position;
      return pos ? `No serviço: posição na página ${pos.page}.` : "No serviço: sem posição.";
    }
    case "note.save": {
      const note = p.notes.get(e.entity_id);
      if (!note) return "No serviço: nota inexistente.";
      return note.deleted ? "No serviço: nota excluída." : `No serviço: “${note.text.slice(0, 120)}”`;
    }
    case "favorite.set":
      return p.favorites.get(e.entity_id)?.favorite ? "No serviço: favorito." : "No serviço: não favorito.";
    case "card.save": {
      const card = p.cards.get(e.entity_id)?.payload;
      if (!card) return "No serviço: cartão inexistente.";
      return card.deleted ? "No serviço: cartão excluído." : `No serviço: “${card.front.slice(0, 80)}” → “${card.back.slice(0, 80)}”`;
    }
    default:
      return "";
  }
}

export function siteXp(p: Projection): { xp: number; coins: number; pendingSessions: number } {
  let xp = 0;
  let coins = 0;
  let pendingSessions = 0;
  for (const s of p.sessions.values()) {
    if (s.result) {
      xp += s.result.xp;
      coins += s.result.coins;
    } else pendingSessions += 1;
  }
  return { xp, coins, pendingSessions };
}
