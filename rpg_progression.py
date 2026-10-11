"""Deterministic equipment rewards and parallel study paths, entirely offline."""

PATHS = {
    "guardiao": dict(
        name="Paladino",
        metric="reviews",
        targets=(2, 6, 15),
        purpose="Voltar ao conteúdo em revisões, mesmo atrasadas.",
        action="review",
    ),
    "duelista": dict(
        name="Guerreiro",
        metric="answered",
        targets=(10, 40, 100),
        purpose="Praticar questões do seu material; erros também contam como prática.",
        action="practice",
    ),
    "arcanista": dict(
        name="Mago",
        metric="recall",
        targets=(3, 7, 15),
        purpose="Tentar lembrar antes de consultar. Qualquer autoavaliação conta.",
        action="recall",
    ),
    "cartografo": dict(
        name="Cartógrafo",
        metric="topics",
        targets=(2, 5, 10),
        purpose="Explorar assuntos do plano com estudos registrados.",
        action="route",
    ),
    "ladino": dict(
        name="Ladino",
        metric="difficulties",
        targets=(1, 3, 6),
        purpose="Investigar dificuldades e trabalhá-las em revanches reais.",
        action="revenge",
    ),
    "erudito": dict(
        name="Erudito",
        metric="notes",
        targets=(2, 5, 10),
        purpose="Escrever dúvidas, exemplos ou explicações em assuntos estudados.",
        action="notes",
    ),
}
RANKS = ("Iniciante", "Aprendiz", "Adepto", "Veterano")

# Existing IDs, prices and positions remain compatible with v4 inventory.
LEGACY_PURPOSES = {
    "viajante": ("Retomar seu próximo passo.", "resume"),
    "explorador": ("Preparar uma rota entre estudo e revisão.", "route"),
    "cartografo": ("Organizar os próximos passos do seu plano.", "route"),
    "grafite": ("Abrir uma missão curta, com foco no essencial.", "small"),
    "dourada": ("Preparar seu próximo período de foco.", "focus"),
    "livro": ("Revisar uma ideia antes de consultar o material.", "recall"),
    "bussola": ("Consultar uma rota de atividades reais.", "route"),
    "farol": ("Voltar a uma dificuldade registrada por você.", "revenge"),
    "backpack": ("Levar a anotação de onde parou para a próxima missão.", "resume"),
    "scarf": ("Acolher dias difíceis com uma missão de cinco minutos.", "small"),
    "compass": ("Escolher o próximo estudo ou revisão na rota.", "route"),
    "lantern": ("Iluminar uma revisão pendente, sem penalidade por atraso.", "review"),
    "spyglass": ("Olhar de perto uma dificuldade e preparar uma revanche.", "revenge"),
}


def item(name, slot, level, purpose, action, *, kind, rule=None, starter=False):
    return dict(
        name=name,
        slot=slot,
        level=level,
        price=0,
        preview=purpose,
        purpose=purpose,
        action=action,
        kind=kind,
        acquisition="reward",
        rule=rule,
        starter=starter,
    )


