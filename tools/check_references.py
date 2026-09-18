"""
Cross-file reference integrity checks for the Smart Notifications mod.

Added 2026-09-08 per the user: "add tests into your code so we know it's
still working without relying on me testing it all the time." This cannot
replace live testing -- there is no way to execute Jomini script logic
outside the actual game -- but every check here targets a bug class this
project actually hit and had to diagnose live, one at a time, in previous
sessions. Turning each into a static, repeatable check means the NEXT
occurrence of the same mistake is caught by running this script, not by
the user reporting a blank/broken alert in-game.

Run via `python tools/validate_syntax.py` (wired in automatically) or
standalone: `python tools/check_references.py`.

Each `check_*` function returns a list of human-readable error strings
(empty list = pass) and never raises for a normal missing-reference case.
"""
import json
import re
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".gui"}
VANILLA_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")

# This repo holds one folder per mod, with docs/, reference/ and tools/ shared
# at the top. Checks that inspect a MOD resolve from the `root` they are given;
# checks that inspect the REPO (the engine-notes TOC, the vanilla snapshot,
# the census build) must resolve from here instead.
#
# Smart Notifications used to live at the repo root, so `root` meant both
# things at once and three checks read repo-level paths off it. After the
# 2026-09-16 restructure those would have found nothing, returned clean and
# registered no skip -- a PASS with three checks silently not running, on the
# published mod. Measured before the move, which is the only reason it was
# caught.
REPO_ROOT = Path(__file__).resolve().parent.parent
SMART_NOTIFICATIONS_ROOT = REPO_ROOT / "smart_notifications"

# Checks that compare this mod against the INSTALLED vanilla game silently
# no-op when the game isn't on this machine (a cloud session, a fresh
# checkout). They used to print a "(skipped: ...)" line into the middle of
# the output -- or, in one case, nothing at all -- and let the run still
# report a clean PASS, so a cloud PASS read exactly like a local PASS while
# real checks had not run. Every such skip now registers here instead, and
# the caller reports it as PASS (DEGRADED).
# See docs/engine-notes.md "A degraded PASS is not a PASS".
SKIPPED: list[str] = []


def _skip(check: str, reason: str) -> None:
    entry = check + ": " + reason
    if entry not in SKIPPED:
        SKIPPED.append(entry)


# This repo builds more than one mod (see better_decision_info/README.md for why the split
# exists). Checks that assert Smart Notifications' OWN required content is
# present are meaningless against a sibling mod, so they are gated on the mod
# id below rather than skipped by folder name -- a rename cannot then silently
# disable them.
SMART_NOTIFICATIONS_ID = "smart_notifications"

# Diagnostic-only files, dropped whole from a release by
# tools/package_release.py. Stripping their debug_log lines is not enough --
# what would remain is a pile of empty on_action handlers the game still calls
# every month.
#
# The list lives HERE rather than in package_release.py so the packager and
# the validator share one source of truth: it is hand-maintained, and the
# 2026-09-16 probe was very nearly added to the repo without being added to
# the list. Forgetting is silent -- the release simply ships a dev handler --
# so check_dev_only_files_are_consistent() below makes the omission fail the
# ordinary validation run instead, long before a packaging run.
DEV_ONLY_FILES = [
    "common/on_actions/01_smart_notifications_logger.txt",
    "common/on_actions/04_smart_notifications_probes.txt",
    "common/on_actions/05_smart_notifications_toast_popup_audit.txt",
    "common/on_actions/07_smart_notifications_actor_axis_probe.txt",
    "common/on_actions/08_smart_notifications_engine_proxy.txt",
    "common/on_actions/16_smart_notifications_nogeneral_probe.txt",
]

# The marker every one of those files carries, and that no shipped file may.
# A marker rather than a filename convention: `01_..._logger.txt` and
# `05_..._toast_popup_audit.txt` are diagnostic but say so nowhere in their
# names, so any name-based rule would have to guess.
DEV_ONLY_MARKER = "# DEV-ONLY"


def read_mod_id(root: Path) -> str:
    """The `id` from a mod root's .metadata/metadata.json, or "" if this
    directory isn't a mod root (or its metadata is unreadable)."""
    meta = root / ".metadata" / "metadata.json"
    if not meta.is_file():
        return ""
    try:
        return json.loads(meta.read_text(encoding="utf-8")).get("id", "")
    except (json.JSONDecodeError, OSError):
        return ""


def nested_mod_roots(root: Path) -> list[Path]:
    """Other mods developed inside this repo, each identified by its own
    .metadata/metadata.json. Their files are not this mod's files, so every
    whole-tree scan has to exclude them -- otherwise the parent mod's checks
    would judge a sibling mod's `.gui` overrides as its own."""
    return [meta.parent.parent for meta in root.glob("*/.metadata/metadata.json")]


def _strip_comments(content: str) -> str:
    """Quote-aware '#' stripping (same rule as validate_syntax.py's syntax
    checker) so illustrative examples inside doc comments -- e.g. a header
    explaining `custom_tooltip = "LOC_KEY"` as generic documentation --
    are never mistaken for real references."""
    out_lines = []
    for line in content.splitlines():
        quote = False
        cut = len(line)
        for i, char in enumerate(line):
            if char == '"':
                quote = not quote
            elif char == '#' and not quote:
                cut = i
                break
        out_lines.append(line[:cut])
    return "\n".join(out_lines)


def _read(path: Path) -> str:
    """Comment-stripped file content -- always what checks should scan."""
    return _strip_comments(path.read_text(encoding="utf-8-sig"))


def _iter_mod_files(root: Path):
    """Files this mod actually ships/the game actually loads -- excludes
    `reference/` (pristine vanilla snapshots and any other reference-only
    copies kept for diffing, never loaded by the game itself; scanning
    them alongside our own files caused a confirmed false-positive here,
    e.g. vanilla's own untouched `popup`-type message getting compared
    against our deliberately-muted override of the same key as if they
    were two messages sharing one group)."""
    siblings = nested_mod_roots(root)
    for path in root.rglob("*.*"):
        if (
            path.suffix in TEXT_SUFFIXES
            and "tools" not in path.parts
            and ".git" not in path.parts
            and "reference" not in path.parts
            and not any(sib in path.parents for sib in siblings)
        ):
            yield path


