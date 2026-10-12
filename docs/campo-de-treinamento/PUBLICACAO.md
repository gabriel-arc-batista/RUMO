# Publicar aulas: repositório de conteúdo, catálogo e PDFs

Nada foi publicado ainda e nenhuma URL abaixo existe. Este é o procedimento para quando houver aulas revisadas.

## Estrutura do repositório de conteúdo (separado do aplicativo)

```
rumo-conteudo/
  catalogo-fonte.json        # matérias, assuntos e aulas; recursos sem bytes/sha256
  aulas/<id-da-aula>/aula.md # fonte editável (texto, exemplos, fontes, checklist)
  aulas/<id-da-aula>/img/    # imagens licenciadas ou próprias
  pdf/<arquivo>.pdf          # PDF renderizado e inspecionado
  cobertura/                 # matriz item de edital ↔ aula/versão (quando auditada)
  LICENSE-CONTEUDO           # licença escolhida pelo autor (ex.: CC BY-SA 4.0)
  publicar/                  # gerado pelo script; não editar à mão
```

Modelo pronto em `repositorio-de-conteudo/`. Use como IDs de matéria os IDs das famílias do planejamento (por exemplo, `dados.sql`). Assim, aula e planejamento se encontram, e a aula publicada substitui a planejada de mesmo ID.

## Regras do catálogo

As mesmas que o app aplica (`training_catalog.py`):

- `publicada` exige `review.status = "aprovada"`, um `reviewer` nomeado e `reviewed_at`.
- Aula planejada, em rascunho ou em revisão não tem `resource`, ou seja, nenhuma URL fictícia.
- O recurso precisa de HTTPS num host aprovado, `media_type` PDF, `bytes`, `sha256` e licença.
- IDs são estáveis e únicos. Mudar o título não muda o ID. Uma nova edição do PDF muda `resource.version` (e `content_version`), nunca o ID.

## Passo a passo com GitHub Pages + Releases

1. Crie o repositório público de conteúdo (por exemplo, `rumo-conteudo`) e ative o GitHub Pages (Settings → Pages → branch `main`, pasta `/docs` ou raiz).
2. Para cada nova versão, crie uma tag imutável (por exemplo, `aulas-2026.10.1`) e uma release com esse nome.
3. Gere o catálogo apontando para o endereço de download da release:
   `python scripts/build_training_catalog.py ../rumo-conteudo https://github.com/<dono>/rumo-conteudo/releases/download/aulas-2026.10.1/ objects.githubusercontent.com release-assets.githubusercontent.com`
4. Anexe à release os PDFs de `publicar/` (sem renomear) e copie `publicar/catalog.json` para a pasta do Pages. Não substitua PDFs de uma release já publicada; faça outra.
5. No RUMO: **Conteúdo → Configurar fonte → Endereço remoto** com `https://<dono>.github.io/rumo-conteudo/catalog.json`, marcando "Permitir os hosts de download do GitHub Releases". Depois, **Atualizar catálogo**.

## Limites consultados em 11/10/2026 (documentação oficial)

- GitHub Pages: site publicado de até 1 GB; limite flexível de banda de 100 GB por mês; 10 builds por hora; não é hospedagem para negócio comercial. https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Releases: até 1000 arquivos por release; cada arquivo menor que 2 GiB; "sem limite de tamanho total nem de banda". https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases

Isso é suficiente para começar, mas não é garantia de gratuidade permanente. Se precisar trocar de hospedagem, mude só a URL de `resource` e os hosts aprovados; os IDs das aulas, as notas e o progresso não mudam.

## Segurança

O SHA-256 garante que o arquivo baixado é o descrito no catálogo, mas não autentica quem editou o catálogo. Assinar o catálogo é uma evolução possível. O app nunca executa conteúdo do catálogo, só aceita PDFs, recusa redirecionamentos para hosts não aprovados e não envia dados pessoais para lugar nenhum.
