"""Character appearance: options, palettes, defaults, validation and layer lists.

Pure data (no Tk, no database). Used by the art generator
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

# id, label, width, height, tilt (outer corner up < 0), crease, hooded
EYE_SHAPES = [
    ("amendoado", "Amendoado", 10.0, 4.6, -0.7, True, False),
    ("redondo", "Redondo", 9.2, 5.8, 0.0, True, False),
    ("grande", "Grande", 11.0, 5.6, -0.4, True, False),
    ("puxado", "Puxado", 10.2, 3.6, -1.4, False, False),
    ("caido", "Caído", 10.0, 4.4, 1.4, True, False),
    ("encapuzado", "Encapuzado", 10.0, 4.2, -0.2, True, True),
]

BROWS = [
    ("naturais", "Naturais"),
    ("arqueadas", "Arqueadas"),
    ("retas", "Retas"),
    ("grossas", "Grossas"),
    ("finas", "Finas"),
    ("angulosas", "Angulosas"),
]

EARS = [
    ("arredondadas", "Arredondadas"),
    ("pequenas", "Pequenas"),
    ("pontudas", "Pontudas"),
]

# id, label, has front layer, has back layer
HAIR_STYLES = [
    ("curto", "Curto clássico", True, False),
    ("baguncado", "Curto bagunçado", True, False),
    ("raspado", "Raspado", True, False),
    ("cacheado", "Cacheado curto", True, False),
    ("crespo", "Crespo volumoso", False, True),
    ("ondulado", "Médio ondulado", True, True),
    ("longo", "Longo liso", True, True),
    ("rabo", "Rabo de cavalo", True, True),
    ("coque", "Coque", True, False),
    ("trancas", "Tranças", True, True),
    ("careca", "Careca", False, False),
]

FIELDS = [
    ("sex", "Corpo", SEXES),
    ("skin", "Tom de pele", SKINS),
    ("hair", "Cabelo", HAIR_STYLES),
    ("hair_color", "Cor do cabelo", HAIR_COLORS),
    ("eyes", "Formato dos olhos", EYE_SHAPES),
    ("eye_color", "Cor dos olhos", EYE_COLORS),
    ("brows", "Sobrancelhas", BROWS),
    ("ears", "Orelhas", EARS),
]

DEFAULT = dict(
    sex="masculino",
    skin="morena-clara",
    hair="curto",
    hair_color="castanho-escuro",
    eyes="amendoado",
    eye_color="castanho",
    brows="naturais",
    ears="arredondadas",
)


def ids(options):
    return [option[0] for option in options]


def option(options, key):
    return next(o for o in options if o[0] == key)


def validate_look(value):
    """True when a stored look only uses known ids (backups are untrusted)."""
    if not isinstance(value, dict) or set(value) - set(DEFAULT):
        return False
    return all(
        value.get(field, DEFAULT[field]) in ids(options) for field, _, options in FIELDS
    )


def normalize(value):
    """Known fields only; unknown or missing values fall back to the default."""
    look = dict(DEFAULT)
    if isinstance(value, dict):
        for field, _, options in FIELDS:
            if value.get(field) in ids(options):
                look[field] = value[field]
    return look


def layers(look):
    """(behind-body, body-and-face) layer names, in drawing order."""
    look = normalize(look)
    style = option(HAIR_STYLES, look["hair"])
    back = []
    if style[3]:
        back.append(f"hairback-{look['hair']}-{look['hair_color']}")
    front = [
        f"body-{look['sex']}-{look['skin']}",
        f"ears-{look['ears']}-{look['skin']}",
        f"head-{look['sex']}-{look['skin']}",
        f"eyes-{look['eyes']}-{look['eye_color']}",
    ]
    if look["sex"] == "feminino":
        front.append(f"lashes-{look['eyes']}")
    front.append(f"brows-{look['brows']}-{look['hair_color']}")
    if style[2]:
        front.append(f"hair-{look['hair']}-{look['hair_color']}")
    return back, front


def describe(look):
    look = normalize(look)
    return " • ".join(
        option(options, look[field])[1] for field, _, options in FIELDS[:4]
    )