GEAR = {
    "rags": item(
        "Trapos de aprendiz",
        "roupa",
        1,
        "Começar pequeno: preparar cinco minutos de estudo.",
        "small",
        kind="Roupas",
        starter=True,
    ),
    "rusty_sword": item(
        "Espada enferrujada",
        "arma",
        1,
        "Primeiros duelos: abrir prática de questões do seu material.",
        "practice",
        kind="Armas",
        starter=True,
    ),
    "travel_tunic": item(
        "Túnica de viagem",
        "roupa",
        2,
        "Preparar um período de foco de quinze minutos.",
        "focus",
        kind="Roupas",
    ),
    "training_sword": item(
        "Espada de treino",
        "arma",
        2,
        "Praticar dez minutos de questões sem exigir uma nota mínima.",
        "practice",
        kind="Armas",
    ),
    "walking_boots": item(
        "Botas de caminhada",
        "pés",
        2,
        "Retomar a missão e a anotação de onde você parou.",
        "resume",
        kind="Roupas",
    ),
    "leather_armor": item(
        "Armadura de couro",
        "peito",
        3,
        "Proteger o aprendizado com uma revisão pendente.",
        "review",
        kind="Armaduras",
        rule=("reviews", 2),
    ),
    "memory_shield": item(
        "Escudo das memórias",
        "escudo",
        3,
        "Transformar uma dificuldade em uma revanche de estudo.",
        "revenge",
        kind="Armaduras",
        rule=("reviews", 2),
    ),
    "chain_armor": item(
        "Cota do Paladino",
        "peito",
        5,
        "Reforçar a revisão dos conteúdos que já encontrou.",
        "review",
        kind="Armaduras",
        rule=("reviews", 6),
    ),
    "plate_armor": item(
        "Armadura do bastião",
        "peito",
        7,
        "Preparar uma revanche a partir dos seus erros descritos.",
        "revenge",
        kind="Armaduras",
        rule=("reviews", 15),
    ),
    "memory_helm": item(
        "Elmo da recordação",
        "cabeça",
        4,
        "Lembrar antes de ler e registrar sua percepção ao final.",
        "recall",
        kind="Armaduras",
        rule=("recall", 3),
    ),
    "steel_sword": item(
        "Espada de aço",
        "arma",
        4,
        "Praticar questões e conferir os erros no seu material.",
        "practice",
        kind="Armas",
        rule=("answered", 10),
    ),
    "precision_bow": item(
        "Arco da prática",
        "arma",
        5,
        "Preparar uma masmorra com assuntos já estudados.",
        "challenge",
        kind="Armas",
        rule=("answered", 40),
    ),
    "veteran_blade": item(
        "Lâmina do Guerreiro",
        "arma",
        7,
        "Preparar um chefe como simulado real do seu material.",
        "boss",
        kind="Armas",
        rule=("answered", 100),
    ),
    "arcane_robe": item(
        "Veste do Mago",
        "roupa",
        3,
        "Preparar uma revisão com tentativa de recordação.",
        "recall",
        kind="Roupas",
        rule=("recall", 3),
    ),
    "wood_staff": item(
        "Cajado de madeira",
        "arma",
        3,
        "Tentar explicar uma ideia de memória antes de reler.",
        "recall",
        kind="Armas",
        rule=("recall", 3),
    ),
    "star_robe": item(
        "Manto das constelações",
        "roupa",
        6,
        "Conectar tentativas de lembrança a revisões reais.",
        "recall",
        kind="Roupas",
        rule=("recall", 7),
    ),
    "crystal_staff": item(
        "Cajado das lembranças",
        "arma",
        5,
        "Retomar uma revisão pendente, sem exigir lembrança perfeita.",
        "recall",
        kind="Armas",
        rule=("recall", 7),
    ),
    "explorer_coat": item(
        "Casaco do Cartógrafo",
        "roupa",
        3,
        "Preparar uma rota entre missão, revisão e dificuldades.",
        "route",
        kind="Roupas",
        rule=("topics", 2),
    ),
    "explorer_hood": item(
        "Capuz de exploração",
        "cabeça",
        4,
        "Consultar as próximas atividades do seu plano.",
        "route",
        kind="Roupas",
        rule=("topics", 5),
    ),
    "expedition_boots": item(
        "Botas de expedição",
        "pés",
        5,
        "Continuar o próximo bloco sem perder o ponto de retomada.",
        "resume",
        kind="Roupas",
        rule=("topics", 5),
    ),
    "pack_mule": item(
        "Mula de carga",
        "montaria",
        3,
        "Carregar sua rota: escolher estudo ou revisão, uma atividade por vez.",
        "route",
        kind="Montarias",
        rule=("days", 3),
    ),
    "trail_horse": item(
        "Cavalo das trilhas",
        "montaria",
        5,
        "Preparar uma rota com missão, revisão e revanche.",
        "route",
        kind="Montarias",
        rule=("days", 7),
    ),
    "rogue_cloak": item(
        "Casaco do Ladino",
        "roupa",
        3,
        "Investigar uma dificuldade e preparar uma revanche de estudo.",
        "revenge",
        kind="Roupas",
        rule=("difficulties", 1),
    ),
    "scholar_book": item(
        "Livro do Erudito",
        "mão",
        3,
        "Abrir seu caderno para escrever dúvidas, exemplos e explicações.",
        "notes",
        kind="Acessórios",
        rule=("notes", 2),
    ),
    "sky_griffin": item(
        "Grifo do horizonte",
        "montaria",
        8,
        "Ver a rota completa e preparar um desafio do seu material.",
        "route",
        kind="Montarias",
        rule=("days", 15),
    ),
}
METRIC_LABELS = {
    "reviews": "revisões realizadas",
    "answered": "questões respondidas",
    "recall": "tentativas de recordação (assunto/data distintos)",
    "topics": "assuntos estudados",
    "days": "datas com estudo, sem precisar ser seguidas",
    "difficulties": "dificuldades trabalhadas em estudos",
    "notes": "assuntos estudados com anotações",
}


