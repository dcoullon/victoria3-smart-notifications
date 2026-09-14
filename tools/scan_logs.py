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
]
MOD_TAG_PATTERN = r"SNW_[A-Z_]+\|"

FILES_TO_SCAN = ["error.log", "debug.log"]


def scan_file(path: Path, lines_limit: int) -> tuple[list[str], list[str]]:
    if not path.exists():
        return [], []
    mod_tag_re = re.compile(MOD_TAG_PATTERN)
    error_re = re.compile("|".join(ENGINE_ERROR_PATTERNS))
    tagged, errors = [], []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if mod_tag_re.search(line):
                tagged.append(line.rstrip())
            elif error_re.search(line):
                errors.append(line.rstrip())
    return tagged[-lines_limit:], errors[-lines_limit:]


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
    ap.add_argument("--unfiltered", action="store_true",
                     help="Print ALL error.log lines (no pattern filter) -- use when checking "
                          "for something not on the known-pattern list, e.g. confirming a save "
                          "loads cleanly with the mod removed.")
    args = ap.parse_args()

    if not args.logs_dir.is_dir():
        print(f"Logs directory not found: {args.logs_dir}")
        print("Pass --logs-dir to point at your own Victoria 3/logs folder.")
        return

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
        tagged, errors = scan_file(path, args.lines)
        print(f"=== {name} ===")
        if not path.exists():
            print("  (not found)")
            continue

        print(f"  Mod debug_log lines (SNW_*), last {len(tagged)}:")
        if tagged:
            for line in tagged:
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
