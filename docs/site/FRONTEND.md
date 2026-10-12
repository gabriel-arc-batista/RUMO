# Site do RUMO — decisões de frontend

Frontend do Claude em `web/`; contrato e serviço do Codex em `docs/integration/` e `backend/`.

## Visual

- **Mesmo produto do app:** tokens Norte Dourado copiados de `theme.THEMES["Norte Dourado"]` (fundo `#101011`, superfícies `#181819`/`#202021`, ouro `#C8AA6E`, verdete `#7FB5A8`). Inter para leitura e Poppins só na marca e no nome do personagem.
- **Superfícies sem borda**, separadas por luminosidade; listas com divisória fina; visões exclusivas em controle segmentado.
- **Um dourado por tela:** a ação principal. No Início, ele vai para a primeira ação de retomada disponível: continuar a aula, depois questões, depois revisar cartões vencidos.
- **Estado nunca só por cor:** "Sua resposta", "Gabarito", "Concluída", "Para revisar", "conflito", "salvo" e "enviando…" sempre têm texto e ícone.
- **RPG discreto:** o retrato real do app (camadas CC0 de N. Erebus) aparece na barra lateral e no Início, com nível e XP vindos de `progress_summary`. Mensagens curtas ("Golpe certeiro.", "Todo erro aqui é treino…", "Memória reforçada.") podem ser desligadas. O modo foco esconde a navegação e o personagem. O movimento segue o sistema ou a preferência.
- **Arena:** fio de bronze no topo da questão e enunciado em corpo maior; nada de molduras ou brilho.
- **Leitor:** a página fica em papel, nunca invertida. O "papel suave" só reduz o brilho (`brightness`/`sepia`), preservando imagens e diagramas. No ajuste "Largura", a página não passa de ~920 px.

## Comportamentos que o pedido exigia

- **"Li esta página":** uma caixa com o número embaixo de cada página e uma barra fixa que reflete a página mais visível ("Li esta página (7)"). A aula só conclui com todas as páginas marcadas, incluindo a última. O progresso diz "8 de 20 páginas marcadas como lidas", separado de "Página 7 de 20". A posição de retomada é outro evento e só é salva depois de a pessoa navegar. Ao voltar sem página indicada, o leitor oferece "Ir para a página N".
- **Arena:** escolher uma alternativa não envia nada; só "Confirmar resposta" cria a tentativa. O resultado aparece em texto e ícone, com gabarito e explicação vindos do serviço. Sem conexão, a resposta fica guardada e a correção aparece depois. O resumo separa respondidas, acertos, erros, anuladas, aguardando correção e tempo registrado, e avisa que poucas questões não medem domínio.
- **Flashcards:** as avaliações só aparecem depois de revelar o verso (teclas Espaço e 1–4). O intervalo mostrado é o `interval_days`/`due_at` devolvido pelo serviço; não há segundo cálculo. Nota e erro abrem um rascunho editável, e a frente é obrigatória. Importação e exportação seguem `RUMO-personal-cards` v1. Excluir pede confirmação específica.
- **Tempo:** cronômetro explícito, pausado quando a aba fica oculta; checkpoints ficam separados por conta e a retomada sempre começa pausada; suspensão longa não conta tempo. Só vira `study.session` (`plan_id: "site"`) ao confirmar. Tentativas e revisões usam o id da sessão, então as contagens ficam derivadas.
- **Sincronização:** fila em IndexedDB gravada antes da rede, com id de evento estável. Lote recusado é reenviado um a um. A gravação da fila e a resolução de conflitos são atômicas; a projeção só assume eventos após o commit. Abas recarregam eventos e cursor juntos, e o token é validado contra a conta da fila. Um conflito retém a cadeia da mesma entidade e só se resolve com escolha explícita ("Manter a do serviço" ou "Aplicar a minha", que aplica a última intenção). Uma ação nova sobre a mesma entidade substitui o conflito antigo.
- **Identidades** iguais às do desktop: favoritos `${tipo}:${id}:${versão}:favorite` (aula, questão, cartão e deck com versão vazia) e marcador `bookmark` com alvo `${aula}:${versão}:page:${N}`.

## Responsividade e acessibilidade

- Barra lateral acima de 1080 px, trilho de ícones no tablet e barra inferior no celular.
- No celular, o leitor mantém navegação, zoom e painéis em duas linhas, com a caixa da página atual sempre visível.
- Link "Pular para o conteúdo", foco visível só com teclado, diálogos com foco preso e Esc, menus navegáveis por setas, controles nomeados, `aria-live` nos resultados e sem rolagem horizontal em 390 px e 820 px.

## Validação (12/10/2026)

- 31 testes Vitest, incluindo falhas de gravação, troca de conta, abas simultâneas, recuperação do cronômetro e agenda entre versões.
- Fluxo de 40 verificações no Chrome 154 real, em dois modos: exemplo e serviço real local (GoTrue 2.177, PostgREST 14.2, Postgres 17.6 com as oito migrações do Codex).
- 16 cenários extras: conflito entre dois dispositivos, isolamento entre contas, sessão e nível, sair e entrar.
- Ida e volta com o cliente de sincronização do desktop (`sync_client.py`/`study_sync.py`): o que o site marca aparece no desktop, e a página e a revisão feitas no desktop aparecem no site.

## Limites reais

- Esta rodada de validação usou um gateway nginx no lugar do gateway do Supabase, sem SMTP, confirmação por e-mail nem chaves hospedadas.
- O catálogo real está vazio. Só há conteúdo de EXEMPLO identificado; os PDFs de exemplo usam `resource.url` porque o SQL reserva `pdf_url` a aulas revisadas.
- Aparência, ciclo, inventário e metas do app não sincronizam: o site mostra o retrato padrão e diz isso.
- Fórmulas aparecem como texto em fonte matemática, sem motor LaTeX.
- Testado só no Chrome (Linux). Firefox, Safari, Windows, leitores de tela e celulares físicos não foram testados.