def requirement(gear):
    if gear.get("starter"):
        return "Equipamento inicial · nível 1"
    if gear.get("acquisition") != "reward":
        return f"Nível {gear['level']} · {gear['price']} moedas"
    result = f"Recompensa do nível {gear['level']}"
    if gear.get("rule"):
        metric, target = gear["rule"]
        result += f" + {target} {METRIC_LABELS[metric]}"
    return result


def metrics(store, plan):
    # Only enrolled real records count; old history remains explicit opt-in.
    row = store.one(
        """SELECT COUNT(DISTINCT CASE WHEN s.elapsed>0 OR s.correct+s.wrong>0 THEN s.topic_id END) topics,
        COUNT(DISTINCT CASE WHEN s.elapsed>0 OR s.correct+s.wrong>0 THEN s.day END) days,
        COALESCE(SUM(s.correct+s.wrong),0) answered,
        COUNT(DISTINCT CASE WHEN (s.elapsed>0 OR s.correct+s.wrong>0) AND
            (trim(s.notes, char(9)||char(10)||char(13)||' ')<>'' OR
             trim(t.notes, char(9)||char(10)||char(13)||' ')<>'') THEN s.topic_id END) notes,
        COUNT(DISTINCT CASE WHEN s.elapsed>0 OR s.correct+s.wrong>0 THEN l.difficulty_id END) difficulties,
        COUNT(DISTINCT CASE WHEN l.recall IS NOT NULL AND (s.elapsed>0 OR s.correct+s.wrong>0)
            THEN s.topic_id || ':' || s.day END) recall
        FROM sessions s JOIN rpg_sources e ON e.session_id=s.id
        LEFT JOIN rpg_links l ON l.session_id=s.id
        LEFT JOIN topics t ON t.id=s.topic_id WHERE s.plan_id=?""",
        (plan,),
    )
    row["reviews"] = store.one(
        """SELECT COUNT(*) n FROM rpg_rewards r JOIN rpg_sources e ON e.id=r.source_id
        WHERE r.plan_id=? AND e.review_id IS NOT NULL AND r.xp>0""",
        (plan,),
    )["n"]
    return row


def paths(progress):
    result = []
    for key, spec in PATHS.items():
        value = progress[spec["metric"]]
        rank = sum(value >= threshold for threshold in spec["targets"])
        result.append(
            dict(
                spec,
                id=key,
                value=value,
                rank=rank,
                rank_name=RANKS[rank],
                target=spec["targets"][min(rank, 2)],
                unit=METRIC_LABELS[spec["metric"]],
            )
        )
    return result


# A mount makes a route easier to scan; it never completes an activity for you.
for _key, _steps in (("pack_mule", 2), ("trail_horse", 3), ("sky_griffin", 4)):
    GEAR[_key]["route_steps"] = _steps