def _brace_span(text: str, pos_after_open_brace: int) -> str | None:
    """Given a position right after an opening '{', return the text up to
    (not including) its matching '}'. Used to isolate one top-level block
    (an alert_type, a scripted_gui, ...) without a full parser."""
    depth = 1
    for j in range(pos_after_open_brace, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[pos_after_open_brace:j]
    return None


def load_defined_loc_keys(root: Path) -> set[str]:
    keys = set()
    for path in (root / "localization" / "english").glob("*.yml"):
        text = _read(path)
        for m in re.finditer(r'(?m)^\s*([A-Za-z0-9_.\-]+):\d*\s*"', text):
            keys.add(m.group(1))
    return keys


def check_custom_tooltip_keys(root: Path, defined_loc: set[str]) -> list[str]:
    """Every `custom_tooltip = "KEY"` must resolve to a real loc key.
    Root cause class: a typo'd or renamed key here fails silently in-game
    (blank/garbled tooltip text), the same failure mode the law commitment
    alert's dynamic-text bug produced -- but a plain missing-key typo has
    no error.log signature at all, so this must be caught statically."""
    errs = []
    for path in _iter_mod_files(root):
        text = _read(path)
        for m in re.finditer(r'custom_tooltip\s*=\s*"([A-Za-z0-9_]+)"', text):
            key = m.group(1)
            if key not in defined_loc:
                errs.append(f"{path}: custom_tooltip references undefined loc key '{key}'")
    return errs


def check_scripted_gui_references(root: Path) -> list[str]:
    """Every `GetScriptedGui('X')` must resolve to an X defined under
    common/scripted_guis/ specifically -- not merely defined ANYWHERE.
    Root cause class: a scripted_gui defined outside that exact folder is
    silently invisible to the engine ("Promote 'GetScriptedGui' returned
    nullptr"), the confirmed real bug behind the law commitment alert's
    blank name (see docs/engine-notes.md). This check also flags any
    scripted_gui-shaped block (has both ai_is_valid and ai_chance) found
    outside that folder, so the mistake is caught even before anything
    references it."""
    errs = []
    sgui_dir = root / "common" / "scripted_guis"
    defined = set()
    if sgui_dir.is_dir():
        for path in sgui_dir.glob("*.txt"):
            text = _read(path)
            for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
                defined.add(m.group(1))

    for path in _iter_mod_files(root):
        text = _read(path)
        for m in re.finditer(r"GetScriptedGui\('([A-Za-z0-9_]+)'\)", text):
            key = m.group(1)
            if key not in defined:
                errs.append(
                    f"{path}: GetScriptedGui('{key}') has no matching definition "
                    f"under common/scripted_guis/ (defined there: {sorted(defined) or 'none'})"
                )

    for path in _iter_mod_files(root):
        if sgui_dir in path.parents:
            continue
        text = _read(path)
        if "ai_is_valid" in text and "ai_chance" in text:
            errs.append(
                f"{path}: looks like a scripted_gui definition (has ai_is_valid "
                f"and ai_chance) but is NOT under common/scripted_guis/ -- the "
                f"engine will not find it (confirmed real bug, see "
                f"docs/engine-notes.md)"
            )
    return errs


def _parse_top_level_blocks(text: str) -> dict[str, str]:
    """Return {block_name: block_body} for every top-level `name = { ... }`
    in a file (used for alert_types)."""
    blocks = {}
    for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
        body = _brace_span(text, m.end())
        if body is not None:
            blocks[m.group(1)] = body
    return blocks


def check_alert_loc_completeness(root: Path, defined_loc: set[str]) -> list[str]:
    """Every alert_type this mod defines needs all 5 loc keys confirmed
    required in docs/engine-notes.md 'An alert type needs TWO name-shaped
    loc keys, not one': alert_<key>_name/_desc/_hint/_action (ribbon
    tooltip) AND <key>_setting_name (Message Settings row label, no
    'alert_' prefix, a genuinely different getter) -- missing the second
    one leaves Message Settings showing a raw key instead of a label,
    with no error.log signature."""
    errs = []
    alert_dir = root / "common" / "alert_types"
    if not alert_dir.is_dir():
        return errs
    required_suffixes = ["_name", "_desc", "_hint", "_action"]
    for path in alert_dir.glob("*.txt"):
        blocks = _parse_top_level_blocks(_read(path))
        for name in blocks:
            for suffix in required_suffixes:
                key = f"alert_{name}{suffix}"
                if key not in defined_loc:
                    errs.append(f"{path}: alert '{name}' missing loc key '{key}'")
            setting_key = f"{name}_setting_name"
            if setting_key not in defined_loc:
                errs.append(f"{path}: alert '{name}' missing loc key '{setting_key}'")
    return errs


def check_alert_group_registration(root: Path, defined_loc: set[str]) -> list[str]:
    """Every `alert_group = X` used on an alert_type must be declared in
    common/alert_groups/*.txt (a separate, easy-to-forget registration
    folder -- confirmed real: an alert_group referenced but never declared
    there is silently never grouped, no error.log signature at all) and
    must have ag_X_name/_desc/_tooltip loc keys."""
    errs = []
    alert_dir = root / "common" / "alert_types"
    group_dir = root / "common" / "alert_groups"
    if not alert_dir.is_dir():
        return errs

    declared_groups = set()
    if group_dir.is_dir():
        for path in group_dir.glob("*.txt"):
            text = _read(path)
            for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
                declared_groups.add(m.group(1))

    used_groups = set()
    for path in alert_dir.glob("*.txt"):
        text = _read(path)
        for m in re.finditer(r"alert_group\s*=\s*([A-Za-z0-9_]+)", text):
            used_groups.add(m.group(1))

    for group in used_groups:
        if group not in declared_groups:
            errs.append(
                f"alert_group '{group}' is used but not declared in any "
                f"common/alert_groups/*.txt file -- it will silently never group"
            )
        for suffix in ("_name", "_desc", "_tooltip"):
            key = f"ag_{group}{suffix}"
            if key not in defined_loc:
                errs.append(f"alert_group '{group}' missing loc key '{key}'")
    return errs


def check_post_notification_targets(root: Path, defined_loc: set[str]) -> list[str]:
    """Every `post_notification = X` must resolve to a real message
    defined under common/messages/*.txt, and that message needs its
    notification_<X>_name/_desc/_tooltip loc keys -- same completeness
    rule as an alert_type's loc keys, generalized. Added 2026-09-09 when
    the law-ready toast was switched from one generic message to 138
    per-law-type ones (see common/on_actions/09_smart_notifications_law_ready_toast.txt)
    specifically so that generated set can't silently drift the same way
    the law_type dispatch files could."""
    errs = []
    messages_dir = root / "common" / "messages"
    defined_messages = set()
    if messages_dir.is_dir():
        for path in messages_dir.glob("*.txt"):
            text = _read(path)
            for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
                defined_messages.add(m.group(1))

    for path in _iter_mod_files(root):
        text = _read(path)
        for m in re.finditer(r"post_notification\s*=\s*([A-Za-z0-9_]+)", text):
            key = m.group(1)
            if key not in defined_messages:
                errs.append(f"{path}: post_notification references undefined message '{key}'")
                continue
            for suffix in ("_name", "_desc"):
                loc_key = f"notification_{key}{suffix}"
                if loc_key not in defined_loc:
                    errs.append(f"message '{key}' missing loc key '{loc_key}'")
    return errs


LAW_TYPE_DISPATCH_FILES = [
    "common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt",
    "common/scripted_guis/smart_notifications_law_notify_sgui.txt",
    "common/scripted_guis/smart_notifications_law_commitment_list_sgui.txt",
    "common/on_actions/09_smart_notifications_law_ready_toast.txt",
    "common/on_actions/15_smart_notifications_law_flag_clear.txt",
]


def check_law_type_dispatch_consistency(root: Path) -> list[str]:
    """The mod maintains one law_type per real law across 4 independently
    generated files. Root cause class this catches: the BOM-extraction bug
    that silently dropped 12 laws from one generated list while the others
    stayed correct (found only because the user happened to test one of
    the missing laws) -- if any future regeneration of one file uses a
    different law list than the others, this fails immediately instead of
    waiting for a specific law to be live-tested."""
    errs = []
    law_sets: dict[str, set[str]] = {}
    for rel in LAW_TYPE_DISPATCH_FILES:
        path = root / rel
        if not path.exists():
            errs.append(f"{rel}: expected law-type dispatch file is missing")
            continue
        law_sets[rel] = set(re.findall(r"law_type:(law_[a-z_0-9]+)", _read(path)))

    if len(law_sets) < 2:
        return errs

    reference_rel, reference_set = next(iter(law_sets.items()))
    for rel, laws in law_sets.items():
        if laws != reference_set:
            missing = reference_set - laws
            extra = laws - reference_set
            detail = []
            if missing:
                detail.append(f"missing {sorted(missing)}")
            if extra:
                detail.append(f"has extra {sorted(extra)}")
            errs.append(
                f"{rel}: law_type set differs from {reference_rel} ({'; '.join(detail)})"
            )
    return errs


def check_json_files_have_no_bom(root: Path) -> list[str]:
    """`.json` files must be PLAIN UTF-8, no BOM -- the opposite rule from
    `.txt`/`.gui`/`.yml`. Confirmed real 2026-09-08: `.metadata/metadata.json`
    carried a leading BOM and the Paradox launcher's mod library showed
    "Parsing metadata failed" plus a bogus 78-byte size, because a BOM is
    not valid JSON syntax under a strict decoder (Python's own
    `json.loads` on plain `utf-8` rejects it outright: "Unexpected UTF-8
    BOM"). This had been silently missed by an earlier one-off repo audit
    that decoded JSON with `utf-8-sig` (BOM-tolerant) instead of plain
    `utf-8` -- that lenient check could never have caught this, which is
    why this is now a permanent, strict check instead of a one-time scan."""
    errs = []
    for path in root.rglob("*.json"):
        if ".git" in path.parts:
            continue
        if path.read_bytes().startswith(b"\xef\xbb\xbf"):
            errs.append(f"{path}: JSON file must NOT have a UTF-8 BOM (breaks strict JSON parsers)")
    return errs


def check_law_types_exist_in_vanilla(root: Path) -> list[str]:
    """Every law_type:X referenced anywhere in this mod must be a real
    vanilla law -- catches a typo'd or removed-by-patch law type. Skipped
    (not failed) if the vanilla game install isn't found on this machine,
    since this check depends on local environment, not just repo state."""
    laws_dir = VANILLA_ROOT / "common" / "laws"
    if not laws_dir.is_dir():
        _skip("check_law_types_exist_in_vanilla",
              f"vanilla install not found at {VANILLA_ROOT}")
        return []

    real_laws = set()
    for path in laws_dir.glob("*.txt"):
        text = path.read_text(encoding="utf-8-sig")
        real_laws.update(re.findall(r"(?m)^(law_\w+)\s*=\s*\{", text))

    errs = []
    for path in _iter_mod_files(root):
        for law in set(re.findall(r"law_type:(law_[a-z_0-9]+)", _read(path))):
            if law not in real_laws:
                errs.append(f"{path}: references law_type:{law}, not a real vanilla law")
    return errs


# Every file this mod FULLY overrides (a same-named vanilla file exists
# and we ship a complete replacement, not an additive new file) needs an
# entry here, mapping it to its baseline snapshot under
# reference/vanilla/1.13.x/. Confirmed real gap found 2026-09-09: this
# mod overrides two .gui files that had never been snapshotted at all --
# see reference/vanilla/README.md for the full writeup.
FULL_OVERRIDE_FILES = [
    ("common/messages/00_messages.txt", "reference/vanilla/1.13.x/common/messages/00_messages.txt"),
    ("gui/message_settings.gui", "reference/vanilla/1.13.x/gui/message_settings.gui"),
    ("gui/politics_panel_change_law.gui", "reference/vanilla/1.13.x/gui/politics_panel_change_law.gui"),
]

# Per-mod, because every mod in this repo that touches a vanilla panel has to
# do it by copying the whole vanilla file -- there is no partial .gui override
# in this engine (confirmed 2026-09-16; see docs/engine-notes.md § A `.gui`
# `@constant` is file-scoped, and the note below). Every such copy needs the
# drift check, or a game patch silently reverts part of the panel for players.
FULL_OVERRIDES_BY_MOD = {
    SMART_NOTIFICATIONS_ID: FULL_OVERRIDE_FILES,
    # Bulk Construction deliberately overrides NO vanilla file: it redefines a
    # single type from its own 00_-prefixed file instead. If that ever changes,
    # list the file here so drift against a patched vanilla is caught.
    "bulk_construction": [],
}


# Lines this mod deliberately does NOT carry over from the vanilla file it
# overrides. The full-override check below exists to catch a game patch adding
# content we then silently ship without; an intentional removal has to be
# declared here, with the reason, or it looks identical to drift.
#
# Both entries below were removed from the MUTED diplo_play_war_start_notification
# on 2026-09-08 to fix a confirmed, reproducible double full-screen popup when
# a war started involving the player: the muted key's presentation properties
# appeared to still be processed independently of notification_type, stacking
# with this mod's own replacement popup. Restoring them reintroduces that bug.
# See the comment on that key in common/messages/00_messages.txt.
#
# Until 2026-09-10 this omission was invisible: the check compares line SETS
# across the whole file, and this mod's own war-start key happened to contain
# the same two lines, so the vanilla ones never registered as missing. Moving
# the mod's keys into 99_smart_notifications_messages.txt removed that
# coincidence and exposed it.
ALLOWED_VANILLA_OMISSIONS: dict[str, set[str]] = {}


def check_full_overrides_match_installed_vanilla(root: Path) -> list[str]:
    """For every file this mod fully overrides, confirm the game's
    CURRENTLY INSTALLED copy has no content our own copy is missing
    (ignoring pure whitespace/line-ending differences) -- catches a
    Victoria 3 patch silently changing a file we've fully overridden,
    which would otherwise ship stale content with no signal at all.
    Skipped (not failed) per-file if the vanilla install or that file
    isn't found locally, since this depends on local environment. This
    only checks for MISSING content (vanilla has something we don't) --
    it can't tell intentional divergence from real drift, so a genuine
    hit here needs a human look at reference/vanilla/README.md's re-sync
    steps, not an automatic fix."""
    errs = []
    for our_rel, snapshot_rel in FULL_OVERRIDES_BY_MOD.get(read_mod_id(root), []):
        installed = VANILLA_ROOT / our_rel
        if not installed.is_file():
            _skip("check_full_overrides_match_installed_vanilla",
                  f"vanilla file not found at {installed}")
            continue
        our_path = root / our_rel
        if not our_path.is_file():
            errs.append(f"{our_rel}: listed as a full override but the file doesn't exist in this repo")
            continue

        def norm(text: str) -> set[str]:
            return {line.strip() for line in text.splitlines() if line.strip()}

        installed_lines = norm(installed.read_text(encoding="utf-8-sig", errors="ignore"))
        our_lines = norm(our_path.read_text(encoding="utf-8-sig", errors="ignore"))
        missing = installed_lines - our_lines
        missing -= ALLOWED_VANILLA_OMISSIONS.get(our_rel.replace("\\", "/"), set())
        if missing:
            sample = sorted(missing)[:3]
            errs.append(
                f"{our_rel}: {len(missing)} line(s) present in the currently installed vanilla file "
                f"are missing from our override -- likely a game patch changed it since this was last "
                f"synced (see reference/vanilla/README.md). Sample: {sample}"
            )
    return errs


def check_mixed_group_notification_types(root: Path) -> list[str]:
    """Every message sharing a `group` must agree on `notification_type`.
    Added 2026-09-09 after a confirmed, LIVE, non-cosmetic bug: muting
    `diplomatic_action_notification` to `none` while it stayed in
    `diplomatic_action_notification_group` alongside 3 `toast` siblings
    produced the engine's own "Diplomatic Action Group has mixed
    Notification Types" warning (player_message_type.cpp:177) in every
    play session -- and, per game.log timestamps lining up exactly with
    when the warning stopped appearing (regrouping fix committed, then
    the unwanted vanilla-worded relations popups the user had been
    seeing stopped in that same session), the mismatch didn't just log a
    warning: it appears to have silently defeated the intended `none`
    mute for the whole group. Never assume this warning is purely
    cosmetic -- treat it as a real bug, same severity as any other check
    here. This scans every message-defining file (not just
    common/messages/) since this mod could in principle add a message
    elsewhere."""
    errs = []
    group_types: dict[str, dict[str, str]] = {}  # group -> {notification_type: sample_key}
    for path in _iter_mod_files(root):
        if path.suffix != ".txt":
            continue
        text = _read(path)
        for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
            key = m.group(1)
            block = _brace_span(text, m.end())
            if block is None:
                continue
            group_m = re.search(r'group\s*=\s*"([^"]+)"', block)
            type_m = re.search(r"notification_type\s*=\s*(\w+)", block)
            if not group_m or not type_m:
                continue
            group_types.setdefault(group_m.group(1), {}).setdefault(type_m.group(1), key)

    for group, types in group_types.items():
        if len(types) > 1:
            detail = ", ".join(f"{t} (e.g. '{k}')" for t, k in sorted(types.items()))
            errs.append(
                f"group '{group}' has mixed notification_type values: {detail} -- "
                f"split the mismatched message(s) into their own group"
            )
    return errs


# --- Watchlist spec conformance ---------------------------------------------
# docs/watchlist-spec.md is the locked behavioural spec. These checks make it
# executable rather than aspirational: the tables below ARE the spec's tiers,
# and a mismatch fails the build instead of surfacing as a surprise toast three
# playtests later.
#
# Keep these tables and the spec in sync BY HAND and deliberately -- that is
# the point. Changing a tier here without changing the spec (or vice versa)
# should feel like editing two things, because it is a behavioural change
# either way.
WATCHLIST_SPEC_CELLS = {
    # F1 -- generic diplomatic actions, five cells.
    "smart_notifications_diplomatic_action_at_player_by_watched": "toast",
    "smart_notifications_diplomatic_action_at_player_by_other": "feed",
    "smart_notifications_diplomatic_action_at_watched_by_watched": "toast",
    "smart_notifications_diplomatic_action_at_watched_by_other": "feed",
    "smart_notifications_diplomatic_action_elsewhere": "feed",
    # F10 -- pact breaks, two toast cells sharing one group.
    "smart_notifications_diplomatic_action_break_at_player_by_watched": "toast",
    "smart_notifications_diplomatic_action_break_at_watched_by_watched": "toast",
    "smart_notifications_diplomatic_action_break_other": "feed",
    # F2 -- diplomatic plays, three tiers per family.
    "smart_notifications_diplo_play_start_player": "toast",
    "smart_notifications_diplo_play_start_watched": "toast",
    "smart_notifications_diplo_play_start_quiet": "feed",
    "smart_notifications_diplo_play_join_side_player": "toast",
    "smart_notifications_diplo_play_join_side_watched": "toast",
    "smart_notifications_diplo_play_join_side_quiet": "feed",
    "smart_notifications_diplo_play_war_start_watched": "toast",
    "smart_notifications_diplo_play_war_start_quiet": "feed",
    # F7 -- subject released, unchanged by the spec but pinned so it cannot
    # drift silently.
    "smart_notifications_diplo_play_subject_released_watched": "toast",
}

# Cells that deliberately SHARE a group, and the group they share. D11 wants
# one group per independently-adjustable cell -- but two cells that the user
# never wants to adjust separately are better merged, because every group costs
# a row in the player's Message Settings list.
#
# War goals are the case: "added" and "removed" need different wording, so they
# stay separate message keys, but the user asked for one control per tier
# rather than two ("not even sure how to remove a war goal", 2026-09-09). Same
# shape the 138 law-ready toasts already use. Sharing is only legal when the
# sharers agree on notification_type, which check_mixed_group_notification_types
# enforces independently.
#
# Anything NOT listed here that shares a group is still an error -- that is the
# accident this check exists to catch.
WATCHLIST_SPEC_SHARED_GROUPS = {
    # The three diplo-play "Non Watched" cells: one concept (a play with
    # nobody the player follows in it), three keys only because each family
    # words it differently. Subject Released is NOT in here -- it is `none`
    # rather than `feed`, and sharers must agree on notification_type.
    # Mod Loaded and Mod Updated: two one-off housekeeping notices the player
    # would never want to tune apart, merged to one row 2026-09-10.
    "smart_notifications_mod_notices_group": {
        "smart_notifications_mod_loaded",
        "smart_notifications_mod_updated",
    },
    "smart_notifications_diplo_play_quiet_group": {
        "smart_notifications_diplo_play_start_quiet",
        "smart_notifications_diplo_play_join_side_quiet",
        "smart_notifications_diplo_play_war_start_quiet",
    },
    "smart_notifications_diplomatic_action_break_watched_group": {
        "smart_notifications_diplomatic_action_break_at_player_by_watched",
        "smart_notifications_diplomatic_action_break_at_watched_by_watched",
    },
}

# Vanilla keys whose tier the spec pins directly (F5, F6, and the two the F9
# split replaces). Same reasoning: deliberate decisions, not defaults, so an
# accidental revert should fail loudly.
WATCHLIST_SPEC_VANILLA_TIERS = {
    "country_owes_obligation": "toast",
    "country_owed_obligation": "toast",
    "country_owes_obligation_removed": "toast",
    "country_owed_obligation_removed": "toast",
    "obligation_owed_to_us_expired": "toast",
    "obligation_owed_by_us_expired": "toast",
    "country_attitude_changed": "feed",
    "country_attitude_improved": "feed",
    "country_attitude_worsened": "feed",
    "harvest_condition_started_in_country_important": "feed",
    "resource_discovered": "feed",
    "resource_depleted": "feed",
    "invasion_started_against_us": "toast",
    # Split 2026-09-15 into smart_notifications_country_swayed_watched
    # (feed) and _quiet (none), routed on whether the SWAYED country is
    # watched. Vanilla's key is now muted, so `none` here is the
    # intended state, not drift.
    "country_swayed": "none",
    "sway_offer_accepted": "feed",
    "reverse_sway_offer_accepted": "feed",
    "sway_offer_rejected": "feed",
    "reverse_sway_offer_rejected": "feed",
    "cobelligerent_in_default_notification": "feed",
    "enemy_in_default_notification": "feed",
    "diplomatic_proposal_third_party_notification": "none",
    "diplomatic_proposal_third_party_accepted": "none",
    "diplomatic_proposal_third_party_declined": "none",
    "diplomatic_proposal_third_party_break_notification": "none",
    "diplomatic_proposal_third_party_break_accepted": "none",
    "diplomatic_proposal_third_party_break_declined": "none",
    "diplomatic_action_break_notification": "none",
    "wargoal_added": "feed",
    "wargoal_removed": "feed",
}


def _message_blocks(root: Path) -> dict[str, str]:
    blocks = {}
    messages_dir = root / "common" / "messages"
    if not messages_dir.is_dir():
        return blocks
    for path in sorted(messages_dir.glob("*.txt")):
        text = _read(path)
        for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
            block = _brace_span(text, m.end())
            if block is not None:
                blocks[m.group(1)] = block
    return blocks


def check_watchlist_spec_tiers(root: Path) -> list[str]:
    """Every message the spec names must exist with the tier the spec gives it.
    Catches the failure mode this project keeps hitting: a tier changed for a
    good reason in the moment, quietly contradicting a decision made
    deliberately earlier, noticed only when a playtest feels wrong."""
    errs = []
    blocks = _message_blocks(root)
    for key, want in {**WATCHLIST_SPEC_CELLS, **WATCHLIST_SPEC_VANILLA_TIERS}.items():
        block = blocks.get(key)
        if block is None:
            errs.append(
                f"watchlist spec: message '{key}' is missing -- docs/watchlist-spec.md requires it"
            )
            continue
        m = re.search(r"notification_type\s*=\s*(\w+)", block)
        got = m.group(1) if m else "<none>"
        if got != want:
            errs.append(
                f"watchlist spec: '{key}' is {got}, spec says {want} "
                f"(docs/watchlist-spec.md) -- change the spec first if this is intended"
            )
    return errs


def check_watchlist_spec_group_isolation(root: Path) -> list[str]:
    """Spec D11: every cell owns its group outright. Player Message Settings
    overrides apply per GROUP, not per key (CLAUDE.md), so two cells sharing a
    group silently collapse into one control -- the player could no longer, for
    instance, mute `elsewhere` without also muting what is aimed at them, which
    is the entire reason the matrix is split into separate keys.

    Deliberately NOT a blanket one-key-per-group rule: the 138 law-ready toasts
    share a group on purpose, so they occupy one Message Settings row, not
    138."""
    errs = []
    blocks = _message_blocks(root)
    group_owners: dict[str, list[str]] = {}
    for key, block in blocks.items():
        gm = re.search(r'group\s*=\s*"([^"]+)"', block)
        if gm:
            group_owners.setdefault(gm.group(1), []).append(key)

    for key in WATCHLIST_SPEC_CELLS:
        block = blocks.get(key)
        if block is None:
            continue  # already reported by the tier check
        gm = re.search(r'group\s*=\s*"([^"]+)"', block)
        if not gm:
            errs.append(
                f"watchlist spec: '{key}' has no group -- D11 requires one group per cell"
            )
            continue
        group = gm.group(1)
        sharers = [k for k in group_owners.get(group, []) if k != key]
        declared = WATCHLIST_SPEC_SHARED_GROUPS.get(group)
        if declared is not None:
            # Deliberate sharing: every occupant must be one of the declared
            # ones, so adding a third key by accident still fails.
            unexpected = sorted(set(sharers + [key]) - declared)
            if unexpected:
                errs.append(
                    f"watchlist spec (D11): group '{group}' is declared shared by "
                    f"{', '.join(sorted(declared))}, but also holds "
                    f"{', '.join(unexpected)} -- update WATCHLIST_SPEC_SHARED_GROUPS "
                    f"if that is intended"
                )
            continue
        if sharers:
            errs.append(
                f"watchlist spec (D11): '{key}' shares group '{group}' with "
                f"{', '.join(sorted(sharers))} -- each cell needs its own group to stay "
                f"independently adjustable in Message Settings"
            )
    return errs


def check_mod_group_labels_are_tagged(root: Path) -> list[str]:
    """Every group this mod creates needs an `(SN) `-prefixed label, and needs
    that label to exist at all. CLAUDE.md requires the prefix on any
    Message-Settings-visible label the mod introduces; a missing label shows the
    raw key name in the settings list, the same silent-ugly failure class as a
    missing notification loc key."""
    errs = []
    loc_values = {}
    loc_dir = root / "localization"
    if loc_dir.is_dir():
        for path in sorted(loc_dir.rglob("*.yml")):
            for line in _read(path).splitlines():
                m = re.match(r'\s*([A-Za-z0-9_]+):\d*\s*"(.*)"\s*$', line)
                if m:
                    loc_values[m.group(1)] = m.group(2)

    for key, block in _message_blocks(root).items():
        if not key.startswith("smart_notifications_"):
            continue
        gm = re.search(r'group\s*=\s*"([^"]+)"', block)
        if not gm:
            continue
        group = gm.group(1)
        if group not in loc_values:
            errs.append(
                f"mod group '{group}' (from '{key}') has no loc label -- "
                f"Message Settings would show the raw key"
            )
        elif not loc_values[group].startswith("(SN) "):
            errs.append(
                f"mod group '{group}' label is {loc_values[group]!r} -- CLAUDE.md requires "
                f'the "(SN) " prefix on every Message-Settings-visible label this mod adds'
            )
    return errs


def check_notification_loc_completeness(root: Path, defined_loc: set[str]) -> list[str]:
    """A message needs all its loc keys, not just the _name/_desc pair
    check_post_notification_targets already enforces for posted keys. A missing
    `_tooltip` renders the raw key on hover. Both fail silently on screen and
    never reach error.log."""
    errs = []
    for key in _message_blocks(root):
        if not key.startswith("smart_notifications_"):
            continue
        for suffix, what in (("_tooltip", "tooltip"), ("_name", "name"), ("_desc", "desc")):
            loc_key = f"notification_{key}{suffix}"
            if loc_key not in defined_loc:
                errs.append(f"message '{key}' missing its {what} loc key '{loc_key}'")
    return errs


def check_loc_lines_are_well_formed(root: Path) -> list[str]:
    """A localization value must live entirely on ONE line. A real newline
    inside it truncates the value at the break and leaves the remainder as junk
    the parser cannot place -- and, like most loc breakage in this game, it says
    nothing at load time and only shows up as a raw key or missing text on
    screen.

    Added 2026-09-10 after writing 17 of them at once: a generator emitted real
    newlines where it meant the two-character sequence backslash-n, and every
    tooltip added that day was silently malformed. Cheap to check, invisible
    otherwise."""
    errs = []
    key_open = re.compile(r'^([A-Za-z0-9_]+):\d*\s*"')
    key_full = re.compile(r'^[A-Za-z0-9_]+:\d*\s*".*"\s*$')
    loc_dir = root / "localization"
    if not loc_dir.is_dir():
        return errs
    for path in sorted(loc_dir.rglob("*.yml")):
        for n, line in enumerate(_read(path).split("\n"), 1):
            st = line.strip()
            if not st or st.startswith("#") or st.endswith(":"):
                continue
            if key_open.match(st):
                if not key_full.match(st):
                    errs.append(
                        f"{path}:{n}: loc value is not closed on its own line -- "
                        f"a real newline inside a value truncates it; use a literal \\n"
                    )
            elif not re.match(r'[A-Za-z0-9_]+:\d*\s', st):
                errs.append(
                    f"{path}:{n}: line is neither a key nor a comment -- "
                    f"probably the tail of a value broken across lines"
                )
    return errs


# Vanilla loc keys this mod REPLACES via localization/replace/english/.
# Each value is a hash of the vanilla text our override was derived from, as
# shipped in the game version recorded below.
#
# WHY THIS EXISTS: a replaced loc key is a silent fork. If Paradox edits the
# vanilla string in a patch -- adds a clause, renames a concept, changes a
# formatting token -- our copy keeps rendering the OLD text forever, with no
# error and nothing in error.log. The player just sees stale wording, or
# loses a sentence the patch added. That is exactly the failure mode nobody
# notices until a review mentions it.
#
# So every patch, this check tells you which overrides actually need
# re-deriving, instead of leaving it to memory.
#
# TO UPDATE after reviewing a patch's changes: re-run the hash for the key
# (sha256 of the raw string between the quotes, first 16 hex chars) and paste
# it here, having merged the vanilla change into our override.
REPLACED_LOC_BASELINE_GAME_VERSION = "1.13.11"
REPLACED_LOC_BASELINE = {
    "POP_EFFECT_FILTER": "605327a4a3c58031",
    "POP_EFFECT_FILTER_INTEREST_GROUP": "174908cfa3301662",
    "POP_EFFECT_FILTER_CULTURE": "20c3a7dbef52a7a9",
    "POP_EFFECT_FILTER_RELIGION": "5201ef34656d95cc",
    "POP_EFFECT_FILTER_POP_TYPE": "2389a7c580434297",
    "ADD_RADICALS_IN_STATE_THIRD": "a234c3847df477e8",
    "ADD_LOYALISTS_IN_STATE_THIRD": "3576276f3952fa7f",
}


def check_replaced_loc_still_matches_vanilla(root: Path) -> list[str]:
    """Every key in REPLACED_LOC_BASELINE must still look, in the INSTALLED
    vanilla files, exactly as it did when we forked it. A mismatch means the
    patch changed it and our override is now stale."""
    import hashlib
    replace_dir = root / "localization" / "replace" / "english"
    if not replace_dir.is_dir():
        return []
    ours = set()
    for path in replace_dir.glob("*.yml"):
        for m in re.finditer(r'(?m)^\s*([A-Z_0-9]+):\d*\s*"', _read(path)):
            ours.add(m.group(1))

    vanilla_loc = VANILLA_ROOT / "localization" / "english"
    if not vanilla_loc.is_dir():
        # This one used to return silently -- no "(skipped)" line at all --
        # so a stale override against a patched vanilla string could
        # survive a green run without leaving a trace in the output.
        _skip("check_replaced_loc_still_matches_vanilla",
              f"vanilla localization not found at {vanilla_loc}")
        return []
    blob = ""
    for path in vanilla_loc.glob("*.yml"):
        try:
            blob += path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue

    errs = []
    for key, expected in REPLACED_LOC_BASELINE.items():
        if key not in ours:
            continue  # we no longer override it; nothing to keep in sync
        m = re.search(rf'(?m)^\s*{re.escape(key)}:\d*\s*"(.*)"\s*$', blob)
        if not m:
            errs.append(
                f"replaced loc key '{key}' no longer exists in installed vanilla -- "
                f"the patch removed or renamed it, so our override is dead weight"
            )
            continue
        got = hashlib.sha256(m.group(1).encode()).hexdigest()[:16]
        if got != expected:
            errs.append(
                f"replaced loc key '{key}': vanilla text CHANGED since "
                f"{REPLACED_LOC_BASELINE_GAME_VERSION} (baseline {expected}, now {got}). "
                f"Re-derive our override from the new vanilla string, then update "
                f"REPLACED_LOC_BASELINE in tools/check_references.py."
            )
    return errs


def check_engine_notes_toc_is_current(root: Path) -> list[str]:
    """docs/engine-notes.md carries a generated table of contents. CLAUDE.md
    tells every session to read the relevant section there before relying on a
    rule, so a stale TOC sends the reader to the wrong place -- or, worse,
    makes a section invisible and gets a settled question re-litigated from
    scratch. Regenerate with: python tools/gen_engine_notes_toc.py"""
    doc = REPO_ROOT / "docs" / "engine-notes.md"
    if not doc.is_file():
        return []
    text = doc.read_text(encoding="utf-8-sig")
    m = re.search(r"<!-- TOC -->(.*?)<!-- /TOC -->", text, re.S)
    headings = re.findall(r"(?m)^## (.+?)\s*$", text)
    if not m:
        if headings:
            return ["docs/engine-notes.md has no <!-- TOC --> block -- run "
                    "python tools/gen_engine_notes_toc.py"]
        return []
    listed = re.findall(r"(?m)^- \[(.+?)\]\(#", m.group(1))

    def norm(t: str) -> str:
        return t.replace("`", "").replace("\\[", "[").replace("\\]", "]").strip()

    want = [norm(h) for h in headings]
    got = [norm(x) for x in listed]
    if want == got:
        return []
    errs = []
    for t in want:
        if t not in got:
            errs.append(f"engine-notes TOC is missing section: {t!r}")
    for t in got:
        if t not in want:
            errs.append(f"engine-notes TOC lists a section that no longer exists: {t!r}")
    if not errs:
        errs.append("engine-notes TOC lists the right sections but in the wrong order")
    errs.append("  fix: python tools/gen_engine_notes_toc.py")
    return errs



# Repo-wide checks run once per process, not once per mod: they inspect
# REPO_ROOT, so running them per mod root would just triple every message.
_REPO_WIDE_DONE: set[str] = set()


def check_markdown_links_resolve(root: Path) -> list[str]:
    """Every relative link in this repo's own .md files has to point at a file
    that exists.

    Added 2026-09-16, after the one-folder-per-mod restructure moved
    CHANGELOG.md, TODO.md and the whole of common/, gui/ and localization/
    under `smart_notifications/` and left 14 links pointing at their old
    paths. Nothing caught it -- the mod still loaded, the validator still
    passed, and the only symptom was a doc link that 404s months later when
    someone follows it looking for the evidence behind a decision. A moved
    file is exactly what a static scan sees and a playtest never will.

    Only relative links are checked; http(s)/mailto are somebody else's
    problem, and a citation of a VANILLA game file must not be written as a
    markdown link in the first place (it does not exist in this repo, so it
    would fail here -- cite it in backticks instead)."""
    if "markdown_links" in _REPO_WIDE_DONE:
        return []
    _REPO_WIDE_DONE.add("markdown_links")

    link_re = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    skip_dirs = {".git", "__pycache__", "node_modules"}
    errs = []
    for md in sorted(REPO_ROOT.rglob("*.md")):
        if any(part in skip_dirs or part.endswith("_release") for part in md.parts):
            continue
        for m in link_re.finditer(md.read_text(encoding="utf-8-sig", errors="replace")):
            target = m.group(1).split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "claude://")):
                continue
            if not (md.parent / target).exists():
                rel = md.relative_to(REPO_ROOT).as_posix()
                errs.append(f"{rel} links to a path that does not exist: {target}")
    return errs


