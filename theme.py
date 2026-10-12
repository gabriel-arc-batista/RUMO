"""Design tokens: color, type, spacing and radius. Screens read names, never hex.

Dark is the identity (layered graphite with moderate gold). Light keeps the same
roles on warm paper. Contrast pairs are verified by tests/test_journey.py.
"""

# Norte Dourado (the original) is derived further below from its three colors.

LIGHT = dict(
    bg="#F4F2ED",
    sidebar="#ECE9E2",
    surface="#FFFFFF",
    raised="#F8F6F1",
    hover="#F0EDE6",
    border="#E2DDD2",
    strong="#CBC4B6",
    fg="#1F1D1A",
    muted="#5F5B54",
    faint="#6B665D",
    accent="#7D5E17",
    tint="#F6EFDD",
    selected="#F3EAD4",
    primary="#C9A24F",
    primary_hover="#B89140",
    primary_ink="#1C170C",
    success="#2A7247",
    success_bg="#E5F3EA",
    error="#B03A47",
    error_bg="#F9E6E8",
    info="#3A6396",
    info_bg="#E6EEF8",
    warning="#8F5D12",
    warning_bg="#FAF0DE",
    track="#E9E5DC",
)

# Tk point sizes. Inter for reading; Poppins only for brand and character areas.
FONT = "Inter"
DISPLAY = "Poppins"
ICON = "lucide"
TYPE = dict(
    display=(DISPLAY, 20, "bold"),
    title=(FONT, 17, "bold"),
    h2=(FONT, 12, "bold"),
    h3=(FONT, 10, "bold"),
    body=(FONT, 10),
    small=(FONT, 9),
    caption=(FONT, 8),
    overline=(FONT, 8, "bold"),
    metric=(FONT, 19, "bold"),
)

# 4 px grid.
SPACE = dict(xs=4, sm=8, md=12, lg=16, xl=24, xxl=32)
RADIUS = dict(sm=6, md=8, lg=12)


def luminance(color):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


LIGHT.setdefault("secondary", LIGHT["info"])
LIGHT.setdefault("secondary_bg", LIGHT["info_bg"])

DEFAULT_THEME = "Norte Dourado"
LIGHT_THEME = "Aurora"
# Older preference values keep working.
LEGACY_THEMES = {"Escuro": DEFAULT_THEME, "Claro": LIGHT_THEME}


