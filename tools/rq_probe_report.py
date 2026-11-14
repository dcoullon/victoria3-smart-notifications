"""Read the Research Queue probe's RQ_PROBE| lines from debug.log and print
a verdict per operation (docs/research-queue-investigation.md).

Each operation the probe logs looks like:

    drop|x|f            the action: tech at x moved to final position f (or "end")
    pos|<p>|<tech> ...  queue BEFORE: shown techs (pos) and overflow (tpos)
    blocked|<tech>      the prerequisite check stopped the move; <tech> is
                        the shown tech it conflicts with
    fire_top|<tech> / fire_tail|<tech> ...   what was re-queued
    after               one second later
    pos|<p>|<tech> ...  queue AFTER

The expected AFTER order is computed here, independently of the GUI: f
moves the tech to that position (the construction queue's MoveToIndex
semantics), "end" moves it after the last shown tech, and a blocked drop
must leave the queue unchanged.

Usage: python tools/rq_probe_report.py [--logs-dir PATH]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vic3_paths import VIC3_USER_DIR  # noqa: E402

LINE = re.compile(r"RQ_PROBE\|(.*)$")


# GetName in script dynamic text wraps the name in tooltip markup:
# "\x15tooltippable_name \x15tooltip:...,TechnologyTooltip Psychiatry\x15!\x15!"
MARKUP = re.compile(r"TechnologyTooltip ([^\x15!]+)")


def clean(text: str) -> str:
    m = MARKUP.search(text)
    return m.group(1).strip() if m else text


def read_events(log: Path) -> list[list[str]]:
    out = []
    with log.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LINE.search(line.rstrip("\n"))
            if m:
                out.append([clean(part) for part in m.group(1).split("|")])
    return out


def ordered(dump: list[list[str]], kinds=("pos", "tpos")) -> list[str]:
    rows = [(int(e[1]), e[2]) for e in dump if e[0] in kinds and len(e) > 2 and e[1].isdigit()]
    return [name for _, name in sorted(rows)]


def first_pos(dump: list[list[str]]) -> int:
    nums = [int(e[1]) for e in dump if len(e) > 1 and e[1].isdigit()]
    return min(nums) if nums else 1


def main() -> int:
    logs = VIC3_USER_DIR / "logs"
    if "--logs-dir" in sys.argv:
        logs = Path(sys.argv[sys.argv.index("--logs-dir") + 1])
    log = logs / "debug.log"
    if not log.exists():
        print(f"no {log}")
        return 1
    ev = read_events(log)
    if not ev:
        print("No RQ_PROBE lines at all: the mod did not load, or nothing was clicked.")
        return 1

    starts = [i for i, e in enumerate(ev) if e[0] in ("drop", "back", "now")]
    passed = failed = 0
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(ev)
        op = ev[i:end]
        kinds = [e[0] for e in op]
        after = kinds.index("after") if "after" in kinds else None
        head = "|".join(op[0])
        print(f"\n== {head}")
        if op[0][:2] == ["drop", "noop"]:
            print("  drop landed on a position pair the probe does not cover (no action taken)")
            continue
        pre_part = op[1:after] if after else op[1:]
        pre = [e for e in pre_part if e[0] in ("pos", "tpos")]
        fires = [e for e in pre_part if e[0].startswith("fire_")]
        blocks = [e for e in pre_part if e[0] == "blocked"]
        post = [e for e in op[after + 1:] if e[0] in ("pos", "tpos")] if after else []
        before, got = ordered(pre), ordered(post)
        shown = ordered(pre, ("pos",))
        base = first_pos(pre)
        print(f"  before ({len(shown)} shown + {len(before) - len(shown)} overflow, "
              f"first position {base}): {before}")
        for f in fires:
            print(f"  {f[0]}: {f[1]}")
        for b in blocks:
            print(f"  BLOCKED by: {b[1]}")
        print(f"  after  ({len(got)}): {got}")
        if any(len(e) > 1 and e[1] == "over" for e in pre + post):
            print("  NOTE: some techs sit beyond the dump's position range; order check is partial")
        if after is None:
            if n == len(starts) - 1:
                print("  INCOMPLETE: the log ends inside this operation (game still running, or closed mid-drop)")
            else:
                print("  INCOMPLETE: no 'after' line (the delayed dump never ran)")
                failed += 1
            continue
        if op[0][0] == "now":
            print("  (now: recorded only, see where the tech and the old first entry went)")
            continue
        expected = list(before)
        if blocks:
            if fires:
                print("  FAIL: blocked, yet techs were re-queued")
                failed += 1
                continue
        elif op[0][0] == "drop" and op[0][2] == "end":
            x = int(op[0][1])
            if not 0 <= x - base < len(shown):
                print(f"  CANNOT JUDGE: position {x} outside the shown techs")
                failed += 1
                continue
            tech = shown[x - base]
            expected = [t for t in shown if t != tech] + [tech] + before[len(shown):]
        elif op[0][0] == "drop":
            x, k = int(op[0][1]), int(op[0][2])
            if not (0 <= x - base < len(before) and 0 <= k - base < len(before)):
                print(f"  CANNOT JUDGE: positions {x}->{k} outside the dumped range")
                failed += 1
                continue
            tech = expected.pop(x - base)
            expected.insert(k - base, tech)
        else:
            tech = op[0][1]
            if tech not in expected:
                print(f"  CANNOT JUDGE: {tech} not in the before-dump")
                failed += 1
                continue
            expected.remove(tech)
            expected.append(tech)
        if got == expected:
            print("  PASS: " + ("blocked and unchanged" if blocks else "after-order matches the expected order"))
            passed += 1
        else:
            print(f"  FAIL: expected {expected}")
            lost = set(before) - set(got)
            if lost:
                print(f"  LOST from the queue: {sorted(lost)}")
            failed += 1
    print(f"\n{passed} pass, {failed} fail, {len(starts)} operations")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
