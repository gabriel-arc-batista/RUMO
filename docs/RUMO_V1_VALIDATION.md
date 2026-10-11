# Revisão final — RUMO 1.0.0

Release v1 da aplicação integrada, em 11/10/2026. A numeração pública recomeça em 1.0.0 para esta versão; o esquema SQLite permanece 5 e os identificadores históricos são preservados. As tags 1.4.x anteriores permanecem disponíveis.

## Integração e correções

- Frontend integrado ao motor real de estudos e RPG. Prévia fictícia apenas com `RUMO_JOURNEY=preview`.
- Paladino, Guerreiro, Mago, Cartógrafo, Ladino e Erudito; personagem inicial no nível 1, trapos e arma velha. Equipamentos, montarias e recompensas acompanham atividades reais.
- Seletores e diálogos aguardam a janela estar visível antes de capturar o foco. Regressão cobre o formulário ainda não mapeado que antes causava tela branca/fechamento.
- Personalização salva somente após confirmação; cancelar descarta o rascunho. O build regenera todas as camadas, e cada avatar mantém as imagens que está exibindo mesmo quando o cache é renovado.
- Abertura do edital retificado corrigida para Linux e Windows.
- Carregamento de fontes privadas corrigido no Windows; o import específico de Linux não pode ocultar o módulo `ctypes` no ramo Windows.

## Verificação

118 testes de domínio, persistência, migrações, backups, entradas inválidas, progressão e aparência. Scripts nativos `verify_rpg_gui.py`, `verify_rpg_dialogs.py` e `verify_appearance_gui.py` verificam atividades reais, formulários, equipamentos, caderno do Erudito, temas e personalização com bases sintéticas. Não se usa o banco pessoal.

Formatação Black e revisão de arquivos antes do commit. Pip-audit do ambiente de desenvolvimento: nenhuma vulnerabilidade conhecida encontrada. Bandit: nenhum achado alto; composição SQL revisada, valores parametrizados e identificadores limitados a listas internas. `random.choice` só seleciona aparência cosmética. Abertura de documentos/diretórios é ação explícita do usuário.

A distribuição Linux é extraída e executada sem as variáveis do ambiente de desenvolvimento. Conferem-se janela visível, esquema 5, ausência de sessões/XP fictícios, encerramento normal, logs e sockets de internet observados. O workflow Windows verifica os mesmos testes de fonte, o executável compilado, persistência, segunda instância, migração e instalação/desinstalação em diretório isolado. Resultado da execução e artefatos ficam vinculados à release.

## Limites

Testes não garantem ausência absoluta de bugs. Não houve teste externo com leitor de tela, IME, VM ou todas as configurações de DPI. No Linux/X11, o uso de XIM externo está desativado para evitar bloqueio no IBus. Os binários não têm assinatura digital. Hashes SHA-256 acompanham os pacotes. Dados locais e backups não são criptografados.
