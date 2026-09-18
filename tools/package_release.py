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

This repo hosts one folder per mod, each with its own `.metadata/metadata.json`.
Which one gets packaged is the first argument, and it is required -- with
several mods in one repo, defaulting to any of them is how you upload the
wrong one.

Usage:
    python tools/package_release.py smart_notifications
    python tools/package_release.py bulk_construction
    python tools/package_release.py --out "D:\\some\\other\\folder"

Default output: Documents/Paradox Interactive/Victoria 3/mod/<mod id>_release
-- so `smart_notifications_release` as before, and `bulk_construction_release`
for that mod. A plain directory the launcher will pick up as a separate mod
entry -- NOT a junction, a real copy, rebuilt each time this is run.

Before this took a mod argument it read every shipped folder from the repo
root unconditionally, so asking it for a sibling mod silently staged Smart
Notifications' `common/`, `gui/`, `events/` and `localization/` under the
sibling's name -- i.e. it would have uploaded the wrong mod, quietly, at the
one moment that is hardest to undo.

Only the specific SHIP_ITEMS subpaths are removed and replaced on each
run -- the rest of the output directory (e.g. any bookkeeping the
launcher or Steam itself writes there after a first upload) is left
alone, specifically so re-running this doesn't risk losing whatever
identifies "this is an update to the same Workshop item" rather than a
new one.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import check_references

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_DIR = Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3" / "mod"


def resolve_mod_root(arg: str | None) -> Path:
    """Which mod in this repo to package. Required: the repo root stopped
    being a mod in the 2026-09-16 restructure, and with three mods in one repo
    a default is how you upload the wrong one.

    A bare name like `bulk_construction` is resolved against the repo root, so
    the command reads the same from anywhere; an explicit path still works.
    Anything without a `.metadata/metadata.json` is refused outright rather
    than packaged as an empty mod -- a typo'd folder name would otherwise
    produce a valid-looking output directory with nothing in it."""
    if arg is None:
        # The repo root stopped being a mod in the 2026-09-16 restructure, so
        # there is no sensible default any more. Naming the mod explicitly is
        # also the safer habit with three of them: the failure this whole
        # argument exists to prevent is packaging the wrong one.
        known = sorted(p.parent.parent.name
                       for p in REPO_ROOT.glob("*/.metadata/metadata.json"))
        example = known[0] if known else "<mod>"
        print("ABORTED: name the mod to package, e.g.")
        print(f"    python tools/package_release.py {example}")
        print(f"Mods in this repo: {', '.join(known)}")
        sys.exit(1)
    candidate = Path(arg)
    if not candidate.is_dir():
        candidate = REPO_ROOT / arg
    candidate = candidate.resolve()
    if not (candidate / ".metadata" / "metadata.json").is_file():
        known = [REPO_ROOT.name] + [p.name for p in check_references.nested_mod_roots(REPO_ROOT)]
        print(f"ABORTED: {candidate} is not a mod root -- no .metadata/metadata.json there.\n"
              f"Mods in this repo: {', '.join(known)}")
        sys.exit(1)
    return candidate


def default_out_for(mod_root: Path) -> Path:
    """`<mod id>_release`, next to the launcher's other mod entries. Derived
    from the packaged mod's own id rather than hardcoded, so two mods cannot
    end up sharing one output folder and overwriting each other."""
    mod_id = check_references.read_mod_id(mod_root)
    if not mod_id:
        print(f"ABORTED: {mod_root}/.metadata/metadata.json has no `id`.")
        sys.exit(1)
    return MOD_DIR / f"{mod_id}_release"

# Everything Victoria 3 actually loads for this mod. Anything NOT listed
# here (tools/, docs/, reference/, .claude/, .git/, TODO.md, CHANGELOG.md,
# README.md, LICENSE, STORE_ASSETS_GUIDE.md,
# STEAM_WORKSHOP_DESCRIPTION.bbcode, DC-WIPthoughts.md, .gitignore) is
# deliberately excluded.
SHIP_DIRS = [".metadata", "common", "events", "gui", "localization"]
SHIP_FILES = ["thumbnail.png"]  # copied only if present

