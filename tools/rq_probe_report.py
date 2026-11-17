"""Read the Research Queue probe's RQ_PROBE| lines from debug.log and print
a verdict per drop (docs/research-queue-investigation.md, run 3 criteria).

Each drop the probe logs looks like:

    drop|up|f or drop|down|f   the move: the dragged tech to slot f (up|0: dropped
                               on the current research, which dumps as pos|0)
    drop|noop / drop|badx      no move (badx: the name recorded at drag start
                               did not match the dropped tech)
    x|<tech>                   the dragged tech
    pos|<p>|<tech> ...         queue BEFORE: shown techs (pos), overflow (tpos)
    fire_top|<tech> / fire_tail|<tech> ...   techs sent to the back, in order
    after                      one second later
    pos|<p>|<tech> ...         queue AFTER
    nomove                     the "not moved" message was shown

The expected result is computed here from the before-order and the game's
prerequisite data, independently of the GUI:

    up to f   : the dragged tech X and its prerequisites (direct or indirect)
                stay; every other tech at position >= f goes to the back
    down to f : X, every tech at position > f, and every tech after X that
                depends on it or is another mod's (unknown to the game's
                files) go to the back

Expected order = the techs that stay, then the sent-back ones, each in their
original order. A drop passes when the after-order matches, the techs sent
back are exactly that set in that order, no shown tech was sent back
after an overflow one, and the "not moved" message was shown exactly when
the after-order equals the before-order.

Usage: python tools/rq_probe_report.py [--logs-dir PATH]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vic3_paths import VIC3_USER_DIR  # noqa: E402
from gen_research_queue_probe import VANILLA_ROOT, ancestor_pairs, known_techs  # noqa: E402

LINE = re.compile(r"RQ_PROBE\|(.*)$")
# GetName in script dynamic text wraps the name in tooltip markup:
# "\x15tooltippable_name \x15tooltip:...,TechnologyTooltip Psychiatry\x15!\x15!"
MARKUP = re.compile(r"TechnologyTooltip ([^\x15!]+)")
LOC_LINE = re.compile(r'^\s+([\w\-]+):\d*\s+"(.*)"\s*(?:#.*)?$')  # vanilla has trailing comments


def clean(text: str) -> str:
    m = MARKUP.search(text)
    return m.group(1).strip() if m else text


LANGUAGES = ("english", "french", "german", "spanish", "braz_por", "polish",
             "russian", "turkish", "japanese", "korean", "simp_chinese")


def game_loc(language: str) -> dict[str, str]:
    loc: dict[str, str] = {}
    folder = VANILLA_ROOT / "localization" / language
    if not folder.is_dir():
        return loc
    for f in folder.rglob("*.yml"):
        for line in f.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            m = LOC_LINE.match(line)
            if m:
                loc.setdefault(m.group(1), m.group(2))

    def resolve(text: str, depth: int = 0) -> str:
        if depth > 5:
            return text
        return re.sub(r"\$([\w\-]+)\$", lambda m: resolve(loc.get(m.group(1), m.group(0)), depth + 1), text)

    return {k: resolve(v) for k, v in loc.items()}


def ancestors_by_name() -> tuple[dict[str, set[str]], set[str]]:
    """Tech name -> names of its direct and indirect prerequisites, and the
    names of every tech the game's files define, in every game language (the
    log carries names in the player's language; run 3 was played in French).
    A name outside the second set is another mod's tech."""
    out: dict[str, set[str]] = {}
    known: set[str] = set()
    for language in LANGUAGES:
        loc = game_loc(language)
        for p, t in ancestor_pairs():
            out.setdefault(loc.get(t, t), set()).add(loc.get(p, p))
        known |= {loc.get(k, k) for k in known_techs()}
    return out, known


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
    anc, known = ancestors_by_name()

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
            xpos = before.index(x) + base
            members = [t for p, t in enumerate(before, base)
                       if t == x or p > f or (p > xpos and (x in anc.get(t, set()) or t not in known))]
        expected = [t for t in before if t not in members] + members
        fired = [e[1] for e in fires]
        problems = []
        if got != expected:
            problems.append(f"after-order differs, expected {expected}")
            lost = set(before) - set(got)
            if lost:
                problems.append(f"LOST from the queue: {sorted(lost)}")
        nomove = any(e[0] == "nomove" for e in op[after + 1:])
        print(f"  'not moved' message: {'shown' if nomove else 'not shown'}")
        if nomove != (got == before):
            problems.append("the 'not moved' message was " + ("shown after a real move" if nomove
                            else "not shown though nothing moved"))
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
    drags = sum(1 for e in ev if e[0] == "dragstart")
    print(f"\ndragstart lines: {drags} for {len(starts)} drops "
          "(about one per drag means the name is recorded at drag start; a burst "
          "when the panel opens means it is not, and drops refuse as badx)")
    print(f"{passed} pass, {failed} fail, {len(starts)} drops")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
