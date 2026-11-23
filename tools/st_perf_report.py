"""Seconds per opening of the goods list, from a --perf build's debug.log.

A --perf build (python tools/gen_smart_trade_gui.py --perf) logs
ST_PERF|begin|<mode> before each card's figure search and
ST_PERF|end|<mode>|ok|bad after it, the search repeated PERF_REPEAT times so
an opening lasts seconds. One opening = consecutive cards in the same mode
(the mode moves on at every opening). Time = last end minus first begin, to
the second (debug.log has no finer timestamp), so each figure is +-1 s.

Usage:  python tools/st_perf_report.py [--logs-dir PATH]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_logs import DEFAULT_LOGS_DIR  # noqa: E402

LINE = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\].*ST_PERF\|(begin|end)\|(new|old|off)(?:\|(ok|bad))?\|")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs-dir", type=Path, default=DEFAULT_LOGS_DIR)
    args = ap.parse_args()
    openings = []
    with open(args.logs_dir / "debug.log", encoding="utf-8", errors="replace") as f:
        for raw in f:
            m = LINE.match(raw)
            if not m:
                continue
            h, mi, s, phase, mode, ok = m.groups()
            t = int(h) * 3600 + int(mi) * 60 + int(s)
            if phase == "begin" and (not openings or openings[-1]["mode"] != mode):
                openings.append({"mode": mode, "start": t, "end": t, "cards": 0, "ok": 0, "bad": 0})
            o = openings[-1] if openings else None
            if o is None or o["mode"] != mode:
                continue
            if phase == "end":
                o["end"] = t
                o["cards"] += 1
                o[ok or "ok"] += 1
    if not openings:
        print("No ST_PERF begin/end lines: not a --perf run, or the cards never logged.")
        return 1
    print("opening  mode  cards  repeats-ran  seconds")
    for i, o in enumerate(openings, 1):
        ran = "all" if o["bad"] == 0 else f"{o['bad']} cards NOT"
        print(f"{i:>7}  {o['mode']:<4}  {o['cards']:>5}  {ran:>11}  {(o['end'] - o['start']) % 86400:>7}")
    by = {}
    for o in openings:
        by.setdefault(o["mode"], []).append((o["end"] - o["start"]) % 86400)
    print()
    for mode in ("new", "old", "off"):
        if mode in by:
            print(f"{mode}: {by[mode]} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