# Files that exist ONLY to diagnose this mod during development. Every one of
# them posts zero notifications -- they exist to write debug_log lines -- so
# once logging is stripped from a release they would ship as on_action handlers
# with empty bodies. Between them that is 70 vanilla on_actions this mod would
# hook, and the game would call every one of them, forever, to do nothing.
#
# Counted 2026-09-10 while reviewing for the first public release:
#   01_smart_notifications_logger.txt          32 hooks, 0 post_notification
#   04_smart_notifications_probes.txt          10 hooks, 0 post_notification
#   05_smart_notifications_toast_popup_audit.txt  28 hooks, 0 post_notification
#
# They stay in the repo -- they are how this mod gets diagnosed without asking
# the user to watch for toasts -- and are simply not copied into a release.
# Single source of truth, shared with the validator: check_references.py also
# asserts this list against the `# DEV-ONLY` markers in the files themselves,
# so a probe that never made it into the list fails an ordinary
# `validate_syntax.py` run rather than quietly shipping.
DEV_ONLY_FILES = check_references.DEV_ONLY_FILES

# The dev/test mod entry's metadata.json intentionally carries a
# " - Dev" suffix on its name (2026-09-09 per the user: the two entries
# looked confusingly identical in the launcher's upload flow). Since the
# dev junction points at this repo's real .metadata/metadata.json
# directly, that suffix has to be stripped back off for the actual
# packaged/published copy -- the public Workshop listing should never
# say "Dev".
DEV_NAME_SUFFIX = " - Dev"


def run_validation(mod_root: Path) -> bool:
    """Validate the mod being packaged, not the repo. Passing the mod root
    explicitly also selects the right per-mod checks inside the validator,
    which gate on the mod id found there (see check_references.run_all).

    `--strict` because this is the release path: CLAUDE.md section 4 says a
    DEGRADED pass -- one where the vanilla-comparison checks were skipped
    because the game is not installed on this machine -- is not a pass, and a
    release is exactly the moment that distinction matters."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "validate_syntax.py"),
         str(mod_root), "--strict"],
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


# Matches a debug_log / debug_log_scopes call anywhere on a line. The string
# argument never contains an escaped quote in this mod, so a non-greedy
# quoted run is enough; debug_log_scopes takes a bare yes/no instead.
DEBUG_CALL_RE = re.compile(r'\bdebug_log\s*=\s*"[^"]*"|\bdebug_log_scopes\s*=\s*\w+')


def drop_dev_only_files(staging: Path, mod_id: str) -> list[str]:
    """Remove the diagnostic-only files from the packaged copy entirely.
    Stripping their debug_log lines is not enough -- what would remain is a
    pile of empty on_action handlers the game still calls.

    DEV_ONLY_FILES is a hand-maintained list of Smart Notifications' own
    paths, so it is gated on the mod id rather than left to miss by accident:
    a sibling mod with a same-named file would otherwise have it silently
    dropped from its release."""
    if mod_id != check_references.SMART_NOTIFICATIONS_ID:
        return []
    dropped = []
    for rel in DEV_ONLY_FILES:
        p = staging / rel
        if p.is_file():
            p.unlink()
            dropped.append(rel)
    return dropped


def strip_debug_logging(staging: Path) -> int:
    """Remove every `debug_log` / `debug_log_scopes` line from the packaged
    copy. The dev tree keeps them -- they are how this mod gets diagnosed
    without asking the user to watch for toasts -- but players should not pay
    for them.

    Why it matters, measured rather than assumed: one session with the
    per-participant taps still in place emitted 10,822 log lines and rotated
    through five 512KB debug.log files, and the user reported the game slowing
    noticeably during a large diplomatic play. Every one of those lines is a
    string built and formatted at runtime, several with dynamic-text lookups
    (`[SCOPE.sC('actor').GetNameNoFormatting]`), inside on_actions that fire
    once per involved country.

    Line-based on purpose. Every debug_log in this mod occupies exactly one
    line, so removing whole lines cannot unbalance braces -- and the packaged
    output is re-validated afterwards, which is what actually proves it. A
    block left empty by the removal (`else = { }`) is valid script and simply
    does nothing, which is the intent.
    """
    removed = 0
    for path in sorted(staging.rglob("*.txt")):
        raw = path.read_bytes()
        had_bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        out, n = [], 0
        for line in text.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(("debug_log =", "debug_log=",
                                    "debug_log_scopes =", "debug_log_scopes=")):
                # A line that is nothing but a log call: drop it whole.
                n += 1
                continue
            # A log call sitting INSIDE a one-line compound statement, e.g.
            #   if = { limit = { ... } THIS.owner = { ... } debug_log = "..." }
            # The generated per-law file is written this way, and a purely
            # line-based strip left 138 of them in the shipped build -- found
            # 2026-09-10 by counting the packaged output rather than trusting
            # the strip. Remove just the call, keeping the braces around it.
            new_line, k = DEBUG_CALL_RE.subn("", line)
            if k:
                n += k
                # Collapse the double space the removal leaves behind.
                new_line = re.sub(r"[ \t]{2,}", " ", new_line).rstrip()
                if not new_line.strip():
                    continue
                line = new_line
            out.append(line)
        if not n:
            continue
        body = "\n".join(out)
        path.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + body.encode("utf-8"))
        removed += n
    return removed


def validate_staging(staging: Path) -> bool:
    """Re-run the validator against the STAGED copy, after stripping. Catches
    the one way stripping could go wrong -- a removal that leaves something
    the game will not parse -- before it reaches the output folder, while the
    previous good release is still untouched."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "validate_syntax.py"), str(staging)],
        capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result.returncode == 0


