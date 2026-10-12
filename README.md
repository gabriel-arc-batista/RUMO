# RUMO — Estudos

Organize sua preparação para concursos, provas e outros objetivos de aprendizagem. O RUMO é um aplicativo desktop em português que reúne planos, ciclos, assuntos, sessões de foco e acompanhamento de progresso.

Funciona localmente, sem exigir conta, assinatura ou conexão com a internet. A interface nativa usa Python, Tk e SQLite, com foco em baixo consumo de memória.

## Recursos

- **Planos independentes:** organize diferentes concursos ou objetivos, com matérias próprias e data de prova opcional.
- **Assuntos e subassuntos:** monte seu conteúdo, marque o que concluiu e guarde observações durante o estudo.
- **Ciclos de estudos:** distribua matérias em blocos, gere uma fila por pesos e acompanhe o próximo passo.
- **Foco e registro:** use cronômetro ou contagem regressiva, pause quando precisar e registre tempo líquido, questões, materiais e onde parou.
- **Revisões e simulados:** acompanhe tarefas de revisão e resultados por matéria.
- **Metas e desafios:** escolha seu nível e uma meta principal, lembrada durante o foco.
- **Estatísticas:** acompanhe constância, tempo estudado, questões e aproveitamento com dados dos seus registros.
- **Personalização:** temas claro e escuro, fonte Inter e animações que podem ser desativadas.
- **Backup e exportação:** backups automáticos, restauração de JSON/SQLite e exportação de registros em CSV.

## Jornada de estudos

A missão sugerida retoma o próximo bloco, o assunto e sua anotação de onde parou. “Hoje está difícil” permite reduzir o tempo; sessões parciais guardam o restante sem decidir o bloco ou avançar o ciclo.

O RPG usa seus registros reais: um XP por minuto líquido completo e uma moeda virtual por dez XP de cada sessão. Concluir um encontro de revisão ou desafio rende cinco XP de participação. Acertos não multiplicam XP. O nível L exige 100 × L XP para o seguinte. Tempo representa esforço; desempenho observado exige pelo menos 20 questões respondidas em três datas e não comprova domínio.

Descreva dificuldades manualmente, registrando por que errou e o que precisa lembrar. A revanche usa a agenda de revisões existente. Tente lembrar antes de consultar o material e, se quiser, registre “Lembrei”, “Parcial” ou “Não lembrei”. Evidências espaçadas podem sugerir superação; você decide se a dificuldade foi superada. Atrasos e ausências não retiram recompensas.

Masmorras e chefes usam assuntos já estudados e questões do seu material. Chefes registram simulados e resultados por matéria no histórico existente. Não há geração de questões por IA nem catálogo de provas. Moedas compram acessórios com prévia e confirmação. Equipamentos têm atalhos de estudo, sem alterar resultados ou multiplicar XP.

Editar ou excluir um estudo recalcula recompensas. Compras permanecem: se uma correção retirar moedas já gastas, o saldo disponível fica em zero e ganhos futuros compensam a diferença. Capítulos desbloqueados permanecem. Estudos antigos não ganham XP automaticamente: “Importar XP do histórico” apresenta os registros e valores antes da confirmação. Personagem, história, efeitos e avisos de recompensa podem ser ocultados nas preferências.

### Equipamentos e caminhos de classe

Um personagem novo começa no nível 1 com **trapos e uma espada enferrujada**, sem moedas ou experiência fictícias. O inventário tem 38 itens entre roupas, armaduras, armas, montarias e acessórios. Recompensas de evolução são recebidas gratuitamente ao atingir o nível e o marco indicados; acessórios antigos continuam compráveis. Clique no item para ver o propósito, os requisitos, equipar e usar seu atalho.

Os seis caminhos crescem juntos, sem obrigar a escolher uma classe:

| Caminho | Prática que faz evoluir |
| --- | --- |
| Paladino | Revisões realizadas, mesmo atrasadas ou com erros. |
| Guerreiro | Questões respondidas do seu material; erros também contam. |
| Mago | Tentativas de recordação, contadas uma vez por assunto/data; “Não lembrei” também conta. |
| Cartógrafo | Assuntos distintos estudados. |
| Ladino | Dificuldades investigadas em estudos e revanches reais. |
| Erudito | Assuntos estudados com anotações próprias no caderno ou na sessão. |

