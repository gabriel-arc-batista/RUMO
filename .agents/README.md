# Contexto para continuidade

Versão preparada: **1.0.0**, em 11/10/2026. Python 3.13, Tk 8.6, SQLite esquema 5. A versão anterior foi validada em Windows 11 x64; esta integração é verificada em Linux com testes nativos e dados temporários, e o workflow de release valida os pacotes Windows. Consulte a execução da release para o resultado. O produto atende concursos e objetivos de aprendizagem em geral. Os planos BACEN 2024 incluídos são referências iniciais, não uma restrição do aplicativo.

## Produto e decisões aceitas

Aplicativo sem conta, assinatura, servidor ou serviços em segundo plano. Dados ficam em `%LOCALAPPDATA%/RUMO`; binários instalados em `%LOCALAPPDATA%/Programs/RUMO`. `RUMO_DATA` permite uma pasta alternativa para testes. Não é segredo e não carrega `.env`.

Oito temas nomeados (original: Norte Dourado, preto/grafite e dourado; claro padrão: Aurora), Inter para leitura e Poppins só na marca/personagem, ícones Lucide; tudo carregado privadamente. Motivo da marca: navegação (rosa dos ventos, viajante). Referências e tokens em `docs/RUMO_DESIGN.md` (substituem Estudei/Linear/MD3). Uma ação dourada por tela; frase diária em uma linha no cabeçalho do Início; relógio em pílula fixa no cabeçalho; RPG com selo DEMONSTRAÇÃO enquanto vier da prévia. Animações de entrada, hover e foco são finitas e respeitam a preferência de reduzir movimento.

Cada subassunto tem conclusão verde e observações salvas sem reconstruir a lista. Nomes visíveis não mostram IDs. Relógio com busca, presets e progresso; pausas não contam. Desafios têm três níveis e permitem escolher a meta principal, lembrada no relógio. Preferências em quatro abas. Ciclo guiado usa 25 minutos por matéria e o próximo assunto pendente na ordem de aprendizagem; não é uma agenda diária rígida.

São 287 itens originais, mais 1.090 desdobramentos: 565 folhas em TI e 525 em Economia e Finanças. Original e retificado estão disponíveis offline. O guia é curadoria pedagógica, não texto oficial nem garantia de exaustividade. 150 frases com fontes; não inventar atribuições.

A revisão de segurança 1.4.1 separou backups, protegeu retenção, CSV e links, reforçou limites e relações e atualizou Pillow de desenvolvimento. Consulte `SECURITY.md` e o relatório público `SECURITY_REVIEW.md`.

## Leia em seguida

- `ARCHITECTURE.md`: módulos e contratos.
- `TESTING.md`: testes e limites de validação.
- `SECURITY.md`: superfície de ataque e invariantes.
- `RELEASE.md`: conta pessoal, build e publicação.
- `ROADMAP.md`: expansão sem regressões.

## Marca e compatibilidade 1.4.3

Todos os identificadores atuais usam RUMO: executável, instalação, ícones, AppUserModelID, variável RUMO_DATA e formato exportado. Preserve o AppId UUID do instalador para manter a identidade da atualização. O repositório pessoal é RUMO. A primeira abertura identifica bases anteriores por esquema, copia com a API de backup SQLite sob bloqueio e preserva a origem. Se houver várias bases candidatas, recusa escolher uma silenciosamente. RUMO_DATA evita a descoberta automática. Backups JSON v1/v2/v3/v4/v5 são aceitos por estrutura e validação integral, sem depender do antigo rótulo de marca.

## Apresentação e licença

O README apresenta o uso geral e começa pela criação de um plano próprio. Evite personalizar a documentação pública para o concurso do autor. As fontes dos planos incluídos ficam em `FONTES.md`. Repositório privado e código próprio sem licença definida: não anunciar como open source nem mudar visibilidade/licença sem instrução explícita do proprietário.

## RPG 1.5.0

Perfil real é o padrão. `RUMO_JOURNEY=preview` é uma opção explícita de demonstração em memória. Missões, dificuldades/revanche, encontros de revisões, masmorras/chefes, moedas e inventário usam `Store.rpg`; consulte `docs/RUMO_BACKEND_CONTRACT.md`. Novas preferências `rpg_show_character`, `rpg_effects`, `rpg_story`, `rpg_reward_notifications` mantêm as ferramentas de estudo acessíveis. Não conceder XP retroativo sem a prévia opt-in.

## Equipamentos e classes 1.0.0

`rpg_progression.py` define 25 equipamentos de início/evolução e seis caminhos paralelos; os 13 IDs e preços antigos permanecem. Recompensas são gratuitas, idempotentes e persistem após correções. Novos personagens equipam apenas trapos/arma velha; itens conquistados não substituem escolhas automaticamente. Atalhos preparam fluxos existentes sem gravar estudos no clique. Esquema 5 amplia slots do inventário com migração transacional e cópia `pre-equipment` de bases v4. Backups v1–v5 aceitos. Arte original em camadas por `scripts/prepare_rpg_equipment.py`, chamada depois de `prepare_character.py`. A janela modal só captura foco quando visível; no Linux não usar fade de opacidade em Toplevels. Veja `docs/RUMO_EQUIPMENT.md`.