# How each snapshotted `reference/vanilla/<ver>/` directory is used, because
# the right completeness rule differs and cannot be inferred from the files
# present (inferring it is what let the 2026-09-15 bug hide -- a corpus
# baseline holding one file looks exactly like a correct diff baseline).
#
#   "corpus" -- tooling reads the whole directory as "what vanilla defines".
#               It MUST hold every installed file, or vanilla looks smaller
#               than it is.
#   "diff"   -- the snapshot exists only to diff the files this mod overrides.
#               It must hold exactly those, and nothing else is expected.
REFERENCE_SNAPSHOT_MODE: dict[str, str] = {
    "common/messages": "corpus",
    "gui": "diff",
}


def check_vanilla_reference_snapshot_is_complete(root: Path) -> list[str]:
    """A partially-snapshotted reference directory is silently wrong.

    Found 2026-09-15: the snapshot held only `common/messages/00_messages.txt`
    while the game ships seven message files, so the vanilla column of
    `compare_notification_settings.py` -- the join table the notification
    census and its Reddit post both rest on -- was missing whole groups
    (`colonial_claim`, `on_impose_law`, ...) and reported them as absent.
    Nothing failed; the numbers were just quietly short.

    Skipped (not failed) without a local game install.
    """
    ref_root = REPO_ROOT / "reference" / "vanilla"
    if not ref_root.is_dir():
        return []
    if not VANILLA_ROOT.is_dir():
        _skip("check_vanilla_reference_snapshot_is_complete",
              f"vanilla install not found at {VANILLA_ROOT}")
        return []

    errs = []
    for version_dir in sorted(d for d in ref_root.iterdir() if d.is_dir()):
        for our_dir in sorted(d for d in version_dir.rglob("*") if d.is_dir()):
            rel = our_dir.relative_to(version_dir).as_posix()
            game_dir = VANILLA_ROOT / rel
            if not game_dir.is_dir():
                continue
            ours = {f.name for f in our_dir.iterdir() if f.is_file()}
            if not ours:
                continue

            mode = REFERENCE_SNAPSHOT_MODE.get(rel)
            if mode is None:
                errs.append(
                    f"reference/vanilla/{version_dir.name}/{rel} is snapshotted "
                    f"but not declared in REFERENCE_SNAPSHOT_MODE"
                )
                errs.append(
                    "    fix: declare it 'corpus' (tooling reads the whole "
                    "directory as vanilla) or 'diff' (only the files this mod "
                    "overrides), in tools/check_references.py"
                )
                continue

            if mode == "corpus":
                exts = {f.suffix for f in our_dir.iterdir() if f.is_file()}
                for ext in sorted(exts):
                    have = {f.name for f in our_dir.glob(f"*{ext}")}
                    want = {f.name for f in game_dir.glob(f"*{ext}")}
                    missing = want - have
                    if missing:
                        errs.append(
                            f"vanilla reference snapshot is incomplete: "
                            f"reference/vanilla/{version_dir.name}/{rel} has "
                            f"{len(have)} of {len(want)} installed {ext} file(s)"
                        )
                        for name in sorted(missing):
                            errs.append(f"    missing: {name}")
                        errs.append(f"    fix: copy them from {game_dir}")
            else:  # diff
                mod_dir = root / rel
                overrides = (
                    {f.name for f in mod_dir.iterdir() if f.is_file()}
                    & {f.name for f in game_dir.iterdir() if f.is_file()}
                    if mod_dir.is_dir() else set()
                )
                missing = overrides - ours
                if missing:
                    errs.append(
                        f"vanilla reference snapshot is missing a file this "
                        f"mod overrides: reference/vanilla/{version_dir.name}/{rel}"
                    )
                    for name in sorted(missing):
                        errs.append(f"    missing: {name}")
                    errs.append(f"    fix: copy them from {game_dir}")
    return errs


