"""Prepare downloaded CC0 layers; only resize, multiply tint and composite.

Pillow is a build dependency only. Never draws character geometry. Original
1024px PNGs remain in sources; runtime PNGs are 264px, thumbnails 88px.
"""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import appearance as A

SOURCE = ROOT / "assets/character/sources/erebus/example_assets"
OUT = ROOT / "assets/character/look"
ORIGIN = "https://n-erebus.itch.io/portrait-creator"
HAIRS = {
    "curto": 1,
    "baguncado": 11,
    "raspado": 6,
    "cacheado": 3,
    "crespo": 10,
    "ondulado": 8,
    "longo": 7,
    "rabo": 2,
    "coque": 4,
    "trancas": 5,
    "franja": 9,
}
EYES = dict(zip(A.ids(A.EYE_SHAPES), range(1, 7)))
BROWS = dict(zip(A.ids(A.BROWS), range(1, 8)))


def tinted(source, color):
    with Image.open(source) as image:
        rgba = image.convert("RGBA")
        if color:
            rgb = ImageChops.multiply(
                rgba.convert("RGB"), Image.new("RGB", rgba.size, color)
            )
            rgb.putalpha(rgba.getchannel("A"))
            rgba = rgb
        return rgba.resize((264, 264), Image.Resampling.LANCZOS)


def save_png(image, target):
    """Publish each complete PNG atomically so a running Tk cannot read half a file."""
    temporary = target.with_suffix(".png.tmp")
    image.save(temporary, format="PNG", optimize=True)
    temporary.replace(target)


def main():
    records = []
    for view in ("bust", "full", "thumbnails"):
        (OUT / view).mkdir(parents=True, exist_ok=True)

    def emit(name, category, relative, color=None, order=0):
        source = SOURCE / relative
        image = tinted(source, color)
        save_png(image, OUT / "bust" / f"{name}.png")
        # Portrait-only pack: full panel shows the same face, not a fake body.
        save_png(
            image.resize((240, 240), Image.Resampling.LANCZOS),
            OUT / "full" / f"{name}.png",
        )
        records.append(
            dict(
                id=name,
                name=A.layer_label(name),
                category=category,
                path=f"bust/{name}.png",
                compatibility=["masculino", "feminino"],
                layer=order,
                origin=ORIGIN,
                source=relative,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                color=color,
                license="CC0-1.0",
            )
        )

    for head in A.ids(A.FACES):
        for skin in A.SKINS:
            emit(
                f"head-{head}-{skin[0]}",
                "face",
                f"head/head_{head[-1]}.png",
                skin[2],
                10,
            )
    emit("eyeball", "eyes", "eyeball/eyeball_1.png", None, 20)
    for key, number in EYES.items():
        for skin in A.SKINS:
            emit(
                f"eyes-{key}-{skin[0]}", "eyes", f"eyes/eyes_{number}.png", skin[2], 30
            )
    for shape in A.ids(A.IRISES):
        for color in A.EYE_COLORS:
            emit(
                f"iris-{shape}-{color[0]}",
                "iris",
                f"iris/iris_{shape[-1]}.png",
                color[3],
                25,
            )
    for key, number in BROWS.items():
        for color in A.HAIR_COLORS:
            emit(
                f"brows-{key}-{color[0]}",
                "brows",
                f"eyebrow/eb_{number}.png",
                color[2],
                40,
            )
    for key, number in HAIRS.items():
        for color in A.HAIR_COLORS:
            emit(
                f"hair-{key}-{color[0]}",
                "hair",
                f"hair/hair_{number}.png",
                color[2],
                80,
            )
            back = f"hair_back/hair_back_{number}.png"
            if (SOURCE / back).is_file():
                emit(f"hairback-{key}-{color[0]}", "hair", back, color[2], 0)
    for key in A.ids(A.NOSES):
        emit(f"nose-{key}", "nose", f"nose/nose_{key[-1]}.png", "#705245", 45)
    for key in A.ids(A.MOUTHS):
        emit(
            f"mouth-{key}",
            "mouth",
            f'mouth/mouth_{key.split("-")[-1]}.png',
            "#79514C",
            50,
        )
    for color in A.HAIR_COLORS:
        emit(f"beard-bigode-{color[0]}", "beard", "beard/beard_1.png", color[2], 60)
    for field, _, options in A.FIELDS:
        for key in A.ids(options):
            look = A.normalize(dict(A.DEFAULT, **{field: key}))
            if field == "sex":
                look["face"] = "rosto-4" if key == "feminino" else "rosto-1"
            image = Image.new("RGBA", (264, 264))
            back, front = A.layers(look)
            for name in back + front:
                with Image.open(OUT / "bust" / f"{name}.png") as layer:
                    image.alpha_composite(layer)
            save_png(
                image.resize((88, 88), Image.Resampling.LANCZOS),
                OUT / "thumbnails" / f"{field}-{key}.png",
            )
    (OUT / "catalog.json").write_text(
        json.dumps(
            dict(
                package="Portrait Creator example_assets",
                author="N. Erebus",
                origin=ORIGIN,
                license="CC0-1.0",
                source_size=[1024, 1024],
                size=[264, 264],
                pieces=records,
                options={
                    field: [
                        {
                            "id": o[0],
                            "name": o[1],
                            "thumbnail": f"thumbnails/{field}-{o[0]}.png",
                        }
                        for o in options
                    ]
                    for field, _, options in A.FIELDS
                },
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(records)} image layers and real thumbnails, offline.")


if __name__ == "__main__":
    main()
