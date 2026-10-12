"""Inventory thumbnails cut from the existing equipment layers.

Usage: python scripts/prepare_item_thumbs.py
Reads assets/character/eq-<item>.png (full-body 240x304 layers drawn by
prepare_rpg_equipment.py), crops each item to its visible pixels and writes transparent
thumbnails to assets/character/items/<size>/<item>.png (96, 64 and 44 px). Pillow is a
build dependency only; the app loads the PNGs with Tk.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "character"
TARGET = SOURCE / "items"
SIZES = (96, 64, 44)
SKIP = {"backpack-back", "lantern-glow"}


def thumbnail(path, size):
    image = Image.open(path).convert("RGBA")
    box = image.getbbox()
    if not box:
        return None
    item = image.crop(box)
    # Small art is enlarged up to 1.6x at most, so thin items stay crisp.
    scale = min((size - 8) / item.width, (size - 8) / item.height, 1.6 * size / 64)
    item = item.resize(
        (max(1, round(item.width * scale)), max(1, round(item.height * scale))),
        Image.LANCZOS,
    )
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(item, ((size - item.width) // 2, (size - item.height) // 2))
    return canvas


def main():
    written = 0
    for size in SIZES:
        (TARGET / str(size)).mkdir(parents=True, exist_ok=True)
    for path in sorted(SOURCE.glob("eq-*.png")):
        name = path.stem[3:]
        if name in SKIP:
            continue
        for size in SIZES:
            image = thumbnail(path, size)
            if image:
                image.save(TARGET / str(size) / f"{name}.png", optimize=True)
                written += 1
    print(f"{written} miniaturas em {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
