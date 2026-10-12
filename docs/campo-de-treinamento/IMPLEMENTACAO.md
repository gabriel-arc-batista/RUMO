# Campo de Treinamento — o que foi implementado (11/10/2026)

## Decisões a partir da inspeção

- **Stack mantida:** Python 3.13 + Tk 8.6 + SQLite. Nada web, nada embutido de navegador.
- **Leitor:** pypdfium2 (PDFium, Apache-2.0/BSD-3). As páginas viram dados PPM exibidos pelo próprio Tk, sem Pillow em tempo de execução. Só a página visível e duas vizinhas ficam em memória. PyMuPDF foi descartado pela licença AGPL.
- **Dados pessoais** (página, notas, marcadores, favoritos, conclusão manual, vínculo sessão↔aula, metadados de PDFs próprios) ficam no SQLite, no **esquema v6 aditivo**, com cópia `pre-campo-*.sqlite3` antes de migrar. Backups v6 incluem esses dados; v1 a v5 continuam aceitos.
- **Catálogo e PDFs** ficam em arquivos em `<dados>/conteudo/` (`catalogo/`, `arquivos/<aula>/<versão>/<sha256>.pdf`, `pessoal/`, `temp/`). Remover um download nunca apaga notas.
- **Sessão de estudo:** "Estudar esta aula" abre o relógio existente com matéria, assunto e aula. O estado do relógio carrega `lesson_id` e `lesson_version`, inclusive após reiniciar. Ao encerrar, `save_session` grava `training_session_links` na mesma transação. Regravar o mesmo encerramento não duplica nada: o ID da sessão é o do relógio.
- **RPG discreto:** nenhum XP ou moeda por abrir, baixar, favoritar ou concluir leitura. Só o tempo da sessão segue as regras que já existiam.

## Arquivos

| Arquivo | Papel |
|---|---|
| `training_schema.py` | Tabelas v6 e validação dessas tabelas nos backups |
| `training_catalog.py` | Contrato e validação do catálogo público |
| `training_content.py` | Provedores (pasta local e HTTPS), downloads, importação de PDF próprio |
| `training.py` | Estado de leitura, biblioteca combinada, filtros, busca, "continuar" |
| `pdf_reader.py` | Leitor dentro da janela |
| `screen_training.py` | Tela do Campo de Treinamento |
| `assets/training/curriculo.json` | 9 programas (907 itens extraídos, pendentes) e planejamento (60 famílias, 267 aulas) |
| `scripts/audit_training_programs.py` | Extração auditável dos editais oficiais |
| `scripts/prepare_training_curriculum.py` | Gera o currículo empacotado |
| `scripts/make_test_lesson.py` | Catálogo e PDF **de teste** em `tests/fixtures/campo-teste/` |
| `scripts/build_training_catalog.py` | Monta o `catalog.json` publicável (bytes, SHA-256, validação) |

## Como usar

1. Abra **Campo** na barra lateral. Sem fonte configurada, você vê o planejamento (filtro *Planejadas*) e pode importar PDFs próprios (menu **Conteúdo → Importar PDF próprio**). PDFs próprios aparecem como "Material pessoal" e nunca contam como cobertura.
2. **Conteúdo → Configurar fonte de conteúdo:**
   - *Pasta local:* uma pasta com `catalog.json` e os PDFs em caminhos relativos.
   - *Endereço remoto:* o `https://…/catalog.json` público. Marque "Permitir os hosts de download do GitHub Releases" se os PDFs estiverem lá.
3. **Conteúdo → Atualizar catálogo.** Um catálogo inválido é recusado com o motivo, e o anterior continua ativo.
4. Na aula: **Baixar** → **Abrir** ou **Estudar esta aula**.

Para ver o fluxo agora, aponte a pasta local para `tests/fixtures/campo-teste` (catálogo de **teste**, identificado como tal).

## Leitor

- Páginas: PgUp/PgDn, setas e roda do mouse, que passa de página no fim.
- Zoom com Ctrl +/−, ajuste por largura ou por página.
- Índice do PDF quando existe; caso contrário, a ausência é informada.
- Marcadores com Ctrl+D.
- Busca com Ctrl+F e Enter, com destaque na página. Se o PDF não tiver texto, a busca avisa que não está disponível; não há OCR.
- Notas no painel lateral, ligadas à aula, à versão e opcionalmente à página.
- Modo foco esconde a navegação; Esc sai. O relógio no rodapé continua visível.
- A página do PDF mantém as cores originais.

## Estados

- **Publicação:** `planejada`, `rascunho`, `em_revisao`, `publicada`, `arquivada` e `teste`, este só em catálogo de teste.
- **Disponibilidade local:** precisa baixar, baixando, disponível offline, falha e nova versão disponível. Uma versão antiga continua abrindo; notas antigas ficam marcadas com a versão em que foram escritas.

## Validação feita (Linux, dados temporários)

- 133 testes unitários, incluindo `tests/test_training.py`: catálogo malformado mantém o anterior, hash incompatível, arquivo maior que o declarado, cancelamento, falha de conexão, redirecionamento para host não aprovado, atualização de versão preservando notas e posição, remoção de download preservando notas, encerramento idempotente, backup v6 e restauração v5, migração v5→v6 com cópia e importação de PDF próprio.
- Fluxo no aplicativo real (19 verificações): catálogo → download → leitor (busca, nota, marcador) → "Estudar esta aula" → leitor e rodapé com a mesma sessão → encerramento único (25 XP de 25 min, zero questões) → reinício com a fonte sem conexão → leitura offline na página salva, com notas e marcador.
- `verify_rpg_gui.py`, `verify_rpg_dialogs.py` e `verify_appearance_gui.py` executados depois da integração.

## Não verificado

- Build do executável Windows e o leitor no Windows (o `RUMO.spec` coleta o PDFium; confirme no workflow da release).
- Download real de um catálogo HTTPS publicado: ainda não existe hospedagem. A lógica remota foi testada com respostas simuladas.
- Leitor de tela externo e escalas de sistema acima de 100%.
