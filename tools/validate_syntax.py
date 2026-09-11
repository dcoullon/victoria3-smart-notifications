import sys
from pathlib import Path

import check_references

def validate_file(file_path: Path):
    errors = []
    if file_path.suffix == ".yml":
        raw = file_path.read_bytes()
        if not raw.startswith(b'\xef\xbb\xbf'):
            errors.append("Localization YAML must be encoded as UTF-8 with BOM.")
        lines = raw.decode("utf-8-sig", errors="replace").splitlines()
        if lines and not lines[0].strip().startswith("l_english:"):
            errors.append("First line must start with 'l_english:'.")
        return errors

    # Confirmed against the game's own lexer (2026-09-03): it logs
    # "should be in utf8-bom encoding" for any modded .txt/.gui file missing
    # the BOM, even though it tries to proceed anyway. Enforce it here so
    # that warning never reappears silently.
    raw = file_path.read_bytes()
    if not raw.startswith(b'\xef\xbb\xbf'):
        errors.append(f"{file_path.suffix} file must be encoded as UTF-8 with BOM.")

    content = file_path.read_text(encoding="utf-8-sig")
    curly = 0
    square = 0
    quote = False

    # BUGFIX (2026-09-07, found while adding the first .gui file this repo
    # has ever shipped): comments used to be stripped with a plain
    # `line.split('#')[0]`, which cuts the line at the FIRST '#' regardless
    # of whether it's inside a quoted string. GUI files routinely use
    # in-string formatting codes like "#title", "#clickable", "#header ...#!"
    # -- splitting on those truncated real content (hiding real closing
    # brackets later on the same line) AND desynced the quote-tracker (an
    # opening quote with no closing quote on the truncated remainder), which
    # then miscounts every line after it for the rest of the file. This is
    # exactly the kind of false positive that could make a real syntax error
    # in a LATER file go unnoticed by drowning it in bogus ones -- comment
    # detection must be quote-aware.
    for line_num, line in enumerate(content.splitlines(), start=1):
        for char in line:
            if char == '"':
                quote = not quote
            elif not quote:
                if char == '#':
                    break
                elif char == '{': curly += 1
                elif char == '}': curly -= 1
                elif char == '[': square += 1
                elif char == ']': square -= 1
                if curly < 0:
                    errors.append(f"Line {line_num}: Extra closing '}}'")
                    curly = 0
                if square < 0:
                    errors.append(f"Line {line_num}: Extra closing ']'")
                    square = 0

    if curly != 0: errors.append(f"Mismatch: {curly} unclosed '{{'")
    if square != 0: errors.append(f"Mismatch: {square} unclosed '['")
    errors.extend(check_known_mistake_patterns(content))
    return errors


# --- Known mistake patterns -------------------------------------------------
# Confirmed-real engine errors this project has hit MORE THAN ONCE, each
# time only caught after asking the user to test a broken build. Added
# 2026-09-08 per the user, directly: "how do we prevent you from doing the
# same mistakes over and over again, and not even verifying before sending
# me to test?" -- a human re-reading the code before shipping had already
# failed to catch these several times in one session, so the fix is a
# mechanical check that runs every time, not a promise to look harder.
#
# Each entry here is a class of mistake, not a one-off typo -- these are
# real corners of the Jomini script/dynamic-text system where two
# almost-identical-looking constructs mean different things, confirmed via
# live error.log entries this session:
# - SCOPE.GetRootScope is a generic wrapper needing an explicit per-type
#   cast (.GetCountry, .GetState, ...) chained on immediately -- confirmed
#   by an exhaustive check of every vanilla localization/english/ usage,
#   100% of which cast it. Calling .MakeScope (or anything else) on it
#   directly produced a real "Failed to convert statement" error live.
# - `any_X` (any_law, any_active_law, any_country, ...) is trigger-only;
#   the effect-side iterator is always a DIFFERENTLY NAMED keyword
#   (every_X). Using any_X inside an `effect` block produced a real
#   "Unknown effect any_X" error live.
# - `save_scope_as`/`set_variable`/`remove_variable` are effects; `valid`/
#   `is_valid` blocks in alert_types/scripted_guis are pure triggers.
#   Effects silently do nothing inside a trigger block (no crash, no
#   error at the call site -- just "Event target ... is used but is never
#   set" much later, when something tries to read it) -- confirmed live.
import re

