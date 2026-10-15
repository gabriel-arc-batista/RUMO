import type { Projection } from "./projection";
import type { Catalog } from "./types";

/** Evidence of studied material, independent of theoretical mastery and reviews.
 * Only the current lesson version, explicitly marked read in full, qualifies. */
export function studiedTopics(catalog: Catalog, projection: Projection | undefined): Set<string> {
  const topics = new Set<string>();
  if (!projection) return topics;
  for (const lesson of catalog.lessons) {
    if (lesson.status !== "disponivel" || !lesson.pages) continue;
    const reading = projection.reading.get(`${lesson.id}@${lesson.version}`);
    if (!reading) continue;
    let complete = true;
    for (let page = 1; page <= lesson.pages; page++) {
      if (!reading.marks.get(page)?.read) { complete = false; break; }
    }
    if (complete) lesson.topicIds.forEach((id) => topics.add(id));
  }
  return topics;
}

export function topicScope(catalog: Catalog, root: string): Set<string> {
  const ids = new Set([root]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const topic of catalog.topics) {
      if (topic.parentId && ids.has(topic.parentId) && !ids.has(topic.id)) {
        ids.add(topic.id); changed = true;
      }
    }
  }
  return ids;
}
