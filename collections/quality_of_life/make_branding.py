"""Branding image options for the Workshop collection "Quality of life essentials".

Measured 2026-11-22 on the Victoria 3 collections browse page: the image shows
at 134 px, three per row, next to the collection's title text. The neighbours
are mostly dark paintings, portraits, anime art and grey "no image"
placeholders. The collection will grow, so no option depicts a specific mod.

Fonts and icons are the game's own (Playfair Display and EB Garamond are OFL),
the same family as the Smart Treaties and Reorder thumbnails.

Usage: python collections/quality_of_life/make_branding.py [--round3] [search_screenshot]
Writes branding.png (the chosen design, option 11, for the collection name
"QoL Essentials"), plus every option in options/ and previews in previews/.
options/ and previews/ are not committed: previews embed other authors' art.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")
FONTS = GAME / "fonts"
GFX = GAME / "gfx/interface"
PLAY = str(FONTS / "PlayfairDisplay/PlayfairDisplay-Black.ttf")
PLAY_I = str(FONTS / "PlayfairDisplay/PlayfairDisplay-BlackItalic.ttf")
GARA = str(FONTS / "EBGaramond/EBGaramond-ExtraBold.ttf")
GARA_I = str(FONTS / "EBGaramond/EBGaramond-BoldItalic.ttf")
UI_B = r"C:\Windows\Fonts\arialbd.ttf"
S = 512

CREAM = (243, 235, 217)
INK = (28, 26, 24)
OXBLOOD = (124, 26, 22)
GOLD = (214, 176, 98)
NAVY = (16, 24, 44)
TEAL = (22, 128, 140)
BOTTLE = (22, 74, 52)
ROYAL = (32, 62, 150)


def font(path, size):
    return ImageFont.truetype(path, size)


def gfx(rel, size=None):
    im = Image.open(GFX / rel).convert("RGBA")
    if size:
        im = im.resize((size, int(im.height * size / im.width)), Image.LANCZOS)
    return im


def width(txt, f, tracking=0):
    b = f.getbbox(txt)
    return b[2] - b[0] + tracking * (len(txt) - 1)


def fit(txt, path, max_w, start, tracking=0):
    size = start
    while size > 10 and width(txt, font(path, size), tracking) > max_w:
        size -= 1
    return font(path, size)


def tracked(d, cx, cy, txt, f, fill, tracking):
    x = cx - width(txt, f, tracking) / 2
    for ch in txt:
        d.text((x, cy), ch, font=f, fill=fill, anchor="lm")
        x += f.getlength(ch) + tracking


def center(d, cy, txt, f, fill, cx=S / 2):
    d.text((cx, cy), txt, font=f, fill=fill, anchor="mm")


def qol(d, cx, base, size, fill):
    """QoL with an italic o, kerned tight."""
    parts = [("Q", font(PLAY, size)), ("o", font(PLAY_I, size)), ("L", font(PLAY, size))]
    k = size * .03
    total = sum(f.getlength(t) for t, f in parts) - 2 * k
    x = cx - total / 2
    for t, f in parts:
        d.text((x, base), t, font=f, fill=fill, anchor="ls")
        x += f.getlength(t) - k


def recenter(c, bg):
    box = ImageChops.difference(c.convert("RGB"), Image.new("RGB", c.size, bg)).getbbox()
    out = Image.new("RGB", c.size, bg)
    out.paste(c.convert("RGB").crop((0, box[1], S, box[3])), (0, (S - (box[3] - box[1])) // 2))
    return out


# --- the ten options -------------------------------------------------------

def o01_qol_oxblood():
    """Type only: QoL monogram, oxblood and gold."""
    c = Image.new("RGB", (S, S), OXBLOOD)
    d = ImageDraw.Draw(c)
    qol(d, S / 2, 236, 236, CREAM)
    d.line((96, 300, S - 96, 300), fill=GOLD, width=4)
    tracked(d, S / 2, 360, "ESSENTIALS", fit("ESSENTIALS", GARA, 340, 60, 9), GOLD, 9)
    return recenter(c, OXBLOOD)


def o02_title_cream():
    """Type only: the full title stacked, framed, on cream."""
    c = Image.new("RGB", (S, S), CREAM)
    d = ImageDraw.Draw(c)
    d.rectangle((12, 12, S - 13, S - 13), outline=(120, 92, 52), width=4)
    f = fit("QUALITY", PLAY, 440, 160)
    center(d, 138, "QUALITY", f, INK)
    center(d, 272, "OF LIFE", f, INK)
    d.line((70, 362, S - 70, 362), fill=(120, 92, 52), width=4)
    d.line((70, 446, S - 70, 446), fill=(120, 92, 52), width=4)
    tracked(d, S / 2, 404, "ESSENTIALS", fit("ESSENTIALS", GARA, 372, 64, 10), OXBLOOD, 10)
    return c


def o03_tools_teal():
    """The game's tools icon, big, on teal: fixing things."""
    c = Image.new("RGBA", (S, S), TEAL + (255,))
    ic = gfx("icons/goods_icons/tools.dds", 330)
    c.alpha_composite(ic, ((S - ic.width) // 2, 14))
    d = ImageDraw.Draw(c)
    qol(d, S / 2, 440, 120, (255, 255, 255))
    tracked(d, S / 2, 478, "ESSENTIALS", fit("ESSENTIALS", GARA, 250, 34, 7), (255, 230, 140), 7)
    return c.convert("RGB")


def o04_checkbox_cream():
    """One big ticked checkbox: the essentials list, ticked."""
    c = Image.new("RGBA", (S, S), CREAM + (255,))
    ic = gfx("icons/generic_icons/checkbox_greencheck.dds", 300)
    c.alpha_composite(ic, ((S - ic.width) // 2 + 10, 20))
    d = ImageDraw.Draw(c)
    tracked(d, S / 2, 372, "QUALITY OF LIFE", fit("QUALITY OF LIFE", GARA, 400, 50, 6), (110, 40, 30), 6)
    center(d, 440, "ESSENTIALS", fit("ESSENTIALS", PLAY, 450, 100), INK)
    return c.convert("RGB")


def o05_checklist_ledger():
    """A ledger page of ticked rows: grows with the collection, names no mod."""
    c = Image.new("RGBA", (S, S), CREAM + (255,))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, S, 150), fill=NAVY)
    qol(d, 150, 118, 108, GOLD)
    tracked(d, 360, 78, "ESSENTIALS", fit("ESSENTIALS", GARA, 210, 40, 5), CREAM, 5)
    sprite = Image.open(GFX / "buttons/check_button.dds").convert("RGBA")
    box = sprite.crop((sprite.width // 2, 0, sprite.width, sprite.height)).resize((64, 64), Image.LANCZOS)
    for i, w in enumerate((300, 250, 330, 210)):
        y = 176 + i * 82
        c.alpha_composite(box, (40, y))
        d.rounded_rectangle((128, y + 24, 128 + w, y + 40), radius=8, fill=(70, 62, 54))
        d.line((24, y + 74, S - 24, y + 74), fill=(200, 186, 160), width=2)
    return c.convert("RGB")


def o06_seal():
    """A round stamp: title around the ring, QoL in the middle."""
    c = Image.new("RGBA", (S, S), CREAM + (255,))
    seal = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(seal)
    d.ellipse((22, 22, S - 22, S - 22), outline=OXBLOOD, width=14)
    d.ellipse((128, 128, S - 128, S - 128), outline=OXBLOOD, width=5)
    qol(d, S / 2, 292, 100, OXBLOOD)
    ring = "QUALITY OF LIFE  \u2022  ESSENTIALS  \u2022  "
    f = font(GARA, 50)
    r = 170
    total = sum(f.getlength(ch) for ch in ring)
    a = -math.pi / 2 - (total / r) / 2 * 0  # start at the top
    a = -math.pi / 2
    step = 2 * math.pi / total
    for ch in ring:
        w = f.getlength(ch)
        mid = a + w / 2 * step
        g = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((40, 40), ch, font=f, fill=OXBLOOD, anchor="mm")
        g = g.rotate(-math.degrees(mid) - 90, resample=Image.BICUBIC)
        seal.alpha_composite(g, (int(S / 2 + r * math.cos(mid) - 40), int(S / 2 + r * math.sin(mid) - 40)))
        a += w * step
    c.alpha_composite(seal.rotate(-10, resample=Image.BICUBIC))
    return c.convert("RGB")


def o07_split_navy_gold():
    """Two flat blocks, Build All's navy and gold."""
    c = Image.new("RGB", (S, S), NAVY)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 300, S, S), fill=GOLD)
    f = fit("QUALITY", PLAY, 440, 140)
    center(d, 108, "QUALITY", f, GOLD)
    center(d, 222, "OF LIFE", f, GOLD)
    center(d, 404, "ESSENTIALS", fit("ESSENTIALS", PLAY, 456, 100), NAVY)
    return c


def o08_giant_q():
    """One cropped letter: a giant gold Q on bottle green."""
    c = Image.new("RGB", (S, S), BOTTLE)
    d = ImageDraw.Draw(c)
    d.text((-24, 350), "Q", font=font(PLAY, 440), fill=GOLD, anchor="ls")
    d.text((488, 130), "oL", font=font(PLAY_I, 150), fill=CREAM, anchor="rs")
    tracked(d, S / 2, 474, "ESSENTIALS", fit("ESSENTIALS", GARA, 420, 56, 8), CREAM, 8)
    return c


def o09_label():
    """A Victorian shop label on black: the title as a product."""
    c = Image.new("RGB", (S, S), (18, 18, 20))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((34, 70, S - 34, S - 70), radius=40, fill=CREAM)
    d.rounded_rectangle((48, 84, S - 48, S - 84), radius=30, outline=OXBLOOD, width=5)
    d.rounded_rectangle((58, 94, S - 58, S - 94), radius=24, outline=OXBLOOD, width=2)
    center(d, 160, "Quality of Life", font(GARA_I, 56), OXBLOOD)
    center(d, 258, "ESSENTIALS", fit("ESSENTIALS", PLAY, 370, 90), INK)
    d.line((120, 320, S - 120, 320), fill=OXBLOOD, width=3)
    tracked(d, S / 2, 360, "FOR VICTORIA 3", font(GARA, 30), OXBLOOD, 5)
    return c


def o10_gold_check_royal():
    """The game's gold tick, huge, on royal blue."""
    c = Image.new("RGBA", (S, S), ROYAL + (255,))
    ic = gfx("icons/generic_icons/checkmark.dds", 420)
    c.alpha_composite(ic, (60, 70))
    d = ImageDraw.Draw(c)
    qol(d, 150, 160, 130, (255, 255, 255))
    tracked(d, S / 2, 470, "ESSENTIALS", fit("ESSENTIALS", GARA, 330, 46, 8), (255, 255, 255), 8)
    return c.convert("RGB")


def split_qol(top, qol_fill, band, word_fill, band_top=346, margin=14, rule=None):
    """Option 7's two blocks in option 1's colours, for the name "QoL Essentials":
    QoL on top, ESSENTIALS spanning the full width of the bottom block."""
    c = Image.new("RGB", (S, S), top)
    d = ImageDraw.Draw(c)
    if band != top:
        d.rectangle((0, band_top, S, S), fill=band)
    qol(d, S / 2, band_top - 74, 254, qol_fill)
    f = fit("ESSENTIALS", PLAY, S - 2 * margin, 140)
    b = f.getbbox("ESSENTIALS")
    # Place by the ink box, so the word starts and ends exactly at the margins.
    y = band_top + (S - band_top - (b[3] - b[1])) / 2 - b[1]
    d.text((margin - b[0] + (S - 2 * margin - (b[2] - b[0])) / 2, y), "ESSENTIALS", font=f, fill=word_fill)
    if rule:
        d.line((margin, band_top, S - margin, band_top), fill=rule, width=4)
    return c


OPTIONS = [o01_qol_oxblood, o02_title_cream, o03_tools_teal, o04_checkbox_cream,
           o05_checklist_ledger, o06_seal, o07_split_navy_gold, o08_giant_q,
           o09_label, o10_gold_check_royal]

# Round 3 (2026-11-22): option 7's layout in option 1's colours.
def o11_split_gold_band():
    """Oxblood top, gold band, oxblood ESSENTIALS edge to edge."""
    return split_qol(OXBLOOD, CREAM, GOLD, OXBLOOD)


def o12_split_cream_band():
    """Oxblood top, cream band, oxblood ESSENTIALS edge to edge."""
    return split_qol(OXBLOOD, CREAM, CREAM, OXBLOOD)


def o13_all_oxblood_gold_word():
    """No band: all oxblood, ESSENTIALS in gold under a gold rule."""
    return split_qol(OXBLOOD, CREAM, OXBLOOD, GOLD, rule=GOLD)


def o14_all_oxblood_white_word():
    """No band: all oxblood, white ESSENTIALS, the loudest contrast."""
    return split_qol(OXBLOOD, GOLD, OXBLOOD, (255, 255, 255), rule=GOLD)


ROUND3 = [o11_split_gold_band, o12_split_cream_band, o13_all_oxblood_gold_word, o14_all_oxblood_white_word]
if "--round3" in sys.argv:
    OPTIONS = ROUND3

# Slot of "no Tall no Life" (a grey placeholder) in the user's
# "quality of life" search screenshot, 1757x843: row 3, column 2.
SLOT = (821, 361, 134)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shot = Path(args[0]) if args else None
    tag = "round3" if "--round3" in sys.argv else "ten"
    out_o, out_p = HERE / "options", HERE / "previews"
    out_o.mkdir(exist_ok=True)
    out_p.mkdir(exist_ok=True)
    made = []
    for fn in OPTIONS:
        im = fn()
        name = fn.__name__[1:]
        im.save(out_o / f"{name}.png")
        made.append((name, im))
    # Contact sheet: each option at 200 px and at the real 134 px.
    cw, ch = 360, 250
    sheet = Image.new("RGB", (cw * min(5, len(made)), ch * math.ceil(len(made) / 5)), (27, 40, 56))
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(made):
        x, y = (i % 5) * cw, (i // 5) * ch
        sheet.paste(im.resize((200, 200), Image.LANCZOS), (x + 10, y + 10))
        sheet.paste(im.resize((134, 134), Image.LANCZOS), (x + 218, y + 76))
        d.text((x + 10, y + 216), name.replace("_", " ", 1), font=font(UI_B, 18), fill=(230, 230, 230))
    sheet.save(out_p / f"{tag}_options.png")
    if shot and shot.exists():
        base = Image.open(shot).convert("RGB")
        x, y, s = SLOT
        crops = []
        for name, im in made:
            b = base.copy()
            b.paste(im.resize((s, s), Image.LANCZOS), (x, y))
            b.save(out_p / f"search_{name}.png")
            crops.append(b)
        # At the real size: the slot and its neighbours, every option in place.
        nb = (357, 205, 1270, 650)
        cw, chh = nb[2] - nb[0], nb[3] - nb[1]
        grid = Image.new("RGB", (cw * 2 + 10, (chh + 10) * math.ceil(len(crops) / 2)), (0, 0, 0))
        for i, b in enumerate(crops):
            grid.paste(b.crop(nb), ((i % 2) * (cw + 10), (i // 2) * (chh + 10)))
        grid.save(out_p / f"search_{tag}.png")
    # Chosen 2026-11-22: option 11. This is the file to upload to the collection.
    o11_split_gold_band().save(HERE / "branding.png")
    print("wrote", len(made), "options and branding.png")


if __name__ == "__main__":
    main()
