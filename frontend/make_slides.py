"""Makes web-sized copies of the hero images in frontend/img/slides/ (max 1400 px wide, JPEG quality 82). The originals in frontend/img/ are not touched.
The copies carry no metadata (EXIF, XMP, content credentials): the captions and the credits line on the page say where each picture comes from."""
from pathlib import Path
from PIL import Image

IMG = Path(__file__).resolve().parent / "img"
OUT = IMG / "slides"
OUT.mkdir(exist_ok=True)
SLIDES = [  # (original file, name of the copy)
    ("sousse.jpg", "01-sousse.jpg"),
    ("el-jem.webp", "02-el-jem.jpg"),
    ("sidi-bou-said.webp", "03-sidi-bou-said.jpg"),
    ("ghorfas.jpg", "04-ghorfas.jpg"),
    ("tunis-rooftop.jpg", "05-tunis-rooftop.jpg"),
    ("roman-ruins-ai.png", "06-roman-ruins-ai.jpg"),
    ("mountain-snow.jpg", "07-mountain-snow.jpg"),
]
total = 0
for src, name in SLIDES:
    with Image.open(IMG / src) as im:
        im = im.convert("RGB")
        if im.width > 1400:
            im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
        im.save(OUT / name, "JPEG", quality=82, optimize=True, progressive=True)
    size = (OUT / name).stat().st_size
    total += size
    print(f"{name:24s} {im.width}x{im.height}  {size / 1024:.0f} KB   (from {src})")
print(f"total {total / 1024:.0f} KB")
