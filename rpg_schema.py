"""Additive RPG schema; canonical sessions and reviews remain the study source."""

RPG_TABLES = [
    "rpg_characters",
    "rpg_difficulties",
    "rpg_missions",
    "rpg_challenges",
    "rpg_challenge_topics",
    "rpg_links",
    "rpg_sources",
    "rpg_rewards",
    "rpg_inventory",
    "rpg_story",
]

RPG_SCHEMA = """
CREATE TABLE IF NOT EXISTS rpg_characters(plan_id TEXT PRIMARY KEY REFERENCES plans(id),name TEXT NOT NULL DEFAULT 'Viajante');
CREATE TABLE IF NOT EXISTS rpg_difficulties(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),subject_id TEXT NOT NULL REFERENCES subjects(id),topic_id TEXT NOT NULL REFERENCES topics(id),session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,description TEXT NOT NULL,why TEXT NOT NULL,remember TEXT NOT NULL,source TEXT NOT NULL DEFAULT '',state TEXT NOT NULL DEFAULT 'Aberta' CHECK(state IN ('Aberta','Em prática','Superada pelo usuário')),created_day TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rpg_missions(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),subject_id TEXT NOT NULL REFERENCES subjects(id),topic_id TEXT NOT NULL REFERENCES topics(id),block_id TEXT REFERENCES blocks(id) ON DELETE SET NULL,lap INTEGER,review_id TEXT REFERENCES reviews(id) ON DELETE SET NULL,difficulty_id TEXT REFERENCES rpg_difficulties(id) ON DELETE SET NULL,kind TEXT NOT NULL CHECK(kind IN ('Estudo','Encontro','Revanche')),target INTEGER NOT NULL CHECK(target>=60),small_target INTEGER CHECK(small_target IS NULL OR small_target>=60),next_step TEXT NOT NULL DEFAULT '',state TEXT NOT NULL DEFAULT 'Ativa' CHECK(state IN ('Ativa','Concluída','Arquivada')),created_day TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rpg_challenges(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans(id),name TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('Masmorra','Chefe')),questions INTEGER NOT NULL CHECK(questions>0),time_limit INTEGER CHECK(time_limit IS NULL OR time_limit>0),source TEXT NOT NULL DEFAULT '',created_day TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rpg_challenge_topics(challenge_id TEXT NOT NULL REFERENCES rpg_challenges(id) ON DELETE CASCADE,topic_id TEXT NOT NULL REFERENCES topics(id),PRIMARY KEY(challenge_id,topic_id));
CREATE TABLE IF NOT EXISTS rpg_links(session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,mission_id TEXT REFERENCES rpg_missions(id) ON DELETE SET NULL,difficulty_id TEXT REFERENCES rpg_difficulties(id) ON DELETE SET NULL,challenge_id TEXT REFERENCES rpg_challenges(id) ON DELETE SET NULL,recall TEXT CHECK(recall IS NULL OR recall IN ('Lembrei','Parcial','Não lembrei')));
CREATE TABLE IF NOT EXISTS rpg_sources(id TEXT PRIMARY KEY,session_id TEXT UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,review_id TEXT UNIQUE REFERENCES reviews(id) ON DELETE CASCADE,challenge_id TEXT UNIQUE REFERENCES rpg_challenges(id) ON DELETE CASCADE,CHECK((session_id IS NOT NULL)+(review_id IS NOT NULL)+(challenge_id IS NOT NULL)=1));
CREATE TABLE IF NOT EXISTS rpg_rewards(source_id TEXT PRIMARY KEY REFERENCES rpg_sources(id) ON DELETE CASCADE,plan_id TEXT NOT NULL REFERENCES plans(id),subject_id TEXT REFERENCES subjects(id),xp INTEGER NOT NULL CHECK(xp>=0),coins INTEGER NOT NULL CHECK(coins>=0),explanation TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rpg_inventory(plan_id TEXT NOT NULL REFERENCES plans(id),item_id TEXT NOT NULL,slot TEXT NOT NULL CHECK(slot IN ('Título','Moldura','Insígnia','costas','pescoço','peito','cinto','mão','roupa','cabeça','pés','arma','escudo','montaria')),price INTEGER NOT NULL CHECK(price>=0),equipped INTEGER NOT NULL DEFAULT 0 CHECK(equipped IN (0,1)),acquired_day TEXT NOT NULL,PRIMARY KEY(plan_id,item_id));
CREATE UNIQUE INDEX IF NOT EXISTS rpg_one_equipped_slot ON rpg_inventory(plan_id,slot) WHERE equipped=1;
CREATE TABLE IF NOT EXISTS rpg_story(plan_id TEXT NOT NULL REFERENCES plans(id),chapter INTEGER NOT NULL CHECK(chapter BETWEEN 1 AND 4),unlocked_day TEXT NOT NULL,PRIMARY KEY(plan_id,chapter));
CREATE INDEX IF NOT EXISTS rpg_mission_plan ON rpg_missions(plan_id,state);
CREATE INDEX IF NOT EXISTS rpg_difficulty_plan ON rpg_difficulties(plan_id,state);
PRAGMA user_version=5;
"""

