"""Smart Notifications: write the population-in-events overrides for the ten
non-English languages, from each language's OWN vanilla text.

    python tools/gen_sn_event_context.py           write all ten files
    python tools/gen_sn_event_context.py --check   exit 1 if any file is stale,
                                                   or the rule no longer
                                                   reproduces English

The feature (shipped English-only in 0.40) replaces seven vanilla loc keys.
Each language words them differently -- Chinese puts the state first, German
quotes it, Russian wraps it in a tooltip block, Polish puts the filter in
brackets -- so a translation of the English override would be wrong in all of
them. Instead one rule is applied to every language's own vanilla strings:

- POP_EFFECT_FILTER: vanilla text + the size block (language-neutral: it only
  calls SMART_NOTIFICATIONS_EVT_SIZE_* keys). The block is taken from the
  hand-written English override, so English stays the single source.
- ADD_RADICALS_IN_STATE_THIRD / ADD_LOYALISTS_IN_STATE_THIRD: vanilla text
  with the state's population inserted right after the state name.
- The four POP_EFFECT_FILTER_* sub-keys: vanilla text, unchanged (overriding
  the parent means they must live in the same file).
- The seven SMART_NOTIFICATIONS_EVT_SIZE_* keys: the English expressions with
  this language's word for "nationwide".

Proof the rule is right: applied to ENGLISH vanilla it must reproduce the
hand-written English override value for value. --check fails if it does not,
and refuses to write anything either.

After a game patch, rerun this. --check (also run by validate_syntax.py via
check_references.py) fails as soon as a patch changes any of these vanilla
strings in any language, so the overrides cannot silently go stale.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOC = REPO / "smart_notifications" / "localization" / "replace"
ENGLISH = LOC / "english" / "smart_notifications_event_context_l_english.yml"
VANILLA_LOC = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game\localization")

LANGS = ["french", "german", "spanish", "braz_por", "polish", "russian",
         "simp_chinese", "japanese", "korean", "turkish"]

FILTER = "POP_EFFECT_FILTER"
STATE_KEYS = ["ADD_RADICALS_IN_STATE_THIRD", "ADD_LOYALISTS_IN_STATE_THIRD"]
SUB_KEYS = ["POP_EFFECT_FILTER_INTEREST_GROUP", "POP_EFFECT_FILTER_CULTURE",
            "POP_EFFECT_FILTER_RELIGION", "POP_EFFECT_FILTER_POP_TYPE"]
REPLACED = [FILTER] + STATE_KEYS + SUB_KEYS

# Number expression for each of our own size keys.
SIZE_EXPR = {
    "SMART_NOTIFICATIONS_EVT_SIZE_IG": "[InterestGroup.GetPopulation|K]",
    "SMART_NOTIFICATIONS_EVT_SIZE_CULTURE": "[Culture.GetPopulation(GetPlayer)|K]",
    "SMART_NOTIFICATIONS_EVT_SIZE_RELIGION": "[Religion.GetPopulation(GetPlayer)|K]",
    "SMART_NOTIFICATIONS_EVT_SIZE_POPTYPE": "[PopType.GetPopulation(GetPlayer)|K]",
    "SMART_NOTIFICATIONS_EVT_SIZE_STRATA_LOWER": "[GetTrendValue(GetPlayer.GetLowerStrataPopulationTrend)|K]",
    "SMART_NOTIFICATIONS_EVT_SIZE_STRATA_MIDDLE": "[GetTrendValue(GetPlayer.GetMiddleStrataPopulationTrend)|K]",
    "SMART_NOTIFICATIONS_EVT_SIZE_STRATA_UPPER": "[GetTrendValue(GetPlayer.GetUpperStrataPopulationTrend)|K]",
}
STATE_EXPR = "[STATE.GetPopulationSize|K]"

# (nationwide template, inhabitants template); @N@ is the bolded number.
# Bracket style follows each language's own vanilla text: full-width in
# Chinese and Japanese, ASCII elsewhere (Korean vanilla uses ASCII).
WORDS = {
    "english": (" (@N@ nationwide)", " (@N@ inhabitants)"),
    "french": (" (@N@ dans tout le pays)", " (@N@ habitants)"),
    "german": (" (@N@ landesweit)", " (@N@ Einwohner)"),
    "spanish": (" (@N@ en todo el país)", " (@N@ habitantes)"),
    "braz_por": (" (@N@ em todo o país)", " (@N@ habitantes)"),
    "polish": (" (@N@ w całym kraju)", " (@N@ mieszkańców)"),
    "russian": (" (@N@ по всей стране)", " (@N@ жителей)"),
    "simp_chinese": ("（全国@N@）", "（人口@N@）"),
    "japanese": ("（全国で@N@）", "（人口@N@）"),
    "korean": (" (전국 @N@)", " (인구 @N@)"),
    "turkish": (" (ülke genelinde @N@)", " (@N@ nüfus)"),
}

# Where the state's name ends, in each form vanilla writes it. Exactly one
# must match per string, or the generator stops.
STATE_NAME = re.compile(
    r"#tooltippable_name #tooltip:\[STATE\.GetTooltipTag\][^#]*?#!#!"  # russian
    r"|\[STATE\.GetName\]“"                                            # german
    r"|\[STATE\.GetName\]")

LINE = re.compile(r'^\s*([A-Za-z0-9_]+)(:\d*)\s*"(.*)"\s*$')


def bold(expr: str) -> str:
    return "#b " + expr + "#!"


def vanilla(lang: str) -> dict:
    """{key: value} for the seven replaced keys, from the installed game."""
    out = {}
    for path in sorted((VANILLA_LOC / lang).rglob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            m = LINE.match(line)
            if m and m.group(1) in REPLACED:
                if m.group(1) in out:
                    raise SystemExit(f"{lang}: {m.group(1)} defined twice in vanilla")
                out[m.group(1)] = m.group(3)
    missing = [k for k in REPLACED if k not in out]
    if missing:
        raise SystemExit(f"{lang}: vanilla no longer defines {', '.join(missing)}")
    return out


def english_override() -> dict:
    out = {}
    for line in ENGLISH.read_text(encoding="utf-8-sig").splitlines():
        m = LINE.match(line)
        if m:
            out[m.group(1)] = (m.group(2), m.group(3))
    return out


def size_block() -> str:
    """The language-neutral tail English appends to POP_EFFECT_FILTER."""
    ours = english_override()[FILTER][1]
    van = vanilla("english")[FILTER]
    if not ours.startswith(van):
        raise SystemExit("English POP_EFFECT_FILTER override no longer starts with "
                         "vanilla's text -- re-derive it by hand first")
    return ours[len(van):]


def render_values(lang: str, block: str) -> dict:
    van = vanilla(lang)
    nationwide, inhabitants = WORDS[lang]
    # Vanilla ships the seven replaced keys with a bare ":" (no version
    # number); matched, as the English override does.
    vals = {FILTER: (":", van[FILTER] + block)}
    for key in STATE_KEYS:
        hits = list(STATE_NAME.finditer(van[key]))
        if len(hits) != 1:
            raise SystemExit(f"{lang}: {key} has {len(hits)} state names, expected 1: "
                             f"{van[key]!r}")
        end = hits[0].end()
        insert = inhabitants.replace("@N@", bold(STATE_EXPR))
        vals[key] = (":", van[key][:end] + insert + van[key][end:])
    for key in SUB_KEYS:
        vals[key] = (":", van[key])
    for key, expr in SIZE_EXPR.items():
        vals[key] = (":0", nationwide.replace("@N@", bold(expr)))
    return vals


def render_file(lang: str, block: str) -> str:
    vals = render_values(lang, block)
    lines = ["l_%s:" % lang,
             " # GENERATED by tools/gen_sn_event_context.py from this language's",
             " # vanilla text. Do not edit; rerun the script (rationale and the",
             " # hand-written source of truth: replace/english/)."]
    for key in REPLACED + list(SIZE_EXPR):
        ver, value = vals[key]
        lines.append(' %s%s "%s"' % (key, ver, value))
    return "\ufeff" + "\n".join(lines) + "\n"


def english_matches(block: str) -> list:
    """The rule applied to English vanilla must give the hand-written file."""
    want = english_override()
    got = render_values("english", block)
    errs = []
    for key, (ver, value) in got.items():
        if key not in want:
            errs.append(f"English override lacks {key}")
        elif want[key][0] != ver:
            errs.append(f"rule writes {key}{ver} but English has {key}{want[key][0]}")
        elif want[key][1] != value:
            errs.append(f"rule does not reproduce English {key}:\n  hand: {want[key][1]}\n  rule: {value}")
    return errs


def main(argv) -> int:
    if not VANILLA_LOC.is_dir():
        print(f"vanilla localization not found at {VANILLA_LOC}")
        return 2
    block = size_block()
    errs = english_matches(block)
    if errs:
        print("\n".join(errs))
        return 1
    stale = []
    for lang in LANGS:
        text = render_file(lang, block)
        out = LOC / lang / f"smart_notifications_event_context_l_{lang}.yml"
        current = out.read_text(encoding="utf-8") if out.is_file() else None
        if current == text:
            continue
        if "--check" in argv:
            stale.append(str(out.relative_to(REPO)))
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {out.relative_to(REPO)}")
    if stale:
        print("stale (rerun python tools/gen_sn_event_context.py): " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
