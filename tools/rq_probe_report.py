"""Read the Research Queue probe's RQ_PROBE| lines from debug.log and print
a verdict per drop (docs/research-queue-investigation.md, run 3 criteria).

Each drop the probe logs looks like:

    drop|up|f or drop|down|f   the move: the dragged tech to slot f
    drop|noop / drop|badx      no move (badx: the name recorded at drag start
                               did not match the dropped tech)
    x|<tech>                   the dragged tech
    pos|<p>|<tech> ...         queue BEFORE: shown techs (pos), overflow (tpos)
    fire_top|<tech> / fire_tail|<tech> ...   techs sent to the back, in order
    after                      one second later
    pos|<p>|<tech> ...         queue AFTER

The expected result is computed here from the before-order and the game's
prerequisite data, independently of the GUI:

    up to f   : the dragged tech X and its prerequisites (direct or indirect)
                stay; every other tech at position >= f goes to the back
    down to f : X, every tech at position > f, and every dependent of X go
                to the back

Expected order = the techs that stay, then the sent-back ones, each in their
original order. A drop passes when the after-order matches, the techs sent
back are exactly that set in that order, and no shown tech was sent back
after an overflow one.

Usage: python tools/rq_probe_report.py [--logs-dir PATH]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vic3_paths import VIC3_USER_DIR  # noqa: E402
from gen_research_queue_probe import VANILLA_ROOT, ancestor_pairs  # noqa: E402

LINE = re.compile(r"RQ_PROBE\|(.*)$")
# GetName in script dynamic text wraps the name in tooltip markup:
# "\x15tooltippable_name \x15tooltip:...,TechnologyTooltip Psychiatry\x15!\x15!"
MARKUP = re.compile(r"TechnologyTooltip ([^\x15!]+)")
LOC_LINE = re.compile(r'^\s+([\w\-]+):\d*\s+"(.*)"\s*(?:#.*)?$')  # vanilla has trailing comments


def clean(text: str) -> str:
    m = MARKUP.search(text)
    return m.group(1).strip() if m else text


def english_loc() -> dict[str, str]:
    loc: dict[str, str] = {}
    for f in (VANILLA_ROOT / "localization" / "english").rglob("*.yml"):
        for line in f.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            m = LOC_LINE.match(line)
            if m:
                loc.setdefault(m.group(1), m.group(2))

    def resolve(text: str, depth: int = 0) -> str:
        if depth > 5:
            return text
        return re.sub(r"\$([\w\-]+)\$", lambda m: resolve(loc.get(m.group(1), m.group(0)), depth + 1), text)

    return {k: resolve(v) for k, v in loc.items()}


def ancestors_by_name() -> dict[str, set[str]]:
    loc = english_loc()
    out: dict[str, set[str]] = {}
    for p, t in ancestor_pairs():
        out.setdefault(loc.get(t, t), set()).add(loc.get(p, p))
    return out


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
    nums = [int(e[1]) for e in dump if e[0] in ("pos", "tpos") and len(e) > 1 and e[1].isdigit()]
    return min(nums) if nums else 1


def main() -> int:
    logs = VIC3_USER_DIR / "logs"
    if "--logs-dir" in sys.argv:
        logs = Path(sys.argv[sys.argv.index("--logs-dir") + 1])
    # The game rotates debug.log into debug.1.log .. debug.5.log at each launch
    # (and at some save loads), so take the newest one that has probe lines.
    ev, log = [], None
    for c in [logs / "debug.log"] + [logs / f"debug.{i}.log" for i in range(1, 6)]:
        if c.exists():
            ev = read_events(c)
            if ev:
                log = c
                break
    if not ev:
        print("No RQ_PROBE lines in debug.log or debug.1-5.log: the mod did not load, "
              "or no drop ever landed.")
        return 1
    print(f"reading {log.name}")
    anc = ancestors_by_name()

    starts = [i for i, e in enumerate(ev) if e[0] == "drop"]
    passed = failed = 0
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(ev)
        op = ev[i:end]
        head = "|".join(op[0])
        print(f"\n== {head}")
        if len(op[0]) < 3:
            print("  no move: " + {"noop": "the drop landed where nothing changes",
                                   "badx": "FAIL: the drag-start name did not match the dropped tech"}.get(op[0][1], op[0][1]))
            if op[0][1] == "badx":
                failed += 1
            continue
        d, f = op[0][1], op[0][2]
        if d not in ("up", "down"):
            print("  older probe build's line, not judged")
            continue
        f = int(f)
        kinds = [e[0] for e in op]
        after = kinds.index("after") if "after" in kinds else None
        pre_part = op[1:after] if after else op[1:]
        pre = [e for e in pre_part if e[0] in ("pos", "tpos")]
        fires = [e for e in pre_part if e[0].startswith("fire_")]
        xs = [e[1] for e in pre_part if e[0] == "x"]
        post = [e for e in op[after + 1:] if e[0] in ("pos", "tpos")] if after else []
        before, got = ordered(pre), ordered(post)
        shown = ordered(pre, ("pos",))
        base = first_pos(pre)
        print(f"  before ({len(shown)} shown + {len(before) - len(shown)} overflow): {before}")
        print(f"  dragged: {xs}")
        for e in fires:
            print(f"  {e[0]}: {e[1]}")
        print(f"  after  ({len(got)}): {got}")
        if after is None:
            if n == len(starts) - 1:
                print("  INCOMPLETE: the log ends inside this drop (game still running, or closed mid-drop)")
            else:
                print("  NOT JUDGED: the next drop came before this one's check a second later")
            continue
        if len(xs) != 1 or xs[0] not in before:
            print(f"  FAIL: expected exactly one x| line naming a queued tech, got {xs}")
            failed += 1
            continue
        x = xs[0]
        if any(e[1] == "over" for e in pre + post):
            print("  NOTE: some techs sit beyond the dump's position range; order check is partial")
        if d == "up":
            members = [t for p, t in enumerate(before, base)
                       if p >= f and t != x and t not in anc.get(x, set())]
        else:
            members = [t for p, t in enumerate(before, base)
                       if t == x or p > f or x in anc.get(t, set())]
        expected = [t for t in before if t not in members] + members
        fired = [e[1] for e in fires]
        problems = []
        if got != expected:
            problems.append(f"after-order differs, expected {expected}")
            lost = set(before) - set(got)
            if lost:
                problems.append(f"LOST from the queue: {sorted(lost)}")
        if fired != members:
            problems.append(f"sent back {fired}, expected {members}")
        kinds_fired = [e[0] for e in fires]
        if "fire_tail" in kinds_fired and "fire_top" in kinds_fired[kinds_fired.index("fire_tail"):]:
            problems.append("a shown tech was sent back after an overflow one")
        if problems:
            for p in problems:
                print(f"  FAIL: {p}")
            failed += 1
        else:
            print("  PASS")
            passed += 1
    print(f"\n{passed} pass, {failed} fail, {len(starts)} drops")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
