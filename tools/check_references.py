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
    for path in root.rglob("*.*"):
        if path.suffix in TEXT_SUFFIXES and "tools" not in path.parts and ".git" not in path.parts:
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


def run_all(root: Path) -> list[str]:
    defined_loc = load_defined_loc_keys(root)
    errs = []
    errs += check_custom_tooltip_keys(root, defined_loc)
    errs += check_scripted_gui_references(root)
    errs += check_alert_loc_completeness(root, defined_loc)
    errs += check_alert_group_registration(root, defined_loc)
    errs += check_law_type_dispatch_consistency(root)
    errs += check_law_types_exist_in_vanilla(root)
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
          "alert_group registration, law-type dispatch consistency).")
    sys.exit(0)
