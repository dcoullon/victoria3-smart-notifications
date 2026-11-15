"""Draw the five Workshop thumbnail options for Reorder Research Queue, and
preview each one where it will be seen: the "In the past week" carousel
(~244px tiles, the priority) and the "most popular" list (~136px).

Art comes from the installed game: tech icons, the research queue's own
round frame and position badge, the game's pointer cursor, and its display
fonts (Paradox Victorian; Playfair Display and EB Garamond are OFL).

Usage: python research_queue/store_assets/make_thumbnails.py [carousel.webp] [popular.webp]
Writes thumb_A..E.png next to this file, plus previews in previews/.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
G = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")
ICONS = G / "gfx/interface/icons/invention_icons"
FRAME = Image.open(G / "gfx/interface/backgrounds/round_frame_dec.dds").convert("RGBA")
BADGE = Image.open(G / "gfx/interface/backgrounds/round_button_bg.dds").convert("RGBA")
CURSOR = Image.open(G / "gfx/cursors/standard.png").convert("RGBA")
# Paradox Victorian renders capitals as swashes, unreadable at 244px; titles use Playfair.
VICT = str(G / "fonts/PlayfairDisplay/PlayfairDisplay-Black.ttf")
PLAY = str(G / "fonts/PlayfairDisplay/PlayfairDisplay-Black.ttf")
GARA = str(G / "fonts/EBGaramond/EBGaramond-ExtraBold.ttf")
S = 512

HERO = "electrical_generation"
OTHERS = ["railways", "telephone", "camera", "dynamite"]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def icon(name: str, size: int) -> Image.Image:
    return Image.open(ICONS / f"{name}.dds").convert("RGBA").resize((size, size), Image.LANCZOS)


def tile(name: str, size: int, number: int | None = None, ghost: bool = False) -> Image.Image:
    """A queued tech as the game draws it: round frame, icon, position badge."""
    t = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if ghost:
        d = ImageDraw.Draw(t)
        w = max(3, size // 28)
        d.ellipse((w, w, size - w, size - w), outline=(255, 255, 255, 150), width=w)
        return t
    # Vanilla order (tech_tree.gui, type queued_technology): frame, then the
    # 60/80-size icon on top of it.
    t.alpha_composite(FRAME.resize((size, size), Image.LANCZOS))
    ic = icon(name, int(size * .75))
    t.alpha_composite(ic, ((size - ic.width) // 2, (size - ic.height) // 2))
    if number is not None:
        b = int(size * .34)
        t.alpha_composite(BADGE.resize((b, b), Image.LANCZOS), (0, 0))
        f = font(GARA, int(b * .72))
        d = ImageDraw.Draw(t)
        d.text((b / 2, b / 2 - b * .04), str(number), font=f, fill=(245, 236, 210), anchor="mm")
    return t


def shadow(img: Image.Image, radius: int = 10, offset=(6, 10), alpha=150) -> Image.Image:
    pad = radius * 3
    sh = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: v * alpha // 255)
    blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
    blk.putalpha(a)
    sh.alpha_composite(blk, (pad + offset[0], pad + offset[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    sh.alpha_composite(img, (pad, pad))
    return sh, pad


def paste_lifted(canvas: Image.Image, img: Image.Image, xy, angle=0.0):
    if angle:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh, pad = shadow(img)
    canvas.alpha_composite(sh, (int(xy[0] - pad), int(xy[1] - pad)))


def cursor(canvas: Image.Image, xy, scale=2.0):
    c = CURSOR.resize((int(CURSOR.width * scale), int(CURSOR.height * scale)), Image.LANCZOS)
    sh, pad = shadow(c, radius=4, offset=(3, 4), alpha=120)
    canvas.alpha_composite(sh, (int(xy[0] - pad), int(xy[1] - pad)))


def arrow(canvas: Image.Image, p0, p1, bend, color, width, outline=(0, 0, 0, 255)):
    """Curved arrow p0 -> p1, bulging by `bend` px (negative = upwards)."""
    d = ImageDraw.Draw(canvas)
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + bend
    pts = []
    for i in range(41):
        t = i / 40
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * mx + t ** 2 * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * my + t ** 2 * p1[1]
        pts.append((x, y))
    head = width * 2.6
    tx, ty = pts[-1]
    ax, ay = pts[-6]
    ang = math.atan2(ty - ay, tx - ax)
    body = pts[:-4]
    tri = [(tx + math.cos(ang) * head * .35, ty + math.sin(ang) * head * .35),
           (tx - math.cos(ang - .55) * head, ty - math.sin(ang - .55) * head),
           (tx - math.cos(ang + .55) * head, ty - math.sin(ang + .55) * head)]
    for col, w, grow in ((outline, width + 8, 4), (color, width, 0)):
        d.line(body, fill=col, width=w, joint="curve")
        if grow:
            cx, cy = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
            big = [(cx + (x - cx) * 1.22, cy + (y - cy) * 1.22) for x, y in tri]
            d.polygon(big, fill=col)
        else:
            d.polygon(tri, fill=col)


def text_center(d, y, txt, f, fill, stroke=0, stroke_fill=None, x=S / 2):
    d.text((x, y), txt, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=stroke_fill)


def fit(txt: str, path: str, max_w: int, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 10:
        f = font(path, size)
        if f.getbbox(txt)[2] - f.getbbox(txt)[0] <= max_w:
            return f
        size -= 2
    return font(path, size)


def row_band(canvas, y, h, color):
    ImageDraw.Draw(canvas).rectangle((0, y, S, y + h), fill=color)


def option_a() -> Image.Image:
    """Cream, the Smart Treaties family: big title, a dark band of the queue,
    the last tech lifted and dropped first."""
    c = Image.new("RGBA", (S, S), (243, 235, 217, 255))
    d = ImageDraw.Draw(c)
    d.rectangle((8, 8, S - 9, S - 9), outline=(120, 92, 52), width=3)
    text_center(d, 72, "RESEARCH", fit("RESEARCH", VICT, 430, 104), (28, 26, 24))
    text_center(d, 166, "QUEUE", fit("QUEUE", VICT, 430, 112), (28, 26, 24))
    text_center(d, 240, "DRAG TO REORDER", fit("DRAG TO REORDER", GARA, 380, 40), (110, 40, 30))
    row_band(c, 300, 160, (36, 40, 46))
    ts, y = 104, 336
    xs = [40 + i * 112 for i in range(4)]
    c.alpha_composite(tile(None, ts, ghost=True) if False else tile(OTHERS[0], ts, 2), (xs[1], y))
    c.alpha_composite(tile(OTHERS[1], ts, 3), (xs[2], y))
    c.alpha_composite(tile(OTHERS[2], ts, 4), (xs[3], y))
    c.alpha_composite(tile(HERO, ts, ghost=True), (xs[0], y))
    paste_lifted(c, tile(HERO, 128, 1), (xs[0] - 18, y - 46), angle=8)
    arrow(c, (xs[3] + 60, y + 6), (xs[0] + 112, y - 40), -70, (232, 196, 90, 255), 9)
    cursor(c, (xs[0] + 70, y + 30))
    return c


def option_b() -> Image.Image:
    """Bright teal, one giant arrow: slot 4 jumps to slot 1."""
    c = Image.new("RGBA", (S, S), (22, 128, 140, 255))
    g = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((-180, 180, S + 180, S + 520), fill=(14, 92, 104, 255))
    c.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(c)
    text_center(d, 78, "REORDER", fit("REORDER", VICT, 450, 150), (255, 255, 255), 4, (8, 50, 58))
    text_center(d, 168, "RESEARCH", fit("RESEARCH", VICT, 450, 150), (255, 230, 140), 4, (8, 50, 58))
    ts, y = 112, 330
    xs = [24 + i * 118 for i in range(4)]
    c.alpha_composite(tile(HERO, ts, ghost=True), (xs[0], y))
    for i, n in enumerate(OTHERS[:2]):
        c.alpha_composite(tile(n, ts, i + 2), (xs[i + 1], y))
    c.alpha_composite(tile(OTHERS[2], ts, 4), (xs[3], y))
    arrow(c, (xs[3] + 20, y - 8), (xs[0] + 90, y - 22), -95, (255, 214, 64, 255), 16, (8, 50, 58, 255))
    paste_lifted(c, tile(HERO, 132, 1), (xs[0] - 16, y - 60), angle=-8)
    cursor(c, (xs[0] + 80, y + 20))
    return c


def option_c() -> Image.Image:
    """Before / after on cream: the dragged tech's prerequisite comes with it."""
    c = Image.new("RGBA", (S, S), (243, 235, 217, 255))
    d = ImageDraw.Draw(c)
    text_center(d, 58, "DRAG YOUR", fit("DRAG YOUR", VICT, 430, 96), (28, 26, 24))
    text_center(d, 136, "RESEARCH QUEUE", fit("RESEARCH QUEUE", VICT, 470, 72), (28, 26, 24))
    lab = font(GARA, 26)
    ts = 82
    xs = [128 + i * 94 for i in range(4)]
    before = ["railways", "telephone", "camera", HERO]
    after = [HERO, "railways", "telephone", "camera"]
    for label, names, y in (("BEFORE", before, 196), ("AFTER", after, 352)):
        d.text((14, y + ts / 2), label, font=lab, fill=(110, 40, 30), anchor="lm")
        for i, n in enumerate(names):
            c.alpha_composite(tile(n, ts, i + 1), (xs[i], y))
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((xs[3] - 6, 190, xs[3] + ts + 6, 196 + ts + 6), outline=(232, 160, 40, 255), width=6)
    ImageDraw.Draw(hl).ellipse((xs[0] - 6, 346, xs[0] + ts + 6, 352 + ts + 6), outline=(232, 160, 40, 255), width=6)
    c.alpha_composite(hl)
    arrow(c, (xs[3] + 40, 292), (xs[0] + 50, 344), 30, (232, 160, 40, 255), 8, (90, 60, 20, 255))
    return c


