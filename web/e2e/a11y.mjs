// Auditoria automática de acessibilidade (axe-core, WCAG 2.x A/AA) nas telas principais.
// Não substitui teste com leitor de tela real.
import { chromium } from "playwright-core";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const axe = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const BASE = process.env.BASE ?? "http://localhost:4173";
const b = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true });
const page = await (await b.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
const report = [];
async function audit(name) {
  await page.waitForTimeout(900);
  await page.addScriptTag({ content: axe });
  const result = await page.evaluate(async () =>
    // eslint-disable-next-line no-undef
    (await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"] } })).violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      help: v.help,
      nodes: v.nodes.slice(0, 3).map((n) => n.target.join(" ")),
    })),
  );
  report.push({ name, result });
  const serious = result.filter((v) => ["serious", "critical"].includes(v.impact));
  console.log(`${serious.length ? "FALHA" : "ok  "} ${name}: ${result.length} apontamentos (${serious.length} graves)`);
  for (const v of result) console.log(`     [${v.impact}] ${v.id} — ${v.help} — ${v.nodes.join(" , ")}`);
}
await page.goto(`${BASE}/entrar`);
await audit("entrar");
await page.getByLabel("E-mail").fill(`a11y-${Date.now()}@exemplo.dev`);
await page.getByLabel("Senha").fill("senha-exemplo-123");
await page.locator("form").getByRole("button", { name: "Entrar" }).click();
await page.waitForURL(`${BASE}/`);
await audit("início");
await page.goto(`${BASE}/campo`);
await audit("campo");
await page.goto(`${BASE}/campo/aula/exemplo.aula.modelo-relacional`);
await audit("detalhe da aula");
await page.goto(`${BASE}/campo/aula/exemplo.aula.modelo-relacional/ler?painel=notas`);
await page.locator(".pdf-page canvas").first().waitFor();
await audit("leitor com notas");
await page.goto(`${BASE}/arena`);
await audit("arena");
await page.goto(`${BASE}/arena/sessao?materia=subject.estruturas-dados`);
await page.locator(".option").first().click();
await page.getByRole("button", { name: "Confirmar resposta" }).click();
await page.locator(".result-title").waitFor();
await audit("questão respondida");
await page.goto(`${BASE}/flashcards`);
await audit("flashcards");
await page.goto(`${BASE}/flashcards/revisar?novos=1`);
await page.getByRole("button", { name: "Mostrar resposta" }).click();
await audit("revisão com verso");
await page.goto(`${BASE}/conta`);
await audit("conta");
const graves = report.flatMap((r) => r.result).filter((v) => ["serious", "critical"].includes(v.impact)).length;
console.log(`\n${report.length - report.filter((r) => r.result.some((v) => ["serious", "critical"].includes(v.impact))).length}/${report.length} telas sem apontamentos graves (${graves} graves no total)`);
await b.close();
