/** Classify each activity by its own content, independently of timer metadata. */
export interface PracticeActivity {
  id: string;
  subjectId: string | null;
  topicIds: string[];
  outcome: "correct" | "incorrect" | "annulled" | "review" | "pending";
}
export interface PracticeCount {
  answered: number;
  correct: number;
  incorrect: number;
  annulled: number;
  review: number;
  pending: number;
}
export function practiceStatistics(activities: PracticeActivity[]) {
  const subjects = new Map<string, PracticeCount>();
  const topics = new Map<string, PracticeCount>();
  const seen = new Set<string>();
  const add = (map: Map<string, PracticeCount>, key: string, activity: PracticeActivity) => {
    const count = map.get(key) ?? { answered: 0, correct: 0, incorrect: 0, annulled: 0, review: 0, pending: 0 };
    count.answered++;
    count[activity.outcome]++;
    map.set(key, count);
  };
  for (const activity of activities) {
    if (seen.has(activity.id)) continue;
    seen.add(activity.id);
    add(subjects, activity.subjectId ?? "unclassified", activity);
    for (const id of new Set(activity.topicIds)) add(topics, id, activity);
  }
  return { subjects, topics };
}

export function sessionSubject(subjects: (string | null)[]): string {
  const unique = new Set(subjects.filter((id): id is string => Boolean(id)));
  return unique.size === 1 && subjects.every(Boolean) ? [...unique][0] : "misto";
}

import type { Card, Catalog, Deck } from "./types";

export function cardClassification(card: Card, catalog: Catalog, decks: Deck[]) {
  const deck = decks.find((d) => d.id === card.deckId);
  const question = catalog.questions.find((q) => q.id === card.questionId);
  const lesson = catalog.lessons.find((l) => l.id === card.lessonId);
  const topicIds = [...new Set([
    ...(deck?.topicId ? [deck.topicId] : []),
    ...(question?.topicIds ?? []), ...(lesson?.topicIds ?? []),
  ])];
  return { subjectId: deck?.subjectId ?? question?.subjectId ?? lesson?.subjectId ?? null, topicIds };
}
