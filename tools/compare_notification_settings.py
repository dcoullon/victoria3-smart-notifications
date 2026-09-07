"""
Compare, per notification `group`:
  - vanilla script default (reference/vanilla/<version>/common/messages/*.txt)
  - this mod's current script default (common/messages/*.txt)
  - the current player's live override, if any
    (Documents/Paradox Interactive/Victoria 3/messagetypes_custom.txt)

Never loads these files into an LLM context window -- this is a plain
regex-based parser, run directly, output kept small and structured.
See the override-hierarchy note in CLAUDE.md for why the player-override
file matters and is keyed by group, not by individual message id.

Usage:
    python tools/compare_notification_settings.py [--all]

By default only prints groups where at least two of the three sources
disagree (the interesting rows). --all prints every group found.
"""
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VANILLA_MESSAGES = REPO_ROOT / "reference" / "vanilla" / "1.13.x" / "common" / "messages" / "00_messages.txt"
MOD_MESSAGES = REPO_ROOT / "common" / "messages" / "00_messages.txt"
USER_SETTINGS = Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3" / "messagetypes_custom.txt"

ENTRY_RE = re.compile(r"^(\w+)\s*=\s*\{\n(.*?)\n\}", re.MULTILINE | re.DOTALL)
GROUP_RE = re.compile(r'group\s*=\s*"([^"]+)"')
NTYPE_RE = re.compile(r"notification_type\s*=\s*(\w+)")
USER_ENTRY_RE = re.compile(r"(\w+)=\{\s*notification=(\w+)(?:\s*pause_game=(\w+))?\s*\}")


def parse_messages_file(path: Path) -> dict:
    """group -> set of notification_type values used by keys in that group."""
    text = path.read_text(encoding="utf-8-sig")
    group_defaults: dict[str, set[str]] = {}
    for key, body in ENTRY_RE.findall(text):
        gmatch = GROUP_RE.search(body)
        nmatch = NTYPE_RE.search(body)
        if not gmatch or not nmatch:
            continue
        group_defaults.setdefault(gmatch.group(1), set()).add(nmatch.group(1))
    return group_defaults


def collapse(values: set) -> str:
    if not values:
        return "-"
    if len(values) == 1:
        return next(iter(values))
    return "mixed(" + "/".join(sorted(values)) + ")"


def parse_user_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    out = {}
    for group, ntype, pause in USER_ENTRY_RE.findall(text):
        out[group] = (ntype, pause or "no")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="print every group, not just disagreements")
    args = ap.parse_args()

    if not VANILLA_MESSAGES.exists():
        print(f"Missing vanilla baseline: {VANILLA_MESSAGES}", file=sys.stderr)
        sys.exit(1)
    if not MOD_MESSAGES.exists():
        print(f"Missing mod messages file: {MOD_MESSAGES}", file=sys.stderr)
        sys.exit(1)

    vanilla = parse_messages_file(VANILLA_MESSAGES)
    mod = parse_messages_file(MOD_MESSAGES)
    user = parse_user_settings(USER_SETTINGS)

    if not user:
        print(f"(note: no user settings file found/parsed at {USER_SETTINGS})")

    all_groups = sorted(set(vanilla) | set(mod))
    rows = []
    for g in all_groups:
        v = collapse(vanilla.get(g, set()))
        m = collapse(mod.get(g, set()))
        u_ntype, u_pause = user.get(g, ("-", "-"))
        disagreement = len({v, m, u_ntype} - {"-"}) > 1
        if args.all or disagreement:
            rows.append((g, v, m, u_ntype, u_pause))

    if not rows:
        print("No groups found (check paths).")
        return

    w = max(len(r[0]) for r in rows)
    header = f"{'group'.ljust(w)}  {'vanilla':10}{'mod':10}{'user_live':10}{'user_pause'}"
    print(header)
    print("-" * len(header))
    for g, v, m, u, p in rows:
        print(f"{g.ljust(w)}  {v:10}{m:10}{u:10}{p}")
    print(f"\n{len(rows)} group(s) shown out of {len(all_groups)} total.")


if __name__ == "__main__":
    main()
