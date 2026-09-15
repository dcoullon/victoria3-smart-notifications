"""
Analyse a notification-census run -- reached via `scan_logs.py --census`.

Reads the `SNW_CENSUS|...` lines a census build wrote to debug.log (see
build_census_mod.py) and joins them against three things:

  1. the build's manifest  -- call site id -> key, file, scope verdict, origin
  2. vanilla's messages    -- per-key notification_type (the VANILLA tier)
  3. this mod's messages   -- per-key notification_type (the SMART NOTIFS tier)

and prints the four things the census exists to answer: which keys actually
fire, how volume grows over the campaign, what the player-visible tier split
looks like vanilla-vs-mod, and how much of the picture is missing.

NEVER loads a log into an LLM context -- debug.log from a full census run runs
to hundreds of MB. This streams the file and prints only aggregates
(CLAUDE.md's Token Budget rule).

WHY THE TIER JOIN IS ENOUGH TO GET BOTH COLUMNS. The mod changes which tier a
notification displays at, not how often it fires, so one instrumented run
yields both:

    volume_vanilla(tier) = sum firings(key) over keys whose VANILLA tier is `tier`
    volume_mod(tier)     = sum firings(key) over keys whose MOD tier is `tier`

The build spec flagged the mod's split families (diplomatic actions, diplo
plays, pact breaks) as the one case where the firing itself differs, needing a
hand-built mod-key -> vanilla-key mapping. Running the census build ALONGSIDE
Smart Notifications removes that need: the mod cannot suppress a vanilla
`post_notification` (its only vanilla overrides are common/messages and two
.gui files), so it mutes vanilla keys by setting `notification_type = none`
and posts its own key in parallel. Both are therefore observed directly, and
the mute falls out of the tier join as a `none` tier. No inferred mapping is
load-bearing anywhere in this report.

LOWER BOUND. 103 vanilla message keys are posted by native engine code with no
`post_notification` call site anywhere in common/ or events/, so nothing can
hook them -- including several of the loudest suspected offenders
(country_attitude_*, country_conscription, invasion_*). Every total here is
therefore a floor, not a count, and the report says so in its own output
rather than leaving it to be remembered later.
"""
import collections
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")
DEFAULT_MANIFEST = (Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3"
                    / "mod" / "smart_notifications_census" / "census_manifest.json")

CENSUS_RE = re.compile(r"SNW_CENSUS\|([PWQ])\|(\d+)\|(\w+)\|(.*?)\s*$")
# re.M matters: without it `$` anchors to end-of-STRING, so scanning a whole
# log file matches only its last line. Caught by the synthetic test.
LOCPROBE_RE = re.compile(r"SNW_LOCPROBE\|(\w+)\|(.*?)[ 	]*$", re.M)
# The date comes from [TimeKeeper.GetCurrentDate.GetString], whose exact
# rendering is a game-side formatting choice ("1836.1.1", "1 January 1836",
# ...). Pull the year out of whatever it produced rather than assuming one
# layout -- and if it produced nothing at all, that is a broken tap, not a
# quiet game, so the report says which.
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
ENTRY_RE = re.compile(r"^(\w+)\s*=\s*\{(.*?)^\}", re.M | re.S)
NTYPE_RE = re.compile(r"notification_type\s*=\s*(\w+)")
TIERS = ["popup", "toast", "feed", "none"]


CATALOG_PATH = Path(__file__).resolve().parent / "message_catalog.json"

_BRACKET_RE = re.compile(r"\[[^\]]*\]")
_CONCEPT_RE = re.compile(r"\$([^$]*)\$")
_MARKUP_RE = re.compile(r"#[a-zA-Z_]+ |#!")


