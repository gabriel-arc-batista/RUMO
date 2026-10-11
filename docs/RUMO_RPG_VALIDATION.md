# Validação da integração RPG — RUMO 1.5.0

## Resultado

O frontend entregue por Claude foi integrado ao provedor real, padrão da aplicação. Prévia só com `RUMO_JOURNEY=preview`. Nenhum teste abriu ou alterou o banco pessoal.

- 98 testes unitários/de domínio: estudos, ciclos, revisões, backups, migração v1–v4, recompensas idempotentes, edição/exclusão, compras, desempenho observado, dificuldades e contratos visuais.
- `scripts/verify_rpg_gui.py`: Tk nativo, missão reduzida ajustável, 180 segundos líquidos com pausa sem XP, revisão atrasada, recordação declarada, dificuldade manual, masmorra, chefe registrado como simulado e compra/equipamento confirmado pela interface. Preferências de ocultação e páginas sem erros de callback.
- Fontes Inter e ícones carregados; Início/Jornada nos temas claro/escuro em 1366×768 e 1024×700. Capturas locais usam dados sintéticos.
- Importação de 10 mil fontes canônicas: 300 mil XP calculados em aproximadamente 1,53 segundo nesta máquina.
- Pacote Linux extraído em pasta temporária, sem variáveis do ambiente de build: janela visível, schema 4, histórico e recompensas inicialmente vazios, encerramento normal, sem ERROR nos logs. Não havia sockets de internet nos processos durante a inspeção; isso não representa auditoria de tráfego prolongada. RSS observado: 45 MiB.
- Avisos Bandit de SQL composto foram revisados contra identificadores constantes/permitidos; não se afirma ausência de alertas ou de bugs.

## Artefato e limites

`dist/RUMO-linux-portatil.tar.gz`, com avisos de licenças Python, Tcl/Tk, fontes/ícones e tzdata; checksum em `dist/SHA256SUMS-linux.txt`. Build com Python 3.14 e Tk 8.6/Xft.

No Linux/X11, XIM externo está desativado para evitar espera indefinida na conexão com IBus. Métodos de entrada externos precisam de validação específica. A abertura animada é assíncrona. Leitor de tela externo, assinatura, VM isolada e pacote Windows 1.5.0 não foram validados nesta execução. As verificações Linux não substituem as de Windows.

## Uso

Em Jornada, use Dificuldades/Revanche, Desafios, Nome do personagem e Importar XP do histórico. Missões usam o cronômetro e o histórico existentes. XP é esforço: um por minuto líquido completo, cinco por revisão/desafio concluído; moedas são uma por dez XP de cada sessão. Acertos não multiplicam XP. Importação histórica exige prévia e confirmação, e equipamentos são apenas decorativos.
