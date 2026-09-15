"""
Measure what the census MISSED, by diffing what the player actually saw
against what the instrumentation logged.

Why this exists
---------------
The census counts `post_notification` call sites. 103 of the game's 468
notification keys have no call site at all, so the census cannot see them, and
every figure it produces is a lower bound. Saying "it's a lower bound" in a
Reddit post is a hand-wave. Saying "the instrumentation caught 78% of what
actually appeared on screen, and here is the measured gap" is a finding.

That number needs one thing the logs cannot supply: a record of what was
really on screen. The user takes 2-3 fully-scrolled feed screenshots at noted
in-game dates during the census run; those become the observations file, and
this does the diff.

Observations file (JSON)
------------------------
    {
      "country": "SWE",
      "observations": [
        {"date": "1840.1.1", "source": "feed screenshot",
         "keys": ["country_attitude_improved", "colony_complete"],
         "unidentified": 2}
      ]
    }

`keys` are message keys read off the screenshot. `unidentified` counts entries
that could not be resolved to a key -- they still count against coverage, so a
screenshot full of unreadable entries lowers the score rather than being
quietly dropped.

Usage
-----
    python tools/scan_logs.py --coverage observations.json
"""
import collections
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "tools" / "message_catalog.json"

CENSUS_RE = re.compile(r"SNW_CENSUS\|([PWQ])\|\d+\|(\w+)\|(.*?)[ \t]*$", re.M)
PROXY_RE = re.compile(r"SNW_PROXY\|([PW])\|(\w+)\|(.*?)[ \t]*$", re.M)
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")


def load_catalog():
    if not CATALOG_PATH.exists():
        return {}
    return {r["key"]: r for r in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))}


def scan_logs(logs_dir):
    """-> (census_keys, proxy_keys, years_seen). Streams; never holds a file."""
    census, proxy, years = set(), set(), set()
    # Use the census report's rotation-aware ordering rather than a bare glob.
    # A plain glob("debug*.log") also matches `debug.previous.log`, the backup
    # the archiver makes when it starts -- which would silently merge the
    # PREVIOUS run's notifications into this run's coverage number.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "census_report", Path(__file__).resolve().parent / "census_report.py")
    cr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cr)
    for path in cr.debug_logs(logs_dir):
        try:
            with path.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "SNW_CENSUS|" in line:
                        m = CENSUS_RE.search(line)
                        if m:
                            census.add(m.group(2))
                            y = YEAR_RE.search(m.group(3))
                            if y:
                                years.add(int(y.group(1)))
                    elif "SNW_PROXY|" in line:
                        m = PROXY_RE.search(line)
                        if m:
                            proxy.add(m.group(2))
                            y = YEAR_RE.search(m.group(3))
                            if y:
                                years.add(int(y.group(1)))
        except OSError:
            continue
    return census, proxy, years


def classify(key, catalog, census_keys, proxy_keys):
    """Why was an observed notification not in the log?

    The distinction that matters is between a gap we already KNOW about
    (engine-fired, no call site to hook) and a gap that means the instrument
    is broken (a key with a call site that still never logged). The second
    kind is a bug; the first is the lower bound we publish.
    """
    if key in census_keys:
        return "logged"
    if key in proxy_keys:
        return "logged-via-proxy"
    rec = catalog.get(key)
    if rec is None:
        return "unknown-key"
    if rec.get("engine_fired"):
        return "engine-fired"
    return "MISSED"


def report(logs_dir, obs_path):
    obs_path = Path(obs_path)
    if not obs_path.exists():
        print(f"observations file not found: {obs_path}")
        return 1
    data = json.loads(obs_path.read_text(encoding="utf-8"))
    observations = data.get("observations", [])
    if not observations:
        print(f"no observations in {obs_path}")
        return 1

    catalog = load_catalog()
    if not catalog:
        print("no message catalog -- run `python tools/message_catalog.py` first.")
        return 1

    census_keys, proxy_keys, years = scan_logs(logs_dir)

    print("=" * 72)
    print("CENSUS COVERAGE -- what was on screen vs what the log caught")
    print("=" * 72)
    if data.get("country"):
        print(f"run country          : {data['country']}")
    print(f"distinct keys logged : {len(census_keys)} census + {len(proxy_keys)} proxy")
    print(f"log years present    : {min(years)}-{max(years)}" if years else
          "log years present    : (none -- the tap may be broken)")
    print()

    verdicts = collections.Counter()
    unidentified = 0
    misses = []
    for ob in observations:
        date = ob.get("date", "?")
        keys = ob.get("keys", [])
        unidentified += int(ob.get("unidentified", 0) or 0)
        print(f"--- {date}  ({ob.get('source', 'observation')}) "
              f"{len(keys)} identified"
              f"{', %d unidentified' % ob['unidentified'] if ob.get('unidentified') else ''}")
        for key in keys:
            v = classify(key, catalog, census_keys, proxy_keys)
            verdicts[v] += 1
            tier = (catalog.get(key) or {}).get("tier", "?")
            flag = "  <-- INSTRUMENT GAP" if v == "MISSED" else ""
            print(f"    [{tier:5}] {key:46} {v}{flag}")
            if v == "MISSED":
                misses.append((date, key))
        print()

    identified = sum(verdicts.values())
    total = identified + unidentified
    caught = verdicts["logged"] + verdicts["logged-via-proxy"]
    print("--- Coverage ---")
    if total:
        print(f"  observed on screen      : {total} "
              f"({identified} identified, {unidentified} unidentified)")
        print(f"  caught by instrument    : {caught}  "
              f"({caught / total * 100:.0f}% of everything observed, "
              f"{caught / identified * 100:.0f}% of identified)")
    for v in ("logged", "logged-via-proxy", "engine-fired", "MISSED", "unknown-key"):
        if verdicts[v]:
            print(f"    {v:20} {verdicts[v]}")
    print()

    if misses:
        # These are the ones that should have been caught and were not.
        print("!! INSTRUMENT GAPS -- these keys HAVE a call site but never logged.")
        print("   That is a broken tap, not a quiet game. Check the build before")
        print("   trusting any count for them:")
        for date, key in misses:
            rec = catalog.get(key, {})
            print(f"     {key:46} (reach={rec.get('reach')}, seen {date})")
        print()
    elif verdicts["engine-fired"]:
        print("No instrument gaps: every observed key that COULD be hooked was.")
        print("The shortfall is entirely the engine-fired set, which is the")
        print("lower bound we publish -- now measured rather than asserted.")
        print()

    if verdicts["unknown-key"]:
        print("Some observed keys are not in the catalog at all. Either a typo in")
        print("the observations file, or the catalog is stale -- regenerate it with")
        print("`python tools/message_catalog.py`.")
    return 0