CENSUS_BUILD = (Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3"
                / "mod" / "smart_notifications_census")


def check_census_build_not_stale(root: Path) -> list[str]:
    """The census build copies this mod's own files -- and then shadows them.

    The census mod loads AFTER Smart Notifications, so its copy of an SN file
    wins. That copy is a snapshot taken at build time. Edit the real file
    afterwards and the running game keeps using the snapshot, silently.

    That is not hypothetical. On 2026-09-15 a fix to
    08_smart_notifications_engine_proxy.txt was made ten minutes before an
    11-year measurement run, validated, committed -- and had no effect,
    because a census build from twenty minutes earlier was shadowing it. The
    whole run produced the old, broken output and nothing anywhere said so.

    So: whenever a census build exists, every SN file inside it must still
    match the repo. Compared by stripping the census's own inserted logging
    lines back out, which needs no sidecar file to go stale in its own right.

    Skipped (not failed) when no census build is present -- it is a dev-only
    artifact that most checkouts will not have.

    Also skipped when `root` is not the live dev repo itself. The hazard this
    guards against is entirely about the tree the game loads through the dev
    junction; a copy of the mod somewhere else is never shadowed by anything.
    Without that gate this fired on tools/package_release.py's staging
    directory -- which is a deliberately MODIFIED copy (debug_log lines are
    stripped out of a release), so every on_action file "differed" from the
    census snapshot and the check reported all nine as stale. That aborted
    packaging outright, i.e. Smart Notifications could not be packaged for
    release at all. Found 2026-09-16, and confirmed against the unmodified
    script from git HEAD so it could not be mistaken for a regression.
    """
    if not CENSUS_BUILD.is_dir():
        return []
    if root.resolve() != SMART_NOTIFICATIONS_ROOT.resolve():
        return []

    errs = []
    checked = 0
    for copy in sorted(CENSUS_BUILD.rglob("*.txt")):
        rel = copy.relative_to(CENSUS_BUILD).as_posix()
        ours = root / rel
        if not ours.is_file():
            continue          # a vanilla file, not one of ours
        try:
            built = copy.read_text(encoding="utf-8-sig", errors="replace")
            current = ours.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        checked += 1
        stripped = "\n".join(l for l in built.splitlines()
                              if "SNW_CENSUS|" not in l)
        if stripped.strip() != current.strip():
            errs.append(
                f"census build is STALE for a file this mod owns: {rel}")
            errs.append(
                "    the census loads after Smart Notifications, so its copy "
                "shadows yours and your edit will have no effect in-game")
            errs.append(
                "    fix: python tools/build_census_mod.py --mode measure "
                "--events all --sources all --probe-localize 0")
    if errs:
        errs.append(f"    ({checked} mod-owned file(s) in the census build)")
    return errs


