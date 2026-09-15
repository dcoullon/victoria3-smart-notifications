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
PROXY_RE = re.compile(r"SNW_PROXY\|([PW])\|(\w+)\|(.*?)[ \t]*$", re.M)
LOCPROBE_RE = re.compile(r"SNW_LOCPROBE\|(\w+)\|(.*?)[ 	]*$", re.M)
# The date comes from [TimeKeeper.GetCurrentDate.GetString], whose exact
# rendering is a game-side formatting choice ("1836.1.1", "1 January 1836",
# ...). Pull the year out of whatever it produced rather than assuming one
# layout -- and if it produced nothing at all, that is a broken tap, not a
# quiet game, so the report says which.
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
ENTRY_RE = re.compile(r"^(\w+)\s*=\s*\{(.*?)^\}", re.M | re.S)
NTYPE_RE = re.compile(r"notification_type\s*=\s*(\w+)")
COMMENT_RE = re.compile(r"#.*")
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
        # Strip `#` comments first. Without this the parser reads commented-out
        # config as live: diplomatic_action_notification carries a comment
        # recording that its former siblings "are still notification_type =
        # toast", and NTYPE_RE takes the first match in the body -- so the key
        # the mod MUTES was reported as a toast, in the very table the post's
        # vanilla-vs-mod comparison is built from. SECOND copy of this bug; the
        # first was fixed in compare_notification_settings.py the same day, and
        # this one survived because the two tools parse the same files through
        # separate code.
        text = COMMENT_RE.sub(
            "", f.read_text(encoding="utf-8-sig", errors="replace"))
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


def debug_logs(logs_dir):
    """Every debug log, oldest first.

    Victoria 3 rotates debug.log at ~512KB DURING a session, keeping
    debug.1.log..debug.5.log. Reading only debug.log therefore reads only the
    last slice: on the 2026-09-15 calibrate run that was 762 of 7,842 census
    lines, a 90% undercount that looked like a complete result.

    Highest-numbered file is the oldest, so iterate .5 -> .1 -> current.

    NOTE the hard limit this implies: six files x ~512KB is roughly 3MB of
    total capture per session. A long measure run WILL exceed that and silently
    lose its earliest years. Run tools/log_archiver.py alongside the game to
    capture continuously.
    """
    logs_dir = Path(logs_dir)
    rotated = []
    for f in logs_dir.glob("debug.*.log"):
        stem = f.name[len("debug."):-len(".log")]
        if stem.isdigit():
            rotated.append((int(stem), f))
    ordered = [f for _, f in sorted(rotated, reverse=True)]
    current = logs_dir / "debug.log"
    if current.exists():
        ordered.append(current)
    return ordered


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
    logs = debug_logs(logs_dir)
    if not logs:
        print(f"no debug*.log found in: {logs_dir}")
        return 1
    manifest_path = manifest_path or DEFAULT_MANIFEST
    by_id = {}
    if manifest_path.exists():
        by_id = {e["id"]: e for e in json.loads(manifest_path.read_text(encoding="utf-8"))}
    vanilla_tiers = per_key_tiers(GAME_ROOT / "common" / "messages")
    mod_tiers = dict(vanilla_tiers)
    mod_tiers.update(per_key_tiers(REPO_ROOT / "common" / "messages"))

    rows, shown, skipped = [], 0, 0
    for log in logs:
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
    for path in debug_logs(logs_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        probes.extend(LOCPROBE_RE.findall(text))
    if not probes:
        return
    print()
    print("--- Localize() probe: can we log the rendered text? ---")
    # Three outcomes, not two. The call can fail outright, OR resolve the loc
    # key but render every [SCOPE...] substitution empty -- which is what
    # actually happened on 2026-09-15: "exile_notification" came back as
    # " exiled from ." The notification's own scopes are bound by the engine
    # when it builds the message, not in the effect scope we log from, so the
    # substitutions have nothing to read. Reporting that as WORKS would send
    # the next session off to raise the probe count for no gain.
    unresolved = [(k, v) for k, v in probes
                  if not v or v.startswith("notification_")]
    rendered = [(k, v) for k, v in probes if (k, v) not in unresolved]

    # Did the SUBSTITUTIONS fill in, or only the static skeleton survive?
    # Comparing against real words is not enough: "Failed Assassination
    # Attempt on" is all static template text with an empty [SCOPE] after it.
    # The test that works is to strip every [...] out of the catalog template
    # and see whether the render says any more than that skeleton does.
    catalog = {}
    if CATALOG_PATH.exists():
        catalog = {r["key"]: (r.get("loc_name") or "")
                   for r in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))}

    def norm(s):
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    def substitutions_filled(key, value):
        template = catalog.get(key)
        if not template:
            return True          # cannot tell; do not claim it is empty
        skeleton = norm(re.sub(r"\[[^\]]*\]", " ", template))
        return norm(value) != skeleton

    empty = [(k, v) for k, v in rendered if not substitutions_filled(k, v)]
    seen = set()
    for k, v in probes:
        if k in seen:
            continue
        seen.add(k)
        print(f"  {k:46} -> {v[:60]!r}")
        if len(seen) >= 6:
            break

    if not rendered:
        print(f"  VERDICT: DOES NOT RESOLVE (0/{len(probes)}). Expected -- .gui and "
              f"script dynamic text are separate function tables (CLAUDE.md). "
              f"Use the static catalog and rebuild with --probe-localize 0.")
    elif len(empty) == len(rendered):
        print(f"  VERDICT: RESOLVES, BUT RENDERS EMPTY ({len(rendered)}/{len(probes)} "
              f"resolved, all with blank substitutions).")
        print("  Localize() IS available in script dynamic text -- worth knowing, and")
        print("  it contradicts the assumption that .gui-only functions never cross.")
        print("  But the notification's scopes are bound by the engine when it builds")
        print("  the message, not in the effect scope we log from, so every [SCOPE...]")
        print("  comes back blank. The static catalog is strictly better here: it at")
        print("  least marks where the dynamic parts go. Rebuild with")
        print("  --probe-localize 0 for the measure run; these lines are pure noise.")
    else:
        print(f"  VERDICT: WORKS WITH REAL TEXT ({len(rendered) - len(empty)} of "
              f"{len(probes)} rendered with live substitutions). The census can log "
              f"what the player actually read -- raise --probe-localize.")
    print()


