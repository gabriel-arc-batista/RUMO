// Nova versão de uma aula: nada é herdado sozinho; trazer marcações é explícito.
import { chromium } from "playwright-core";
import { execFileSync } from "node:child_process";

const BASE = process.env.BASE ?? "http://localhost:4175";
const sql = (q) => execFileSync("docker", ["exec", "-i", "rumo-webtest-db", "psql", "-U", "postgres", "-At"], { input: q }).toString().trim();
const email = `versao-${Date.now()}@example.invalid`;
const b = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true });
const page = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
let ok = 0, total = 0;
const check = (name, cond, detail = "") => { total++; if (cond) ok++; console.log(`${cond ? "ok  " : "FALHA"} ${name}${detail ? ` — ${detail}` : ""}`); };
await page.goto(`${BASE}/entrar`);
await page.getByRole("button", { name: "Criar conta" }).first().click();
await page.getByLabel("E-mail").fill(email);
await page.getByLabel("Senha").fill("senha-exemplo-123");
await page.locator("form").getByRole("button", { name: "Criar conta" }).click();
await page.waitForURL(`${BASE}/`);
const current = sql("select version from public.rumo_lessons where id='exemplo.aula.juncoes' order by catalog_revision desc limit 1;");
await page.goto(`${BASE}/campo/aula/exemplo.aula.juncoes/ler`);
await page.locator(".pdf-page canvas").first().waitFor();
for (const n of [1, 2, 3]) {
  await page.locator(`#li-pagina-${n}`).scrollIntoViewIfNeeded();
  await page.locator(`#li-pagina-${n}`).check();
}
await page.waitForTimeout(2500);
// Publica uma versão nova (mesmo PDF de exemplo) com ordem editorial maior.
const next = `${current}-rev${Date.now() % 100000}`;
sql(`insert into public.rumo_lessons(id,version,pages,title,subject_id,topic_ids,exam_ids,resource,status,summary,objectives,prerequisite_topic_ids,sources,version_label,outline,example)
 select id,'${next}',pages,title,subject_id,topic_ids,exam_ids,resource,status,summary,objectives,prerequisite_topic_ids,sources,'versão ${next} (exemplo)',outline,example
 from public.rumo_lessons where id='exemplo.aula.juncoes' and version='${current}';`);
await page.goto(`${BASE}/campo/aula/exemplo.aula.juncoes/ler`);
await page.locator(".pdf-page canvas").first().waitFor();
await page.waitForTimeout(1500);
check("versão nova começa sem marcações", !(await page.locator("#li-pagina-1").isChecked()));
check("aviso oferece trazer marcações", await page.getByText(`Você marcou 3 páginas como lidas na versão ${current}`).isVisible());
await page.getByRole("button", { name: "Trazer marcações" }).click();
const field = page.getByLabel("Páginas a marcar nesta versão");
check("diálogo vem preenchido e editável", (await field.inputValue()) === "1-3");
await field.fill("1-99");
await page.getByRole("button", { name: "Marcar estas páginas" }).click();
check("intervalo inválido é recusado", await page.getByText(/Páginas fora desta versão/).isVisible());
await field.fill("1-2");
await page.getByRole("button", { name: "Marcar estas páginas" }).click();
await page.waitForTimeout(3000);
check("só as páginas confirmadas foram marcadas", (await page.locator("#li-pagina-1").isChecked()) && (await page.locator("#li-pagina-2").isChecked()) && !(await page.locator("#li-pagina-3").isChecked()));
const uid = sql(`select id from auth.users where email='${email}';`);
const counts = sql(`select payload->>'version', count(*) filter (where (payload->>'read')::boolean) from rumo_private.entities where user_id='${uid}' and kind='reading.page' group by 1 order by 1;`);
check("versão anterior preservada no serviço", counts.includes(`${current}|3`) && counts.includes(`${next}|2`), counts.replace(/\n/g, " ; "));
check("sem erros de página", errors.length === 0, errors.join(" | "));
// Versões publicadas são imutáveis (trigger immutable_content): a pilha local é descartável.
console.log(`${ok}/${total} verificações ok`);
await b.close();