def load_catalog_titles():
    """key -> readable notification title, from tools/message_catalog.json.

    The census log carries only the key. A key is not what a player sees, and
    a chart captioned `country_attitude_improved` is unreadable to anyone who
    has not modded the game -- so the report joins against the static catalog
    and prints the real title.

    These are TEMPLATES: the `[SCOPE...]` calls inside them only resolve inside
    the engine at post time, and script cannot read the rendered string back
    (see docs/engine-notes.md). Dynamic parts collapse to `<>` rather than
    being dropped, so a title stays honestly incomplete instead of looking
    like the whole text.

    Regenerate with `python tools/message_catalog.py`; absent, the report
    simply falls back to bare keys.
    """
    if not CATALOG_PATH.exists():
        return {}

    def flatten(raw):
        text = _BRACKET_RE.sub("<>", raw)
        text = _CONCEPT_RE.sub(lambda m: m.group(1), text)
        return _MARKUP_RE.sub("", text).strip()

    out = {}
    for rec in json.loads(CATALOG_PATH.read_text(encoding="utf-8")):
        raw = rec.get("loc_name")
        if not raw:
            continue
        text = flatten(raw)
        # 35 of 459 titles are almost entirely dynamic once flattened
        # ("<> <>", "<>!"), which tells a reader nothing. The description is
        # more prose and less substitution, so fall back to it rather than
        # print a row of placeholders.
        if len(_BRACKET_RE.sub("", text).replace("<>", "").strip()) < 6:
            desc = rec.get("loc_desc")
            if desc:
                first = flatten(desc).splitlines()[0].strip()
                if first:
                    text = first
        out[rec["key"]] = text
    return out


