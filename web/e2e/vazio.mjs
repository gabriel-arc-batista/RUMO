// Catálogo vazio (estado real da produção): estados vazios honestos nas três áreas.
import { chromium } from "playwright-core";
import { fileURLToPath } from "node:url";
import { mkdirSync } from "node:fs";
const BASE = process.env.BASE ?? "http://localhost:4175";
const OUT = fileURLToPath(new URL("./.shots/vazio/", import.meta.url));
mkdirSync(OUT, { recursive: true });
const b = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true });
const page = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
let ok = 0, total = 0;
const check = (name, cond) => { total++; if (cond) ok++; console.log(`${cond ? "ok  " : "FALHA"} ${name}`); };
await page.goto(`${BASE}/entrar`);
await page.getByRole("button", { name: "Criar conta" }).first().click();
await page.getByLabel("E-mail").fill(`vazio-${Date.now()}@example.invalid`);
await page.getByLabel("Senha").fill("senha-exemplo-123");
await page.locator("form").getByRole("button", { name: "Criar conta" }).click();
await page.waitForURL(`${BASE}/`);
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}inicio.png` });
check("início sem ações falsas de aula/questão", !(await page.getByText("Continuar leitura").count()) && !(await page.getByText("Comece pelo Campo").count()));
for (const [path, text, name] of [
  ["/campo", "Ainda não há aulas publicadas", "campo"],
  ["/arena", "Ainda não há questões publicadas", "arena"],
  ["/flashcards", "Ainda não há decks", "flashcards"],
]) {
  await page.goto(`${BASE}${path}`);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}${name}.png` });
  check(`${name}: estado vazio real`, await page.getByText(text).first().isVisible());
}
check("sem erros de página", errors.length === 0);
console.log(`${ok}/${total} verificações ok`);
await b.close();