def option_d() -> Image.Image:
    """Navy and gold, the Build All family: title, then the row as a strip of UI."""
    c = Image.new("RGBA", (S, S), (16, 24, 44, 255))
    d = ImageDraw.Draw(c)
    text_center(d, 76, "RESEARCH", fit("RESEARCH", VICT, 430, 104), (226, 190, 110))
    text_center(d, 170, "QUEUE", fit("QUEUE", VICT, 430, 112), (226, 190, 110))
    text_center(d, 246, "DRAG & DROP TO REORDER", fit("DRAG & DROP TO REORDER", GARA, 420, 36), (235, 235, 240))
    d.rectangle((0, 304, S, 470), fill=(44, 46, 50))
    d.line((0, 304, S, 304), fill=(150, 120, 70), width=3)
    d.line((0, 470, S, 470), fill=(150, 120, 70), width=3)
    ts, y = 104, 336
    xs = [26 + i * 116 for i in range(4)]
    c.alpha_composite(tile(OTHERS[0], ts, 1), (xs[0], y))
    c.alpha_composite(tile(HERO, ts, ghost=True), (xs[1], y))
    c.alpha_composite(tile(OTHERS[1], ts, 3), (xs[2], y))
    c.alpha_composite(tile(OTHERS[2], ts, 4), (xs[3], y))
    paste_lifted(c, tile(HERO, 124, 2), (xs[3] - 40, y - 44), angle=6)
    arrow(c, (xs[3] - 30, y + 20), (xs[1] + 92, y + 30), -40, (232, 196, 90, 255), 8)
    cursor(c, (xs[3] + 30, y + 26))
    return c


