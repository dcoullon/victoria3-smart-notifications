"""What is actually live on the Steam Workshop, versus what is in this repo?

The reliable answer is not the Workshop web page and not memory of having
clicked upload: when you are subscribed to your own item, Steam downloads the
published files back to disk. Those files ARE the published mod, so this reads
their metadata.json directly. That is evidence, not inference.

    python tools/published_version.py           # version comparison
    python tools/published_version.py --files   # also compare the file lists

Reports three things and how they relate:
  repo      -- .metadata/metadata.json on this branch
  packaged  -- what package_release.py last built, ready to upload
  published -- what Steam has actually downloaded back from the Workshop
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKAGED = (Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3"
            / "mod" / "smart_notifications_release")
# Workshop file ID 3799284646, Victoria 3 App ID 529340.
PUBLISHED = Path(r"C:\Program Files (x86)\Steam\steamapps\workshop\content\529340\3799284646")
SHIP_DIRS = [".metadata", "common", "events", "gui", "localization"]


def read(root: Path) -> tuple[str | None, str | None]:
    meta = root / ".metadata" / "metadata.json"
    if not meta.is_file():
        return None, None
    try:
        version = json.loads(meta.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None, None
    when = datetime.fromtimestamp(meta.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return version, when


def files_of(root: Path) -> set[str]:
    out = set()
    for d in SHIP_DIRS:
        base = root / d
        if base.is_dir():
            out |= {str(p.relative_to(root)).replace("\\", "/")
                    for p in base.rglob("*") if p.is_file()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", action="store_true",
                    help="also compare the shipped file lists")
    a = ap.parse_args()

    rows = [("repo", REPO), ("packaged", PACKAGED), ("published", PUBLISHED)]
    seen = {}
    for label, root in rows:
        version, when = read(root)
        seen[label] = version
        if version is None:
            print(f"  {label:10s} not found at {root}")
        else:
            print(f"  {label:10s} v{version:<8s} ({when})")

    print()
    if seen["published"] is None:
        print("VERDICT: cannot tell -- Steam has no downloaded copy of the item here.")
        print("  Subscribe to your own Workshop item so Steam keeps a copy on disk,")
        print("  or check the item page's Change Notes by hand.")
        return 1
    if seen["repo"] == seen["published"]:
        print(f"VERDICT: v{seen['published']} is LIVE and matches this branch.")
    else:
        print(f"VERDICT: live is v{seen['published']}, this branch is v{seen['repo']}"
              " -- the repo is ahead, an upload is pending.")
        print("  Build it with: python tools/package_release.py")
        print("  Then upload from the smart_notifications_release folder, never the dev junction.")

    if a.files:
        pub, pack = files_of(PUBLISHED), files_of(PACKAGED)
        print("\nfile lists (published vs packaged):")
        for name, diff in (("only published", pub - pack), ("only packaged", pack - pub)):
            print(f"  {name}: {len(diff)}")
            for f in sorted(diff)[:20]:
                print(f"    {f}")
        print(f"  in both: {len(pub & pack)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