_ANY_TRIGGER_ONLY = [
    "any_law", "any_active_law", "any_country", "any_scope_state",
    "any_scope_country", "any_active_law", "any_scope_play_involved",
    "any_scope_amendment", "any_character_in_exile_pool",
]
_EFFECT_ONLY_KEYWORDS = [
    "save_scope_as", "save_temporary_scope_as", "set_variable",
    "remove_variable", "post_notification", "trigger_event",
    "custom_tooltip", "hidden_effect", "add_variable",
]

def check_known_mistake_patterns(content: str) -> list[str]:
    errors = []

    # 1. SCOPE.GetRootScope must always be immediately followed by a cast
    #    (a `.` then a capitalized Get-style method). Bare `.MakeScope` or
    #    any other chain directly on it is the confirmed-broken pattern.
    for m in re.finditer(r"SCOPE\.GetRootScope\.(\w+)", content):
        if not m.group(1).startswith("Get"):
            line_num = content.count("\n", 0, m.start()) + 1
            errors.append(
                f"Line {line_num}: SCOPE.GetRootScope.{m.group(1)}(...) -- "
                f"GetRootScope must be cast first (e.g. .GetCountry, .GetState) "
                f"before chaining anything else; confirmed real vanilla usage "
                f"never skips this cast."
            )

    # 2. Track brace depth alongside a block-type stack: are we inside an
    #    `effect = {` block, or a `valid =`/`is_valid =`/`limit =` (pure
    #    trigger) block? A nested `limit = {` inside an effect flips back to
    #    trigger context for that nested block; there is no real inverse
    #    (effects cannot appear inside `limit`), so a simple stack of "which
    #    kind of block are we in at this depth" is enough. Walk the file
    #    once, classifying each new block by the keyword immediately before
    #    its opening '{', and flag any_X-in-effect / effect-keyword-in-trigger
    #    as they're encountered.
    stack = []  # list of "effect" | "trigger" | "other" per open '{'
    quote = False
    i = 0
    n = len(content)
    line_num = 1
    pending_keyword = ""
    word_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    while i < n:
        ch = content[i]
        if ch == "\n":
            line_num += 1
        if ch == '"':
            quote = not quote
            i += 1
            continue
        if quote:
            i += 1
            continue
        if ch == '#':
            nl = content.find("\n", i)
            i = nl if nl != -1 else n
            continue
        m = word_re.match(content, i)
        if m:
            word = m.group(0)
            cur_kind = stack[-1] if stack else "other"
            if cur_kind == "effect" and word in _ANY_TRIGGER_ONLY:
                errors.append(
                    f"Line {line_num}: `{word}` used directly inside an "
                    f"`effect` block -- any_X is trigger-only; the effect-side "
                    f"iterator is a differently-named every_X keyword."
                )
            if cur_kind == "trigger" and word in _EFFECT_ONLY_KEYWORDS:
                errors.append(
                    f"Line {line_num}: `{word}` used inside a `valid`/"
                    f"`is_valid`/`limit` (trigger-only) block -- this is an "
                    f"effect and will silently do nothing there."
                )
            i = m.end()
            pending_keyword = word
            continue
        if ch == "{":
            kw = pending_keyword
            if kw == "effect":
                kind = "effect"
            elif kw in ("valid", "is_valid", "limit"):
                kind = "trigger"
            else:
                kind = stack[-1] if stack else "other"
            stack.append(kind)
            pending_keyword = ""
            i += 1
            continue
        if ch == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if ch not in " \t\r\n=":
            pending_keyword = ""
        i += 1

    return errors

