import { isComplete, isFavorite, readPages, readingKey, type Projection } from "../../domain/projection";
import type { Catalog, Lesson } from "../../domain/types";
import { entity, type FavoriteType } from "../../service/contract";

export interface LessonProgress {
  read: number;
  pages: number;
  complete: boolean;
  position: number | null;
  started: boolean;
  favorite: boolean;
}

export function lessonProgress(p: Projection | undefined, lesson: Lesson): LessonProgress {
  const state = p?.reading.get(readingKey(lesson.id, lesson.version));
  const read = readPages(state).length;
  return {
    read,
    pages: lesson.pages ?? 0,
    complete: isComplete(state, lesson.pages),
    position: state?.position?.page ?? null,
    started: read > 0 || Boolean(state?.position),
    favorite: p ? isFavorite(p, "lesson", lesson.id) : false,
  };
}

export function subjectName(catalog: Catalog, id: string | null | undefined) {
  return catalog.subjects.find((s) => s.id === id)?.name ?? "Sem matéria";
}

export function topicName(catalog: Catalog, id: string | null | undefined) {
  return catalog.topics.find((t) => t.id === id)?.name ?? "Sem assunto";
}

/** Favoritos de aula, questão, cartão e deck são globais (versão vazia). */
export const favoriteEntity = (type: FavoriteType, id: string, version = "") => entity.favorite(type, id, version);

export const lessonPath = (lesson: Pick<Lesson, "id">) => `/campo/aula/${encodeURIComponent(lesson.id)}`;
