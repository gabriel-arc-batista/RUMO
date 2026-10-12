// Fluxo ponta a ponta no Google Chrome real (modo EXEMPLO), com capturas.
import { chromium, firefox, webkit } from "playwright-core";
import { fileURLToPath } from "node:url";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE ?? "http://localhost:4173";
const OUT = process.env.OUT ?? fileURLToPath(new URL("./.shots/", import.meta.url));
mkdirSync(OUT, { recursive: true });

const results = [];
const check = (name, ok, detail = "") => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "ok  " : "FALHA"} ${name}${detail ? ` — ${detail}` : ""}`);
};

// BROWSER=firefox|webkit usa os navegadores do Playwright; padrão: Google Chrome do sistema.
const engine = { firefox, webkit }[process.env.BROWSER ?? ""];
const browser = engine
  ? await engine.launch({ headless: true })
  : await chromium.launch({ executablePath: process.env.CHROME ?? "/usr/bin/google-chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "pt-BR", deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
const shot = (name) => page.screenshot({ path: `${OUT}${name}.png` });

// 1. Conta
await page.goto(`${BASE}/`);
await page.waitForURL(/\/entrar/);
check("sem conta redireciona para /entrar", page.url().includes("/entrar"));
await shot("01-entrar");
await page.getByRole("button", { name: "Criar conta" }).first().click();
const EMAIL = process.env.EMAIL ?? (process.env.MODE === "servico" ? `viajante-${Date.now()}@example.invalid` : `viajante-${Date.now()}@exemplo.dev`);
await page.getByLabel("E-mail").fill(EMAIL);
await page.getByLabel("Senha").fill("curta");
await page.locator("form").getByRole("button", { name: "Criar conta" }).click();
check("senha curta mostra erro", await page.getByText("pelo menos 8 caracteres").first().isVisible());
await page.getByLabel("Senha").fill("senha-exemplo-123");
await page.locator("form").getByRole("button", { name: "Criar conta" }).click();
await page.waitForURL(`${BASE}/`);
await page.getByRole("heading", { level: 1 }).waitFor();
await page.waitForTimeout(600);
await shot("02-inicio-vazio");
check("início mostra ações de retomada", (await page.locator(".resume-row").count()) >= 2);

// 2. Campo
await page.getByRole("link", { name: "Campo de Treinamento" }).first().click();
await page.getByRole("heading", { name: "Campo de Treinamento" }).waitFor();
await shot("03-campo");
await page.getByRole("button", { name: /Planejadas/ }).click();
await page.waitForTimeout(400);
check("planejadas aparecem separadas", (await page.locator(".lesson-row .tag", { hasText: "Planejada" }).count()) >= 3);
await page.getByRole("button", { name: /Disponíveis/ }).click();
await page.waitForTimeout(400);
await page.getByPlaceholder("Buscar aula, matéria ou assunto").fill("xyz inexistente");
await page.waitForTimeout(400);
check("busca sem resultado oferece limpar", await page.getByRole("button", { name: "Limpar busca e edital" }).isVisible());
await page.getByRole("button", { name: "Limpar busca e edital" }).click();
await page.waitForTimeout(300);
await page.getByLabel("Filtrar pelo edital-alvo").selectOption("dataprev-2024-desenvolvimento");
await page.waitForTimeout(400);
check("filtro por edital", (await page.locator(".lesson-row").count()) === 1);
await page.getByLabel("Filtrar pelo edital-alvo").selectOption("");
await page.waitForTimeout(400);
await page.getByRole("link", { name: /Modelo relacional: tabelas/ }).click();
await page.getByRole("heading", { name: /Modelo relacional/ }).waitFor();
await shot("04-aula-detalhe");
check("detalhe mostra 0 de 20", await page.getByText("0 de 20 páginas").isVisible());

// 3. Leitor
await page.getByRole("link", { name: "Começar leitura" }).click();
await page.locator(".pdf-page canvas").first().waitFor();
await page.waitForTimeout(1200);
await shot("05-leitor");
check("barra mostra página 1", (await page.locator(".reader-bar").innerText()).includes("Página 1 de 20"));
await page.locator("#li-pagina-1").check();
await page.waitForTimeout(700);
check("marcar página 1 atualiza progresso", (await page.locator(".reader-bar").innerText()).includes("1 de 20 páginas marcadas"));
await page.getByRole("button", { name: "Próxima página" }).click();
await page.waitForTimeout(900);
check("navegação vai à página 2", (await page.locator(".reader-bar").innerText()).includes("Página 2 de 20"));
await page.locator("#li-pagina-barra").check();
await page.waitForTimeout(700);
check("barra marca a página atual (2)", await page.locator("#li-pagina-2").isChecked());
await page.locator("#pagina-atual").fill("7");
await page.locator("#pagina-atual").press("Enter");
await page.waitForTimeout(1200);
await shot("06-leitor-diagrama");
check("ir para página 7", (await page.locator(".reader-bar").innerText()).includes("Página 7 de 20"));
await page.locator("#li-pagina-barra").check();
await page.locator("#li-pagina-barra").uncheck();
await page.waitForTimeout(600);
check("desmarcar recalcula", (await page.locator(".reader-bar").innerText()).includes("2 de 20 páginas marcadas"));
await page.getByRole("button", { name: /Buscar/ }).first().click();
await page.getByPlaceholder("Buscar no PDF").fill("estrangeira");
await page.waitForTimeout(1500);
await shot("07-leitor-busca");
const hits = await page.locator(".hits li").count();
check("busca no PDF encontra ocorrências", hits > 0, `${hits} ocorrências`);
await page.getByRole("button", { name: /Notas/ }).first().click();
await page.getByPlaceholder(/Nota sobre a página/).fill("Chave estrangeira referencia chave candidata.");
await page.getByRole("button", { name: "Salvar nota" }).click();
await page.waitForTimeout(800);
await shot("08-leitor-notas");
check("nota aparece na lista", await page.locator(".note-text", { hasText: "Chave estrangeira referencia" }).isVisible());
await page.getByRole("button", { name: "Criar flashcard desta nota" }).click();
check("nota abre rascunho de cartão", await page.getByRole("dialog", { name: /flashcard da nota/ }).isVisible());
await page.getByRole("button", { name: "Salvar cartão" }).click();
check("frente vazia bloqueia salvar", await page.getByText("Escreva a pergunta da frente.").isVisible());
await page.getByLabel("Frente (pergunta)").fill("O que uma chave estrangeira referencia?");
await page.getByRole("button", { name: "Salvar cartão" }).click();
await page.waitForTimeout(600);
await page.getByRole("button", { name: "Índice" }).click();
await page.waitForTimeout(300);
check("índice do PDF lido", (await page.locator(".outline li").count()) >= 5);
await page.getByRole("button", { name: "Fechar painel" }).click();
// Posição salva: sai e volta sem ?pagina → oferta de retomar.
await page.waitForTimeout(2000);
await page.goto(`${BASE}/campo/aula/exemplo.aula.modelo-relacional/ler`);
await page.locator(".pdf-page canvas").first().waitFor();
await page.waitForTimeout(1000);
const offer = await page.getByText(/Você parou na página 7/).isVisible();
check("ao voltar oferece retomar a última posição", offer);
await shot("09-leitor-retomar");
if (offer) await page.getByRole("button", { name: "Ir para a página 7" }).click();

// Conclusão: marcar todas menos a última não conclui; com a última, conclui.
for (let n = 1; n <= 19; n += 1) {
  const box = page.locator(`#li-pagina-${n}`);
  await box.scrollIntoViewIfNeeded();
  if (!(await box.isChecked())) await box.check();
}
await page.waitForTimeout(800);
check("19 de 20 não conclui", !(await page.locator(".reader-bar").innerText()).includes("Aula concluída"));
const last = page.locator("#li-pagina-20");
await last.scrollIntoViewIfNeeded();
await last.check();
await page.waitForTimeout(1200);
check("todas as páginas concluem a aula", (await page.locator(".reader-bar").innerText()).includes("Aula concluída"));
await shot("10-leitor-concluida");

