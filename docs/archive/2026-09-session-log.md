# Session log archive — September 2026

Working notes moved out of TODO.md on 2026-09-15, when that file had reached
4,034 lines with 55% of it dated logs, which made the live backlog unreadable.

**This is history, not a plan.** Nothing here is an open commitment; anything
still open lives in [TODO.md](../../smart_notifications/TODO.md). It is kept because several of
these entries carry the evidence behind a decision — what was tried, what the
engine actually did, and why an approach was abandoned — and that evidence is
not recorded anywhere else. Durable engine facts have been promoted to
[engine-notes.md](../engine-notes.md); this is the narrative underneath them.

Ordered as it appeared in TODO.md: closed phases first, then the
2026-09-08..09-09 session rounds in sequence.

## DONE 2026-09-10: this mod's rows now sit last in Message Settings

Kept for the findings, which cost two attempts to get.

**The order is filename order, then definition order within the file.** Paradox
reads `common/messages/*.txt` in filename order. This mod's keys were already
last within `00_messages.txt`, but vanilla's `01_event_messages.txt` through
`unification_notifcations.txt` are read after it -- so the fix was a filename,
not a reordering. All 166 invented keys now live in
`common/messages/99_smart_notifications_messages.txt`.

**What the first attempt got wrong**, both worth remembering:

1. Extracting by byte offset instead of by name. The blocks looked contiguous,
   but the backward walk over the introducing comment run cut into vanilla
   content. The rewrite parses line by line, buckets every line into head or a
   named block, and asserts that no code line was lost -- so a mistake fails
   loudly instead of quietly shipping.
2. A regex using `re.S` for the block body while also matching the comment run
   with `.*` -- DOTALL makes `.` cross newlines, so the comment pattern
   swallowed whole blocks and only three units were found.

**And it exposed a real latent problem.** `check_full_overrides_match_installed_vanilla`
compares line SETS across the whole file. Our muted `diplo_play_war_start_notification`
had deliberately dropped `popup_name` and `on_created_soundeffect` (they caused
a confirmed double full-screen popup, see that key's comment), and the check
never noticed because this mod's OWN war-start key contained the same two
lines. Moving the mod's keys out removed the coincidence. The omission is now
declared in `ALLOWED_VANILLA_OMISSIONS` with its reason, so it is exempt on
purpose rather than by accident.

### Superseded notes from before it was done

Asked for by the user 2026-09-10: all `(SN)` rows grouped at the end of the
Notification Types list, ordered so related ones sit together. Attempted the
same day, backed out, worth doing properly as its own focused change.

### What was learned

**The order is filename order, then definition order within the file.** The
game reads `common/messages/*.txt` in filename order and lists rows in the
order it read the definitions. This mod's keys are already last *within*
`00_messages.txt`, but vanilla's own `01_event_messages.txt` through
`05_japan_messages.txt` and `unification_notifcations.txt` are read after it,
which is why vanilla rows (Law Imposed, Colonial Claim Granted, ...) still
appear below ours.

**So the fix is a filename**, not a reordering: move every key this mod
invents into `common/messages/99_smart_notifications_messages.txt`. A 99_
prefix sorts after every vanilla message file.

**Sort within the file by the group's `(SN) ...` loc label, not by key name.**
What sits together on screen is decided by the label, and several keys
deliberately share a group. Keys sharing a group must keep their relative
order, because a shared row renders at whichever of its keys the game reads
first (this is why the three "Non Watched" diplo-play keys are defined after
the per-family rows -- see `common/messages/00_messages.txt`).

### Why the first attempt failed -- read before retrying

`00_messages.txt` is a **full override of vanilla's file**, and
`check_references.py` enforces that every line present in the installed
vanilla file is also present in ours. The extraction script assumed this mod's
blocks were a contiguous tail and cut from the first one to EOF; they are not
quite, and the cut removed vanilla content. The checker caught it immediately
and the file was restored from a backup taken before the run.

Retry with: extract blocks **by name** (`smart_notifications_*` only), never
by offset; carry each block's leading comment with it; assert the count of
extracted blocks matches the count of `smart_notifications_*` definitions
before writing anything; and run `validate_syntax.py` before committing. Take
a copy of `00_messages.txt` first -- that copy is the only reason the failed
attempt cost nothing.

### Worth knowing

This is cosmetic. It changes nothing about behaviour, and it touches the file
with the highest blast radius in the mod, so it should not ride along with
functional changes.

## Phase 0 — Bootstrap Verification (target: v0.1.0)

Confirm the simplest possible mod actually loads in-game before anything else.

- [x] Ship one trivial, visibly-different-from-vanilla change whose only
      purpose is to prove the mod is loading: a custom
      `smart_notifications_mod_loaded` toast (see
      [00_messages.txt](../../smart_notifications/common/messages/00_messages.txt)) fired once per
      campaign via an `on_game_started_after_lobby` hook (see
      [00_smart_notifications_on_actions.txt](../../smart_notifications/common/on_actions/00_smart_notifications_on_actions.txt)),
      with its own localization
      ([smart_notifications_l_english.yml](../../smart_notifications/localization/english/smart_notifications_l_english.yml)).
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
      [00_messages.txt:1489](../../smart_notifications/common/messages/00_messages.txt)), not scoped to
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

## Phase 3 — Country Watchlist Selection UI — CLOSED, confirmed working 2026-09-07

