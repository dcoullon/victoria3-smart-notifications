"""
Build a clean, upload-only copy of the mod -- just the folders Victoria 3
actually loads -- separate from this dev repo's own tooling/docs.

Why this exists: the Paradox Launcher's Mod Tools "Upload Mod" packages
the ENTIRE directory a mod entry points at. The dev junction
(Documents/Paradox Interactive/Victoria 3/mod/smart_notifications) points
at this whole repo, so uploading straight from it would ship tools/,
docs/, reference/ (vanilla file snapshots), TODO.md, .git/, and every
other dev-only file to every subscriber. This script copies ONLY the real
mod content to a separate output directory, meant to be added as its own
(second, upload-only) mod entry in the launcher -- the existing dev
junction is untouched, so live-editing during testing keeps working
exactly as before.

Refuses to run if `tools/validate_syntax.py` fails on the source repo --
never package known-broken content.

Usage:
    python tools/package_release.py
    python tools/package_release.py --out "D:\\some\\other\\folder"

Default output: Documents/Paradox Interactive/Victoria 3/mod/smart_notifications_release
(a plain directory the launcher will pick up as a separate mod entry --
NOT a junction, a real copy, rebuilt each time this is run).

Only the specific SHIP_ITEMS subpaths are removed and replaced on each
run -- the rest of the output directory (e.g. any bookkeeping the
launcher or Steam itself writes there after a first upload) is left
alone, specifically so re-running this doesn't risk losing whatever
identifies "this is an update to the same Workshop item" rather than a
new one.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3" / "mod" / "smart_notifications_release"

# Everything Victoria 3 actually loads for this mod. Anything NOT listed
# here (tools/, docs/, reference/, .claude/, .git/, TODO.md, CHANGELOG.md,
# README.md, LICENSE, STORE_ASSETS_GUIDE.md,
# STEAM_WORKSHOP_DESCRIPTION.bbcode, DC-WIPthoughts.md, .gitignore) is
# deliberately excluded.
SHIP_DIRS = [".metadata", "common", "events", "gui", "localization"]
SHIP_FILES = ["thumbnail.png"]  # copied only if present


def run_validation() -> bool:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "validate_syntax.py")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
    return result.returncode == 0


def package(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    copied = []

    for name in SHIP_DIRS:
        src = REPO_ROOT / name
        dst = out_dir / name
        if not src.is_dir():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        copied.append(name + "/")

    for name in SHIP_FILES:
        src = REPO_ROOT / name
        if src.is_file():
            shutil.copy2(src, out_dir / name)
            copied.append(name)

    return copied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-validation", action="store_true",
                     help="Not recommended -- skips the pre-package validate_syntax.py check.")
    args = ap.parse_args()

    if not args.skip_validation:
        print("Validating source repo before packaging...")
        if not run_validation():
            print("\nABORTED: source repo failed validation. Fix the reported "
                  "issues before packaging a release (or pass --skip-validation "
                  "if you're certain).")
            sys.exit(1)

    copied = package(args.out)

    print(f"\nPackaged to: {args.out}")
    print("Included:", ", ".join(copied) if copied else "(nothing found to copy)")
    if "thumbnail.png" not in copied:
        print("NOTE: no thumbnail.png at repo root -- required before uploading "
              "(see STORE_ASSETS_GUIDE.md).")
    print(
        "\nAdd this folder as its own mod entry in the Paradox Launcher's Mod "
        "Library (separate from your dev/test entry) and upload FROM there. "
        "Re-running this script only replaces the folders above -- any "
        "Steam/launcher bookkeeping already written into this output "
        "directory after a first upload is left untouched."
    )


if __name__ == "__main__":
    main()
