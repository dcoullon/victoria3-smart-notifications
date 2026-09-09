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
import json
import shutil
import subprocess
import sys
from datetime import date
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

# The dev/test mod entry's metadata.json intentionally carries a
# " - Dev" suffix on its name (2026-09-09 per the user: the two entries
# looked confusingly identical in the launcher's upload flow). Since the
# dev junction points at this repo's real .metadata/metadata.json
# directly, that suffix has to be stripped back off for the actual
# packaged/published copy -- the public Workshop listing should never
# say "Dev".
DEV_NAME_SUFFIX = " - Dev"


def run_validation() -> bool:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "validate_syntax.py")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
    return result.returncode == 0


def strip_dev_name_suffix(metadata_path: Path):
    """Rewrite the staged metadata.json's `name` back to the real public
    name, removing the dev-only ' - Dev' suffix (see DEV_NAME_SUFFIX).
    Every other field (id, version, etc.) is left exactly as-is -- this
    is purely a display-name fix, never a `.json` file with a BOM (see
    docs/engine-notes.md § JSON files must not have a BOM -- read/write
    strictly as plain utf-8 here, deliberately not utf-8-sig)."""
    with open(metadata_path, encoding="utf-8") as f:
        meta = json.load(f)
    if meta.get("name", "").endswith(DEV_NAME_SUFFIX):
        meta["name"] = meta["name"][: -len(DEV_NAME_SUFFIX)]
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")


def package(out_dir: Path):
    """Stage the full copy in a sibling temp directory first, and only
    swap it into place once every folder has copied successfully --
    confirmed necessary 2026-09-09: an earlier version deleted-then-
    recreated each SHIP_DIR directly in `out_dir`, and a file lock
    (the Paradox Launcher watching that folder as a registered mod entry)
    mid-rmtree left the real output folder partially deleted and broken
    (common/alert_groups and common/alert_types gone, common/messages
    emptied) until the lock cleared. Staging first means a failure here
    leaves the PREVIOUS good output in `out_dir` untouched."""
    staging = out_dir.parent / (out_dir.name + "_staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    copied = []

    try:
        for name in SHIP_DIRS:
            src = REPO_ROOT / name
            if not src.is_dir():
                continue
            shutil.copytree(src, staging / name)
            copied.append(name + "/")

        for name in SHIP_FILES:
            src = REPO_ROOT / name
            if src.is_file():
                shutil.copy2(src, staging / name)
                copied.append(name)

        strip_dev_name_suffix(staging / ".metadata" / "metadata.json")
    except PermissionError as e:
        print(f"\nABORTED while staging: {e.filename} is locked by another "
              f"process. The existing output at {out_dir} was NOT touched. "
              f"Close the Paradox Launcher (and the game, if running) and try again.")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    failed = []
    for name in SHIP_DIRS + SHIP_FILES:
        src = staging / name
        if not src.exists():
            continue
        dst = out_dir / name
        try:
            if not dst.exists():
                shutil.move(str(src), str(dst))
            elif dst.is_dir():
                # Merge/overwrite into the EXISTING directory rather than
                # deleting it first -- confirmed real 2026-09-09: an empty
                # directory can be held by a transient handle (Windows
                # Search Indexer watching Documents for changes is the
                # common cause) that blocks rmdir/rmtree even with no
                # game/launcher running and no file inside actually
                # locked. dirs_exist_ok=True never needs to remove the
                # container, only write into it, sidestepping the whole
                # class of problem.
                shutil.copytree(src, dst, dirs_exist_ok=True)
                # Remove stale files/subdirs that exist in dst but not in
                # the freshly staged src (best-effort; a locked stale item
                # left behind harmlessly doesn't affect what the game
                # loads, so this never raises).
                src_names = {p.name for p in src.iterdir()}
                for existing in dst.iterdir():
                    if existing.name not in src_names:
                        try:
                            if existing.is_dir():
                                shutil.rmtree(existing)
                            else:
                                existing.unlink()
                        except PermissionError:
                            pass
                shutil.rmtree(src, ignore_errors=True)
            else:
                dst.unlink()
                shutil.move(str(src), str(dst))
        except PermissionError as e:
            failed.append((name, str(e.filename)))

    shutil.rmtree(staging, ignore_errors=True)
    if failed:
        print(f"\nPARTIAL SWAP into {out_dir}: the following were locked by "
              f"another process and NOT updated (old content there is still "
              f"intact, just stale):")
        for name, locked_file in failed:
            print(f"  - {name} (locked file: {locked_file})")
        print("Close the Paradox Launcher (and the game, if running) and "
              "re-run this script.")

    return copied, failed


def tag_release_commit() -> str | None:
    """Tag the current HEAD commit as `release-v<version>-<date>` so it's
    trivially findable later ("what did we actually package for external
    release on this date") -- separate from the per-version-bump `v<version>`
    tags (CLAUDE.md), since not every version bump gets externally
    released, and packaging can happen more than once for the same
    version. Returns the tag name, or None if it already existed."""
    with open(REPO_ROOT / ".metadata" / "metadata.json", encoding="utf-8") as f:
        version = json.load(f)["version"]
    tag = f"release-v{version}-{date.today().isoformat()}"

    existing = subprocess.run(["git", "tag", "-l", tag], cwd=REPO_ROOT,
                               capture_output=True, text=True).stdout.strip()
    if existing:
        return None

    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT,
                             capture_output=True, text=True).stdout.strip()
    if status:
        print("NOTE: working tree has uncommitted changes -- the tag will "
              "still point at the last commit, which may not include them.")

    subprocess.run(["git", "tag", "-a", tag, "-m", f"Packaged for release: version {version}"],
                    cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push", "origin", tag], cwd=REPO_ROOT,
                    capture_output=True, text=True)
    return tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-validation", action="store_true",
                     help="Not recommended -- skips the pre-package validate_syntax.py check.")
    ap.add_argument("--no-tag", action="store_true",
                     help="Skip creating the release-vX.Y-<date> git tag.")
    args = ap.parse_args()

    if not args.skip_validation:
        print("Validating source repo before packaging...")
        if not run_validation():
            print("\nABORTED: source repo failed validation. Fix the reported "
                  "issues before packaging a release (or pass --skip-validation "
                  "if you're certain).")
            sys.exit(1)

    copied, failed = package(args.out)

    print(f"\nPackaged to: {args.out}")
    print("Included:", ", ".join(copied) if copied else "(nothing found to copy)")
    if "thumbnail.png" not in copied:
        print("NOTE: no thumbnail.png at repo root -- required before uploading "
              "(see STORE_ASSETS_GUIDE.md).")

    if failed:
        print(f"\nDO NOT upload from {args.out} yet -- {len(failed)} item(s) "
              f"above are stale (locked during swap). Re-run after closing "
              f"whatever has them open.")
        sys.exit(1)

    if not args.no_tag:
        tag = tag_release_commit()
        if tag:
            print(f"Tagged and pushed: {tag} (so this exact state is easy to find/checkout later)")
        else:
            print("(A release tag for this version/date already exists -- skipped.)")

    print(
        "\nAdd this folder as its own mod entry in the Paradox Launcher's Mod "
        "Library (separate from your dev/test entry) and upload FROM there. "
        "Re-running this script only replaces the folders above -- any "
        "Steam/launcher bookkeeping already written into this output "
        "directory after a first upload is left untouched."
    )


if __name__ == "__main__":
    main()