// 4. Arena
await page.goto(`${BASE}/arena`);
await page.getByRole("heading", { name: "Arena" }).waitFor();
await page.waitForTimeout(500);
await shot("11-arena");
await page.getByLabel("Matéria").selectOption("subject.bancos-dados");
await page.getByRole("link", { name: "Entrar na Arena" }).click();
await page.locator(".question").waitFor();
await shot("12-arena-questao");
await page.locator(".option", { hasText: "10" }).click();
check("selecionar não envia", (await page.locator(".result").count()) === 0);
await page.getByRole("button", { name: "Confirmar resposta" }).click();
await page.locator(".result-title").waitFor({ timeout: 8000 });
await shot("13-arena-erro");
check("erro mostra gabarito em texto", await page.locator(".tag", { hasText: "Gabarito" }).isVisible());
check("erro mostra sua resposta em texto", await page.locator(".tag", { hasText: "Sua resposta" }).isVisible());
await page.getByRole("button", { name: "Criar flashcard do erro" }).click();
check("erro abre rascunho editável", await page.getByRole("dialog", { name: /flashcard do erro/ }).isVisible());
await page.getByRole("button", { name: "Descartar rascunho" }).click();
await page.getByRole("button", { name: "Próxima questão" }).click();
await page.locator(".option", { hasText: "Certo" }).click();
await page.getByRole("button", { name: "Confirmar resposta" }).click();
await page.locator(".result-title").waitFor({ timeout: 8000 });
check("acerto reconhecido", (await page.locator(".result-title").innerText()).includes("Você acertou"));
await shot("14-arena-acerto");
await page.getByRole("button", { name: /Sair/ }).click();
await page.getByRole("button", { name: "Ver resumo e encerrar" }).click();
await page.getByRole("heading", { name: "Resultado da sessão" }).waitFor();
await shot("15-arena-resumo");
check("resumo separa acertos e erros", (await page.locator(".stat-row").first().innerText()).includes("acertos"));