def _mix(a, b, fraction):
    channels = [
        round(int(a[i : i + 2], 16) * (1 - fraction) + int(b[i : i + 2], 16) * fraction)
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _readable(color, backgrounds, toward, minimum=4.6):
    """Move a text color toward ``toward`` until it reads on every background."""
    for step in range(40):
        if all(contrast(color, bg) >= minimum for bg in backgrounds):
            return color
        color = _mix(color, toward, 0.06)
    return color


def derive(dark, bg, surface, fg, muted, accent, primary, secondary, **extra):
    """Build every role from a few chosen colors, then enforce contrast."""
    light_mix = (
        (lambda t: _mix(surface, fg, t)) if dark else (lambda t: _mix(bg, fg, t))
    )
    p = dict(
        bg=bg,
        sidebar=extra.pop("sidebar", _mix(bg, surface, 0.45)),
        surface=surface,
        raised=_mix(surface, fg, 0.035) if dark else _mix(surface, bg, 0.55),
        hover=light_mix(0.075 if dark else 0.03),
        border=light_mix(0.1 if dark else 0.085),
        strong=light_mix(0.2 if dark else 0.2),
        fg=fg,
        muted=muted,
        faint=_mix(muted, bg, 0.22),
        accent=accent,
        tint=_mix(surface, primary, 0.14 if dark else 0.16),
        selected=_mix(surface, primary, 0.1 if dark else 0.13),
        primary=primary,
        primary_hover=(
            _mix(primary, "#FFFFFF", 0.18) if dark else _mix(primary, "#000000", 0.09)
        ),
        primary_ink=extra.pop("ink", "#17130B"),
        success=extra.pop("success", "#72C493" if dark else "#2A7247"),
        error=extra.pop("error", "#E58085" if dark else "#B03A47"),
        info=secondary,
        warning=extra.pop("warning", "#E2AE62" if dark else "#8F5D12"),
        secondary=secondary,
        track=light_mix(0.11 if dark else 0.07),
    )
    p.update(extra)
    surfaces = [p[k] for k in ("bg", "surface", "raised", "sidebar")]
    for key in (
        "fg",
        "muted",
        "faint",
        "accent",
        "success",
        "error",
        "info",
        "warning",
    ):
        p[key] = _readable(p[key], surfaces, "#FFFFFF" if dark else "#000000")
    p["secondary"] = p["info"]
    for key in ("success", "error", "info", "warning", "secondary"):
        p[key + "_bg"] = _mix(surface, p[key], 0.14 if dark else 0.1)
        p[key] = _readable(p[key], [p[key + "_bg"]], "#FFFFFF" if dark else "#000000")
    for key in ("tint", "selected"):
        p["accent"] = _readable(p["accent"], [p[key]], "#FFFFFF" if dark else "#000000")
    return p


# The original: black, gold and verdigris (the patina of an old bronze compass).
DARK = derive(
    True,
    "#101011",
    "#181819",
    "#F0EEE8",
    "#B5B1A8",
    "#D6B97E",
    "#C8AA6E",
    "#7FB5A8",
    sidebar="#0C0C0D",
    raised="#202021",
    hover="#262627",
    border="#2C2C2B",
    strong="#3D3D3B",
    track="#2A2A29",
)

# Every theme: a name, light/dark, a sentence, its three colors and its palette.
# Three hues each: the background family, the main color and one companion.
THEMES = {
    "Norte Dourado": dict(
        dark=True,
        about="O original: preto, ouro e verdete, como uma bússola antiga.",
        palette=DARK,
    ),
    "Alto-Mar": dict(
        dark=True,
        about="Azul-marinho, ouro e água-marinha: a carta náutica do RUMO.",
        palette=derive(
            True,
            "#0A101C",
            "#111A2B",
            "#E6ECF5",
            "#9AA8BE",
            "#DDBA6E",
            "#D2AE5E",
            "#62C6D9",
            sidebar="#0D1424",
        ),
    ),
    "Esmeralda Noturna": dict(
        dark=True,
        about="Grafite, ouro e esmeralda: foco calmo para as noites longas.",
        palette=derive(
            True,
            "#0C100F",
            "#141A18",
            "#E9EDE8",
            "#9FAAA4",
            "#D4B26A",
            "#CBA65A",
            "#5CC79E",
            sidebar="#0F1412",
        ),
    ),
    "Rubi Imperial": dict(
        dark=True,
        about="Vinho escuro, ouro e rubi: a elegância de uma biblioteca antiga.",
        palette=derive(
            True,
            "#120C0E",
            "#1B1316",
            "#F0E6E6",
            "#B19FA4",
            "#D9B66E",
            "#CFA85C",
            "#E07A8E",
            sidebar="#160F12",
            error="#F0956F",
        ),
    ),
    "Ametista": dict(
        dark=True,
        about="Roxo profundo, ouro e lavanda: criatividade com serenidade.",
        palette=derive(
            True,
            "#0F0C16",
            "#18141F",
            "#ECE7F4",
            "#A9A0BA",
            "#D8B76F",
            "#CDA95D",
            "#B39CF2",
            sidebar="#130F1B",
        ),
    ),
    "Brasa": dict(
        dark=True,
        about="Carvão, ouro e cobre: energia para a reta final.",
        palette=derive(
            True,
            "#100E0C",
            "#1A1714",
            "#F1EAE2",
            "#ADA296",
            "#DDB86A",
            "#D3AC5C",
            "#E8915A",
            sidebar="#14110F",
            warning="#E8C35A",
        ),
    ),
    "Aurora": dict(
        dark=False,
        about="Papel quente, ouro e azul: claro e acolhedor para o dia.",
        palette=LIGHT,
    ),
    "Brisa": dict(
        dark=False,
        about="Branco frio, ouro e verde-água: leve e arejado.",
        palette=derive(
            False,
            "#EFF4F3",
            "#FFFFFF",
            "#172221",
            "#4E5E5C",
            "#7A5C14",
            "#C9A24F",
            "#1D7A76",
            sidebar="#E6EEEC",
        ),
    ),
    "Nórdico": dict(
        dark=True,
        about="Ardósia, azul-gelo e âmbar: a calma de um porto no inverno.",
        palette=derive(
            True,
            "#0D1015",
            "#151A21",
            "#E8EDF2",
            "#9BA6B2",
            "#A3D0EC",
            "#8FC1E3",
            "#E3B873",
            sidebar="#0A0D11",
        ),
    ),
    "Menta e Coral": dict(
        dark=True,
        about="Grafite, menta e coral: fresco e vivo para as manhãs de revisão.",
        palette=derive(
            True,
            "#0F1111",
            "#171A1A",
            "#EAEEEC",
            "#A0A9A6",
            "#8EDDBD",
            "#7DD3B0",
            "#F2A08F",
            sidebar="#0C0E0E",
            error="#F27A7A",
        ),
    ),
    "Sálvia": dict(
        dark=False,
        about="Papel claro, sálvia e terracota: um caderno de campo.",
        palette=derive(
            False,
            "#F0F3EE",
            "#FFFFFF",
            "#1C241E",
            "#556058",
            "#3F6B4A",
            "#8DB596",
            "#B5583A",
            sidebar="#E7ECE5",
        ),
    ),
    "Pergaminho": dict(
        dark=False,
        about="Pergaminho, bordô e azul-petróleo: biblioteca antiga à luz do dia.",
        palette=derive(
            False,
            "#F3EDE0",
            "#FFFCF5",
            "#2A1F1A",
            "#6A5B50",
            "#7A2E3A",
            "#7A2E3A",
            "#2F5D62",
            sidebar="#ECE4D3",
            ink="#FFF6EC",
            error="#A3322B",
        ),
    ),
    "Cobalto": dict(
        dark=False,
        about="Neve, cobalto e âmbar: claro, nítido e objetivo.",
        palette=derive(
            False,
            "#EEF1F7",
            "#FFFFFF",
            "#172033",
            "#4F5B70",
            "#2449B8",
            "#2F5BD3",
            "#A86400",
            sidebar="#E4E9F3",
            ink="#FFFFFF",
        ),
    ),
}
# Dark themes first, then light ones; the picker follows this order.
THEMES = dict(sorted(THEMES.items(), key=lambda item: not item[1]["dark"]))
THEME_NAMES = tuple(THEMES)


def resolve_theme(preference, system_dark=True):
    """Preference value -> theme name. 'Sistema' follows the OS light/dark."""
    if preference == "Sistema":
        return DEFAULT_THEME if system_dark else LIGHT_THEME
    preference = LEGACY_THEMES.get(preference, preference)
    return preference if preference in THEMES else DEFAULT_THEME


def theme_palette(name):
    return dict(THEMES[resolve_theme(name)]["palette"])


def palette(dark=True):
    return dict(DARK if dark else LIGHT)


def compact_duration(seconds):
    """Readable time for summaries: 41h 36min, 25 min, 40 s."""
    seconds = max(0, int(seconds))
    hours, minutes = seconds // 3600, seconds // 60 % 60
    if hours:
        return f"{hours}h {minutes:02d}min" if minutes else f"{hours}h"
    if minutes:
        return f"{minutes} min"
    return f"{seconds} s"


def number(value):
    """Brazilian thousands separator: 1097 -> 1.097."""
    return f"{int(value):,}".replace(",", ".")


def percent(value, digits=0):
    if value is None:
        return "—"
    return f"{value:.{digits}f}%".replace(".", ",")


def relative_day(day, today):
    """'hoje', 'ontem', 'há 3 dias' or a short date for older records."""
    if not day:
        return ""
    from datetime import date

    days = (today - date.fromisoformat(day)).days
    if days <= 0:
        return "hoje"
    if days == 1:
        return "ontem"
    if days < 30:
        return f"há {days} dias"
    return date.fromisoformat(day).strftime("%d/%m/%Y")
