"""150 sourced excerpts, translated specifically for this offline application.

Historic attributions are identified instead of presenting reported sayings as
audio transcripts. Source passages, not internet motivational quote lists.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUOTES = []


def group(author, url, text, kind="Tradução própria de trecho da obra"):
    for line in text.strip().splitlines():
        reference, quote = line.split("|", 1)
        QUOTES.append(
            dict(
                author=author,
                source=url,
                reference=reference.strip(),
                text=quote.strip(),
                kind=kind,
            )
        )


group(
    "Jesus — segundo os Evangelhos",
    "https://www.gutenberg.org/ebooks/10",
    """
Mateus 5:9 | Felizes os que promovem a paz.
Mateus 5:14 | Vocês são a luz do mundo.
Mateus 5:16 | Que a luz de vocês brilhe diante das pessoas.
Mateus 6:21 | Onde estiver seu tesouro, ali estará também seu coração.
Mateus 6:27 | Quem, por se preocupar, pode aumentar a própria estatura?
Mateus 6:34 | Não se preocupem com o amanhã.
Mateus 7:7 | Peçam, e lhes será dado; busquem, e encontrarão.
Mateus 7:12 | Façam aos outros o que desejam que façam a vocês.
Mateus 7:24 | Quem ouve estas palavras e as pratica é como um homem prudente.
Mateus 11:28 | Venham a mim, todos os que estão cansados e sobrecarregados.
Mateus 11:29 | Aprendam de mim, pois sou manso e humilde de coração.
Mateus 22:39 | Ame o seu próximo como a si mesmo.
Mateus 26:41 | O espírito está disposto, mas a carne é fraca.
Marcos 9:23 | Tudo é possível para aquele que crê.
Lucas 6:36 | Sejam misericordiosos, como seu Pai é misericordioso.
Lucas 6:45 | A boca fala daquilo de que o coração está cheio.
Lucas 12:15 | A vida de uma pessoa não consiste na abundância de seus bens.
Lucas 16:10 | Quem é fiel no pouco também é fiel no muito.
João 8:32 | Conhecerão a verdade, e a verdade os libertará.
João 13:34 | Amem uns aos outros.
""",
    "Tradução própria; fala atribuída a Jesus no texto bíblico",
)
group(
    "Salomão — tradição bíblica",
    "https://www.gutenberg.org/ebooks/10",
    """
Provérbios 1:5 | Que o sábio ouça e aumente seu aprendizado.
Provérbios 3:13 | Feliz quem encontra a sabedoria e alcança entendimento.
Provérbios 4:7 | Adquira sabedoria; com tudo que adquirir, adquira entendimento.
Provérbios 4:23 | Acima de tudo, guarde seu coração.
Provérbios 9:9 | Instrua o sábio, e ele se tornará ainda mais sábio.
Provérbios 10:4 | A mão diligente traz riqueza.
Provérbios 12:1 | Quem ama a disciplina ama o conhecimento.
Provérbios 13:20 | Quem anda com os sábios se torna sábio.
Provérbios 14:29 | Quem demora a se irar tem grande entendimento.
Provérbios 15:1 | Uma resposta branda afasta a ira.
Provérbios 16:16 | Quanto melhor adquirir sabedoria do que ouro!
Provérbios 17:22 | Um coração alegre é um bom remédio.
Provérbios 18:13 | Responder antes de ouvir é insensatez e vergonha.
Provérbios 21:5 | Os planos de quem é diligente conduzem à abundância.
Eclesiastes 3:1 | Há um tempo para tudo.
""",
    "Tradução própria; atribuição tradicional, autoria histórica não demonstrada",
)
group(
    "Davi — tradição dos Salmos",
    "https://www.gutenberg.org/ebooks/10",
    """
Salmo 23:1 | O Senhor é meu pastor; nada me faltará.
Salmo 27:14 | Espere no Senhor; seja forte e tenha coragem.
Salmo 34:14 | Afaste-se do mal e faça o bem; busque a paz e persiga-a.
Salmo 37:5 | Entregue seu caminho ao Senhor e confie nele.
Salmo 51:10 | Crie em mim um coração puro.
""",
    "Tradução própria; Salmo tradicionalmente atribuído a Davi",
)
group(
    "Epicteto",
    "https://www.gutenberg.org/ebooks/45109",
    """