def package(mod_root: Path, out_dir: Path):
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
            src = mod_root / name
            if not src.is_dir():
                continue
            shutil.copytree(src, staging / name)
            copied.append(name + "/")

        for name in SHIP_FILES:
            src = mod_root / name
            if src.is_file():
                shutil.copy2(src, staging / name)
                copied.append(name)

        strip_dev_name_suffix(staging / ".metadata" / "metadata.json")

        dropped = drop_dev_only_files(staging, check_references.read_mod_id(mod_root))
        for rel in dropped:
            print(f"Excluded dev-only file: {rel}")

        stripped = strip_debug_logging(staging)
        print(f"Stripped {stripped} debug logging line(s) from the packaged copy.")
        if not validate_staging(staging):
            print("\nABORTED: the packaged copy failed validation AFTER debug "
                  "logging was stripped. The existing output was NOT touched. "
                  "This means a removed line was load-bearing -- fix it in the "
                  "source repo before packaging again.")
            shutil.rmtree(staging, ignore_errors=True)
            sys.exit(1)
    except PermissionError as e:
        print(f"\nABORTED while staging: {e.filename} is locked by another "
              f"process. The existing output at {out_dir} was NOT touched. "
              f"Close the Paradox Launcher (and the game, if running) and try again.")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    failed = []
    for name in SHIP_DIRS + SHIP_FILES:
        src = staging / name
        dst = out_dir / name
        if not src.exists():
            # The mod no longer ships this item at all. The stale-item sweep
            # below never sees that case -- it only runs INSIDE a directory
            # that was staged -- so before 2026-09-18 a whole shipped
            # directory dropped from a mod kept shipping forever. Found the
            # day Bulk Construction lost its `common/`: the previous release
            # folder still held the inert scripted GUI this cleanup exists to
            # remove, and re-running the packager would not have taken it out.
            # Same failure as the 2026-09-10 recursive fix below, one level up.
            if dst.exists():
                try:
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                    print(f"  Removed {name} -- this mod no longer ships it")
                except PermissionError:
                    failed.append(f"{name} (stale, still locked)")
            continue
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
                #
                # RECURSIVE since 2026-09-10. This used to compare only the
                # top level of each shipped directory, so a file removed from
                # the mod at any depth below that kept shipping forever --
                # found when three diagnostic-only files were excluded from the
                # release and reappeared in the output regardless, because they
                # live at common/on_actions/ rather than directly under
                # common/. A stale on_action file the game still loads is
                # exactly the kind of thing nobody would think to look for.
                stale = []
                for existing in dst.rglob("*"):
                    counterpart = src / existing.relative_to(dst)
                    if not counterpart.exists():
                        stale.append(existing)
                # Deepest first, so a directory is emptied before it is removed.
                for existing in sorted(stale, key=lambda p: len(p.parts), reverse=True):
                    try:
                        if existing.is_dir():
                            shutil.rmtree(existing)
                        elif existing.exists():
                            existing.unlink()
                    except PermissionError:
                        pass
                if stale:
                    print(f"  Removed {len(stale)} stale item(s) from {name}/ "
                          f"left over from a previous package.")
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


