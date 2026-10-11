"""Extend original code-drawn traveler layers; Pillow is build-time only."""

from pathlib import Path
from PIL import ImageDraw
import prepare_character as art

ROOT = Path(__file__).resolve().parents[1]


def rag_base():
    """Level 1 look: the plain human base itself (no hood, no gold)."""
    image = art.base()
    art.avatar(image, 88)
    art.avatar(image, 44)


def clothing(key, color, edge):
    im = art.canvas()
    d = ImageDraw.Draw(im)
    d.polygon(art.pts((111, 151), (189, 151), (193, 282), (107, 282)), fill=color)
    d.polygon(art.pts((95, 158), (111, 153), (107, 242), (89, 242)), fill=color)
    d.polygon(art.pts((189, 153), (205, 158), (211, 242), (193, 242)), fill=color)
    d.line(art.pts((149, 155), (149, 281)), fill=edge, width=3 * art.K)
    d.rectangle(art.box(109, 249, 191, 262), fill="#4B3628")
    d.rounded_rectangle(
        art.box(141, 249, 159, 263), radius=2 * art.K, outline=edge, width=2 * art.K
    )
    if key in ("arcane_robe", "star_robe"):
        d.polygon(art.pts((110, 270), (190, 270), (205, 329), (95, 329)), fill=color)
        for x, y in ((125, 180), (174, 220), (136, 297), (185, 307)):
            d.line(art.pts((x - 4, y), (x + 4, y)), fill=edge, width=art.K)
            d.line(art.pts((x, y - 4), (x, y + 4)), fill=edge, width=art.K)
    art.save(im, f"eq-{key}.png")


def armor(key, color, edge):
    im = art.canvas()
    d = ImageDraw.Draw(im)
    d.polygon(
        art.pts((116, 151), (184, 151), (193, 232), (175, 249), (125, 249), (107, 232)),
        fill=color,
        outline=edge,
        width=2 * art.K,
    )
    for x in (92, 184):
        d.rounded_rectangle(
            art.box(x, 145, x + 25, 172),
            radius=6 * art.K,
            fill=color,
            outline=edge,
            width=2 * art.K,
        )
    for y in (174, 197, 220):
        d.line(art.pts((115, y), (185, y)), fill=edge, width=art.K)
    if key == "chain_armor":
        for x in range(121, 185, 10):
            for y in range(162, 231, 9):
                d.arc(art.box(x, y, x + 7, y + 7), 0, 340, fill=edge, width=art.K)
    art.save(im, f"eq-{key}.png")


HAND = (97, 249)  # traveler's weapon hand on the 300x380 grid (see prepare_character)
BLADES = {
    "rusty_sword": 64,
    "training_sword": 74,
    "steel_sword": 88,
    "veteran_blade": 96,
}


def weapon(key, color, edge):
    """Every weapon is gripped at the hand; it is drawn behind the body so the
    hand (in the chosen skin tone) covers the grip."""
    im = art.canvas()
    d = ImageDraw.Draw(im)
    hx, hy = HAND
    if "staff" in key:
        d.line(art.pts((hx - 2, 128), (hx + 2, 352)), fill=color, width=7 * art.K)
        d.ellipse(
            art.box(hx - 12, 108, hx + 12, 134),
            fill=edge,
            outline="#E8C979" if key == "crystal_staff" else color,
            width=2 * art.K,
        )
    elif "bow" in key:
        d.arc(art.box(hx, 168, hx + 44, 330), 90, 270, fill=color, width=5 * art.K)
        d.line(art.pts((hx + 22, 170), (hx + 22, 328)), fill=edge, width=art.K)
    else:
        length = BLADES.get(key, 80)
        top = hy + 11
        tip = top + length
        if key == "rusty_sword":
            # Crude, chipped and dull: a beggar's blade, not a hero's.
            d.polygon(
                art.pts(
                    (hx - 5, top),
                    (hx + 5, top),
                    (hx + 6, top + 18),
                    (hx + 3, top + 22),
                    (hx + 5, tip - 10),
                    (hx, tip),
                    (hx - 5, tip - 14),
                    (hx - 3, top + 30),
                ),
                fill="#9A8F7E",
                outline="#5E5446",
                width=art.K,
            )
            for y in (top + 12, top + 34, top + 46):
                d.ellipse(art.box(hx - 3, y - 3, hx + 2, y + 3), fill="#8E5A36")
            d.line(
                art.pts((hx - 7, top), (hx + 7, top)), fill="#4B3A2C", width=3 * art.K
            )
            d.line(art.pts((hx, hy - 14), (hx, top)), fill="#8C7A60", width=6 * art.K)
        else:
            d.polygon(
                art.pts(
                    (hx - 6, top),
                    (hx + 6, top),
                    (hx + 4, tip - 12),
                    (hx, tip),
                    (hx - 4, tip - 12),
                ),
                fill=color,
                outline=edge,
                width=art.K,
            )
            d.line(art.pts((hx, top + 4), (hx, tip - 14)), fill=edge, width=art.K)
            d.rounded_rectangle(
                art.box(hx - 15, top - 3, hx + 15, top + 3), 2 * art.K, fill=edge
            )
            d.line(art.pts((hx, hy - 14), (hx, top)), fill="#513B2B", width=6 * art.K)
            d.ellipse(art.box(hx - 5, hy - 20, hx + 5, hy - 10), fill=edge)
    art.save(im, f"eq-{key}.png")


