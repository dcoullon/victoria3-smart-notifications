# Victoria 3 — Smart Notifications & Watchlist: Roadmap

This is the living backlog/roadmap for the mod. It's forward-looking (what's
planned and what's in progress). For a player-facing, backward-looking record
of what actually shipped in each version, see [CHANGELOG.md](CHANGELOG.md).

## Distribution & platform scope

- **Steam is the sole distribution target** for now (Steam Workshop / the
  Paradox Mods integration Steam surfaces for Victoria 3) — not a standalone
  Paradox Mods upload, not Nexus, etc.
- **Single-player only.** Multiplayer compatibility is explicitly not a goal.
  `metadata.json` sets `multiplayer_synchronized: false` accordingly.

## How to use this file

- Each unchecked box is planned, not yet shipped.
- Status markers: `[ ]` not started · `[~]` in progress / partially done ·
  `[x]` done.
- When an item ships, check it off **here** and add a matching entry to
  [CHANGELOG.md](CHANGELOG.md) under the version it shipped in (Added /
  Changed / Fixed / Removed), so the two files never drift apart.

---

## Phase 0 — Bootstrap Verification (target: v0.1.0)

Confirm the simplest possible mod actually loads in-game before anything else.

- [x] Ship one trivial, visibly-different-from-vanilla change whose only
      purpose is to prove the mod is loading: a custom
      `smart_notifications_mod_loaded` toast (see
      [00_messages.txt](common/messages/00_messages.txt)) fired once per
      campaign via an `on_game_started_after_lobby` hook (see
      [00_smart_notifications_on_actions.txt](common/on_actions/00_smart_notifications_on_actions.txt)),
      with its own localization
      ([smart_notifications_l_english.yml](localization/english/smart_notifications_l_english.yml)).
      Cheap enough to keep permanently as a "mod active" signal.
- [x] Set `multiplayer_synchronized: false` in `metadata.json` — this mod is
      single-player only. Also relocated `metadata.json` itself into
      `.metadata/metadata.json`, which is where the current Vic3 mod format
      expects it (was sitting at the mod root before).
- [x] Deploy the mod: created an NTFS junction from
      `Documents/Paradox Interactive/Victoria 3/mod/smart_notifications` to
      this repo, so edits here are picked up live without re-copying.
- [x] Fix `supported_game_version` — was stale at `1.8.*` from the initial
      commit; the actually-installed game is `1.13.11`. Now `1.13.*`.
- [x] Add the mod to an active **Playset** in the Paradox Launcher (Mod
      Library alone isn't enough — the Home screen only shows/loads mods in
      the currently-selected playset) and toggle it on.
- [x] Confirmed via `game.log`: mod mounted and
      `"Mod Smart Notifications (smart_notifications) version 1.13.* successfully
      matched game version 1.13.11"`. No fatal errors attributable to this
      mod in `error.log` (two unrelated pre-existing vanilla warnings are not
      ours — see the Phase 0/1 test plan). Still needs eyes-on: does the
      "Smart Notifications active" toast actually render on screen?

## Phase 1 — Signal-to-Noise Baseline (target: v0.1.0)

- [x] **Dominion & Subject War Mute** — shipped 2026-09-07 as part of
      Phase 4's relational engine landing (see below), not as a blunt
      `notification_type` change. `diplo_play_join_side_notification` is
      now muted entirely and replaced by
      `smart_notifications_diplo_play_join_side_watched`/`_quiet`
      (`common/on_actions/03_smart_notifications_relational_notifications.txt`),
      which only elevates a join-side event to toast when a watched
      country (or the player) is involved — a dominion/subject
      auto-joining its overlord's side now stays in the quiet feed unless
      someone in the play is actually on the watchlist. **Not yet
      confirmed in-game.**
- [x] **Conscription Noise Reduction** — shipped as a blunt global demotion:
      `country_conscription` is `none` for everyone (see
      [00_messages.txt:1489](common/messages/00_messages.txt)), not scoped to
      "declared strategic interests" as originally envisioned. Scoping that
      condition also depends on Phase 4-style relational/on_action logic —
      revisit then if the blunt version proves too quiet.
- [x] **Attitude Shift Demotion** — `country_attitude_improved/changed/worsened`
      all demoted to `none`. No scoping needed here; matches spec as-is.
- [x] **Threat Escalation** — already satisfied by vanilla defaults, no change
      needed: `diplo_play_war_start_notification` is `popup`,
      `diplo_play_start_notification` is `toast`. Confirming the popup
      actually auto-pauses is part of Phase 0 in-game verification, not a
      code change.
- [x] **Gemini Gem review folded in (2026-09-04)**: muted
      `foreign_political_lobby_disbanded(_with_reason)` and
      `harvest_condition_started_in_country`/`_in_market` (106 firings in
      one session, confirmed the right call); demoted
      `national_awakening_started` and
      `political_lobby_disbanded(_with_reason)` to feed; left
      `character_exiled`, `diplomatic_proposal_third_party`,
      `diplo_play_start_third_party` at vanilla feed (Gemini judged these
      too risky to mute — real early-warning value); kept the sway family
      unified at toast. **Split two groups** rather than force siblings to
      match: `invasion_started_against_us` → new group
      `invasion_against_us_notification_group` (toast, defensive
      emergency), while `invasion_started`/`invasion_succeeded`/
      `invasion_failed` stay in the original group at feed (planned
      execution, not an emergency); `diplo_play_subject_released_overlord_notification`
      → new group `diplo_play_subject_overlord_notification_group` (toast,
      losing your own subject), while `diplo_play_subject_released_notification`
      stays at feed (third-party, ambient). Re-ran
      `tools/compare_notification_settings.py --all` — no mixed-group
      warnings introduced.
