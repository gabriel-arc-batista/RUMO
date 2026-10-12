# Personalização leve com imagens licenciadas

Entrega local em 11/10/2026: Portrait Creator example_assets, N. Erebus, CC0.
Pesquisa, escolhas, limites e licenças: [THIRD_PARTY_ASSETS](../THIRD_PARTY_ASSETS.md).

Aparência/nome ficam em rascunho até salvar. Nome/aparência são gravados numa
única transação, sem alterar XP, moedas, inventário, histórico ou progressão.
A aparência continua global entre planos e o nome continua por plano, como os
contratos existentes. IDs antigos e preferência de orelhas são preservados.

6 rostos, 11 penteados + sem cabelo, 8 tons de pele, 8 cores de cabelo,
6 formatos de olhos, 5 íris, 7 cores de íris, 7 sobrancelhas, 7 narizes,
11 bocas, sem pelos faciais ou bigode. Todos compartilhados pelos dois presets
masculino/feminino. Não há corpo completo, óculos nem barba completa.

## Validação executada

Linux, Python 3.14 e Tk 8.6 com Xft, exclusivamente bases temporárias.

- 121 testes unitários aprovados; 8 específicos de aparência também passaram
  após a revisão final, com imagens, manifesto, origem/SHA-256, camadas, IDs,
  fallback, inventário não vazio, persistência e backup/restauração JSON.
- verify_appearance_gui: todos os 13 temas disponíveis na reforma concorrente;
  81 opções percorridas por tema, prévia, nome, salvar/cancelar, reset, aleatório,
  reabertura, imagens visíveis retidas, LRU e métricas inalteradas.
- Sem acessos externos para carregar imagens: teste de 120 aparências aleatórias
  com socket.create_connection e urllib.request.urlopen bloqueados. Os assets
  ficam locais; o código da personalização não faz solicitações de rede.
- Após percorrer os temas, 120 trocas adicionais: 141,0 MiB de RSS do processo
  completo, crescimento de 2,7 MiB sobre o começo desse lote. O valor inclui
  Tk, demais telas e módulos de QA; não equivale à RAM isolada da personalização.
  Cache compartilhado limitado a 24 imagens; miniaturas só da categoria aberta;
  imagens de editor descartadas ao fechar. Sem Pillow no runtime.
- Capturas reais das janelas em validation/character-examples: masculino,
  feminino, janela menor 900×620 e Jornada. Sem dados pessoais e fora do Git.
- Black nos arquivos tocados, diff --check e check_repository aprovados.
- Bandit: um aviso B311, random.choice na aparência aleatória. Revisado:
  apenas escolhe IDs visuais, sem criptografia, prêmios, dinheiro ou autenticação.
- Preparador legado de empacotamento base() verificado: compõe PNGs reais e
  continua produzindo a dimensão esperada 1200×1520, sem desenhar personagem.

Não foi produzido/publicado um novo instalador nesta tarefa. GUI Windows,
DPI e leitor de tela não foram validados. A reforma visual do Claude continua
independente, conforme .agents/CHARACTER_WORK.md; não atribuir suas mudanças
à implementação dos assets.