// 5. Flashcards
await page.goto(`${BASE}/flashcards`);
await page.getByRole("heading", { name: "Flashcards" }).waitFor();
await page.waitForTimeout(500);
await shot("16-flashcards");
await page.getByRole("link", { name: /Estudar cartões novos/ }).click();
await page.locator(".flashcard").waitFor();
check("avaliações escondidas antes de revelar", (await page.locator(".ratings").count()) === 0);
await shot("17-cartao-frente");
await page.getByRole("button", { name: "Mostrar resposta" }).click();
await shot("18-cartao-verso");
check("avaliações aparecem após revelar", (await page.locator(".rating").count()) === 4);
await page.getByRole("button", { name: /^Bom/ }).click();
await page.waitForTimeout(1500);
await page.getByRole("button", { name: "Mostrar resposta" }).click();
await page.keyboard.press("4");
await page.waitForTimeout(1200);
check("intervalo vem do serviço", (await page.getByText(/Cartão anterior: volta em/).count()) === 1);
await page.getByRole("button", { name: /Encerrar/ }).click();
await page.getByRole("button", { name: "Encerrar rodada" }).click();
await shot("19-rodada-concluida");
await page.goto(`${BASE}/flashcards?ver=pessoais`);
await page.waitForTimeout(800);
check("cartão criado da nota aparece", await page.getByText("O que uma chave estrangeira referencia?").isVisible());
await shot("20-cartoes-pessoais");
await page.getByRole("button", { name: /Ações do cartão/ }).first().click();
await page.getByRole("menuitem", { name: "Excluir" }).click();
check("exclusão pede confirmação específica", await page.getByRole("dialog", { name: "Excluir este cartão?" }).isVisible());
await page.getByRole("button", { name: "Cancelar" }).click();
await page.goto(`${BASE}/flashcards/deck/exemplo.deck.vazio`);
await page.getByRole("heading", { level: 1 }).waitFor();
await page.waitForTimeout(300);
check("deck vazio tem estado próprio", await page.getByText("Este deck ainda não tem cartões").isVisible());
await shot("21-deck-vazio");

// 6. Conta e falha de conexão (no serviço real: rede do navegador cortada de verdade)
const SERVICO = process.env.MODE === "servico";
await page.goto(`${BASE}/conta`);
await page.getByRole("heading", { name: "Conta e progresso" }).waitFor();
await page.waitForTimeout(800);
await shot("22-conta");
if (!SERVICO) {
  await page.getByLabel(/Simular queda de conexão/).check();
  await page.waitForTimeout(800);
}
await page.goto(`${BASE}/campo/aula/exemplo.aula.juncoes/ler`);
await page.locator(".pdf-page canvas").first().waitFor();
await page.waitForTimeout(800);
if (SERVICO) await ctx.setOffline(true);
await page.locator("#li-pagina-1").check();
await page.waitForTimeout(1500);
const pill = await page.locator(".sync-pill").getAttribute("data-state");
check("sem conexão a marcação fica guardada", ["offline", "pending", "error"].includes(pill ?? ""), `estado ${pill}`);
check("status da página indica pendência", await page.locator(".pdf-page").first().locator(".mark-status.warn").isVisible());
await shot("23-leitor-offline");
if (SERVICO) {
  await ctx.setOffline(false);
  await page.waitForTimeout(3000);
} else {
  await page.goto(`${BASE}/conta`);
  await page.getByLabel(/Simular queda de conexão/).uncheck();
  await page.waitForTimeout(2500);
}
const pill2 = await page.locator(".sync-pill").getAttribute("data-state");
check("ao reconectar envia a fila", pill2 === "synced", `estado ${pill2}`);

// 7. Celular e tablet
for (const [w, h, tag] of [
  [390, 844, "celular"],
  [820, 1180, "tablet"],
]) {
  await page.setViewportSize({ width: w, height: h });
  await page.goto(`${BASE}/`);
  await page.waitForTimeout(700);
  await shot(`30-${tag}-inicio`);
  await page.goto(`${BASE}/campo/aula/exemplo.aula.juncoes/ler`);
  await page.locator(".pdf-page canvas").first().waitFor();
  await page.waitForTimeout(1000);
  await shot(`31-${tag}-leitor`);
  await page.goto(`${BASE}/arena/sessao?materia=subject.estruturas-dados`);
  await page.locator(".question").waitFor();
  await page.waitForTimeout(400);
  await shot(`32-${tag}-arena`);
  await page.goto(`${BASE}/flashcards`);
  await page.waitForTimeout(600);
  await shot(`33-${tag}-flashcards`);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  check(`sem rolagem horizontal (${tag})`, !overflow);
}

// 8. Teclado: foco visível no primeiro controle
await page.setViewportSize({ width: 1440, height: 900 });
await page.goto(`${BASE}/campo`);
await page.keyboard.press("Tab");
const skip = await page.evaluate(() => document.activeElement?.textContent);
check("primeiro Tab é 'Pular para o conteúdo'", skip?.includes("Pular para o conteúdo") ?? false);

check("sem erros de página/console", errors.length === 0, errors.slice(0, 5).join(" | "));
await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} verificações ok`);
process.exit(failed.length ? 1 : 0);
