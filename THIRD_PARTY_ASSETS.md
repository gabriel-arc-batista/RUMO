# Assets do personagem

O RUMO usa **Portrait Creator — example_assets**, de **N. Erebus**,
[fonte original](https://n-erebus.itch.io/portrait-creator), sob **CC0-1.0**.
Arquivos baixados e licença integral: `assets/character/sources/`.
Catálogo: `assets/character/look/catalog.json`. Uso inteiramente offline.
A licença dos assets é independente da licença do código.

## Pesquisa e comparação (11/10/2026)

| Conjunto / fonte do autor | Conteúdo e estilo | Personalização / transparência | Redistribuição, custo e download | Decisão |
| --- | --- | --- | --- | --- |
| [N. Erebus — Portrait Creator](https://n-erebus.itch.io/portrait-creator) | Retratos ilustrados, PNGs originais 1024×1024 | 6 rostos compartilháveis, 11 cabelos, 6 olhos, 7 sobrancelhas, 5 íris, 7 narizes, 11 bocas e um bigode. RGBA, camadas traseiras para 6 cabelos; sem categorias masculina/feminina explícitas | CC0 declarada pelo autor; gratuito, ZIP example_assets obtido sem pagamento | Escolhido: camadas reais e recoloração autorizada por multiply |
| [Kenney — Modular Character Pack](https://opengameart.org/content/modular-character-pack) | Personagens vetoriais planos, 425 PNGs; seis spritesheets e vetores | Corpo e peças separadas; ZIP baixado e inspecionado. Sem o detalhamento facial do escolhido | CC0, página publicada pelo autor; ZIP gratuito de 1,8 MB | Estilo mais cartunesco e foco em corpo. Arquivo de comparação mantido localmente em validation/character-research |
| [Universal LPC](https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator) | Pixel art modular de corpo inteiro, bases humanas masculina/feminina e equipamentos | PNGs e grade de animações, peças compatíveis com bases específicas; créditos individuais | Gratuito, arquivos via GitHub; CC0/CC-BY/CC-BY-SA/OGA-BY/GPL conforme peça. Requer auditoria e atribuição individual | Bom para corpo, mas menor detalhe facial e maior escopo de integração. Não incorporado |

## Categorias implementadas e limites

Duas bases de aparência são presets dos rostos 1 e 4, compartilhando as opções
sem restringir penteados ou pelos faciais por gênero. O pacote não identifica
sexo anatômico e não inclui corpos; não anunciar duas bases corporais.
Seis rostos, onze penteados mais sem cabelo, oito tons de pele, oito cores de
cabelo, seis olhos, cinco íris, sete cores de íris, sete sobrancelhas, sete
narizes, onze bocas, sem pelos faciais ou bigode. Sobrancelhas e olhos são
realmente independentes. Cores são aplicadas em camadas separadas no build.

Não há barba completa, óculos, tranças nem opção crespa comprovada. IDs antigos
`crespo`, `trancas`, `rabo` e `coque` permanecem aceitos para backup, mas os
rótulos agora descrevem os PNGs efetivos; o mapeamento está no preparador.
Orelhas fazem parte do rosto: a preferência legada é preservada, sem controle
enganoso. Não há cílios separados; os olhos usam o contorno original.

A mesma aparência é usada no painel da barra lateral (inclusive no Início),
na Jornada e nos diálogos existentes (via Portrait/CharacterView). Não existe
uma tela separada de Arena nesta versão do projeto.
O painel que antes mostrava corpo usa agora o retrato: roupas, armaduras, armas
e montarias mantêm inventário, preços, aquisição e equipagem, mas não recebem
uma representação visual inventada nem overlays corporais incompatíveis.
A arte corporal antiga não é reaplicada ao novo rosto.

## RAM e preparação

Sem Pillow no runtime, serviço, rede ou animação do personagem. Tk carrega PNGs
locais. Somente a categoria aberta mantém miniaturas; cache LRU de 24 imagens
compartilhado, com referências adicionais apenas para widgets visíveis.
Um PNG RGBA 264×264 ocupa aproximadamente 272 KiB de pixels; 24 desses dão
aproximadamente 6,4 MiB, além de buffers Tk, imagens visíveis e demais telas.
Esse cálculo não é uma medição de RAM total do aplicativo.

`python scripts/prepare_avatar.py` recompõe offline usando Pillow de build;
originais são preservados. O manifesto registra origem, licença, SHA-256,
compatibilidade, ordem, categoria e transformação de cada peça.