CATALOG = {
    "viajante": {
        "name": "Viajante",
        "slot": "Título",
        "price": 0,
        "level": 1,
        "preview": "Título discreto do personagem",
    },
    "explorador": {
        "name": "Explorador de ideias",
        "slot": "Título",
        "price": 10,
        "level": 2,
        "preview": "Título dourado; não altera suas notas",
    },
    "cartografo": {
        "name": "Cartógrafo do saber",
        "slot": "Título",
        "price": 30,
        "level": 3,
        "preview": "Título da jornada; efeito exclusivamente decorativo",
    },
    "grafite": {
        "name": "Moldura grafite",
        "slot": "Moldura",
        "price": 0,
        "level": 1,
        "preview": "Contorno neutro e discreto",
    },
    "dourada": {
        "name": "Moldura dourada",
        "slot": "Moldura",
        "price": 15,
        "level": 2,
        "preview": "Contorno dourado suave",
    },
    "livro": {
        "name": "Livro de viagem",
        "slot": "Insígnia",
        "price": 5,
        "level": 1,
        "preview": "Insígnia de livro, sem bônus de desempenho",
    },
    "bussola": {
        "name": "Bússola",
        "slot": "Insígnia",
        "price": 20,
        "level": 2,
        "preview": "Insígnia de orientação",
    },
    "farol": {
        "name": "Farol",
        "slot": "Insígnia",
        "price": 40,
        "level": 3,
        "preview": "Insígnia de luz, sem multiplicadores de XP",
    },
}


CATALOG.update(
    {
        "backpack": {
            "name": "Mochila de viagem",
            "slot": "costas",
            "price": 5,
            "level": 1,
            "preview": "Mochila em couro; exclusivamente decorativa",
        },
        "scarf": {
            "name": "Lenço do viajante",
            "slot": "pescoço",
            "price": 10,
            "level": 1,
            "preview": "Lenço bordô sobre o personagem",
        },
        "compass": {
            "name": "Bússola de bolso",
            "slot": "cinto",
            "price": 15,
            "level": 2,
            "preview": "Bússola em latão no cinto",
        },
        "lantern": {
            "name": "Lanterna de exploração",
            "slot": "mão",
            "price": 20,
            "level": 2,
            "preview": "Lanterna dourada; não altera XP, notas ou memória",
        },
        "spyglass": {
            "name": "Luneta de horizonte",
            "slot": "mão",
            "price": 30,
            "level": 3,
            "preview": "Luneta de viagem; substitui o item da mesma mão",
        },
    }
)

STORY = [
    (
        "O primeiro mapa",
        "Você abriu o mapa. Um pequeno estudo já deixa uma trilha.",
        "Primeiro estudo com esforço registrado",
    ),
    (
        "O arquivo das memórias",
        "Você voltou a uma ideia e conferiu o que ainda precisava de atenção.",
        "Primeira revisão realizada",
    ),
    (
        "A ponte em construção",
        "Uma dificuldade virou um próximo passo. A ponte se constrói com encontros.",
        "Primeira dificuldade trabalhada",
    ),
    (
        "Uma nova volta",
        "Você percorreu a trilha e voltou ao mapa. Há espaço para outras jornadas.",
        "Uma volta com estudo e blocos concluídos pelo usuário",
    ),
]

# Gear rewards coexist with the original purchasable IDs and unchanged prices.
from rpg_progression import GEAR, LEGACY_PURPOSES

for key, (purpose, action) in LEGACY_PURPOSES.items():
    CATALOG[key].update(
        purpose=purpose,
        action=action,
        kind="Acessórios",
        acquisition="shop",
        preview=purpose,
    )
CATALOG.update(GEAR)

INVENTORY_SCHEMA = next(
    line
    for line in RPG_SCHEMA.splitlines()
    if line.startswith("CREATE TABLE IF NOT EXISTS rpg_inventory(")
)
INVENTORY_V5_MIGRATION = (
    "DROP INDEX IF EXISTS rpg_one_equipped_slot;"
    "ALTER TABLE rpg_inventory RENAME TO rpg_inventory_v4;"
    + INVENTORY_SCHEMA
    + "INSERT INTO rpg_inventory SELECT * FROM rpg_inventory_v4;"
    "DROP TABLE rpg_inventory_v4;"
    "CREATE UNIQUE INDEX rpg_one_equipped_slot ON rpg_inventory(plan_id,slot) WHERE equipped=1;"
    "PRAGMA user_version=5;"
)
