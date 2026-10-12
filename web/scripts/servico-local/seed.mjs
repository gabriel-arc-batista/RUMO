// Gera SQL de seed a partir do catálogo de EXEMPLO do site (tudo com example=true).
import { EXAMPLE_CATALOG as c, EXAMPLE_ANSWERS as answers } from "./.tmp/catalog.mjs";
const q = (v) => (v === null || v === undefined ? "null" : `'${String(v).replace(/'/g, "''")}'`);
const arr = (a) => `array[${a.map(q).join(",")}]::text[]`;
const js = (v) => `${q(JSON.stringify(v))}::jsonb`;
const out = ["begin;"];
for (const s of c.subjects) out.push(`insert into public.rumo_subjects values(${q(s.id)},${q(s.name)});`);
for (const t of c.topics) out.push(`insert into public.rumo_topics values(${q(t.id)},${q(t.subjectId)},null,${q(t.name)});`);
for (const e of c.exams) out.push(`insert into public.rumo_exams values(${q(e.id)},${q(e.name)});`);
const base = process.argv[2];
for (const l of c.lessons) {
  const resource = l.pdfUrl ? { url: `${base}${l.pdfUrl}`, media_type: "application/pdf", example: true } : null;
  out.push(`insert into public.rumo_lessons(id,version,pages,title,subject_id,topic_ids,exam_ids,resource,status,summary,objectives,prerequisite_topic_ids,sources,version_label,outline,example) values(${q(l.id)},${q(l.version)},${l.pages ?? 1},${q(l.title)},${q(l.subjectId)},${arr(l.topicIds)},${arr(l.examIds)},${resource ? js(resource) : "null"},'planejada',${q(l.summary)},${arr(l.objectives)},${arr(l.prerequisiteTopicIds)},${js(l.sources)},${q(l.versionLabel)},${js(l.outline)},true);`);
}
for (const x of c.questions) {
  const text = x.statement.map((b) => (b.kind === "code" ? "```" + (b.lang ?? "") + "\n" + b.text + "\n```" : b.kind === "formula" ? `$$${b.text}$$` : b.kind === "image" ? `![${b.alt}](${b.src})` : b.text)).join("\n\n");
  const opts = Object.fromEntries(x.options.map((o) => [o.id, o.text]));
  const k = answers[x.id];
  out.push(`insert into rumo_private.questions(id,version,prompt,options,answer,annulled,type,comment,subject_id,topic_ids,exam_ids,provenance,example) values(${q(x.id)},${q(x.version)},${q(text)},${js(opts)},${q(k.answer)},${x.annulled},${q(x.type === "certo_errado" ? "certo-errado" : "multipla-escolha")},${q(k.comment)},${q(x.subjectId)},${arr(x.topicIds)},${arr(x.examIds)},${js({ kind: "autoral", label: x.provenance.label })},true);`);
}
for (const d of c.decks) out.push(`insert into public.rumo_decks(id,version,title,subject_id,topic_ids,source,topic_id,example) values(${q(d.id)},'1.0.0',${q(d.title)},${q(d.subjectId)},${arr(d.topicId ? [d.topicId] : [])},${q(d.description)},${q(d.topicId)},true);`);
for (const x of c.cards) out.push(`insert into public.rumo_cards(id,version,front,back,explanation,deck_id,deck_version,source,example) values(${q(x.id)},${q(x.version)},${q(x.front)},${q(x.back)},${q(x.explanation)},${q(x.deckId)},'1.0.0',${q(x.source)},true);`);
out.push("commit;");
console.log(out.join("\n"));
