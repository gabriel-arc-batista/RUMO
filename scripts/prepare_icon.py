"""Draw the original book/clock mark; Pillow is used only at build time."""

from pathlib import Path
from PIL import Image, ImageDraw

assets = Path(__file__).resolve().parents[1] / "assets"
size = 1024
image = Image.new("RGBA", (size, size))
mask = Image.new("L", (size, size))
pen = ImageDraw.Draw(mask)
pen.rounded_rectangle((32, 32, 992, 992), radius=224, fill=255)
gradient = Image.new("RGBA", (size, size))
pixels = ImageDraw.Draw(gradient)
for y in range(size):
    t = y / (size - 1)
    color = tuple(round(a + (b - a) * t) for a, b in zip((35, 32, 25), (9, 9, 9))) + (
        255,
    )
    pixels.line((0, y, size, y), fill=color)
image.paste(gradient, (0, 0), mask)
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((52, 52, 972, 972), radius=207, outline="#D6B467", width=14)
# An open book with a clear central fold, readable at small icon sizes.
draw.polygon(
    [
        (220, 292),
        (454, 316),
        (512, 354),
        (570, 316),
        (804, 292),
        (804, 653),
        (570, 680),
        (512, 720),
        (454, 680),
        (220, 653),
    ],
    fill="#E2C47F",
)
draw.line([(512, 370), (512, 687)], fill="#8B713C", width=18)
for x in (267, 563):
    for y in (409, 475, 541):
        draw.line((x, y, x + 130, y + 14), fill="#AD8E4E", width=17)
# A small clock on the cover ties the mark to a study cycle.
draw.ellipse((591, 569, 893, 871), fill="#16130E", outline="#E2C47F", width=18)
draw.line([(742, 631), (742, 720), (803, 753)], fill="#FFFFFF", width=20, joint="curve")
draw.ellipse((730, 708, 754, 732), fill="#FFFFFF")
image = image.resize((256, 256), Image.Resampling.LANCZOS)
image.save(assets / "RUMO.png")
image.save(
    assets / "RUMO.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("Original app icon generated in seven Windows sizes.")