Manual, 1 | Algumas coisas dependem de nós; outras não.
Manual, 2 | Lembre que o desejo promete alcançar aquilo que deseja.
Manual, 3 | Em tudo que você ama, lembre qual é sua natureza.
Manual, 4 | Antes de agir, recorde a natureza da atividade.
Manual, 5 | As pessoas se perturbam por suas opiniões sobre as coisas.
Manual, 6 | Não se orgulhe de uma excelência que não é sua.
Manual, 8 | Deseje que as coisas aconteçam como acontecem.
Manual, 9 | A doença é um impedimento para o corpo, não para a vontade.
Manual, 10 | A cada acontecimento, pergunte que capacidade possui para enfrentá-lo.
Manual, 11 | Nunca diga que perdeu algo; diga que o devolveu.
Manual, 13 | Se deseja progredir, aceite parecer ignorante nas coisas externas.
Manual, 15 | Lembre-se de se comportar na vida como em um banquete.
Manual, 17 | Você é um ator em uma peça cujo papel foi escolhido por outro.
Manual, 18 | Aconteça o que acontecer, cabe a mim tirar disso proveito.
Manual, 19 | Pode ser invencível se não entrar em disputas fora de seu controle.
Manual, 20 | Quando alguém o provoca, sua opinião é o que o perturba.
Manual, 23 | Se se volta ao exterior para agradar alguém, perdeu seu propósito.
Manual, 29 | Em toda ação, examine o que vem antes e depois.
Manual, 33 | Seja geralmente silencioso; diga apenas o necessário.
Manual, 46 | Não fale sobre como se deve comer; coma como se deve.
""",
)
group(
    "Confúcio — Analectos",
    "https://www.gutenberg.org/ebooks/3330",
    """
Analectos 1.1 | Aprender e praticar o que se aprendeu não é uma alegria?
Analectos 1.3 | Palavras hábeis e modos insinuantes raramente acompanham a virtude.
Analectos 1.6 | Se lhe restar energia, aplique-a ao estudo.
Analectos 1.8 | Ao cometer um erro, não tenha medo de corrigi-lo.
Analectos 1.14 | Quem ama aprender não busca conforto em sua morada.
Analectos 2.11 | Rever o antigo e conhecer o novo permite ser mestre.
Analectos 2.13 | Primeiro pratique o que diz; depois fale de acordo com a prática.
Analectos 2.15 | Aprender sem pensar é trabalho perdido; pensar sem aprender é perigoso.
Analectos 2.17 | Saber o que sabe e reconhecer o que não sabe: isso é conhecimento.
Analectos 4.17 | Ao ver alguém digno, pense em se tornar semelhante.
Analectos 4.24 | A pessoa nobre é modesta no falar e diligente no agir.
Analectos 6.18 | Quando substância e refinamento se equilibram, surge a pessoa nobre.
Analectos 6.20 | Quem conhece não se iguala a quem ama; quem ama não se iguala a quem se alegra.
Analectos 7.2 | Guardar o conhecimento em silêncio e aprender sem se cansar.
Analectos 7.8 | Não esclareço quem não está empenhado em aprender.
Analectos 7.22 | Entre três pessoas caminhando, encontrarei alguém que me ensine.
Analectos 9.17 | Tudo passa como este rio, sem cessar de dia ou de noite.
Analectos 12.2 | Não imponha aos outros o que não deseja para si.
Analectos 15.30 | Ter erros e não corrigi-los: isso é realmente um erro.
Analectos 15.31 | Passei o dia sem comer e a noite sem dormir, pensando; estudar foi melhor.
""",
)
group(
    "Laozi — tradição do Tao Te Ching",
    "https://www.gutenberg.org/ebooks/216",
    """
