// Conta sintética confirmada criada/removida pelo wrapper administrativo externo.
// Não cria usuários, conteúdo publicado ou fixtures de catálogo.
import { chromium } from "playwright-core";
const { BASE, EMAIL, PASSWORD } = process.env;
if (!BASE || !EMAIL || !PASSWORD) throw new Error("BASE, EMAIL e PASSWORD são obrigatórios.");
const base = new URL(BASE);
if (base.protocol !== "https:") throw new Error("O smoke hospedado exige HTTPS.");
const origin = base.origin;
const browser = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", () => errors.push(true));
  await page.goto(`${origin}/entrar`);
  await page.getByLabel("E-mail").fill(EMAIL);
  await page.getByLabel("Senha").fill(PASSWORD);
  await page.locator("form").getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(`${origin}/`);
  for (const [path, text] of [
    ["/campo", "Ainda não há aulas publicadas"],
    ["/arena", "Ainda não há questões publicadas"],
    ["/flashcards", "Ainda não há decks"],
  ]) {
    await page.goto(`${origin}${path}`);
    await page.getByText(text).first().waitFor();
  }
  await page.goto(`${origin}/flashcards?ver=pessoais`);
  await page.getByRole("button", { name: "Novo cartão" }).click();
  const front = `Smoke de persistência ${Date.now()}`;
  await page.getByLabel("Frente (pergunta)").fill(front);
  await page.getByLabel("Verso (resposta)").fill("Conta sintética de validação.");
  await page.getByRole("button", { name: "Salvar cartão" }).click();
  await page.getByText(front, { exact: true }).waitFor();
  await page.waitForFunction(() => document.querySelector(".sync-pill")?.getAttribute("data-state") === "synced");
  // Outro contexto impede que a fila local mascare uma falha de persistência remota.
  const fresh = await browser.newPage();
  fresh.on("pageerror", () => errors.push(true));
  await fresh.goto(`${origin}/entrar`);
  await fresh.getByLabel("E-mail").fill(EMAIL);
  await fresh.getByLabel("Senha").fill(PASSWORD);
  await fresh.locator("form").getByRole("button", { name: "Entrar" }).click();
  await fresh.waitForURL(`${origin}/`);
  await fresh.goto(`${origin}/flashcards?ver=pessoais`);
  await fresh.getByText(front, { exact: true }).waitFor();
  await fresh.reload();
  await fresh.getByText(front, { exact: true }).waitFor();
  await fresh.goto(`${origin}/conta`);
  await fresh.getByRole("button", { name: "Sair da conta", exact: true }).click();
  await fresh.getByRole("dialog").getByRole("button", { name: "Sair da conta", exact: true }).click();
  await fresh.waitForURL(`${origin}/entrar`);
  if (errors.length) throw new Error("Erro de execução no navegador.");
  console.log("ok smoke hospedado: login, catálogo vazio, cartão persistido em outro contexto, reload e logout");
} finally {
  await browser.close();
}
