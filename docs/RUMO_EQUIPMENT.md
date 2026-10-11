# Equipamentos e classes — RUMO 1.6.0

## Regras

Perfil novo: nível 1, zero XP/moedas, trapos e espada enferrujada. 38 itens: 25 iniciais/de evolução e 13 acessórios anteriores com IDs/preços preservados. Equipar substitui somente o item da mesma posição. Roupas, armadura, arma, escudo, cabeça, pés e montaria podem coexistir.

Recompensas de evolução são gratuitas e recebidas uma única vez. Não se equipam automaticamente sobre a escolha do usuário. Corrigir estudos recalcula esforço, saldo e marcos atuais; equipamentos já adquiridos permanecem. Histórico antigo continua opt-in. Não há bônus nas notas/XP nem recompensa por clicar numa ação.

| Caminho | Aprendiz / Adepto / Veterano |
| --- | --- |
| Paladino | 2 / 6 / 15 revisões realizadas |
| Guerreiro | 10 / 40 / 100 questões respondidas, acertos + erros |
| Mago | 3 / 7 / 15 tentativas de lembrar em pares assunto/data distintos |
| Cartógrafo | 2 / 5 / 10 assuntos estudados |
| Ladino | 1 / 3 / 6 dificuldades trabalhadas em estudos reais |
| Erudito | 2 / 5 / 10 assuntos estudados com anotações próprias |

São caminhos paralelos, sem especialização obrigatória. Autoavaliação “Não lembrei” conta como tentativa. Não se afirma domínio com base nos caminhos.

## Recompensas

- Nível 2: túnica, botas e espada de treino.
- Paladino: couro/escudo no nível 3 + 2 revisões; cota no nível 5 + 6; armadura do bastião no nível 7 + 15.
- Guerreiro: espada de aço no nível 4 + 10 respostas; arco no nível 5 + 40; lâmina no nível 7 + 100.
- Mago: veste/cajado de madeira no nível 3 + 3 tentativas; elmo no nível 4 + 3; cajado de lembranças no nível 5 + 7; manto no nível 6 + 7.
- Cartógrafo: casaco no nível 3 + 2 assuntos; capuz no nível 4 + 5; botas de expedição no nível 5 + 5.
- Ladino: casaco no nível 3 + 1 dificuldade trabalhada; abre o fluxo de revanche.
- Erudito: livro no nível 3 + 2 assuntos estudados com anotações; abre o caderno existente. “Erudito” é o equivalente adotado para scholar.
- Montarias: mula no nível 3 + 3 datas, cavalo no nível 5 + 7, grifo no nível 8 + 15. Datas não precisam ser seguidas.

Todos mostram propósito e requisitos no inventário. Ações preparam foco, retomada, questões, recordação, revisão, revanche, masmorra/chefe ou rota. Mula oferece duas opções de rota; cavalo acrescenta revanche; grifo acrescenta desafio. Cada atividade é realizada e registrada separadamente, pelos fluxos existentes.

## Persistência e bugs de janela

Esquema 5 amplia slots sem mudar os registros canônicos. SQLite v4 recebe cópia `pre-equipment` antes da migração transacional. Backups JSON/SQLite v1–v5 continuam aceitos, com IDs/preços validados. Personagens existentes conservam XP e itens.

O log apontou `grab failed: window not viewable` em um seletor. Seletores e confirmações agora adiam a captura de foco até o mapeamento; fechar a janela durante a abertura cancela a operação. Linux não anima opacidade de janelas nativas, evitando a transição que pode deixar conteúdo branco no compositor. Sem assuntos estudados, criar desafio explica o requisito e desativa salvar.

## Verificação

112 testes unitários/de domínio passaram, incluindo treze testes de evolução. Integração nativa do cronômetro/revisão/chefe/compra passou. `verify_rpg_dialogs.py` passou: seletor antes de aparecer o formulário, confirmação real, criação pela seleção múltipla, categorias e atalho da arma inicial, nos temas claro/escuro com animações ligadas/desligadas. Capturas com dados sintéticos verificaram personagem inicial/evoluído, montarias e caminhos em 1366×768 e 1024×700.

Pacote Linux 1.6.0 gerado e extraído em pasta temporária, sem variáveis do ambiente de desenvolvimento: janela aberta, schema 5, perfil real sem XP fictício, nenhum socket de internet na inspeção, encerramento normal e sem ERROR nos logs. RSS observado: 45 MiB. Windows 1.6.0 não foi validado nesta execução. Não foi usado o banco pessoal nos testes.

Ladino conta cada dificuldade uma vez, apenas com um estudo elegível inscrito no RPG e vinculado a ela; repetir ou abrir o formulário não aumenta o marco. Erudito conta cada assunto uma vez: exige estudo elegível inscrito e texto não vazio nas observações da sessão ou no caderno do assunto. Anotações sozinhas, espaços em branco e estudos antigos não incluídos no RPG não concedem progresso. Escrever notas não acrescenta XP nem cria uma sessão.

Verificação da ampliação para seis classes: testes de Ladino contam a dificuldade uma vez e preservam o casaco após correção; testes de Erudito exigem estudo inscrito e notas não vazias, sem bônus de XP. `verify_rpg_dialogs.py` também abre, edita e salva o caderno real pelo botão do Erudito, sem duplicar sessões. Paladino conserva o identificador anterior para compatibilidade; nomes exibidos e equipamentos usam Paladino.