BULK_CONSTRUCTION_ID = "bulk_construction"

# Effects that would hand the player something the game did not charge them
# for. All four are real vanilla effect names (common/effect_localization/),
# so a typo here fails loudly rather than silently passing.
#
# `start_building_construction` is deliberately NOT on this list: it starts a
# normal, paid construction rather than conjuring a building, and it is the
# honest fallback primitive if the GUI-native route fails (see
# docs/bulk-construction-spec.md section 2). Banning it would flag a
# legitimate design change as cheating.
CHEAT_VERBS = {
    "create_building": "creates a finished building instantly and free",
    "add_building_level": "adds a building level instantly and free",
    "add_treasury": "moves money the game did not agree to move",
    "add_modifier": "a UX mod has no business altering construction cost, "
                    "points, speed or anything else via a modifier",
}


def check_bc_gui_filename_still_sorts_first(root: Path) -> list[str]:
    """This mod works by redefining one vanilla `type` from its own file, and
    the engine keeps the FIRST definition it reads, in filename order. So the
    file must sort before vanilla's `map_list_panel.gui` or the mod silently
    does nothing -- it parses cleanly, loads, and the panel just renders
    vanilla's version.

    That is not hypothetical: an identical earlier version named
    `zz_bulk_construction_types.gui` did exactly that and cost two playtests
    to diagnose. A rename is the one edit that breaks this mod without
    breaking anything a normal check would notice."""
    gui_dir = root / "gui"
    if not gui_dir.is_dir():
        return []
    ours = [p.name for p in gui_dir.glob("*.gui")]
    if not ours:
        return []
    late = [n for n in ours if n.lower() >= "map_list_panel.gui"]
    if late:
        return [f"gui/{late[0]}: sorts at or after vanilla's map_list_panel.gui, "
                f"so its type redefinition will lose and the mod will silently "
                f"do nothing. Keep the 00_ prefix (see the file's own header)."]
    return []