Tao Te Ching 8 | A maior excelência é como a água: beneficia tudo sem disputar.
Tao Te Ching 9 | É melhor deixar o vaso incompleto que tentar carregá-lo cheio.
Tao Te Ching 11 | É o espaço vazio que torna o recipiente útil.
Tao Te Ching 15 | Deixe a água turva repousar, e ela gradualmente ficará clara.
Tao Te Ching 22 | Quem se curva permanece inteiro.
Tao Te Ching 23 | Falar pouco está de acordo com a natureza.
Tao Te Ching 24 | Quem fica na ponta dos pés não se mantém firme.
Tao Te Ching 27 | Quem sabe caminhar não deixa rastros.
Tao Te Ching 33a | Conhecer os outros é inteligência; conhecer a si mesmo é sabedoria.
Tao Te Ching 33b | Vencer os outros é força; vencer a si mesmo é poder.
Tao Te Ching 33c | Quem sabe estar satisfeito é rico.
Tao Te Ching 44 | Quem sabe quando parar não corre perigo.
Tao Te Ching 46 | Não há desgraça maior que não saber se contentar.
Tao Te Ching 48 | Na busca do aprendizado, todos os dias algo é acrescentado.
Tao Te Ching 63 | Trate o difícil enquanto ainda é fácil.
Tao Te Ching 64a | Uma jornada de mil li começa debaixo dos pés.
Tao Te Ching 64b | Uma árvore enorme cresce de um broto minúsculo.
Tao Te Ching 67 | Tenho três tesouros: compaixão, economia e humildade.
Tao Te Ching 78 | Nada é mais suave que a água, mas ela vence o que é duro.
Tao Te Ching 81 | Palavras verdadeiras não são necessariamente belas.
""",
)
group(
    "Benjamin Franklin",
    "https://www.gutenberg.org/ebooks/43855",
    """
O caminho da riqueza: tempo | Se ama a vida, não desperdice tempo: é disso que ela é feita.
O caminho da riqueza: adiamento | Nunca deixe para amanhã o que pode fazer hoje.
O caminho da riqueza: dificuldades | A diligência supera as dificuldades; a preguiça as torna maiores.
O caminho da riqueza: paciência | A gota constante desgasta a pedra.
O caminho da riqueza: iniciativa | Quem vive de esperança morrerá em jejum.
O caminho da riqueza: vigilância | Um gato com luvas não apanha ratos.
O caminho da riqueza: movimento | A chave usada sempre brilha.
O caminho da riqueza: tempo perdido | O tempo perdido nunca é encontrado de novo.
O caminho da riqueza: dívida | Os credores têm melhor memória que os devedores.
O caminho da riqueza: barco | Um pequeno vazamento afunda um grande navio.
O caminho da riqueza: necessidades | Compre o desnecessário e logo venderá o necessário.
O caminho da riqueza: hábito | É mais fácil suprimir o primeiro desejo que satisfazer todos os seguintes.
O caminho da riqueza: trabalho | A preguiça viaja tão devagar que a pobreza logo a alcança.
O caminho da riqueza: direção | Conduza seu negócio; não deixe que ele o conduza.
O caminho da riqueza: regularidade | Golpes pequenos derrubam grandes carvalhos.
O caminho da riqueza: cuidado | A falta de cuidado nos causa mais dano que a falta de conhecimento.
O caminho da riqueza: organização | Uma pequena negligência pode causar um grande prejuízo.
O caminho da riqueza: ação | Empregue bem seu tempo se deseja obter lazer.
O caminho da riqueza: dinheiro | Se quer conhecer o valor do dinheiro, tente pedir emprestado.
O caminho da riqueza: vontade | A diligência é a mãe da boa sorte.
""",
)
group(
    "Marco Aurélio",
    "https://classics.mit.edu/Antoninus/meditations.html",
    """
Meditações 4.3 | Em nenhum lugar alguém encontra refúgio mais tranquilo que na própria alma.
Meditações 4.17 | Não viva como se fosse viver dez mil anos.
Meditações 5.1 | Ao amanhecer, lembre: levanto para fazer o trabalho de um ser humano.
Meditações 5.20 | O que impede a ação faz avançar a ação.
Meditações 6.6 | A melhor vingança é não se tornar semelhante a quem errou.
Meditações 7.7 | Não se envergonhe de receber ajuda.
Meditações 8.36 | Não deixe que a visão de toda sua vida o perturbe.
Meditações 9.6 | Basta que sua opinião presente seja fundada no entendimento.
Meditações 10.16 | Não discuta mais como deve ser uma pessoa boa. Seja uma.
Meditações 12.17 | Se não é certo, não faça; se não é verdadeiro, não diga.
""",
)
group(
    "Francis Bacon",
    "https://www.gutenberg.org/ebooks/575",
    """