**BASELINE.** The country selector was confirmed working end-to-end in-game
by the user on 2026-09-07 and is the clean baseline for all later work: five
views (Watched / Great Powers / Neighbors grouped by continent / Rivals /
All Countries), per-row checkboxes, and Select All / Deselect All per tab
(Watched has Deselect All only). Decentralized countries are excluded
throughout. The mechanisms that make it work are pinned in
`tools/validate_syntax.py`'s KNOWN_GOOD list — if a later change trips one of
those, restore the invariant rather than "fixing" it, and re-read
`docs/engine-notes.md` first.

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
dump, see [docs/engine-notes.md](../engine-notes.md) for how that dump
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
      [watchlist_sgui.txt](../../smart_notifications/common/scripted_guis/watchlist_sgui.txt).
      Toggles the watched state (all 4 flags, per the individual-row
      semantics above) on a target country; includes
      `ai_is_valid = { always = no }` and `ai_chance = { base = 0 }` per
      [CLAUDE.md](../../CLAUDE.md). Will be wired to row checkboxes on the
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
      ([00_smart_notifications_on_actions.txt](../../smart_notifications/common/on_actions/00_smart_notifications_on_actions.txt)):
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
      ([gui/message_settings.gui](../../smart_notifications/gui/message_settings.gui), full-file
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
      [docs/engine-notes.md § validate_syntax.py bug](../engine-notes.md):
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
   [docs/engine-notes.md § A scripted GUI's is_valid also gates .Execute()](../engine-notes.md).
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
- [x] **Neighbors / Rivals live checks — CONFIRMED CORRECT LIVE
      2026-09-07.** `any_country = { is_player = yes <trigger using
      root> }` in the row's `is_valid` works fine; the user verified the
      resulting lists are right for their game (a heavily-expanded
      Portugal genuinely is adjacent to Horn-of-Africa minors, which had
      been misread as the list being over-inclusive). Briefly rewritten
      to a global-variable lookup on that wrong diagnosis and then
      restored — the actual bug was in the bulk actions, see below.
- [x] **Bulk-select/deselect buttons — CONFIRMED WORKING IN-GAME
      2026-09-07.** Root cause found by the user. Select All appeared to skip
      countries on the Neighbors tab across many versions. It was not the
      effect body (rewritten three times: root -> global variable ->
      is_player+save_scope_as) and not the invocation: the root probes
      confirmed all three SetRoot forms execute the effect. **The skipped
      countries were all decentralized** (Ajuran, Anuak, Aulihan, Bemba)
      — they show as adjacent for display purposes but aren't picked up
      the same way by the bulk scan. Fix, per the user: decentralized
      countries are excluded from the Watchlist entirely — watching one is
      meaningless since you don't meaningfully interact with them — which
      makes the displayed list and the bulk actions agree by construction.
      `NOT = { is_country_type = decentralized }` added to the neighbour /
      rival / Great Power row checks, a new
      `watchlist_is_watchable_check_sgui` for the previously-unfiltered
      "Add a Country" list, every bulk action limit, and the game-start
      population.
      **Also fixed along the way:** every `debug_log` in this mod used
      `[THIS.GetNameNoFormatting]`, which is not valid — vanilla always
      writes `[THIS.GetCountry.GetNameNoFormatting]` (13 occurrences, zero
      of the bare form). All instrumentation had been silently rendering
      as "Data error in loc string" instead of data, which is a large part
      of why this took so many rounds: the diagnostics were blind and
      diagnosis fell back to inferring from screenshots.
      **Note:** an existing save may still carry `watched_via_*` flags on
      decentralized countries from an earlier campaign-start population;
      they'll show on the Watched tab until cleared with Deselect All.
      **Temporary diagnostics removed 2026-09-07** (probe buttons, probe
      SGUIs, their loc keys, and the SNW_BULK taps) now that the selector
      is confirmed. The working mechanism — `is_player` + `save_scope_as`
      for the player, and the decentralized exclusion — is pinned in
      `tools/validate_syntax.py`'s KNOWN_GOOD list so it can't be
      refactored away silently.
- [x] **Watched-tab provenance tags — BUILT 2026-09-07, not yet seen
      in-game.** Per the original v1 spec ("small tags showing which
      category(ies) currently apply, e.g. 'Prussia — Great Power,
      Neighbor'") — this part was never actually built in the original
      2026-09-06 pass. Added originally to explain the per-flag
      Deselect All behavior above before that was simplified away; kept
      regardless since a Watched-tab row checked for more than one
      reason is still useful to see at a glance. Up to 4 small
      abbreviation tags (GP/NB/RV/MA, full name on hover) next to each
      Watched-tab row, driven by 3 new flag-only checks
      (`watchlist_is_flagged_great_power_check_sgui`/
      `_neighbor_check_sgui`/`_rival_check_sgui`, `watchlist_sgui.txt` --
      distinct from the live adjacency/rivalry checks used for section
      filtering, since the tag should reflect what's actually recorded,
      not current live status).
- [~] **"Add a Country" — deliberately still unfiltered; a real search
      box was investigated and found genuinely blocked, not just
      unbuilt.** Vanilla's own country search (`diplomatic_overview.gui`)
      turns out to be backed by a `SearchBar` C++ datacontext object with
      no equivalent accessor on `MessageSettingsWindow`, and no
      dynamic-text substring/contains function exists anywhere in
      vanilla to filter on typed text another way — see
      [docs/engine-notes.md § No generic substring-search filter available for a custom country list](../engine-notes.md).
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
      **Real bug found live 2026-09-07, fixed same day (confirmed by the
      user's screenshot — garbled, overlapping header and row text on
      the Neighbors tab):** the 4 continent flowcontainers were direct
      siblings of the outer `container` widget, same as every other
      top-level section in this file — that only ever worked before
      because every other section here is mutually exclusive (`visible`
      never true for two siblings at once); `container` does NOT
      auto-stack children that are simultaneously visible, and these 4
      ARE all visible together by design, so they rendered on top of
      each other instead of stacking. Fixed by wrapping all 4 in one
      outer `flowcontainer` (`direction = vertical`), which does the
      stacking — same technique already used throughout this file for a
      single section's own rows, just one level higher this time.
      **Not yet re-confirmed live.**
- [ ] **v2 / stretch, only if v1 proves too broad in practice** —
      restrict the manual-add search list to countries within the
      player's declared strategic interest regions
      (`any_scope_interest_marker` from country scope, per the user's
      "likely only surface countries in your strategic interest regions"
      idea) rather than every country in the world. Explicitly deferred —
      the user flagged this as the part most likely to be over-engineering
      if done too early.

- [x] **On-Action Interception / Relational Scope Filtering / Targeted
      Alerts — v1 BUILT 2026-09-07, CONFIRMED WORKING 2026-09-08** (v0.33)
      via a live session: unrelated plays (Bali, Sulu) correctly stayed
      quiet, and a play where a Watchlist country was a genuine backer
      (Kathiri, via Great Britain as overlord) correctly elevated — see
      the "CRITICAL BUG"/"FIXED" writeup further down for the two real
      bugs this took to get right. Scoped
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
      [03_smart_notifications_relational_notifications.txt](../../smart_notifications/common/on_actions/03_smart_notifications_relational_notifications.txt)
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
      **CRITICAL BUG found 2026-09-08 via the user's second real
      playtest, likely the single biggest source of remaining spam,
      diagnostic shipped, fix not yet built.** The user reported "super
      painful" toasts for a Two Sicilies internal revolution and a Rwanda
      internal revolution — countries with zero connection to the
      player's watchlist (Great Britain, Spain, United Netherlands,
      Portugal). The `SNW_FILTER|...|involved` log lines proved why: for
      BOTH unrelated plays, Great Britain (and for one of them, Portugal)
      showed up as `watched=yes` in the `every_scope_play_involved`
      breakdown despite having nothing to do with either country's
      internal politics. `any_scope_play_involved`/`every_scope_play_involved`
      is documented as "Iterate through all involved in a: diplomatic
      play" — but "involved" evidently means something much broader than
      "on a committed side": the game's own `triggers.log` documents a
      real distinction between `is_diplomatic_play_committed_participant`
      and `is_diplomatic_play_undecided_participant`, strongly suggesting
      "involved" includes eligible-but-uncommitted potential interveners
      too (plausibly every Great Power, everywhere, for every play, since
      Great Powers are near-universally eligible to intervene). If true,
      this means watchlist elevation has been firing for **nearly every
      diplomatic play in the world**, not just ones genuinely involving a
      watched country — as long as the player has 2+ Great Powers
      watched (very likely for most players), almost nothing ever gets
      quieted. This would also fully explain the "random country starting
      annex on a random country" complaint (same on_diplo_play_start
      hook, same bug) — no separate root cause needed there. Does NOT
      explain "random country improving relations" (a different,
      already-tracked issue — see the `diplomatic_action_notification`
      item below).
      **CORRECTED same day** — the "duplicate join-side notification"
      report was NOT the harmless toast-then-feed-row rendering first
      guessed at (that guess was based on an incomplete grep of only part
      of the log). The user pushed back, correctly: re-checking the FULL
      log showed `on_diplo_play_join_side` fired **13 times, identically**
      (same actor=Cambodia/target=Nepal/recipient, same second) for one
      real event — a genuine repeat-invocation bug, not a rendering
      artifact. **Fixed same day, all 4 events (not just join_side, since
      the same on_action-repeats-itself pattern likely affects all of
      them):** a same-play dedup guard using a confirmed-real vanilla
      pattern (`set_variable = { name = X value = yes days = N }`, the
      exact mechanic behind e.g. `ai_expedition_cooldown` in
      `common/decisions/*_expedition_decision.txt`) — a `days = 1` flag
      set on root (the diplomatic play, which persists across the repeat
      invocations) suppresses every firing after the first one each day.
      Known, accepted tradeoff: two genuinely different real events for
      the same diplomatic play on the same calendar day would also
      collapse into one notification — far preferable to 13x spam. Not
      yet confirmed in-game (needs a restart + a fresh join-side/start/
      war-start/subject-released event to verify the guard actually
      suppresses the repeats without swallowing the real notification
      too).
      **Diagnostic shipped, not yet fixed:** added two more targeted
      checks inside all 3 events' existing `every_scope_play_involved`
      loop — `is_diplomatic_play_committed_participant` (global, "is this
      country committed to ANY play") and `is_diplomatic_play_participant_with
      = scope:actor` (pairwise, "is this country a committed participant
      in the SAME play as the actor" — the more promising one, since it's
      actually scoped to this specific play rather than any play
      anywhere). **User's own read, 2026-09-08:** "involved" is broad by
      design — it likely just means a country *can* participate in the
      play (probably gated by having sufficiently high interest in the
      region/parties), not that it has. Exactly matched what the data
      showed next.
      **FIXED same day, confirmed against 2 more real revolutions (Bali,
      Sulu).** Both candidate replacements got tested with real log data
      before either was trusted: `is_diplomatic_play_committed_participant`
      turned out to ALSO be wrong — it's a GLOBAL check ("committed to ANY
      play right now"), so Great Britain/Netherlands still false-positived
      by being committed to some unrelated play elsewhere in the world at
      the same time. `is_diplomatic_play_participant_with = scope:actor`
      (pairwise, same-play-scoped) proved correct both times: only the
      real actor/target ever showed `participant_with_actor=yes`, every
      Great Power correctly showed `no`. The elevation check in
      [03_smart_notifications_relational_notifications.txt](../../smart_notifications/common/on_actions/03_smart_notifications_relational_notifications.txt)
      now reads `any_scope_play_involved = { is_diplomatic_play_participant_with
      = scope:actor  smart_notifications_is_watched = yes }` — ANDed, so
      only a watched country that's a genuine committed participant of
      THIS specific play elevates it. Applied to all 4 events (start,
      join_side, war_start, subject_released) for consistency; only
      start/join_side/war_start have real confirming data so far.
      **Same session also fixed a second, independently-confirmed bug:**
      the user caught that my first "duplicate join-side notification =
      harmless toast/feed rendering" theory was wrong (based on an
      incomplete log excerpt) — the full log showed
      `on_diplo_play_join_side` firing 13 times identically for one real
      event. Fixed with a `days=1` same-play dedup guard (confirmed-real
      vanilla `set_variable`-with-expiry pattern) on all 4 events.
      **Elevation fix CONFIRMED WORKING 2026-09-08** via a fresh session
      after restart: a Bali revolution and a Sulu revolution both
      correctly stayed quiet (no Watchlist country genuinely involved), a
      Kathiri revolution correctly elevated (Great Britain is Kathiri's
      overlord — a real, legitimate case, not the old false-positive
      bug), and multiple war-starts elevated/quieted correctly depending
      on whether Portugal or a Watchlist country was the actual
      combatant. **Dedup guard not yet stress-tested** — 0
      `DUPLICATE_SUPPRESSED` lines appeared this session, meaning the
      13x-repeat scenario didn't recur to actually exercise the guard;
      still believed correct (the mechanism is standard, confirmed-real
      vanilla usage) but wants a session where it visibly fires before
      fully closing this out.
      **CONFIRMED by the user 2026-09-08, fix shipped same day, not yet
      re-tested.** A war starting that involves the player reliably
      produces the exact same full-screen popup twice in a row. Checked
      across every rotated debug log for the confirmed matching event
      (`actor=Ovambo|target=Portugal|ELEVATED`, `debug.1.log`): still only
      ONE `SNW_FILTER` decision line, no `DUPLICATE_SUPPRESSED` nearby —
      our own script genuinely only calls `post_notification` once, ruled
      out as the source. Also confirmed vanilla's original
      `diplo_play_war_start_notification` really is muted (`none`), and
      no other message key anywhere shares `popup_name = war_started`
      besides that muted key and our own `smart_notifications_diplo_play_war_start_watched`.
      **Found and fixed:** the muted vanilla key was the ONLY muted key
      in the entire file still carrying leftover `popup_name`/
      `on_created_soundeffect` properties (confirmed via a full scan) —
      every other muted key cleanly has just `notification_type`/`color`.
      Stripped both from it. Leading hypothesis: `popup_name` gets
      processed at some layer independent of `notification_type`'s
      toast/feed/popup gating, so the muted key's own reference was still
      triggering a phantom popup render alongside our replacement's.
      **Needs the user to see another war start involving them to
      confirm this actually fixed it** — a restart is required first
      (script changes need a fresh session).
      **Second report, same day.** The user saw what looked like a toast
      for "Ottoman Empire sides with Great Qing" (a play with no
      watchlist connection) and flagged it as unexpected. The log is
      unambiguous: `SNW_FILTER|join_side|actor=Ottoman
      Empire|target=Great Qing|recipient=Russia|QUIET`, and neither
      country showed watched — the filtering decision was correct, and
      the message key it posted (`smart_notifications_diplo_play_join_side_quiet`)
      is confirmed `notification_type = feed` in
      [00_messages.txt](../../smart_notifications/common/messages/00_messages.txt), not toast. Also
      confirmed the dedup guard held here: dozens of repeat on_action
      invocations, only ONE decision line.
      **My first theory ("Vic3 shows a brief toast-shaped card for any
      feed notification too") was directly rejected by the user
      2026-09-08** — they're confident this really rendered like a toast,
      not a feed entry. Since script has no visibility into how a
      notification actually renders on screen, and this group's name has
      never changed since creation (confirmed via `git log -p` across
      every commit — ruling out a stale override surviving under an old
      name), the leading remaining explanation is a **manual/accidental
      Message Settings override** on this specific row — the user has
      been actively poking around that exact screen all session, and a
      player override persists independently of what the file says until
      reset. Fastest check, no reload needed: open Message Settings and
      look at "Diplomatic Play Join Side, Ambient (Smart Notifications)"
      directly. If it already reads Feed, this explanation is wrong too
      and the mystery is still open (script confirms it posted the right
      key at the right tier — nothing else queryable from our side).
      Added a belt-and-suspenders `posted_key=<literal key name>` field
      to every `SNW_FILTER` decision line across all 4 diplo-play events
      and the new diplomatic_action filter, so which exact key posted is
      never in doubt from the log, even though it can't resolve a
      rendering-vs-override question on its own.
      **Third report, same day, second confirmed correct-but-toast-feeling
      instance:** "German Empire sides with Kaarta" — logged
      `posted_key=smart_notifications_diplo_play_join_side_quiet|...|QUIET`,
      all 4 watchlist countries confirmed `participant_with_actor=no`.
      Both incidents so far are `join_side` events. **My second theory
      ("a native activity-ticker card tied to having the play's detail
      panel open") was also directly rejected by the user** — they opened
      the panel BY CLICKING the notification itself, meaning it rendered
      prominently while the panel was still closed. Two hypotheses down;
      script genuinely cannot see how something renders, so the
      Message-Settings-override check above (still unconfirmed by the
      user) remains the only concrete next step — no further script-side
      diagnostic is possible without new information from an actual
      in-game observation (e.g. does the card auto-dismiss like a toast,
      or sit until dismissed like a feed entry?).

## First real playtest of the new alerts — 2026-09-08, fixes applied

The user's first live test of the agitator and taxation deficit alerts
surfaced real bugs, plus a design-clarification round on the law
commitment alert before it was ever seen live. All fixed same day:

1. **Every alert was missing its `_hint` loc key.** Confirmed live via
   screenshot: the alert tooltip showed the raw key name
   (`alert_smart_notifications_taxation_deficit_alert_hint`) as literal
   text instead of hiding the line — vanilla's own alert tooltip template
   always tries to render a hint. Fixed for all four alerts (amendment,
   agitator, taxation deficit, law commitment); `_desc` turns out to be
   genuinely optional (vanilla's own `low_market_access_alert` skips it),
   but `_hint` isn't.
2. **Country-scoped alerts were also missing `_action`** (the "Click to
   open..." link's own text) — confirmed live via the agitator alert's
   screenshot showing the raw key there too. The taxation deficit alert
   already had one (copied from vanilla's state-scoped alerts), but that
   same convention needed applying to amendment/agitator/law-commitment
   too. Fixed for all four.
3. **Taxation deficit alert never aggregated across multiple states** (the
   "many states in deficit, like a big colonial empire" case the user
   asked about) despite having `alert_group` set. Root cause: an
   `alert_group` on the alert_type only turns grouping ON in the engine —
   the actual collapsed header ("X states...", with a count) needs its
   OWN separate `ag_<group>_name`/`_desc`/`_tooltip` loc keys, confirmed
   via vanilla's own `ag_low_sol_in_state_name`/
   `ag_expensive_government_goods_name` (same loc file). Missing these,
   the game apparently falls back to listing every instance as a flat
   individual row — which is also the leading explanation for the user's
   separately-reported **font-size inconsistency** between our alerts
   (that fallback path likely isn't styled for standalone display). Added
   the missing `ag_smart_notifications_taxation_deficit_states_*` keys;
   this is now the answer to "is aggregation possible" — yes, this exact
   mechanism, already used, just missing its loc half. **Not yet
   re-confirmed live** whether this also fixed the font-size symptom —
   worth another look once the user has 2+ states in deficit again.
4. **Alert-list "jump to top, an entry seems to vanish" glitch** — reported
   once, not yet reproduced or diagnosed. Nothing found yet linking this
   to our alerts specifically (could be vanilla, could be ours) — needs a
   repro and/or `error.log`/`game.log` lines from the user before this can
   be investigated further.
5. **No cross-alert-type category ("Smart Notifications Mod" folder)
   exists in the engine.** Checked: `alert_group` only aggregates multiple
   INSTANCES of the SAME alert_type (e.g. many states each triggering the
   taxation deficit alert) — it does not merge DIFFERENT alert_types
   (ours or vanilla's) under one shared parent label the way "Low Standard
   of Living" and "Expensive Government Goods" are still two separate
   groups, not one. No `category` field or equivalent found anywhere in
   `common/alert_types/00_alert_types.txt`. Building this would mean
   modifying `gui/important_actions_list.gui` itself (the file that
   actually renders the alert list) — a bigger, GUI-level undertaking in
   the same risk class as Phase 3's dropped country-panel star icon.
   **Not started** — worth doing only if the user still wants it once told
   the real cost; the "(SN) " prefix already gives at-a-glance
   recognizability without this.
6. **Law commitment: the checkbox was never visible at all.** The user
   correctly identified this only lived in the (usually-empty,
   nothing-selected-yet) detail panel; per their explicit ask, added a
   SECOND copy directly on each row of the law list itself
   (`gui/politics_panel_change_law.gui`, via a real, already-existing
   empty `block "spacing_between_button_and_approval_info"` slot vanilla
   declares inside `enactable_generic_law2` for exactly this kind of
   per-row addition — found by reading that type's full definition rather
   than guessing, and confirmed it needs no changes to its own much
   larger host file, `gui/politics_panel_types.gui`). Both copies read/
   write the same underlying `law`-scope flag, so they always agree.
   **Still carries the same unconfirmed `Law.MakeScope` risk as before** —
   now used in two places instead of one, so if it's wrong, expect neither
   checkbox to work. Added a temporary `SNW_LAW_NOTIFY` debug_log tap to
   the toggle SGUI specifically to tell "click did nothing because
   MakeScope failed" apart from "click worked but the read-back is wrong"
   — check `debug.log` for it on the next test.

## Second playtest round — 2026-09-08, same day

1. **Taxation deficit still not aggregating — REAL second bug found and
   fixed.** The `ag_*` loc added in the first round wasn't the whole
   story: every `alert_group` value must ALSO be registered in
   `common/alert_groups/` (confirmed real — vanilla's own
   `00_alert_groups.txt` lists every one of its own alert_types' group
   names as an empty `{}` entry). Ours was referenced from the alert_type
   but never declared there, so the engine silently never grouped it
   at all — the `ag_*` loc was necessary but not sufficient. Fixed:
   [common/alert_groups/01_smart_notifications_alert_groups.txt](../../smart_notifications/common/alert_groups/01_smart_notifications_alert_groups.txt).
   **Not yet re-confirmed live**, but this is now believed to be the
   actual, complete fix (both pieces the grouping mechanism needs are in
   place). Also worth re-checking whether this incidentally fixes the
   font-size inconsistency reported the same round, per the earlier
   hypothesis that the missing-group fallback rendering was the cause.
2. **Alert list not scrollable by mouse wheel for the first 20-30s after
   opening — reported, not diagnosed.** Checked whether any of our
   alerts' `valid` triggers could plausibly be expensive enough to cause
   a UI hitch: none are — agitator's `any_character_in_exile_pool` is a
   small global list, taxation deficit's checks are cheap per-state
   comparisons, law commitment's `any_law` only runs the expensive
   `enactment_chance_for_law` calc for laws that already pass a cheap
   `has_variable` filter first. No obvious mechanism found tying this to
   our mod specifically — most likely a general engine/UI thing (session
   startup settling) rather than something we caused, but not ruled out.
   **Needs a repro and/or `error.log`/`game.log` lines** before this can
   be investigated further.
3. **No cross-alert-type "Smart Notifications Mod" category exists in the
   engine, checked and confirmed.** `alert_group` only aggregates
   multiple INSTANCES of the SAME alert_type (e.g. many states each
   triggering the taxation deficit alert) — it does not merge DIFFERENT
   alert_types (ours or vanilla's) under one shared parent label; "Low
   Standard of Living" and "Expensive Government Goods" are two separate
   groups in vanilla, not one. No `category` field or equivalent exists
   anywhere in `common/alert_types/00_alert_types.txt` or
   `common/alert_groups/`. Building this would mean modifying
   `gui/important_actions_list.gui` itself (the file that actually
   renders the list) — a bigger, GUI-level undertaking in the same risk
   class as Phase 3's dropped country-panel star icon. **Not started** —
   worth doing only if the user still wants it once told the real cost.
4. **Law commitment checkbox: confirmed NOT WORKING live, and the design
   itself is now in real doubt.** The user tested both a law with
   success > stall and one with stall > success — clicking did nothing
   either way. Investigated further and found a second, independent
   negative signal beyond the already-flagged missing `Law.MakeScope`
   precedent: an exhaustive grep of every `scope = ` line across EVERY
   vanilla `common/scripted_guis/*.txt` file shows only
   `country`/`state`/`character`/`political_movement` ever used — `law`
   has zero precedent as a scripted_gui scope anywhere in the base game.
   Combined with zero examples of `Law.MakeScope` (or any
   `<type>.MakeScope` outside those same four types) anywhere in
   `gui/`, the working theory has flipped from "unconfirmed but
   plausible" (how it was shipped) to "likely genuinely unsupported by
   the engine" — scripted GUIs may simply be restricted to those four
   scope kinds, with no way to root one at an arbitrary law. **This is a
   real design problem, not just an unconfirmed detail**, since the
   feature's whole point (flag a SPECIFIC law, not just "whatever I'm
   enacting") depends on identifying that specific law from a scripted
   GUI call, and there's no confirmed way to do that yet. Investigated
   and rejected two alternate approaches before stopping to reassess:
   - Passing the law's identity through `GuiScope.AddScope` instead of
     `SetRoot` — checked every vanilla `AddScope(...)` call in `gui/`;
     all of them pass `MakeScopeBool`/`MakeScopeValue` (a plain bool or
     number), never a scope reference to another object. No evidence
     this can carry "which law" at all.
   - One scripted_gui PER LAW TYPE (country-scoped, so definitely
     supported), picked dynamically via
     `GetScriptedGui(Concatenate('...', Law.GetLawType.GetName))` — the
     `Concatenate` half is confirmed real and used for exactly this kind
     of dynamic-key purpose elsewhere in this exact vanilla file
     (`GetVariableSystem.Toggle(Concatenate(Amendment.GetName,
     '_amendment_effects'))`, `gui/politics_panel_types.gui`), but that
     one is a pure client-side UI toggle, NOT the same variable system
     script triggers can read — so it doesn't solve the actual problem
     of a SCRIPT-visible flag either way. Separately, this path would
     also need ~126 near-identical generated scripted_gui blocks (one
     per real `common/laws/*.txt` law_type) since a script effect can't
     build a variable NAME dynamically — a maintenance and DLC-mismatch
     burden judged not worth it without confirming the dynamic
     `GetScriptedGui` key lookup even works first.
   Removed the second checkbox copy (the per-row one added the same
   session) per the user's own placement feedback below regardless of
   this open question, since it was mispositioned anyway. Left the
   detail-panel checkbox and its `SNW_LAW_NOTIFY` debug tap in place as
   a live diagnostic — **next step is checking `debug.log` for that tap**
   to confirm whether `Law.MakeScope` fails outright (no log line) or
   something else is wrong (log line present, still doesn't toggle),
   before deciding between: (a) descoping back to the original
   "notify about current enactment" design (fully confirmed to work,
   country-scoped, no per-law identification needed, but doesn't cover
   flagging a law before starting to enact it), or (b) investing in the
   bigger per-law-type generator approach above, accepting its own
   unconfirmed piece and DLC-maintenance cost.
5. **Checkbox positioning fixed per feedback**: the per-row copy sat at
   the far LEFT of each law row (a leftover misreading of where
   `spacing_between_button_and_approval_info` actually sits in
   `gui/politics_panel_types.gui` — it's BEFORE the law button, not
   between it and the approval-info icon on the right as its name
   suggested) — user found it "out of position." Removed; the
   detail-panel copy (right-side, for whichever law is currently chosen)
   is now the only one, matching what the user asked for.
6. **Label text tightened**: "Notify Me" → "Alert Me When I Can Pass
   This", tooltip similarly reworded to name the actual condition
   (support vs. pushback) rather than a vague "chance becomes good."

## Third playtest round — 2026-09-08, same day

1. **Confirmed working**: taxation deficit aggregation (both the
   `ag_*` loc and the `common/alert_groups/` registration together were
   the complete fix).
2. **Checked, no fix needed**: only the taxation deficit alert uses
   `alert_group` — amendment/agitator/law-commitment fire at most once
   per country, never needed grouping. All four alerts already have
   complete `_name`/`_desc`/`_hint`/`_action`/`_setting_name` loc from the
   prior round.
3. **Law commitment checkbox — ROOT CAUSE FOUND (not a guess), and FIXED
   same day.** Checked `error.log` directly (per the user's ask — Claude
   checks logs itself now, not the user) rather than continuing to guess.
   Found, verbatim, for every law type tested: `has_variable trigger
   [ This scope doesn't support variables. Scope: Law <name> (<id>) ]`.
   This is genuinely good news buried in a bug report: `Law.MakeScope`
   and the `.Execute()`/`.IsValid()` dispatch through it were ALREADY
   working correctly — the error message itself named the exact law
   clicked each time, proving the scripted GUI plumbing was never the
   problem. The actual issue is narrower and now fully confirmed: `law`
   scope objects cannot hold variables at all, engine-wide, for any law.
   **Fix, built and shipped:** kept the checkbox rooted at `Law.MakeScope`
   (proven to work) but moved the flag itself onto the COUNTRY (`ROOT`,
   fully proven throughout this whole mod), using one static,
   per-law-type variable name (`smart_notifications_wanted_law_<type>`)
   matched via `THIS.type = law_type:X` comparisons. Since effects can't
   build a variable name dynamically (`Concatenate` is GUI/loc-only, not
   available in script effects), this needs one branch per real law
   type — mechanically generated (not hand-typed) from every law_type key
   in the installed game's own `common/laws/*.txt` (126 at generation
   time), covering:
   - [common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt](../../smart_notifications/common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt)
     — new shared scripted_trigger, `smart_notifications_law_matches_wanted_flag`,
     the single source of truth for the law_type↔variable_name mapping,
     reused by both the check_sgui's `is_valid` and the alert's `valid`
     (avoids tripling 126 branches across three places).
   - [common/scripted_guis/smart_notifications_law_notify_sgui.txt](../../smart_notifications/common/scripted_guis/smart_notifications_law_notify_sgui.txt)
     — the toggle SGUI's effect, one `if`/`else_if` branch per law type
     (needs its own copy since it performs an action, not just a check).
   - [common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt)'s
     `smart_notifications_law_commitment_alert` — `valid` now calls the
     shared scripted_trigger instead of a plain `has_variable` on `law`
     scope.
   **On future DLC/patches adding new law types** (the user's explicit
   ask): this list is regenerable, not hand-maintained — re-extracting
   law_type keys from `common/laws/*.txt` and re-running the same
   generation covers new laws. Until regenerated, a brand-new law type
   simply matches no branch, so its checkbox silently does nothing for
   that one law specifically — it doesn't error, and doesn't affect any
   existing law's entry. Law_type keys themselves are static database
   identifiers (unlike a country's tag, which genuinely can change
   identity mid-campaign per the Phase 3/4 renaming caveat elsewhere in
   this file) — Paradox renaming an EXISTING key in a future patch would
   need the same kind of update any mod referencing vanilla content
   would, not something specific to this design.
   **On performance** (the user's explicit ask): walked through the cost
   of all three pieces before building — the toggle only runs on click
   (irrelevant), the check's `is_valid` runs once per frame while the
   detail panel is open (~126 cheap short-circuiting comparisons, trivial
   next to what the engine already evaluates per frame elsewhere), and
   the alert's `valid` runs on the normal alert refresh cadence, not
   every frame, with `has_variable` false for essentially all 126
   branches in the typical case (few laws flagged at once). Judged not a
   meaningful performance concern; flagging this plainly per the user's
   instruction to skip the feature entirely if it were.
4. **Checkbox label re-tagged and re-cased per the user**: `(SN) Alert me
   when I can pass this` — CLAUDE.md's tagging convention extended to
   cover standalone in-panel UI labels too (previously scoped to
   Message-Settings rows only), and only the leading word plus the
   pronoun "I" are capitalized, not every word. See
   [docs/engine-notes.md § Tagging mod-created notifications](../engine-notes.md)
   for the extension writeup.
   **Not yet re-confirmed live** — needs another test: does the checkbox
   now actually toggle, and does the alert fire for a flagged-but-not-yet-
   enacting law.

## Fourth playtest round — 2026-09-08, same day

**Law commitment checkbox still not working — SECOND real bug found and
fixed, same root-cause family as the first.** The user reported the click
still did nothing after the country-scope fix; checked `error.log`
myself again (per the user's earlier ask) rather than asking them to.
Found the EXACT same error as before —
`has_variable trigger [ This scope doesn't support variables. Scope: Law
Workers' Protections (1809) ]` — but now pointing at
`common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt:153`
instead of the sgui file. Root cause: that trigger used `ROOT` to reach
the country, which is only correct in ONE of its two call sites. From
`any_law` (the alert's `valid`), ROOT correctly stays the original
country. But called DIRECTLY from
`smart_notifications_law_notify_check_sgui` (`scope = law`), ROOT at that
point IS the law — the SGUI's own root — not a country at all, so the
`has_variable` check landed right back on `law` scope, exactly the thing
the whole redesign was meant to avoid.
**Fixed** by using `THIS.owner` instead of `ROOT` in both
[common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt](../../smart_notifications/common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt)
and
[common/scripted_guis/smart_notifications_law_notify_sgui.txt](../../smart_notifications/common/scripted_guis/smart_notifications_law_notify_sgui.txt) —
`owner` is confirmed real for `law` scope (event_targets.log: "Scope to
the owner country of object", Input Scopes includes `law`), and unlike
`ROOT`, `THIS` (the law being evaluated) is consistent across both
calling shapes: bound to the iterated law inside `any_law`, and bound to
the SGUI's own root when called directly. Regenerated both files from
the same Python generator used for the first build (not hand-patched),
so the fix is consistent across all 126 branches rather than a
one-off edit. **Not yet re-confirmed live.**

## Pre-emptive audit before the next test — 2026-09-08, same day

Per the user's ask (repeated test-fix-test cycles were "getting
painful") — rather than ship the `THIS.owner` fix and wait for another
round-trip, re-audited the rest of this feature by hand for the exact
same "which scope is this actually evaluated in" mistake that had
already hit twice, and improved logging so one test run should now be
conclusive either way.

- **Third scope bug found and fixed BEFORE testing, not after.**
  `smart_notifications_law_commitment_alert`'s `valid` called
  `enactment_chance_for_law` as a bare trigger directly inside `any_law`
  — but that trigger's own docs say `Supported Scopes: country`, while
  `any_law` rebinds the current scope to the iterated LAW. Same class of
  mistake as the two already-confirmed bugs, just not live-tested yet.
  Fixed using the exact pattern already proven in
  [common/on_actions/02_smart_notifications_truce_tracker.txt](../../smart_notifications/common/on_actions/02_smart_notifications_truce_tracker.txt)
  (`save_scope_as` to carry a reference across a `root = { ... }` switch)
  rather than guessing a new mechanism: `THIS.type = { save_scope_as =
  ... }` while still law-scoped, then `root = { enactment_chance_for_law
  = { target = scope:... value > 0.5 } }` from country scope.
- **Toggle SGUI's debug tap fixed and extended.** The original tap
  (`[THIS.GetCountry.GetNameNoFormatting]`) had silently errored
  ("Data error in loc string") every single time since it was first
  added, for reasons never isolated — dropped `.GetCountry` entirely
  (kept only the already-safe `THIS.GetNameNoFormatting`) and added a
  SECOND tap reading back through the same shared
  `smart_notifications_law_matches_wanted_flag` trigger the checkbox and
  alert both use, reporting the FINAL state (`FLAGGED`/`UNFLAGGED`) right
  after the toggle runs — so one click's `debug.log` output alone now
  confirms whether the write actually stuck, not just that the effect
  ran.
- **New temporary diagnostic for the alert side specifically**, since
  that path has never been live-tested at all (only the checkbox has):
  `common/on_actions/08_smart_notifications_law_commitment_probe.txt` (since deleted, commit b7676e5),
  an `on_monthly_pulse_country` tap (same real hook the truce tracker
  uses) that logs, for every currently-flagged law, which of the
  remaining two gates (`can_be_enacted`, the 0.5 threshold) it passes or
  fails — `SNW_LAW_ALERT|probe|...` in `debug.log`. This means if the
  alert never visibly appears next test, the log says exactly why
  (not flagged reaching this law at all / can't currently be enacted /
  under the threshold) without needing yet another round of added
  instrumentation after the fact. **Delete once the alert is confirmed
  working live** (noted in the file's own header too).
- Re-audited `common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt`
  and the alert's other conditions (`can_be_enacted`,
  `smart_notifications_law_matches_wanted_flag`) for the same mistake —
  both are documented `law`-scope triggers and correctly stay evaluated
  with `THIS` = law throughout; no further issues found by this pass.

## Fifth playtest round — 2026-09-08, same day

**Toggle confirmed working.** The checkbox now correctly flags/unflags a
specific law. Two NEW real bugs found, both from the pre-emptive fix
above — the audit caught the right category of problem (scope
confusion) but the specific fix chosen was itself wrong in a different
way, confirmed live and by `error.log`:

1. **The `save_scope_as`/`root = {}` fix for the alert's
   `enactment_chance_for_law` never actually worked** — the user flagged
   a law with success clearly greater than stall and never saw the
   alert. `error.log`: `Event target
   'smart_notifications_law_commitment_candidate' is used but is never
   set. Setting it in an unused scripted trigger or effect does not
   count.` Root cause: `save_scope_as` is an EFFECT, and an alert's
   `valid` block is a pure TRIGGER context — effects cannot run inside a
   trigger at all, so the save silently never happened and the `target`
   reference was permanently undefined, making the whole condition
   always false. **Real fix**: `prev` — a genuine trigger-side scope
   link ("the previous scope"), confirmed real via a live vanilla
   example doing the exact same thing
   (`common/achievements/ip2_pivot_of_empire_achievements.txt`:
   `harvest_condition_intensity = { target = prev.owner value > 5 }`).
   Needs no effect: enter `THIS.owner = { ... }` (a plain scope
   transition, valid in triggers) and reference `prev.type` from inside
   it to mean "the law we just came from"'s type. Rewritten in
   [common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt).
2. **The diagnostic probe itself had a bug**, caught via `error.log`
   before it ever produced a useful line: `Unknown effect any_law at
   common/on_actions/08_smart_notifications_law_commitment_probe.txt:31`.
   `any_law` is trigger-only; the effect-side iterator is a different
   keyword, `every_law` (confirmed: effects.log documents it separately,
   "Iterate through all laws in a country"). Fixed in
   `common/on_actions/08_smart_notifications_law_commitment_probe.txt` (since deleted, commit b7676e5).

**Lesson for this whole feature, now confirmed three times over**:
`any_X`/`every_X` and effect-vs-trigger context are NOT
interchangeable even when they read almost identically — this is now
the single most error-prone corner of this entire mod, more so than
anything from earlier phases. **Not yet re-confirmed live** — needs
another flag on a law with success > stall to confirm the alert now
actually fires; the second flagged law (stall > success, per the user)
remains a good negative-control test once its odds eventually cross
50%.

## Deeper verification pass — 2026-09-08, before asking for a sixth test

Per the user, directly: too many rounds had shipped on plausible-but-
unverified patterns, each one only confirmed wrong by another manual
playtest. Real gap, not a hard limit — there's no way to execute this
game's scripts directly, but `triggers.log`/`effects.log`/real vanilla
examples ARE checkable before shipping, and the two bugs in the previous
round (effect-in-a-trigger, `any_law` vs `every_law`) were exactly the
kind of thing that check would have caught. Before asking for another
test, went back and did that check properly instead of moving on once
something looked plausible:

- **Found a genuine, repeated (3x) vanilla precedent for the exact `prev`
  construction the previous fix relied on**, in the LAWS domain
  specifically:
  `common/laws/00_governance_principles.txt` uses `prev.owner = {
  activate_law = prev.type }` three separate times — enter a law's
  owner, then reference `prev` inside that block to mean the law just
  left. Structurally identical to
  `THIS.owner = { enactment_chance_for_law = { target = prev.type ... } }`.
  This is materially stronger confirmation than the single achievement-file
  example cited when the fix first shipped — a repeated, in-domain vanilla
  idiom rather than one example from an unrelated system.
- **Removed the toggle SGUI's debug taps entirely** now that the toggle
  itself is confirmed working live — both lines errored
  ("Data error in loc string") on every single click for reasons never
  isolated, and leaving them in place going forward would only add
  guaranteed noise to future `debug.log` checks for no remaining
  diagnostic value. Cleaner logs for whatever gets debugged next.
- Re-confirmed every other piece of the chain (the shared scripted
  trigger, `can_be_enacted`, `smart_notifications_law_matches_wanted_flag`)
  against triggers.log's "Supported Scopes" for each, since the toggle's
  own success already empirically proves `THIS.type`/`THIS.owner` resolve
  correctly for real. The one part that had NOT been touched by that
  empirical proof was `enactment_chance_for_law` specifically (a
  country-scope trigger reached via a different path than the toggle
  uses) — now the piece with the strongest independent confirmation of
  anything in this feature.

**Confidence level, stated plainly**: high, based on a real matching
vanilla idiom rather than a first-principles guess, but not a
certainty — there is no way to execute-test this without the game
itself. If this specific line is still wrong, that reflects a genuine
limit on what's checkable without running the game, not a repeat of the
same shortcut.

## Sixth playtest round — 2026-09-08, same day

**The `prev.type` fix works — the probe confirms it, cleanly, with no
errors.** `debug.log` showed, for a flagged law:
`SNW_LAW_ALERT|probe|considering` → `can_be_enacted=yes` →
`chance_over_threshold=no` — no scope errors, meaning the whole
`THIS.owner = { enactment_chance_for_law = { target = prev.type ... } }`
chain evaluated successfully this time. Real progress, not another dead
end.

**Two separate findings from this round, one a real bug (fixed), one
likely a metric mismatch (not a bug, needs a decision):**

1. **Checkbox silently did nothing on "Merchant Navy" — REAL BUG,
   FOUND AND FIXED.** Root cause: the original law_type extraction used
   `grep -E "^law_"` against every `common/laws/*.txt` file — but ALL 24
   of those files carry a UTF-8 BOM, and a BOM's bytes sit before the
   very first line's content, breaking the `^` anchor for exactly the
   FIRST law_type entry in each file. `law_merchant_navy` is literally
   line 1 of `00_navy_model.txt`. Re-extracted BOM-aware (Python,
   `encoding='utf-8-sig'`) and found **12 missing law types total**, not
   just this one: `law_guild_system`, `law_hereditary_bureaucrats`,
   `law_merchant_navy`, `law_no_colonial_affairs`, `law_no_health_system`,
   `law_no_home_affairs`, `law_no_migration_controls`, `law_no_police`,
   `law_no_schools`, `law_no_social_security`, `law_peasant_levies`,
   `law_serfdom` — every one of them the first entry in its own file.
   Regenerated
   [common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt](../../smart_notifications/common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt)
   and
   [common/scripted_guis/smart_notifications_law_notify_sgui.txt](../../smart_notifications/common/scripted_guis/smart_notifications_law_notify_sgui.txt)
   from the corrected 138-law list. This also directly answers the
   user's earlier question about future DLC laws: the mechanism already
   degrades gracefully (an unmatched law's checkbox just does nothing,
   confirmed by this exact incident) — the fix here was to correct which
   laws were IN the list today, not the degrade-gracefully design itself,
   which held up as intended.
2. **"No Worker's Rights" flagged with success > stall, alert never
   fired — likely NOT a bug, a metric mismatch worth a decision.** The
   probe's own log is unambiguous: `can_be_enacted=yes` but
   `chance_over_threshold=no`. The user's "success > stall" comparison is
   the law list's per-CHECKPOINT outcome breakdown (Success/Advance/
   Debate/Stall — the next roll only); `enactment_chance_for_law` is
   documented as "the enactment success chance," which reads more like an
   overall/compounded probability across the whole (possibly
   multi-checkpoint) enactment process, not the same figure. A law can
   clear one checkpoint's odds comfortably while its OVERALL chance of
   ultimately becoming active is still under 50%, especially early in a
   multi-phase enactment. Nothing in the log suggests a script error —
   the condition was checked correctly and came back false. **Needs a
   user decision**, not a code fix by default: lower the 0.5 threshold,
   swap to a different trigger if a closer match to the per-checkpoint
   number exists, or confirm this is actually the intended, more
   holistic signal and simply wait longer to see it fire.

**Also answered directly: alert timing.** The alert itself is NOT tied
to the monthly probe — alerts globally re-evaluate every
`ALERTS_FRAMES_BETWEEN_UPDATES` (5) frames, i.e. multiple times per
second, the same as every other alert in the game. Only the TEMPORARY
diagnostic probe
(`common/on_actions/08_smart_notifications_law_commitment_probe.txt` (since deleted, commit b7676e5))
is monthly — that's what needed the wait, not the alert. If the
underlying condition is ever true, the real alert would show up within a
second or two, not a month.

## Alert condition redefined — 2026-09-08, per the user

**Decision made**: "ready to activate" now means the next checkpoint's
Success chance beats its Stall chance — the same comparison the law list
itself displays — not an absolute ">50% overall" threshold. This
directly replaces the flat `enactment_chance_for_law > 0.5` check.

No single trigger does this comparison directly, and there's no
confirmed way to pull either chance out as a raw number for script math —
`enactment_chance_for_law`/`stall_chance_for_law` (both confirmed real,
triggers.log) only support "> literal" comparisons, not comparing to
each other. Worked around this with a threshold-sweep: "success > stall"
is true if and only if some value V exists with success > V and
stall <= V, so testing this across a dense grid (19 steps, every 0.05
from 0.05 to 0.95) approximates the exact comparison to within the
grid's own spacing. The only remaining inaccuracy is the rare case where
both values land in the same 5-point band (e.g. 44% vs 41%), which this
can't distinguish — accepted as a reasonable precision/complexity
tradeoff for a heads-up alert, since every individual comparison is the
same already-confirmed `_for_law` trigger shape repeated at 19 points,
not a new mechanism.

Updated both
[common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt)
(the real condition) and
`common/on_actions/08_smart_notifications_law_commitment_probe.txt` (since deleted, commit b7676e5)
(the temporary diagnostic, now mirroring the exact same check so its
output stays meaningful) to match. **Not yet re-confirmed live.**

**Grid tightened same day, per the user**: the initial 5-point grid (19
steps) was too coarse — success/stall commonly both sit in the 20-30%
range, close enough together that a single 5-point band can contain
both and miss a real "success > stall" case. There was never an actual
reason to keep it coarse (each comparison is cheap, this doesn't run in
a hot per-frame loop, and the number of simultaneously-flagged laws is
normally small), so tightened to a 1-point grid (99 steps, every 0.01
from 0.01 to 0.99) in both files. Same mechanism, just finer.

## CONFIRMED WORKING LIVE 2026-09-08 — the alert actually fires

The user saw "(SN) Law Ready to Enact" appear for real. This closes out
the core mechanism after five real bugs across the session (law-scope
variables not supported, `ROOT` vs `THIS.owner`, effect-in-a-trigger,
`any_law`/`every_law` mixup, and the >50% vs success>stall threshold
question) — the checkbox-to-alert pipeline is now confirmed correct
end-to-end.

**Follow-up requested immediately**: the alert didn't say WHICH law, and
clicking it opened the Laws tab with nothing highlighted, so there was no
way to tell which of the flagged laws (or which group) was actually
ready. Two real asks: name the law/group in the text, and deep-link
directly to it.

**Deep link: checked, not possible.** The real native function for
jumping straight to a specific law's group,
`InformationPanelBar.OpenChangeLaw(Law.GetGroup)`
(`gui/politics_panel_types.gui`, the law list's own row onclick), is a
GUI-only action that takes a live object argument. `alert_types`'
`open_panel`/`open_popup` fields only accept a static `"panel[|tab]"`
string (confirmed via the alert_types header comment and every vanilla
example) — there's no way to parameterize either field with a specific
law/group from script. This is a hard engine limitation, not something
worth spending more time trying to work around; `open_panel =
politics|laws` (the general overview) remains the best available click
target.

**Naming the law/group: built, using a real documented technique.**
`common/scripted_guis/scripted_guis.md`'s own "Using SGUIs to build lists
in loc" section describes exactly this: a scripted GUI's effect can call
`custom_tooltip = "LOC_KEY"` once per matching item, and a loc string
elsewhere renders the built list live via
`[GetScriptedGui('key').ExecuteTooltip(GuiScope.SetRoot(...).End)]` —
evaluated fresh every time the tooltip renders, so there's no staleness
the way a slow monthly-pulse-computed value would have. Added
`smart_notifications_law_commitment_list_sgui`
([common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt)),
which lists every ready law via `[THIS.GetNameNoFormatting]
([THIS.GetGroup.GetName])` entries, embedded into the alert's `_desc`.

**Real refactor along the way**: with a third consumer (this list
builder) needing the identical ~400-line success-vs-stall threshold
sweep as the alert and the probe, factored it into one shared scripted
trigger, `smart_notifications_law_ready_to_enact`
([common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt](../../smart_notifications/common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt)) —
the alert's own `valid` and the probe both got dramatically shorter as a
result, and there's now exactly one place to ever change this logic
again.

**UNCONFIRMED, flagged honestly**: `THIS.GetNameNoFormatting` from a
`law`-scoped `THIS` inside `custom_tooltip` specifically. The toggle
SGUI's own debug_log tap failed with this exact call from law scope
earlier this session ("Data error in loc string", never isolated why) —
`custom_tooltip`'s rendering pipeline may or may not share that same
failure mode; genuinely don't know without testing. **First thing to
check**: does the alert's text show real law/group names, or blank/
garbled text? If the latter, check `error.log` for "Data error in loc
string" pointing at
`smart_notifications_law_commitment_list_entry` — the group name half
(`THIS.GetGroup.GetName`) is more likely to survive even if the law name
half doesn't, since `GetGroup` returns a different, simpler object type.

## Dynamic list still not rendering — real bug, found and fixed

Confirmed live via the user's screenshot: the alert's tooltip showed no
body text at all (just the title and hint, nothing in between) — the
whole `_desc` failed, not a partial/garbled render. `error.log` was
explicit and pointed at the actual cause immediately: `Failed to convert
statement for argument '0' for call 'ExecuteTooltip'` — the
`GuiScope.SetRoot(SCOPE.GetRootScope.MakeScope)` argument itself never
even constructed.

**Root cause: the exact same mistake this project already learned once,
just for a different accessor.** `SCOPE.GetRootScope` is a generic
wrapper that always needs an explicit per-type cast chained onto it
before anything else works — this mod's own
[docs/engine-notes.md](../engine-notes.md) already documents this for
`THIS` vs `SCOPE.sC(...)`, and the taxation deficit alert's own working
loc (`SCOPE.GetRootScope.GetState.GetName`) already demonstrated the
cast pattern for state alerts — but writing this alert's `player_country`
version, the cast was dropped entirely rather than swapped for the
country equivalent. Confirmed by an exhaustive check of every
`SCOPE.GetRootScope.` usage across every vanilla `localization/english/`
file: 100% of them chain `.GetCountry` immediately after, with zero
exceptions, even inside journal-entry contexts where root is already
conceptually a country. **Fixed**: `SCOPE.GetRootScope.GetCountry.MakeScope`.

**Also fixed while in there**: the alert's "Click to open the Open
Politics" wording (visible in the same screenshot) — vanilla's own
`_action` convention is `"<Panel Name> Panel"` (confirmed:
`alert_can_resign_alert_action:0 "Politics Panel"` and every other
vanilla example), never `"Open <Panel Name>"`. Applied `"Politics
Panel"` to all three of this mod's country-scoped alerts (amendment,
agitator, law commitment) for consistency — they'd all shipped with the
same wording mistake, just only this one had a screenshot revealing it.

**Not yet re-confirmed live.**

## Law name still blank — real bug #4, found and fixed

`error.log`: "Promote 'GetScriptedGui' returned nullptr" — the scripted
GUI wasn't found AT ALL, not a rendering/cast problem this time. Root
cause: `smart_notifications_law_commitment_list_sgui` was defined inside
`common/alert_types/01_smart_notifications_alerts.txt` — the only
scripted_gui in this whole mod NOT placed in `common/scripted_guis/`.
The engine only scans that dedicated folder for scripted_gui
definitions. Fixed by moving it, unchanged otherwise, to
[common/scripted_guis/smart_notifications_law_commitment_list_sgui.txt](../../smart_notifications/common/scripted_guis/smart_notifications_law_commitment_list_sgui.txt).
**Not yet re-confirmed live.**

## Alert won't re-fire after dismissal — likely a real engine constraint, not a bug

Reported same session: once the player dismisses (X's) the alert, a
different law becoming ready afterward doesn't bring it back. No
`error.log` evidence of a script fault here. Checked
`common/defines/00_interfaces.txt` for a dismiss-cooldown/mute define —
none exists, meaning this is native, unexposed client-side state, not
something a definable value controls.

**Working theory**: `important_action` dismissal is almost certainly
edge-triggered on the alert's own `valid` going false→true, not
per-list-item — reasonable default for a persistent icon, but a real
mismatch for this alert's design, where ONE alert instance's underlying
condition can stay continuously true (some law is always ready) while
WHICH law changes underneath it. Since there's no `player_law`
script_context (confirmed earlier this session), there's no way to give
each law its own independently-dismissible alert instance.

**Confirmed via the user's own Gemini research** (independently converging
with the `MarkAsHidden`/`UnhideAllImportantActions` finding above, minus
that answer's specific "Morgenröte" case study, which reads as fabricated
— its citations are generic Steam/wiki pages, not the actual mod source
it describes with suspiciously precise line numbers and error text):
dismissal is edge-triggered on the alert's `valid`, not per-item, and the
standard fix pattern is a decoupled one-time toast independent of the
persistent alert.

**Built**: [common/on_actions/09_smart_notifications_law_ready_toast.txt](../../smart_notifications/common/on_actions/09_smart_notifications_law_ready_toast.txt),
a monthly edge-detector (same real hook as the truce tracker) — for each
law, fires `smart_notifications_law_ready_toast`
([common/messages/00_messages.txt](../../smart_notifications/common/messages/00_messages.txt)) once
when it transitions from not-ready to ready (a per-law-type "already
notified" variable, cleared again once the law stops being ready, so it
can fire again on a future readiness edge), independent of whether the
persistent alert is currently dismissed. Deliberately generic toast text
(no dynamic law name) to avoid re-risking the same law-scope dynamic-text
uncertainty the alert's own list already carries — the alert itself
(already fixed) is where the specific name/group shows. **Not yet
confirmed live** — needs a fresh law to hit its readiness edge after this
ships (or wait for the next monthly pulse if one is already there).

## Process fix: mistake patterns now caught mechanically, not by memory

Per the user, directly: "how do we prevent you from doing the same
mistakes over and over again, and not even verifying before sending me
to test?" Real, fair critique — the same general class of mistake
(a subtly-wrong scope/context assumption) hit this one feature five
times in an afternoon, each only caught after a live test. Rather than
just committing to look harder, extended
[tools/validate_syntax.py](../../tools/validate_syntax.py) (already a required
step after every file change, per CLAUDE.md) to catch the three
confirmed-real patterns behind those five bugs automatically: an uncast
`SCOPE.GetRootScope`, `any_X` used inside an `effect` block, and effect
keywords used inside a `valid`/`is_valid`/`limit` trigger block. Verified
it actually works both directions — reproduced known-bad snippets from
this session's real bugs (all three caught) and known-good snippets from
the current codebase (zero false positives) — before trusting it. See
[docs/engine-notes.md § Known mistake patterns](../engine-notes.md) for
the full writeup; add new patterns there (and to the checker function)
if a similar mistake shape turns up again.

**Also answered directly: why 99 threshold steps instead of `A - B >
1%`.** Checked rather than just re-asserted: there is no confirmed way
to pull either chance out as a raw number for arithmetic —
`enactment_chance_for_law`/`stall_chance_for_law` are pure comparison
triggers (`{ target = X value > Y }`), and `common/script_values/script_values.md`
(the actual spec for what can appear as a numeric value) gives no
indication a comparison-shaped trigger like these can be embedded as a
plain number; an exhaustive grep for `value = enactment_chance`/
`value = stall_chance` anywhere in the game's own files (vanilla
included) found nothing. The threshold sweep is the closest
approximation of an exact subtraction the engine's own vocabulary
allows, not an unnecessary complication. See
[docs/engine-notes.md § Success-vs-stall comparisons have no numeric form](../engine-notes.md).

## New notifications/alerts backlog — sized and sequenced 2026-09-08

All four items below are **P1 per the user**. This is the recommended
build order (easiest/lowest-risk first), with a rough size estimate
factoring in this project's own track record — GUI-touching work
(Phase 3's Watchlist selector) took far more iterations than pure
script/on_action work (Phase 4's relational filtering, or the existing
amendment-repeal alert) ever did:

1. **Verify the amendment-repeal alert — Size: S.** Already built (see
   below), not new work — just needs in-game confirmation, and the user's
   own note that "currently the requirements means they never really
   become repealable" needs investigating: is `amendment_can_be_repealed`
   just naturally rare, or does its trigger condition need revisiting?
2. **New alert: agitator invite available — Size: M.** New alert_type,
   same shape as the amendment-repeal one (no GUI work needed, just a
   trigger + ribbon icon). Needs: confirming whether agitators are
   DLC-gated content before investing further; a trigger checking for an
   open invite slot AND a non-empty eligible-candidates list (both, not
   just slot availability); and awareness of the ~5-year cooldown after
   inviting someone, so the alert doesn't fire again during it.
3. **New alert: state in taxation deficit — Size: M** (base version),
   **L** if the "only alert when fixing it is net-positive" refinement is
   pursued. New alert_type; needs finding the right state-economy value
   for a taxation deficit and, for the refinement, a `script_value`
   comparing the fix's benefit against added bureaucrat/paper upkeep —
   real extra complexity, worth shipping the simple version first and
   deciding separately whether the refinement is worth it.
4. **"You can now pass a law you wanted" notification — Size: L.** The
   biggest of the four: needs a genuinely new `common/scripted_guis/`
   entry with a checkbox/button on the actual law-enactment GUI screen
   (per-law opt-in), not just script/on_action work — the same category
   of work as Phase 3's Watchlist selector, which took the most
   iterations of anything shipped so far in this project. See the
   existing scoping below for the details already worked out.

Below are the original, more detailed entries for items 1 and 4 (kept
from earlier scoping sessions), plus two new entries for items 2 and 3.

More candidates surfaced in the user's WIP doc (2026-09-05), same
monthly-pulse + repeat-guard shape as the Law Commitment idea above —
grouping them here rather than writing three near-duplicate sections:

- [~] **New alert: agitator invite available — BUILT 2026-09-08, not yet
      confirmed in-game.** Research done first, per the plan: (1) agitators
      ARE DLC-gated — `has_dlc_feature = agitators` (confirmed real,
      already used by vanilla's own `grant_leadership_to_agitator`/
      `grant_command_to_agitator` interactions in
      `common/character_interactions/00_character_interactions.txt`) —
      part of the Voice of the People Immersion Pack, not base game. (2)
      Real trigger names confirmed via `triggers.log`:
      `empty_agitator_slots >= 1` (country scope) for the open-slot half,
      and `any_character_in_exile_pool = { can_agitate = ROOT }` for the
      non-empty-eligible-list half — `any_character_in_exile_pool` is a
      global iterator (no scope needed) over the exile pool, `can_agitate`
      is the exact same country-eligibility check vanilla's own
      `invite_exile` interaction gates its `possible` block with
      (`can_agitate = scope:actor`), so this mirrors real vanilla
      eligibility rather than a guessed condition. (3) The ~5-year
      cooldown is real and confirmed exactly: `invite_exile`'s own
      `cooldown = { days = normal_modifier_time }` where
      `normal_modifier_time = 1825` days (`common/script_values/
      event_values.txt`) = 5 years. **Not directly queryable from
      script** — no documented trigger exists for "is this specific
      character-interaction on cooldown". Working assumption, UNCONFIRMED:
      the invited agitator's own tenure (`add_career_length` months =
      60-90 on invite, i.e. ~5-7.5 years) should keep their slot occupied
      for the whole cooldown window anyway, so `empty_agitator_slots`
      should naturally stay at 0 and keep this alert quiet without a
      separate cooldown check — but if a session ever shows this alert
      lit up while Invite Exile is still greyed out on cooldown, that
      assumption is wrong and needs revisiting. Shipped:
      [common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt)
      (`smart_notifications_agitator_invite_available_alert`, `type =
      important_action`, `open_panel = politics|default` matching the
      exile pool's own overlay on the Politics Overview tab), loc in
      [smart_notifications_l_english.yml](../../smart_notifications/localization/english/smart_notifications_l_english.yml)
      (both `_name`/`_desc` and the separate `_setting_name`, per the "two
      name-shaped loc keys" engine-notes entry). **Needs in-game
      confirmation**, same caveat as every other alert here: an open slot
      + an eligible exile actually appearing, and specifically a session
      spanning the ~5-year cooldown to check the assumption above.
- [~] **New alert: state in taxation deficit — BUILT 2026-09-08 (base
      version), not yet confirmed in-game.** Real find while researching:
      vanilla ALREADY has this exact alert worked out, just never
      shipped — `insufficient_tax_capacity_alert` sits commented out under
      "Hidden by default" in `common/alert_types/00_alert_types.txt`, with
      the trigger `tax_capacity < tax_capacity_usage` +
      `is_incorporated = yes` (both confirmed real, state-scope triggers
      per `triggers.log`). "Taxation deficit" is the game's own "Insufficient
      Taxation Capacity" concept — when a state's population outgrows its
      Taxation Capacity, all taxation there loses efficiency (confirmed via
      `concept_tax_capacity_desc`/`STATE_TAX_CAPACITY_INSUFFICIENT_LONG`,
      `localization/english/concepts_l_english.yml` /
      `interfaces_l_english.yml`) — not a distinct "Xk/Wk lost" trigger of
      its own; the deficit shows up as reduced tax revenue efficiency, and
      vanilla's own trigger is the accepted way to detect it. Reused that
      trigger verbatim rather than inventing a new one, since Paradox had
      already worked out the right condition and simply left it off.
      Shipped:
      [common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt)
      (`smart_notifications_taxation_deficit_alert`, `script_context =
      player_state`, `open_panel = states_panel`, `alert_group =
      smart_notifications_taxation_deficit_states` since multiple states
      can trigger it simultaneously and an `important_action` with no
      `alert_group` never groups — matching vanilla's own
      `low_market_access_alert`/the hidden tax-capacity alert's choice to
      group by state), loc in
      [smart_notifications_l_english.yml](../../smart_notifications/localization/english/smart_notifications_l_english.yml)
      using the exact `SCOPE.GetRootScope.GetState.GetName` dynamic-text
      chain (plus the extra `_action` key used for grouped
      important-actions) copied from vanilla's own `player_state`-scoped
      alerts, not guessed. **Nice-to-have, deliberately not attempted
      here:** the "only alert if fixing it pays for itself" refinement
      (comparing the deficit's cost against added bureaucrat/paper
      upkeep via a `script_value`) — scope separately once the base
      version is confirmed working. **Needs in-game confirmation**, same
      caveat as every other alert here.

- [x] **Truce expiry notification — CONFIRMED DONE (marked complete by
      the user 2026-09-08).** The user confirmed (2026-09-06) they want this
      despite the small country count, and only the "just expired" half is
      buildable (see the earlier finding below on why "expiring in one
      month" isn't). Shipped:
      [common/on_actions/02_smart_notifications_truce_tracker.txt](../../smart_notifications/common/on_actions/02_smart_notifications_truce_tracker.txt)
      — a monthly pulse (`on_monthly_pulse_country`, `is_player`-gated)
      that iterates every country, flags one with `has_truce_with = root`
      via a variable set *on that country* (variable names are static
      keys, can't be parameterized per-tag, so the flag has to live on the
      other country rather than as a list on us), and fires
      `smart_notifications_truce_expired`
      ([00_messages.txt](../../smart_notifications/common/messages/00_messages.txt), new `toast`
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
- [~] **"You can now pass a law you wanted" notification — BUILT
      2026-09-08, REVISED same day after the user rejected the first
      version, not yet seen in-game.** First pass flagged "the enactment
      currently in progress" rather than a specific law (to avoid an
      unconfirmed law_type-scoped variable / `LawType.MakeScope` GUI
      call — neither had any vanilla precedent anywhere). **The user
      correctly rejected this as useless**: it only worked once you'd
      already committed to enacting something, which defeats the purpose
      — the actual ask is "tell me when a law I want, that I haven't
      necessarily started enacting, now has more support than pushback,"
      i.e. a real per-law decision aid, not a progress ping on something
      already underway.
      **Redesigned around a cleaner mechanism found during the
      rework:** `enactment_chance_for_law = { target = scope:my_lawtype
      value > 0.2 }` (confirmed real, triggers.log) computes a
      SPECIFIC law's hypothetical enactment chance regardless of whether
      it's actively being enacted — exactly the "worth starting" signal
      needed, and something the original `enactment_chance` (used by the
      rejected first version) can't do at all, since it only describes
      whatever's already in progress. This meant the flag DOES need to
      identify a specific law after all — but rather than the originally-
      feared `law_type` (the global, country-agnostic database entry,
      which would make "wanted" one setting shared by every save), the
      flag lives on `law` scope instead — a country's own per-law-type
      record, confirmed real and already scriptable in this exact mod
      (the amendment alert above already does
      `any_active_law = { any_scope_amendment = { ... } }`, and `law` is
      `any_law`/`any_active_law`'s own documented iteration target,
      inherently per-country already). This sidesteps the country-vs-law_type
      ambiguity entirely. Shipped, three pieces:
      1. [common/scripted_guis/smart_notifications_law_notify_sgui.txt](../../smart_notifications/common/scripted_guis/smart_notifications_law_notify_sgui.txt)
         — toggle/check SGUI pair, `scope = law`, same
         is_valid-also-gates-Execute split as `watchlist_sgui.txt`.
      2. [gui/politics_panel_change_law.gui](../../smart_notifications/gui/politics_panel_change_law.gui)
         — the same full-file GUI override as before (transcription
         re-verified with a `diff` against vanilla), now with the
         checkbox moved onto the shared law-detail panel so it's visible
         for whichever law the player has SELECTED-but-not-enacting too,
         not gated to `Law.IsBeingEnacted` — that's the case this feature
         exists for. Wired via `Law.MakeScope`. **This is now the single
         biggest unconfirmed risk in the whole feature**: `.MakeScope` is
         confirmed on Character/State/Country/PoliticalMovement GUI
         objects elsewhere in vanilla, and `Law` here is exactly
         analogous (a GUI wrapper around a real, documented `law` scope),
         but no vanilla file anywhere actually calls `Law.MakeScope` —
         this is extrapolation from a consistent pattern, not a copied
         confirmed example. **First thing to check in-game**: does the
         checkbox render and actually toggle at all.
      3. [common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt)
         (`smart_notifications_law_commitment_alert`) — `valid =
         { any_law = { has_variable = smart_notifications_wanted_law
         can_be_enacted = yes  enactment_chance_for_law = { target =
         THIS.type  value > 0.5 } } }`. `can_be_enacted = yes` (confirmed
         real, law scope) doubles as free self-cleanup: once a flagged
         law becomes active or blocked, this alert naturally stops firing
         for it with no separate reset needed — simpler than the first
         version's `on_law_enactment_started` reset hook, which is no
         longer needed and was removed. **The 0.5 threshold is still
         UNCONFIRMED**, same open question as originally scoped — a
         reasonable "better support than pushback" guess, not verified
         against how vanilla's own UI colors the number; first thing to
         tune if the alert fires too early or too late. loc in
         [smart_notifications_l_english.yml](../../smart_notifications/localization/english/smart_notifications_l_english.yml),
         static/generic text (no dynamic law-name reference) for the same
         lower-risk reason the amendment-repeal alert made that call.
      **Needs in-game confirmation across the whole chain** — checkbox
      render/toggle (the real open question now), the alert actually
      lighting up for a flagged-but-not-enacting law, and whether 0.5 is
      the right threshold — expect this to need the most follow-up rounds
      of anything shipped this session, consistent with the "budget the
      most iterations for this one" sizing call.
- [x] **"You can now repeal an amendment" notification — built and
      shipped 2026-09-06.** Per the user, this one should surface on the
      top ribbon — used `type = important_action` (not plain `alert`) for
      exactly that. Shipped:
      [common/alert_types/01_smart_notifications_alerts.txt](../../smart_notifications/common/alert_types/01_smart_notifications_alerts.txt),
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
[docs/engine-notes.md § An alert type needs TWO name-shaped loc keys](../engine-notes.md).

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
   [docs/engine-notes.md § `GetName` is not a valid dynamic-text function](../engine-notes.md).

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
[docs/engine-notes.md § Tagging mod-created notifications](../engine-notes.md)
and [CLAUDE.md](../../CLAUDE.md). Deliberately NOT applied to
`invasion_against_us_notification_group`/`diplo_play_subject_overlord_notification_group`
(Phase 1 group-splits of vanilla content, not new notifications).


## Law commitment alert: real root cause of the blank law name found and fixed (2026-09-08)

Live testing (screenshot) confirmed the tooltip still showed blank/garbled
text ("• )") after the SGUI-folder fix. Checked error.log directly instead
of asking for another test round -- found the SECOND, real root cause,
distinct from the folder issue:

```
Could not find data system function 'GetNameNoFormatting' in 'THIS.GetNameNoFormatting'.
Could not find promote for 'GetGroup' in 'THIS.GetGroup.GetName'.
Data error in loc string 'smart_notifications_law_commitment_list_entry'
```

`law` scope has neither a name-getter nor a `GetGroup` promote in the
script-side dynamic-text/data-function system used by `custom_tooltip`/
`[...]` loc brackets. The GUI-binding-language `Law.GetGroup` used by
vanilla's own law-list widgets (`gui/politics_panel_types.gui`) is a
completely separate function table -- confirmed real there, but not
reachable from script-side dynamic text, which is a different system. This
was never re-verified after the folder fix in the last session, exactly
the kind of unverified claim the user has been (rightly) pushing back on --
this time it was checked directly against error.log before reporting back.

**Fix:** dropped dynamic text for this entirely. Every one of the 138 law
types already has its own vanilla loc key (`law_<type>`) and so does its
`group` field (`lawgroup_<X>`) -- confirmed for all 138 by cross-checking
`common/laws/*.txt` against `localization/english/*.yml`. Generated one
static loc key per law type
(`smart_notifications_law_entry_<type>:0 "• $law_<type>$ ($lawgroup_<X>$)
"`)
using the vanilla inline-loc-reference syntax (`$key$`, confirmed real via
`laws_l_english.yml`'s own `"$ideology_carlist$"` usage) -- no dynamic
function call needed, so this class of error can't recur here. The
tooltip-list SGUI now dispatches on `THIS.type = law_type:X` (138
branches, same generated pattern as the notify-toggle SGUI) and calls the
matching static key instead of the broken dynamic one.
`validate_syntax.py` passes; not yet re-tested live.

**On the "wrong screen on click" complaint in the same report:** checked
whether `important_action`-type alerts actually honor a tab argument in
`open_panel` (rather than assuming) -- vanilla's own `formable_possible`
alert (`common/alert_types/00_alert_types.txt`) is `type = important_action`
with `open_panel = diplomatic_overview|nation_formation` and is known-working
vanilla content, confirming the mechanism does apply the tab for this alert
type. `politics|laws` should behave the same way. The known, already-
documented limitation stands: this can only land on the Laws tab overview,
never highlight/jump to the specific law group (no scriptable parameterized
version of `InformationPanelBar.OpenChangeLaw(Law.GetGroup)` exists --
confirmed in the previous session). The just-fixed tooltip text (specific
law name + group) is the intended mitigation for that gap, not a
workaround still to come.


## Law commitment alert CONFIRMED working live (2026-09-08) + alert-order question answered

User confirmed the correct law name and group now render in the alert
tooltip. Root cause and fix are documented above and in
[docs/engine-notes.md § Two separate function tables](../engine-notes.md)
-- this took far more live-test rounds than it should have, and that
section is the retrospective on why, plus the new CLAUDE.md rule meant to
stop it recurring: precedent for a dynamic-text/`custom_tooltip` call must
come from another dynamic-text call, never from a `.gui` file's own
bindings, even when the `.gui` usage is genuinely real.

**"Can it sit at the bottom with the other SN alerts?"** -- checked rather
than guessed: `common/alert_types/00_alert_types.txt`'s own complete
header comment documents every field the format supports, and there is no
priority/order field at all (only "angry_important_action alerts are
sorted first" is documented). No code change was needed or possible here
-- the three SN alerts already appear grouped, consecutively, after every
vanilla one, because they all live in one file
(`01_smart_notifications_alerts.txt`) that sorts after vanilla's `00_`
file by filename, in the order they were added within it. Full writeup:
[docs/engine-notes.md § Important-action alert order](../engine-notes.md).

The temporary diagnostic probe
(`common/on_actions/08_smart_notifications_law_commitment_probe.txt`) can
now be deleted -- both pieces of this feature (the alert itself and the
name-render fix) are confirmed working live. Still unconfirmed: the
decoupled one-time toast for re-firing after dismissal
(`common/on_actions/09_smart_notifications_law_ready_toast.txt`).


## Automated cross-reference tests added (2026-09-08), per the user

"Add tests into your code so we know it's still working without relying
on me testing it all the time." Can't execute Jomini script logic outside
the actual game, but every bug this session (and several from before)
that produced NO error.log signature at all -- a typo'd loc key, a
forgotten alert_group registration, a scripted_gui in the wrong folder, a
law dropped from one generated list but not another -- is exactly the
kind of thing a static cross-reference scan CAN catch, mechanically,
every time, without needing a live repro. Added
`tools/check_references.py`, wired into `python tools/validate_syntax.py`
so the existing habit covers it automatically:

- Every `custom_tooltip = "KEY"` resolves to a real loc key.
- Every `GetScriptedGui('X')` resolves to an X defined under
  `common/scripted_guis/` specifically (and any scripted_gui-shaped block
  found outside that folder is flagged even before anything references
  it) -- direct regression test for the exact bug behind the law
  commitment alert's blank name.
- Every `alert_group` used is declared in `common/alert_groups/` and has
  its `ag_*_name/_desc/_tooltip` loc keys -- regression test for the
  taxation deficit alert's aggregation bug.
- Every alert_type has all 5 required loc keys
  (`alert_<key>_name/_desc/_hint/_action`, `<key>_setting_name`).
- The 4 generated per-law-type files (wanted-flag trigger, notify
  toggle/check sgui, commitment tooltip sgui, readiness toast) all
  reference the exact same 138 laws -- regression test for the BOM
  extraction bug that silently dropped 12 laws from one list only.
- Every `law_type:X` referenced anywhere is a real vanilla law (skipped,
  not failed, if the vanilla install isn't found on the machine running
  the check).

Verified the checker actually catches regressions, not just passes
vacuously, by injecting each of the three confirmed-real historical bugs
into a scratch copy and confirming a FAIL with the right message for
each, before trusting it clean on the real repo.


## Launcher bundles the whole mod folder on upload -- fixed with a packaging script (2026-09-08)

User's own screenshot of the Paradox Launcher's Upload Mod dialog,
opened on the existing dev/test entry (the junction to this repo's
root), confirmed it: the Launcher packages the ENTIRE target directory
for upload, no include/exclude filter. Uploading straight from the dev
junction would ship tools/, docs/, reference/, .git/, TODO.md and every
other dev-only file to subscribers.

Given a choice between restructuring this repo (mod content into its own
subfolder, repoint the junction -- correct in principle but touches
every tool script's paths and dozens of references across
CLAUDE.md/TODO.md/engine-notes.md) versus a separate packaging script
(zero risk to the existing dev/test workflow), the user chose the
packaging script. Added `tools/package_release.py` (wrapped as
`/package-release`): copies only `.metadata/`, `common/`, `events/`,
`gui/`, `localization/`, `thumbnail.png` to a SEPARATE mod folder,
`smart_notifications_release`, refusing to run if `validate_syntax.py`
fails on the source first. The existing dev junction/entry is completely
untouched. Verified the output contains exactly those 5 folders and
nothing else, and ran it for real against the actual Documents mod
folder so `smart_notifications_release` is ready to add as its own
Mod Library entry.

Still blocking before any actual upload: `thumbnail.png` doesn't exist
yet (see STORE_ASSETS_GUIDE.md) -- the packaging script picks it up
automatically from the repo root once it does.


## Toast vs alert investigated (2026-09-09): confirmed NOT a regression, then fixed the actual ask

User reported the persistent alert no longer appears, only the toast --
on both the dev and packaged release folders. Checked the code before
assuming a bug: the toast's own header comment
(common/on_actions/09_smart_notifications_law_ready_toast.txt) already
documented this exact scenario as the reason the toast was built in the
first place -- important_action dismissal is edge-triggered on the
alert's `valid` going false->true, so if some OTHER wanted law was
already ready (and the alert shown+dismissed) before this new law became
ready, "any wanted law ready" never flips false->true again and the
persistent alert stays hidden, while the toast (per-law edge detection)
correctly fires independently. Toast firing is proof the underlying
condition is true, since both check the identical shared triggers -- this
is expected, previously-documented engine behavior, not a new bug. (To
confirm live: TopFrontend.UnhideAllImportantActions, the list's own
"unhide all" control, should bring the alert back immediately.)

The actual, valid ask underneath the report: "the toast is a great idea,
just need to ensure it has the details of which law triggered it, just
like the alert." The toast's body text was deliberately generic when
built, to avoid re-risking the law-scope dynamic-text bug that was still
unfixed at the time. That bug is now fixed and proven
(docs/engine-notes.md "Two separate function tables") -- applied the
identical technique here: 138 per-law-type message keys
(`smart_notifications_law_ready_toast_<type>`, all sharing one `group`
so Message Settings still shows a single row), each with its own
`$law_X$ Is Ready to Enact` / `... ($lawgroup_Y$)` static loc text, and
the on_action's 138-branch dispatch now calls the matching per-law key
instead of one shared generic one (`post_notification` takes a bare key,
no per-call override -- CLAUDE.md). Verified positionally (the branch
order and the law-type order matched exactly before doing a 1:1 string
rewrite) rather than guessing the mapping held.

Added `check_post_notification_targets` to `tools/check_references.py`,
generalizing the alert-loc-completeness check to messages: every
`post_notification` target must resolve to a real message with its
`_name`/`_desc` loc keys. Verified it fires on an injected typo before
trusting it clean.


## Release candidates now versioned via git tags (2026-09-09)

User asked: "can I easily go back to what we released on [this date]?"
Answer was no before today -- only one unrelated tag existed. Backfilled
`v<version>-<short-hash>` tags for the entire history (v0.20 through
v0.34, 18 tags total, using the short hash because a past version-
numbering regression means some version numbers legitimately point at
two different real commits -- see docs/engine-notes.md for the full
list). Added the rule to CLAUDE.md: every future version bump gets a tag
on that same commit, immediately.

Also added automatic tagging to `tools/package_release.py`
(`release-v<version>-<date>`) so "what did we actually package for
external release" is separately, trivially findable -- distinct from
version-bump tags since not every bump gets externally released.

**Real bug found and fixed while testing this**: the packaging script's
original delete-then-recreate-in-place approach hit a file lock (the
Paradox Launcher had the release folder open as a registered mod entry)
mid-delete, leaving the live output folder PARTIALLY DELETED
(common/alert_groups and common/alert_types gone, common/messages
emptied) -- worse than not running it at all. Fixed by staging the full
copy in a temp directory first and only swapping items into place once
staged, with per-item failure handling instead of one all-or-nothing
operation. The actual release folder is still in that broken state as of
this writing -- the Launcher needs to be closed before a re-run can
finish repairing it; flagged to the user.


## Toast rarity investigated (2026-09-09): likely by design, instrumented rather than guessed

User confirmed both the alert and toast now show the correct law, but
reported only getting the toast once, with the alert showing far more
often -- "unclear what makes it show or not."

Leading explanation, NOT yet confirmed via logs (deliberately not
asserted as fact until it is): the alert is level-triggered (visible
continuously whenever ANY wanted law is currently ready, refreshed every
ALERTS_FRAMES_BETWEEN_UPDATES), while the toast is edge-triggered (fires
once per LAW's own false-to-true readiness transition, sampled only
monthly via on_monthly_pulse_country, then suppressed for that same law
until it goes un-ready and ready again). If only one flagged law has
crossed ready so far and stays ready, the toast correctly fires once and
goes quiet while the alert keeps showing continuously -- exactly matching
what was reported, and not a bug under that explanation.

Rather than asserting this without proof (the exact mistake being
actively corrected all session), added TEMPORARY diagnostic logging to
common/on_actions/09_smart_notifications_law_ready_toast.txt:
- Once per month per player-country: whether the alert-equivalent
  condition (any_law wanted+can_be_enacted+ready) is currently true
  (`SNW_LAW_TOAST|pulse|...|at_least_one_wanted_law_ready=yes/no`).
- Every actual toast fire, per law type (`SNW_LAW_TOAST|fired|<type>`).
- Every notified-flag reset, per law type
  (`SNW_LAW_TOAST|reset|<type>`) -- confirms when a law drops back to
  not-ready, re-arming it for a future toast.

Next play session: `python tools/scan_logs.py` (or `/scan-logs`) will
surface all of these. If `at_least_one_wanted_law_ready=yes` persists for
many months with no new `fired` line for a DIFFERENT law type, that
confirms the level-vs-edge explanation is the whole story. If a `fired`
line is missing despite conditions looking right, or a `reset` never
happens for a law that visibly stopped being enactable, that's a real
bug to chase. DELETE this instrumentation once confirmed either way, not
before.

## Taxation deficit toast added (2026-09-09), per the user

User confirmed the same edge-triggered-dismissal gap the law toast was
built for also applies to taxation deficit: it's grouped/aggregated
(alert_group), so if State A's deficit already showed+dismissed and a
DIFFERENT state B later develops one while A's is still ongoing, "some
state has a deficit" never flips false->true again and the alert never
resurfaces for B. Asked whether to add a matching toast; user said yes.

Structurally different from the law toast, and simpler: states aren't a
small fixed enumerable set the way exactly 138 law types are, so a
static per-type dispatch (the law toast's approach) doesn't scale here.
Instead: one shared message (`type = state`, matching vanilla's own
`type = state` messages like colony_created), naming the state via
`[SCOPE.GetRootScope.GetState.GetName]` -- the EXACT cast chain our own
taxation_deficit_alert's loc already uses and has been confirmed working
live all session, so no new dynamic-text risk. Individual state tracking
uses a country-scope variable list of event-target references
(`add_to_variable_list`/`is_target_in_variable_list`/`remove_list_variable`,
all confirmed real via effects.log/triggers.log) instead of a
per-type "notified" variable.

New file: common/on_actions/10_smart_notifications_taxation_deficit_toast.txt.
Uses `prev = { post_notification = ... }` to re-scope back to the
specific state (after stepping into `THIS.owner` to reach the country's
variable list) so `type = state` resolves correctly at the point
`post_notification` is called -- this exact bare-`prev`-as-block-header
usage is inferred from vanilla's own confirmed `prev.owner = { activate_law
= prev.type }` pattern (common/laws/00_governance_principles.txt), not
independently tested before now. `validate_syntax.py` passes. Added
matching `SNW_TAX_TOAST|fired`/`|reset` debug_log taps (same pattern as
the law toast) so this can be confirmed or debugged from logs rather
than guessed at. NOT YET LIVE TESTED -- next thing to verify.

## Dev mod entry renamed to avoid upload-flow confusion (2026-09-09)

User: the two mod entries (dev/test junction vs. release folder) looked
identical in the Launcher's upload flow. Since the dev junction points
directly at this repo's real `.metadata/metadata.json`, it can't show a
different name than the release folder just by editing that file in
place -- the packaging step has to actively rewrite it for the shipped
copy. Repo's canonical `name` is now `"Smart Notifications - Dev"`;
`tools/package_release.py` strips the `" - Dev"` suffix back off when
staging the packaged copy (`strip_dev_name_suffix`), so the actual
published listing never says "Dev". Verified: dev entry now reads
`Smart Notifications - Dev`, packaged release entry reads
`Smart Notifications`, both otherwise byte-identical metadata (version,
id, etc. unchanged).

## Diplomatic action duplicate fixed; Watchlist empty-prompt added (2026-09-09)

User pushed back on the earlier "not a bug" answer, correctly: two
notifications for one event is still bad UX even if technically from two
separate systems, and our own generic text was weak. Fixed properly
instead of re-explaining:

Checked every `*_action_notification_desc` key in vanilla's
diplomacy_l_english.yml -- confirmed ALL of them (increase_relations,
damage_relations, expel_diplomats, rivalry, embargo, ...) are written
from the RECIPIENT's own perspective (GetPlayer/"us"/"we") and are NOT
common/messages/ entries at all (checked both vanilla's and our own
copy -- zero matches), fired by a separate, hardcoded, unfilterable
mechanism that only exists when the action targets the PLAYER
specifically. Our own generic elevated notification duplicated this
exactly in that one case, with strictly worse (non-specific) wording.
Fixed common/on_actions/06_smart_notifications_diplomatic_action_filtering.txt
to suppress our own notification entirely when `scope:recipient` is the
player, letting vanilla's specific popup stand alone. Left unchanged for
the case that's genuinely uncovered: a watched third party's action
where the player is NOT the recipient (no native popup exists there for
an observer).

Also built the Watchlist empty-prompt the user asked for
(common/on_actions/11_smart_notifications_watchlist_empty_prompt.txt):
checked first whether there's any "on save load" on_action to hook
directly -- confirmed there genuinely isn't one anywhere in this engine
(on_game_started/on_game_started_after_lobby both explicitly fire "for
the first time for each campaign" only, per vanilla's own comment; no
on_savegame_loaded-shaped on_action exists in any on_actions file).
Worked around this the same way the law/tax toasts already do: check
monthly instead, reaching the same practical outcome (seen shortly after
opening any save, new or old) without a hook that doesn't exist. Fires
once when the Watchlist has no non-player country with any real
watch-provenance flag, clears if it's no longer empty (same edge-
detection pattern as every other toast in this mod). Also updated the
existing smart_notifications_mod_loaded toast to name the Watchlist tab
explicitly.

Caught and fixed my own mistake while writing the loc text: initially
wrote "Interesting Countries" as the tab name (a real vanilla label, but
for vanilla's own separate, hidden, unused third tab) -- checked
gui/message_settings.gui directly and confirmed our actual tab is a
genuinely new fourth one labeled "Watchlist"
(SMART_NOTIFICATIONS_WATCHLIST_TAB). Fixed both loc entries before
shipping either.


## Startup message shortened (2026-09-09)

User: too long. Cut from 3 sentences down to 1: "Great powers and
neighbors are already on your Watchlist. Adjust it anytime in Message
Settings (bell icon) > Watchlist."


## Taxation toast capped at 3 concurrent; diplomatic-action unfilterable-native-popup confirmed (2026-09-09)

User clarified the ask: keep the persistent ALERT as-is (already grouped
into one stacked row, fine), cap only the one-time TOASTS at 3
concurrent. Much simpler than ranking states by deficit severity (the
earlier, more complex idea that would have needed the same threshold-
sweep workaround as the law alert) -- the toast's own tracking list
(`smart_notifications_notified_deficit_states`) already IS the live
count of active notifications, so `variable_list_size >= 3` as a firing
gate is a direct, small addition. Capped in
common/on_actions/10_smart_notifications_taxation_deficit_toast.txt.

Separately: reviewed the user's Tibet/Shan/Baroda screenshots. Confirmed
these are NOT a gap in our own filtering -- they're vanilla's own native,
per-action-type popups (damage_relations/increase_relations_action_
notification, etc.), which fire for ANY country's diplomatic action
targeting the player, completely independent of watchlist status,
confirmed via the earlier investigation (not a common/messages/ entry,
no on_action posts it, fired by hardcoded engine logic with no moddable
hook at all). Baroda (not a neighbor, not a great power, not watched) is
exactly what this looks like when it fires -- expected, not a bug, and
not something any mod can filter. This is the same confirmed limitation
already logged in memory as "Notification logger coverage gaps."

**CORRECTION, same day, later: the above "hardcoded/unfilterable" claim
was wrong.** User pushed back after screenshots showed these popups
appearing in an earlier test session but NOT in a later one, despite
nothing about their watch status changing. Actually checked the log
evidence this time instead of re-asserting the earlier claim:
`increase_relations_action_notification_name`/`damage_relations_
action_notification_name` (the exact loc keys behind these popups) are
resolved via `GetDiplomaticAction.GetActionNotificationName`, which is
also the SAME dynamic-text call behind
`notification_diplomatic_action_notification_name` -- i.e. these popups
ARE `diplomatic_action_notification`, just with per-action-type wording
substituted in. That key is fully within this mod's own
`common/messages/` and had been muted since Phase 4 -- but see the
"Mixed group notification types" fix above/in engine-notes.md: it was
still sharing a group with 3 `toast` siblings, which (per exact
game.log timestamp correlation) appears to have silently defeated its
own mute the whole time. The popups disappeared in the exact same
session the regroup fix landed, with the mixed-types warning also gone.
Not hardcoded, not unfilterable, not a "no moddable hook" case -- it
was our own grouping bug. See the corrected, evidence-based writeup in
docs/engine-notes.md's "Override hierarchy" section. Added
`tools/check_references.py`'s `check_mixed_group_notification_types` so
this exact bug class fails the build automatically from now on
(confirmed it catches the original bug by re-injecting it and reverting).


## Found and fixed a real silent-notification regression from the above (2026-09-09)

User asked a sharp follow-up: "if these countries were in our watchlist,
we should get the toast notification for that, no?" That's what exposed
an actual bug, on top of the wrong-claim correction above. Two fixes
made earlier the SAME DAY interacted badly:

- 12:20 (`ae81158`): suppressed our own
  `smart_notifications_diplomatic_action_watched` notification whenever
  `scope:recipient` was the player, on the (wrong, since-corrected)
  belief vanilla's own popup was a separate unfilterable mechanism that
  would "stand alone."
- 14:28 (`03eaf5d`): fixed the mixed-notification-types bug, which (per
  the game.log timestamp evidence already documented above) was the
  actual reason vanilla's *muted* `diplomatic_action_notification` had
  been leaking through as a toast up to that point.

Once the second fix actually closed that leak, the first fix's
assumption ("vanilla's popup will still show") stopped being true --
net result: a diplomatic action targeting the player directly now
produced NO toast at all, from either side. Fixed in
common/on_actions/06_smart_notifications_diplomatic_action_filtering.txt
by removing the player-recipient suppression branch entirely -- it was
redundant as well as wrong, since `smart_notifications_is_watched`
already includes `is_player = yes`
(common/scripted_triggers/00_smart_notifications_triggers.txt), so the
normal watched-check elevates a player-targeted action on its own with
no special case needed. NOT YET LIVE-TESTED.


## Taxation toast cap: first attempt CONFIRMED BROKEN, rebuilt on a different mechanism (2026-09-09)

User: cap didn't work, still got ~15/30 toasts. Checked the actual
debug.log rather than re-guessing: 30 `SNW_TAX_TOAST|fired` lines, all
the same timestamp -- confirmed the cap never engaged.

Root cause: the first attempt gated firing on
`NOT = { variable_list_size >= 3 }` INSIDE the same `every_scope_state`
loop that also does `add_to_variable_list` for each match. Each state's
`limit` does not see the list mutations made by earlier states in the
SAME pass -- confirmed by the log, not assumed. every_scope_state
combines filter+act per item with no isolation between iterations'
trigger checks and prior iterations' effects within one pulse.

Rebuilt on `ordered_scope_state` instead (confirmed real,
script_docs effects.log, real vanilla precedent in
common/scripted_effects/00_victoria_ip4_scripted_effects.txt) --
select-then-act by design: it picks its max-capped subset FIRST (against
the list's state before any of this pulse's effects run), then executes
effects for exactly that subset. This is architecturally immune to the
specific bug that broke the first attempt, not the same approach
retried. `order_by` has no real ranking criterion available (tax_capacity/
usage confirmed comparison-only, same limitation as the law alert), so
uses a flat tied literal -- which specific 3 states get picked doesn't
matter, only that no more than 3 do.

Disclosed, not hidden: this checks the current count ONCE per pulse
before allowing up to 3 MORE, so if 1-2 were already active going in, a
pulse could push the total to 4-5 rather than holding a strict cap.
NOT the reported scenario (many states going into deficit simultaneously
from 0 active, where this is exact). A fully precise cap would need
`max` to be a computed `3 - <current count>` script value; not attempted
since no confirmed-real vanilla precedent was found for reading
variable_list_size as a raw number rather than a boolean comparison, and
guessing at that syntax is exactly the mistake being corrected here.

STILL NOT LIVE-CONFIRMED. Next test: count `SNW_TAX_TOAST|fired` lines
in debug.log after a fresh China-style start with many simultaneous
deficits -- should be <= 3, not 15+.


## Taxation toast cap: upgraded with confirmed vanilla precedent, not just reasoning (2026-09-09)

User: "are you sure?" then "do what it takes so we don't do more than 1
or 2 back and forths." Went and found actual proof rather than just
re-asserting confidence: common/on_actions/00_on_actions_monthly.txt's
exile-pool culling on_action uses `ordered_character_in_exile_pool` with
a computed `max` and ONE effect line applied to the whole selected
batch -- direct, real vanilla confirmation that ordered_X + max really
does run its effect body against N selected entities, the core
assumption the whole fix depends on. That same example also exposed a
real gap: `order_by` needs a nested script_value block
(`order_by = { value = ... }`), not the bare literal (`order_by = 1`)
the previous version used with no vanilla precedent found for that
specific form -- fixed to match the confirmed shape exactly.

Also added `[TimeKeeper.GetCurrentDate.GetString]` (confirmed real,
used throughout vanilla's own loc) to every debug_log line, and an
unconditional per-pulse `gate=open/blocked` log, so if this somehow
still fails, the log alone tells us whether the outer gate or the
ordered_scope_state selection is the broken half -- no more blind
re-guessing rounds needed.


## Taxation toast repeating monthly for same state(s) -- investigating (2026-09-09)

User: the toast repeats every month or so, should only fire once per
new deficit. Checked debug.log: `gate=open` every pulse with 3 fresh
`fired` lines each time and ZERO `reset` lines in between -- meaning
either the notified-list isn't persisting membership across monthly
pulses at all, or (less likely) 3 genuinely different states are newly
entering deficit every single month. Ruled out an auto-expiry theory
for `add_to_variable_list` (multiple real vanilla examples, e.g.
journal_entries' acw_dixie_states/krakatoa_states, add to a list with no
duration specified and clearly mean it to be permanent).

Added diagnostics rather than guess further: state names now logged on
every fired/reset line (`[prev.GetName]`, matching the confirmed-real
state-scope `.GetName` pattern, NOT `.GetNameNoFormatting` which is
country-only), plus a full list-membership dump every pulse via
`every_in_list` (confirmed real, vanilla precedent:
common/journal_entries/05_danubian_federation.txt's
`every_in_list = { variable = aus_integrated_cultures ... }`). This will
show definitively whether the SAME states repeat (real bug) or DIFFERENT
ones fire each month (not a bug, just legitimately volatile early-game
finances) before attempting any further fix.


## Repeated taxation toast: real root cause found, fixed (2026-09-09)

User confirmed: same set of states firing every month, not just newly-
deficit ones. Root cause found by inspecting the exact code, not
guessing: the "not already notified" check inside `ordered_scope_state`'s
own `limit` called `is_target_in_variable_list = { target = THIS }`
directly, but THIS there is the candidate STATE, not the country -- the
list only ever lives on the country. That check was unconditionally
asking "does this state have this list on itself" (always false), making
"not already notified" always true regardless of real membership. Fixed
by re-scoping to `THIS.owner` first, matching the same owner+prev idiom
already proven working elsewhere in the same file.

Same session, found the diagnostic logging added to chase this had its
own version of the identical mistake: `[prev.GetName]`/`[THIS.GetName]`
without the required `.GetState` cast, producing "Data error in loc
string" and corrupting the very data meant to catch the bug (per this
project's own "verify instrumentation before trusting it" rule -- the
list-member dump I read before this fix could not be trusted at all).
Fixed to `.GetState.GetName`. NOT YET LIVE-CONFIRMED after this specific
fix -- next test needs a session reload (script only re-parses at
campaign/session start) and a few months of play to check the corrected
diagnostics.


## Taxation toast: redesigned as a 3-toasts-per-campaign cap, not concurrent slots (2026-09-09)

User: the scope-fix worked (no more stuck-on-same-3), but now it just
cycles through a stream of different states over time as old ones
recover and new slots open -- still not the desired experience. Said
this was the last attempt before reverting to alert-only, no toast.

Rather than retune the "concurrent slots that free up on recovery"
design a third time -- every bug so far (same-pass mutation visibility,
wrong-scope membership check) lived in that specific mechanism -- removed
it entirely. New design: once a state has ever triggered a toast this
campaign, it's permanently marked (no reset branch exists anymore), and
once 3 states have ever done so, the outer gate permanently blocks all
further selection for the rest of the campaign. This is a genuine
behavior change (a meaningful, isolated deficit occurring long after the
initial 3 will now stay toast-silent, though the persistent alert is
completely unaffected and still shows it) -- accepted deliberately
because it trades a small amount of coverage for removing an entire
class of state-tracking complexity that had been the source of every bug
in this file. The membership-check scope fix from the previous round is
preserved (that part was correct); only the recover-and-reopen mechanism
was removed. Simulated it wasn't like the earlier over-firing bug
because -- (a) no reset branch, entries can never be removed, so
variable_list_size only ever grows -- (b) the outer gate directly
enforces the lifetime cap on that monotonic count. NOT YET LIVE-TESTED.


## Taxation toast: corrected to per-round semantics per the user's precise spec (2026-09-09)

User corrected my read of the problem: it was never about recovery/
flicker, and not about a lifetime cap either. The real model: each
monthly pulse is its own "round" of newly-crossing states (e.g. China's
initial ~20-state burst is ONE round). Within a round, toast up to 3, but
mark ALL of that round's newly-crossing states as handled immediately --
not just the 3 shown -- so the other 17 don't trickle out one by one
over following months. A state only becomes eligible again if it
independently recovers and re-enters deficit later, starting a fresh
round with its own 3-toast budget.

My previous "lifetime cap" redesign (this same day) was based on a wrong
diagnosis (assumed the issue was the recover/reopen mechanism itself);
this correction restores that mechanism (needed for the "recovers and
re-enters" requirement) but fixes the actual gap: overflow candidates
beyond the first 3 were never being marked at all in earlier versions,
leaving them eligible to surface in later pulses -- exactly the
"cycling through the batch over time" behavior reported.

Implementation: THREE passes per pulse now, not one -- (A) the proven
ordered_scope_state select+toast+mark for the first 3, (B) a new,
uncapped every_scope_state that silently marks any remaining newly-
crossing states with no toast, (C) the restored recover/re-enter reset.
Confirmed (B) is not vulnerable to the earlier mid-loop-mutation-
invisibility bug -- that bug was specifically about an aggregate COUNT
check not seeing prior same-loop mutations; (B) only does a per-state
membership check, no counting/aggregation involved, and it runs as a
separate, already-sequenced effect after (A) fully completes, not
nested inside it. NOT YET LIVE-TESTED.


## common/messages/ cross-file key redefinition: conclusively answered, no gameplay needed (2026-09-09)

Standing question from earlier the same day ("why can't we do an append
rather than an override here?"): does a later-loaded file in
common/messages/ that redefines an EXISTING key (as opposed to adding a
brand-new key) win, the way loc overrides do? Built a throwaway test
file (99_smart_notifications_redefinition_test.txt) redefining vanilla's
country_attitude_improved, plus a loc override on its text so a hit
would be unmistakable if it ever fired. Never needed to actually play
for it -- the very first game load with the test file present wrote the
engine's own answer straight to error.log:
"[gamedatabase.h:378]: Duplicated key country_attitude_improved will not
be created from file: common/messages/99_smart_notifications_redefinition_test.txt:41"
Confirmed: cross-file key redefinition in common/messages/ is silently
rejected by the engine (last-loaded file does NOT win, unlike loc).
Adding brand-new keys across multiple files IS additive -- vanilla
itself splits messages across 7 files with zero key overlap -- but
redefining an existing key from a second file is not. This conclusively
validates that 00_messages.txt needed to be a full-copy override, not
an assumption. Test file and its loc override deleted once the answer
was in hand; no logging/live-test was ever needed for this question.


## Two more real bugs found while investigating the above (2026-09-09)

While checking error.log/game.log for the redefinition test result,
found two unrelated, real, confirmed bugs:

1. **variable_list_size / is_target_in_variable_list on a never-created
   list throws an outright engine error**, not a graceful false/0 --
   confirmed via error.log: "jomini_trigger.cpp:706: Failed to read
   'target' for 'variable_list_size' [ Could not find list from read
   name flag smart_notifications_notified_deficit_states ]". Fixed by
   initializing the list (add-then-immediately-remove a dummy target) in
   common/on_actions/00_smart_notifications_on_actions.txt's
   smart_notifications_on_game_started effect, right after the mod-
   loaded toast, so the list exists (empty) from turn one of every
   campaign.

2. **"Diplomatic Action Group has mixed Notification Types" engine
   warning**, confirmed firing live 3x in game.log
   (player_message_type.cpp:177). Root cause: diplomatic_action_notification
   was muted to notification_type = none (Phase 4 filtering) but left in
   diplomatic_action_notification_group alongside 3 sibling messages
   still set to toast -- vanilla itself never has such a mismatch. Fixed
   by moving the muted message into its own new group,
   smart_notifications_diplomatic_action_notification_muted_group, with
   its own loc entry in smart_notifications_l_english.yml.

Both fixed and passing validate_syntax.py; neither yet re-confirmed
live.


## Diplomatic action toast now shows the real per-action wording, not generic text (2026-09-09)

User, after confirming the silent-notification regression fix worked:
"why do we have to have this super generic notification instead of just
telling me directly what they did?" Right question -- the earlier
"deliberately generic, accepted loss of detail" decision (2026-09-08)
was based on an incomplete investigation, not a real engine limitation.

Found the actual mechanism: vanilla's own
`notification_diplomatic_action_notification_name` resolves via
`[SCOPE.GetRootScope.GetDiplomaticAction.GetActionNotificationName]` --
a function on the diplomatic action object itself, not something tied
to that specific vanilla message key. Our own replacement messages
(`smart_notifications_diplomatic_action_watched`/`_quiet`) share the
same `type = diplomatic_action` root scope (same on_diplomatic_action
pulse that already proven-binds `SCOPE.sC('actor')`/`SCOPE.sC('recipient')`),
so the same call works for us. This is the real, confirmed-real function
`[ROOT.GetName]` was a wrong guess at reaching back on 2026-09-08.

Used only for the `_name`/title, not `_desc`: every
`_action_notification_desc` in vanilla's diplomacy_l_english.yml
hardcodes `GetPlayer` ("our mutual relations"), which is only accurate
when the player is the actual recipient -- wrong for a genuinely
third-party watched country's action. Kept our own desc text generic
for that reason. Checked every `_name` field for the common action
types (relations, rivalry, embargo, alliance, ...) -- none reference
GetPlayer, so they're safe for both the player-recipient and
third-party-watched cases. A handful of less common ones still do
(`guarantee_independence_action_notification_name`,
`bankroll_action_notification_name`, `raise_payments_*`,
`decrease_payments_*`) -- accepted as a narrow, known wording
inaccuracy (says "our"/"us" for a third-party case that isn't actually
about the player) rather than building per-action-type text overrides
for this small a gap.

Updated both `smart_notifications_diplomatic_action_watched` and
`_quiet`'s `_name` loc in smart_notifications_l_english.yml. Full
comment/history preserved and extended in the loc file itself so the
two earlier (now-superseded) investigations aren't lost. NOT YET
LIVE-TESTED.


## Diplomatic action toast: player-targeted case gets its own message with vanilla's full desc (2026-09-09)

User pushed further, correctly: "it still feels like a weirdly
unspecific message" -- the title fix above wasn't enough, since the
desc ("X has taken a diplomatic action involving Y. Open the Diplomacy
screen for details.") stayed generic and now reads as redundant next to
a specific title.

Checked every `_action_notification_desc` in vanilla's
diplomacy_l_english.yml (not just the relations ones checked earlier):
essentially all of them are written assuming the player is a direct
party to the action ("our mutual relations", "we", "us", GetPlayer
throughout). That's not a generic-engine-text problem to work around --
it's specifically ACCURATE for the one case where the player really is
the recipient, and would be WRONG for a genuinely third-party watched
country's action (says "our relations" about two countries that aren't
the player at all).

So: split the player-is-recipient case into its own dedicated message,
`smart_notifications_diplomatic_action_targeting_player`
(common/messages/00_messages.txt), whose desc uses
`[SCOPE.GetRootScope.GetDiplomaticAction.GetActionNotificationDesc]`
directly -- full vanilla detail (relation values, attitude, obligations,
whatever that action type's real desc contains), since this is exactly
the situation that text was written for. The genuinely-third-party-
watched case still goes through the existing
`smart_notifications_diplomatic_action_watched` with the safe generic
desc, since reusing vanilla's text there would misrepresent an action
the player isn't part of.

common/on_actions/06_smart_notifications_diplomatic_action_filtering.txt
now checks `scope:recipient ?= { is_player = yes }` FIRST (a strict
subset of the watched-check, so it has to come first or it'd never be
reached) and posts the new key; falls through to the existing
watched/quiet branches otherwise. This effectively reintroduces a
player-recipient special case (removed entirely just one fix ago) --
but this time as its own accurate message, not a suppression, so it
can't reintroduce the earlier silent-notification regression.


## Confirmed live; watched-but-not-player diplomatic action toast demoted to feed (2026-09-09)

Player-targeted case confirmed working: user saw real vanilla-quality
wording and detail in a live session ("it seems that they all triggered
well now, with the format used by the native notifs"). Bumped to 0.36
and tagged (per this feature being genuinely new and confirmed working).

User then pushed on a second point: "the lighter generic wording
doesn't make things less spammy, it just is generic" -- correctly
separating two different problems the earlier fixes conflated
(wording quality vs. interruption frequency). Asked directly whether
the watched-but-not-player case (a watched great power acting on some
unwatched minor, e.g.) is even supposed to toast, since they hadn't
consciously noticed it firing.

Checked debug.log rather than guessing: confirmed 13 fires in the
current session alone (Spain -> Philippines, Ottoman Empire -> Fezzan,
Portugal -> Gaza, Brunei -> Bulungan, US -> Tokugawa Shogunate, ...) --
genuinely firing often, just blending into other toast traffic
unnoticed. User's call once confirmed: suppress it. Demoted
`smart_notifications_diplomatic_action_watched` from `notification_type
= toast` to `feed` in common/messages/00_messages.txt -- keeps the
accurate specific title/detail (now genuinely useful to skim in the
feed log) without popping a toast for routine third-party diplomacy.
The player-targeted case
(`smart_notifications_diplomatic_action_targeting_player`) is
unaffected -- still toasts, since that's the case actually worth
interrupting for. NOT YET LIVE-TESTED (the demotion itself).


## Player-targeted diplomatic actions: routine relations changes demoted, real type-discrimination found (2026-09-09)

Live example surfaced the question: "i got toast notified that aceh was
improving relations despite it not being in my watchlist, why?" Checked
debug.log -- confirmed expected (Aceh was the actor, player was
recipient, so it went through the always-toasts targeting_player path,
correctly independent of watchlist).

User then pushed back harder: shouldn't a low-stakes routine action
(improve relations) get the same feed-tier treatment we just gave the
watched-but-not-player case, rather than always toasting just because
it's aimed at the player? I initially answered by asking the user to
choose between "keep all player-targeted actions as toast" or "demote
ALL of them to feed," on the claimed basis that script can't
distinguish action types. User correctly rejected that framing:
"aren't we able to see the type of action? improve relation is very
different from starting a diplo play."

That claim was wrong, and re-checking properly (Documents/.../docs/triggers.log
this time, not assumption) found it: `has_diplomatic_pact = { who = X
type = Y is_initiator = yes/no }` -- a real, `country`-scoped trigger,
already used by vanilla's own increase_relations/damage_relations
definitions in common/diplomatic_actions/00_relations_actions.txt. This
lets us check, from `scope:actor`, whether the actor now holds an
increase_relations or damage_relations pact with `scope:recipient`
specifically. (Diplomatic Plays were never actually part of this gap --
those already go through a completely separate, already-correctly-
elevated on_action from earlier phases; the user's example was slightly
off but the underlying point -- routine relations changes shouldn't
toast -- was right.)

Implemented in
common/on_actions/06_smart_notifications_diplomatic_action_filtering.txt:
within the player-targeted branch, check for an increase_relations/
damage_relations pact (with `is_initiator = yes` to tie it to THIS
actor, not some unrelated pre-existing pact of that type) and route to
a new feed-tier message,
`smart_notifications_diplomatic_action_targeting_player_routine`
(common/messages/00_messages.txt), with the exact same full accurate
text as the toast version -- just not interrupting. Everything else
targeting the player (rivalry, subjugation, embargo, autonomy changes,
alliance offers, ...) still toasts, since `has_diplomatic_pact` only
matches those two specific types.


## Routine-relations demotion narrowed: only applies to an unwatched actor (2026-09-09)

User clarified the rule further: the routine-relations-targeting-player
demotion should only kick in when the ACTOR isn't on the watchlist --
"if it's an important notification type (like start a diplo play)
targeting you it should toast regardless of the country being in the
watchlist." A watched country's action against you is worth knowing
even when it's "only" a relations change, precisely because you're
tracking that country specifically -- the demotion was only ever meant
for the "random unwatched minor doing something routine" case. Added
`scope:actor ?= { NOT = { smart_notifications_is_watched = yes } }` to
the existing has_diplomatic_pact check in
06_smart_notifications_diplomatic_action_filtering.txt, so a watched
actor always falls through to the full toast regardless of action type.

Noted for the user but didn't need a code change: Diplomatic Plays
(their "start a diplo play" example) were never actually routed through
this file at all -- they fire through a completely separate on_action,
already elevated appropriately from earlier phases, so they were never
affected by any of this session's demotions either way.


## Full toast/feed/popup table given to the user; Subject Released (watched) raised to toast (2026-09-09)

Gave the user a complete, code-verified table of every notification tier
across both the diplomatic-action and diplomatic-play systems (all 12
keys). Surfaced an inconsistency worth a decision: unlike every other
diplo-play event, `smart_notifications_diplo_play_subject_released_watched`
was `feed`, not `toast`, even for a watched participant. User's call:
raise it to `toast` -- "we can put to toast when watched if it's just
changing a small setting." Changed in common/messages/00_messages.txt.
The unwatched sibling stays `none` (fully muted), unaffected. NOT YET
LIVE-TESTED.

## RESOLVED: routine-relations demotion never actually fires (2026-09-09)

User: "i got toasted for relationship improvement by siam who isn't on
my watch list." Checked debug.log across two rotated sessions --
confirmed real: Siam -> Great Qing (player), `role=actor|watched=no`
(genuinely not watched, matching the user's report), yet the decision
still posted `smart_notifications_diplomatic_action_targeting_player`
(the full toast), not `..._targeting_player_routine`. The
`has_diplomatic_pact = { who = scope:recipient type = increase_relations
is_initiator = yes }` check added earlier today has never once matched
in two real sessions -- the routine-demotion feature has never actually
worked despite passing validate_syntax.py cleanly both times.

Two live hypotheses, unconfirmed:
1. Timing -- the diplomatic_pact object may not be registered in
   gamestate yet at the exact instant `on_diplomatic_action` fires (same
   class of "not bound yet" issue found earlier this session with
   diplo-play's `scope:target`).
2. `is_initiator = yes` semantics -- the trigger doc's phrasing ("checks
   to see if scope country is the original initiator/target of the
   pact") is ambiguous about which value means what; vanilla's own only
   confirmed usage (common/diplomatic_actions/00_relations_actions.txt)
   never uses this parameter at all, just a bare `has_diplomatic_pact =
   { who = X type = Y }`.

Added TEMPORARY diagnostic instrumentation in
06_smart_notifications_diplomatic_action_filtering.txt (SNW_PACT_PROBE
debug_log lines) -- breaks out increase_relations/damage_relations, each
WITH and WITHOUT is_initiator, into 4 independent results per firing, so
the next test conclusively shows which variant (if any) actually
matches, instead of guessing again.

**RESULT: all 4 combinations returned "no" in a real firing (Bulungan ->
Great Qing, confirmed watched=no).** Dropping `is_initiator` entirely
made no difference, ruling out the semantics theory. This left two live
hypotheses: (a) timing -- the pact isn't registered in gamestate yet at
the exact instant `on_diplomatic_action` fires, or (b) the user's own
hypothesis -- these one-sided relations actions never create a
`has_diplomatic_pact`-queryable pact object at all, ever.

Re-checked vanilla's own code for evidence: `increase_relations`'s own
`possible` block (common/diplomatic_actions/00_relations_actions.txt)
uses `NOT = { has_diplomatic_pact = { who = scope:target_country type =
damage_relations } } }` to block proposing Increase Relations while a
Decrease Relations pact is already active -- this only works if
`has_diplomatic_pact` CAN reliably detect an established one-sided
relations pact, which argues against hypothesis (b) and for (a) (timing
-- works for OLD pacts, not the one just created by THIS action).

User's call: keep pushing rather than revert. Added a NEW temporary
diagnostic to distinguish (a) from (b) conclusively --
common/on_actions/04_smart_notifications_probes.txt's
`smart_notifications_probe_pact_sweep`, hooked to
`on_monthly_pulse_country`: from the player's own scope, sweeps EVERY
other country monthly checking `has_diplomatic_pact = { who = ROOT type
= increase_relations/damage_relations }` (both with and without
`is_initiator`), logging any match via SNW_PACT_SWEEP. If Siam or
Bulungan (or any country already confirmed to have fired this
notification) EVER shows up on a LATER pulse, that confirms (a) --
pure timing gap, fixable by deferring the check. If neither ever shows
up despite clearly having taken such an action, that's strong evidence
for (b) -- these actions never register as a queryable pact at all, and
type-based filtering for this case isn't achievable this way.

NOT YET LIVE-TESTED. A prompt for continuing this specific investigation
in a fresh Opus 5 session (per the user's request) is at the end of this
file.


## RESOLUTION (2026-09-09, evening): hypothesis 1 -- timing. Feature removed.

Settled by a live test with the two competing theories instrumented
separately. **Hypothesis 1 (timing) is correct**; hypothesis 2
(`is_initiator` semantics) and the user's own hypothesis (one-sided
pacts never create a queryable pact object) are both ruled out.

Nawanagar -> Great Qing, Improve Relations, 17 Jan 1836. At the firing
instant all four `has_diplomatic_pact` variants said no, AND an
`every_scope_diplomatic_pact` walk of Nawanagar's own pacts found two
pacts of which neither was `increase_relations`. On the next monthly
pulse the identical query returned **yes** for Nawanagar. Tibet
(`damage_relations`) and Selangor (`increase_relations`, the action the
user was toasted for in this test) reproduced it exactly. The pact
object simply is not in gamestate yet when `on_diplomatic_action` runs.

One-sided pacts DO create queryable pact objects -- both relations types
showed up by name in the sweep -- so `is_two_sided_pact = no` was never
the problem.

**No replacement signal exists at that instant**, and this is now
established rather than assumed: zero triggers and zero effects in the
game's own script_docs support `diplomatic_action` scope, no event target
leads out of it or into a `diplomatic_pact`, and the only bound scopes
are `actor`, `recipient` and `notification_target` (all countries).
`debug_log_scopes = yes` confirmed all of this in one line -- worth
reaching for first, next time a scope's contents are in question.

Reverted to a plain toast for every diplomatic action targeting the
player, i.e. the state before the attempt, and deleted the dead
`..._targeting_player_routine` message key, group and loc (never present
in any tagged version, so no player ever saw it). Both temporary
diagnostics (SNW_PACT_PROBE, SNW_PACT_SWEEP) deleted. Full write-up in
docs/engine-notes.md § The pact for a diplomatic action does not exist
yet, and in the header comment of
06_smart_notifications_diplomatic_action_filtering.txt.

**If the "random minor shouldn't toast like something consequential"
complaint comes back**, the direction to take is a property of the
ACTOR -- rank, `has_diplomatic_relevance`, country type -- all readable
at that instant, rather than a property of the action, which is not.
Not built: it would demote a rivalry or embargo from a minor too, which
is a product call the user hasn't been asked yet.

**One incidental bug found and NOT fixed** (out of scope, worth its own
pass): `SNW_TAX_TOAST`'s two debug_log lines in
10_smart_notifications_taxation_deficit_toast.txt are silently failing
with "Data error in loc string" on `[prev.GetState.GetName]` -- lowercase
`prev` is effect syntax, invalid in dynamic text, and `.GetName` is the
already-documented wrong accessor. That instrumentation is currently
blind.


## Handoff prompt: routine-relations demotion investigation (2026-09-09)

Copy-pasted verbatim into a new session per the user's request.
**Closed out 2026-09-09** -- see the RESOLUTION section directly above
for the answer. Kept only as a record of what the question looked like
before it was answered.

```
I'm working on a Victoria 3 mod, "Smart Notifications"
(C:\Users\damie\Dropbox\_Damien\Perso et tech\Claude-code\Victoria-smart-notifs,
git remote dcoullon/victoria3-smart-notifications). Read CLAUDE.md and
docs/engine-notes.md first -- they document hard-won engine constraints
(dynamic-text vs effect/trigger syntax are two separate function tables,
BOM requirements, known mistake patterns, etc.) that matter for this bug.

CURRENT BUG: a feature added earlier today demotes routine "Increase/
Decrease Relations" diplomatic actions targeting the player from a toast
to a feed-tier notification, UNLESS the acting country is on the
player's Watchlist (in which case it should still toast). The mechanism
-- checking `has_diplomatic_pact = { who = scope:recipient type =
increase_relations/damage_relations is_initiator = yes/no }` from
scope:actor, in
common/on_actions/06_smart_notifications_diplomatic_action_filtering.txt
-- has NEVER successfully matched in two real, confirmed test firings
(Siam -> Great Qing, Bulungan -> Great Qing, both genuinely relations-
improvement actions, both confirmed `watched=no` via a separate
diagnostic). All 4 combinations (increase/damage_relations x with/
without is_initiator) returned "no" every time -- see SNW_PACT_PROBE
debug_log lines already in that file (search for that tag).

Two live hypotheses:
(a) TIMING -- the diplomatic_pact object for the just-fired action isn't
    registered in gamestate yet at the exact instant `on_diplomatic_action`
    fires. Evidence FOR: vanilla's own increase_relations definition
    (common/diplomatic_actions/00_relations_actions.txt) uses
    `NOT = { has_diplomatic_pact = { who = scope:target_country
    type = damage_relations } } }` in its own `possible` block to check
    for an EXISTING (already-established) pact before allowing a NEW
    action -- meaning has_diplomatic_pact DOES work for this exact pact
    type in general, just apparently not for the one JUST created.
(b) The user's own hypothesis -- these one-sided relations actions
    (`is_two_sided_pact = no` in their definition) never create a
    `has_diplomatic_pact`-queryable pact object at all, ever, regardless
    of timing.

A diagnostic to distinguish these was just added and pushed
(common/on_actions/04_smart_notifications_probes.txt,
`smart_notifications_probe_pact_sweep`, hooked to
`on_monthly_pulse_country`): from the player's own scope, sweeps every
other country monthly, logging (via debug_log tagged SNW_PACT_SWEEP)
any country that shows `has_diplomatic_pact = { who = ROOT type =
increase_relations/damage_relations }` true, with and without
is_initiator. NOT YET LIVE-TESTED -- the user needs to relaunch
Victoria 3 (mod files only load at launch) and play at least a few
in-game months after triggering another relations-change action against
themselves (Great Qing, in the current test save), then report back
what SNW_PACT_SWEEP shows in
`C:\Users\damie\Documents\Paradox Interactive\Victoria 3\logs\debug.log`.

YOUR TASK: guide the user through running this test, read the resulting
debug.log yourself (same path pattern used throughout this project --
grep for the relevant SNW_* tags, never dump the whole log into
context), and determine which hypothesis is correct:
- If (a): a country that already fired the notification eventually shows
  up in a LATER sweep. Fix: since we can't retroactively un-toast an
  already-shown notification, and delaying the notification itself would
  be worse UX, consider whether the routine-relations demotion feature
  is worth keeping at all, or whether a different signal exists (re-scan
  vanilla script_docs / triggers.log / effects.log the same way this
  session did for `has_diplomatic_pact` and `is_diplomatic_action_type`
  -- there may be a scope reachable at THIS exact moment, before the
  pact commits, that also carries the action type).
- If (b): no country ever shows up despite clearly having taken such
  actions. This rules out type-based filtering for this specific case
  entirely via any pact-query mechanism. Recommend reverting the
  routine-relations demotion to always-toast (the state before today's
  attempt) -- explain this clearly to the user with the evidence, don't
  just silently revert.

Also worth deleting once resolved: the temporary SNW_PACT_PROBE
diagnostic already in 06_smart_notifications_diplomatic_action_filtering.txt
and the SNW_PACT_SWEEP one in 04_smart_notifications_probes.txt, per this
project's own convention of removing temporary diagnostics once their
question is answered (see TODO.md's many prior examples of this pattern).
Run `python tools/validate_syntax.py` after any change, and follow
CLAUDE.md's git rules (no AI/attribution lines in commits, version bump
only for confirmed-working new features, tag every version bump).
```

## Phase 4 — Shorten Message Settings row labels (SHIPPED 2026-09-08)

*(Moved out of TODO.md 2026-09-15; the split on 09-15 had kept this one shipped item in the live file by mistake.)*

- [x] **Shorten Message Settings row labels + re-tag mod-created
      notifications — SHIPPED 2026-09-08.** Flagged 2026-09-07 per the
      user's screenshot: our group labels (e.g. "Diplomatic Play Started,
      Watched Country Inv…") truncated hard in the list's fixed-width
      column, and the old trailing `" (Smart Notifications)"` suffix
      (per CLAUDE.md's tagging convention) made it worse — it was exactly
      the part that got cut off. **Extended 2026-09-08 per the user:**
      wanted a way to tell "this is the mod" at a glance without such
      long names. **Fix:** the tagging convention changed from a trailing
      `" (Smart Notifications)"` suffix to a short leading `"(SN) "`
      prefix on every mod-created group/alert label (13 labels in
      [smart_notifications_l_english.yml](../../smart_notifications/localization/english/smart_notifications_l_english.yml)) —
      visible even when truncated, and 5 characters instead of 22.
      CLAUDE.md and engine-notes.md updated to document the revised
      convention for future additions.
      **Grouping itself: user first said our rows already sit at the
      bottom of the default list (no active work needed); corrected the
      same day** after checking whether "Law Imposed"/"Colonial Claim
      Granted" were ours (confirmed via grep: no, 100% vanilla, untouched)
      — those sit after our rows, so we're grouped together but not
      strictly last. Not pursuing further — the short prefix already
      solves the actual problem (telling rows apart at a glance) without
      needing exact positioning.
      **GUI-level section divider — investigated, not pursued:** the
      list is populated from a native datamodel
      (`MessageSettingsWindow.GetNotificationSettingsItems` per
      [gui/message_settings.gui](../../smart_notifications/gui/message_settings.gui)), with an
      existing "sort by Notification Type" column the player can already
      click — but the DEFAULT (unsorted) order was never confirmed (could
      be alphabetical, native registration order, file definition order,
      or something else), and a real section-divider would need actual
      GUI work. Don't attempt without
      first confirming what's realistic — this list's sort/grouping
      behavior hasn't been investigated at all yet.
