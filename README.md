# RUMO — Estudos

Organize sua preparação para concursos, provas e outros objetivos de aprendizagem. O RUMO é um aplicativo desktop em português que reúne planos, ciclos, assuntos, sessões de foco e acompanhamento de progresso.

Funciona localmente, sem conta, assinatura ou conexão obrigatória com a internet. A interface nativa usa Python, Tk e SQLite, com foco em baixo consumo de memória.

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

## Instalação no Windows

Baixe os arquivos na página de [Releases](https://github.com/gabriel-arc-batista/RUMO/releases). O acesso depende da visibilidade do repositório e das permissões da sua conta.

| Opção | Como usar |
| --- | --- |
| Instalador | Execute `RUMO-Instalar-Windows.exe`. A instalação é por usuário, sem necessidade de administrador. Há opção de criar atalho na área de trabalho. |
| Portátil | Extraia `RUMO-Windows-Portatil.zip` e abra `RUMO/RUMO.exe`. Mantenha a pasta `_internal` junto do executável. |

Não é necessário instalar Python para usar esses pacotes. Executável, pasta de instalação, ícones, backups novos e configuração de dados usam a marca `RUMO`.

Os dados ficam em `%LOCALAPPDATA%\RUMO`, separados dos arquivos do programa. Atualizar ou desinstalar o aplicativo preserva essa pasta. Na primeira abertura, uma base anterior é identificada pelo esquema e copiada de forma consistente, sem apagar o original. Feche a instalação anterior antes de abrir a nova. Backups JSON e SQLite das versões 1, 2 e 3 continuam sendo validados e aceitos independentemente do rótulo de marca.

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
python scripts/verify_gui.py
python scripts/build.py
```

O build gera o executável e o ZIP em `dist/`. Para gerar também o instalador Windows, disponibilize o compilador Inno Setup conforme [as instruções de release](.agents/RELEASE.md). Execute os testes de interface um de cada vez; eles abrem janelas reais e usam dados isolados.

O executável ficou em aproximadamente 40–65 MB de RAM nas medições locais anteriores. Esse intervalo é uma observação, não um requisito máximo garantido. Linux tem caminho de build, mas ainda não foi validado.

## Continuidade do projeto

Leia [AGENTS.md](AGENTS.md) e o [contexto de arquitetura, testes e segurança](.agents/README.md) antes de alterar o código. Preserve os dados existentes e a compatibilidade dos backups. Bancos pessoais, `.env`, credenciais, capturas, relatórios locais e builds não devem entrar no Git.

Sugestões de melhoria devem descrever o problema, o comportamento esperado e, quando possível, como reproduzi-lo, sem incluir dados pessoais.

## Licença e status open source

O código próprio do RUMO ainda não tem uma licença de uso e redistribuição definida. Portanto, o projeto ainda não é apresentado como open source. Torná-lo público, por si só, não concede essas permissões; é necessário adotar uma licença apropriada. Consulte a [orientação do GitHub sobre licenças](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) e a [definição da Open Source Initiative](https://opensource.org/osd).

As dependências, fontes e demais materiais de terceiros mantêm seus próprios termos e atribuições, descritos em [THIRD_PARTY.md](THIRD_PARTY.md) e [FONTES.md](FONTES.md).
