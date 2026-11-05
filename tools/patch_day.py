"""Bring all three mods to the installed game version.

Report only, writes nothing:
    python tools/patch_day.py

Do it:
    python tools/patch_day.py --apply

On an open beta the game's number is not the release's, so name the release:
    python tools/patch_day.py --apply --target 1.16

What --apply does, in order:
  1. 3-way merges each full-file override (base: the old vanilla baseline,
     which is why this must run BEFORE anything refreshes that baseline;
     ours: the mod, theirs: the installed game). Any conflict stops the run
     before anything is written, because the old baseline is the merge base.
  2. Snapshots the game's text folders to C:/Users/damie/v3_snapshots/<version>.
  3. Refreshes reference/vanilla and renames it to the new version.
  4. Adds new laws to Smart Notifications (tools/add_sn_laws.py).
  5. Reruns every generator.
  6. Sets the game version in metadata, README, descriptions and dev tools.
  7. Runs strict validation.

It reports what still needs judgement: vanilla GUI types we shadow that changed
since the previous snapshot, and whatever the validator flags (replaced loc
keys, new message tiers). It commits nothing and bumps no mod version: both
wait for a test run. See reference/vanilla/README.md.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import check_references as cr

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
GAME = cr.VANILLA_ROOT
INSTALL = GAME.parent
SNAPSHOTS = Path(r"C:\Users\damie\v3_snapshots")
SNAPSHOT_DIRS = ("common", "events", "gui", "localization")
MODS = ("smart_notifications", "bulk_construction", "smart_trade")
SN = REPO / "smart_notifications"
CONFLICTS = Path(tempfile.gettempdir()) / "v3-patch-day-conflicts"
GENERATORS = ("gen_law_flag_clear.py", "gen_law_cooldown.py", "gen_sn_translations.py",
              "gen_smart_trade_values.py", "gen_smart_trade_gui.py")


def installed_version() -> str:
    settings = json.loads((INSTALL / "launcher" / "launcher-settings.json").read_text(encoding="utf-8"))
    return settings["rawVersion"]


def version_key(name: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", name))


def normalise(data: bytes) -> bytes:
    return data.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n")


def restore(merged: bytes, original: bytes) -> bytes:
    """Give merged text the BOM and line endings of the file it replaces."""
    if original.count(b"\r\n") * 2 > original.count(b"\n"):
        merged = merged.replace(b"\n", b"\r\n")
    return (b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b"") + merged


def merge_override(rel: str, base_dir: Path, tmp: Path) -> tuple[bytes | None, int, bool]:
    """Return (merged text restored for writing, conflict count, vanilla moved)."""
    ours_path = SN / rel
    original = ours_path.read_bytes()
    base = normalise((base_dir / rel).read_bytes())
    theirs = normalise((GAME / rel).read_bytes())
    if base == theirs:
        return None, 0, False
    name = Path(rel).name
    paths = {}
    for tag, data in (("ours", normalise(original)), ("base", base), ("theirs", theirs)):
        paths[tag] = tmp / f"{name}.{tag}"
        paths[tag].write_bytes(data)
    done = subprocess.run(["git", "merge-file", "-p", str(paths["ours"]), str(paths["base"]),
                           str(paths["theirs"])], capture_output=True)
    if done.returncode < 0 or done.returncode > 127:
        raise SystemExit(f"git merge-file failed on {rel}: {done.stderr.decode()[:200]}")
    if done.returncode > 0:
        CONFLICTS.mkdir(exist_ok=True)
        (CONFLICTS / name).write_bytes(done.stdout)
    return restore(done.stdout, original), done.returncode, True


def type_blocks(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    out = {}
    for m in re.finditer(r"(?m)^\s*type\s+(\w+)\s*=\s*[\w.]+\s*\{", text):
        i, depth, quoted = m.end(), 1, False
        while depth and i < len(text):
            ch = text[i]
            if ch == '"':
                quoted = not quoted
            elif not quoted:
                if ch == "#":
                    i = text.find("\n", i)
                    if i < 0:
                        break
                    continue
                depth += (ch == "{") - (ch == "}")
            i += 1
        out[m.group(1)] = text[m.start():i]
    return out


def gui_types(root: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in root.rglob("*.gui"):
        for name, body in type_blocks(path).items():
            found.setdefault(name, [line.strip() for line in body.splitlines() if line.strip()])
    return found


def previous_snapshot(version: str) -> Path | None:
    if not SNAPSHOTS.is_dir():
        return None
    older = [d for d in SNAPSHOTS.iterdir() if (d / "game" / "gui").is_dir() and d.name != version]
    older.sort(key=lambda d: version_key(d.name))
    return older[-1] / "game" if older else None


def shadowed_type_drift(version: str) -> list[str]:
    """Vanilla GUI types we redefine that changed between snapshots. Our copy
    keeps working but silently misses what the patch added."""
    previous = previous_snapshot(version)
    if previous is None:
        return ["no earlier snapshot to compare GUI types against"]
    old, new = gui_types(previous / "gui"), gui_types(GAME / "gui")
    drift = []
    for mod in MODS:
        for path in sorted((REPO / mod / "gui").glob("*.gui")):
            if (GAME / "gui" / path.name).is_file():
                continue  # a full-file override, handled by the merge
            for name in type_blocks(path):
                if name not in new:
                    if name in old:
                        drift.append(f"{mod}: vanilla removed type {name}")
                elif name in old and old[name] != new[name]:
                    drift.append(f"{mod}: vanilla changed type {name} ({previous.parent.name} to now)")
    return drift


def goods_in(root: Path) -> set[str]:
    text = re.sub(r"#[^\n]*", "", (root / "common/goods/00_goods.txt").read_text(encoding="utf-8-sig"))
    return set(re.findall(r"(?m)^(\w+)\s*=\s*\{", text))


def missing_laws() -> set[str]:
    laws = set()
    for path in (GAME / "common/laws").glob("*.txt"):
        laws.update(re.findall(r"(?m)^(law_\w+)\s*=\s*\{", path.read_text(encoding="utf-8-sig")))
    dispatch = SN / "common/on_actions/09_smart_notifications_law_ready_toast.txt"
    return laws - set(re.findall(r"law_type:(law_\w+)", dispatch.read_text(encoding="utf-8-sig")))


def new_goods(version: str) -> set[str]:
    """Against the last snapshot: the quantity table lists only goods that
    differ from the default rate, so it cannot show which goods are new."""
    previous = previous_snapshot(version)
    return goods_in(GAME) - goods_in(previous) if previous else set()


def refresh_baseline(base_dir: Path, target_minor: str) -> Path:
    new_dir = base_dir.parent / f"{target_minor}.x"
    if new_dir != base_dir:
        base_dir.rename(new_dir)
        readme = base_dir.parent / "README.md"
        readme.write_bytes(readme.read_bytes().replace(base_dir.name.encode(), new_dir.name.encode()))
    messages = new_dir / "common/messages"
    for old in messages.glob("*.txt"):
        old.unlink()
    for path in (GAME / "common/messages").glob("*.txt"):
        shutil.copyfile(path, messages / path.name)
    for rel, _ in cr.FULL_OVERRIDE_FILES:
        shutil.copyfile(GAME / rel, new_dir / rel)
    return new_dir


def snapshot(version: str):
    target = SNAPSHOTS / version / "game"
    for name in SNAPSHOT_DIRS:
        shutil.copytree(GAME / name, target / name, dirs_exist_ok=True)


# (file, pattern, replacement), %s being the minor version such as 1.15
VERSION_EDITS = [
    *[(f"{m}/.metadata/metadata.json", rb'("supported_game_version": ")[^"]*"', rb'\g<1>%s.*"') for m in MODS],
    *[(f"{m}/STEAM_WORKSHOP_DESCRIPTION.bbcode", rb"(\[b\]Game version:?(?:\[/b\])? )1\.\d+(\.\*)?",
       rb"\g<1>%s\g<2>") for m in MODS],
    ("smart_notifications/README.md", rb"(targeting game `)[^`]*`", rb"\g<1>%s.*`"),
    ("tools/build_census_mod.py", rb'("supported_game_version": ")[^"]*"', rb'\g<1>%s.*"'),
    ("tools/build_tick_probe.py", rb'("supported_game_version": ")[^"]*"', rb'\g<1>%s.*"'),
]


def set_versions(target_minor: str) -> list[str]:
    missed = []
    for rel, pattern, replacement in VERSION_EDITS:
        path = REPO / rel
        data = path.read_bytes()
        new, count = re.subn(pattern, replacement.replace(b"%s", target_minor.encode()), data)
        if count == 0:
            missed.append(rel)
        elif new != data:
            path.write_bytes(new)
    return missed


def run(script: str, *args: str) -> bool:
    done = subprocess.run([sys.executable, str(TOOLS / script), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if done.returncode:
        print(f"  {script} failed:\n{(done.stdout + done.stderr)[-1500:]}")
    return done.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bring all mods to the installed game version.")
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--target", help="release version on a beta, such as 1.16")
    args = parser.parse_args()

    version = installed_version()
    target = args.target or ".".join(version.split(".")[:2])
    base_dir = cr.BASELINE_DIR
    declared = json.loads((REPO / "smart_trade/.metadata/metadata.json").read_text(encoding="utf-8"))
    print(f"Game {version}, target {target}.*, mods declare "
          f"{declared['supported_game_version']}, baseline {base_dir.name}\n")

    print("Overrides (3-way merge):")
    merged, conflicts = {}, 0
    with tempfile.TemporaryDirectory() as tmp:
        for rel, _ in cr.FULL_OVERRIDE_FILES:
            result, count, moved = merge_override(rel, base_dir, Path(tmp))
            state = "unchanged in vanilla" if not moved else f"{count} conflict(s)" if count else "merges cleanly"
            print(f"  {rel}: {state}")
            conflicts += count
            if moved and not count:
                merged[rel] = result

    print(f"\nLaws missing from Smart Notifications: {sorted(missing_laws()) or 'none'}")
    print(f"New goods since the last snapshot: {sorted(new_goods(version)) or 'none'}")
    drift = shadowed_type_drift(version)
    print("\nShadowed GUI types vanilla changed (check each is ported):")
    print("\n".join(f"  {line}" for line in drift) or "  none")

    if not args.apply:
        print("\nReport only. Rerun with --apply to write.")
        return 1 if conflicts else 0
    if conflicts:
        print(f"\nSTOPPED: {conflicts} conflict(s), nothing written. Markers are in {CONFLICTS}.")
        return 1

    print("\nApplying:")
    for rel, data in merged.items():
        (SN / rel).write_bytes(data)
    snapshot(version)
    print(f"  snapshot at {SNAPSHOTS / version}")
    new_dir = refresh_baseline(base_dir, target)
    print(f"  baseline now {new_dir.name}")
    ok = run("add_sn_laws.py")
    for script in GENERATORS:
        ok = run(script) and ok
    missed = set_versions(target)
    if missed:
        print(f"  version text not found in: {', '.join(missed)}")
    ok = run("validate_syntax.py", "--strict") and ok and not missed

    print("\nDone with no failures." if ok else "\nDone, but see the failures above.")
    print("Still yours: port any GUI type listed above, re-derive any replaced loc key the\n"
          "validator named, run dump_data_types in game, test, then bump and package.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
