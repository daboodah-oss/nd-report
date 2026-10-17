#!/usr/bin/env python3
"""Draw every app icon and the link-preview card from a simple "ND" monogram.

    python3 tools/make_icons.py

The monogram is the letters "ND" in metallic gold on a navy square, set in
Barlow Condensed Bold (the page's display face, OFL, bundled in assets/fonts/).
It is drawn here in code; no Notre Dame logo is scraped, copied or hotlinked.

Writes, all into icons/:
  icon-192.png, icon-512.png ... navy rounded square, gold "ND" (purpose any)
  icon-maskable-512.png ........ navy to the edge, "ND" sized so its farthest
                                 pixel from the centre sits at 38% of the side
                                 (inside the 40% maskable safe circle), measured
                                 on the generated file
  apple-touch-icon.png (180), favicon-32.png
  og.png (1200x630) ............ link-preview card (og:image)

One-time tool, run by hand when the mark changes; the scheduled build never
calls it.  Needs Pillow (pip install pillow), which requirements.txt does not.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAVY = (0x0C, 0x23, 0x40)
GOLD = (0xAE, 0x91, 0x42)
BG_DARK = (0x11, 0x12, 0x16)       # the dark theme's --bg (manifest background_color)
INK_DARK = (0xEC, 0xEE, 0xF2)      # dark --ink
MUTED_DARK = (0x9A, 0xA0, 0xAE)    # dark --muted
CUR_DARK = (0x8F, 0xB0, 0xEA)      # dark --cur (current season)
P1_DARK = (0xF0, 0x71, 0x67)       # dark --p1 (previous season)
DISPLAY = ROOT / "assets" / "fonts" / "barlow-condensed-latin-700-normal.woff"
BODY = ROOT / "assets" / "fonts" / "public-sans-latin-400-normal.woff"
SS = 4  # supersampling factor for smooth edges


def font(path, px):
    from PIL import ImageFont
    return ImageFont.truetype(str(path), px)


def monogram(n, box_frac):
    """A transparent n x n layer with gold "ND" whose ink box is box_frac of n tall, centred."""
    from PIL import Image, ImageDraw
    layer = Image.new("L", (n, n), 0)
    probe = font(DISPLAY, 1000)
    l, t, r, b = probe.getbbox("ND")
    px = int(1000 * box_frac * n / (b - t))
    f = font(DISPLAY, px)
    l, t, r, b = f.getbbox("ND")
    ImageDraw.Draw(layer).text(((n - (r - l)) / 2 - l, (n - (b - t)) / 2 - t), "ND", font=f, fill=255)
    return layer


def farthest(mask):
    """Distance from the centre to the farthest inked pixel, as a fraction of the side."""
    n = mask.size[0]; c = (n - 1) / 2; px = mask.load()
    return max((((x - c) ** 2 + (y - c) ** 2) ** 0.5 for y in range(n) for x in range(n) if px[x, y] > 127), default=0) / n


def icon(size, box_frac=0.5, radius_frac=0.2):
    from PIL import Image, ImageDraw
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    if radius_frac: g.rounded_rectangle([0, 0, n - 1, n - 1], radius=radius_frac * n, fill=NAVY)
    else: g.rectangle([0, 0, n - 1, n - 1], fill=NAVY)
    img.paste(GOLD, (0, 0), monogram(n, box_frac))
    return img.resize((size, size), Image.LANCZOS)


def maskable(size=512, target=0.38):
    """Shrink the mark until its farthest pixel (measured on the output) is within target of the side."""
    frac = 0.5
    for _ in range(20):
        out = icon(size, frac, radius_frac=0).convert("RGB")
        px = out.load()  # measure on the generated file: an inked pixel is one nearer gold than navy
        ink = out.convert("L").point(lambda v: 0)
        ip = ink.load()
        for y in range(size):
            for x in range(size):
                if sum((a - b) ** 2 for a, b in zip(px[x, y], GOLD)) < sum((a - b) ** 2 for a, b in zip(px[x, y], NAVY)): ip[x, y] = 255
        reach = farthest(ink)
        if reach <= target: return out, reach
        frac *= target / reach * 0.995
    sys.exit("make_icons: maskable mark did not fit the safe circle")


def og():
    from PIL import Image, ImageDraw
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG_DARK)
    g = ImageDraw.Draw(img)
    g.rectangle([0, 0, W, 14], fill=NAVY)
    g.rectangle([0, 14, W, 18], fill=GOLD)
    img.paste(icon(220, 0.46), (70, 120), icon(220, 0.46))
    big = font(DISPLAY, 132)
    g.text((335, 112), "CARR", font=big, fill=CUR_DARK)
    g.text((335, 262), "VS THE FREEMAN ERA", font=font(DISPLAY, 104), fill=P1_DARK)
    g.text((72, 440), "ND FOOTBALL REPORT  ·  NOTRE DAME FOOTBALL", font=font(DISPLAY, 56), fill=INK_DARK)
    g.text((72, 515), "Same-game comparison, national ranks, the AP Top 5 and the Heisman race.", font=font(BODY, 31), fill=MUTED_DARK)
    return img


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("make_icons needs Pillow: pip install pillow")
    out = ROOT / "icons"; out.mkdir(exist_ok=True)
    icon(512).save(out / "icon-512.png", optimize=True)
    icon(192).save(out / "icon-192.png", optimize=True)
    icon(180, radius_frac=0).convert("RGB").save(out / "apple-touch-icon.png", optimize=True)  # iOS rounds the corners itself
    icon(32, 0.56, radius_frac=0.18).save(out / "favicon-32.png", optimize=True)
    m, reach = maskable()
    m.save(out / "icon-maskable-512.png", optimize=True)
    og().save(out / "og.png", optimize=True)
    print(f"wrote icons/: icon-192, icon-512, icon-maskable-512 (farthest pixel {reach:.3f} of the side), apple-touch-icon, favicon-32, og")


if __name__ == "__main__":
    main()
