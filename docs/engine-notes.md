# Engine notes

Detailed reference for facts about the Victoria 3 engine confirmed during
development — the "why" and "how we know" behind the terse rules in
`CLAUDE.md`. Read the relevant section here before relying on one of these
in new code; `CLAUDE.md` only states the rule, not the reasoning.

## Override hierarchy

A player's in-game Message Settings changes are stored client-side in
`Documents/Paradox Interactive/Victoria 3/messagetypes_custom.txt`, keyed by
notification **`group`**, not by individual message key — confirmed
empirically by reading that file directly, e.g.
`country_attitude_changed_group={notification=feed}`. If a group has an
entry there, it overrides our script default until the player clicks
"Reset to Default"/"Reset All" — our mod cannot see or change that file.

Consequences:
- Any returning player who's ever touched Message Settings won't see our
  new defaults for those groups until they reset them. Every release's
  Workshop notes must say so (see the release checklist in `TODO.md`).
- `post_notification = <key>` only ever takes a bare key — no inline
  override of `notification_type`/`pause_game` per call. A key's priority
  is a fixed script default. Anything needing situational priority (e.g.
  Phase 4's relational engine) needs **separate keys/groups per priority
  tier**, chosen via script logic in the on_action that fires it.
- A brand-new key/group has no entry in `messagetypes_custom.txt` yet, so
  our script default always applies the first time — confirmed with the
  Phase 0 bootstrap notification.
- If two keys share a group but disagree on `notification_type`, the game
  logs `"<Group> has mixed Notification Types"` — confirmed live in
  `error.log`. Fix by aligning them or splitting the diverging one into its
  own group (with a matching `<group>_group` localization string).

## BOM required on every modded file, not just `.yml`

The game's lexer logs `should be in utf8-bom encoding` for any modded
`.txt`/`.gui` missing a BOM (non-fatal, confirmed in `error.log`).
`tools/validate_syntax.py` enforces this on all three extensions. The
`Write` tool does not add a BOM itself — after writing a new file, prepend
it:

```python
p = "path/to/file.txt"
with open(p, "rb") as f:
    data = f.read()
if not data.startswith(b'\xef\xbb\xbf'):
    with open(p, "wb") as f:
        f.write(b'\xef\xbb\xbf' + data)
```

## Dynamic text vs. effect/trigger syntax

`root` / `scope:x` (lowercase effect-syntax keywords) only work inside
`effect`/`trigger` blocks. They are **not valid inside `[...]` bracket
dynamic text** — localization strings, tooltips, or `debug_log`'s string
argument all use a different grammar:
- `THIS` — the dynamic-text equivalent of the current root/this scope.
- `SCOPE.sC('name')` — reads a saved scope named `name`, cast to Country
  (other casts exist per type: `sParty`, `sDiplomaticPlay`, etc.).

Confirmed the hard way: an early debug tool used `[Root.GetName]` /
`[scope:actor.GetName]` and every single call errored
(`Failed to find type 'Root' in 'Root.GetName'`) — silently, for a whole
playtest, before anyone checked `error.log`. Always verify a bracket
expression against a real vanilla example before trusting it.

## `debug_log`, not `log`

The debug-logging effect is `debug_log = "..."` (with full bracket
interpolation support) — a plain `log` effect does not exist. Grepped all
of vanilla `common/` for `^\s*log\s*=\s*"` and found zero matches; confirmed
`debug_log` from its extensive real usage in `00_code_on_actions.txt`, etc.
Output lands in `debug.log`, not `game.log` — confirmed by matching known
vanilla `debug_log` strings against the user's own log files.

## Scope types are not all countries

Several on_actions that fire our reviewed notifications are **not** rooted
on a country at all — `# Root = Diplomatic Play` / `Diplomatic Demand` /
`Diplomatic Action` are their own object types. Applying a country-only
trigger (`is_player`) directly to the wrong scope type risks a validation
error (load-time, or a real runtime error like `is_player trigger [ Wrong
scope for trigger: diplomatic_action, expected country ]`) — worse than a
silent miscount.

**Only trust a vanilla comment on the on_action itself** (e.g. `#
Root = Diplomatic Action` directly above the `on_x = { ... }` block in
`00_code_on_actions.txt`) as confirmation of an on_action's runtime root.
**Learned the hard way, 2026-09-06:** a `.md` doc file describing a
*type's own* effect/trigger blocks is a different context and does NOT
confirm an on_action's root, even when it looks related — the
`diplomatic_proposal_third_party*` family was `is_player`-filtered on the
strength of `common/diplomatic_actions/diplomatic_action.md` saying
`root = action initiator`, which describes the scope *inside a
diplomatic_action type's own `effect`/`ai` blocks at definition time* —
not the runtime root of the separate `on_diplomatic_action_third_party*`
on_actions, which really is "Diplomatic Action" per vanilla's own on_action
comment, confirmed by that exact repeating runtime error. Reverted to
unfiltered. See `common/on_actions/01_smart_notifications_logger.txt`'s
header comment for the current confirmed/unconfirmed hook list.

## Two entirely separate notification systems: messages vs. alerts

Confirmed 2026-09-05, from the user's screenshot of Message Settings'
second tab ("Important Actions & Alerts") plus the vanilla files behind it.
Everything Phase 0-1 has touched so far (`common/messages/*.txt`,
`notification_type = none/feed/toast/popup`) is **one** of two independent
systems — don't assume it covers a spammy/missing notification without
checking which system actually owns it first.

- **Messages** (`common/messages/*.txt`) — one-shot events, fired by an
  `on_action`/effect via `post_notification = <key>`. Player-tunable value:
  `none | feed | toast | popup`. Everything this mod has changed so far.
- **Alerts** (`common/alert_types/00_alert_types.txt`,
  `common/alert_groups/00_alert_groups.txt`) — **standing conditions**, each
  with a `valid = { trigger block }` the game re-evaluates continuously (no
  on_action, no pulse-scan, no repeat-guard needed — the engine handles
  show/hide itself as the trigger flips). Shown as icons in the top ribbon
  / Important Actions panel. Player-tunable value:
  `alert | important_action | angry_important_action | none` (an alert
  type's own `type = ` field sets the *default*; the player's per-type
  override lives under this tab). Examples: `revolution_alert`,
  `has_no_war_goal_alert`, `obligation_expiring`,
  `overlord_can_decrease_subject_autonomy`.
- An alert type also supports `open_panel = <panel>|<tab>` or
  `open_popup = <popup>` — clicking it navigates the player straight to the
  relevant screen, which a plain message notification can't do.
- **Practical consequence:** the "state-change watcher" pattern (see the
  Law Commitment candidate feature) doesn't need `on_monthly_pulse_country`
  + a repeat-guard variable at all if the condition can be expressed as a
  `valid` trigger — a new `common/alert_types/` entry is simpler, is
  naturally exactly the "top ribbon" behavior several of the user's
  requested notifications asked for, and needs no message key or
  localization for a "did this just become true" ping (only for the
  alert's own tooltip/name strings). Prefer this over the pulse+message
  shape wherever the underlying condition is already a queryable trigger.
- **Resolved 2026-09-06**, via the real `script_docs` dump (see below) —
  no truce day-count trigger exists anywhere (only `has_truce_with`,
  boolean), but `enactment_chance`/`enacting_any_law` (for laws) and
  `amendment_can_be_repealed` (for amendments) do exist and are exactly
  what's needed. See the Phase-2-adjacent state-change-watcher entries in
  [TODO.md](../TODO.md) for the specifics and the resulting alert-type
  trigger chains.

### Where `script_docs` actually writes its output

`-debug_mode` alone doesn't auto-dump anything — it just unlocks the
console (`~`). The dump is the console command **`script_docs`**
(confirmed via the Vic3 wiki's Trigger/Effect pages, which say their
tables are generated from it), run once after enabling debug mode.
**Confirmed 2026-09-06, the actual output location:**
`Documents/Paradox Interactive/Victoria 3/docs/` (a folder that doesn't
otherwise exist until you run the command) — NOT the sibling `logs/`
folder, which only picked up an unrelated `event_scopes.log`. Files
produced: `triggers.log`, `effects.log`, `event_targets.log`,
`on_actions.log`, `modifiers.log`, `custom_localization.log`. Each entry
is a `## name` heading with a one-line description, its usage shape, and
a `**Supported Scopes**:`/`**Supported Targets**:` line — grep these
directly instead of guessing a trigger/effect name exists.

## Tagging mod-created notifications

Confirmed 2026-09-06, from the user's own screenshot of the full Message
Settings list: once you have several custom groups mixed in among ~15
vanilla ones, a plain label like "Truce Expired" is indistinguishable from
a vanilla row at a glance — nothing marks it as this mod's own content. The
one existing group that *did* self-identify (`smart_notifications_mod_loaded_group`
→ "Smart Notifications Mod") only did by coincidence of its name, not by
any deliberate convention.

**Convention adopted:** any message group or alert type that is genuinely
**new content this mod created** (not a vanilla notification we only
re-tuned `notification_type` on, and not a vanilla notification we split
into a new group for independent priority) gets a `" (Smart Notifications)"`
suffix on whichever loc string is the **settings-list label** (parentheses,
not square brackets — see § Literal `[...]` in loc text below; the first
version of this convention used brackets and broke every string it
touched):
- For messages, that's the `group` loc key (e.g.
  `smart_notifications_truce_expired_group:0 "Truce Expired (Smart
  Notifications)"`) — not the message's own `_name`/`_desc`, which is the
  actual toast/popup sentence shown in-game and reads awkwardly with a
  tag appended mid-sentence.
- For alerts, there's no separate settings-list label — an alert's own
  `_name` loc *is* both its Message Settings row label and its ribbon
  tooltip title, so tagging `_name` covers both automatically (e.g.
  `alert_smart_notifications_amendment_repealable_alert_name:0 "Amendment
  Repeal Available (Smart Notifications)"`).

**Explicitly NOT tagged:** `invasion_against_us_notification_group` and
`diplo_play_subject_overlord_notification_group` (Phase 1's group-splits)
— the underlying notification is 100% vanilla content; we only gave it its
own settings row so two siblings could have independent priority. Tagging
those would misleadingly imply we invented the notification itself, not
just its settings entry. Only apply the tag to something a player couldn't
otherwise experience without this mod installed at all.

## An alert type needs TWO name-shaped loc keys, not one

Confirmed 2026-09-06, from a real bug: our first `smart_notifications_amendment_repealable_alert`
shipped with only `alert_<key>_name` defined, and the Message Settings
list showed the raw script key instead of a label. Checking
`gui/message_settings.gui` confirmed the settings-list row is NOT bound to
the same loc as the ribbon tooltip:

- `alert_<key>_name` / `_desc` / `_hint` / `_action` — the ribbon icon's
  own tooltip (title/description/hint/button-label), bound via
  `[AlertSettingsItem.GetCurrentOption...]`-adjacent getters.
- `<key>_setting_name` — **no `alert_` prefix** — the label shown in the
  Message Settings → Important Actions & Alerts list, bound via
  `[AlertSettingsItem.GetSettingName]`, a genuinely different getter.

Confirmed against a real working vanilla example
(`naval_hostilities_alert`): both
`alert_naval_hostilities_alert_name` and
`naval_hostilities_alert_setting_name` exist side by side in
`alerts_l_english.yml`, pointing at the same text in that case, but as two
separate keys — omitting the second one is what leaves Message Settings
showing a raw key instead of a label. Every alert type this mod defines
needs both.

## Literal `[...]` in loc text is always a dynamic-text function call

Confirmed 2026-09-06, from a real bug: a `" [Smart Notifications]"` tag
suffix added to a couple of Message-Settings-visible labels (see
"Tagging mod-created notifications" above) silently blanked those exact
strings in-game. `error.log` explained why: `Unexpected characters found
at end of Statement 'Smart Notifications'` / `Could not find data system
function 'Smart' in 'Smart '`. **There is no escape sequence for a
literal square bracket** — `[...]` in any loc string is unconditionally
parsed as a dynamic-text call, even plain English words with no `SCOPE`/
`THIS` in sight. Use parentheses (or any other delimiter) for a visual
tag instead — corrected everywhere this convention is used to
`" (Smart Notifications)"`.

## `GetName` is not a valid dynamic-text function — use `GetNameNoFormatting`

Confirmed 2026-09-06, from a real bug: the truce-expiry notification
(`smart_notifications_truce_expired`) never visibly fired for the user
despite the underlying on_action logic correctly detecting the truce
ending (confirmed via its own debug taps). Root cause, from `error.log`:
`Could not find data system function 'GetName' in 'THIS.GetName'` —
plain `.GetName` on a country **errors outright** in dynamic text/
`debug_log` context, it isn't a registered function there. Grepped every
vanilla `debug_log` call using a country name across
`common/on_actions/00_code_on_actions.txt` and found **100% of them** use
`.GetNameNoFormatting` instead (e.g. `[THIS.GetCountry.GetNameNoFormatting]`)
— never plain `.GetName`. This was previously assumed safe by analogy
with `[SCOPE.sC('actor').GetName]` used in the deleted Phase 2 debug tool,
which was never actually confirmed working in-game before Phase 2 closed
— so that assumption carried forward uncaught until this bug. **Always
use `.GetNameNoFormatting` for a country's name in dynamic text/loc/
debug_log going forward — never plain `.GetName`.**

## `validate_syntax.py` bug: comment-stripping wasn't quote-aware

Found 2026-09-07, adding this mod's first-ever `.gui` file
(`gui/message_settings.gui`). The validator's comment stripper was a plain
`line.split('#')[0]` — fine for `.txt`/`.yml` script, but GUI files
routinely embed formatting codes like `"#title"`, `"#clickable"`,
`"#header ...#!"` **inside quoted strings**. Splitting on the first `#`
regardless of quote state truncated real content (hiding genuine closing
brackets later on the line) and desynced the quote tracker for every
subsequent line in the file, reporting a false `6 unclosed '{'` on a file
that was actually perfectly balanced (confirmed by hand with a
quote-aware recount before touching the tool). Fixed the tool itself to
only treat `#` as a comment-starter when not currently inside a quoted
string — this is exactly the kind of false positive that could bury a
real error in a later file, so worth trusting the tool again now, but
watch for `.gui` files specifically if it ever seems to misfire again.

## A scripted GUI's `is_valid` also gates whether `.Execute()` runs

Confirmed 2026-09-07, from a real, fully-reproduced bug: the Watchlist
tab's row checkbox never toggled on, even after a full window close/
reopen (ruling out a caching/redraw explanation). Root cause:
`watchlist_toggle_sgui`'s `is_valid` was set to "is this country already
watched," on the assumption `is_valid` was just a query I could dual-purpose
for the checkbox's `checked` display state. It's not — per
`scripted_guis.md`, `is_valid` literally "Determines whether the SGUI can
be used by a player," and the engine enforces that on `.Execute()` too, not
just `.IsValid()` reads. So clicking to *watch* an unwatched country was
silently refused every time, because `is_valid` was `false` for exactly
the countries you'd want to click — a fully silent failure, no error
logged anywhere.

**Fix, following a real vanilla precedent:** split into two scripted GUIs
when a check and an action need different validity — confirmed via
`je_meiji_restoration_japanese_emperor_check_sgui`
(`common/scripted_guis/journal_entry_sguis.txt`), which is `is_valid`-only
with no `effect` at all, used purely for a `.IsValid()` display check
elsewhere. Our toggle SGUI now has no `is_valid` (always executable); a
second, read-only SGUI holds the real "is this watched" check for the
checkbox's `checked` binding only. **Rule of thumb going forward:** never
give an action-performing scripted GUI an `is_valid` that encodes the
*current value being toggled* — that's a checkbox-loop bug by
construction. If a display-only check and an action need the same
underlying condition, that's a sign they need to be two separate SGUIs,
not one.

## No confirmed way to reference "the player" as a GuiScope root

Investigated 2026-09-07 while scoping the Watchlist category bulk-select
buttons (see TODO.md Phase 3). A bulk action ("flag every current Great
Power/Neighbor/Rival") needs its effect to run with the player's country
as root, so `every_country = { limit = { is_adjacent_to_country = root }
... }` compares against the player rather than some arbitrary scope.
Looked for a way to build that GuiScope (`GetScriptedGui('...').Execute(
GuiScope.SetRoot(<something>).End)`) from a plain button click, not tied
to any specific country's row. `GetPlayer.Self` and `AccessPlayer` are
real, pervasively-used GUI accessors, but found **zero vanilla example**
of either being followed by `.MakeScope` or otherwise fed into
`GuiScope.SetRoot(...)` — every confirmed `SetRoot(...)` example roots on
a country/character *already available in that specific context*
(`Country.MakeScope` inside a country-scoped widget, `Character.MakeScope`
inside a character-scoped one), never "the local player" from an
arbitrary/unrelated context. Did not guess this — same class of mistake
that caused the `is_valid` bug and the tab-merge bug, both from
unverified assumptions about how a GUI mechanism behaved. **Left the
bulk-select/deselect buttons unbuilt** rather than ship another probable
silent-failure. Revisit if a confirmed pattern for this turns up (a real
`script_docs`-style GUI reference would resolve this cleanly, if one
exists).

## Steam Workshop / Paradox mod policy

See [distribution-guidelines.md](distribution-guidelines.md) for the full,
sourced writeup (Paradox's official mod policy, Steam Workshop rules, and
why a similar prior-art mod got removed).
