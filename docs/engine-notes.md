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
  `error.log`/`game.log` (`player_message_type.cpp:177`). Fix by aligning
  them or splitting the diverging one into its own group (with a matching
  `<group>_group` localization string).
  **This is NOT purely cosmetic — treat it as a real functional bug, not
  just log noise.** Confirmed 2026-09-09: `diplomatic_action_notification`
  was muted (`notification_type = none`) but left sharing
  `diplomatic_action_notification_group` with 3 sibling messages still set
  to `toast`. Every play session before the fix (`game.5.log` 12:56 through
  `game.1.log` 14:05, all same day) logged the mixed-types warning 3x, and
  the user kept seeing vanilla-worded "X improving/damaging Relations"
  popups they shouldn't have (that generic wording is
  `diplomatic_action_notification`'s own vanilla text, confirmed via
  `GetDiplomaticAction.GetActionNotificationName`'s loc dispatch — it is
  NOT a separate hardcoded/unfilterable notification with no moddable
  hook, an earlier wrong claim made this same session before the logs were
  actually checked). The regroup fix (splitting the muted key into its own
  group) was committed at 14:28; the very next session (`game.log`,
  started 14:29) has zero mixed-types warnings AND the unwanted popups
  stopped appearing, in the same session, alongside the warning
  disappearing. Working theory, log-correlated but not proven from source:
  a mixed-type group doesn't just warn, it silently falls back the whole
  group to its loudest member's type, defeating an individual `none`.
  Whether or not that's the exact mechanism, the actionable rule is the
  same: never let a muted (`none`) message share a group with a `toast`/
  `popup` one. `tools/check_references.py`'s
  `check_mixed_group_notification_types` now catches this statically —
  confirmed by re-injecting the exact original bug and seeing it fail.

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

**`SCOPE.sC('name')` does NOT need `.GetCountry` chained onto it — it's
already cast.** Confirmed the hard way a second time, 2026-09-08: writing
`06_smart_notifications_diplomatic_action_filtering.txt`, a probe had
confirmed `[THIS.GetCountry.GetNameNoFormatting]` worked from *inside* a
re-scoped `scope:actor ?= { ... }` block (see the probes file). That
result got pattern-matched into a different, un-re-scoped context —
`[SCOPE.sC('actor').GetCountry.GetNameNoFormatting]` — on the assumption
that "add `.GetCountry`" was the general fix, the same shape as the
`THIS` cast below. It isn't: `SCOPE.sC(...)` is *already* Country-cast
(see the line above), so chaining `.GetCountry` onto it is the wrong
accessor for that return type, and it errored the same "Data error in
loc string" way — silently, again, for a whole build cycle, found only
because the user reported a *different*, user-visible bug (broken
notification text) that prompted checking `error.log` at all. `THIS`
needs the cast because it's a generic wrapper; `SCOPE.sC(...)` doesn't,
because the cast is already baked into that function. Two different
things that happen to look similar in the debug_log source — don't
transplant a working chain from one without checking which kind of
scope reference it started from.

## `every_country` does not appear to reach decentralized countries

Confirmed empirically 2026-09-07, and it invalidates the docs: the
`script_docs` dump describes both `every_country` and `any_country` as
"Iterate through all countries globally" with no stated exclusion.

The evidence is unusually clean. The Watchlist's "Deselect All" clears
flags with a plain `every_country` sweep. After a click, **exactly two
countries kept their flags: Anangu and Loango — both decentralized.**
Everything else cleared. The user then unchecked those two by hand (the
per-row checkbox drives a scripted GUI rooted on that specific country, so
it does not iterate) and every bulk action behaved correctly afterwards.

This retro-explains the entire "Select All doesn't select everything"
saga, which cost several rounds and three wrong diagnoses: decentralized
neighbours were never skipped because of adjacency semantics, a bad root,
or a broken effect body. `every_country` simply never visited them, so no
rewrite of the effect body could ever have fixed it.

**Consequences for this mod:**
- Decentralized countries are excluded from the Watchlist everywhere: row
  filters, bulk action limits, the game-start population, the
  `watchlist_is_watched_check_sgui` display check, and the runtime
  `smart_notifications_is_watched` trigger. "Decentralized ⇒ never
  watched" is a hard invariant rather than a filter in one place.
- A stale flag set on a decentralized country *before* those exclusions
  existed cannot be cleared by any bulk action. It is instead rendered
  inert: both the display check and the runtime trigger refuse to treat a
  decentralized country as watched. Only the per-row checkbox can actually
  remove such a flag.

**Lesson:** an iterator's documented description is not a guarantee about
which objects it visits. When a bulk operation misses a *specific,
nameable subset* rather than failing wholesale, suspect the iterator's
coverage before rewriting the body — "which items were missed, and what do
they have in common" is a much faster question than "why is my effect
wrong".

