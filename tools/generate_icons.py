"""Generate PWA icons (rounded square + note glyph) with PIL."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

BG = (20, 26, 36, 255)
FG = (255, 255, 255, 255)


def make_icon(size: int, path: Path):
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    # Double note: two heads + stems
    head_r = size * 0.16
    y = size * 0.62
    for x in (size * 0.36, size * 0.62):
        d.ellipse((x - head_r, y - head_r, x + head_r, y + head_r), fill=FG)
    stem_w = max(2, int(size * 0.045))
    d.rectangle(
        (size * 0.36 - stem_w / 2, size * 0.30, size * 0.36 + stem_w / 2, y),
        fill=FG,
    )
    d.rectangle(
        (size * 0.62 - stem_w / 2, size * 0.30, size * 0.62 + stem_w / 2, y),
        fill=FG,
    )
    # Beam connecting stems
    d.rectangle(
        (
            size * 0.36 - stem_w / 2,
            size * 0.30,
            size * 0.62 + stem_w / 2,
            size * 0.30 + stem_w,
        ),
        fill=FG,
    )
    img.save(path)


if __name__ == "__main__":
    make_icon(192, OUT / "icon-192.png")
    make_icon(512, OUT / "icon-512.png")
    print("icons written to", OUT)
