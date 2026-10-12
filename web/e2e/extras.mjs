// Cenários extras contra o serviço real: favoritos/marcadores, nota de questão,
// sessão registrada + nível, conflito entre dois dispositivos e isolamento entre contas.
import { chromium, firefox, webkit } from "playwright-core";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE ?? "http://localhost:4175";
const OUT = fileURLToPath(new URL("./.shots/extras/", import.meta.url));
mkdirSync(OUT, { recursive: true });
const results = [];
const check = (name, ok, detail = "") => {
  results.push(ok);
  console.log(`${ok ? "ok  " : "FALHA"} ${name}${detail ? ` — ${detail}` : ""}`);
};
const sql = (q) => execFileSync("docker", ["exec", "-i", "rumo-webtest-db", "psql", "-U", "postgres", "-At"], { input: q }).toString().trim();

// BROWSER=firefox|webkit usa os navegadores do Playwright; padrão: Google Chrome do sistema.
const engine = { firefox, webkit }[process.env.BROWSER ?? ""];
const browser = engine
  ? await engine.launch({ headless: true })
  : await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true });
const errors = [];
async function device(email, create) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "pt-BR" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(`${BASE}/entrar`);
  if (create) await page.getByRole("button", { name: "Criar conta" }).first().click();
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill("senha-exemplo-123");
  await page.locator("form").getByRole("button", { name: create ? "Criar conta" : "Entrar" }).click();
  await page.waitForURL(`${BASE}/`);
  await page.waitForTimeout(800);
  return { ctx, page };
}
const syncState = (page) => page.locator(".sync-pill").getAttribute("data-state");

const email = `extras-${Date.now()}@example.invalid`;
const A = await device(email, true);

// Favorito global da aula e marcador de página.
await A.page.goto(`${BASE}/campo/aula/exemplo.aula.juncoes`);
await A.page.getByRole("button", { name: "Favoritar" }).click();
await A.page.getByRole("link", { name: /Começar leitura|Continuar/ }).click();
await A.page.locator(".pdf-page canvas").first().waitFor();
await A.page.locator("#pagina-atual").fill("3");
await A.page.locator("#pagina-atual").press("Enter");
await A.page.waitForTimeout(900);
await A.page.getByRole("button", { name: "Marcar página 3" }).click();
await A.page.waitForTimeout(2500);
const favs = sql(`select string_agg(entity_id, ' | ' order by entity_id) from rumo_private.entities where kind='favorite.set' and user_id=(select id from auth.users where email='${email}');`);
check("favorito global e marcador com identidade canônica", favs.includes("lesson:exemplo.aula.juncoes::favorite") && favs.includes("bookmark:exemplo.aula.juncoes:1.0.0:page:3:1.0.0:favorite"), favs);
await A.page.getByRole("button", { name: /Marcadores/ }).click();
await A.page.waitForTimeout(600);
await A.page.screenshot({ path: `${OUT}marcadores.png` });
check("marcador aparece no painel", await A.page.locator(".outline", { hasText: "Página 3" }).isVisible());

// Nota de questão e sessão registrada (cronômetro com 2 min já contados).
const timerUser = sql(`select id from auth.users where email='${email}';`);
await A.page.evaluate((userId) => {
  const key = `rumo.timer.servico:${userId}:arena.materia=subject.estruturas-dados`;
  localStorage.setItem(key, JSON.stringify({ id: crypto.randomUUID(), seconds: 125, runningSince: null }));
}, timerUser);
await A.page.goto(`${BASE}/arena/sessao?materia=subject.estruturas-dados`);
await A.page.locator(".question").waitFor();
await A.page.locator(".option", { hasText: "Θ(n log n)" }).click();
await A.page.getByRole("button", { name: "Confirmar resposta" }).click();
await A.page.locator(".result-title").waitFor({ timeout: 10000 });
await A.page.getByRole("button", { name: /Anotação/ }).click();
await A.page.getByLabel("Anotação sobre a questão").fill("Teorema mestre, caso 2.");
await A.page.getByRole("button", { name: "Salvar anotação" }).click();
await A.page.waitForTimeout(500);
await A.page.getByRole("button", { name: "Encerrar e registrar sessão" }).click();
await A.page.getByRole("button", { name: /^Registrar 2 min/ }).click();
await A.page.waitForTimeout(3000);
const notes = sql(`select payload->>'question_id', payload->>'lesson_id' is null from rumo_private.entities where kind='note.save' and user_id=(select id from auth.users where email='${email}');`);
check("anotação de questão aceita pelo serviço", notes.includes("exemplo.q.recorrencia|t"), notes);
const session = sql(`select e.payload->>'category', e.payload->>'elapsed', r.result->>'xp', e.payload->>'plan_id' from rumo_private.events e join rumo_private.results r on r.user_id=e.user_id and r.event_id=e.id where e.kind='study.session' and e.user_id=(select id from auth.users where email='${email}');`);
check("sessão do site registrada com XP do servidor", session.startsWith("Questões|125|2|site"), session);
const linked = sql(`select count(*) from rumo_private.events a where a.kind='arena.attempt' and a.user_id=(select id from auth.users where email='${email}') and exists(select 1 from rumo_private.entities s where s.user_id=a.user_id and s.kind='study.session' and s.entity_id=a.payload->>'session_id');`);
check("tentativa ligada à sessão registrada", linked === "1", linked);
await A.page.goto(`${BASE}/conta`);
await A.page.waitForTimeout(1500);
await A.page.screenshot({ path: `${OUT}conta-nivel.png` });
check("nível vem do progress_summary", (await A.page.locator(".account-grid").innerText()).includes("nível na conta"));

