"""
Build the throwaway NOTIFICATION CENSUS mod -- see docs/feed-census-plan.md.

WHAT IT DOES. Copies every vanilla (and Smart Notifications) script file that
contains a `post_notification` call into a separate, disposable mod folder,
inserting a `debug_log` line beside each call so a real playthrough can be
counted afterwards. Re-runnable and idempotent: the output folder's script
directories are rebuilt from scratch every run.

    python tools/build_census_mod.py                 # measure build (default)
    python tools/build_census_mod.py --mode calibrate
    python tools/build_census_mod.py --events all    # widen the events/ allowlist
    python tools/build_census_mod.py --manifest-only # classify, write nothing

THIS MOD IS NEVER SHIPPED. It overrides ~100 vanilla files, which is only
acceptable precisely because it is thrown away after one measurement run. It
gets its own mod id (`smart_notifications_census`) and its own folder, is never
added to the Smart Notifications playset entry, and `package_release.py` never
sees it. Nothing here is merged back into the mod.

LOAD ORDER. The census build must sit AFTER Smart Notifications in the playset,
because it also overrides SN's own call sites (SN's keys need counting too, and
SN's split families -- at_player_* / at_watched_* / elsewhere -- depend on the
live watchlist, so no vanilla-only run can produce them). SN's only vanilla
overrides are common/messages/00_messages.txt and two .gui files, none of which
this build touches, so the two mods share no file outside SN's own.

LOG LINE FORMAT
    SNW_CENSUS|<P|W>|<id>|<key>|[TimeKeeper.GetCurrentDate.GetString]
`P` = player-scoped (the call site is inside a country scope and that country
is the player -- what the player actually SEES). `W` = world (every firing
anywhere, including AI countries). `<id>` is an integer indexing the manifest
written next to the build, which carries the file, line, key and scope verdict
for every call site.

`[TimeKeeper.GetCurrentDate.GetString]` is confirmed valid in script-side
dynamic text -- vanilla itself uses it inside `debug_log` in common/ and
events/ (e.g. the Taikun and election-campaign logging). Per CLAUDE.md that is
the only acceptable kind of precedent for a dynamic-text call; a .gui binding
would not have been.

`debug_log` (NOT `log`, which does not exist) writes to debug.log.

MODES
  measure   -- one line per call site. Guarded (`P`) where the scope is
               confidently a country, unguarded (`W`) otherwise. This is the
               long-run build: smallest log, and the guarded lines are the
               numbers that go in the post.
  calibrate -- BOTH lines at every call site. Run this for a year or two first.
               Any call site showing `W` lines but no `P` lines is either a
               non-country scope (check error.log) or simply never the player;
               that is how the UNKNOWN verdicts below get resolved empirically
               rather than guessed. Log volume is irrelevant over a short run.

Verify the instrument before trusting it: a silent census is far more likely to
be a broken tap than a quiet game.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")
DEFAULT_OUT = (Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3"
               / "mod" / "smart_notifications_census")

MOD_ID = "smart_notifications_census"
MOD_NAME = "ZZ Notification Census (dev only -- never upload)"

# Directories rebuilt from scratch each run. Anything else in the output
# folder (launcher bookkeeping) is left alone, same policy as package_release.
BUILD_DIRS = ["common", "events"]

DATE_TOKEN = "[TimeKeeper.GetCurrentDate.GetString]"

# ---------------------------------------------------------------------------
# events/ allowlist
# ---------------------------------------------------------------------------
# The events/ tree holds 166 keys, but almost all of it is one-shot historical
# narrative -- one file per storyline (Spanish monarchy succession, the Paris
# Commune, the Tibet expedition, Koh-i-Noor). Those fire once per campaign at
# most and most never fire at all, so they are noise in the census, not signal,
# and instrumenting them means overriding ~60 more vanilla files for nothing.
#
# These are the events files whose notifications RECUR in an ordinary game.
# law_notification.txt is the important one: 7 toast keys that fire over and
# over through every single law enactment, which is squarely the noise this mod
# exists to fix. Widen with --events all if a run suggests something is missing.
EVENTS_ALLOWLIST = [
    "events/law_events/law_notification.txt",
    "events/law_imposition_events.txt",
    "events/diplomatic_friction_events.txt",
    "events/diplomatic_events.txt",
    "events/obligation_events.txt",
    "events/neighbor_events.txt",
    "events/ig_suppression_events.txt",
    "events/slave_revolts.txt",
    "events/tech_events/production_tech_events.txt",
    "events/agitators_events/revolution_events_01.txt",
]

# ---------------------------------------------------------------------------
# Scope classification
# ---------------------------------------------------------------------------
# WHY THIS IS NEEDED. `post_notification` fires in whatever scope its call site
# sits in, including AI countries -- which the player never sees. A raw count
# answers "how often does this happen in the world", which for something like
# diplomatic_action_notification is ~100x what a player sees. Counting what the
# player sees means guarding with `if = { limit = { is_player = yes } ... }`.
#
# WHY IT IS NOT TRIVIAL. `is_player` is a COUNTRY trigger and post_notification
# is not always called in a country scope -- vanilla's on_diplomatic_action
# roots on Diplomatic Action and calls it there. Guarding a non-country scope
# reproduces the exact repeating runtime error this project already hit once
# ("Wrong scope for trigger: diplomatic_action, expected country" -- CLAUDE.md
# scope rule, docs/engine-notes.md).
#
# So: never guess COUNTRY without positive evidence. An UNKNOWN verdict logs
# unguarded and is reported honestly as a world count; a wrong COUNTRY guess
# would yield zero data for that key PLUS error spam, a strictly worse failure.
COUNTRY, NON_COUNTRY, UNKNOWN = "country", "non_country", "unknown"

# Blocks that do not change scope -- walk straight through them.
TRANSPARENT = {
    "effect", "immediate", "if", "else", "else_if", "hidden_effect", "option",
    "on_complete", "on_fail", "on_timeout", "show_as_tooltip", "switch",
    "random_list", "first_valid", "?",
    # Journal-entry sub-blocks: containers inside the entry, not scope links.
    "on_monthly_pulse", "on_weekly_pulse", "on_yearly_pulse", "on_invalid",
}
# Scope references that resolve to whatever the enclosing scope already is.
TRANSPARENT_REFS = {"root", "this", "prev", "fromfrom", "from"}

# Iterators / scope links whose inner scope is a COUNTRY. A closed allowlist
# built from the blocks that actually enclose a vanilla post_notification, not
# a name pattern -- `scope:raid_state` is a state and a "_country" regex would
# not have caught `scope:oranje` anyway.
COUNTRY_BLOCKS = {
    "every_country", "random_country", "ordered_country",
    "every_subject_or_below", "random_subject_or_below",
    "every_diplomatically_relevant_country", "random_diplomatically_relevant_country",
    "every_cobelligerent_in_war", "random_cobelligerent_in_war",
    "every_enemy_in_war", "random_enemy_in_war",
    "every_scope_country", "random_scope_country",
    "every_neighbouring_country", "random_neighbouring_country",
    "every_subject", "random_subject", "every_overlord",
    "owner", "overlord", "capital_owner", "imposer_of_law", "country",
    "every_in_hierarchy", "random_in_hierarchy",
}
NON_COUNTRY_BLOCKS = {
    "state_region", "capital", "every_state", "random_state", "every_scope_state",
    "every_interest_group", "random_interest_group", "every_character",
    "random_character", "every_political_movement", "random_political_movement",
    "every_party", "random_party", "every_building", "random_building",
    "every_market", "random_market", "every_pop", "random_pop", "every_scope_pop",
    "every_institution", "random_institution", "every_law", "random_law",
    "every_journal_entry", "random_journal_entry", "every_war", "random_war",
    "every_scope_state_region", "every_character_in_jail",
    "random_character_in_jail", "random_active_law", "every_active_law",
}

# `scope:<name>` blocks. A saved scope's type cannot be read off its name, so
# this is an explicit table built from the vanilla call sites that actually
# enclose a post_notification. Anything unlisted stays UNKNOWN by design.
COUNTRY_SCOPE_VARS = {
    "adversary_scope", "obligation_request_sender", "overlord_scope",
    "india_scope", "expulsion_destination_country", "parent_of_safehaven",
    "target_country", "neighbor_country", "initiator", "actor", "recipient",
    "african_colony_conflict_sender", "african_colony_claim_conflict_sender",
    "foreign_imposition_country", "expedition_country", "algerian_raider_scope",
    "oranje", "probably_east_india_company_scope", "afghan_nation_scope",
    "raid_state.owner", "third_party_country", "attacker", "defender",
    # Each verified at its `save_scope_as` site rather than by name:
    # rival_scope is saved off a rivalry relation, and both *_neighbor scopes
    # are saved inside an `owner = { ... }` block.
    "rival_scope", "plastic_neighbor", "radio_production_neighbor",
}
NON_COUNTRY_SCOPE_VARS = {"law", "raid_state", "target_state", "state"}

# Root scope by source directory, for call sites whose enclosing stack is
# entirely transparent. scripted_buttons are clicked by the player, so their
# scope is the player's own country by construction. scripted_effects are
# caller-dependent and therefore honestly unknown.
ROOT_BY_DIR = {
    "common/journal_entries": (COUNTRY, "journal entry root"),
    "common/scripted_buttons": (COUNTRY, "player-clicked button"),
    "common/scripted_effects": (UNKNOWN, "caller-dependent"),
    "common/diplomatic_actions": (UNKNOWN, "diplomatic_action definition"),
    "common/character_interactions": (UNKNOWN, "character_interaction definition"),
}

# Manual scope verdicts, applied after the static classifier and keyed by
# "<mod-relative file>#<key>#<nth occurrence of that key in that file>" -- a
# key that survives regeneration as long as the source file itself is
# unchanged, unlike a line number or the manifest's sequential id.
#
# This is where a calibrate run's findings get written back: an UNKNOWN site
# that produced `is_player` scope errors is demoted to "non_country" here, and
# one that logged clean P lines is promoted to "country" to stop paying for the
# redundant world line. Hand-editing it is fine; it is data, not code.
OVERRIDES_PATH = REPO_ROOT / "tools" / "census_scope_overrides.json"

# Some non-country roots can still REACH the player, even though `is_player`
# cannot be applied to them directly -- a Treaty is not a country, but it has a
# `first_country`. Losing those to "world count only" would gut the census: the
# six Treaty keys are ALL toasts, and `journal_entry_completed`, `new_ruler` and
# `diplo_play_war_start_notification` sit in the same bucket.
#
# SOURCE OF TRUTH: the `script_docs` console dump at
# Documents/Paradox Interactive/Victoria 3/docs/event_targets.log, which lists
# every event target with its input and output scopes. Each link below is one
# whose Output Scope is literally `country`. This is documentation generated by
# the game itself, not inference from names -- the standard this project
# requires before trusting a construct.
#
# Diplomatic Play uses an ITERATOR instead: event_targets.log offers only
# `initiator`, which would miss the target and every country that joined, while
# `every_scope_play_involved` covers all of them. It is confirmed valid on a
# diplomatic play scope -- vanilla uses it inside `scope:diplomatic_play = {...}`
# in common/on_actions/00_code_on_actions.txt (~line 6441) with a country
# trigger (`has_journal_entry`) in its limit.
#
# ABSENT DELIBERATELY: `diplomatic_action`, `diplomatic_demand`, `culture` and
# `front` have NO country link in the dump at all. For diplomatic_action that
# confirms the earlier script_docs finding recorded in the header of
# common/on_actions/01_smart_notifications_logger.txt -- 15 keys including
# `diplomatic_action_notification` simply cannot be player-scoped. Do not try
# again; the dump is the answer.
# NAMED SCOPES. Separate mechanism from the event-target links above, and the
# reason `diplomatic_action` looked unreachable at first: an on_action can BIND
# named scopes (`scope:actor`, `scope:recipient`) that have nothing to do with
# what links exist off the root's scope TYPE. event_targets.log documents the
# latter and says nothing about the former, and vanilla's own `# scope:` header
# comments are incomplete -- they do not mention actor/recipient at all.
#
# Each entry below is confirmed, never assumed:
#   on_diplomatic_action / on_diplomatic_action_break / on_diplo_play_subject_released
#     -- proven by this mod's own shipped, working code
#        (06_..._diplomatic_action_filtering.txt, 13_..._pact_break_filtering.txt,
#         03_..._relational_notifications.txt).
#   the rest -- documented in vanilla's `# scope:` comments above the on_action.
#
# Assuming a SIBLING on_action shares its bindings is exactly the mistake that
# produced `Wrong scope for trigger: diplomatic_action, expected country`
# before: the `_third_party_` variants do NOT bind these. Unconfirmed on_actions
# are probed in calibrate mode instead of guessed at -- see PROBE_SCOPES.
ON_ACTION_SCOPES = {
    "on_diplomatic_action": ["actor", "recipient"],
    "on_diplomatic_action_break": ["actor", "recipient"],
    "on_diplo_play_subject_released": ["actor", "target"],
    "on_diplomatic_play_started": ["initiator", "target"],
    "on_country_withdrawn_from_treaty": ["withdrawing_country", "non_withdrawing_country"],
    "on_country_broke_treaty": ["withdrawing_country", "non_withdrawing_country"],
    "on_wargoal_added": ["actor"],
    "on_wargoal_removed": ["actor"],
    "on_war_end": ["actor", "target"],
    "on_diplomatic_incident": ["actor", "target"],
}

# Candidate named scopes to PROBE on a non-country call site we cannot reach
# any other way. Only emitted in calibrate mode, and only through the optional
# scope operator `?=`, which skips silently when the scope is not bound -- so a
# wrong candidate costs nothing, unlike applying `is_player` to the root, which
# is what actually threw before. A probe that logs proves the binding exists
# and the call site can be promoted into ON_ACTION_SCOPES for the real run.
PROBE_SCOPES = ["actor", "recipient", "initiator", "target",
                "attacker", "defender", "first_country", "second_country"]

PLAY_ITERATOR = "every_scope_play_involved"
PLAYER_REACH = {
    "Diplomatic Play": PLAY_ITERATOR,
    "Treaty": ["first_country", "second_country",
               "enforced_on_country", "enforcer_country"],
    "Diplomatic Pact": ["first_country", "second_country",
                        "diplomatic_pact_other_country"],
    "Military Formation": ["country", "owner"],
    "Character": ["home_country", "owner"],
    "political movement": ["owner"],
    "journal entry": ["owner"],
    "State": ["owner", "controller"],
    "Institution": ["owner"],
    "Interest Group": ["owner"],
}
# Same table, for call sites classified from the enclosing BLOCK rather than an
# on_action's `# Root =` comment.
PLAYER_REACH_BY_BLOCK = {
    "scope:law": ["owner", "imposer_of_law"],
    "random_active_law": ["owner", "imposer_of_law"],
    "every_character_in_jail": ["home_country", "owner"],
}
# ...but NOT for third-party keys. A `*_third_party_*` notification is
# addressed to countries that are NOT parties, so a parties-only reach would
# count precisely the wrong set. Those stay world-only rather than carry a
# confidently wrong number.
THIRD_PARTY_MARKER = "third_party"

ROOT_COMMENT_RE = re.compile(r"^\s*#\s*Root\s*=\s*(.+?)\s*$", re.I)
# Vanilla's Root comments are prose, not an enum. Every country-rooted variant
# it actually uses -- "Country", "country", "The applicable country", "owner
# Country of the Law", "Country (that owns a state in the state region)" --
# starts with an optional article/qualifier then the word "country". Nothing
# else in the file matches (Treaty, Character, Diplomatic Play, State,
# Institution, Culture, journal entry, political movement, Military Formation).
ROOT_IS_COUNTRY_RE = re.compile(r"^(the\s+applicable\s+|owner\s+)?country\b", re.I)
# A handler registered on a vanilla on_action: `on_x = { on_actions = { y } }`.
REGISTERS_RE = re.compile(r"^(on_\w+)\s*=\s*\{\s*on_actions\s*=\s*\{([^}]*)\}", re.M)
ON_ACTION_RE = re.compile(r"^(on_\w+)\s*=\s*\{", re.M)
EVENT_TYPE_RE = re.compile(r"^\s*type\s*=\s*(\w+)", re.M)
BLOCK_OPEN_RE = re.compile(r"([A-Za-z_][\w:.']*)\s*=\s*\{")
POST_RE = re.compile(r"post_notification\s*=\s*(\w+)")


def scan_call_sites(text):
    """Brace-aware walk yielding (offset, line, col_indent, key, stack).

    Hand-rolled rather than regex-only because the enclosing block stack is
    what decides whether the player guard is safe, and because `#` inside a
    quoted string is not a comment (the same trap validate_syntax.py hit).
    """
    stack, out = [], []
    i, line, n = 0, 1, len(text)
    line_start = 0
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            line_start = i
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\n":
                    line += 1
                i += 1
            i += 1
            continue
        m = BLOCK_OPEN_RE.match(text, i)
        if m:
            stack.append(m.group(1))
            i = m.end()
            continue
        if c == "{":
            stack.append("?")
            i += 1
            continue
        if c == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        m = POST_RE.match(text, i)
        if m:
            indent = text[line_start:i]
            out.append((i, m.end(), line, indent, m.group(1), list(stack)))
            i = m.end()
            continue
        i += 1
    return out


def classify(text, offset, stack, rel_path):
    """-> (verdict, reason). Innermost-out, falling back to the file root.

    `stack[0]` is skipped deliberately: the outermost block in any Paradox
    script file is the definition's own name (the event id, the on_action
    handler name, the journal entry key), which is a container, not a scope
    change. Treating it as an unrecognised scope link would send every
    otherwise-transparent call site to UNKNOWN.
    """
    for name in reversed(stack[1:]):
        if name in TRANSPARENT or name.lower() in TRANSPARENT_REFS:
            continue
        # Dotted scope paths -- `THIS.owner`, `scope:raid_state.owner`. The
        # LAST segment is the resulting scope; the ones before it are just the
        # route taken to get there.
        base, _, tail = name.rpartition(".")
        if tail and base:
            if tail in COUNTRY_BLOCKS:
                return COUNTRY, name
            if tail in NON_COUNTRY_BLOCKS:
                return NON_COUNTRY, name
            return UNKNOWN, name
        if name.startswith("scope:"):
            var = name[len("scope:"):]
            if var in COUNTRY_SCOPE_VARS:
                return COUNTRY, f"scope:{var}"
            if var in NON_COUNTRY_SCOPE_VARS:
                return NON_COUNTRY, f"scope:{var}"
            return UNKNOWN, f"scope:{var} (untyped)"
        if name in COUNTRY_BLOCKS:
            return COUNTRY, name
        if name in NON_COUNTRY_BLOCKS:
            return NON_COUNTRY, name
        return UNKNOWN, name

    # Nothing decisive in the stack -- fall back to what the file itself is.
    if "/on_actions/" in rel_path:
        if stack and not stack[0].startswith("on_"):
            resolved = handler_root_map().get(stack[0])
            if resolved:
                return resolved
        return root_from_on_action_comment(text, offset)
    if rel_path.startswith("events/"):
        return root_from_event_type(text, offset)
    for prefix, verdict in ROOT_BY_DIR.items():
        if rel_path.startswith(prefix):
            return verdict
    return UNKNOWN, "(unrecognised source dir)"


def verdict_from_root_comment(root):
    return (COUNTRY if ROOT_IS_COUNTRY_RE.match(root) else NON_COUNTRY), f"# Root = {root}"


def reach_for(reason, key):
    """How to walk from a non-country root to the player, or None."""
    if THIRD_PARTY_MARKER in key:
        return None
    for root, how in PLAYER_REACH.items():
        if f"# Root = {root}" in reason:
            return how
    return PLAYER_REACH_BY_BLOCK.get(reason)


def named_scope_guard(scopes, pad, payload):
    """`scope:x ?= { if = { limit = { is_player = yes } ... } }` per candidate.

    `?=` is the optional-scope form vanilla itself uses; an unbound scope is
    skipped rather than raising. One statement per scope instead of an OR so
    that a probe records WHICH scope was bound.
    """
    return [
        f'{pad}scope:{s} ?= {{ if = {{ limit = {{ is_player = yes }} {payload(s)} }} }}'
        for s in scopes
    ]


def reach_guard(how, pad, payload):
    """Render the player check for a reachable non-country scope."""
    if how == PLAY_ITERATOR:
        return f"{pad}{PLAY_ITERATOR} = {{ limit = {{ is_player = yes }} {payload} }}"
    # `exists` first: a link can legitimately be null at runtime (a treaty with
    # no enforcer), and testing is_player on a null scope logs an error.
    clauses = " ".join(
        f"AND = {{ exists = {link} {link} = {{ is_player = yes }} }}" for link in how
    )
    return f"{pad}if = {{ limit = {{ OR = {{ {clauses} }} }} {payload} }}"


def root_comment_above(text, start):
    """The `# Root = X` in the contiguous comment block directly above `start`.

    Scans the WHOLE contiguous run of comment lines, not a fixed window:
    vanilla routinely puts the Root line above several `# scope:foo - ...`
    lines (on_enemy_supply_ships_raided has seven of them), and a fixed
    lookback silently loses those.
    """
    for raw in reversed(text[:start].splitlines()):
        stripped = raw.strip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            return None
        m = ROOT_COMMENT_RE.match(raw)
        if m:
            return m.group(1).strip()
    return None


def root_from_on_action_comment(text, offset):
    """Vanilla annotates every on_action with `# Root = X` directly above it.

    That comment is the only documentation these scope types have, and is what
    common/on_actions/01_smart_notifications_logger.txt was built from -- the
    hard way, after `is_player` on a Diplomatic Action root threw at runtime.
    """
    header = None
    for m in ON_ACTION_RE.finditer(text, 0, offset):
        header = m
    if header is None:
        return UNKNOWN, "(no enclosing on_action)"
    root = root_comment_above(text, header.start())
    if root is None:
        return UNKNOWN, "(on_action has no Root comment)"
    return verdict_from_root_comment(root)


# Handler name -> verdict, for Smart Notifications' own on_action handlers.
# SN's handlers are named `smart_notifications_*`, so they carry no `# Root`
# comment of their own; their scope is whatever the VANILLA on_action that
# registers them is rooted on. Resolving that link is a lookup, not a guess --
# which matters here, because most of them turn out to be Diplomatic Play or
# Diplomatic Action roots, exactly the case that threw at runtime before.
_HANDLER_ROOTS = None


def handler_root_map():
    global _HANDLER_ROOTS
    if _HANDLER_ROOTS is not None:
        return _HANDLER_ROOTS
    vanilla_roots = {}
    for f in sorted((GAME_ROOT / "common" / "on_actions").glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        for m in ON_ACTION_RE.finditer(text):
            root = root_comment_above(text, m.start())
            if root:
                vanilla_roots[m.group(1)] = verdict_from_root_comment(root)
    handlers = {}
    for f in sorted((REPO_ROOT / "common" / "on_actions").glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        for m in REGISTERS_RE.finditer(text):
            on_action, body = m.group(1), m.group(2)
            if on_action not in vanilla_roots:
                continue
            verdict, reason = vanilla_roots[on_action]
            for name in body.split():
                handlers[name] = (verdict, f"{reason} (via {on_action})")
    _HANDLER_ROOTS = handlers
    return handlers


def root_from_event_type(text, offset):
    last = None
    for m in EVENT_TYPE_RE.finditer(text, 0, offset):
        last = m
    if last is None:
        return UNKNOWN, "(no event type)"
    t = last.group(1)
    if t == "country_event":
        return COUNTRY, "type = country_event"
    return NON_COUNTRY, f"type = {t}"


def load_overrides():
    if not OVERRIDES_PATH.exists():
        return {}
    data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def instrument(text, rel_path, next_id, mode, manifest, overrides,
               probe_localize=0):
    """Insert the census logging beside every post_notification in `text`."""
    sites = scan_call_sites(text)
    if not sites:
        return text, next_id
    out, cursor = [], 0
    seen = {}
    for _start, end, line, indent, key, stack in sites:
        verdict, reason = classify(text, _start, stack, rel_path)
        nth = seen[key] = seen.get(key, -1) + 1
        site_key = f"{rel_path}#{key}#{nth}"
        if site_key in overrides:
            verdict, reason = overrides[site_key], f"override ({overrides[site_key]})"
        cid = next_id
        next_id += 1
        manifest.append({
            "id": cid, "key": key, "file": rel_path, "line": line,
            "site_key": site_key, "scope": verdict, "reason": reason,
        })
        pad = indent if indent.strip() == "" else "\t"
        # COUNTRY     -> guarded only; the player count is the number that
        #                matters and the world line would just inflate the log.
        # NON_COUNTRY -> never guarded; `is_player` there is the known runtime
        #                error, so don't write it at all.
        # UNKNOWN     -> BOTH. The guard gives a player count if the scope does
        #                turn out to be a country (most scripted effects are),
        #                and the unguarded line is the safety net if it doesn't
        #                -- a wrong guess then costs error.log noise rather
        #                than a silently missing key. Demote the noisy ones via
        #                the overrides file once a calibrate run has named them.
        on_action = stack[0] if stack and stack[0].startswith("on_") else None
        named = ON_ACTION_SCOPES.get(on_action) if verdict == NON_COUNTRY else None
        if named and THIRD_PARTY_MARKER in key:
            named = None
        reach = None if named else (reach_for(reason, key) if verdict == NON_COUNTRY else None)
        if named:
            manifest[-1]["reach"] = "scope:" + "/scope:".join(named)
        elif reach:
            manifest[-1]["reach"] = reach if isinstance(reach, str) else "/".join(reach)
        emit_guard = verdict in (COUNTRY, UNKNOWN)
        emit_world = verdict in (NON_COUNTRY, UNKNOWN) or mode == "calibrate"
        lines = []
        if named:
            # Reachable via scopes the on_action binds by name.
            lines.extend(named_scope_guard(
                named, pad,
                lambda s: f'debug_log = "SNW_CENSUS|P|{cid}|{key}|{DATE_TOKEN}"'))
        elif reach:
            # Reachable non-country root: walk to the countries this scope
            # actually concerns and log once if one of them is the player.
            lines.append(reach_guard(
                reach, pad,
                f'debug_log = "SNW_CENSUS|P|{cid}|{key}|{DATE_TOKEN}"'))
        elif verdict == NON_COUNTRY and mode == "calibrate":
            # Nothing confirmed reaches the player here. Probe, so the run
            # tells us whether one of the usual named scopes is bound after
            # all, rather than leaving it assumed unmeasurable.
            manifest[-1]["probed"] = True
            lines.extend(named_scope_guard(
                PROBE_SCOPES, pad,
                lambda s: f'debug_log = "SNW_CENSUS|Q|{cid}|{key}|{DATE_TOKEN}|{s}"'))
        elif emit_guard:
            lines.append(
                f'{pad}if = {{ limit = {{ is_player = yes }} '
                f'debug_log = "SNW_CENSUS|P|{cid}|{key}|{DATE_TOKEN}" }}'
            )
        if emit_world:
            lines.append(f'{pad}debug_log = "SNW_CENSUS|W|{cid}|{key}|{DATE_TOKEN}"')
        # Does `Localize` -- which exists in the GUI function table -- also work
        # in script dynamic text? If it does, the census can log the notification
        # the player actually READ, not just its key. CLAUDE.md is explicit that
        # a function confirmed in a .gui binding is NOT evidence it works here:
        # the two are separate function tables, so this has to be probed.
        #
        # Deliberately capped at a handful of sites. An invalid dynamic-text
        # function logs "Could not find data system function" EVERY time it is
        # evaluated -- across 596 call sites that would bury the real errors the
        # calibrate run exists to surface. A few probes answer it just as well.
        if probe_localize and cid <= probe_localize:
            lines.append(
                f'{pad}debug_log = "SNW_LOCPROBE|{key}|'
                f"[Localize('notification_{key}_name')]\""
            )
        out.append(text[cursor:end])
        out.append("\n" + "\n".join(lines))
        cursor = end
    out.append(text[cursor:])
    return "".join(out), next_id


COMMENT_STRIP_RE = re.compile(r"#.*")


def has_call_site(path):
    """Does this file actually POST a notification, comments excluded?

    Testing the raw text was wrong: 08_smart_notifications_engine_proxy.txt's
    header comment contains the phrase "no `post_notification` call site
    anywhere", which pulled the whole file into the census build. That copy
    then shadowed the real one -- the census loads after Smart Notifications --
    and froze it at build time, so a fix made afterwards was silently ignored
    for a whole 11-year run. Found 2026-09-15.
    """
    text = COMMENT_STRIP_RE.sub(
        "", path.read_text(encoding="utf-8-sig", errors="replace"))
    return "post_notification" in text


def collect_sources(events_mode, sources_mode="all"):
    """-> list of (absolute source path, mod-relative path, origin label)."""
    found = []
    for sub in ("common", "events"):
        base = GAME_ROOT / sub
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.txt")):
            rel = f.relative_to(GAME_ROOT).as_posix()
            try:
                if not has_call_site(f):
                    continue
            except OSError:
                continue
            if rel.startswith("events/"):
                if events_mode == "none":
                    continue
                if events_mode == "recurring" and rel not in EVENTS_ALLOWLIST:
                    continue
            found.append((f, rel, "vanilla"))

    # Smart Notifications' own call sites. Its keys need counting too, and its
    # watchlist-conditional split families cannot be derived from a vanilla run.
    #
    # MUST be skipped when the census runs WITHOUT Smart Notifications enabled.
    # These 8 files are copies of SN's own on_action handlers; loaded on their
    # own they are orphans -- they reference SN's scripted_triggers, script
    # values, message keys and alert groups, none of which exist without SN --
    # so they would produce error spam and post keys that are not defined.
    # `--sources vanilla` exists for exactly that run.
    if sources_mode == "vanilla":
        return found
    for sub in ("common", "events"):
        base = REPO_ROOT / sub
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.txt")):
            rel = f.relative_to(REPO_ROOT).as_posix()
            if not has_call_site(f):
                continue
            if rel.startswith("common/messages/"):
                continue  # definitions, not call sites
            found.append((f, rel, "smart_notifications"))
    return found


def write_metadata(out_dir):
    """metadata.json must NOT carry a BOM -- a BOM is invalid JSON and breaks
    the Paradox launcher's mod parsing outright (CLAUDE.md)."""
    meta_dir = out_dir / ".metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": MOD_NAME,
        "id": MOD_ID,
        "version": "0.01",
        "supported_game_version": "1.13.*",
        "short_description": "Throwaway measurement build. Never upload.",
        "tags": ["Utilities"],
        "relationships": [],
        "game_custom_data": {"multiplayer_synchronized": False},
    }
    (meta_dir / "metadata.json").write_text(
        json.dumps(payload, indent=4), encoding="utf-8", newline="\n"
    )