def per_key_tiers(messages_dir):
    """key -> notification_type, across every messages file in a tree."""
    out = {}
    if not messages_dir.is_dir():
        return out
    for f in sorted(messages_dir.glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        for key, body in ENTRY_RE.findall(text):
            m = NTYPE_RE.search(body)
            if m:
                out[key] = m.group(1)
    return out


def engine_fired_keys(vanilla_tiers):
    """Vanilla keys with no `post_notification` call site anywhere = unhookable."""
    called = set()
    for sub in ("common", "events"):
        base = GAME_ROOT / sub
        if not base.is_dir():
            continue
        for f in base.rglob("*.txt"):
            try:
                text = f.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            if "post_notification" not in text:
                continue
            called.update(re.findall(r"post_notification\s*=\s*(\w+)", text))
    return {k for k in vanilla_tiers if k not in called}


def parse_log(path):
    """Stream debug.log -> (counts, years, malformed). Never holds the file."""
    probes = collections.Counter()       # (key, named scope) -> probe hits
    counts = collections.Counter()       # (scope, key) -> firings
    years = collections.Counter()        # (scope, year) -> firings
    ids_seen = collections.Counter()     # call-site id -> firings
    undated = collections.Counter()
    total = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if "SNW_CENSUS|" not in line:
                continue
            m = CENSUS_RE.search(line)
            if not m:
                continue
            scope, cid, key, datestr = m.groups()
            total += 1
            if scope == "Q":
                # Calibrate probe: a named scope we were not sure was bound
                # turned out to be bound AND to be the player.
                parts = datestr.rsplit("|", 1)
                probes[(key, parts[1] if len(parts) == 2 else "?")] += 1
                datestr = parts[0]
                y = YEAR_RE.search(datestr)
                if y:
                    years[("Q", int(y.group(1)))] += 1
                continue
            counts[(scope, key)] += 1
            ids_seen[(scope, int(cid))] += 1
            y = YEAR_RE.search(datestr)
            if y:
                years[(scope, int(y.group(1)))] += 1
            else:
                undated[scope] += 1
    return counts, years, ids_seen, undated, total, probes


def timeline(logs_dir, manifest_path=None, date_from=None, date_to=None):
    """Chronological list of every logged firing, for checking against the UI.

    The ground-truth check the census cannot do on its own: play with only the
    census mod enabled, screenshot the message feed, then lay this beside it.

      - something on screen with no `P` line here -> we are UNDER-counting
        (a player-scoped call site was classified as world-only, or missed)
      - a `P` line here with nothing on screen    -> we are OVER-counting
        (the guard is firing for a non-player, or the tier is `none`)

    `W` lines are printed too, dimmed by a marker, because a notification that
    shows up on screen while only a `W` line exists is the single most useful
    finding available -- it names a call site whose scope verdict is wrong.
    """
    log = logs_dir / "debug.log"
    if not log.exists():
        print(f"debug.log not found: {log}")
        return 1
    manifest_path = manifest_path or DEFAULT_MANIFEST
    by_id = {}
    if manifest_path.exists():
        by_id = {e["id"]: e for e in json.loads(manifest_path.read_text(encoding="utf-8"))}
    vanilla_tiers = per_key_tiers(GAME_ROOT / "common" / "messages")
    mod_tiers = dict(vanilla_tiers)
    mod_tiers.update(per_key_tiers(REPO_ROOT / "common" / "messages"))

    rows, shown, skipped = [], 0, 0
    with log.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if "SNW_CENSUS|" not in line:
                continue
            m = CENSUS_RE.search(line)
            if not m:
                continue
            scope, cid, key, datestr = m.groups()
            y = YEAR_RE.search(datestr)
            year = int(y.group(1)) if y else None
            if date_from and (year is None or year < date_from):
                skipped += 1
                continue
            if date_to and (year is None or year > date_to):
                skipped += 1
                continue
            shown += 1
            entry = by_id.get(int(cid), {})
            rows.append([
                datestr or "?",
                "PLAYER" if scope == "P" else "world",
                key,
                vanilla_tiers.get(key, mod_tiers.get(key, "-")),
                entry.get("reason", "-"),
            ])
    if not rows:
        print("No SNW_CENSUS lines in range. If the run happened, the tap is broken --")
        print("check the mod is enabled and ordered after Smart Notifications.")
        return 1
    print(_table(rows, ["date", "scope", "key", "tier", "why that scope"]))
    print()
    print(f"{shown:,} firings shown"
          + (f", {skipped:,} outside the date filter" if skipped else ""))
    print()
    print("Compare against the message feed: anything visible on screen that")
    print("appears here only as `world` is a call site we are mis-classifying.")
    return 0


def _table(rows, headers):
    widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    out = ["  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))]
    out.append("-" * len(out[0]))
    for r in rows:
        out.append("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))
    return "\n".join(out)


def _report_localize_probe(logs_dir):
    """Did `Localize()` resolve in script dynamic text?

    If it did, the census can log the notification the player actually READ,
    not just its key. Reported here rather than left for someone to notice in
    debug.log. Printed before the "nothing logged" bail-out, so a run that
    produced probe lines and nothing else still yields its verdict.
    """
    probes = []
    for path in sorted(Path(logs_dir).glob("debug*.log")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        probes.extend(LOCPROBE_RE.findall(text))
    if not probes:
        return
    print()
    print("--- Localize() probe: can we log the rendered text? ---")
    # An unresolved call leaves the raw loc key (or nothing) in place.
    resolved = [(k, v) for k, v in probes
                if v and not v.startswith("notification_")]
    for k, v in probes[:8]:
        print(f"  {k:46} -> {v[:60]!r}")
    if resolved:
        print(f"  VERDICT: WORKS ({len(resolved)}/{len(probes)} rendered). "
              f"Localize() resolves in script dynamic text, so the census can "
              f"log real notification text -- raise --probe-localize.")
    else:
        print(f"  VERDICT: DOES NOT RESOLVE (0/{len(probes)} rendered). "
              f"Expected: .gui and script dynamic text are separate function "
              f"tables (CLAUDE.md). Use the static catalog instead "
              f"(tools/message_catalog.py) and rebuild with --probe-localize 0.")
    print()


def report(logs_dir, manifest_path=None, top=30):
    log = logs_dir / "debug.log"
    if not log.exists():
        print(f"debug.log not found: {log}")
        return 1

    manifest_path = manifest_path or DEFAULT_MANIFEST
    manifest = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        print(f"(note: no census manifest at {manifest_path} -- "
              f"per-call-site detail and the unfired-site check are skipped)")

    vanilla_tiers = per_key_tiers(GAME_ROOT / "common" / "messages")
    mod_tiers = dict(vanilla_tiers)
    mod_tiers.update(per_key_tiers(REPO_ROOT / "common" / "messages"))

    counts, years, ids_seen, undated, total, probes = parse_log(log)
    size_mb = log.stat().st_size / (1024 * 1024)

    print("=" * 72)
    print("NOTIFICATION CENSUS")
    print("=" * 72)
    print(f"debug.log            : {log}  ({size_mb:.1f} MB)")
    print(f"SNW_CENSUS lines     : {total:,}")
    _report_localize_probe(logs_dir)

    if total == 0:
        print()
        print("NOTHING WAS LOGGED. Before concluding the game is quiet, check the")
        print("instrument -- that is far more often the cause:")
        print("  - is the census mod enabled in the playset, ordered AFTER Smart Notifications?")
        print("  - NOT debug mode: `debug_log` writes without it (settled 2026-09-15).")
        print("  - does `python tools/build_census_mod.py` report files written?")
        return 1

    p_years = sorted(y for (s, y) in years if s == "P")
    w_years = sorted(y for (s, y) in years if s == "W")
    all_years = sorted(set(p_years) | set(w_years))
    if all_years:
        print(f"campaign span        : {all_years[0]} -> {all_years[-1]}  "
              f"({all_years[-1] - all_years[0] + 1} years)")
    if undated:
        print(f"UNDATED lines        : {dict(undated)}  <-- the date token did not "
              f"render; per-decade figures below are incomplete")

    p_total = sum(v for (s, _), v in counts.items() if s == "P")
    w_total = sum(v for (s, _), v in counts.items() if s == "W")
    print(f"player-scoped (P)    : {p_total:,}")
    print(f"world (W)            : {w_total:,}")
    print()

    # --- tier split, vanilla vs mod -------------------------------------
    # Split by SCOPE, not merged. A key measured player-side (`P`) and a key
    # only measurable world-side (`W`) answer different questions, and adding
    # them would produce a headline number that cannot be defended: `W` counts
    # every AI country's copy too. The diplomatic families land in the `W`
    # table for BOTH vanilla and the mod -- vanilla's on_diplomatic_action and
    # the mod's own handlers are both rooted on Diplomatic Action, so neither
    # can be player-scoped -- which at least keeps that comparison like-for-like.
    # A key can carry both P and W lines: UNKNOWN-scope sites emit both as a
    # safety net, and a calibrate build emits both everywhere. Where a key has
    # player data, that data is strictly better, so it is excluded from the
    # world table -- which keeps the two tables disjoint and stops the same
    # firing being reported twice under two different meanings.
    p_keys = {key for (s, key) in counts if s == "P"}

    def tier_split(scope):
        v_tier, m_tier = collections.Counter(), collections.Counter()
        mod_only, untiered = 0, 0
        for (s, key), n in counts.items():
            if s != scope:
                continue
            if scope == "W" and key in p_keys:
                continue
            vt, mt = vanilla_tiers.get(key), mod_tiers.get(key)
            if vt:
                v_tier[vt] += n
            elif mt:
                # A key the mod invents. In vanilla these firings do not exist
                # at all, so they contribute NOTHING to the vanilla column --
                # they are reported separately rather than given a fake tier.
                mod_only += n
            else:
                untiered += n
            if mt:
                m_tier[mt] += n
        return v_tier, m_tier, mod_only, untiered

    def print_tier_table(title, scope, note):
        v_tier, m_tier, mod_only, untiered = tier_split(scope)
        if not v_tier and not m_tier:
            return
        print(title)
        print(note)
        rows = [[t, f"{v_tier.get(t, 0):,}", f"{m_tier.get(t, 0):,}"]
                for t in TIERS if v_tier.get(t) or m_tier.get(t)]
        print(_table(rows, ["tier", "vanilla", "Smart Notifications"]))
        v_seen = v_tier["popup"] + v_tier["toast"] + v_tier["feed"]
        m_seen = m_tier["popup"] + m_tier["toast"] + m_tier["feed"]
        v_loud = v_tier["popup"] + v_tier["toast"]
        m_loud = m_tier["popup"] + m_tier["toast"]
        if v_seen:
            print(f"\nsurfaced at all : {v_seen:,} -> {m_seen:,}  "
                  f"({(m_seen - v_seen) / v_seen * 100:+.0f}%)")
        if v_loud:
            print(f"toast or popup  : {v_loud:,} -> {m_loud:,}  "
                  f"({(m_loud - v_loud) / v_loud * 100:+.0f}%)"
                  "   <-- the interrupting kind")
        if mod_only:
            print(f"\n(of the mod column, {mod_only:,} firings are keys the mod "
                  f"invents; they have no vanilla counterpart and so add nothing "
                  f"to the vanilla column)")
        if untiered:
            print(f"({untiered:,} firings of keys with no notification_type found)")
        print()

    print_tier_table(
        "--- What the PLAYER saw, by tier: vanilla vs Smart Notifications ---",
        "P",
        "(player-scoped call sites only -- this is the headline number)")
    print_tier_table(
        "--- World-scoped keys only (NOT what one player saw) ---",
        "W",
        "(call sites that cannot be player-scoped -- chiefly the Diplomatic\n"
        " Play / Diplomatic Action rooted families. Counts every country's\n"
        " copy, so treat as a ratio between the two columns, not a volume.)")

    # --- ranked keys ----------------------------------------------------
    print(f"--- Top {top} keys by player-visible firings ---")
    titles = load_catalog_titles()
    rows = []
    for (scope, key), n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if scope != "P" or len(rows) >= top:
            continue
        rows.append([f"{n:,}", key, vanilla_tiers.get(key, "-"),
                     mod_tiers.get(key, "-"), titles.get(key, "")[:52]])
    print(_table(rows, ["firings", "key", "vanilla", "mod", "what the player sees"])
          if rows else "  (none)")
    if rows and not titles:
        print("  (no titles: run `python tools/message_catalog.py` to build the catalog)")
    print()

    # --- growth curve ---------------------------------------------------
    print("--- Player-visible firings per decade (the growth curve) ---")
    dec = collections.Counter()
    for (scope, y), n in years.items():
        if scope == "P":
            dec[(y // 10) * 10] += n
    if dec:
        peak = max(dec.values())
        rows = []
        for d in sorted(dec):
            bar = "#" * max(1, round(dec[d] / peak * 40))
            rows.append([f"{d}s", f"{dec[d]:,}", bar])
        print(_table(rows, ["decade", "firings", ""]))
    else:
        print("  (no dated lines)")
    print()

    # --- coverage / lower bound ----------------------------------------
    print("--- Coverage: every number above is a LOWER BOUND ---")
    unhookable = engine_fired_keys(vanilla_tiers)
    unhookable_toast = sum(1 for k in unhookable if vanilla_tiers[k] in ("toast", "popup"))
    fired_keys = {k for (s, k) in counts if s == "P"}
    print(f"vanilla message keys total        : {len(vanilla_tiers)}")
    print(f"engine-fired, IMPOSSIBLE to hook  : {len(unhookable)}  "
          f"({unhookable_toast} of them toast/popup)")
    print(f"instrumented call sites           : {len(manifest)}")
    print(f"keys that actually fired (player) : {len(fired_keys)}")
    if manifest:
        by_id = {e["id"]: e for e in manifest}
        never = [e for e in manifest
                 if not ids_seen.get(("P", e["id"])) and not ids_seen.get(("W", e["id"]))]
        print(f"call sites that never fired at all: {len(never)} of {len(manifest)}")
        unknown_sites = [e for e in manifest if e["scope"] == "unknown"]
        if unknown_sites:
            resolved = sum(1 for e in unknown_sites if ids_seen.get(("P", e["id"])))
            note = (f"{resolved} logged player lines, so those ARE country-scoped "
                    f"-- promote them in tools/census_scope_overrides.json"
                    if resolved else
                    "none logged a player line, so either they are not "
                    "country-scoped or they never concerned the player")
            print(f"unresolved-scope sites            : {len(unknown_sites)}  ({note})")
        del by_id
    if probes:
        print("--- PROBE HITS: these call sites CAN be player-scoped after all ---")
        rows = []
        for (key, scope_name), n in sorted(probes.items(), key=lambda kv: -kv[1]):
            rows.append([f"{n:,}", key, f"scope:{scope_name}",
                         vanilla_tiers.get(key, "-")])
        print(_table(rows, ["hits", "key", "bound scope", "tier"]))
        print()
        print("Each row is a non-country call site whose named scope turned out")
        print("to be bound. Add its on_action to ON_ACTION_SCOPES in")
        print("tools/build_census_mod.py, then rebuild for the measurement run.")
        print()
    elif any(s == "Q" for s, _ in years):
        print("(probes ran and none were bound -- those call sites really are unreachable)")
        print()
    print()
    print("Several of the loudest suspected offenders are in the unhookable set")
    print("(country_attitude_*, country_conscription, invasion_*), so the real")
    print("vanilla volume is higher than anything printed here. Say so in the post.")
    return 0


def actor_axis(logs_dir) -> int:
    """Report on the SNW_A3 lines written by
    common/on_actions/07_smart_notifications_actor_axis_probe.txt.

    Answers TODO.md's open question 3(a) with counts: of the diplomatic-action
    toasts a player actually receives, how many would each candidate
    actor-based rule silence? Each rule is logged independently, so all three
    are compared from one run.
    """
    import re
    from collections import Counter

    path = logs_dir / "debug.log"
    if not path.is_file():
        print(f"debug.log not found in {logs_dir}")
        return 1

    firings = Counter()
    verdicts = Counter()          # (cell, rule, verdict) -> n
    actors = Counter()            # (cell, actor) -> n
    line_re = re.compile(r"SNW_A3\|(?P<cell>\w+)\|(?P<rest>.+?)\s*$")
    for raw in path.open(encoding="utf-8", errors="replace"):
        m = line_re.search(raw)
        if not m:
            continue
        cell, rest = m.group("cell"), m.group("rest")
        if rest.startswith("firing"):
            firings[cell] += 1
            am = re.search(r"actor=(.*)$", rest)
            if am:
                actors[(cell, am.group(1).strip())] += 1
        else:
            rm = re.match(r"rule=(\w+)\|verdict=(\w+)", rest)
            if rm:
                verdicts[(cell, rm.group(1), rm.group(2))] += 1

    if not firings:
        print("No SNW_A3 lines found.")
        print("  Verify the instrument before concluding nothing fired:")
        print("  - is 07_smart_notifications_actor_axis_probe.txt in the dev mod folder?")
        print("  - did any diplomatic action aimed at you or a watched country occur?")
        print("  - do SNW_FILTER|diplomatic_action lines appear at all?")
        return 1

    RULES = {
        "rank": "actor is below major_power",
        "relevance": "actor has no diplomatic relevance to the recipient",
        "type": "actor is not a `recognized` country",
    }
    print("=== Actor-axis measurement (TODO.md open question 3a) ===")
    print("How many of the toasts you actually get would each candidate rule silence?\n")
    for cell in sorted(firings):
        total = firings[cell]
        print(f"{cell}: {total} firings that currently reach a toast")
        for rule, desc in RULES.items():
            quiet = verdicts.get((cell, rule, "quiet"), 0)
            keep = verdicts.get((cell, rule, "keep"), 0)
            seen = quiet + keep
            if not seen:
                print(f"  {rule:10s} no verdicts logged")
                continue
            pct = 100.0 * quiet / seen
            flag = ""
            if seen != total:
                flag = f"  [!] {seen} verdicts vs {total} firings -- scope:actor missing on some"
            print(f"  {rule:10s} would quiet {quiet:5d} of {seen:5d}  ({pct:5.1f}%)   {desc}{flag}")
        print()

    print("Top actors, by how often they reached you:")
    for (cell, actor), n in actors.most_common(15):
        print(f"  {n:5d}  {cell:11s} {actor}")
    print("\nReading this: a high 'would quiet' percentage means the rule is")
    print("effective but also that it is doing a lot -- check the top actors above")
    print("to see whether the countries it silences are ones you would want to hear")
    print("from. The rule judges the sender, never the message, so anything that")
    print("actor does would be quieted, including a rivalry declaration.")
    return 0
