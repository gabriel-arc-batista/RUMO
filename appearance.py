"""Character appearance: options, palettes, defaults, validation and layer lists.

Pure data (no Tk, no database). Used by the downloaded-asset preparer
(scripts/prepare_avatar.py), the customizer, CharacterView/Portrait and the
backup validator. The look is stored as the preference ``character_look``.
"""

PREFERENCE = "character_look"

SEXES = [("masculino", "Masculino"), ("feminino", "Feminino")]

# id, label, base, shade, deep, light, lip
SKINS = [
    ("porcelana", "Porcelana", "#F1D5C3", "#D9B19B", "#BF927C", "#FAE7DB", "#CF8D84"),
    ("clara", "Clara", "#E8C0A1", "#CFA081", "#B48264", "#F4D7C1", "#C57D6E"),
    ("bege", "Bege", "#D9AA85", "#BE8B67", "#A1704D", "#E9C3A3", "#B56E5C"),
    ("oliva", "Oliva", "#C49C77", "#A67E5D", "#896346", "#D6B493", "#A46454"),
    (
        "morena-clara",
        "Morena clara",
        "#B58262",
        "#966848",
        "#7A5136",
        "#C99D7C",
        "#975848",
    ),
    ("morena", "Morena", "#996A4A", "#7C5237", "#623E27", "#B08260", "#83473A"),
    ("marrom", "Marrom", "#784D34", "#5E3A25", "#482B1A", "#906248", "#6C392F"),
    ("retinta", "Retinta", "#563525", "#422818", "#311C10", "#6C4734", "#592D25"),
]

# id, label, base, shade, light
HAIR_COLORS = [
    ("preto", "Preto", "#211C1A", "#120F0E", "#3E3632"),
    ("castanho-escuro", "Castanho-escuro", "#3B2A20", "#251912", "#5C4434"),
    ("castanho", "Castanho", "#5E3F2A", "#41291A", "#86603F"),
    ("mel", "Mel", "#93683A", "#6C4A24", "#BE9459"),
    ("ruivo", "Ruivo", "#8E3F22", "#662A15", "#BA633B"),
    ("loiro", "Loiro", "#C39A56", "#9A733A", "#E2C17F"),
    ("platinado", "Platinado", "#DED2B8", "#BBAB8E", "#F4EDDB"),
    ("grisalho", "Grisalho", "#8E8B87", "#6A6764", "#B9B6B1"),
]

# id, label, outer iris, inner iris
EYE_COLORS = [
    ("castanho-escuro", "Castanho-escuro", "#2F1D12", "#55351F"),
    ("castanho", "Castanho", "#4E3119", "#87582D"),
    ("avela", "Avelã", "#5B4B22", "#9A8242"),
    ("ambar", "Âmbar", "#7A4F12", "#C48C2C"),
    ("verde", "Verde", "#355E33", "#6F9E59"),
    ("azul", "Azul", "#294F7C", "#6B9BCC"),
    ("cinza", "Cinza", "#545F67", "#97A3AB"),
]

# Stable legacy id and label of a downloaded eye piece
EYE_SHAPES = [
    ("amendoado", "Amendoado"),
    ("redondo", "Redondo"),
    ("grande", "Grande"),
    ("puxado", "Puxado"),
    ("caido", "Caído"),
    ("encapuzado", "Encapuzado"),
]

BROWS = [
    ("naturais", "Naturais"),
    ("arqueadas", "Arqueadas"),
    ("retas", "Retas"),
    ("grossas", "Grossas"),
    ("finas", "Finas"),
    ("angulosas", "Angulosas"),
    ("suaves", "Suaves"),
]

EARS = [
    ("arredondadas", "Arredondadas"),
    ("pequenas", "Pequenas"),
    ("pontudas", "Pontudas"),
]

# id, label, has front layer, has back layer
HAIR_STYLES = [
    ("curto", "Curto clássico", True, False),
    ("baguncado", "Curto ondulado", True, True),
    ("raspado", "Raspado", True, False),
    ("cacheado", "Médio ondulado", True, True),
    ("crespo", "Longo volumoso", True, True),
    ("ondulado", "Longo ondulado", True, True),
    ("longo", "Longo liso", True, True),
    ("rabo", "Curto lateral", True, False),
    ("coque", "Curto penteado", True, False),
    ("trancas", "Laterais curtas", True, False),
    ("careca", "Sem cabelo", False, False),
    ("franja", "Longo com franja", True, True),
]