def tag_release_commit(mod_root: Path) -> str | None:
    """Tag the current HEAD commit as `release-v<version>-<date>` so it's
    trivially findable later ("what did we actually package for external
    release on this date") -- separate from the per-version-bump `v<version>`
    tags (CLAUDE.md), since not every version bump gets externally
    released, and packaging can happen more than once for the same
    version. Returns the tag name, or None if it already pointed at HEAD
    or was moved onto it.

    The version comes from the mod being packaged. A sibling mod's tag also
    carries its id (`release-bulk_construction-v0.01-<date>`): one git repo
    holds all three mods, so without it two mods released on the same day at
    the same version number would collide on one tag. The root mod's tag
    format is left exactly as it was, so existing tags stay consistent."""
    with open(mod_root / ".metadata" / "metadata.json", encoding="utf-8") as f:
        version = json.load(f)["version"]
    mod_id = check_references.read_mod_id(mod_root)
    scope = "" if mod_id == check_references.SMART_NOTIFICATIONS_ID else f"{mod_id}-"
    tag = f"release-{scope}v{version}-{date.today().isoformat()}"

    # If the tag already exists but points somewhere else, MOVE it. This tag
    # answers "what did we actually release on this date", so when a mod is
    # packaged several times in one day -- which is the normal shape of a
    # release day -- the answer is the last packaging, not the first.
    #
    # It used to return None instead, leaving the tag on the earliest build
    # of the day. Found 2026-09-18, after Build All was packaged four times
    # and published: the tag pointed at a build from that morning, three
    # commits of shipped content out of date, so the one tag whose entire
    # purpose is reproducing a release reproduced something never released.
    existing = subprocess.run(["git", "tag", "-l", tag], cwd=REPO_ROOT,
                               capture_output=True, text=True).stdout.strip()
    moved_from = None
    if existing:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True).stdout.strip()
        tagged = subprocess.run(["git", "rev-list", "-n1", tag], cwd=REPO_ROOT,
                                capture_output=True, text=True).stdout.strip()
        if tagged == head:
            return None
        moved_from = tagged[:7]

    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT,
                             capture_output=True, text=True).stdout.strip()
    if status:
        print("NOTE: working tree has uncommitted changes -- the tag will "
              "still point at the last commit, which may not include them.")

    subprocess.run(["git", "tag", "-f", "-a", tag,
                    "-m", f"Packaged for release: version {version}"],
                    cwd=REPO_ROOT, check=True)
    subprocess.run(["git", "push", "--force", "origin", tag], cwd=REPO_ROOT,
                    capture_output=True, text=True)
    if moved_from:
        print(f"Moved {tag} from {moved_from} to HEAD "
              f"(repackaged the same day -- the tag tracks the LAST build).")
        return None
    return tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", nargs="?", default=None,
                     help="Which mod in this repo to package: a folder name like "
                          "bulk_construction, or a path. Defaults to the repo root "
                          "(Smart Notifications).")
    ap.add_argument("--out", type=Path, default=None,
                     help="Output directory. Defaults to "
                          "Documents/Paradox Interactive/Victoria 3/mod/<mod id>_release.")
    ap.add_argument("--skip-validation", action="store_true",
                     help="Not recommended -- skips the pre-package validate_syntax.py check.")
    ap.add_argument("--no-tag", action="store_true",
                     help="Skip creating the release-vX.Y-<date> git tag.")
    args = ap.parse_args()

    mod_root = resolve_mod_root(args.mod)
    out_dir = args.out if args.out is not None else default_out_for(mod_root)
    mod_name = check_references.read_mod_id(mod_root)

    print(f"Packaging mod: {mod_name}  (from {mod_root})")

    if not args.skip_validation:
        print("Validating the mod before packaging...")
        if not run_validation(mod_root):
            print("\nABORTED: the mod failed validation. Fix the reported "
                  "issues before packaging a release (or pass --skip-validation "
                  "if you're certain).")
            sys.exit(1)

    copied, failed = package(mod_root, out_dir)

    print(f"\nPackaged to: {out_dir}")
    print("Included:", ", ".join(copied) if copied else "(nothing found to copy)")
    if "thumbnail.png" not in copied:
        print(f"NOTE: no thumbnail.png in {mod_root} -- required before uploading "
              "(see STORE_ASSETS_GUIDE.md).")

    if failed:
        print(f"\nDO NOT upload from {out_dir} yet -- {len(failed)} item(s) "
              f"above are stale (locked during swap). Re-run after closing "
              f"whatever has them open.")
        sys.exit(1)

    if not args.no_tag:
        tag = tag_release_commit(mod_root)
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