def detail(key):
    im = art.canvas()
    d = ImageDraw.Draw(im)
    if key == "memory_shield":
        d.polygon(
            art.pts((185, 211), (231, 211), (229, 263), (208, 285), (188, 262)),
            fill="#47566B",
            outline=art.GOLD,
            width=3 * art.K,
        )
        d.line(art.pts((208, 221), (208, 268)), fill=art.GOLD, width=3 * art.K)
        d.line(art.pts((194, 243), (222, 243)), fill=art.GOLD, width=3 * art.K)
    elif key in ("memory_helm", "explorer_hood"):
        # Fitted to the proportioned head (face 126-174, brows at y 97).
        color = "#596273" if key == "memory_helm" else "#40504A"
        d.polygon(
            art.pts(
                (120, 100),
                (123, 72),
                (135, 59),
                (150, 55),
                (165, 59),
                (177, 72),
                (180, 100),
                (171, 93),
                (129, 93),
            ),
            fill=color,
            outline=art.GOLD,
            width=2 * art.K,
        )
        d.rectangle(art.box(146.5, 58, 153.5, 91), fill=art.GOLD)
    else:
        color = "#69513A" if key == "walking_boots" else "#374F48"
        for x in (117, 153):
            d.rounded_rectangle(
                art.box(x, 311, x + 31, 353),
                radius=5 * art.K,
                fill=color,
                outline=art.GOLD,
                width=art.K,
            )
            d.line(art.pts((x + 7, 321), (x + 24, 321)), fill=art.GOLD, width=2 * art.K)
    art.save(im, f"eq-{key}.png")


def mount(key, color):
    im = art.canvas()
    d = ImageDraw.Draw(im)
    if key == "sky_griffin":
        for points in (
            ((62, 262), (19, 158), (66, 185), (96, 264)),
            ((83, 258), (154, 164), (142, 220), (111, 279)),
        ):
            d.polygon(
                art.pts(*points), fill="#D6C9AE", outline="#9D8B6C", width=2 * art.K
            )
    for x in (38, 73, 106):
        d.line(art.pts((x, 295), (x - 3, 348)), fill="#332D29", width=8 * art.K)
    d.ellipse(
        art.box(22, 257, 130, 316), fill=color, outline="#3C342D", width=2 * art.K
    )
    d.polygon(art.pts((30, 278), (26, 222), (48, 209), (66, 267)), fill=color)
    d.ellipse(art.box(15, 201, 54, 235), fill=color)
    for x in (25, 41):
        d.polygon(
            art.pts(
                (x, 211), (x - 5, 173 if key == "pack_mule" else 187), (x + 5, 209)
            ),
            fill=color,
            outline="#4A3F35",
            width=art.K,
        )
    d.ellipse(art.box(19, 215, 25, 221), fill="#111114")
    if key == "sky_griffin":
        d.polygon(art.pts((16, 220), (5, 231), (23, 230)), fill=art.GOLD)
    d.rounded_rectangle(
        art.box(59, 254, 101, 278),
        radius=5 * art.K,
        fill="#654933",
        outline=art.GOLD,
        width=2 * art.K,
    )
    d.line(art.pts((129, 282), (144, 308)), fill="#3C342D", width=5 * art.K)
    art.save(im, f"eq-{key}.png")


def scholar_book():
    image = art.canvas()
    d = ImageDraw.Draw(image)
    d.polygon(
        art.pts((181, 239), (206, 245), (233, 238), (234, 278), (208, 285), (179, 278)),
        fill="#594537",
        outline=art.GOLD,
        width=2 * art.K,
    )
    d.polygon(art.pts((184, 244), (205, 249), (207, 279), (183, 274)), fill="#D6CBB3")
    d.polygon(art.pts((209, 249), (229, 244), (230, 274), (211, 280)), fill="#E8DDC4")
    for y in (255, 263, 271):
        d.line(art.pts((188, y), (202, y + 2)), fill="#8D7961", width=art.K)
        d.line(art.pts((213, y + 2), (225, y)), fill="#8D7961", width=art.K)
    art.save(image, "eq-scholar_book.png")


def main():
    art.OUT.mkdir(exist_ok=True, parents=True)
    rag_base()
    scholar_book()
    for key, color, edge in [
        ("travel_tunic", "#546B65", "#C4A76A"),
        ("arcane_robe", "#454160", "#BDA9D7"),
        ("star_robe", "#303F65", "#D9CA8D"),
        ("explorer_coat", "#3F5B4B", "#B9A273"),
        ("rogue_cloak", "#373647", "#9380AF"),
    ]:
        clothing(key, color, edge)
    for key, color, edge in [
        ("leather_armor", "#785740", "#AB8661"),
        ("chain_armor", "#505C6B", "#8A97A5"),
        ("plate_armor", "#606E83", "#D0AD62"),
    ]:
        armor(key, color, edge)
    for key, color, edge in [
        ("rusty_sword", "#776B5C", "#A58357"),
        ("training_sword", "#796044", "#BCA072"),
        ("steel_sword", "#8D9EAF", "#D1AF69"),
        ("veteran_blade", "#D5DCE5", "#E6BD62"),
        ("precision_bow", "#80613B", "#DECEAB"),
        ("wood_staff", "#71503B", "#C7AB74"),
        ("crystal_staff", "#465977", "#9AC4DF"),
    ]:
        weapon(key, color, edge)
    for key in (
        "walking_boots",
        "expedition_boots",
        "memory_helm",
        "explorer_hood",
        "memory_shield",
    ):
        detail(key)
    for key, color in [
        ("pack_mule", "#8F8D85"),
        ("trail_horse", "#906846"),
        ("sky_griffin", "#AD966A"),
    ]:
        mount(key, color)
    print("Original starter, clothing, armor, weapons and mounts generated.")


if __name__ == "__main__":
    main()