# --- Known-good invariants -------------------------------------------------
# Confirmed-correct-in-game behaviour that has been broken by later edits more
# than once. Syntax checking cannot catch these: the regressions were all
# perfectly valid script that silently did the wrong thing. Each entry is
# (file, required substring, why it matters).
#
# The Watchlist is the cautionary tale these exist for. Its row checks were
# broken twice by rewriting `root` (the ROW's country, supplied by the GUI)
# into a player reference, turning "is the player adjacent to this row's
# country" into "is the player adjacent to the player" -- always false, which
# empties the tab. The bulk actions are the opposite case: `root` is NOT a
# usable country there, so they must find the player via is_player +
# save_scope_as. Same-looking expression, opposite correct answers, one file.
# Both directions are asserted so neither can be "fixed" into the other again.
#
# Baseline: the country selector was confirmed working end-to-end in-game on
# 2026-09-07. Everything below is part of that confirmed state.
KNOWN_GOOD = [
    ("common/scripted_guis/watchlist_sgui.txt",
     "is_adjacent_to_country = root",
     "Watchlist Neighbors ROW check must compare the row's country (root) "
     "against the player, not the player against themselves"),
    ("common/scripted_guis/watchlist_sgui.txt",
     "this ?= root",
     "Watchlist Rivals ROW check must compare against root (the row's country)"),
    ("common/on_actions/00_smart_notifications_on_actions.txt",
     "limit = { is_player = yes }",
     "The game-start hook must keep finding the player by trigger -- this is "
     "the one player-identification pattern proven to work in this codebase, "
     "and the bulk actions are modelled on it"),
    # Added 2026-09-07 once the user confirmed the country selector works
    # end-to-end. Both entries below are the mechanism that finally made the
    # bulk buttons work, after three failed approaches (root, a global
    # variable, then this). Do not "simplify" either one away.
    ("common/scripted_guis/watchlist_sgui.txt",
     "save_scope_as = snw_bulk_player",
     "Watchlist BULK actions must find the player with is_player + "
     "save_scope_as. `root` is NOT a usable country in a button-triggered "
     "scripted GUI (proven by the 2026-09-07 root probes: the effect runs, "
     "but the root cannot be resolved as a country)"),
    ("common/scripted_triggers/00_smart_notifications_triggers.txt",
     "NOT = { is_country_type = decentralized }",
     "A decentralized country must never count as watched at RUNTIME either "
     "-- a stale flag on one cannot be cleared by any bulk action, because "
     "every_country does not reach decentralized countries"),
    ("common/scripted_guis/watchlist_sgui.txt",
     "NOT = { is_country_type = decentralized }",
     "Decentralized countries must stay excluded from the Watchlist. They "
     "were the countries Select All appeared to 'miss' -- adjacent for "
     "display but not picked up by the bulk scan. Excluding them is what "
     "makes the displayed list and the bulk actions agree"),
]


def check_known_good(root: Path):
    # Every KNOWN_GOOD entry names a Smart Notifications file, so against a
    # sibling mod in this repo (see smart_ui/README.md) they all report
    # MISSING. Gated on the mod id, not the folder name, so a rename can't
    # quietly turn these regression guards off.
    if check_references.read_mod_id(root) != check_references.SMART_NOTIFICATIONS_ID:
        return []
    errs = []
    for rel, needle, why in KNOWN_GOOD:
        path = root / rel
        if not path.exists():
            errs.append(f"{rel}: MISSING (expected to contain: {needle!r})")
            continue
        if needle not in path.read_text(encoding="utf-8-sig"):
            errs.append(f"{rel}: lost {needle!r}\n      why: {why}")
    return errs


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    has_err = False
    for path in target.rglob("*.*"):
        if path.suffix in [".txt", ".gui", ".yml"] and "tools" not in str(path):
            errs = validate_file(path)
            if errs:
                has_err = True
                print(f"FAIL: {path}")
                for e in errs: print(f"  - {e}")

    kg = check_known_good(target)
    if kg:
        has_err = True
        print("FAIL: known-good invariant broken (confirmed-working behaviour regressed)")
        for e in kg: print(f"  - {e}")

    # Cross-file reference integrity (tools/check_references.py) -- separate
    # module, run automatically here so the existing "always run
    # validate_syntax.py" habit (CLAUDE.md) covers it without a second
    # command to remember.
    ref_errs = check_references.run_all(target)
    if ref_errs:
        has_err = True
        print("FAIL: cross-reference checks (see tools/check_references.py)")
        for e in ref_errs: print(f"  - {e}")

    if not has_err:
        print("PASS: Syntax, brackets, known-good invariants, and cross-references verified.")
    sys.exit(1 if has_err else 0)
