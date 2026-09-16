"""
Scan Victoria 3's own log files for lines relevant to this mod, without
ever dumping a whole log into context (error.log/debug.log routinely run
several hundred KB -- see CLAUDE.md's Token Budget rule).

Two categories, always both scanned:
  - This mod's own `debug_log` output (all tagged `SNW_<NAME>|...`,
    confirmed real convention -- see `grep -rohE 'debug_log = "[A-Z_]+\\|'
    common/`).
  - Confirmed-real engine error signatures this project has hit before
    (see docs/engine-notes.md) -- "Could not find data system function",
    "Could not find promote for", "This scope doesn't support variables",
    "Data error in loc string" -- printed regardless of tag, since a
    genuine new engine error from this mod's own files won't carry an
    SNW_ tag.

Usage:
    python tools/scan_logs.py                 # last 20 matches per file/category
    python tools/scan_logs.py --lines 50       # more context per category
    python tools/scan_logs.py --logs-dir PATH  # override the default logs dir
    python tools/scan_logs.py --unfiltered     # ALL error.log lines, no pattern filter
    python tools/scan_logs.py --census         # analyse a notification-census run

`--census` is the analysis half of the notification census (see
docs/feed-census-plan.md and tools/build_census_mod.py). It streams the
SNW_CENSUS lines a census build wrote and prints aggregates only -- ranked
keys, the per-decade growth curve, and the vanilla-vs-mod tier split. A census
debug.log runs to hundreds of MB, so it is never read into a context window;
the work lives in tools/census_report.py.

Intended for a beta tester to run against their own log files and paste
the (small, filtered) output when reporting an issue -- see
STEAM_WORKSHOP_DESCRIPTION.bbcode's Issue Reporting section.

`--unfiltered` exists for checks where you're specifically looking for
something NOT on the known-pattern list -- e.g. confirming a save loads
cleanly after removing the mod (orphaned script variables left behind in
the save are expected and harmless, but any genuinely NEW error type
wouldn't match SNW_* tags or the known engine-error signatures below, so
the normal filtered scan could miss it).
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_LOGS_DIR = Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3" / "logs"

ENGINE_ERROR_PATTERNS = [
    r"Could not find data system function",
    r"Could not find promote for",
    r"This scope doesn't support variables",
    r"Data error in loc string",
    r"Promote 'GetScriptedGui' returned nullptr",
    r"Unknown effect",
    r"Failed to convert statement",
    r"should be in utf8-bom encoding",
    # Added 2026-09-16. A .gui file referencing an @constant declared in a
    # DIFFERENT file fails with this, kills the enclosing type, and the panel
    # silently falls back to vanilla -- no missing-widget error, nothing on
    # screen to explain it. It sat at line 2 of error.log and this scan
    # reported "no errors found" because nothing here matched it.
    r"Malformed token",
    r"Failed to read key reference",
    # Added 2026-09-16, the THIRD time this scan reported "clean" while a real
    # failure sat in error.log. A loc string whose dynamic text cannot be
    # resolved renders as an EMPTY widget -- a blank button, no crash, no
    # visible clue -- and the engine reports it under these two, naming the
    # loc key rather than any file of ours, so neither the signature list nor
    # the shipped-filename matcher caught it.
    r"FetchData failed",
    r"PdxDataFetchLocalizedData failed",
]

# Any log line naming a file THIS REPO ships, whatever the engine called the
# problem. The signature list above can only catch failure modes we have
# already met once; this catches the first occurrence of one we haven't.
#
# It exists because of a concrete miss: the @panel_width failure above was in
# error.log, attributed by name to our own .gui file, and a filtered scan
# still printed "(none found)" -- which read as "the mod loaded fine".
# A clean scan has to mean the mod is clean, or it is worse than no scan.
REPO_FILE_SUFFIXES = (".txt", ".gui", ".yml")
REPO_ROOT = Path(__file__).resolve().parent.parent


LOC_KEY_PREFIXES = ("SNW_", "BC_", "SMART_NOTIFICATIONS_")


def shipped_file_names() -> set[str]:
    """Basenames of every script file this repo ships, across all its mods.
    `reference/` (pristine vanilla snapshots) and `tools/` are excluded --
    the game never loads either, so an error naming one is not ours."""
    names = set()
    for path in REPO_ROOT.rglob("*"):
        if (path.suffix in REPO_FILE_SUFFIXES
                and "reference" not in path.parts
                and "tools" not in path.parts
                and ".git" not in path.parts):
            names.add(path.name)
    return names
# This repo now hosts more than one mod (see better_decision_info/ and
# bulk_construction/), so the tag pattern covers every mod prefix in it:
# SNW_ for Smart Notifications, BC_ for Bulk Construction. A new sibling
# mod adds its prefix here, or its debug_log output is silently invisible
# to every tool and slash command that reads logs through this module.
MOD_TAG_PATTERN = r"(?:SNW|BC)_[A-Z_]+\|"

FILES_TO_SCAN = ["error.log", "debug.log"]


def scan_file(path: Path, lines_limit: int) -> tuple[list[str], list[str], list[str]]:
    if not path.exists():
        return [], [], []
    mod_tag_re = re.compile(MOD_TAG_PATTERN)
    error_re = re.compile("|".join(ENGINE_ERROR_PATTERNS))
    ours_re = re.compile("|".join(
        [re.escape(n) for n in sorted(shipped_file_names())]
        + [re.escape(pfx) for pfx in LOC_KEY_PREFIXES]))
    tagged, errors, ours = [], [], []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if mod_tag_re.search(line):
                tagged.append(line.rstrip())
                continue
            # Deliberately not `elif` against the error list: a line naming one
            # of our files is worth showing under its own heading even when it
            # also matches a known signature, because that heading is the one
            # that means "this is yours, not vanilla noise".
            if ours_re.search(line):
                ours.append(line.rstrip())
            elif error_re.search(line):
                errors.append(line.rstrip())
    return tagged[-lines_limit:], errors[-lines_limit:], ours[-lines_limit:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=20, help="max lines to show per file/category")
    ap.add_argument("--logs-dir", type=Path, default=DEFAULT_LOGS_DIR)
    ap.add_argument("--census", action="store_true",
                     help="Analyse a notification-census run (see tools/census_report.py).")
    ap.add_argument("--census-manifest", type=Path, default=None,
                     help="Override the census build's manifest location.")
    ap.add_argument("--top", type=int, default=30, help="--census: keys to rank.")
    ap.add_argument("--timeline", action="store_true",
                     help="--census: list every firing chronologically instead of "
                          "aggregating, to check the log against what was on screen.")
    ap.add_argument("--from-year", type=int, default=None)
    ap.add_argument("--to-year", type=int, default=None)
    ap.add_argument("--actor-axis", action="store_true",
                     help="Aggregate the SNW_A3 lines from the actor-axis probe "
                          "(07_smart_notifications_actor_axis_probe.txt) and report how "
                          "many of your toasts each candidate rule in TODO.md's open "
                          "question 3(a) would silence.")
    ap.add_argument("--coverage", type=Path, default=None,
                     help="Diff an observations file (what was actually on screen, from "
                          "feed screenshots) against what the census logged, and report "
                          "measured coverage. See tools/census_coverage.py.")
    ap.add_argument("--unfiltered", action="store_true",
                     help="Print ALL error.log lines (no pattern filter) -- use when checking "
                          "for something not on the known-pattern list, e.g. confirming a save "
                          "loads cleanly with the mod removed.")
    args = ap.parse_args()

    if not args.logs_dir.is_dir():
        print(f"Logs directory not found: {args.logs_dir}")
        print("Pass --logs-dir to point at your own Victoria 3/logs folder.")
        return

    if args.coverage:
        import census_coverage
        sys.exit(census_coverage.report(args.logs_dir, args.coverage))

    if args.actor_axis:
        import census_report
        sys.exit(census_report.actor_axis(args.logs_dir))

    if args.census:
        import census_report
        if args.timeline:
            sys.exit(census_report.timeline(args.logs_dir, args.census_manifest,
                                            args.from_year, args.to_year))
        sys.exit(census_report.report(args.logs_dir, args.census_manifest, args.top))

    if args.unfiltered:
        path = args.logs_dir / "error.log"
        print(f"=== error.log (unfiltered, last {args.lines} lines) ===")
        if not path.exists():
            print("  (not found)")
            return
        with path.open(encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if not lines:
            print("  (empty -- no errors logged at all)")
        for line in lines[-args.lines:]:
            print(f"    {line.rstrip()}")
        return

    for name in FILES_TO_SCAN:
        path = args.logs_dir / name
        tagged, errors, ours = scan_file(path, args.lines)
        print(f"=== {name} ===")
        if not path.exists():
            print("  (not found)")
            continue

        print(f"  Mod debug_log lines (SNW_*/BC_*), last {len(tagged)}:")
        if tagged:
            for line in tagged:
                print(f"    {line}")
        else:
            print("    (none found)")

        # First, and loudly: anything the engine blamed on one of our own
        # files, whether or not its wording is on the signature list.
        print(f"  !! Lines naming THIS REPO's own files, last {len(ours)}:")
        if ours:
            for line in ours:
                print(f"    {line}")
        else:
            print("    (none found)")

        print(f"  Known engine-error signatures, last {len(errors)}:")
        if errors:
            for line in errors:
                print(f"    {line}")
        else:
            print("    (none found)")
        print()


if __name__ == "__main__":
    main()