def option_e() -> Image.Image:
    """Amber, one giant tech mid-drag: the gesture itself, title underneath."""
    c = Image.new("RGBA", (S, S), (236, 170, 40, 255))
    g = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((60, 10, 452, 300), fill=(255, 214, 110, 255))
    c.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    d = ImageDraw.Draw(c)
    ts = 84
    xs = [36 + i * 92 for i in range(5)]
    for i, n in enumerate(["railways", None, "telephone", "camera", "dynamite"]):
        if n is None:
            c.alpha_composite(tile(HERO, ts, ghost=True), (xs[i], 236))
        else:
            c.alpha_composite(tile(n, ts, i + 1), (xs[i], 236))
    paste_lifted(c, tile(HERO, 200, 2), (150, 26), angle=-10)
    cursor(c, (300, 150), 2.6)
    text_center(d, 382, "DRAG & DROP", fit("DRAG & DROP", VICT, 470, 120), (30, 20, 10))
    text_center(d, 462, "RESEARCH QUEUE", fit("RESEARCH QUEUE", VICT, 470, 84), (120, 30, 20))
    return c


def option_b_full(bg, glow, line1, line2, stroke, arrow_fill, arrow_edge) -> Image.Image:
    """B with the whole mod name: REORDER / RESEARCH QUEUE, one big arrow."""
    c = Image.new("RGBA", (S, S), bg)
    g = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((-180, 200, S + 180, S + 520), fill=glow)
    c.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(c)
    sw = 4 if stroke else 0
    text_center(d, 76, "REORDER", fit("REORDER", VICT, 450, 150), line1, sw, stroke)
    text_center(d, 172, "RESEARCH QUEUE", fit("RESEARCH QUEUE", VICT, 470, 90), line2, sw, stroke)
    ts, y = 112, 338
    xs = [24 + i * 118 for i in range(4)]
    c.alpha_composite(tile(HERO, ts, ghost=True), (xs[0], y))
    for i, n in enumerate(OTHERS[:2]):
        c.alpha_composite(tile(n, ts, i + 2), (xs[i + 1], y))
    c.alpha_composite(tile(OTHERS[2], ts, 4), (xs[3], y))
    arrow(c, (xs[3] + 20, y - 8), (xs[0] + 90, y - 22), -80, arrow_fill, 16, arrow_edge)
    paste_lifted(c, tile(HERO, 132, 1), (xs[0] - 16, y - 60), angle=-8)
    cursor(c, (xs[0] + 80, y + 20))
    return c