def _report_proxy(logs_dir):
    """Counts for engine-fired keys, from the proxy on_actions in
    common/on_actions/08_smart_notifications_engine_proxy.txt.

    Kept in its own table and never added to the census totals. A proxy counts
    the EVENT behind a notification, not the notification: the engine may apply
    display conditions we cannot see, so these are an UPPER bound, the opposite
    direction of error from the census's lower bound. Adding the two would
    produce a number that is neither.
    """
    counts = collections.Counter()
    for path in debug_logs(logs_dir):
        try:
            with path.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "SNW_PROXY|" not in line:
                        continue
                    m = PROXY_RE.search(line)
                    if m:
                        counts[(m.group(1), m.group(2))] += 1
        except OSError:
            continue
    if not counts:
        return
    titles = load_catalog_titles()
    print("--- Engine-fired keys, counted via proxy on_actions ---")
    print("  UPPER bound: counts the event, not the notification. Never added")
    print("  to the census totals above.")
    keys = sorted({k for _, k in counts})
    rows = []
    anomalies = []
    for key in sorted(keys, key=lambda k: -counts[("W", k)]):
        p_n = counts[("P", key)]
        w_n = counts[("W", key)]
        # Every hook writes its W line unconditionally and its P line only as
        # a subset, so W < P is impossible in a sound run. If it happens the
        # instrument is wrong -- say so rather than print a negative count.
        if w_n < p_n:
            anomalies.append((key, p_n, w_n))
            others = "?"
        else:
            others = f"{w_n - p_n:,}"
        rows.append([f"{p_n:,}", f"{w_n:,}", others, key,
                     titles.get(key, "")[:44]])
    print(_table(rows, ["you", "world", "others", "key", "what the player sees"]))
    for key, p_n, w_n in anomalies:
        print(f"  !! {key}: {p_n} player lines but only {w_n} world lines. "
              f"Every P is a subset of W, so the hook is wrong -- do not "
              f"trust this row.")
    print("  'others' is world minus you -- for the revolution and secession")
    print("  families that column IS the noise: other countries' events.")
    print()