def check_bc_panel_width_matches_vanilla(root: Path) -> list[str]:
    """`@constant`s are file-scoped in this engine's GUI parser, confirmed the
    hard way on 2026-09-16: referencing vanilla's `@panel_width` from our own
    .gui file produced `Malformed token: @panel_width`, which killed the whole
    redefined type and made the panel fall back to vanilla silently.

    So we declare our own copy, which can now drift from vanilla's without
    anything complaining. This asserts it hasn't."""
    ours = root / "gui" / "00_bulk_construction_map_list.gui"
    if not ours.is_file():
        return []
    vanilla = VANILLA_ROOT / "gui" / "map_list_panel.gui"
    if not vanilla.is_file():
        _skip("bc panel width", "Victoria 3 not installed on this machine")
        return []

    m = re.search(r"^@bc_panel_width\s*=\s*(\d+)", _read(ours), re.M)
    if not m:
        return ["gui/00_bulk_construction_map_list.gui: @bc_panel_width is gone -- "
                "it must stay declared here, never borrowed from vanilla "
                "(a cross-file @constant is a parse error that kills the type)"]
    v = re.search(r"^@panel_width\s*=\s*(\d+)", _read(vanilla), re.M)
    if v and v.group(1) != m.group(1):
        return [f"gui/00_bulk_construction_map_list.gui: @bc_panel_width is "
                f"{m.group(1)}, but vanilla's @panel_width is now {v.group(1)} "
                f"-- the construction panel rows will be misaligned until it matches"]
    return []