// Conflito: mesmo usuário em dois dispositivos.
const B = await device(email, false);
await A.page.goto(`${BASE}/campo/aula/exemplo.aula.juncoes/ler`);
await B.page.goto(`${BASE}/campo/aula/exemplo.aula.juncoes/ler`);
await A.page.locator(".pdf-page canvas").first().waitFor();
await B.page.locator(".pdf-page canvas").first().waitFor();
await B.page.waitForTimeout(1500);
await B.ctx.setOffline(true);
await A.page.locator("#li-pagina-1").check();
await A.page.waitForTimeout(2500);
check("dispositivo A sincronizou", (await syncState(A.page)) === "synced");
// B ainda não sabe da marcação de A: marca e desmarca a mesma página offline.
await B.page.locator("#li-pagina-1").check();
await B.page.locator("#li-pagina-1").uncheck();
await B.page.waitForTimeout(500);
await B.ctx.setOffline(false);
await B.page.waitForTimeout(4000);
const bState = await syncState(B.page);
check("dispositivo B detecta conflito sem descartar nada", bState === "conflict", `estado ${bState}`);
await B.page.locator(".sync-pill").click();
await B.page.screenshot({ path: `${OUT}conflito.png` });
const conflictText = await B.page.getByRole("dialog").innerText();
check("painel mostra a versão do serviço", conflictText.includes("No serviço"), conflictText.slice(0, 200));
while ((await B.page.getByRole("button", { name: "Aplicar a minha" }).count()) > 0) {
  await B.page.getByRole("button", { name: "Aplicar a minha" }).first().click();
  await B.page.waitForTimeout(300);
}
await B.page.getByRole("button", { name: "Fechar" }).click();
await B.page.waitForTimeout(3500);
check("após escolher, B sincroniza", (await syncState(B.page)) === "synced", await syncState(B.page));
const final = sql(`select payload->>'read' from rumo_private.entities where kind='reading.page' and entity_id='exemplo.aula.juncoes:1.0.0:page:1' and user_id=(select id from auth.users where email='${email}');`);
check("serviço guarda a escolha explícita de B (desmarcada)", final === "false", final);
// A recebe a mudança de B ao sincronizar.
await A.page.locator(".sync-pill").click();
await A.page.getByRole("button", { name: "Sincronizar agora" }).click();
await A.page.waitForTimeout(2500);
await A.page.getByRole("button", { name: "Fechar" }).click();
check("A recebe a desmarcação feita em B", !(await A.page.locator("#li-pagina-1").isChecked()));

// Isolamento: outra conta não vê nada da primeira.
const C = await device(`isolada-${Date.now()}@example.invalid`, true);
await C.page.goto(`${BASE}/campo?ver=favoritas`);
await C.page.waitForTimeout(1500);
check("outra conta não vê favoritos alheios", (await C.page.locator(".lesson-row").count()) === 0);
await C.page.goto(`${BASE}/arena`);
await C.page.waitForTimeout(800);
check("outra conta começa sem respostas", (await C.page.locator(".stat .value").first().innerText()) === "0");

// Sair e entrar de novo retoma a atividade.
await A.page.goto(`${BASE}/conta`);
await A.page.getByRole("button", { name: "Sair da conta" }).click();
await A.page.getByRole("dialog").getByRole("button", { name: "Sair da conta" }).click();
await A.page.waitForURL(/\/entrar/);
await A.page.getByLabel("E-mail").fill(email);
await A.page.getByLabel("Senha").fill("senha-exemplo-123");
await A.page.locator("form").getByRole("button", { name: "Entrar" }).click();
await A.page.waitForURL(`${BASE}/`);
await A.page.waitForTimeout(2000);
await A.page.screenshot({ path: `${OUT}retomar.png` });
check("após sair e entrar, o início oferece continuar a aula", (await A.page.locator(".resume").innerText()).includes("Continuar leitura"));

check("sem erros de página", errors.length === 0, errors.slice(0, 3).join(" | "));
await browser.close();
console.log(`\n${results.filter(Boolean).length}/${results.length} verificações ok`);
