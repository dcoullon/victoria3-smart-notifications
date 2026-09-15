"""Crop and downscale the newest Victoria 3 screenshot(s) before they are read.

Why this exists. Measured across the 2026-09-08..09-14 sessions: 100 raw
screenshots were read into conversations, every one of them 1920x1080, which
costs about 2,764 image tokens each -- roughly 276k tokens, and each one stays
in context for the rest of the session. Almost always the question was about
one panel: a toast, the feed, the Message Settings list. Cropping to that panel
and halving the resolution turns ~2,800 tokens into ~200-400.

Usage:
    python tools/shot.py                    # newest shot, whole frame, halved
    python tools/shot.py --region toast     # newest shot, cropped to the toast area
    python tools/shot.py -n 3 --region feed # three newest, cropped to the feed
    python tools/shot.py --list             # just list the newest files, no work

Regions are fractions of the frame, so they hold at any resolution. They are
deliberately generous -- a crop that misses the thing is a wasted round trip,
which is the exact cost this script exists to avoid.

Prints the paths it wrote; those are what to read.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image

SHOTS = Path(r"C:\Program Files (x86)\Steam\userdata\42572\760\remote\529340\screenshots")
OUT = Path.home() / "AppData" / "Local" / "Temp" / "v3-shots"

# left, top, right, bottom as fractions of width/height.
REGIONS = {
    "full":     (0.00, 0.00, 1.00, 1.00),
    "toast":    (0.58, 0.05, 1.00, 0.55),  # toasts stack down the right edge
    "alerts":   (0.00, 0.05, 0.22, 0.75),  # Important Actions, left edge
    # CORRECTED 2026-09-15 against real screenshots. The feed is NOT the right
    # column -- that is the outliner (journal, markets, interest groups). The
    # message feed stacks bottom-CENTRE, left of the outliner. The old region
    # returned the outliner every time and missed the thing entirely.
    "feed":     (0.50, 0.58, 0.84, 1.00),
    "outliner": (0.80, 0.05, 1.00, 1.00),  # what "feed" used to point at
    "date":     (0.74, 0.00, 0.92, 0.05),  # in-game date, top right
    "settings": (0.15, 0.05, 0.85, 0.95),  # centred Message Settings dialog
    "topbar":   (0.00, 0.00, 1.00, 0.10),
    "panel":    (0.15, 0.10, 0.85, 0.90),  # any centred panel
}


def newest(n: int) -> list[Path]:
    if not SHOTS.is_dir():
        sys.exit(f"screenshot folder not found: {SHOTS}")
    files = sorted(SHOTS.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        sys.exit(f"no screenshots in {SHOTS}")
    return files[:n]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=1, help="how many of the newest to process")
    ap.add_argument("--region", default="full", choices=sorted(REGIONS),
                    help="which part of the frame to keep (default: full)")
    ap.add_argument("--scale", type=float, default=0.5,
                    help="resize factor applied after cropping (default: 0.5)")
    ap.add_argument("--list", action="store_true",
                    help="list the newest screenshots and exit")
    a = ap.parse_args()

    files = newest(a.n)
    if a.list:
        for f in files:
            print(f"{f.name}  {f.stat().st_size // 1024}KB")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    box = REGIONS[a.region]
    for f in files:
        im = Image.open(f)
        w, h = im.size
        im = im.crop((int(box[0] * w), int(box[1] * h),
                      int(box[2] * w), int(box[3] * h)))
        if a.scale != 1.0:
            im = im.resize((max(1, int(im.width * a.scale)),
                            max(1, int(im.height * a.scale))), Image.LANCZOS)
        dest = OUT / f"{f.stem}_{a.region}.png"
        im.save(dest, optimize=True)
        # ~750 pixels per image token is the rule of thumb used to size these.
        print(f"{dest}  ({im.width}x{im.height}, was {w}x{h}, "
              f"~{im.width * im.height // 750} image tokens vs ~{w * h // 750})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