def check_bc_loc_has_no_nested_arithmetic(root: Path) -> list[str]:
    """A loc string whose dynamic text cannot be resolved renders as an EMPTY
    widget. No crash, no fallback text, no visible clue -- the button is just
    blank, and only error.log says why:

        FetchData failed for 'Multiply_CFixedPoint(IntToFixedPoint(...))'
        PdxDataFetchLocalizedData failed for 'BC_BUILD_BUTTON_5'

    Confirmed 2026-09-16: the level-count buttons tried to show N*M by nesting
    IntToFixedPoint inside Multiply_CFixedPoint. Both functions are real and
    used by vanilla, but not composed over a call like this, and it fails at
    fetch time rather than at load.

    There is no datamodel-filtering function in this engine either (only
    GetDataModelSize / SkipFirst / SubSpan / First / Last), so the count shown
    can only ever be "rows listed", never "rows that will actually build" --
    which is why the label says "where possible" instead of a product."""
    loc = root / "localization" / "english"
    if not loc.is_dir():
        return []
    errs = []
    for path in loc.glob("*.yml"):
        for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if re.search(r"(Multiply|Add|Subtract|Divide)_\w+\(\s*\w+\(", line):
                errs.append(
                    f"localization/english/{path.name}:{i}: nested arithmetic in a loc "
                    f"string. It fails at fetch time and renders the widget BLANK with "
                    f"no visible error -- see this check's docstring")
    return errs


def check_bc_loc_has_no_bracket_decoration(root: Path) -> list[str]:
    """A literal `[...]` in loc text is ALWAYS parsed as a dynamic-text call --
    there is no escape (CLAUDE.md section 3). Used as a visual tag, e.g.
    `[Build All] Queue 5 levels`, it fails to resolve and the widget renders
    BLANK, exactly like the nested-arithmetic failure above. Use parentheses.

    Proposed as a mod tag on 2026-09-16 and caught before it shipped. The
    pattern below is deliberately narrow: it wants a bracketed run containing a
    space and starting with a capital, with no `(` inside -- prose, in other
    words. Real calls carry parentheses, and vanilla's bare concept references
    (`[concept_state]`) are lowercase and spaceless, so neither trips it."""
    loc = root / "localization" / "english"
    if not loc.is_dir():
        return []
    errs = []
    for path in loc.glob("*.yml"):
        for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            for m in re.finditer(r"\[([A-Z][^\[\]()]*\s[^\[\]()]*)\]", line):
                errs.append(
                    f"localization/english/{path.name}:{i}: '[{m.group(1)}]' reads as "
                    f"decoration but will be parsed as a dynamic-text call and render "
                    f"the widget BLANK. Use parentheses: '({m.group(1)})'")
    return errs


def check_dev_only_files_are_consistent(root: Path) -> list[str]:
    """DEV_ONLY_FILES and the `# DEV-ONLY` markers must agree, both ways.

    Root cause class: a diagnostic on_action file shipping to subscribers.
    Its handlers do nothing once their debug_log lines are stripped, so
    nothing breaks loudly -- the game just calls a set of empty handlers on
    every monthly pulse forever, and no log line or error signature says so.
    The only moment it is visible is by reading the packaged output, which is
    exactly the step nobody repeats before an upload.

    Three ways it can drift, all caught here:
      - a new probe is written and not added to the list  (the near-miss that
        prompted this check)
      - a listed file is renamed, so the exclusion silently matches nothing
      - a marker is pasted into a file that genuinely ships
    """
    errs = []
    on_actions = root / "common" / "on_actions"
    if not on_actions.is_dir():
        return []

    # Raw text, NOT _read(): the marker IS a comment, and _read() strips
    # comments, so every file would look unmarked and the check would fail
    # everything indiscriminately -- which is exactly what it did when first
    # written.
    def raw(p: Path) -> str:
        return p.read_text(encoding="utf-8-sig")

    listed = set(DEV_ONLY_FILES)

    # A RELEASE STAGING copy has had every one of these deleted on purpose
    # (package_release.drop_dev_only_files), and validate_staging then runs
    # this whole module against it -- so the rename arm below would fire on
    # all of them and abort every package run. It did, from 17faaec until
    # 2026-09-18: Smart Notifications could not be packaged at all, found
    # while packaging its sibling. Absent-because-dropped is distinguishable
    # from absent-because-renamed by whether ANY of them survived, and a
    # rename leaves the rest in place.
    all_dropped = listed and not any((root / rel).is_file() for rel in listed)

    for rel in sorted(listed):
        path = root / rel
        if all_dropped:
            continue
        if not path.is_file():
            errs.append(
                f"{rel}: listed in DEV_ONLY_FILES but does not exist -- the "
                f"exclusion matches nothing, so if the file was renamed its "
                f"replacement is now shipping. Update the list in "
                f"tools/check_references.py")
        elif DEV_ONLY_MARKER not in raw(path):
            errs.append(
                f"{rel}: listed in DEV_ONLY_FILES but carries no "
                f"`{DEV_ONLY_MARKER}` marker comment. Add one so the file "
                f"says for itself that it never ships")

    for path in sorted(on_actions.glob("*.txt")):
        rel = path.relative_to(root).as_posix()
        if DEV_ONLY_MARKER in raw(path) and rel not in listed:
            errs.append(
                f"{rel}: marked `{DEV_ONLY_MARKER}` but NOT in DEV_ONLY_FILES "
                f"-- it would ship to subscribers as a set of empty handlers. "
                f"Add it to the list in tools/check_references.py")
    return errs