# Original ids remain accepted for old profiles/backups. Labels describe real assets.
FACES = [
    (f"rosto-{i}", name)
    for i, name in enumerate(
        ("Oval", "Alongado", "Angular", "Suave", "Arredondado", "Estreito"), 1
    )
]
IRISES = [
    (f"iris-{i}", name)
    for i, name in enumerate(
        ("Com brilho", "Circular", "Pequena", "Escura", "Discreta"), 1
    )
]
NOSES = [(f"nariz-{i}", f"Nariz {i}") for i in range(1, 8)]
MOUTHS = [(f"boca-{i}", f"Boca {i}") for i in range(1, 12)]
BEARDS = [("nenhuma", "Sem pelos faciais"), ("bigode", "Bigode")]
FIELDS = [
    ("sex", "Base de aparência", SEXES),
    ("face", "Rosto", FACES),
    ("skin", "Tom de pele", SKINS),
    ("hair", "Cabelo", HAIR_STYLES),
    ("hair_color", "Cor do cabelo", HAIR_COLORS),
    ("eyes", "Formato dos olhos", EYE_SHAPES),
    ("iris", "Formato da íris", IRISES),
    ("eye_color", "Cor dos olhos", EYE_COLORS),
    ("brows", "Sobrancelhas", BROWS),
    ("nose", "Nariz", NOSES),
    ("mouth", "Boca", MOUTHS),
    ("beard", "Pelos faciais", BEARDS),
]
DEFAULT = dict(
    sex="masculino",
    face="rosto-1",
    skin="morena-clara",
    hair="curto",
    hair_color="castanho-escuro",
    eyes="amendoado",
    iris="iris-1",
    eye_color="castanho",
    brows="naturais",
    nose="nariz-1",
    mouth="boca-1",
    beard="nenhuma",
    ears="arredondadas",
)


def ids(options):
    return [option[0] for option in options]


def option(options, key):
    return next(o for o in options if o[0] == key)


def validate_look(value):
    """Strict backup ids, including the legacy ears preference (now integral)."""
    if not isinstance(value, dict) or set(value) - set(DEFAULT):
        return False
    return all(
        value.get(field, DEFAULT[field]) in ids(options) for field, _, options in FIELDS
    ) and value.get("ears", DEFAULT["ears"]) in ids(EARS)


def normalize(value):
    """Fallback each unknown id separately; migrate old faces without DB writes."""
    look = dict(DEFAULT)
    if isinstance(value, dict):
        for field, _, options in FIELDS + [("ears", "Orelhas legadas", EARS)]:
            if isinstance(value.get(field), str) and value[field] in ids(options):
                look[field] = value[field]
        if "face" not in value and look["sex"] == "feminino":
            look["face"] = "rosto-4"
    return look


def layers(look):
    """Downloaded portrait pieces, ordered using the author's rear/front layers."""
    look = normalize(look)
    back_styles = {"baguncado", "cacheado", "crespo", "ondulado", "longo", "franja"}
    back = (
        [f"hairback-{look['hair']}-{look['hair_color']}"]
        if look["hair"] in back_styles
        else []
    )
    front = [
        f"head-{look['face']}-{look['skin']}",
        "eyeball",
        f"iris-{look['iris']}-{look['eye_color']}",
        f"eyes-{look['eyes']}-{look['skin']}",
        f"brows-{look['brows']}-{look['hair_color']}",
        f"nose-{look['nose']}",
        f"mouth-{look['mouth']}",
    ]
    if look["beard"] != "nenhuma":
        front.append(f"beard-{look['beard']}-{look['hair_color']}")
    if look["hair"] != "careca":
        front.append(f"hair-{look['hair']}-{look['hair_color']}")
    return back, front


def layer_label(name):
    groups = {
        "head": (FACES, SKINS),
        "hair": (HAIR_STYLES, HAIR_COLORS),
        "hairback": (HAIR_STYLES, HAIR_COLORS),
        "eyes": (EYE_SHAPES, SKINS),
        "iris": (IRISES, EYE_COLORS),
        "brows": (BROWS, HAIR_COLORS),
        "nose": (NOSES,),
        "mouth": (MOUTHS,),
        "beard": (BEARDS, HAIR_COLORS),
    }
    labels = []
    for options in groups.get(name.split("-")[0], ()):
        for item in sorted(options, key=lambda value: len(value[0]), reverse=True):
            if f"-{item[0]}-" in name + "-":
                labels.append(item[1])
                break
    return " • ".join(labels) or "Branco dos olhos"


def describe(look):
    look = normalize(look)
    return " • ".join(
        option(options, look[field])[1]
        for field, _, options in FIELDS
        if field in ("sex", "face", "hair")
    )
