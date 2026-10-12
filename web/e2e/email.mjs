// E-mail real de teste (Mailpit, `MAIL=1 npm run servico:up`): confirmação de
// cadastro e recuperação de senha seguindo os links recebidos.
import { chromium } from "playwright-core";

const BASE = process.env.BASE ?? "http://localhost:4175";
const MAIL = "http://localhost:8025/api/v1";
const email = `email-${Date.now()}@example.invalid`;
let ok = 0, total = 0;
const check = (name, cond, detail = "") => { total++; if (cond) ok++; console.log(`${cond ? "ok  " : "FALHA"} ${name}${detail ? ` — ${detail}` : ""}`); };

async function linkFor(subjectHint, after) {
  for (let i = 0; i < 40; i += 1) {
    const list = await (await fetch(`${MAIL}/search?query=${encodeURIComponent(`to:${email}`)}`)).json();
    const msg = (list.messages ?? []).find((m) => new Date(m.Created).getTime() >= after && (!subjectHint || m.Subject.toLowerCase().includes(subjectHint)));
    if (msg) {
      const full = await (await fetch(`${MAIL}/message/${msg.ID}`)).json();
      const href = (full.HTML || full.Text).match(/https?:\/\/[^"'\s<>]+verify[^"'\s<>]*/)?.[0];
      if (href) return { subject: msg.Subject, href: href.replace(/&amp;/g, "&") };
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return null;
}

const b = await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true });
const page = await (await b.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));

let t0 = Date.now() - 1000;
await page.goto(`${BASE}/entrar`);
await page.getByRole("button", { name: "Criar conta" }).first().click();
await page.getByLabel("E-mail").fill(email);
await page.getByLabel("Senha").fill("senha-inicial-123");
await page.locator("form").getByRole("button", { name: "Criar conta" }).click();
await page.getByRole("heading", { name: "Confirme seu e-mail" }).waitFor();
check("cadastro pede confirmação por e-mail", true);
const confirm = await linkFor("", t0);
check("e-mail de confirmação recebido", Boolean(confirm), confirm?.subject);
await page.goto(confirm.href);
await page.waitForURL(/\/conta/, { timeout: 15000 });
await page.waitForTimeout(1500);
check("link de confirmação entra na conta", (await page.getByRole("heading", { name: "Conta e progresso" }).count()) === 1);

await page.getByRole("button", { name: "Sair da conta" }).click();
await page.getByRole("dialog").getByRole("button", { name: "Sair da conta" }).click();
await page.waitForURL(/\/entrar/);
t0 = Date.now() - 1000;
await page.getByRole("link", { name: "Esqueci minha senha" }).click();
await page.waitForURL(/\/conta\/recuperar/);
await page.getByRole("heading", { name: "Recuperar acesso" }).waitFor();
await page.getByLabel("E-mail").fill(email);
await page.getByRole("button", { name: "Enviar link" }).click();
await page.getByText(/você vai receber um link/).waitFor();
const recovery = await linkFor("", t0);
check("e-mail de recuperação recebido", Boolean(recovery), recovery?.subject);
await page.goto(recovery.href);
await page.waitForURL(/\/conta\/nova-senha/, { timeout: 15000 });
await page.getByLabel("Nova senha").fill("senha-nova-456");
await page.getByRole("button", { name: "Salvar nova senha" }).click();
await page.waitForURL(`${BASE}/`, { timeout: 15000 });
check("nova senha salva e sessão aberta", true);

const fresh = await (await b.newContext()).newPage();
await fresh.goto(`${BASE}/entrar`);
await fresh.getByLabel("E-mail").fill(email);
await fresh.getByLabel("Senha").fill("senha-inicial-123");
await fresh.locator("form").getByRole("button", { name: "Entrar" }).click();
check("senha antiga deixa de valer", await fresh.getByText("E-mail ou senha incorretos.").waitFor({ timeout: 8000 }).then(() => true, () => false));
await fresh.getByLabel("Senha").fill("senha-nova-456");
await fresh.locator("form").getByRole("button", { name: "Entrar" }).click();
await fresh.waitForURL(`${BASE}/`, { timeout: 15000 });
check("entra com a senha nova", true);
check("sem erros de página", errors.length === 0, errors.join(" | "));
console.log(`${ok}/${total} verificações ok`);
await b.close();