## `THIS` needs a cast: `[THIS.GetCountry.GetNameNoFormatting]`, never `[THIS.GetNameNoFormatting]`

Confirmed 2026-09-07 from the user's own `debug.log`. Every `debug_log`
line this mod had written since the truce tracker used
`[THIS.GetNameNoFormatting]` and every one of them logged
`Data error in loc string '...'` and rendered nothing — including in
plain on_action country scope, where the scope is unambiguously a country.

`THIS` in dynamic text is a generic scope wrapper, not a country. It has
to be cast first. Vanilla is completely consistent about this: grepping
`common/` for `[THIS.*GetNameNoFormatting]` returns 13 hits, **all** of
the form `[THIS.GetCountry.GetNameNoFormatting]` (or
`[THIS.GetCharacter.GetCountry...]`), and **zero** of the bare form.

This is distinct from the earlier `.GetName` vs `.GetNameNoFormatting`
finding, and compounds with it — the accessor name was right, the missing
cast still broke it.

**Why this one was expensive:** it made all instrumentation silently
blind. Several diagnostic rounds on the Watchlist bulk buttons produced
log lines that looked like they had fired but carried no data, so
diagnosis fell back to inferring from screenshots, which produced three
successive wrong root causes. **When a debug tap prints nothing useful,
check the tap itself before theorising about the code it is measuring.**

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
into a new group for independent priority) gets a `"(SN) "` prefix on
whichever loc string is the **settings-list label** (parentheses, not
square brackets — see § Literal `[...]` in loc text below; the first
version of this convention used brackets and broke every string it
touched):
- For messages, that's the `group` loc key (e.g.
  `smart_notifications_truce_expired_group:0 "(SN) Truce Expired"`) — not
  the message's own `_name`/`_desc`, which is the actual toast/popup
  sentence shown in-game and reads awkwardly with a tag prepended.
- For alerts, there's no separate settings-list label — an alert's own
  `_name` loc *is* both its Message Settings row label and its ribbon
  tooltip title, so tagging `_name` covers both automatically (e.g.
  `alert_smart_notifications_amendment_repealable_alert_name:0 "(SN)
  Amendment Repeal Available"`).

**REVISED 2026-09-08** — this started as a trailing `" (Smart
Notifications)"` suffix, changed to a leading `"(SN) "` prefix per the
user after two real problems with actually using the settings screen:
the fixed-width label column truncates hard, and the suffix — the one
thing marking a row as ours — was exactly the part getting cut off; and
the long form made every already-long label longer still. A short prefix
fixes both at once: visible even when truncated, and far shorter.

**EXTENDED 2026-09-08** to also cover standalone in-panel UI labels this
mod adds to a vanilla screen — specifically the law commitment feature's
"Alert me when I can pass this" checkbox
(`gui/politics_panel_change_law.gui`). Originally left untagged on the
reasoning that the convention was about Message-Settings rows
specifically, not general UI text; the user explicitly asked for the tag
here too, since it's still mod-created content a player could mistake for
a vanilla control otherwise. Convention now: `"(SN) "` applies to any
label surfacing that this mod added something, not only Message Settings
rows — the toast/popup body/desc sentence remains the one place it never
goes.

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

## No confirmed way to pass the player in as a GuiScope AddScope value — RESOLVED via two different techniques, not this one

Investigated 2026-09-07 while scoping the Watchlist category bulk-select
buttons and the Neighbors/Rivals live per-row checks (see TODO.md Phase
3). Originally looked for a way to build a GuiScope
(`GetScriptedGui('...').Execute(GuiScope.SetRoot(<something>).End)`)
rooted directly on the player, or to pass the player in as an extra
`AddScope(...)` value, from a plain button click or a per-row check not
tied to a country's own row context. `GetPlayer.Self` and `AccessPlayer`
are real, pervasively-used GUI accessors, but found **zero vanilla
example** of either being followed by `.MakeScope` or otherwise fed into
`GuiScope.SetRoot(...)`/`AddScope(...)` — every confirmed `SetRoot(...)`
example roots on a country/character *already available in that specific
context*. That specific technique is still unconfirmed; **left unused**.

**Resolved 2026-09-07 anyway, via two different confirmed techniques**
that sidestep the whole problem instead of solving it as originally
framed:

1. **For the per-row Neighbors/Rivals live check** (comparing a row's
   candidate country against the player, from inside a scripted_gui's
   `is_valid`, without changing what the row's own root is): don't pass
   the player IN at all — look the player UP from inside the trigger
   block instead. `any_country = { is_player = yes <triggers using
   root> }` is real, confirmed vanilla syntax (`common/scripted_buttons/
   00_balkan_wars_buttons.txt`, `events/ethiopia.txt`,
   `events/krakow_events.txt` all use exactly this "find the player from
   inside a trigger" idiom), and `root` stays bound to the scripted_gui's
   own invocation root throughout the nesting (confirmed by this same
   project's own `common/on_actions/00_smart_notifications_on_actions.txt`,
   which uses `is_adjacent_to_country = scope:smart_notifications_watchlist_player`
   several nesting levels deep and still means the outer root). So
   `watchlist_is_neighbor_check_sgui`/`watchlist_is_rival_check_sgui`
   (`common/scripted_guis/watchlist_sgui.txt`) both use
   `any_country = { is_player = yes ... }` internally, comparing `root`
   (the row's country) against the located player, with zero new GUI
   scope-passing mechanism needed. Rival comparison uses the `?=` scope
   equality comparator inside `any_rival_country`, confirmed via
   `common/power_bloc_names/00_power_bloc_names.txt`'s `c:FRA ?= this`.
2. **For the bulk-select/deselect buttons** (need root itself to BE the
   player, since these run `every_country`/`every_rival_country` effects
   directly off root): bind the button's own container's
   `datacontext = "[GetMetaPlayer.GetPlayedOrObservedCountry]"` in
   `gui/message_settings.gui`. This is a real, confirmed accessor already
   used identically in vanilla (`market_panel.gui`, `right_click_menu.gui`,
   `ingame_hud.gui` all bind a widget's Country context to the player this
   same way, no row/list involved) — inside that container,
   `Country.MakeScope` IS the player, so
   `GetScriptedGui('watchlist_bulk_select_neighbor_sgui').Execute(
   GuiScope.SetRoot(Country.MakeScope).End)` runs with root = player
   directly. The bulk SGUIs (`watchlist_sgui.txt`) then mirror the same
   `every_country`/`every_rival_country` shapes already proven in the
   game-start on_action, just re-triggerable on demand.

Neither technique needed the originally-sought "player as a GuiScope
value" mechanism at all — worth remembering as a general lesson: if a
specific GUI mechanism looks unconfirmed/unsafe, look for a way to route
around the need for it (a trigger-side lookup, or a `datacontext`
rebind) before concluding the feature is blocked.

## `datacontext` + `Country.MakeScope` does NOT give you the player as a scripted_gui root

Found 2026-09-07. The Watchlist's bulk Select All / Deselect All buttons
need their effect to run with the player's country as `root`. The button
container was bound with
`datacontext = "[GetMetaPlayer.GetPlayedOrObservedCountry]"` and the
onclick used `GuiScope.SetRoot(Country.MakeScope)` — reasoning by
analogy with the per-row checkboxes, which use exactly that shape
(`datacontext = "[InterestingCountryItem.GetCountry]"` +
`SetRoot(Country.MakeScope)`) and demonstrably work.

**It does not work for the player accessor.** The row version works
because the datacontext comes from a list item; the
`GetMetaPlayer.GetPlayedOrObservedCountry` version yields a root that is
not usable as the player. The failure is silent — no error, the effect
just doesn't match what it should.

**The diagnostic that isolated it, and the reason it took three attempts:**
the symptom was "Select All doesn't select everything" on the Neighbors
tab only, with the other tabs "working fine". Sorting the bulk actions by
whether they actually depend on `root` explains the whole pattern exactly:

| Bulk action | Uses root how? | Worked? |
|---|---|---|
| Great Powers select/deselect | only `NOT = { this = root }` | yes |
| Watched deselect (clear all) | not at all | yes |
| Neighbors select/deselect | `is_adjacent_to_country = root` | **no** |
| Rivals select | `every_rival_country` (iterates rivals *of root*) | **no** |

Every action that genuinely needs root = player failed; every action that
doesn't need it worked. "Which tab behaves differently" was the clue that
mattered, and it pointed at the shared mechanism, not at the tab.

**Fix:** store the player's country in a global variable from real script
context (game start + monthly pulse, where `is_player` provably works),
and have the bulk effects reference that instead of `root`:

```
set_global_variable = { name = smart_notifications_player_country value = this }   # effect context
is_adjacent_to_country = global_var:smart_notifications_player_country            # anywhere
```

Both halves have vanilla precedent: storing a country scope in a global
variable (`set_global_variable = { name = circassia_recognizer value =
ROOT }`, `common/decisions/01_russia_decisions.txt`) and comparing one in
a trigger (`global_var:chinese_central_government ?= THIS`,
`common/diplomatic_plays/00_diplomatic_plays.txt`). `every_rival_country`
had to be inverted to a world scan (`every_country = { limit = {
any_rivaling_country = { this ?= global_var:... } } }`) since it iterates
relative to the current scope rather than taking a target.

**What is NOT true, recorded because it was written down as fact here for
one commit:** an earlier version of this note claimed
`any_country = { is_player = yes ... }` misbehaves inside a scripted_gui
`is_valid`. It does not — that idiom is used by the Neighbors/Rivals row
checks and the user confirmed those lists are correct in-game. The wrong
conclusion came from assuming a surprising-looking list (a heavily
expanded Portugal being adjacent to Horn-of-Africa minors) was wrong
without checking the actual game state, and then "fixing" the half that
was working.

**Lessons:**
1. When one surface misbehaves and others don't, diff them by *mechanism*
   rather than by feature — the table above took minutes and was decisive
   after two wrong guesses.
2. Before concluding data is wrong, confirm against the actual game state.
   A list that looks implausible may just reflect a campaign that has
   changed a lot.
3. `root` inside a scripted_gui is only as trustworthy as whatever the GUI
   passed into `SetRoot`. It is reliable from a list row (the item supplies
   the object); it is not reliable from the player accessor. Prefer a
   stored global for "the player".

## Known-good invariants are enforced by the validator, not by comments

Added 2026-09-07 after breaking the same confirmed-working code twice in
three commits. The Watchlist's Neighbors row check
(`any_country = { is_player = yes  is_adjacent_to_country = root }`) was
verified correct in-game, then regressed twice:

1. **v0.28, deliberately** — rewritten to a global-variable lookup on a
   wrong diagnosis (a surprising-looking list was assumed wrong without
   checking the game state; it was right).
2. **v0.30, accidentally** — the restore and a blanket
   `s.replace("is_adjacent_to_country = root", ...)` ran *in the same
   script*, so the blanket replace clobbered the line the script had just
   restored. Net effect: the check read "is the player adjacent to the
   player" — always false, emptying the whole tab. It passed syntax
   validation both times, because it was valid script that silently did
   the wrong thing.

Note the asymmetry that makes this trap easy to fall into: the ROW checks
must use `root` (the GUI supplies the row's country, and that works),
while the BULK actions must use the global player pointer (`root` is not
reliably the player from a button). One file, one identical-looking
expression, two opposite correct answers.

`tools/validate_syntax.py` now asserts a `KNOWN_GOOD` list of required
substrings covering both directions, so either kind of rewrite fails the
check that already runs after every file change. Verified by reproducing
the exact v0.30 blanket replace and confirming it now fails.

**Lessons:**
1. Never blanket string-replace across a file that also contains
   deliberately similar-looking expressions with opposite meanings. Edit
   the specific occurrence.
2. A comment saying "do not change this" does not survive a regex. When
   behaviour is confirmed working in-game and cannot be re-tested without
   a human, pin it with a mechanical check.
3. Silent-wrong-behaviour regressions need their own guard: syntax
   validation by definition cannot catch them.

## No generic substring-search filter available for a custom country list

Investigated 2026-09-07 while scoping the "Add a Country" search box
(TODO.md Phase 3). Vanilla's own country search
(`gui/diplomatic_overview.gui`'s `search_bar`, bound to
`DiplomaticOverviewPanel.GetCountriesSearchBar`) turned out to be backed
by a generic `SearchBar` C++ datacontext object
(`gui/shared/search_bar.gui`: `SearchBar.IsQueryEmpty`,
`SearchBar.GetResults`, `SearchResult.GetName`, etc.) — real engine
infrastructure, not something buildable from data-driven script/GUI
alone, and `MessageSettingsWindow` (the class our Watchlist tab is built
inside) exposes no equivalent accessor of its own the way
`DiplomaticOverviewPanel` does. Also grepped every `.gui` file for any
dynamic-text string-contains/substring function (`Contains`, `Find`,
etc.) to see if row `visible` bindings could filter on typed text some
other way — zero matches anywhere in vanilla. Concluded there's no
confirmed-safe way to build a live text filter over the "Add a Country"
list as a mod; the unfiltered list (every country, per TODO.md's original
"contained by design" note) stays the design for this list rather than
guessing at an unconfirmed mechanism. Revisit only if a genuine
per-window search accessor is found some other way.

## Known mistake patterns — now caught by `validate_syntax.py`, not just memory

Raised directly by the user 2026-09-08, mid-session, after the law
commitment feature (see TODO.md) hit the same general CLASS of mistake
five separate times across one afternoon, each only caught after asking
for a live test: "how do we prevent you from doing the same mistakes
over and over again, and not even verifying before sending me to test?"
The honest answer: re-reading the code carefully before shipping had
already failed to catch these more than once in the same session, so the
fix is a mechanical check that runs every time (already a required step
per CLAUDE.md § Autonomous Quality Assurance), not a promise to look
harder next time.

`tools/validate_syntax.py`'s `check_known_mistake_patterns` now flags
three confirmed-real, repeated patterns automatically:

1. **`SCOPE.GetRootScope` used without an immediate cast.** It's a
   generic wrapper — every single vanilla `localization/english/` usage
   of it chains a `.Get*` cast (`.GetCountry`, `.GetState`,
   `.GetDiplomaticPlay`, ...) immediately afterward, with zero
   exceptions found in an exhaustive check, even from contexts where
   root is already conceptually the right type. Calling `.MakeScope` (or
   anything else) on it directly produced a real, confirmed
   `error.log` entry: "Failed to convert statement for argument '0' for
   call 'ExecuteTooltip'" — the whole GuiScope argument never even
   constructed. This is the SAME underlying lesson as `THIS` needing a
   cast that `SCOPE.sC(...)` doesn't (see § Dynamic text vs
   effect/trigger syntax above), just re-hit for a different accessor
   because the earlier lesson wasn't generalized into a rule that gets
   checked every time.
2. **`any_X` (any_law, any_country, ...) used directly inside an
   `effect` block.** `any_X` is trigger-only; the effect-side iterator
   is always a differently-spelled keyword (`every_X`). Produced a real
   `error.log` entry: "Unknown effect any_law". A `limit = { ... }`
   nested inside an effect is still a trigger context, so `any_X` is
   fine there — the checker tracks this correctly (a `limit` block
   flips back to trigger classification even inside an enclosing
   `effect`).
3. **Effect-only keywords (`save_scope_as`, `set_variable`,
   `remove_variable`, `post_notification`, `trigger_event`,
   `custom_tooltip`, `hidden_effect`, `add_variable`) used inside a
   `valid`/`is_valid`/`limit` (pure trigger) block.** Effects silently
   do nothing there — no crash, no error at the call site, just a
   confirmed-real, much-later, easy-to-misread `error.log` entry ("Event
   target 'X' is used but is never set. Setting it in an unused scripted
   trigger or effect does not count") once something tries to read the
   variable that was never actually set.

All three were reproduced against known-bad snippets and known-good
snippets from this repo before being trusted (a linter that's never been
shown to catch anything is worse than useless — it's a false sense of
safety). If a new mistake pattern of this same shape turns up (a
same-looking construct with a subtly different, confirmed-real
requirement), add it to the same function rather than just noting it
here — the goal is that this class of error gets caught by the next
`validate_syntax.py` run, not by re-reading the code more carefully next
time.

## Success-vs-stall comparisons have no numeric form — only threshold checks

The law commitment alert (TODO.md) needed "does this law's next
checkpoint have Success beating Stall" — the same comparison the law
list's own UI displays. There is no single trigger for this, and,
checked directly per the user's own question ("why do you need 99 steps
to compare 2 values? shouldn't you just do A - B > 1%?"): there is no
confirmed way to get either value out as a plain number to subtract.
`enactment_chance_for_law`/`stall_chance_for_law` (script_docs
triggers.log) are pure `{ target = X value > Y }` comparison triggers,
not value-returning functions — `Y` must be a literal (or another
script_value), never another trigger's result. Checked
`common/script_values/script_values.md` directly (the actual spec for
what can appear as a numeric `value`): script values accept numbers,
named script values, and `scope.something` chains to real numeric
event_targets, but nothing suggests a comparison-shaped trigger like
these can be embedded as a bare number — an exhaustive grep for
`value = enactment_chance`/`value = stall_chance` anywhere in the game's
own files (vanilla never does this either) turned up nothing. Absent a
raw number to subtract, "success > stall" is approximated by testing
whether some threshold value V exists with success > V and stall <= V,
swept across a fine grid (1-point steps, 0.01 to 0.99) — see
common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt's
`smart_notifications_law_ready_to_enact` for the implementation. This
isn't overengineering for its own sake; it's the closest approximation
of an exact numeric comparison the engine's own trigger vocabulary
allows.

## Two separate function tables: `.gui` bindings vs. script-side dynamic text — confirming one does NOT confirm the other

**The expensive mistake, made explicit so it doesn't repeat.** The law
commitment alert's dynamic law-name/group text
(`common/scripted_guis/smart_notifications_law_commitment_list_sgui.txt`)
went through several live-test rounds before working, and the final root
cause was a category of mistake this project's own precedent-checking
habit should have caught on the first try: `Law.GetGroup` was treated as
"confirmed real" because it's genuinely, verifiably used in
`gui/politics_panel_types.gui` (`widgetid = "[Law.GetGroup.GetKey]"`,
`InformationPanelBar.OpenChangeLaw(Law.GetGroup)`). That confirmation was
real — but it confirmed the wrong system. Victoria 3 has (at least) two
separate, non-overlapping function/promote tables:

1. **The GUI-binding language**, used inside `.gui` files' own
   `onclick`/`text`/`visible`/`widgetid` attributes. `Law.GetGroup` lives
   here.
2. **The script-side dynamic-text / data-function system**, used inside
   `[...]` brackets in loc strings, `custom_tooltip`, and `debug_log`. This
   is a different, much more restricted table — confirmed by `error.log`
   itself distinguishing them by error type ("Could not find data system
   function" / "Could not find promote for 'X' in 'Y'").

A function confirmed real in one table is **not evidence** it exists in
the other, even for the exact same scope and the exact same-looking dotted
call. `law` scope turned out to have neither a name-getter nor `GetGroup`
in table 2 at all — confirmed directly from `error.log`'s own two lines
(`Could not find data system function 'GetNameNoFormatting'`, `Could not
find promote for 'GetGroup'`), not inferred.

**The fix, once this was understood, was mechanical and fast**: both the
`Get*` calls turned out to be replaceable with zero dynamic-function calls
at all — every law and every law group already carries its own plain
vanilla loc key (`law_<type>`, `lawgroup_<X>`), so a static per-law-type
dispatch (`THIS.type = law_type:X`) selecting a static
`"$law_X$ ($lawgroup_Y$)"` loc string sidesteps the whole function-table
question. Confirmed as the right vanilla pattern before shipping it, this
time by finding on-point precedent in the SAME context we needed — vanilla's
`ACW_DIXIE_STATES_LIST_ENTRY` (a `custom_tooltip`-built list entry, same
mechanism as ours) mixes `[THIS.GetState.GetName]` with plain
`$concept_incorporated$`/`$dixie$` references in one string, proving `$key$`
substitution works inside this exact rendering path, not just in an
ordinary static loc line.

**Why this should not take multiple iterations next time:** the standing
rule (see [[v3-claude-md-restructure]], CLAUDE.md § Engine & Syntax Rules)
was always "confirm via vanilla precedent, don't guess" — but precedent
was accepted from the wrong context. The rule now has teeth: **precedent
for a dynamic-text/`[...]`/`custom_tooltip` call must come from another
dynamic-text/`[...]`/`custom_tooltip` call, never from a `.gui` file's own
binding attributes** — even when the `.gui` usage is 100% real and looks
identical. When no such same-context precedent exists for a scope (as
turned out to be the case for `law` scope's name/group), the safe default
is to assume the function doesn't exist there and reach for a static
`$key$` loc reference instead, which needs no scope-specific function at
all.

## A `.md` schema doc is not proof a key parses — `effect` in a diplomatic action

Confirmed 2026-09-09, and it cost a live test.
`common/diplomatic_actions/diplomatic_action.md` — the game's own schema
doc, shipped in the same folder as the definitions it describes — lists:

```
effect = {} # Effect of action on execution
```

at the top level of an action, between `second_state_trigger` and
`is_hostile`. Placed exactly there, in an override of
`00_relations_actions.txt`, the 1.13.11 parser rejects it outright:

```
Error: "Unexpected token: effect, near line: 70" in file:
"common/diplomatic_actions/00_relations_actions.txt"
```

The key does not exist in this version, whatever the doc says.

**The warning sign was there and was noted before testing:** grepping all
49 vanilla files in `common/diplomatic_actions/` for a top-level `effect`
block returns **zero** hits. A documented field that no vanilla file uses
even once is a field to test in isolation before designing around it —
the same "documented ≠ confirmed" rule this project already applies to
dynamic-text functions (see § Two separate function tables), now extended
to schema docs. The `.md` files are as capable of being stale as any
wiki.

**Cheap way to test a doubtful key next time:** put it in a throwaway
override with a static `debug_log` beside it, launch once, and grep
`error.log` for the filename. A parse error names the file and line
directly. That is one relaunch, versus discovering it after building a
feature on top.

**Practical consequence here:** there is no way to attach mod script to
the execution of a specific vanilla diplomatic action type. Combined with
the finding below (nothing about an action is knowable inside
`on_diplomatic_action`), notification tiers cannot depend on which
diplomatic action fired — from any direction, by any known mechanism.

## The pact for a diplomatic action does not exist yet when `on_diplomatic_action` fires

Confirmed 2026-09-09 with named countries in two independent instruments
at two different times, after a feature built on the opposite assumption
failed silently through 11 real firings.

**The claim:** at the exact instant `on_diplomatic_action` runs, the
`diplomatic_pact` object the action creates is not yet in gamestate. Any
`has_diplomatic_pact` query made from that on_action therefore returns
`no` for the very action that just triggered it — while returning `yes`
normally for every pact established earlier.

**The evidence.** Nawanagar took Improve Relations on the player (Great
Qing) on 17 Jan 1836. At the firing instant:

- all four `has_diplomatic_pact` variants (`increase_relations` /
  `damage_relations`, with and without `is_initiator`) returned `no`;
- an `every_scope_diplomatic_pact` walk of Nawanagar's *own* pact list
  found two pacts, **neither** of type `increase_relations`.

On the next monthly pulse, the identical query — `has_diplomatic_pact = {
who = ROOT type = increase_relations is_initiator = yes }` — returned
`yes` for Nawanagar. Tibet (`damage_relations`, 16 Jan) and Selangor
(`increase_relations`) reproduced it exactly. Two unrelated mechanisms
agreeing at time T+1month and both silent at time T is what makes this a
timing finding rather than a "that trigger doesn't work" finding: **the
query is correct, it is just asked one moment too early.**

This also settles the competing theory that one-sided pacts
(`is_two_sided_pact = no`, which both relations actions are) never create
a queryable pact object at all. They do — `increase_relations` and
`damage_relations` pacts both showed up in the sweep by name.

### Nothing about the action is knowable at that instant

Worth recording so the next attempt doesn't re-derive it. `debug_log_scopes
= yes` at that moment prints:

```
Root: Diplo action Improve Relations (165)

Saved event targets:
actor: Country Nawanagar (415)
recipient: Country Great Qing (156)
notification_target: Country Great Qing (156)
```

The root object plainly knows its own type — and script still cannot ask
it. `triggers.log` and `effects.log` between them support **zero**
triggers and **zero** effects on `diplomatic_action` scope;
`event_targets.log` has no target leading out of `diplomatic_action`, and
none leading into `diplomatic_pact` from anywhere. `is_diplomatic_action_type`
is real but documented for `diplomatic_pact` scope only, and no pact is
reachable here. The three bound scopes are all countries.

(`notification_target` was previously undocumented in this project — it
is bound here and equals the recipient. Found by the scope dump, not by
guessing at names; `debug_log_scopes = yes` is the right first move any
time a scope's contents are in question, and vanilla uses it in
`common/scripted_effects/00_victoria_scripted_effects.txt`.)

**Consequence for design:** a notification's tier cannot depend on the
*type* of the diplomatic action that fired it, because the tier is chosen
at post time and the type is unknowable at post time. Deferring the post
to a later pulse would make the type readable but costs the saved scopes
the message text depends on (`GetActionNotificationDesc` and friends
resolve against the notification's own root), so it trades correct text
for correct tier. If action-importance filtering is wanted here again,
filter on a property of the **actor** — rank, `has_diplomatic_relevance`,
country type — all of which are available at that instant.

## Important-action alert order has no priority field — it's file/definition order

Checked directly (per the user asking what it'd take to keep the law
commitment alert grouped with this mod's other alerts at the bottom of the
Important Actions list) rather than guessing: `common/alert_types/`'s own
complete header comment (`00_alert_types.txt`, lines 1-8) documents every
field the format supports, and there is no priority/weight/order field of
any kind — the only documented sort behavior at all is
"angry_important_action alerts are sorted first". No script-side function
to reorder them was found either (`gui/important_actions_list.gui`'s list
binds to `TopFrontend.AccessImportantActions`, a native accessor with
nothing exposed to influence its ordering).

The observed order (agitator invite, taxation deficit, law commitment —
exactly this mod's own alerts, consecutively, after every vanilla one) is
consistent with the base sort being **file-scan order, then in-file
definition order**: this mod's alerts all live in one file,
`01_smart_notifications_alerts.txt`, which sorts after vanilla's own
`00_alert_types.txt` by filename alone, and the three alerts appear inside
it in exactly the order they were added
(amendment repeal, agitator, taxation deficit, law commitment). No code
change was needed — this grouping already happens by construction and
should stay stable as long as future mod alerts are added to files
numbered `01_` or higher and kept in one file (or several, all sorting
after `00_`); it is not something the alert format lets us pin down more
precisely than that.

## JSON files must NOT have a BOM

Confirmed 2026-09-08 from a real bug: the Paradox launcher's Mod Library
showed "Parsing metadata failed" on this mod, plus a bogus 78-byte size
that never updated after real edits (a stale fallback value shown when
parsing fails, not the real file size). `.metadata/metadata.json` carried
a leading UTF-8 BOM — present since early in this project's history, well
before it was ever noticed, because nothing had actually opened the
Paradox launcher's Mod Library screen against a recently-edited copy
until now.

This is the *opposite* rule from every other modded file: CLAUDE.md
requires a BOM on `.txt`/`.gui`/`.yml` (the game's own script lexer
expects one — see § BOM above), but a BOM is not valid JSON syntax at
all. Confirmed directly: `json.loads(data.decode("utf-8"))` on the BOM'd
file raises `Unexpected UTF-8 BOM` outright, while decoding with
`utf-8-sig` (BOM-tolerant) hides the problem completely. That's exactly
what let this slip past an earlier one-off repo audit in this same
session — it validated "all JSON files parse cleanly" using `utf-8-sig`,
which is BOM-tolerant by design, so it could never have caught this. Any
future JSON validation in this project must decode as plain `utf-8`, not
`utf-8-sig`, specifically to catch this. `tools/check_references.py`'s
`check_json_files_have_no_bom` now does this permanently, for every
`.json` file in the repo, not just `metadata.json`.

## Release candidates are now tagged

The user asked (2026-09-09): "can I easily go back to what we released
on [this date]?" -- previously no. Only one, unrelated tag
(`watchlist-baseline`) existed; every version bump was just a plain
commit, findable only by scrolling `git log`.

Two tag types now exist, both pushed to origin immediately:

- `v<version>-<short-hash>` -- created on every version bump commit (see
  CLAUDE.md § Git Authorship Rules). The short hash is part of the name,
  not decoration: a past version-numbering regression (a 2026-09-07
  commit accidentally reverted `version` from 0.33 back to 0.31, then
  0.32/0.33 were re-earned going forward) means the same version STRING
  legitimately points at two different real commits in this repo's
  history (`v0.31-56e91734` and `v0.31-a2fe32f9`, `v0.32-f8470253` and
  `v0.32-8b852a1b`, `v0.33-0172fc5c` and `v0.33-b70e79e1`) -- a bare
  `v0.31` tag would have collided. Backfilled retroactively for the
  entire existing history (`v0.20` through `v0.34`), from
  `git log --follow -- .metadata/metadata.json`.
- `release-v<version>-<date>` -- created automatically by
  `tools/package_release.py` every time it successfully packages (see
  its own `tag_release_commit` function), pointing at whatever commit was
  actually packaged for external release that day. This is the one that
  directly answers "what did we release on this date" -- distinct from
  the version-bump tags because not every version bump gets externally
  released, and packaging can happen more than once for the same
  version.

To go back to either: `git checkout v0.34-b61f8715` (or any tag from
`git tag -l`). Both are annotated tags (`git tag -a`), not lightweight,
so `git show <tag>` also gives the tagging message/date directly.

## Packaging must stage before swapping, never delete-then-copy in place

Confirmed real 2026-09-09: `package_release.py`'s first version deleted
each shipped folder in the output directory, then recreated it directly.
The Paradox Launcher had `smart_notifications_release` open as a
registered mod entry, and hit a file lock mid-`rmtree` on
`common/messages` -- this left the live output folder PARTIALLY DELETED
(`common/alert_groups` and `common/alert_types` gone entirely,
`common/messages` emptied) until the lock cleared, worse than doing
nothing. Fixed by staging the full copy in a sibling temp directory
first (a lock during staging only touches the temp copy, leaving the
previous good output completely untouched), then swapping each top-level
item into place independently, catching a lock on any individual item
without corrupting the others or aborting the whole operation. A retry
after closing whatever holds the lock only needs to re-run the same
command -- staging always starts fresh from source, which is cheap and
not the risky part.

## Never upload the dev mod folder directly -- it bundles the whole repo

Confirmed 2026-09-08 from the user's own screenshot of the Paradox
Launcher's "Upload Mod" dialog, opened on the existing dev/test mod entry
(`Documents/Paradox Interactive/Victoria 3/mod/smart_notifications`, the
junction to this repo's root). The Launcher's Mod Tools package the
ENTIRE directory a mod entry points at for upload -- there's no
per-folder include/exclude filter in that dialog. Since the dev junction
points at this whole repo, uploading from it would ship `tools/`,
`docs/`, `reference/` (verbatim vanilla-file snapshots, see
docs/distribution-guidelines.md), `.git/`, `TODO.md` (160KB+ of internal
process history), and every other dev-only file to every subscriber.

**Decision (explicitly the user's call, not assumed):** given a choice
between (a) restructuring this repo so mod content lives in its own
subfolder and repointing the dev junction there -- correct in principle,
but touches every tool script's paths and dozens of path references
across CLAUDE.md/TODO.md/this file -- versus (b) a separate packaging
script producing a clean copy at a second, upload-only mod folder, the
user chose (b): zero risk to the existing dev/test workflow. Implemented
as `tools/package_release.py` (wrapped as `/package-release`) -- copies
only `.metadata/`, `common/`, `events/`, `gui/`, `localization/`, and
`thumbnail.png` to
`Documents/Paradox Interactive/Victoria 3/mod/smart_notifications_release`,
refusing to run if `validate_syntax.py` fails on the source first. The
existing dev junction is untouched; add the release folder as its own
separate Mod Library entry and upload from there, never from the dev
one.

## Steam Workshop / Paradox mod policy

See [distribution-guidelines.md](distribution-guidelines.md) for the full,
sourced writeup (Paradox's official mod policy, Steam Workshop rules, and
why a similar prior-art mod got removed).
