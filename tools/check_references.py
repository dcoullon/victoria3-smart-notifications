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
import re
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".gui"}
VANILLA_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")


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
    for path in root.rglob("*.*"):
        if (
            path.suffix in TEXT_SUFFIXES
            and "tools" not in path.parts
            and ".git" not in path.parts
            and "reference" not in path.parts
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
        print(f"  (skipped: vanilla install not found at {VANILLA_ROOT})")
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
    for our_rel, snapshot_rel in FULL_OVERRIDE_FILES:
        installed = VANILLA_ROOT / our_rel
        if not installed.is_file():
            print(f"  (skipped: vanilla install file not found at {installed})")
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
    # F2 -- diplomatic plays, three tiers per family.
    "smart_notifications_diplo_play_start_player": "popup",
    "smart_notifications_diplo_play_start_watched": "toast",
    "smart_notifications_diplo_play_start_quiet": "feed",
    "smart_notifications_diplo_play_join_side_player": "popup",
    "smart_notifications_diplo_play_join_side_watched": "toast",
    "smart_notifications_diplo_play_join_side_quiet": "feed",
    "smart_notifications_diplo_play_war_start_player": "popup",
    "smart_notifications_diplo_play_war_start_watched": "toast",
    "smart_notifications_diplo_play_war_start_quiet": "feed",
    # F7 -- subject released, unchanged by the spec but pinned so it cannot
    # drift silently.
    "smart_notifications_diplo_play_subject_released_watched": "toast",
    "smart_notifications_diplo_play_subject_released_quiet": "none",
    # F9 -- war goals.
    "smart_notifications_wargoal_added_player": "toast",
    "smart_notifications_wargoal_added_other": "feed",
    "smart_notifications_wargoal_removed_player": "toast",
    "smart_notifications_wargoal_removed_other": "feed",
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
    "smart_notifications_wargoal_player_group": {
        "smart_notifications_wargoal_added_player",
        "smart_notifications_wargoal_removed_player",
    },
    "smart_notifications_wargoal_other_group": {
        "smart_notifications_wargoal_added_other",
        "smart_notifications_wargoal_removed_other",
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
    "wargoal_added": "none",
    "wargoal_removed": "none",
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


def run_all(root: Path) -> list[str]:
    defined_loc = load_defined_loc_keys(root)
    errs = []
    errs += check_custom_tooltip_keys(root, defined_loc)
    errs += check_scripted_gui_references(root)
    errs += check_alert_loc_completeness(root, defined_loc)
    errs += check_alert_group_registration(root, defined_loc)
    errs += check_post_notification_targets(root, defined_loc)
    errs += check_law_type_dispatch_consistency(root)
    errs += check_law_types_exist_in_vanilla(root)
    errs += check_json_files_have_no_bom(root)
    errs += check_full_overrides_match_installed_vanilla(root)
    errs += check_mixed_group_notification_types(root)
    errs += check_watchlist_spec_tiers(root)
    errs += check_watchlist_spec_group_isolation(root)
    errs += check_mod_group_labels_are_tagged(root)
    errs += check_notification_loc_completeness(root, defined_loc)
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
    print("PASS: all cross-reference checks (loc keys, scripted_gui folder, "
          "alert_group registration, law-type dispatch consistency, "
          "watchlist spec tiers and group isolation).")
    sys.exit(0)