Dos estudos: leitura | Ler torna a pessoa completa; conversar a prepara; escrever a torna precisa.
Dos estudos: livros | Alguns livros são para provar, outros para engolir, e poucos para mastigar e digerir.
Dos estudos: aplicação | Os estudos servem ao prazer, ao ornamento e à capacidade.
Dos estudos: experiência | Os estudos aperfeiçoam a natureza e são aperfeiçoados pela experiência.
Dos estudos: julgamento | Leia para pesar e considerar, não apenas para contradizer.
Dos estudos: formação | A história torna as pessoas sábias; a matemática as torna sutis.
""",
)
group(
    "Charles Darwin",
    "https://www.gutenberg.org/ebooks/1228",
    """
A origem das espécies, introdução | Um resultado justo só pode vir de expor e pesar fatos e argumentos dos dois lados.
A origem das espécies, capítulo IV | A seleção natural não pode agir senão pela preservação e acumulação de pequenas modificações herdadas.
A origem das espécies, capítulo VI | A natureza não dá saltos.
A origem das espécies, capítulo XIV | Há grandeza nessa visão da vida.
""",
)
group(
    "Abraham Lincoln",
    "https://www.loc.gov/exhibits/lincoln/healing-the-nations-wounds.html",
    """
Segundo discurso de posse, 1865: disposição | Sem malícia contra ninguém, com caridade para todos.
Segundo discurso de posse, 1865: tarefa | Esforcemo-nos por terminar o trabalho em que estamos.
Segundo discurso de posse, 1865: cuidado | Cuidemos de quem suportou a batalha, de sua viúva e de seu órfão.
Segundo discurso de posse, 1865: paz | Façamos tudo que possa alcançar e preservar uma paz justa e duradoura.
""",
)
group(
    "Júlio César — relato de Plutarco",
    "https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.03.0078%3Atext%3DCaes.",
    """
Vida de César, 50 | Vim, vi, venci.
""",
    "Tradução própria de fala relatada por Plutarco",
)
group(
    "Alexandre, o Grande — relato de Plutarco",
    "https://atlas.perseus.tufts.edu/library/passage/urn%3Acts%3AgreekLit%3Atlg0007.tlg087.perseus-eng4%3A1.9-1.10/",
    """
Sobre a fortuna ou virtude de Alexandre, I.10 | Se não fosse Alexandre, eu seria Diógenes.
""",
    "Tradução própria de fala relatada por Plutarco",
)
group(
    "Albert Einstein",
    "https://assets.press.princeton.edu/chapters/s10176.pdf",
    """
Entrevista de 1929, citada em The Ultimate Quotable Einstein | A imaginação é mais importante que o conhecimento.
Carta a Carl Seelig, 1952, citada em The Ultimate Quotable Einstein | Não tenho talento especial. Sou apenas apaixonadamente curioso.
""",
)
group(
    "J. Robert Oppenheimer",
    "https://www.atomicarchive.com/media/videos/oppenheimer.html",
    """
Entrevista à NBC, 1965 | Sabíamos que o mundo não seria o mesmo.
""",
)
group(
    "Marie Curie",
    "https://www.nobelprize.org/prizes/chemistry/1911/marie-curie/lecture/",
    """
Conferência Nobel, 1911 | A radioatividade é uma propriedade atômica da matéria.
""",
)


def build():
    assert len(QUOTES) == 150, len(QUOTES)
    assert len({q["text"] for q in QUOTES}) == 150
    # Interleave traditions/authors; avoid a month-long run from the same book.
    groups = {}
    for q in QUOTES:
        groups.setdefault(q["author"], []).append(q)
    output = []
    while any(groups.values()):
        for quotes in groups.values():
            if quotes:
                output.append(quotes.pop(0))
    (ROOT / "assets/quotes.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("150 distinct sourced excerpts prepared.")


if __name__ == "__main__":
    build()