def main():
    global GAME_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["measure", "calibrate"], default="measure")
    ap.add_argument("--probe-localize", type=int, default=None,
                    help="probe whether Localize() resolves in script dynamic text, "
                         "on this many call sites (default: 6 in calibrate, 0 in measure). "
                         "If it works, the census can log the text the player read.")
    ap.add_argument("--events", choices=["recurring", "all", "none"], default="recurring")
    ap.add_argument("--sources", choices=["all", "vanilla"], default="all",
                    help="'all' also instruments Smart Notifications' own call sites and "
                         "REQUIRES SN to be enabled alongside. 'vanilla' instruments only "
                         "vanilla files -- use it when running the census mod ON ITS OWN, "
                         "e.g. to check the logs against what the player actually sees.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--game-root", type=Path, default=GAME_ROOT)
    ap.add_argument("--manifest-only", action="store_true",
                    help="Classify every call site and write the manifest, but build nothing.")
    args = ap.parse_args()
    if args.probe_localize is None:
        args.probe_localize = 6 if args.mode == "calibrate" else 0

    GAME_ROOT = args.game_root
    if not GAME_ROOT.is_dir():
        print(f"Game install not found: {GAME_ROOT}", file=sys.stderr)
        return 1

    sources = collect_sources(args.events, args.sources)
    if not sources:
        print("No source files found -- check --game-root.", file=sys.stderr)
        return 1

    out_dir = args.out
    if not args.manifest_only:
        for d in BUILD_DIRS:
            shutil.rmtree(out_dir / d, ignore_errors=True)
        write_metadata(out_dir)

    overrides = load_overrides()
    manifest, next_id, written = [], 1, 0
    for src, rel, origin in sources:
        text = src.read_text(encoding="utf-8-sig", errors="replace")
        before = len(manifest)
        new_text, next_id = instrument(text, rel, next_id, args.mode, manifest,
                                       overrides, args.probe_localize)
        for entry in manifest[before:]:
            entry["origin"] = origin
        if args.manifest_only:
            continue
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        # UTF-8 BOM is mandatory on every modded .txt (CLAUDE.md); the game's
        # lexer logs "should be in utf8-bom encoding" without it.
        dest.write_text(new_text, encoding="utf-8-sig", newline="\n")
        written += 1

    manifest_path = (out_dir if not args.manifest_only else REPO_ROOT / "tools") / "census_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")

    counts = {}
    for e in manifest:
        counts[e["scope"]] = counts.get(e["scope"], 0) + 1
    keys = {e["key"] for e in manifest}
    guarded = counts.get(COUNTRY, 0)

    print(f"mode={args.mode}  events={args.events}  sources={args.sources}")
    print(f"  source files      : {len(sources)}  ({written} written)")
    print(f"  call sites        : {len(manifest)}")
    print(f"  distinct keys     : {len(keys)}")
    probed = sum(1 for e in manifest if e.get("probed"))
    reached = sum(1 for e in manifest if e.get("reach"))
    if probed:
        print(f"  probed (calibrate): {probed} call sites with no confirmed route to the player")
    print(f"  player-guarded (P): {guarded} direct + {reached} via a reach iterator")
    print(f"  world-only     (W): {counts.get(NON_COUNTRY, 0) + counts.get(UNKNOWN, 0)}"
          f"   (non-country {counts.get(NON_COUNTRY, 0)}, unknown {counts.get(UNKNOWN, 0)})")
    print(f"  overrides applied : {len(overrides)}")
    print(f"  manifest          : {manifest_path}")
    if not args.manifest_only:
        print(f"  output            : {out_dir}")
        print()
        if args.sources == "vanilla":
            print("Built WITHOUT Smart Notifications' files -- run this mod ON ITS OWN.")
            print("Do NOT enable Smart Notifications alongside a --sources vanilla build.")
        else:
            print("Add as its own mod entry, ordered AFTER Smart Notifications.")
        print("NEVER upload this. NEVER add it to the Smart Notifications playset entry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
