# Componentes

O executável inclui Python (PSF License), Tcl/Tk (licenças permissivas próprias), SQLite (domínio público), dados IANA/tzdata e o bootloader do PyInstaller (GPL com exceção para distribuição dos programas empacotados).

- Python: https://docs.python.org/3/license.html
- Tcl/Tk: https://www.tcl.tk/software/tcltk/license.html
- SQLite: https://sqlite.org/copyright.html
- tzdata/IANA: https://www.iana.org/time-zones
- PyInstaller: https://pyinstaller.org/en/stable/license.html
- Poppins: fonte original distribuída sob SIL Open Font License 1.1. Fonte e licença incluídas em `assets/fonts`; carregamento privado por processo, sem instalar fontes no Windows. Origem: https://github.com/google/fonts/tree/main/ofl/poppins

Pillow, psutil e pypdf são ferramentas de teste/preparação e estão excluídos do executável. Inno Setup é ferramenta de empacotamento. O edital oficial incluído foi publicado pelo Banco Central do Brasil; a origem e o hash constam no arquivo estruturado.

- Inter 4.1: SIL Open Font License 1.1, carregamento privado no aplicativo. Arquivos e licença em `assets/fonts`. Origem: https://github.com/rsms/inter/releases/tag/v4.1
- Lucide 0.460.0 (`lucide-static`): ícones sob licença ISC (partes MIT do Feather). Subconjunto de 76 glifos em `assets/fonts/RUMO-Icons.ttf`, licença em `assets/fonts/LUCIDE-LICENSE.txt`, carregamento privado. Origem: https://lucide.dev — preparação reproduzível em `scripts/prepare_icons.py`.
- Personagem, aparências e equipamentos (`assets/character/`): arte original do projeto, gerada por código em `scripts/prepare_avatar.py`, `scripts/prepare_character.py` e `scripts/prepare_rpg_equipment.py`; sem imagens de terceiros.
- pypdfium2 5.14.0 e PDFium (leitor do Campo de Treinamento): pypdfium2 sob Apache-2.0 ou BSD-3-Clause; PDFium sob BSD-3-Clause e Apache-2.0, com componentes de terceiros listados no pacote. Origem: https://github.com/pypdfium2-team/pypdfium2 e https://pdfium.googlesource.com/pdfium/ — renderiza páginas localmente; nenhum PDF é enviado a serviços externos.
- Campo de Treinamento (`assets/training/curriculo.json`, `docs/campo-de-treinamento/`): planejamento editorial do pacote do projeto e itens extraídos automaticamente dos editais oficiais citados em cada registro (textos normativos públicos), pendentes de conferência. Nenhuma aula ou PDF de terceiros é distribuído.
- Miniaturas do inventário (`assets/character/items/`): recortes da arte original do projeto (`scripts/prepare_item_thumbs.py`).
