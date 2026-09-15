"""
Static catalog of every vanilla notification: key, group, tier, where it is
fired from, and its localized title/description templates.

Needs no game session. Everything here is read off the installed game's files,
so it answers "what text does this notification show" and "which keys can we
never instrument" without a playtest.

Two things it is NOT:
  - It does not count firings. That is the census run's job.
  - The loc it extracts are TEMPLATES, still carrying `[SCOPE...]` dynamic-text
    calls. The scope-filled rendering only exists at runtime inside the engine;
    see docs/engine-notes.md on why script cannot read it back.

Usage:
    python tools/message_catalog.py                 # summary + write JSON
    python tools/message_catalog.py --engine-fired  # the unmeasurable keys
    python tools/message_catalog.py --json PATH
"""
import argparse
import collections
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")

ENTRY_RE = re.compile(r"^(\w+)\s*=\s*\{\n(.*?)\n\}", re.MULTILINE | re.DOTALL)
GROUP_RE = re.compile(r'group\s*=\s*"([^"]+)"')
NTYPE_RE = re.compile(r"notification_type\s*=\s*(\w+)")
CALL_RE = re.compile(r"post_notification\s*=\s*(\w+)")
COMMENT_RE = re.compile(r"#.*")
# `key: "value"` or `key:0 "value"` -- the version number is optional in Jomini
LOC_RE = re.compile(r'^\s*([A-Za-z0-9_.]+)\s*:\s*\d*\s*"(.*)"\s*$')


def read(path: Path) -> str:
    return COMMENT_RE.sub("", path.read_text(encoding="utf-8-sig", errors="replace"))


def load_messages(game_root: Path) -> dict:
    """key -> {group, tier, defined_in}."""
    out = {}
    for f in sorted((game_root / "common" / "messages").glob("*.txt")):
        for key, body in ENTRY_RE.findall(read(f)):
            g, n = GROUP_RE.search(body), NTYPE_RE.search(body)
            out[key] = {
                "key": key,
                "group": g.group(1) if g else None,
                "tier": n.group(1) if n else None,
                "defined_in": f.name,
            }
    return out


def load_call_sites(game_root: Path) -> dict:
    """key -> sorted list of relative paths that post it."""
    sites = collections.defaultdict(set)
    for sub in ("common", "events"):
        base = game_root / sub
        if not base.is_dir():
            continue
        for f in base.rglob("*.txt"):
            try:
                text = f.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            if "post_notification" not in text:
                continue
            rel = f.relative_to(game_root).as_posix()
            for key in CALL_RE.findall(COMMENT_RE.sub("", text)):
                sites[key].add(rel)
    return {k: sorted(v) for k, v in sites.items()}


def load_loc(game_root: Path) -> dict:
    """loc key -> raw template string, across every english loc file."""
    out = {}
    base = game_root / "localization" / "english"
    for f in base.rglob("*.yml"):
        try:
            lines = f.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            m = LOC_RE.match(line)
            if m:
                out.setdefault(m.group(1), m.group(2))
    return out


def build(game_root: Path) -> list:
    messages = load_messages(game_root)
    sites = load_call_sites(game_root)
    loc = load_loc(game_root)

    catalog = []
    for key, rec in sorted(messages.items()):
        call_sites = sites.get(key, [])
        rec = dict(rec)
        rec["call_sites"] = call_sites
        rec["engine_fired"] = not call_sites
        # Where the call sites live decides whether we can instrument it safely.
        if not call_sites:
            rec["reach"] = "engine-fired"
        elif all(s.startswith("common/on_actions/") for s in call_sites):
            rec["reach"] = "on_actions"       # safe append, no vanilla file touched
        elif any(s.startswith("events/") for s in call_sites):
            rec["reach"] = "events"
        else:
            rec["reach"] = "other-common"
        for part in ("name", "desc", "tooltip"):
            rec[f"loc_{part}"] = loc.get(f"notification_{key}_{part}")
        catalog.append(rec)
    return catalog


