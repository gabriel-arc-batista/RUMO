"""Draw the RUMO traveler and decorative equipment as transparent PNG layers.

Original artwork made by code for this project (no external images). Layers are
rendered at 4x and reduced with Lanczos, so the native Canvas only composites
them. Usage: python scripts/prepare_character.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/character"
W, H, K = 300, 380, 4
SIZE = (240, 304)

CLOAK = "#2C2E36"
CLOAK_EDGE = "#3A3D47"
CLOAK_BACK = "#202228"
LINING = "#5A4726"
TUNIC = "#3E4656"
TUNIC_DARK = "#333A48"
PANTS = "#2F3440"
BOOT = "#3B2E22"
GOLD = "#CDAA5C"
GOLD_LIGHT = "#EBD093"
SHADOW = "#101116"
LEATHER = "#5A4532"
LEATHER_DARK = "#463526"
SCARF = "#7B3F3C"
SCARF_DARK = "#64322F"
BRASS = "#B08F52"
SKIN = "#C49A74"


def canvas():
    return Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))


def pts(*coords):
    return [(x * K, y * K) for x, y in coords]


def box(x0, y0, x1, y1):
    return [x0 * K, y0 * K, x1 * K, y1 * K]


def save(image, name, blur=0):
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur * K))
    image.resize(SIZE, Image.LANCZOS).save(OUT / name, optimize=True)


LINEN = "#8E806A"
LINEN_DARK = "#74685A"
PATCH = "#6B5D4C"
STITCH = "#A8977A"
TROUSERS = "#4F463E"
WRAP = "#9A8B74"
WRAP_DARK = "#7C6F5C"
ROPE = "#A68E64"
HAIR = "#3A2A1F"
SKIN_SHADE = "#A8774F"
EYE = "#2B1F19"


def base():
    """Default appearance composite (older code and the default avatars use it)."""
    from appearance import DEFAULT, layers

    # Legacy packaging entry point: compose real downloaded assets only.
    portrait = Image.new("RGBA", (264, 264))
    for name in sum(layers(DEFAULT), []):
        with Image.open(OUT / "look/bust" / f"{name}.png") as layer:
            portrait.alpha_composite(layer)
    image = canvas()
    image.alpha_composite(
        portrait.resize((240 * K, 240 * K), Image.LANCZOS), (30 * K, 60 * K)
    )
    save(image, "base.png")
    return image


def backpack_back():
    """Pack behind the shoulders, below the head line."""
    image = canvas()
    d = ImageDraw.Draw(image)
    d.rounded_rectangle(box(96, 140, 204, 214), 14 * K, fill=LEATHER)
    d.rounded_rectangle(box(108, 132, 192, 152), 10 * K, fill=LEATHER_DARK)
    d.line(pts((114, 146), (186, 146)), fill=GOLD, width=2 * K)
    save(image, "eq-backpack-back.png")


def backpack():
    image = canvas()
    d = ImageDraw.Draw(image)
    for x0, x1 in [(116, 112), (184, 188)]:
        d.line(pts((x0, 146), (x1, 232)), fill=LEATHER_DARK, width=8 * K)
        d.ellipse(box(x1 - 4, 220, x1 + 4, 228), fill=GOLD)
    save(image, "eq-backpack.png")


def scarf():
    image = canvas()
    d = ImageDraw.Draw(image)
    d.rounded_rectangle(box(126, 134, 174, 154), 10 * K, fill=SCARF)
    d.polygon(pts((158, 144), (174, 146), (171, 202), (156, 196)), fill=SCARF_DARK)
    for y in (186, 192):
        d.line(pts((157, y), (172, y + 2)), fill=GOLD, width=1 * K)
    save(image, "eq-scarf.png")


def compass():
    image = canvas()
    d = ImageDraw.Draw(image)
    cx, cy = 150, 196
    d.line(pts((134, 150), (cx, cy - 16), (166, 150)), fill=GOLD, width=2 * K)
    d.ellipse(box(cx - 17, cy - 17, cx + 17, cy + 17), fill=GOLD)
    d.ellipse(box(cx - 13, cy - 13, cx + 13, cy + 13), fill="#1C1D22")
    d.polygon(pts((cx, cy - 11), (cx + 4, cy), (cx - 4, cy)), fill=GOLD_LIGHT)
    d.polygon(pts((cx, cy + 11), (cx + 4, cy), (cx - 4, cy)), fill="#8C8E98")
    d.ellipse(box(cx - 2, cy - 2, cx + 2, cy + 2), fill=GOLD)
    save(image, "eq-compass.png")


def lantern(dx=-29, dy=14):
    def at(x0, y0, x1, y1):
        return box(x0 + dx, y0 + dy, x1 + dx, y1 + dy)

    glow = canvas()
    ImageDraw.Draw(glow).ellipse(at(176, 214, 286, 334), fill=(242, 205, 130, 92))
    save(glow, "eq-lantern-glow.png", blur=12)
    image = canvas()
    d = ImageDraw.Draw(image)
    d.arc(at(222, 232, 242, 254), 180, 360, fill="#2A2A30", width=3 * K)
    d.rounded_rectangle(at(218, 252, 246, 258), 2 * K, fill="#2A2A30")
    d.rounded_rectangle(at(220, 258, 244, 292), 4 * K, fill="#F2D28B")
    d.rectangle(at(231, 258, 233, 292), fill="#2A2A30")
    d.rounded_rectangle(at(218, 290, 246, 296), 2 * K, fill="#2A2A30")
    d.ellipse(at(226, 268, 238, 282), fill="#FFF3D6")
    save(image, "eq-lantern.png")


def spyglass():
    image = canvas()
    d = ImageDraw.Draw(image)
    d.line(pts((86, 286), (124, 258)), fill=BRASS, width=9 * K)
    d.line(pts((80, 291), (92, 282)), fill="#8E7240", width=12 * K)
    d.line(pts((108, 270), (112, 267)), fill=GOLD_LIGHT, width=10 * K)
    save(image, "eq-spyglass.png")


def avatar(full, size):
    """Circular bust used in navigation and summaries, cut from the 4x base."""
    crop = full.crop((60 * K, 20 * K, 240 * K, 200 * K)).resize(
        (size * K, size * K), Image.LANCZOS
    )
    disc = Image.new("RGBA", (size * K, size * K), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse([0, 0, size * K - 1, size * K - 1], fill="#3A3224")
    disc.alpha_composite(crop)
    mask = Image.new("L", (size * K, size * K), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * K - 1, size * K - 1], fill=255)
    result = Image.new("RGBA", (size * K, size * K), (0, 0, 0, 0))
    result.paste(disc, (0, 0), mask)
    ImageDraw.Draw(result).ellipse(
        [K, K, size * K - K - 1, size * K - K - 1], outline=GOLD, width=2 * K
    )
    result.resize((size, size), Image.LANCZOS).save(
        OUT / f"avatar-{size}.png", optimize=True
    )


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    full = base()
    backpack_back()
    backpack()
    scarf()
    compass()
    lantern()
    spyglass()
    avatar(full, 88)
    avatar(full, 44)