def instrument_confidence(logs_dir, manifest):
    """How much of the instrument has this run actually exercised?

    Added 2026-09-15 because the user pushed back, correctly: a proxy hook had
    just been found silently broken, and "16 keys cross-check" says nothing
    about the other 580 sites.

    Two questions, deliberately kept apart:

      - Is each GUARD MECHANISM sound? There are only a handful, and the census
        generates every site from one template per kind, so one site producing
        a player line proves that mechanism for all sites using it. Strong
        evidence, available immediately.
      - Has each individual SITE been exercised? Mostly not, and no amount of
        better code fixes that -- a hook for an event that did not occur is
        untestable. It improves with run length, so the figure is printed
        rather than glossed over.

    The dangerous cell is a mechanism that FIRED but produced zero player
    lines: that is exactly what a silently-broken guard looks like.
    """
    ids_seen, p_ids = set(), set()
    pat = re.compile(r"SNW_CENSUS\|([PW])\|(\d+)\|")
    for path in debug_logs(logs_dir):
        try:
            with path.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = pat.search(line)
                    if m:
                        ids_seen.add(int(m.group(2)))
                        if m.group(1) == "P":
                            p_ids.add(int(m.group(2)))
        except OSError:
            continue
    if not ids_seen:
        return

    by_kind = collections.defaultdict(lambda: {"sites": 0, "fired": 0, "p": 0})
    for e in manifest:
        reach = e.get("reach")
        kind = ("named-scope" if reach and reach.startswith("scope:")
                else "reach-iterator" if reach
                else "direct-" + str(e.get("scope", "?")))
        g = by_kind[kind]
        g["sites"] += 1
        g["fired"] += e["id"] in ids_seen
        g["p"] += e["id"] in p_ids

    print("--- Instrument confidence ---")
    rows = []
    for kind in sorted(by_kind):
        g = by_kind[kind]
        if g["p"]:
            v = "mechanism PROVEN"
        elif "non_country" in kind:
            v = "world-only by design"
        elif g["fired"]:
            v = "fired, no player line -- CHECK"
        else:
            v = "never fired -- unproven"
        rows.append([kind, g["sites"], g["fired"], g["p"], v])
    print(_table(rows, ["guard kind", "sites", "fired", "with P", "verdict"]))
    fired = sum(g["fired"] for g in by_kind.values())
    total = sum(g["sites"] for g in by_kind.values()) or 1
    print(f"  {fired} of {total} call sites fired at least once "
          f"({fired / total * 100:.0f}%).")
    print("  The rest are unproven only because their events did not happen in")
    print("  this run -- that improves with length, not with better code.")
    print()


def report(logs_dir, manifest_path=None, top=30):
    logs = debug_logs(logs_dir)
    if not logs:
        print(f"no debug*.log found in: {logs_dir}")
        return 1
    log = logs[-1]

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

    # Fold over every rotated log, not just the current one -- see debug_logs().
    counts, years, ids_seen, undated, probes = (collections.Counter() for _ in range(5))
    total = 0
    for one in logs:
        c, y, i, u, n, pr = parse_log(one)
        counts.update(c); years.update(y); ids_seen.update(i)
        undated.update(u); probes.update(pr); total += n
    size_mb = sum(f.stat().st_size for f in logs) / (1024 * 1024)

    print("=" * 72)
    print("NOTIFICATION CENSUS")
    print("=" * 72)
    print(f"debug.log            : {log}  ({size_mb:.1f} MB)")
    print(f"debug logs read      : {len(logs)} "
          f"({', '.join(f.name for f in logs)})")
    print(f"SNW_CENSUS lines     : {total:,}")
    _report_localize_probe(logs_dir)
    _report_proxy(logs_dir)
    cross_check(logs_dir)
    if manifest:
        instrument_confidence(logs_dir, manifest)

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


