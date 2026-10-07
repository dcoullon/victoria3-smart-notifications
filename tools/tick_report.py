"""Report how fast the game ran, from the tick probe's debug.log lines.

Reads debug.log and its rotated copies (debug.1.log ... one per earlier
launch), finds the TICK_PROBE lines (tools/build_tick_probe.py), and splits
each launch into runs wherever the game was paused: a gap longer than
GAP_FACTOR x the launch's median month marks a pause. For each run it prints
the months recorded, the real seconds they took, and seconds per in-game
month (mean, plus the spread of single months). It also prints which mods
the launch loaded, read from the same log, so runs label themselves.

Only aggregates are printed; no log is dumped (CLAUDE.md § 2).

Usage:  python tools/tick_report.py
        python tools/tick_report.py --logs-dir PATH
        python tools/tick_report.py --gap 4      (pause threshold, x median month)
"""
import argparse
import re
import statistics
from pathlib import Path

LOGS = Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3" / "logs"
TAG = "TICK_PROBE|month"
STAMP = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\]")
MOD_LINE = re.compile(r"Mod (.+?) \(([a-z0-9_]+)\) version")


def read_launch(path):
    """(mods loaded, seconds-of-day of every probe line) for one log file."""
    mods, times, last, day = [], [], None, 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if "dlc.cpp" in line:
                m = MOD_LINE.search(line)
                if m and m.group(2) not in [x[1] for x in mods]:
                    mods.append((m.group(1), m.group(2)))
            if TAG not in line:
                continue
            m = STAMP.match(line)
            if not m:
                continue
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            if last is not None and t + day < last:
                day += 86400          # crossed midnight
            times.append(t + day)
            last = t + day
    return mods, times


def split_runs(times, gap_factor):
    if len(times) < 3:
        return [times] if times else []
    steps = [b - a for a, b in zip(times, times[1:])]
    cut = max(statistics.median(steps) * gap_factor, 5)
    runs, cur = [], [times[0]]
    for prev, t in zip(times, times[1:]):
        if t - prev > cut:
            runs.append(cur)
            cur = [t]
        else:
            cur.append(t)
    runs.append(cur)
    return runs


def describe(run):
    months = len(run) - 1
    if months < 2:
        return f"{months} month(s): too short to time"
    secs = run[-1] - run[0]
    steps = [b - a for a, b in zip(run, run[1:])]
    sd = statistics.stdev(steps) if len(steps) > 1 else 0.0
    return (f"{months:3d} months in {secs:4d} s = {secs / months:6.2f} s/month "
            f"(single months {min(steps)}-{max(steps)} s, sd {sd:.2f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs-dir", type=Path, default=LOGS)
    ap.add_argument("--gap", type=float, default=4.0)
    args = ap.parse_args()
    files = sorted(args.logs_dir.glob("debug*.log"),
                   key=lambda p: int(re.search(r"debug\.?(\d*)\.log", p.name).group(1) or 0),
                   reverse=True)          # oldest launch first
    found = False
    for path in files:
        mods, times = read_launch(path)
        if not times:
            continue
        found = True
        others = [name for name, mid in mods if mid != "tick_probe"]
        print(f"\n{path.name}: mods = {', '.join(others) if others else 'none besides the probe'}")
        for i, run in enumerate(split_runs(times, args.gap), 1):
            print(f"  run {i}: {describe(run)}")
    if not found:
        print("No TICK_PROBE lines found. Is the Tick Probe mod enabled, and was the game unpaused?")
    print("\nResolution: the log stamps whole seconds, so a run's total is +-1 s.")


if __name__ == "__main__":
    main()