Armas preparam questões, revisões ou desafios; armaduras ajudam a preparar revisões e revanches; roupas e botas oferecem foco curto e retomada. A mula libera uma rota de estudo/revisão, o cavalo acrescenta revanche e o grifo acrescenta desafio. As montarias exigem datas de estudo **sem precisar ser consecutivas**. Usar um equipamento prepara uma atividade: o estudo só é registrado após você realizá-lo e salvar a sessão. Os recursos de estudo continuam disponíveis independentemente dos itens.

Recompensas conquistadas permanecem após correções e ausências. Veja níveis, marcos e verificações em [Equipamentos e classes](docs/RUMO_EQUIPMENT.md).

## Instalação no Windows

Baixe os arquivos na página de [Releases](https://github.com/gabriel-arc-batista/RUMO/releases). O acesso depende da visibilidade do repositório e das permissões da sua conta.

| Opção | Como usar |
| --- | --- |
| Instalador | Execute `RUMO-Instalar-Windows.exe`. A instalação é por usuário, sem necessidade de administrador. Há opção de criar atalho na área de trabalho. |
| Portátil | Extraia `RUMO-Windows-Portatil.zip` e abra `RUMO/RUMO.exe`. Mantenha a pasta `_internal` junto do executável. |

Não é necessário instalar Python para usar esses pacotes. Executável, pasta de instalação, ícones, backups novos e configuração de dados usam a marca `RUMO`.

Os dados ficam em `%LOCALAPPDATA%\RUMO`, separados dos arquivos do programa. Atualizar ou desinstalar o aplicativo preserva essa pasta. Na primeira abertura, uma base anterior é identificada pelo esquema e copiada de forma consistente, sem apagar o original. Feche a instalação anterior antes de abrir a nova. Backups JSON e SQLite das versões 1, 2, 3, 4 e 5 continuam sendo validados e aceitos independentemente do rótulo de marca.

O instalador ainda não possui assinatura digital. Os arquivos `SHA256SUMS.txt` das releases permitem conferir os hashes dos downloads.

## Comece com seu próprio plano

1. Abra **Configurações → Gerenciar planos e matérias → Novo plano**. Dê um nome ao concurso ou objetivo; a data da prova é opcional.
2. Cadastre suas matérias em **Nova matéria** e organize o conteúdo em **Edital e assuntos**. Adicione assuntos e subassuntos ou importe conteúdo estruturado.
3. Em **Ciclo de estudos**, crie blocos ou gere uma fila por pesos. Cada bloco representa um período de estudo de uma matéria; sessões parciais acumulam tempo nele.
4. Abra o **Relógio**, no canto inferior direito, para estudar com foco. Para registrar uma sessão manualmente, use **Adicionar estudo**.
5. Marque os subassuntos concluídos, anote suas observações e acompanhe revisões, metas e estatísticas.

Os planos pré-carregados são referências iniciais; você pode criar seu próprio plano e arquivar os que não utiliza. As fontes e os limites dos conteúdos incluídos estão em [FONTES.md](FONTES.md). Guias de estudo são sugestões pedagógicas e devem ser conferidos com o edital do seu concurso.

### Importar conteúdo

A importação aceita texto estruturado, CSV ou JSON e mostra uma prévia antes de salvar. Um exemplo simples de texto é:

```text
Matemática | Operações básicas
Matemática | Adição | Operações básicas
Matemática | Subtração | Operações básicas
Língua Portuguesa | Interpretação de textos
```

O formato de cada linha é `matéria | assunto | assunto pai opcional`. Revise a hierarquia antes de confirmar. Não há extração automática de qualquer PDF de edital.

### Atalhos

| Atalho | Ação |
| --- | --- |
| `Ctrl+N` | Registrar estudo |
| `Ctrl+R` | Abrir relógio |
| `Ctrl+Enter` | Salvar formulário |
| `Esc` | Fechar formulário ou sair da tela cheia |

## Dados e recuperação

Pausas não entram no tempo líquido. Ao reabrir o aplicativo, uma sessão recuperada permanece pausada; o tempo com o programa fechado ou o computador suspenso não é acrescentado. O relógio salva checkpoints a cada cinco segundos.

Backups automáticos usam a API consistente do SQLite, com sete cópias por padrão. Destino e retenção são configuráveis. A restauração valida os dados e guarda uma cópia anterior antes de substituir a base. Para restaurar, finalize ou descarte o rascunho ativo.

Arquivar um plano ou matéria preserva o histórico. Concluir um bloco do ciclo não conclui automaticamente a teoria de um assunto. O aproveitamento considera acertos sobre questões respondidas; não são criados estudos fictícios para preencher gráficos.

Dados e backups são locais e não são criptografados. A revisão de segurança e seus limites estão em [SECURITY_REVIEW.md](SECURITY_REVIEW.md).

## Desenvolvimento

Ambiente validado: Windows 11 x64, Python 3.13 e Tcl/Tk 8.6. O runtime utiliza a biblioteca padrão e `tzdata`; ferramentas de preparação, testes e empacotamento ficam separadas do executável.

```powershell
git clone https://github.com/gabriel-arc-batista/RUMO.git
cd RUMO
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt -r requirements-quality.txt
python app.py
```

Enquanto o repositório for privado, o clone exige acesso autorizado. Para testes com dados isolados, configure `RUMO_DATA` para uma pasta temporária.

### Verificação e build

```powershell
python -m black --check .
python scripts/check_repository.py
python -m unittest discover -s tests -v
python scripts/verify_rpg_gui.py
python scripts/verify_rpg_dialogs.py
python scripts/verify_gui.py
python scripts/build.py
```

O build gera o executável e o ZIP em `dist/`. Para gerar também o instalador Windows, disponibilize o compilador Inno Setup conforme [as instruções de release](.agents/RELEASE.md). Execute os testes de interface um de cada vez; eles abrem janelas reais e usam dados isolados.

A versão 1.0.0 integra o frontend, a progressão RPG e a personalização do viajante. As verificações usam bases temporárias e não alteram seu histórico. Veja [a revisão final](docs/RUMO_V1_VALIDATION.md) e [as regras de equipamentos](docs/RUMO_EQUIPMENT.md).

A versão 2.0.0 acrescenta conta opcional, sincronização de ações de estudo e integração com o site. O aplicativo continua nativo e permite estudar offline. Histórico anterior exige seleção explícita para compartilhamento; PDFs pessoais permanecem locais. Consulte [os contratos e a configuração](docs/integration/SETUP.md).

## Continuidade do projeto

Leia [AGENTS.md](AGENTS.md) e o [contexto de arquitetura, testes e segurança](.agents/README.md) antes de alterar o código. Preserve os dados existentes e a compatibilidade dos backups. Bancos pessoais, `.env`, credenciais, capturas, relatórios locais e builds não devem entrar no Git.

Sugestões de melhoria devem descrever o problema, o comportamento esperado e, quando possível, como reproduzi-lo, sem incluir dados pessoais.

## Licença e status open source

O código próprio do RUMO ainda não tem uma licença de uso e redistribuição definida. Portanto, o projeto ainda não é apresentado como open source. Torná-lo público, por si só, não concede essas permissões; é necessário adotar uma licença apropriada. Consulte a [orientação do GitHub sobre licenças](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) e a [definição da Open Source Initiative](https://opensource.org/osd).

As dependências, fontes e demais materiais de terceiros mantêm seus próprios termos e atribuições, descritos em [THIRD_PARTY.md](THIRD_PARTY.md) e [FONTES.md](FONTES.md).

### Pacote Linux

O build nativo gera `dist/RUMO-linux-portatil.tar.gz`. Extraia o arquivo e execute `RUMO/RUMO`; preserve a pasta `_internal` junto ao executável. O banco permanece no diretório de dados do usuário. Para testes isolados, configure `RUMO_DATA` para uma pasta temporária.

A entrega 2.0.0 está em validação final: pacote Linux e serviço de conta foram
verificados; revisão do frontend, CI Windows e publicação ainda estão pendentes.
Veja [as evidências e os limites](docs/integration/VALIDATION.md).