def readable(raw):
    """Flatten a loc template into something a human can scan.

    Dynamic `[SCOPE...]` calls become `<>` rather than vanishing, so the text
    stays honestly incomplete instead of looking like the whole string.
    """
    if not raw:
        return ""
    text = re.sub(r"\[[^\]]*\]", "<>", raw)
    text = re.sub(r"\$([^$]*)\$", lambda m: m.group(1), text)
    text = re.sub(r"#[a-zA-Z_]+ |#!", "", text)
    # Loc strings carry a literal backslash-n as their line break, not a real
    # newline, so replace both spellings and collapse the whitespace it leaves.
    text = text.replace("\\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def write_markdown(catalog, path):
    """The engine-fired keys as a readable reference document."""
    rows = [r for r in catalog if r["engine_fired"]]
    by_tier = collections.defaultdict(list)
    for r in rows:
        by_tier[r["tier"]].append(r)

    out = ["﻿# Engine-fired notifications — the keys we can never count", "",
           "**Generated by `python tools/message_catalog.py --markdown`. Do not hand-edit.**",
           "",
           f"{len(rows)} of {len(catalog)} vanilla notification keys have **no "
           "`post_notification` call site anywhere** in `common/` or `events/`. The "
           "engine posts them directly, so there is nothing to hook and no way to "
           "instrument them. Confirmed by exhaustive scan of the installed game, "
           "recomputed on every run of the tool rather than quoted from a doc.",
           "",
           "**Engine-fired means uncountable, not uncontrollable.** `notification_type` "
           "still applies to every key here, so the mod and the hand-tuning "
           "recommendations both work on them. Only the census cannot count them — "
           "which is why every published figure is a lower bound.",
           "",
           "Text shown is the localized title (or the description where the title is "
           "almost all substitution). `<>` marks a dynamic part that only resolves "
           "in-engine.",
           ""]
    for tier in ("popup", "toast", "feed", "none"):
        group = by_tier.get(tier, [])
        if not group:
            continue
        out.append(f"## {tier} ({len(group)})")
        out.append("")
        out.append("| key | what the player sees |")
        out.append("|---|---|")
        for r in sorted(group, key=lambda r: r["key"]):
            text = readable(r["loc_name"])
            if len(text.replace("<>", "").strip()) < 6:
                text = readable(r["loc_desc"]).split(". ")[0] or text
            out.append(f"| `{r['key']}` | {text.replace('|', '\|') or '(no loc)'} |")
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-root", type=Path, default=GAME_ROOT)
    ap.add_argument("--json", type=Path,
                    default=REPO_ROOT / "tools" / "message_catalog.json")
    ap.add_argument("--markdown", type=Path, nargs="?",
                    const=REPO_ROOT / "docs" / "engine-fired-keys.md",
                    help="write the engine-fired keys as a readable markdown doc")
    ap.add_argument("--engine-fired", action="store_true",
                    help="print the keys with no script call site anywhere")
    args = ap.parse_args()

    if not args.game_root.is_dir():
        raise SystemExit(f"vanilla install not found at {args.game_root}")

    catalog = build(args.game_root)
    args.json.write_text(json.dumps(catalog, indent=1, ensure_ascii=False),
                         encoding="utf-8")

    print(f"vanilla notification keys: {len(catalog)}")
    print("  by reach:", dict(collections.Counter(r["reach"] for r in catalog)))
    print("  by tier :", dict(collections.Counter(r["tier"] for r in catalog)))
    missing_name = [r["key"] for r in catalog if not r["loc_name"]]
    print(f"  with a localized title: {len(catalog) - len(missing_name)}/{len(catalog)}")
    if missing_name:
        print(f"  no notification_<key>_name loc: {len(missing_name)}")
    print(f"  written: {args.json}")

    if args.markdown:
        n = write_markdown(catalog, args.markdown)
        print(f"  markdown: {args.markdown} ({n} engine-fired keys)")

    if args.engine_fired:
        rows = [r for r in catalog if r["engine_fired"]]
        print(f"\n=== ENGINE-FIRED: {len(rows)} keys, no call site in common/ or events/ ===")
        by_tier = collections.defaultdict(list)
        for r in rows:
            by_tier[r["tier"]].append(r)
        for tier in ("popup", "toast", "feed", "none"):
            group = by_tier.get(tier, [])
            if not group:
                continue
            print(f"\n--- {tier.upper()} ({len(group)}) ---")
            for r in group:
                title = (r["loc_name"] or "(no loc)")
                title = re.sub(r"\[[^\]]*\]", "<>", title)
                title = re.sub(r"\$[^$]*\$", lambda m: m.group(0).strip("$"), title)
                print(f"  {r['key']:52} {title[:58]}")


if __name__ == "__main__":
    main()