AMBER, AMBER_GLOW = (236, 170, 40, 255), (200, 130, 20, 255)
OPTIONS = {
    "A": option_a, "B": option_b, "C": option_c, "D": option_d, "E": option_e,
    # 2026-11-15: B preferred; the whole name, in teal and in E's amber.
    "B_teal_full": lambda: option_b_full((22, 128, 140, 255), (14, 92, 104, 255), (255, 255, 255),
                                         (255, 230, 140), (8, 50, 58), (255, 214, 64, 255), (8, 50, 58, 255)),
    "B_amber_dark": lambda: option_b_full(AMBER, AMBER_GLOW, (30, 20, 10), (120, 30, 20), None,
                                          (255, 255, 255, 255), (60, 30, 10, 255)),
    "B_amber_white": lambda: option_b_full(AMBER, AMBER_GLOW, (255, 255, 255), (255, 248, 225),
                                           (70, 36, 8), (120, 30, 20, 255), (255, 240, 200, 255)),
}


def previews(thumbs: dict, carousel: Path | None, popular: Path | None):
    out = HERE / "previews"
    out.mkdir(exist_ok=True)
    grid = Image.new("RGB", (5 * 266, 300), (24, 26, 30))
    d = ImageDraw.Draw(grid)
    for i, (k, im) in enumerate(thumbs.items()):
        grid.paste(im.convert("RGB").resize((256, 256), Image.LANCZOS), (i * 266 + 5, 5))
        d.text((i * 266 + 133, 280), k, font=font(GARA, 28), fill=(230, 230, 230), anchor="mm")
    grid.save(out / "all_five.png")
    if carousel and carousel.exists():
        base = Image.open(carousel).convert("RGB")
        # Tile 3 of the pasted carousel (Construction Queue) sits at x 584-828, y 66-312.
        for k, im in thumbs.items():
            b = base.copy()
            b.paste(im.convert("RGB").resize((244, 244), Image.LANCZOS), (844, 66))
            b.save(out / f"carousel_{k}.png")
    if popular and popular.exists():
        base = Image.open(popular).convert("RGB")
        for k, im in thumbs.items():
            b = base.copy()
            b.paste(im.convert("RGB").resize((136, 136), Image.LANCZOS), (10, 316))
            b.save(out / f"popular_{k}.png")


def main():
    thumbs = {}
    for k, fn in OPTIONS.items():
        im = fn()
        im.convert("RGB").save(HERE / f"thumb_{k}.png")
        thumbs[k] = im
    args = [Path(a) for a in sys.argv[1:3]] + [None, None]
    previews(thumbs, args[0], args[1])
    print("wrote", ", ".join(f"thumb_{k}.png" for k in thumbs), "and previews/")


if __name__ == "__main__":
    main()