- [x] **Fix mixed-group notification_type inconsistencies** — confirmed live
      in `error.log` ("Diplomatic Play Subject Group has mixed Notification
      Types", "Sway Offer Group has mixed Notification Types", "Invasion
      Group has mixed Notification Types") during the first real playtest.
      Resolved by aligning every sibling in each group to `toast`:
      `invasion_notification_group` (4 members: `invasion_started`,
      `invasion_started_against_us`, `invasion_succeeded`,
      `invasion_failed`), `sway_offer_notification_group` (4 members,
      accepted + rejected), `diplo_play_subject_notification_group` (2
      members). May revisit as a group-split if the relational engine
      (Phase 4) wants any of these pairs to actually differ.

## Phase 2 — War Outcome & Peace Terms Announcer — CLOSED, not needed (2026-09-05)

**Scoping done 2026-09-03, re-scoped 2026-09-04, closed 2026-09-05 — kept
this history rather than deleting it, since it's a real example of scoping
down to "check if the problem still exists" before building anything.**

Confirmed real hooks investigated along the way (all safe append-only,
single effect block each, no vanilla file needs a full override to reach
them, in case a related feature wants them later):
- `on_war_end` — Root = Diplomatic Play, `scope:actor` = Initiator,
  `scope:target` = Target. Currently just sets `recently_had_war` variables.
- `on_peace_agreement_signed_war_leader` / `_war_participant` /
  `_non_participant` — Root = Country (the receiving country per role).
- `on_self_capitulated_notification` / `on_enemy_capitulated_notification` /
  `on_ally_capitulated_notification` — Root = Country; vanilla already
  distinguishes self/enemy/ally, `scope:target` names which specific country.
- Each treaty-article type (`common/treaty_articles/`) supports an
  `on_enforced` effect block, fired only when a treaty article is imposed
  via a war/diplomatic play (not a normal AI-to-AI trade) — the mechanism
  that would have been used for "what specifically did we win/lose", had it
  been needed. Its own scope objects aren't documented, unlike
  `on_entry_into_force`/`on_withdrawal`.

**Resolved 2026-09-05, per the user, closing this phase:** confirmed
in-game that the peace popup now actually shows the treaty terms — the
core complaint this phase was scoped to fix is not a live problem on the
current game version. Removed the exploratory `on_enforced` debug-tap
overrides of `05_transfer_money.txt`/`06_transfer_state.txt`/
`30_transfer_subject.txt` (and their `reference/vanilla/` archive copies)
that were added 2026-09-04 to investigate this — no longer needed, and
per the "minimal override surface" guardrail, an unused override of real
vanilla mechanics isn't worth carrying.

**What's left, not worth its own phase:** the user confirmed the *only*
remaining piece of the original complaint is
`diplo_play_back_down_involved_notification` ("[actor] backed down...
against [target]") still not naming the play's stakes/wargoals — a
different code path (a play backing down before war, not a war ending).
Their WIP doc (see below) flagged this as P1 ("leverage same thing for
when back down on diplo play"), but in the chat that followed they
downgraded it to "not important" — going with the more recent, spoken
call. Not scheduling it; revisit only if it becomes annoying in practice.

**Vanilla display bug observed, not ours to fix:** a "Danish victory over
Great Britain" popup showed the enforced demand as "Annex Denmark" — i.e.
the winner's own name in the loser's slot. This is vanilla's own
localization, not something this mod touches; nothing actionable here
short of a bug report to Paradox. Noted in case it recurs and looks like
something we caused.

## Phase 3 — Country Watchlist Selection UI (target: v0.3.0)

**Spec refined 2026-09-06 with the user — read this before implementing,
it fully replaces the original one-line stub.**

### Scope decision (asked the user directly)

- **Which events get elevated for a watched country:** diplo plays & wars
  only for v1 (join side, start play, war start/end, invasions) — the
  core "are they in a fight" signal. Political-change categories
  (revolutions, attitude, government) explicitly deferred, not in scope
  yet.
- **One unified list**, not a separate "watchlist" + "scary Great Powers"
  list — a country is either watched or not, used for everything
  (including the still-separate, not-yet-built "won't intervene anymore"
  stretch feature, which can reuse this same list later).

### Data model — REVISED 2026-09-06, static flags not live filters

**Reversing the earlier live/dynamic decision** — the user reconsidered:
a live filter risks being confusing (a country silently joining/leaving
your watchlist as borders shift, with no explicit action from the player)
and, more importantly, this mod's stated priority is that **performance
always matters**, and the user wants that treated as a first-order
architectural concern, not an afterthought. Landed on a genuinely simpler
*and* cheaper design instead of a compromise between the two goals:

- **Four flags per country, not one** — `watched_via_great_power`,
  `watched_via_neighbor`, `watched_via_rival`, `watched_manually`.
  **Revised again 2026-09-06:** started with a single shared
  `watched_country` flag, but the user correctly flagged that a country
  can belong to multiple categories at once (e.g. a neighboring Great
  Power) — with only one flag, deselecting a whole category could
  silently un-watch a country you still wanted for a *different* reason.
  Separate provenance flags fix this cleanly.
- **Runtime "is this country watched" check** is an OR of all four:
  `has_variable = watched_via_great_power` OR `_neighbor` OR `_rival` OR
  `_manually` — still just flag lookups, no trigger evaluation, no
  cross-scope comparison. Four `has_variable` checks instead of one is a
  negligible cost difference, nowhere near the live-filter version this
  replaced.
- **"Great Powers" / "Neighbors" / "Rivals" bulk-select** applies only
  that category's own flag (`set_variable = watched_via_great_power`,
  etc.) to every country currently matching it, right now — the confirmed
  triggers below (`country_rank >= rank_value:great_power`,
  `is_adjacent_to_country = root`, `every_rival_country`) are read
  exactly once per click, never again at notification time.
- **Bulk-deselect a category** clears only that category's own flag —
  a country that's also watched via a different provenance flag correctly
  stays on the effective watchlist (the OR is still true). This is the
  whole reason for 4 flags instead of 1.
- **The individual per-row checkbox in the UI means something different
  and simpler:** "is this country watched, period" — unchecking it clears
  *all four* flags at once, a full removal regardless of how many reasons
  it had. Checking an unwatched row (e.g. from a category browse list, or
  the Manually Added search) sets only the one flag appropriate to where
  you checked it.
- **No auto-refresh** — if your neighbors change later (a war, a trade),
  the watchlist doesn't silently update. This is accepted staleness, not
  an oversight: matches "static list, no surprises" per the user, and
  re-clicking a category's bulk-select later is the designed way to
  refresh it.
- **Category *membership* (who currently qualifies) is still computed
  live, but only for the UI**, never for the runtime notification check —
  see the UI section below for exactly how each section is populated.
  This is a one-time computation when a screen opens, the same cost class
  as any other info panel in the game, nothing like a per-notification
  cost.

Confirmed-real triggers behind each category (from the `script_docs`
dump, see [docs/engine-notes.md](docs/engine-notes.md) for how that dump
works) — used only at click-time now, not at runtime:
- **Great Powers:** `country_rank >= rank_value:great_power` — an exact
  tier comparison via `common/country_ranks/00_country_ranks.txt`.
- **Neighbors:** `is_adjacent_to_country = root` — a real country-to-country
  adjacency check (already used in vanilla's own `30_transfer_subject.txt`).
  **Confirmed acceptable 2026-09-06:** the user is fine with this counting
  a country across a sea strait as a neighbor — they don't expect it to
  meaningfully bloat the list.
- **Rivals:** `every_rival_country` (bulk), run directly from the
  player's own scope — **caught and fixed during implementation
  (2026-09-06):** this spec originally said `every_rivaling_country`,
  which is the *other* direction (`any_rivaling_country`/
  `every_rivaling_country` = countries rivaling *us*, i.e. one-sided AI
  hostility; `any_rival_country`/`every_rival_country` = countries *we've*
  declared as rivals). "Countries the player has declared as rivals" is
  `every_rival_country`. Confirmed 2026-09-06: just that declared-rivalry
  mechanic. The "scary folks / won't intervene" idea from the original
  WIP doc is explicitly dropped as a separate concept — not planned as
  part of this list at all anymore.

**Defaults at game start:** run all three bulk actions once
(Great Powers + Neighbors + Rivals) during the existing
`on_game_started_after_lobby` hook, per the user's "prepopulate with
neighbors + Great Powers" answer — this is just the same one-click bulk
action fired automatically at campaign start, not a separate mechanism.

### Country renaming caveat (carried over from Phase 3/4 notes)

Still needs checking whether a revolution/government change swaps to a
genuinely new country tag (variable lost) or renames the same tag in
place (variable survives) before relying on `watched_country` persisting
through one.

### UI — design confirmed 2026-09-06, ready to build

**Star icon dropped 2026-09-06, per the user** — investigating it turned
up real complexity (see the resolved item below): the country panel's
pin/unpin-style icon row isn't local to `country_panel.gui` at all, it's
baked into a shared base template (`gui/block_windows.gui`) used by
dozens of unrelated panel types, with no spare slot for a third icon.
Rather than either risk a shared-file regression or spend more time
hunting for a country-panel-local injection point, the user decided to
drop the country-panel toggle entirely and rely solely on the management
screen for adding/removing countries — which the spec below already
supports fully on its own (every category section already browses *all*
qualifying countries with a checkbox, not just already-watched ones, so
nothing is lost by not also having a panel-side shortcut). **The
management screen is now the single v1 UI deliverable**, not a "v2"
following a star — see the checklist below.

**Related discovery, investigated and rejected as a shortcut (2026-09-06):**
`gui/message_settings.gui` has a fully-wired-looking **third, hidden tab**
— "Interesting Countries" (`MESSAGE_SETTINGS_DIPLOMATICALLY_INTERESTING`),
complete with a per-country dropdown datamodel
(`GetInterestingCountryItems`/`GetInterestingCountrySettings`) that looks
almost exactly like what we're building. It's hardcoded
`visible = no` with a `# todo PRCAL-26835` comment — an unshipped Paradox
feature. Checked whether it's worth re-enabling instead of building our
own screen: **no** — only the tab title itself has any localization
(`MESSAGE_SETTINGS_DIPLOMATICALLY_INTERESTING`); the actual per-option
setting names inside the dropdown have zero loc strings anywhere, and no
`common/` database defines what "interesting" tiers exist (unlike
`alert_types`, which is fully real and complete). That combination reads
as genuinely unfinished — likely UI-only or entirely disconnected from
any real notification behavior — not a small polish gap. Not building on
this; noted here so it doesn't get "discovered" again as a false shortcut
later.

**Management-screen UX** (their ask: show currently-selected countries
with one-click deselect *including by category subsegment*, one-click
select, and a plan for a potentially long country list, "take inspiration
from EU4's country selector, propose something better if you have it"):

- **A "Watched" tab is the default/main view** — added 2026-09-06 per the
  user, who wanted one obvious place to see and remove anyone currently
  watched without having to remember which category section they're
  sitting in. Flat list, the union of all four flags, one row per
  currently-watched country, each with small tags showing which
  category(ies) currently apply (e.g. "Prussia — Great Power, Neighbor")
  for transparency without needing to hunt for them elsewhere. The row
  checkbox here is the same full-removal semantics as below (unchecking
  clears all four flags).
- The other sections — **Great Powers**, **Neighbors**, **Rivals**,
  **Manually Added** — are secondary tabs whose job is *discovering and
  bulk-adding* new countries, not reviewing what's already watched (that's
  what the Watched tab is for).
- **Great Powers / Neighbors / Rivals sections browse everyone who
  currently qualifies for that category**, not just already-watched ones
  — each row has a checkbox reflecting current watched status, computed
  fresh when the screen opens (display-only, doesn't touch the flags by
  itself). This lets the same list both add newly-qualifying countries
  and review/remove existing ones, rather than needing two different
  views. A country matching multiple categories simply appears in more
  than one section — expected and fine, per the multi-category flag
  design above.
- **Manually Added works differently**, since "everyone in the world"
  isn't a browsable list: with an empty search box it shows your current
  `watched_manually` countries; typing in the **search/filter box**
  (flat list, filters live — confirmed 2026-09-06, no dropdown-typeahead
  for v1) searches the full country list so you can check new ones in.
  This is also where the "long list" problem is contained, since the
  other three sections are naturally small.
- Each section header has one **bulk-select** and one **bulk-deselect**
  button acting on that section's current members and setting/clearing
  *only that category's own flag* (see data model above) — this is how
  "deselect just my neighbors, leave Great Powers alone" works without
  side effects, and also how a stale category gets refreshed (re-click
  bulk-select to pick up new neighbors since the last click).
- Each individual row's own checkbox means "watched or not, period" —
  clears/sets across all four flags at once (see data model above), not
  scoped to the section it's shown in.

- [x] **v1 — Scripted GUI Logic** — built 2026-09-06:
      [watchlist_sgui.txt](common/scripted_guis/watchlist_sgui.txt).
      Toggles the watched state (all 4 flags, per the individual-row
      semantics above) on a target country; includes
      `ai_is_valid = { always = no }` and `ai_chance = { base = 0 }` per
      [CLAUDE.md](CLAUDE.md). Will be wired to row checkboxes on the
      management screen (see below) rather than a country-panel star.
- [x] **Country Panel Bookmark Button — dropped 2026-09-06, not
      building.** Investigated `gui/country_panel.gui` for where the
      pin/unpin icon already sits (confirmed real precedent:
      `Country.IsPinnedInOutliner` / `Country.TogglePinInOutliner`, using
      the exact
      `GetScriptedGui('key').Execute(GuiScope.SetRoot(Country.MakeScope).End)]`
      pattern confirmed elsewhere for onclick handlers) — real complexity
      found: that icon row is fixed layout inherited from a shared base
      template (`gui/block_windows.gui`) used by dozens of unrelated panel
      types, with no spare 3rd icon slot, so adding one risks a regression
      well outside this feature's scope. Per the user, dropping this
      entirely rather than pursuing either fix (override the shared file,
      or hunt for a country-panel-local spot) — the management screen
      alone is sufficient, see above.
- [x] **v1 — Game-start defaults** — built 2026-09-06, added to the
      existing `on_game_started_after_lobby` hook
      ([00_smart_notifications_on_actions.txt](common/on_actions/00_smart_notifications_on_actions.txt)):
      runs Great Powers + Neighbors + Rivals bulk-select once, using
      `every_rival_country` run directly from the player's own scope for
      Rivals (simpler than a candidate-loop, since it doesn't need
      comparing against the player) and one shared `every_country` pass
      for Great Powers + Neighbors (avoids iterating the whole world
      twice for two checks that both need it). **Not yet confirmed
      in-game** — needs a fresh campaign start to verify the flags
      actually land on the right countries.
- [~] **v1 — Management screen, first slice built 2026-09-06, NOT YET
      SEEN IN-GAME.** Per the user, dropped the "new topbar button" idea
      entirely in favor of a much lower-risk approach: a genuinely new
      **4th tab inside the existing Message Settings window**
      ([gui/message_settings.gui](gui/message_settings.gui), full-file
      override — same pattern as `common/messages/00_messages.txt`).
      This needed no new entry point at all (the window's already opened
      via the gear icon players already use), and `tab_buttons` already
      supports up to 5 slots (confirmed: `country_panel.gui`'s own tab
      strip uses all 5) — vanilla only wired up 3, so a 4th ("Watchlist")
      is a clean addition, not a repurposing. Left the vanilla, still-hidden
      3rd tab ("Interesting Countries") completely untouched in case
      Paradox ever finishes it.
      **Key technical bet, not yet confirmed:** there is no general
      "every country in the world" datamodel reachable from this window,
      so the new tab's list reuses `[MessageSettingsWindow.GetInterestingCountryItems]`
      — the *same* data source backing that hidden 3rd tab — purely as a
      country-enumeration source. Only that tab's dropdown/settings half
      looked unfinished (zero localization, no backing data file, per the
      earlier investigation); the "give me a list of items wrapping a
      Country" half looked complete, so this reuses only that part with
      our own item template (checkbox wired to `watchlist_toggle_sgui`'s
      new `is_valid` check, added alongside its existing `effect`).
      **This is the single biggest open question in the whole feature:**
      if `GetInterestingCountryItems` turns out to return an empty list
      (since the feature it belongs to is switched off), the new tab will
      render with zero rows and this whole approach needs a rethink. The
      very first thing to check in-game is simply "does the Watchlist tab
      show any countries at all."
      Also found and fixed a real bug in our OWN validator while doing
      this — see
      [docs/engine-notes.md § validate_syntax.py bug](docs/engine-notes.md):
      it falsely reported this file as unbalanced because its
      comment-stripping wasn't quote-aware (GUI files embed `#title`-style
      formatting codes inside strings). Fixed the tool itself, re-confirmed
      PASS across the whole repo.
      Category sub-sections built 2026-09-07, NOT YET SEEN IN-GAME — see
      the dedicated writeup below.

**Two real bugs found live 2026-09-06/07, both fixed, re-test pending:**
1. **Checkbox never visibly toggled, even after a full window
   close/reopen — root-caused and fixed.** The user's clean re-test (fresh
   click, full close/reopen, still unchecked) ruled out a caching/redraw
   explanation and pointed at the click itself doing nothing. Root cause:
   `watchlist_toggle_sgui`'s `is_valid` was set to "is this country
   already watched" — but `is_valid` isn't just a query, it's the actual
   gate the engine uses to decide whether `.Execute()` is allowed to run
   at all. So clicking to *watch* an unwatched country was silently
   refused every time (`is_valid` was false for exactly the countries
   worth clicking), no error logged anywhere. **Fixed** by splitting into
   two scripted GUIs — `watchlist_toggle_sgui` (no `is_valid`, always
   executable) for the click, and a new `watchlist_is_watched_check_sgui`
   (is_valid-only, no effect) for the checkbox's `checked` read — following
   a real vanilla precedent
   (`je_meiji_restoration_japanese_emperor_check_sgui`) that does exactly
   this split. See
   [docs/engine-notes.md § A scripted GUI's is_valid also gates .Execute()](docs/engine-notes.md).
2. **Reproduced consistently by the user, root-caused, fixed:**
   closing Message Settings while the Watchlist tab is active, then
   reopening, merged the Watchlist and Alerts tabs' content visibly on
   top of each other (confirmed by screenshot — both tabs' header rows
   and list rows overlapping). Root cause: the four tab-selection
   variables (`message_settings_notification_types/alerts/
   interesting_countries/watchlist`) are `GetVariableSystem` values that
   persist across the window closing — vanilla's own logic only knows
   about its original three and picks a fallback tab (alerts) on reopen
   without any awareness that a 4th variable exists to also clear, so
   both `message_settings_alerts` and our `message_settings_watchlist`
   ended up simultaneously `'true'`. Explains why clicking any of *our*
   tab buttons fixed it (they're wired to reset all 4) while reopening
   the window didn't. **Fixed** by explicitly clearing
   `message_settings_watchlist` on both paths that close the window we
   control (the header X and the bottom Close button). **Residual risk,
   not fully closed:** couldn't find whether an Escape-key shortcut or
   some other close path exists outside those two buttons — if the bug
   still reproduces via some other route, that's why.
### Category sub-sections — built 2026-09-07, two real simplifications made

Since `tab_buttons` caps at 5 slots (already used by our one outer
Watchlist tab + 3 vanilla ones), the 5 categories live as a **custom
sub-navigation row INSIDE the Watchlist tab** (a plain button row we built
ourselves, not the vanilla `tab_buttons` component), switching a
second, mod-only `GetVariableSystem` variable
(`smart_notifications_watchlist_section`). "Watched" is the default —
its own visibility condition is "explicitly selected OR none of the other
four are" so the list is never empty on first open.

- [x] **Watched** — exact union of all 4 flags, using the same
      `watchlist_is_watched_check_sgui` as the checkbox itself.
- [x] **Great Powers** — a genuinely live check
      (`watchlist_is_great_power_check_sgui`, `country_rank >=
      rank_value:great_power`), browses anyone currently a Great Power
      regardless of watched status, exactly per the original spec.
- [x] **Neighbors / Rivals — UPGRADED 2026-09-07 to true live checks,
      the original spec.** The "no confirmed way to reference the
      player" blocker was real for the *specific* technique tried
      (passing the player in as a GuiScope value), but not for the
      problem itself — found a different, fully-confirmed way around it:
      `any_country = { is_player = yes <triggers using root> }` locates
      the player from *inside* the trigger block instead of needing it
      passed in from the GUI side (confirmed real vanilla idiom — see
      [docs/engine-notes.md § No confirmed way to pass the player in as a GuiScope AddScope value — RESOLVED](docs/engine-notes.md)).
      `watchlist_is_neighbor_check_sgui`/`watchlist_is_rival_check_sgui`
      now browse "anyone currently adjacent/rivaled," not just previously
      flagged countries. **Confirmed live 2026-09-07** — the user's v0.23
      test showed both sections populating correctly (previously empty
      for the boring reason above: the flag-based version depended on a
      game-start hook that had never run for that save).
- [~] **Bulk-select/deselect buttons — BUILT 2026-09-07, confirmed live
      but with 2 real bugs found and fixed same day (see below).** One
      Select All / Deselect All pair per category (Great Powers/
      Neighbors/Rivals), shown under the sub-nav row only for the active
      category. Resolved via a *different* confirmed technique than the
      live-check fix above: binding the button's container to
      `datacontext = "[GetMetaPlayer.GetPlayedOrObservedCountry]"` (a
      real vanilla accessor, used identically in `market_panel.gui`/
      `right_click_menu.gui`/`ingame_hud.gui`) makes `Country.MakeScope`
      inside it resolve to the player, so the bulk SGUIs
      (`watchlist_bulk_select_*_sgui`/`watchlist_bulk_deselect_*_sgui`,
      `common/scripted_guis/watchlist_sgui.txt`) run with root = player
      directly — same `every_country`/`every_rival_country` shapes
      already proven in the game-start on_action. Deselect clears only
      that category's own flag, per the multi-flag data model.
      **Bug #1, fixed:** the individual per-row checkbox
      (`watchlist_toggle_sgui`) was shared across all five row types and
      always set `watched_manually` on a fresh watch regardless of which
      section it was clicked from — contradicting the spec ("sets only
      the one flag appropriate to where you checked it") and making a
      category's Deselect All silently skip any row the player had
      hand-checked from that same category, since it was tagged manual
      underneath, not with that category's flag. Split into
      `watchlist_toggle_great_power_sgui`/`_neighbor_sgui`/`_rival_sgui`,
      one per section, each setting only its own flag on the fresh-watch
      branch; the removal branch (uncheck clears all four) is unchanged
      and still shared conceptually across all five row types.
      **Bug #2, diagnosed via temporary `SNW_WATCHLIST|` debug taps in
      the three bulk-select SGUIs (still in place as of this commit —
      delete once confirmed, same as the truce tracker's taps) — root
      cause not yet fully confirmed live, this is the leading hypothesis
      pending the next test:** the reported "Select All doesn't select
      everything" is suspected to be Bug #1 above wearing a different
      face — countries the player had already hand-checked earlier
      (recorded as `watched_manually`) would already show as checked
      regardless of whether Select All's own `every_country` pass
      actually reached them, masking whether the bulk effect itself
      was working. **Needs a fresh, clean test** (ideally on countries
      never individually clicked before) to confirm Select All now
      covers the full matching set post-Bug-#1-fix.
- [~] **"Add a Country" — deliberately still unfiltered; a real search
      box was investigated and found genuinely blocked, not just
      unbuilt.** Vanilla's own country search (`diplomatic_overview.gui`)
      turns out to be backed by a `SearchBar` C++ datacontext object with
      no equivalent accessor on `MessageSettingsWindow`, and no
      dynamic-text substring/contains function exists anywhere in
      vanilla to filter on typed text another way — see
      [docs/engine-notes.md § No generic substring-search filter available for a custom country list](docs/engine-notes.md).
      Shows every country in the world, unfiltered, so you can scroll and
      check any one — not a stopgap, the actual intended design until a
      real mechanism turns up.
- [x] **Neighbors grouped by continent — BUILT 2026-09-07, not yet
      confirmed in-game.** The user's v0.23 test confirmed the Neighbors
      list can be genuinely huge for a colonial-holding country (their
      Portugal game showed dozens of adjacent countries scattered across
      Africa/Asia/the Americas — real, not a bug, since colonial
      possessions create far-flung borders) and asked for continent
      sub-grouping *within* the existing Neighbors section, not another
      clickable tab layer. Used the exact continent split vanilla itself
      defines for `is_country_on_same_continent`
      (`common/scripted_triggers/00_geography_triggers.txt`): a
      country's capital's state region's `is_in_geographic_region`
      membership in one of vanilla's 4 macro-regions (Europe/Americas/
      Africa/Asia — no separate Oceania bucket in vanilla's own version
      of this check either, so Oceania countries land under Asia here
      too). Four new `watchlist_is_in_<region>_sgui` checks
      (`watchlist_sgui.txt`) ANDed with the existing live neighbor check
      in four new row types, laid out as four flowcontainers with a
      `GetGeographicRegion(...).GetName` header label each (reusing
      vanilla's own continent localization) stacked in the same
      scrollarea — still one "Neighbors" section, just visually grouped.
      Rivals/Great Powers weren't given the same treatment: both are
      naturally small (a handful of declared rivals; Great Power count
      is capped by `country_ranks`), so no grouping need was evident.
- [ ] **v2 / stretch, only if v1 proves too broad in practice** —
      restrict the manual-add search list to countries within the
      player's declared strategic interest regions
      (`any_scope_interest_marker` from country scope, per the user's
      "likely only surface countries in your strategic interest regions"
      idea) rather than every country in the world. Explicitly deferred —
      the user flagged this as the part most likely to be over-engineering
      if done too early.

## Phase 4 — Relational Notification Engine (Capstone) (target: v1.0.0)

This is what actually makes proper Phase 1 dominion/subject scoping possible —
see the note on that checkbox above. This also closes out the mod's stated
scope ("notification defaults, dominion spam mute, and relational country
watchlist" per `metadata.json`).

**Architecture note (see the override-hierarchy entry in `CLAUDE.md`):**
`post_notification = <key>` can't override `notification_type` per call, and a
player's saved Message Settings override a whole `group` regardless of what
our script says. So "toast for watched countries, feed for everyone else" on
what's conceptually the same event needs **two separate message keys/groups**
(e.g. a `_watched` variant and a default variant), with script logic in the
on_action choosing which one to `post_notification`. Plan the message key
list for this phase with that in mind before writing the on_action.

- [~] **On-Action Interception / Relational Scope Filtering / Targeted
      Alerts — v1 BUILT 2026-09-07, not yet confirmed in-game.** Scoped
      with the user to the 3 diplo-play events with a clean, confirmed
      hook (real on_action names found via `common/on_actions/
      00_code_on_actions.txt`, not the approximate `on_diplomatic_play_start`/
      `on_war_begins` names this bullet originally guessed at):
      `on_diplo_play_start`, `on_diplo_play_join_side`,
      `on_diplo_play_war_start` (all Root = Diplomatic Play). Deferred:
      war end/peace (already gets popup+treaty-terms coverage from
      Phase 2's existing, unconditional peace/capitulation
      notifications) and invasions (no moddable hook exists for 3 of its
      4 keys — see Dev Tooling below — only `on_invasion_succeeded` is
      real, and even that can't suppress the vanilla notification, only
      add a supplementary one; deferred rather than shipped
      asymmetrically). Leader deaths (this bullet's original third
      target) dropped entirely — never actually in scope per the 2026-09-06
      scope decision under Phase 3 ("diplo plays & wars only for v1"),
      this bullet's own wording just predated that decision and was
      never reconciled with it until now.
      Implementation:
      [03_smart_notifications_relational_notifications.txt](common/on_actions/03_smart_notifications_relational_notifications.txt)
      appends to all 3 vanilla on_actions (never redefines their effect
      directly, per CLAUDE.md) and uses `any_scope_play_involved`
      (confirmed real via the game's own `script_docs` effects.log —
      "Iterate through all involved in a: diplomatic play") to check
      every participant's watched flags, `OR`ed with `is_player = yes`
      so a play involving the player directly is always elevated
      regardless of watchlist. Per the architecture note above and
      confirmed with the user 2026-09-07: **replaces** vanilla's own
      notification for these 3 groups (muted to `notification_type =
      none` in `00_messages.txt`) with a watched/quiet pair each —
      watched → toast (war-start → `popup`, preserving vanilla's own
      war-start escalation only for wars that actually involve someone
      watched), quiet → feed (war-start quiet → `toast`, since a war
      starting is still more notable than an ordinary play). This also
      lands the long-open Phase 1 "Dominion & Subject War Mute" item —
      see that checkbox above.
- [ ] **Country renaming caveat (from user's WIP doc, 2026-09-05):** a
      watched-country flag stored as a scope variable on the country should
      survive a revolution/government change that renames/reforms the
      country (the user specifically flagged this as something to "pay
      attention to"). Confirm before implementation whether Vic3 revolutions
      actually swap to a *new* country tag (variable would be lost) or
      rename the *same* tag in place (variable survives) — don't assume.

---

## Stretch / under consideration (not scoped into this mod yet)

Deliberately kept out of the numbered roadmap: a UI/UX overhaul rather than a
notification feature, and doesn't fit this mod's stated scope. Revisit once
Phase 4 ships and is stable — possibly as v1.x of this mod, possibly as its
own separate mod. No version target until that's decided.

- [ ] **Diplo Play Infamy & Predictor Warning**
  - [ ] **Infamy Threshold Alert** — compute
        `predicted_infamy = current_infamy + war_goal_infamy` in
        `common/script_values/`.
  - [ ] **Visual Threshold Banners** — in
        `gui/popup_start_diplomatic_play.gui`, show warnings at the 25
        (Infamous) / 50 (Notorious) / 100 (Pariah) thresholds, explaining
        that nearby Great Powers will turn antagonistic.
  - [ ] **Entangling Alliances Surface** — display the defender's active
        defensive pacts, guarantees, and any Great Power with a Protective
        attitude toward them, before the player commits to 'Start Play'.
  - [ ] **Predicted AI reaction, not just infamy** — per the user's WIP doc
        (2026-09-05): crossing an infamy threshold also changes which
        countries are predicted to intervene, not just whether they turn
        antagonistic in the abstract. The predictor should reflect that
        knock-on effect, not just show the raw infamy number.
- [ ] **Diplo Play "leaning for/against" display (P0 per user, 2026-09-05)**
      — screenshotted in the user's WIP doc: the diplomatic-play begin
      screen (`gui/popup_start_diplomatic_play.gui`, the "Demand" popup)
      already computes a per-country prediction score (visible in an
      "Undecided" table with a numeric `Prediction` column and colored
      +/- values) but the top-of-screen "Enemy Side" summary only lists
      countries *guaranteed* to join — it drops everyone merely predicted
      or leaning one way, even though their flags do show up lower in the
      Undecided/Prediction table. Ask: surface at least the predicted set
      in the top "Enemy Side" (their flags already exist per the
      screenshot), ideally also anyone with a positive leaning score on
      either side. Needs a look at `gui/popup_start_diplomatic_play.gui`
      and whatever script value backs that `Prediction` column before
      scoping further.
- [ ] **"Won't intervene anymore" watch (P2 per user, 2026-09-05)** —
      notify when a Great Power (or a user-curated "scary folks" list,
      likely the same watchlist as Phase 3) that previously would have
      intervened against the player stops being willing to, so the player
      knows a window to start a diplo play has opened. Needs a "notify me"
      button surfaced in the diplo-play-start menu per the user — distinct
      from the Entangling Alliances Surface above (that's informational at
      play-start time; this is a standing watch that fires later).

---

## Dev tooling (delete before publish)

- [x] **Scoped notification-frequency logger** —
      [01_smart_notifications_logger.txt](common/on_actions/01_smart_notifications_logger.txt)
      hooks 24 vanilla on_actions to write a distinctive `SNW_LOG|<key>` line
      to `debug.log` (via the `debug_log` effect — an earlier version wrongly
      used a nonexistent `log` effect, fixed 2026-09-03 before it was ever
      tested) every time one of our reviewed notification keys is about to
      fire. After a real playtest, get frequency counts with:
      ```bash
      grep "SNW_LOG|" "Documents/Paradox Interactive/Victoria 3/logs/debug.log" \
        | sed 's/.*SNW_LOG|//' | sort | uniq -c | sort -rn
      ```
      **Player-scoping (2026-09-04, partial; CORRECTED 2026-09-06):** raw
      counts include events the player could never have seen (AI-to-AI
      interactions). Added `is_player` filtering for the hooks where the
      scope type is confirmed (`harvest_condition_started_in_country` and
      a properly-traversed `national_awakening_started`).
      **Correction:** the `diplomatic_proposal_third_party*` family (6
      hooks) was *also* filtered originally, on the strength of
      `diplomatic_action.md` saying "root = action initiator" — that
      turned out to be a category mistake (that doc describes a
      diplomatic_action *type's own* effect/ai blocks at definition time,
      not this on_action's runtime root) confirmed wrong by a real,
      repeating `error.log` entry: `is_player trigger [ Wrong scope for
      trigger: diplomatic_action, expected country ]` (root is genuinely
      "Diplomatic Action" per vanilla's own comment). Reverted those 6 to
      unfiltered, matching the family below, rather than guess a second
      time. **Still unfiltered:** the
      `diplo_play_*`/`sway_*`/`country_swayed`/`diplomatic_demand_*`/
      `diplomatic_proposal_third_party*` families — these are rooted on
      "Diplomatic Play"/"Diplomatic Demand"/"Diplomatic Action" (not a
      country), and no documented target link was found for any of them;
      guessing risks a load-time or runtime validation error, not just a
      wrong number, so left
      as-is rather than repeat the earlier syntax mistake. Their counts
      still mean "how often this happens in the world," not "how often you
      saw it," until this is resolved.
      **Coverage gap, confirmed by exhaustively grepping vanilla `common/`
      and `events/`:** `country_attitude_improved/changed/worsened`,
      `country_conscription`, `country_mobilization`, all four
      `invasion_*` keys, both `political_lobby_disbanded*`/
      `foreign_political_lobby_disbanded*` keys, and
      `harvest_condition_started_in_market` are posted by native engine
      code with **no moddable hook at all** — not fixable, not just
      unexplored. This notably includes the two originally-biggest
      suspected offenders (`country_attitude_changed`,
      `country_conscription`). `exile_notification` is skipped too — it
      fires from many scattered individual events, no single safe append
      point. For all of these, manual observation during play (screenshots)
      is the only signal available.
- [ ] Remove `01_smart_notifications_logger.txt` before publishing, unless a
      later phase (e.g. Phase 4's relational engine) wants to keep some form
      of it.
- [x] **Phase 2 scoping debug tools — removed 2026-09-05, phase closed.**
      `02_phase2_scoping_debug.txt` (war-end/peace/capitulation scope dump)
      and the treaty-article `on_enforced` debug taps in
      `05_transfer_money.txt`/`06_transfer_state.txt`/`30_transfer_subject.txt`
      (added 2026-09-04) are both deleted — see the Phase 2 section above:
      the user confirmed in-game that vanilla's peace popup already shows
      treaty terms, so the phase closed with no new content needed and
      these tools have nothing left to scope.

## Marketing idea (not scheduled — for when the mod is closer to release)

User idea (2026-09-04): a Reddit post showing **how many notifications fire
over ~10 years of default-settings gameplay**, broken down by type, as a
visual way to make the spam problem concrete before linking to the Steam
Workshop page.

- The frequency logger already measures this correctly in principle — it
  counts the underlying game event regardless of `notification_type`, so
  the same tool works whether run against vanilla defaults or our mod's
  tuned defaults, no separate "unmodded" run needed.
- **But this makes finishing the player-scoping fix (see Dev Tooling below)
  a hard requirement, not a nice-to-have** — a public claim needs a
  defensible number. A count that includes AI-vs-AI events the player could
  never have seen would overstate the problem and is an easy, embarrassing
  thing for a skeptical redditor to poke a hole in.
- Getting a real 10-year sample probably means a dedicated `-debug_mode`
  data-gathering run (console-assisted time skip) purely for this
  statistic — separate from any achievement-relevant playtest.
- **Audited 2026-09-04, real gap found:** the logger's original 24 hooks
  only covered notifications from our own Phase 1 muting review. Cross-checked
  against every key this mod actually changes (`CHANGELOG.md`) and found:
  - The two flagship original "worst offenders"
    (`country_attitude_changed`, `country_conscription`) plus
    `country_mobilization`, all four `invasion_*`, and both
    `political_lobby_disbanded*`/`foreign_political_lobby_disbanded*` keys
    are **structurally uncountable** — no script hook exists at all (see
    the coverage-gap note above). No logger fix closes this; a Reddit post
    can't cite exact numbers for these, only observation/screenshots.
  - Added 9 more hooks that *were* closeable:
    `peace_agreement_signed_war_leader/war_participant/non_participant`,
    `self/enemy/ally_capitulated`, `wargoal_added`/`wargoal_removed`, and
    `diplo_play_back_down_involved_notification` (the exact one the user
    observed lacking context). `is_player`-filtered the 8 that are
    confirmed country/scope:actor-rooted; left the back-down one
    unfiltered like the other unconfirmed Diplomatic-Play-rooted hooks.

## More spam candidates from the user's WIP doc (2026-09-05, not yet triaged)

Raw list from the doc, not yet checked against what's already muted in
[00_messages.txt](common/messages/00_messages.txt) or against the
uncountable/no-hook list in Dev Tooling above — triage before building:

- [ ] **Tech spreading notification** — user suspects vanilla may already
      have a per-notification setting for this; check Message Settings
      before assuming it needs a mod change at all.
- [ ] **Foreign political lobby *formed*** — confirmed 2026-09-05: two
      distinct keys, `foreign_political_lobby_created` and
      `foreign_political_lobby_created_from_catalyst`
      ([00_messages.txt:751](common/messages/00_messages.txt)), both still
      at vanilla `feed` — untouched by Phase 1, which only muted the
      *disbanded* pair. Same category of frequent/low-agency noise as the
      disbanded pair we already muted to `none`; likely wants the same
      treatment for consistency, but hasn't been done — do it, or confirm
      with the user first since "formed" (unlike "disbanded") might carry
      slightly more early-warning value.
- [ ] **"Random country won war"** — checked 2026-09-05: **no
      `country_won_war`-shaped message key exists at all** — there's no
      generic "X won the war" notification. What actually exists and would
      fire here is `peace_agreement_signed_war_leader`/`war_participant`
      and the three capitulation keys (already `popup`, Phase 2's hooks),
      plus `diplo_play_war_start_third_party_notification` (already
      vanilla `feed`, i.e. already fairly quiet) for wars you're not part
      of. So this isn't a missing/wrong message — it's the general Phase 4
      relational-scoping gap (these fire for every participant regardless
      of whether the player cares about them). No new key needed; just
      needs Phase 4's watchlist filtering applied to the existing ones.
- [ ] **UK-and-subjects diplo-play spam (P0 per user)** — when a Great
      Power declares war/joins a play, every subject/dominion that follows
      along fires its own separate notification. Wanted: show only the
      overlord's notification, optionally naming the subjects who followed
      inside that same message. **Not yet confirmed in-game as of 2026-09-05
      per the user** — verify it's still actually spammy on the current
      version before scoping (same "check it's still a problem first"
      discipline that closed Phase 2). Likely depends on Phase 4's
      relational engine to identify "reports to the same overlord as an
      already-notified country" and suppress the duplicate.

## Documentation backlog

- [ ] **"How to add this mod" guide with screenshots**, step by step — the
      manual local-install flow turned out to be unintuitive: Mod Library
      alone doesn't make a mod active, it has to be added to a **Playset**
      via the Home screen's playset dropdown, and a stale
      `supported_game_version` silently shows a confusing warning triangle
      instead of a clear error. Cover: where the mod folder goes, Mod
      Library vs. Playset, the "Add more mods"/playset-editing step, and how
      to read the version-mismatch warning. (Steam Workshop subscribers
      won't need this — subscribing adds a mod to the playset automatically;
      this is for manual/local installs, e.g. beta testers pre-Workshop.)
- [x] **Investigate the "Important Actions & Alerts" settings tab —
      confirmed 2026-09-05.** It's a genuinely separate system from
      `common/messages/*.txt`: `common/alert_types/00_alert_types.txt` +
      `common/alert_groups/00_alert_groups.txt` — standing conditions with
      a `valid` trigger the engine re-evaluates continuously (no on_action,
      no pulse-scan needed), shown as top-ribbon icons, independently
      tunable as `alert | important_action | angry_important_action | none`.
      Full writeup in
      [docs/engine-notes.md § Two entirely separate notification systems](docs/engine-notes.md).
      **This directly changes the plan for 3 items below** (truce
      expiry, law-support, repeal-amendment) — an alert-type entry is
      simpler than a monthly-pulse message for all three, if the
      underlying condition turns out to be a queryable trigger.

## Release checklist (every version)

- [ ] No bundled third-party assets (audio/images/fonts) without clear
      rights — see [docs/distribution-guidelines.md](docs/distribution-guidelines.md).
      Still free/non-commercial, per Paradox's mod policy.
- [ ] Workshop update notes remind players to open **Message Settings** and
      click **Reset to Default** (per affected category) or **Reset All** —
      any group they've customized before keeps their old value until reset,
      regardless of what this mod's script defaults say. See the
      override-hierarchy note in `CLAUDE.md`.
- [ ] `python tools/validate_syntax.py` passes.
- [ ] Diff against `reference/vanilla/` reviewed so the changelog entry is
      accurate.

## Technical guardrails

Full protocol lives in [CLAUDE.md](CLAUDE.md) (terse rules) and
[docs/engine-notes.md](docs/engine-notes.md) (the reasoning/evidence behind
them) — not repeated here to avoid a third source of truth.

---

## Candidate feature: state-change watchers (not scheduled into a phase yet)

Idea from the user (2026-09-03): notify when you can safely withdraw from a
**Law Commitment** treaty article (`common/treaty_articles/20_law_commitment.txt`)
without penalty — one country can force another to keep a specific law for a
negotiated **5/10/20-year `binding_period`**. Confirmed directly from the
file: withdrawing before it elapses triggers `on_break` (relations -10 to
-50, infamy +2 to +20, both scaled by time remaining); withdrawing after is
a literally empty `on_withdrawal` effect — zero penalty. Vanilla never
surfaces "you can now withdraw penalty-free" as a notification.

This is a genuinely different *kind* of feature from everything built so
far. Phase 0-2's notifications all react to a vanilla on_action firing at
the moment something happens. This one needs to notice a **state that
becomes true silently over time** (a binding period elapsing) — nothing
"fires," so there's no event to hook.

Feasibility, checked before adding this: `on_monthly_pulse_country` (Root =
Country) is a real, confirmed pulse hook; vanilla itself iterates a
country's treaties/articles via functions like `every_active_treaty` /
`any_scope_article` with `has_type = <article>` filters (confirmed used in
`common/treaty_articles/00_alliance.txt` and others) — so scanning for
"any law_commitment article where `remaining_binding_period` just crossed
zero" is realistic. Needs a repeat-guard (a variable set on first notify)
so it doesn't re-fire every month afterward.

- [ ] **Law Commitment expiry notification** — monthly-pulse scan +
      new message key/localization + a repeat-guard variable. Scope the
      exact variable-storage approach (on the treaty, the article, or the
      country) before starting.
- [ ] Consider this as a template for a broader **"state-change watcher"**
      pattern, not a one-off — other "did a condition just become true"
      ideas (crossing a radicalism threshold, becoming eligible for a
      government-type change, etc.) would reuse the same monthly-pulse +
      repeat-guard shape. Worth a dedicated phase if more of these show up.

More candidates surfaced in the user's WIP doc (2026-09-05), same
monthly-pulse + repeat-guard shape as the Law Commitment idea above —
grouping them here rather than writing three near-duplicate sections:

- [~] **Truce expiry notification — built 2026-09-06, needs an in-game
      truce to confirm.** The user confirmed (2026-09-06) they want this
      despite the small country count, and only the "just expired" half is
      buildable (see the earlier finding below on why "expiring in one
      month" isn't). Shipped:
      [common/on_actions/02_smart_notifications_truce_tracker.txt](common/on_actions/02_smart_notifications_truce_tracker.txt)
      — a monthly pulse (`on_monthly_pulse_country`, `is_player`-gated)
      that iterates every country, flags one with `has_truce_with = root`
      via a variable set *on that country* (variable names are static
      keys, can't be parameterized per-tag, so the flag has to live on the
      other country rather than as a list on us), and fires
      `smart_notifications_truce_expired`
      ([00_messages.txt](common/messages/00_messages.txt), new `toast`
      group) when the flag is set but the truce is gone. Uses
      `save_scope_as` to carry the partner country across the `root = {
      post_notification = ... }` switch-back, mirroring the
      `save_temporary_scope_as` pattern already seen in
      `05_transfer_money.txt`. Localization added with the
      `SCOPE.sC('name').GetName` dynamic-text pattern this project already
      uses. **Not yet confirmed live** — this project's scope/effect
      chaining has been wrong on the first try before (the Phase 2 debug
      tool), so treat this as needing a real truce to expire in-game before
      calling it done. Original finding, for context: grepped the
      `script_docs` dump exhaustively for "truce"/"days_left" and found
      only the boolean `has_truce_with` and two creation effects — no
      remaining-duration value exists (unlike obligations, which do have
      one), which is why only the edge-triggered "just expired" version
      exists at all.
- [~] **"You can now pass a law you wanted" notification — scoped further
      2026-09-06, not yet built.** The user clarified: this should only
      fire for specific laws the player actually wants, not every law —
      so the trigger side (`enacting_any_law = yes` +
      `enactment_chance`, both confirmed real) isn't enough by itself; it
      needs a **per-law opt-in**, the same "toggle a flag via a
      scripted GUI button" shape as Phase 3's watchlist. Concretely: a
      `common/scripted_guis/` entry on the law-enactment screen that sets a
      variable on the law type (or a list of wanted law types on the
      country) when the player clicks "notify me," and the alert's `valid`
      trigger checks `enacting_any_law = yes` + that law being flagged +
      `enactment_chance > <threshold>`. **This is now the same shape as
      Phase 3's watchlist toggle** (Country Panel Bookmark Button) — worth
      building whichever of the two comes first as the template for the
      other. **Still open:** what enactment-chance threshold reads as
      "will pass" (likely `> 0.5`, needs checking against how vanilla's own
      UI colors that number) and where exactly on the law-enactment GUI a
      button anchors cleanly. Remember the notification-tagging convention
      below when this ships.
- [x] **"You can now repeal an amendment" notification — built and
      shipped 2026-09-06.** Per the user, this one should surface on the
      top ribbon — used `type = important_action` (not plain `alert`) for
      exactly that. Shipped:
      [common/alert_types/01_smart_notifications_alerts.txt](common/alert_types/01_smart_notifications_alerts.txt),
      a genuinely new file (alert_types merge additively across files in
      the folder, unlike `common/messages/`, so no vanilla file needed
      copying — see engine-notes.md). Trigger chain:
      `any_active_law = { any_scope_amendment = { amendment_can_be_repealed
      = yes } } }`, confirmed from the `script_docs` dump. Kept the
      localization static (no dynamic scope reference) since clicking the
      alert opens the politics panel where the specific amendment is
      visible anyway — lower-risk than the `SCOPE.GetRootScope...` chains
      vanilla's own alert loc uses for dynamic alert text. **Needs in-game
      confirmation**, same caveat as the truce tracker above — not yet
      seen live.

**Truce tracker confirmed live 2026-09-06** — the user saw the "Truce with
[Country] has expired" toast fire for real, with the country name resolved
correctly, confirming the `save_scope_as` mid-loop pattern works as
designed. Amendment alert still awaiting a real repealable amendment to
confirm the `valid` trigger chain itself, but a real bug was already
caught and fixed in its Message Settings label: an alert needs a separate
`<key>_setting_name` loc key (no `alert_` prefix) distinct from
`alert_<key>_name` (the ribbon tooltip) — omitting it showed the raw
script key in Message Settings instead of a label. See
[docs/engine-notes.md § An alert type needs TWO name-shaped loc keys](docs/engine-notes.md).

**Regression found and fixed 2026-09-06** — a second truce expired and
the user didn't see a toast this time, despite the above. Investigated
via the `SNW_TRUCE|` debug taps added for exactly this: `expired_detected`
and `notification_posted` both logged correctly, so the on_action logic
itself is solid — the break was in text rendering, and `error.log` had
two real, confirmed causes:
1. The `" [Smart Notifications]"` tag added to
   `smart_notifications_truce_expired_group` (see the tagging-convention
   entries elsewhere in this file) used square brackets, which are
   **always** parsed as a dynamic-text function call in this engine, no
   escape exists — broke the entire group label (confirmed:
   `Could not find data system function 'Smart' in 'Smart '`). This is
   the more likely reason the toast didn't visibly appear at all,
   possibly breaking the whole group's rendering, not just its
   Message-Settings label. Fixed by switching the whole tagging
   convention to parentheses instead — see
   [docs/engine-notes.md § Literal `[...]` in loc text](docs/engine-notes.md).
2. Separately, `debug_log` itself errored on plain `.GetName`
   (`Could not find data system function 'GetName' in 'THIS.GetName'`) —
   every vanilla `debug_log` example uses `.GetNameNoFormatting` instead.
   Unclear whether this specific one also breaks real notification loc
   (vs. just `debug_log`'s plain-text renderer specifically) since the
   *first* truce toast worked with plain `.GetName` — but fixed
   defensively everywhere regardless, since `.GetNameNoFormatting` is the
   exhaustively-confirmed-safe vanilla convention and there's no reason
   not to use it. See
   [docs/engine-notes.md § `GetName` is not a valid dynamic-text function](docs/engine-notes.md).

**Not yet re-confirmed live** — needs another truce expiry (or a repeat of
whatever the second, silent one was) to confirm both fixes actually
resolve it.

**Follow-up 2026-09-06 — a second truce expired and the user didn't notice
a toast.** Checked `error.log`/`debug.log` for the session: no errors at
all from `02_smart_notifications_truce_tracker.txt` (a good sign — nothing
is crashing), but there was also no `debug_log` instrumentation in that
file to confirm one way or the other whether the expiry was actually
detected, so absence of an error isn't proof of correct behavior here.
Added three **temporary debug taps** (`SNW_TRUCE|pulse_ran`,
`SNW_TRUCE|flag_set`, `SNW_TRUCE|expired_detected` /
`SNW_TRUCE|notification_posted`) so the next truce set/expire cycle leaves
a full trail in `debug.log` — delete once confirmed either way. One
plausible non-bug explanation worth ruling out first: a truce that was
**already active** before this file was even added only gets its tracking
flag set on the *first* monthly pulse after that (the tracker can't know
retroactively how long a pre-existing truce has left) — so a truce that
happened to expire in that same first tracked month would be a real,
expected one-time miss, not a bug. Grep for `SNW_TRUCE|` after the next
occurrence to tell the two apart.

**Unrelated bug found while checking these logs — fixed same day
(2026-09-06):** `error.log` showed `is_player trigger [ Wrong scope for
trigger: diplomatic_action, expected country ]` repeating constantly,
traced to `01_smart_notifications_logger.txt`'s 6
`diplomatic_proposal_third_party*` hooks (see the corrected
Player-scoping note above for the full detail — the original
"is_player-safe" claim was a category mistake, not a real scope
confirmation). Reverted those 6 to unfiltered.

**Notification tagging convention adopted 2026-09-06** — checking Message
Settings, the user couldn't tell our custom rows apart from vanilla ones
at a glance. Any message group / alert `_name` that's genuinely new content
(not a re-tuned or split vanilla notification) now gets a
`" [Smart Notifications]"` suffix on its settings-list label only (never
the in-game toast/popup sentence itself). Applied retroactively to
`smart_notifications_truce_expired_group` and the amendment alert's
`_name`; full rule and reasoning in
[docs/engine-notes.md § Tagging mod-created notifications](docs/engine-notes.md)
and [CLAUDE.md](CLAUDE.md). Deliberately NOT applied to
`invasion_against_us_notification_group`/`diplo_play_subject_overlord_notification_group`
(Phase 1 group-splits of vanilla content, not new notifications).