def check_gui_textures_exist(root: Path) -> list[str]:
    """Every `texture = "gfx/..."` a mod .gui names must exist, in the mod or
    in vanilla.

    A texture path that resolves to nothing is the quietest bug this engine
    has: nothing draws, and nothing is logged -- no error.log line, no
    warning. The widget is simply invisible, which is indistinguishable from
    a `visible` condition that is false, so it survives a playtest that was
    looking at something else.

    Found 2026-09-18. Bulk Construction's level stepper marked the selected
    level with `gfx/interface/buttons/button_selected_frame.dds`, invented
    rather than looked up. No such file ships with the game, so from 0.01
    onward there was no selected-level highlight at all -- through a playtest
    that confirmed the stepper's behaviour and never questioned its
    appearance. The fix was vanilla's own `highlighted_square_selection`
    template, which does this exact job at
    gui/building_browser_panel.gui:961-976.

    Scanned per line, so only literal single-line paths are checked; a path
    built by a datafunction is skipped rather than guessed at."""
    errs = []
    gui_dir = root / "gui"
    if not gui_dir.is_dir():
        return errs
    if not VANILLA_ROOT.is_dir():
        _skip("gui texture paths", "Victoria 3 not installed on this machine")
        return errs

    pattern = re.compile('texture[^"]*"(gfx/[^"]+)"')
    for path in sorted(gui_dir.rglob("*.gui")):
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(_read(path).split(chr(10)), 1):
            m = pattern.search(line)
            if not m:
                continue
            tex = m.group(1)
            if "[" in tex:  # built at runtime by a datafunction
                continue
            if (root / tex).is_file() or (VANILLA_ROOT / tex).is_file():
                continue
            errs.append(
                f"{rel}:{lineno}: texture `{tex}` exists neither in this mod "
                f"nor in the installed game. Nothing will draw and nothing "
                f"will be logged -- look up a real path, or reuse the vanilla "
                f"template that already does this job")
    return errs


def check_no_inert_scripted_gui(root: Path) -> list[str]:
    """A scripted GUI whose `effect` block is empty is an inert shell: the
    engine still resolves the GetScriptedGui reference and still runs it, once
    per call site, to do nothing.

    This is mod-agnostic and matters most against a RELEASE STAGING copy,
    which is where it actually fires: `package_release.validate_staging`
    re-runs the validator after debug stripping, so a scripted GUI whose whole
    body was a `debug_log` line shows up here rather than in the upload.

    Found 2026-09-18 reviewing Bulk Construction for release. Its
    `bc_built_log_sgui` existed only to count build calls into debug.log. The
    dev tree was fine; the packaged copy shipped `effect = { }` still wired to
    16 onclick triggers and 10 per-row widget states, so a 10-level press
    across 44 states would have run 440 no-op scripted-GUI executions in every
    subscriber's game. Smart Notifications already had DEV_ONLY_FILES for
    exactly this failure, but that list is gated on its own mod id, so the
    sibling mod inherited none of the protection. A check does not need to be
    told which mod it is looking at."""
    errs = []
    sgui_dir = root / "common" / "scripted_guis"
    if not sgui_dir.is_dir():
        return errs
    for path in sorted(sgui_dir.rglob("*.txt")):
        text = _strip_comments(_read(path))
        for m in re.finditer(r"(\w+)\s*=\s*\{", text):
            name = m.group(1)
            if name != "effect":
                continue
            # Walk to the matching close brace and see if anything is inside.
            depth, i = 1, m.end()
            while i < len(text) and depth:
                depth += (text[i] == "{") - (text[i] == "}")
                i += 1
            if not text[m.end():i - 1].strip():
                rel = path.relative_to(root)
                errs.append(
                    f"{rel}: a scripted GUI has an empty `effect` block -- it "
                    f"would still be resolved and executed at every call site "
                    f"to do nothing. If this is a diagnostic whose body was "
                    f"stripped for release, drop the whole file and its call "
                    f"sites instead of shipping the shell")
    return errs


def check_no_cheat_verbs(root: Path) -> list[str]:
    """Bulk Construction's hard rule, enforced rather than documented: fix the
    UX, never change the rules of the game (spec section 1a). The mod's whole
    claim is that its button is the player's own + button, N times -- which
    stops being true the moment any of these appears in a shipped file."""
    errs = []
    for path in _iter_mod_files(root):
        text = _strip_comments(_read(path))
        for verb, why in CHEAT_VERBS.items():
            if re.search(r"(?<![a-z_])" + verb + r"\s*=", text):
                rel = path.relative_to(root)
                errs.append(f"{rel}: uses `{verb}` -- {why}. This mod does not "
                            f"cheat (docs/bulk-construction-spec.md section 1a)")
    return errs


def run_all(root: Path) -> list[str]:
    SKIPPED.clear()
    defined_loc = load_defined_loc_keys(root)
    errs = []

    # Mod-agnostic: these either apply to any mod in this repo, or no-op
    # cleanly when the directory they inspect doesn't exist.
    errs += check_custom_tooltip_keys(root, defined_loc)
    errs += check_scripted_gui_references(root)
    errs += check_no_inert_scripted_gui(root)
    errs += check_gui_textures_exist(root)
    errs += check_alert_loc_completeness(root, defined_loc)
    errs += check_alert_group_registration(root, defined_loc)
    errs += check_post_notification_targets(root, defined_loc)
    errs += check_law_types_exist_in_vanilla(root)
    errs += check_json_files_have_no_bom(root)
    errs += check_mixed_group_notification_types(root)
    errs += check_notification_loc_completeness(root, defined_loc)
    errs += check_loc_lines_are_well_formed(root)
    errs += check_replaced_loc_still_matches_vanilla(root)
    errs += check_engine_notes_toc_is_current(root)
    errs += check_vanilla_reference_snapshot_is_complete(root)
    errs += check_markdown_links_resolve(root)

    # Smart-Notifications-only: each asserts that specific files or message
    # keys THIS mod owns are present, so against a sibling mod every one of
    # them reports the whole mod as missing. See SMART_NOTIFICATIONS_ID above.
    if read_mod_id(root) == SMART_NOTIFICATIONS_ID:
        errs += check_law_type_dispatch_consistency(root)
        errs += check_full_overrides_match_installed_vanilla(root)
        errs += check_watchlist_spec_tiers(root)
        errs += check_watchlist_spec_group_isolation(root)
        errs += check_mod_group_labels_are_tagged(root)
        errs += check_census_build_not_stale(root)
        errs += check_dev_only_files_are_consistent(root)

    # Bulk-Construction-only: its no-cheat rule is structural, so it is
    # asserted on every run rather than remembered at release time.
    if read_mod_id(root) == BULK_CONSTRUCTION_ID:
        errs += check_no_cheat_verbs(root)
        errs += check_full_overrides_match_installed_vanilla(root)
        errs += check_bc_gui_filename_still_sorts_first(root)
        errs += check_bc_panel_width_matches_vanilla(root)
        errs += check_bc_loc_has_no_nested_arithmetic(root)
        errs += check_bc_loc_has_no_bracket_decoration(root)

    return errs


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errs = run_all(target)
    if errs:
        print("FAIL: cross-reference checks")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    if SKIPPED:
        print(f"PASS (DEGRADED): {len(SKIPPED)} vanilla-dependent check(s) did NOT run.")
        for entry in SKIPPED:
            print(f"  - {entry}")
        sys.exit(0)
    print("PASS: all cross-reference checks (loc keys, scripted_gui folder, "
          "alert_group registration, law-type dispatch consistency, "
          "watchlist spec tiers and group isolation).")
    sys.exit(0)