# --------------------------------------------------------------------------
# Cross-check: the census against the mod's OTHER, independent loggers.
# --------------------------------------------------------------------------

SNWLOG_RE = re.compile(r"SNW_LOG\|(\w+)")
CENSUS_XR = re.compile(r"SNW_CENSUS\|([PW])\|\d+\|(\w+)\|")


def cross_check(logs_dir):
    """Validate the census against `01_smart_notifications_logger.txt`.

    Why this is worth more than another playtest: that logger was written
    months earlier, hooks different on_actions, and counts independently. Where
    the two overlap they must agree, and nobody has to look at anything.

    The one subtlety, and it is the whole reason this needs code rather than a
    glance: some logger hooks are `is_player`-guarded and some are not. A
    guarded hook must match the census's **P** count; an unguarded one must
    match **W**. Comparing everything to W reports false disagreements -- which
    is exactly what the first manual pass did on 2026-09-15 before the guards
    were checked.

    Run automatically as part of `scan_logs.py --census`.
    """
    logger_src = REPO_ROOT / "common" / "on_actions" / "01_smart_notifications_logger.txt"
    if not logger_src.exists():
        return
    text = logger_src.read_text(encoding="utf-8-sig")

    # Which logged keys sit under an is_player guard?
    #
    # Brace-depth tracking was tried first and got this wrong: in
    # `limit = { is_player = yes }` the brace opens and closes on one line, so
    # the guard looked like it had already ended by the time the debug_log on
    # the NEXT line was read. It reported national_awakening_started as
    # unguarded when it is guarded three scopes deep.
    #
    # The file's actual shape makes this simpler than parsing. Each key has its
    # own small `smart_notifications_log_<x> = { ... }` handler, so the guard
    # question is just "does this handler mention is_player at all".
    guarded = set()
    for block in re.split(r"\n(?=smart_notifications_log_\w+\s*=\s*\{)", text):
        body = re.sub(r"#.*", "", block)
        if "is_player" not in body:
            continue
        guarded.update(SNWLOG_RE.findall(body))

    census_p, census_w, snwlog = (collections.Counter() for _ in range(3))
    for path in debug_logs(logs_dir):
        try:
            with path.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = CENSUS_XR.search(line)
                    if m:
                        (census_p if m.group(1) == "P" else census_w)[m.group(2)] += 1
                    elif "SNW_LOG|" in line:
                        m2 = SNWLOG_RE.search(line)
                        if m2:
                            snwlog[m2.group(1)] += 1
        except OSError:
            continue
    if not snwlog:
        return

    print("--- Cross-check: census vs the independent SNW_LOG logger ---")
    print("  Two instruments, different hooks, same run. Where they overlap")
    print("  they must agree. Player-guarded logger hooks compare to P, the")
    print("  rest to W.")
    rows, agree, differ = [], 0, 0
    for key, n in snwlog.most_common():
        is_guarded = key in guarded
        expect = census_p[key] if is_guarded else census_w[key]
        ok = (expect == n)
        agree += ok
        differ += (not ok)
        rows.append([f"{n:,}", f"{expect:,}", "P" if is_guarded else "W",
                     "match" if ok else "DIFFERS", key])
    print(_table(rows, ["SNW_LOG", "census", "vs", "verdict", "key"]))
    print(f"  {agree} agree, {differ} differ, of {len(snwlog)} shared keys")
    if differ:
        print("  !! A disagreement means one of the two instruments is wrong.")
        print("     Do not publish a count for a differing key until it is")
        print("     resolved -- check the logger's guard first, then the")
        print("     census site's scope verdict.")
    else:
        print("  No disagreements: the census reproduces an independently")
        print("  written instrument exactly, on every shared key.")
    print()
