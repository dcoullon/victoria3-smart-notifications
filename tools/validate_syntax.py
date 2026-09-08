import sys
from pathlib import Path

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
    return errors

# --- Known-good invariants -------------------------------------------------
# Confirmed-correct-in-game behaviour that has been broken by later edits more
# than once. Syntax checking cannot catch these: the regressions were all
# perfectly valid script that silently did the wrong thing. Each entry is
# (file, required substring, why it matters).
#
# The Watchlist row checks in particular have now been broken twice by
# rewriting `root` (the ROW's country, supplied by the GUI) into the global
# player pointer, which turns "is the player adjacent to this row's country"
# into "is the player adjacent to the player" -- always false, empties the
# tab. The bulk actions are the opposite case: they genuinely need the global
# pointer, because `root` is NOT reliably the player there. Both directions
# are asserted so neither can be "fixed" into the other again.
KNOWN_GOOD = [
    ("common/scripted_guis/watchlist_sgui.txt",
     "is_adjacent_to_country = root",
     "Watchlist Neighbors ROW check must compare the row's country (root) "
     "against the player, not the player against themselves"),
    ("common/scripted_guis/watchlist_sgui.txt",
     "this ?= root",
     "Watchlist Rivals ROW check must compare against root (the row's country)"),
    ("common/scripted_guis/watchlist_sgui.txt",
     "is_adjacent_to_country = global_var:smart_notifications_player_country",
     "Watchlist Neighbors BULK actions must use the global player pointer -- "
     "root is not reliably the player in a button-triggered scripted GUI"),
    ("common/on_actions/00_smart_notifications_on_actions.txt",
     "set_global_variable = {",
     "The global player pointer must still be set at campaign start, or the "
     "Watchlist bulk actions silently do nothing on a fresh campaign"),
]


def check_known_good(root: Path):
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

    if not has_err:
        print("PASS: Syntax, brackets and known-good invariants verified.")
    sys.exit(1 if has_err else 0)
