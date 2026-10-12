// Carga na pilha LOCAL (nunca no serviço hospedado): contas simultâneas enviando
// lotes em paralelo, com reenvios duplicados. Mede latência e confere integridade.
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";

const GATEWAY = "http://localhost:54321";
if (!/^http:\/\/(localhost|127\.0\.0\.1)/.test(GATEWAY)) throw new Error("Carga só na pilha local.");
const env = Object.fromEntries(readFileSync(new URL("../.env.servico.local", import.meta.url), "utf8").trim().split("\n").map((l) => l.split("=")));
const anon = env.VITE_SUPABASE_ANON_KEY;
const USERS = Number(process.env.USERS ?? 40);
const BATCHES = Number(process.env.BATCHES ?? 20);
const PER_BATCH = 5;
const sql = (q) => execFileSync("docker", ["exec", "-i", "rumo-webtest-db", "psql", "-U", "postgres", "-At"], { input: q }).toString().trim();
const lesson = sql("select id||'|'||version||'|'||pages from public.rumo_lessons where example and resource is not null order by catalog_revision desc limit 1;").split("|");
const [lessonId, version, pages] = [lesson[0], lesson[1], Number(lesson[2])];

const call = async (path, body, token) => {
  const t = performance.now();
  const r = await fetch(GATEWAY + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", apikey: anon, Authorization: `Bearer ${token ?? anon}` },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(`${path} ${r.status} ${JSON.stringify(data).slice(0, 120)}`);
  return { data, ms: performance.now() - t };
};

const latencies = [];
let duplicates = 0;
async function user(i) {
  const email = `carga-${Date.now()}-${i}@example.invalid`;
  await call("/auth/v1/signup", { email, password: "senha-carga-123" });
  const { data: session } = await call("/auth/v1/token?grant_type=password", { email, password: "senha-carga-123" });
  const token = session.access_token;
  const device = randomUUID();
  const sessionId = randomUUID();
  let sent = 0;
  const revisions = new Map();
  for (let b = 0; b < BATCHES; b += 1) {
    const events = Array.from({ length: PER_BATCH }, (_, k) => {
      const n = b * PER_BATCH + k;
      if (n % 2) {
        const id = randomUUID();
        return { id, device_id: device, kind: "arena.attempt", entity_id: id, base_revision: 0, payload: { question_id: "exemplo.q.fk", version: "1.0.0", answer: n % 4 === 1 ? "certo" : "errado", session_id: sessionId } };
      }
      const page = (Math.floor(n / 2) % pages) + 1;
      const entity = `${lessonId}:${version}:page:${page}`;
      const base = revisions.get(entity) ?? 0;
      revisions.set(entity, base + 1);
      return { id: randomUUID(), device_id: device, kind: "reading.page", entity_id: entity, base_revision: base, payload: { lesson_id: lessonId, version, page, pages, read: base % 2 === 0 } };
    });
    const { ms } = await call("/rest/v1/rpc/push_events", { events }, token);
    latencies.push(ms);
    sent += events.length;
    // Reenvio idêntico (como após queda de rede): deve devolver os mesmos aceites.
    if (b % 4 === 0) {
      await call("/rest/v1/rpc/push_events", { events }, token);
      duplicates += events.length;
    }
  }
  const { data: pulled } = await call("/rest/v1/rpc/pull_events", { after_sequence: 0, batch_size: 200 }, token);
  return { email, sent, pulled: pulled.length };
}

const t0 = performance.now();
const results = await Promise.allSettled(Array.from({ length: USERS }, (_, i) => user(i)));
const seconds = (performance.now() - t0) / 1000;
const ok = results.filter((r) => r.status === "fulfilled").map((r) => r.value);
const failed = results.filter((r) => r.status === "rejected").map((r) => r.reason.message);
latencies.sort((a, b) => a - b);
const pct = (p) => latencies[Math.min(latencies.length - 1, Math.floor((p / 100) * latencies.length))].toFixed(0);
const total = ok.reduce((s, u) => s + u.sent, 0);
const emails = ok.map((u) => `'${u.email}'`).join(",") || "''";
const stored = Number(sql(`select count(*) from rumo_private.events e join auth.users u on u.id=e.user_id where u.email in (${emails});`));
const dupIds = Number(sql(`select count(*)-count(distinct (e.user_id,e.id)) from rumo_private.events e join auth.users u on u.id=e.user_id where u.email in (${emails});`));
const isolated = ok.every((u) => u.pulled === Math.min(200, u.sent));
console.log(`${ok.length}/${USERS} contas concluíram; falhas: ${failed.length}${failed.length ? ` (${failed[0]})` : ""}`);
console.log(`${total} eventos + ${duplicates} reenvios em ${seconds.toFixed(1)} s (${(total / seconds).toFixed(0)} eventos/s)`);
console.log(`latência por lote de ${PER_BATCH}: p50 ${pct(50)} ms · p95 ${pct(95)} ms · p99 ${pct(99)} ms`);
console.log(`gravados ${stored} (esperado ${total}) · ids duplicados ${dupIds} · cada conta só vê o próprio: ${isolated}`);
process.exit(failed.length || stored !== total || dupIds || !isolated ? 1 : 0);
