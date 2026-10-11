# Rumo — Estudos

Aplicativo desktop de estudos para Windows, local e offline, com interface nativa em português, SQLite, tema preto e dourado e sem navegador embutido. Não exige instalar Python ou Node para usar o executável.

## Abrir

Baixe o instalador ou o ZIP portátil em [Releases](https://github.com/gabriel-arc-batista/RUMO/releases). Os arquivos de `dist/` são gerados pelo build e não ficam no Git.

- **Instalação:** abra `dist/Rumo-Instalar-Windows.exe`. O instalador é por usuário e cria atalho no menu Iniciar.
- **Portátil:** abra `dist/RUMO/RUMO.exe`. Mantenha a pasta `_internal` junto do executável. Copiar apenas o EXE não funciona.
- O ZIP portátil pode ser extraído em qualquer pasta. Os dados ficam em `%LOCALAPPDATA%\RUMO`, separados do programa e preservados ao atualizar/desinstalar.

## Primeiros passos

1. Escolha no alto **BACEN 2024 — Tecnologia da Informação** ou **BACEN 2024 — Economia e Finanças**. Ambos começam sem registros de estudo ou data de nova prova.
2. Em **Edital e assuntos**, abra cada matéria e seus tópicos. São 130 itens oficiais para TI e 157 para Economia e Finanças, preservados, mais um **Guia de estudo** com 565 assuntos menores em TI e 525 em Economia e Finanças. Java inclui estruturas sequenciais, condicionais, laços, classes, métodos, interfaces, exceções e coleções; bancos de dados inclui normalização, joins, transações, índices e SQL procedural. Busque por nome, com ou sem acentos. O progresso conta apenas os assuntos finais, uma vez; o filtro não altera a porcentagem.
3. Em **Ciclo de estudos**, gere uma fila por pesos ou crie seus blocos. Um bloco é um período alvo de uma matéria. Estudos parciais acumulam no bloco; avançar é uma ação explícita.
4. Use **Adicionar estudo** para registrar matéria, assunto, tempo pretendido, tempo líquido, questões, material e onde parou. Pode digitar nomes novos nos seletores para criá-los.
5. O botão circular de **Relógio**, no canto inferior direito, abre o início do foco com busca de matéria/assunto e atalhos de duração. O registro manual fica em **Adicionar estudo**. Seu indicador mostra sessão ativa ou pausada; passe o mouse para ver o tempo e clique para retornar. Pausas não contam. Finalizar abre o registro para completar as questões e salvar.
6. **Revisões** reúne hoje, atrasadas, próximas e concluídas. O calendário é apoio, sem impor matérias em dias fixos.
7. **Configurações e ajuda** permite exportar JSON, CSV, fazer backup SQLite e restaurar JSON ou SQLite.

Atalhos: `Ctrl+N` registrar estudo, `Ctrl+R` relógio, `Ctrl+Enter` salvar formulário, `Esc` fechar formulário/sair da tela cheia. Tabelas têm rolagem horizontal, ordenação pelo cabeçalho e navegação por teclado. O menu ☰ pode ser recolhido.

O painel usa três referências pesquisadas: [Estudei](https://wp.estudei.com.br/tutoriais/) para acompanhamento do estudo, [Linear](https://linear.app/now/how-we-redesigned-the-linear-ui) para hierarquia e navegação e [Material Design 3](https://github.com/material-components/material-web/blob/main/docs/components/text-field.md) para campos e estados de foco. A composição inclui indicadores no topo, constância em uma faixa e matérias ao lado do objetivo, metas e gráfico semanal. A fonte Inter acompanha o programa e é carregada somente nele. O menu lateral de 230 px começa aberto, pode ser recolhido e guarda sua preferência. Conteúdo e cartões ficam alinhados à esquerda, com superfícies escuras, bordas neutras e dourado reservado à identidade, às ações principais e ao progresso. A seleção é discreta, com marcador lateral. O edital usa seções expansíveis, texto com quebra de linha e uma rolagem vertical principal. Cartões entram gradualmente; botões reagem ao mouse e ao teclado. O relógio abre centralizado, deslizando e aparecendo sobre um fundo escurecido, com dígitos grandes e progresso dourado. Animações param ao terminar a interação. Tema claro e preferência de tema são preservados. Para desativar animações, abra **Configurações → Preferências → Animações suaves**.

## BACEN: origem e limites

Incluído o [Edital nº 1 – BCB, de 15 de janeiro de 2024](https://bcb.gov.br/content/acessoinformacao/analista_2024/Edital-n-1-de-Abertura-do-concurso.pdf), PDF oficial completo e conteúdo estruturado da seção 18. É referência histórica de abertura, **não um edital novo**. A versão com retificações também está incluída em `assets/BACEN-2024-edital-retificado.pdf`; o item de conflito de interesses tem aviso da correção para a Lei 12.813/2013. A numeração original é preservada, inclusive inconsistências presentes no PDF. Nenhuma data antiga de prova vira previsão nova.

O script `scripts/prepare_bacen.py` reproduz a extração da fonte oficial; `assets/bacen2024.json` contém URL e SHA-256 do PDF. Reimportar conteúdo igual não duplica os assuntos do mesmo pai. Alterar o plano ativo mantém os registros isolados.

O detalhamento fica separado em `assets/bacen2024-detalhado.json`, reproduzido por `scripts/prepare_study_guide.py`. É um desdobramento pedagógico autoral, não texto oficial nem garantia de exaustividade. Fontes de apoio incluem [Java](https://dev.java/learn/), [Python](https://docs.python.org/3/tutorial/), [PostgreSQL](https://www.postgresql.org/docs/current/tutorial.html), legislação no Planalto e Cosif/BCB. Na atualização dos planos BACEN originais, o aplicativo cria backup consistente antes da expansão, preserva IDs, registros e matérias arquivadas; novos filhos herdam a conclusão do pai. A atualização é aplicada uma vez por versão do guia e por plano. O denominador do progresso passa a refletir os assuntos menores; não são inseridos estudos fictícios.


## Atualização 1.3.0

- Caixas verdes de conclusão por subassunto e caderno de descrição/observações persistente, acessível pelo lápis ou pela barra de ações. Salvar não reconstrói a lista nem desloca a rolagem.
- Seletores pesquisáveis com nomes legíveis, formulário de foco compacto, registro dividido em abas e relógio com anel de progresso. Inter, superfícies grafite, bordas e estados de foco dourados em todo o aplicativo.
- Oito desafios com três níveis (24 combinações), critérios explícitos e pontos calculados pelos registros, sem usar pontuação para inventar horas estudadas. O tempo semanal respeita segmentos que atravessam a meia-noite.
- 150 frases distintas, uma por data, com autor, obra/versículo e fonte consultável. Traduções próprias; atribuições tradicionais ou relatos históricos são identificados. Após 150 dias o ciclo recomeça. A leitura é offline.
- Gráficos de tempo líquido, questões e aproveitamento com unidades, legenda, detalhes ao passar o mouse e indicação de matérias a revisar quando há pelo menos dez respostas.
- Revisão de cobertura com 81 acréscimos nas duas áreas, ligados a provas BACEN/STJ 2024 ou à retificação, separados dos 287 itens originais. Consulte **Edital e assuntos → Fontes e cobertura** e [FONTES.md](FONTES.md).

A base migra da versão 2 para 3 adicionando observações. Backups JSON/SQLite das versões 1 e 2 continuam aceitos. Os novos assuntos são adicionados sem apagar conclusões, registros, notas ou arquivamentos existentes.

## Recuperação e backup

Ao fechar, o relógio pede para pausar e guardar o rascunho. Ao reabrir, ele permanece pausado; o tempo com o aplicativo fechado ou o computador suspenso não é acrescentado. Checkpoints são gravados a cada 5 segundos. Uma interrupção inesperada pode perder até aproximadamente 5 segundos desde o checkpoint, nunca contabiliza toda a ausência. Timer vencido fica pausado até uma ação sua.

O backup automático diário usa a API consistente do SQLite, com sete cópias por padrão. Destino e retenção são configuráveis. A restauração valida formato, versão, relações e dados antes de substituir, mostra uma prévia e guarda backup anterior. Exportar JSON pausa um rascunho ativo. Para restaurar outra base, finalize ou descarte primeiro o rascunho atual.

Arquivar planos, matérias, blocos e assuntos preserva o histórico. Exclusões de registros pedem confirmação. Concluir um bloco não marca teoria nem revisão. Excluir uma sessão não desfaz uma conclusão de teoria que foi marcada explicitamente.

## Critérios dos indicadores

- Aproveitamento: acertos / (acertos + erros), ponderado pelas questões. Sem respondidas, aparece “Sem questões”. Simulados mostram também acertos / total apresentado.
- Simulado aparece no histórico como a mesma sessão. Resultados por matéria não repetem os totais gerais. Tempo sem distribuição medida fica no total do simulado; não se inventam durações por matéria.
- Tempo pretendido, líquido e videoaula são separados. Páginas/h usa somente sessões com páginas e tempo positivo.
- Estudos manuais usam a data informada. O relógio preserva segmentos por data no fuso configurado; gráficos diários distribuem o tempo nesses segmentos. Questões permanecem na data atribuída. Editar a duração redistribui os segmentos proporcionalmente.
- Conquistas são recalculadas, inclusive após correções. Semana perfeita usa os dias elegíveis; Corujão é opcional. Não há notificações quando o aplicativo está fechado.

## Desenvolvimento e testes

Python 3.13, Tcl/Tk 8.6. O runtime usa biblioteca padrão e a base de fusos `tzdata`; Pillow, psutil, pypdf e PyInstaller são ferramentas de desenvolvimento/build e não entram no runtime.

```powershell
python -m pip install -r requirements-dev.txt
python app.py
python -m unittest discover -s tests -v
python scripts/verify_gui.py
python scripts/build.py
```

`verify_gui.py` abre janelas reais, testa fluxos em uma base temporária e salva imagens/medições em `validation`. Não escreve fixtures na base pessoal. `RUMO_DATA` pode indicar uma pasta isolada durante testes.

`verify_performance.py` mede consultas com 10 mil registros temporários. `verify_distribution.py` abre o EXE real com uma base isolada, mede recursos e verifica instância única e persistência. As medições deste Windows ficaram em aproximadamente 40–65 MB de RAM nos testes anteriores para o EXE e CPU em repouso de 0% no intervalo observado; são medições, não limites fixos para qualquer computador.

O build Windows foi realizado no Windows x64. Para Linux, execute o mesmo build em uma máquina Linux com Tk instalado; ele gera um pacote portátil `.tar.gz`. **Linux não foi executado nem validado neste ambiente.** O relatório de validação e a matriz dos requisitos ficam em `validation/` e `CHECKLIST.md`.

## Atualização 1.4.0

Inter em toda a interface, frase no cabeçalho, seletor com rodapé reservado, cartões sem espaços artificiais e tema claro suave. Configurações organizadas em quatro grupos. Escolha a meta principal nos desafios e acompanhe seu lembrete no relógio. O ciclo guiado intercala matérias em blocos de 25 minutos e sugere o próximo subassunto pendente. A ordem de aprendizagem é uma sugestão pedagógica; a numeração e o texto do edital permanecem preservados, e a ordem oficial continua disponível nas preferências. Animação ao passar o mouse nos subassuntos, com opção de desativar movimentos.

## Revisão de segurança e organização 1.4.1

Código formatado com Black; validação de backups extraída para `backups.py` e políticas pequenas em `security.py`. Retenção só remove arquivos próprios; restauração mantém o destino local de backups. Links/pastas, hierarquia, relações e preferências recebem validação. CSV protege textos de interpretação como fórmulas. Consultas de filtro por matéria usam parâmetros. Pillow de desenvolvimento atualizado; não é incluído no executável.

Orientações para continuidade: [AGENTS.md](AGENTS.md) e [.agents/README.md](.agents/README.md). Resultado e limites da revisão: [SECURITY_REVIEW.md](SECURITY_REVIEW.md). Dados pessoais, relatórios locais, `.env` e builds ficam fora do Git. Binários são distribuídos pela página de Releases.

Backups JSON até 20 MB, SQLite até 100 MB e até 100 mil registros. O destino importado é ignorado na restauração. A retenção preserva backups antigos sem o novo prefixo; estes podem ser administrados manualmente. O instalador é por usuário e ainda não tem assinatura digital.

## Nome atualizado na versão 1.4.2

O aplicativo passou a se chamar **Rumo — Estudos**. A atualização mantém estudos, configurações e backups e substitui o atalho antigo. Os nomes internos de arquivos e pastas permanecem para compatibilidade com instalações anteriores.
