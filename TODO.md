# Victoria 3 — Smart Notifications & Watchlist: Roadmap

The living backlog. **Forward-looking only**: what is planned, in progress, or
an open question. Nothing here is a record of what happened.

- What shipped, per version, player-facing: [CHANGELOG.md](CHANGELOG.md).
- How past problems were solved and what the engine actually does:
  [docs/engine-notes.md](docs/engine-notes.md) (it has a table of contents).
- Session-by-session working notes from 2026-09-05..09-09, kept because several
  carry evidence that is not recorded anywhere else:
  [docs/archive/2026-09-session-log.md](docs/archive/2026-09-session-log.md).

## How to use this file

- Each unchecked box is planned, not yet shipped. Status markers: `[ ]` not
  started · `[~]` in progress / partially done · `[x]` done.
- **When an item ships: check it off, add a CHANGELOG entry, and move the
  working notes to the archive.** Closed narrative does not stay here. This
  file was 4,034 lines on 2026-09-15, 55% of it dated session logs, which made
  "what should we do next?" impossible to answer without reading the archive
  first. The split brought it to ~1,090; it should shrink as items close, not
  grow.
- **Every open item states its acceptance criteria** — the observable
  condition that decides it, in the form "when Y happens, X appears in
  <tier>, and nothing appears for Z" — plus **how it will be checked**: a
  static check in `tools/check_references.py`, a `SNW_*` line read with
  `python tools/scan_logs.py`, or, only if neither can do it, a live look.
  See CLAUDE.md § 5 Playtest Protocol. An item without criteria is not ready
  to be worked on.

## Distribution & platform scope

- **Steam is the sole distribution target** for now (Steam Workshop / the
  Paradox Mods integration Steam surfaces for Victoria 3) — not a standalone
  Paradox Mods upload, not Nexus, etc.
- **Single-player only.** Multiplayer compatibility is explicitly not a goal.
  `metadata.json` sets `multiplayer_synchronized: false` accordingly.

## Current state — the Watchlist

*(Written 2026-09-09; (c) and (d) refreshed 2026-09-15. The expectations
half is superseded by [docs/watchlist-spec.md](docs/watchlist-spec.md), the
behavioural spec agreed with the user family by family — that file is what the
code answers to, and it is still DRAFT: nothing is built against it until the
user says OK explicitly.)*

> **2026-09-09, later:** the expectations half of this section has been
> superseded by [docs/watchlist-spec.md](docs/watchlist-spec.md), the
> behavioural spec agreed with the user family by family. That file is the
> reference the code answers to; **it is still DRAFT and nothing is built
> against it until the user says "OK" explicitly.** The state-and-gaps half
> below is still accurate as a description of what exists today.


Written as the starting point for the next session, at the user's
request. Three questions in order: what is the Watchlist *for*, what does
it actually do today, and what stands between the two.

---

### 1. Expectations — what the country selector is for

The user's own formulation, which is the spec:

> The spirit of the country selector is that toasts should contain all
> important actions towards you or involving a watched country, and only
> that.

Two axes, and a notification needs **both** to earn a toast:

| | aimed at you / a watched country | aimed at anyone else |
|---|---|---|
| **important action** | **toast** | feed |
| **routine action** (e.g. relations changes) | feed | feed |

One confirmed exception: a **watched** country's *routine* action toward
you still toasts. Being watched outranks the action being routine — you
are tracking that country specifically.

Implied but worth stating, since it has been violated twice by accident:

- **Never silently drop something aimed at the player.** Over-notifying
  is the safe direction to fail in.
- **"Involving" is not symmetric.** A watched country *acting on* a
  stranger is not the same event as a watched country *being acted on*.
  Only the second is aimed at something you care about.
- The three tiers are `popup` > `toast` > `feed`, plus `none`. The feed
  is not deletion — it's the log you can skim on purpose.

---

### 2. What actually works today

**The Watchlist itself** — selection UI, persistence, `is_player = yes`
baked into `smart_notifications_is_watched` so anything about the player
counts as watched automatically. Confirmed working live, Phase 3.

**Diplomatic plays** (`03_smart_notifications_relational_notifications.txt`),
four families, each split watched/unwatched:

| event | watched | unwatched |
|---|---|---|
| play start (third party) | toast | feed |
| join side | toast | feed |
| war start | **popup** | toast |
| subject released | toast | none |

**Diplomatic actions** (`06_..._diplomatic_action_filtering.txt`) — the
aimed-at axis, rebuilt 2026-09-09 evening:

- aimed at you → toast
- aimed at a watched country → toast
- aimed at anyone else → feed, **even when the actor is watched**

Measured on one real session of 271 diplomatic actions: 233 quiet, 38
reaching a toast.

**Not watchlist-gated at all** (deliberately — they're about *your* own
country, so the Watchlist has no bearing): the law-ready alert family
(138 generated per-law keys), the taxation deficit toast, truce expiry.

---

### 3. What's missing

**(a) The importance axis does not exist.** This is the big one. Every
action aimed at you or a watched country toasts, routine or not, so a
minor nudging relations with you interrupts exactly like a subjugation
demand. Three mechanisms tried on 2026-09-09, each ruled out by direct
evidence, not by inference:

1. Query the pact the action creates — it isn't in gamestate yet at that
   instant (three countries proved it via a later monthly sweep).
2. Ask the action object — zero triggers and zero effects support
   `diplomatic_action` scope; no event target leads out of it.
3. Have the action flag its target from its own definition, via the
   `effect = {}` block the game's own schema doc documents — the parser
   rejects the key (`Unexpected token: effect`).

Both write-ups: `docs/engine-notes.md` §§ *The pact for a diplomatic
action does not exist yet* and *A `.md` schema doc is not proof a key
parses*. **Do not re-attempt these three without new information.**

The only untried axis is a property of the **actor** (rank,
`has_diplomatic_relevance`, `is_country_type`), all readable at the right
instant. It approximates the rule rather than implementing it — it judges
the sender, not the message, so a small country declaring a *rivalry* on
you would be quieted along with the relations nudges. **Needs a product
call from the user before anyone builds it.**

**(b) Only two event families are watchlist-aware.** Diplomatic plays and
diplomatic actions. Everything else in the game either always fires or is
muted globally. Whether that's a gap or the right scope is an open
question — worth listing which other families *could* be watchlist-gated
before deciding.

**(c) v0.40 is built but not published, and two of its branches are
unverified.** Live on the Workshop is **v0.39**; the repo is at v0.40 (event
context). Before it can be uploaded, the two never-observed rendering branches
in § *UNVERIFIED before the next release* have to be confirmed. Packaging is
`python tools/package_release.py`, and the upload comes from
`smart_notifications_release`, never the dev junction.

*(The 2026-09-09 version of this note said the live build predated the
actor/recipient split. That shipped in 0.38, and the diplomatic-play gap it
exposed was fixed in 0.39 — both are live. Detail in the archive.)*

**(d) The blind tax-toast instrumentation is fixed.** `SNW_TAX_TOAST`'s
`debug_log` lines used `[prev.GetState.GetName]`, which is effect syntax in a
dynamic-text position plus the wrong accessor, so they logged nothing usable.
They now log `date=[TimeKeeper.GetCurrentDate.GetString]` and are readable with
`python tools/scan_logs.py`.

---

### 4. Next up

1. **Get the product call on actor-based filtering** (§3a). It is the only
   remaining route to the importance axis, and it is a product decision, not
   an engineering one — it judges the sender rather than the message, so a
   minor power declaring a rivalry on you would be quieted along with its
   relations nudges. Nothing should be built until the user rules on that
   trade-off.
2. **Confirm the two unverified v0.40 branches**, then bump, tag and upload
   (§ *UNVERIFIED before the next release*). Both need a live run; batch them
   with anything else awaiting a launch, per CLAUDE.md § 5.
3. **Decide whether families beyond diplomatic plays and actions should be
   watchlist-gated** (§3b) — list the candidates before deciding, rather than
   gating them one at a time as they come up.

## Open questions

Each carries its acceptance criteria and how it gets checked, per CLAUDE.md
§ 5. Both were previously scattered through the session logs — the
watchlist/tag question alone appeared in three places, worded three different
ways and answered in none of them.

### A watched country that becomes a NEW country loses its watch

*(Merged 2026-09-15 from three duplicate entries: "KNOWN GAP" 2026-09-10,
Phase 4's "Country renaming caveat" 2026-09-05, and an "Open item" raised by
an external report 2026-09-09.)*

Raised by the user 2026-09-10 ("what happens when a country in our watchlist
changes names, e.g. after a revolution").

**What happens today.** The Watchlist is stored as variables on the country
object itself (`watched_manually`, `watched_via_great_power`,
`watched_via_neighbor`, `watched_via_rival` — see
`common/scripted_triggers/00_smart_notifications_triggers.txt`). So:

- A country that merely **changes name** keeps the same object and stays
  watched. Fine.
- A revolution or formation that produces a **genuinely new country** (a new
  tag) produces a new object with no variables, so **the watch is silently
  lost**. Nothing warns the player; the country simply stops appearing in the
  Watched list and its events go quiet.

**Still unknown, and it decides everything else:** does Victoria 3 preserve
country-scope variables across a `change_country_definition`-style transition
(Prussia to German Empire, Ottomans to Turkey), or reset them? No answer found
in `effects.log`. Outright annexation needs no handling — the variable ceases
to exist with the country, which is correct.

**Acceptance criteria.** Watchlist a country that will reform. After it
reforms: it is still listed in the Watchlist UI, and a diplomatic play it
opens against a third party still reaches a toast. Nothing else about the
Watchlist changes — an unwatched country that reforms stays unwatched.

**How it gets checked.** Not statically checkable — whether the engine carries
a scope variable across a tag change is engine behaviour, not repo state. It
needs one live run, so **batch it**: the same run should also carry the
instrumentation for at least two other open questions (CLAUDE.md § 5). Add a
`SNW_TAGCHANGE|` line logging the four flags on both the predecessor and
successor at the moment the transition fires, so the run answers "do variables
survive" and "which flags survive" together rather than one at a time.

**If variables do not survive**, the shape of a fix: hook whatever on_action
fires when a country is formed or a revolution succeeds, and carry the four
flags across from the predecessor. That depends on such a hook exposing both
the old and new country in scope at once — if it only gives one side, this is
not buildable, the same way several other things in this mod turned out not to
be. Practical impact if unfixable is mild (the player silently stops being
notified about a country they cared about; no error, no crash) but it is a
trust problem, not just a missing feature, and worth resolving before the next
release.


### Is the law-readiness toast triggering correctly?

2026-09-09: the user confirmed both the alert and the toast fired correctly in
one run — previously only the alert had been seen consistently. The
level-vs-edge-triggering explanation for the toast's rarity (archive, *Toast
rarity investigated*) looks right, but that is **one** positive data point with
the new diagnostic logging in place. Do not close this from a single success.

**Acceptance criteria.** Across several campaigns: a `SNW_LAW_TOAST|fired`
line appears exactly once per law becoming ready, each `fired` is preceded by
a `|reset`, and no `|pulse` run produces two `fired` lines for the same law
without an intervening `|reset`. Zero related lines in `error.log`.

**How it gets checked.** `python tools/scan_logs.py` after any session that
was going to happen anyway — this one costs no dedicated launch, so it should
ride along with every other playtest until there is enough evidence. When it
holds across several campaigns, remove the temporary instrumentation and note
the conclusion in engine-notes.

## WANTED, blocked on the engine: attitude changes for watched countries only

Per the user, 2026-09-09. Attitude changes toward the player
(`country_attitude_changed` / `_improved` / `_worsened`) are going to
`feed` (see [docs/watchlist-spec.md](docs/watchlist-spec.md) F6), but what
the user actually wants is a **toast when a *watched* country's attitude
toward them shifts**, and nothing for anyone else.

**Blocked purely on a missing hook, not on the design.** No on_action posts
these notifications — they are engine-fired, confirmed by finding zero
references to the keys anywhere in vanilla `common/` outside the message
definitions themselves. With no hook there is no place to test
`smart_notifications_is_watched`, so the tier is global across every
country and toasting it would interrupt for the whole map.

**Revisit if:** a game patch adds an on_action for attitude changes (check
a fresh `script_docs` dump after any major update), or another event that
reliably coincides with an attitude shift turns out to be hookable and
carries the country in scope.

## Minor: suppress the feed entry for a war goal YOU add

Raised by the user 2026-09-10, explicitly parked as low priority: "don't tell
me about things I'm doing while I'm doing it."

**Not currently ours.** The mod no longer touches war goals at all -- the
family was removed on 2026-09-10 and `wargoal_added`/`wargoal_removed` sit at
the base game's own `feed`. So the entry the user sees when they add a goal is
vanilla's, at vanilla's tier.

**What it would cost** to suppress: mute vanilla's key, add one mod key at
`feed`, add an on_action that posts it only when `scope:actor` is not the
player. That is one more Message Settings row (19 -> 20), one more hook, and a
mute -- and mutes are what leave stale settings on players who already
installed, so it also needs a line in the release notes.

**Open question if it is built:** should only the goals YOU add vanish, with
other participants' goals still reaching the feed? That is the version worth
building; a blanket mute would also hide other countries' goals, which the user
said are good where they are.

**Judgement at the time:** a feed entry is the log rather than an interruption,
and your own actions appearing in the log is arguably correct. Left alone in
favour of publishing.

## Phase 4 — Relational Notification Engine (Capstone) (target: v1.0.0)

*(The two shipped items of this phase — on-action interception and the
Message Settings relabel — moved to the archive 2026-09-15; the
country-renaming caveat moved to Open questions. What remains is unfinished.)*

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

- [~] **Third-party notification filtering — the 3 Diplomatic-Play-rooted
      keys BUILT 2026-09-07, two real bugs found and fixed the same day via
      the user's first live playtest, `diplo_play_subject_released` still
      not yet confirmed.** Initial build muted vanilla's
      `diplo_play_start_third_party_notification`,
      `diplo_play_war_start_third_party_notification`, and
      `diplo_play_subject_released_notification` groups (all `none` in
      `00_messages.txt`), replacing each with its own separate watched/quiet
      pair. **Both `start` and `war_start` broke on first real test:**
      1. **Duplicate notifications** — `SNW_FILTER` log lines with matching
         timestamps/actor/target proved the "primary" event
         (`on_diplo_play_start`/inline in `on_diplo_play_war_start`) and the
         new "third party" one both fired for the same play, to the same
         viewer, with near-identical text. They aren't two different
         audiences as assumed going in — `smart_notifications_is_watched`
         already ORs in `is_player = yes`
         ([00_smart_notifications_triggers.txt](common/scripted_triggers/00_smart_notifications_triggers.txt)),
         so a single channel per event already covers "the player is
         involved."
      2. **Blank target text, `on_diplo_play_start` only** — the same log
         showed `target=` resolving empty specifically for that one
         on_action (every other diplo-play on_action resolved it fine).
         Matches vanilla's own loc for `diplo_play_start_notification`,
         which never names a target either ("...against us") — scope:target
         genuinely isn't bound yet at the instant a play starts.
      **Fix:** consolidated to one notification per event, always posted
      from whichever on_action's scopes are confirmed reliable —
      `on_diplo_play_start` is no longer hooked at all; the "play started"
      notification now posts from `on_diplo_play_start_third_party` instead
      (reusing the original `smart_notifications_diplo_play_start_watched/_quiet`
      toast/feed keys, not a separate third-party pair). `on_diplo_play_war_start`
      keeps its own hook but no longer also posts a third-party pair. The
      now-redundant `smart_notifications_diplo_play_start_third_party_watched/_quiet`
      and `_war_start_third_party_watched/_quiet` message keys/loc were
      deleted; `diplo_play_start_third_party_notification`/
      `diplo_play_war_start_third_party_notification` (vanilla) stay muted
      permanently with no replacement of their own. Full writeup in
      [03_smart_notifications_relational_notifications.txt](common/on_actions/03_smart_notifications_relational_notifications.txt)'s
      header comment. `diplo_play_subject_released` has no primary-key
      sibling (no duplication risk architecturally) and kept its own
      watched/quiet pair unchanged — **still needs its own in-game
      confirmation**, hasn't fired yet in any tested session. **The
      remaining ~15 keys (Country-rooted and Diplomatic-Action/Pact-rooted)
      are still blocked/unbuilt** — see the inventory below, unchanged.
      Cross-referenced every
      `post_notification` in vanilla's `00_code_on_actions.txt` (99 have a
      moddable hook; the rest are native engine code and can never be
      filtered) against this mod's own message file. Findings:
      - **Most feed-level notifications are about the PLAYER**
        (`our_supply_ships_raided`, `heir_born_notification`,
        `journal_entry_activated`, `obligation_owed_to_us_expired`...).
        These must never be watchlist-filtered — the player is the
        subject by definition. Filtering them would be a bug.
      - **The genuinely third-party set is ~18 keys**, split by how hard
        they are to filter, which comes down entirely to the on_action's
        root scope:
        - *Root = Diplomatic Play — filterable today* (participant roster
          reachable via `any_scope_play_involved`, already proven in
          `03_smart_notifications_relational_notifications.txt`):
          `diplo_play_start_third_party_notification`,
          `diplo_play_war_start_third_party_notification`,
          `diplo_play_subject_released_notification`.
        - *Root = Country — probably filterable*, but the root is the
          country being TOLD, so the relational question needs the other
          side, which isn't obviously reachable:
          `peace_agreement_signed_non_participant`,
          `start`/`stop_supporting_unification`,
          `unification_candidate_added`/`_removed`,
          `spreading_technology_notification`.
        - *Root = Diplomatic Action / Diplomatic Pact — BLOCKED*: the 6
          `diplomatic_proposal_third_party_*` keys and
          `diplomatic_pact_third_party_auto_break_notification`. The
          `script_docs` event_targets dump documents **no scope links out
          of a diplomatic_action at all**, and we already have a
          confirmed runtime error from guessing here (`is_player trigger
          [ Wrong scope for trigger: diplomatic_action, expected
          country ]`).
        - *Root = Culture*: `national_awakening_started` (scope:region,
          scope:culture) — no country bound directly.
      - **Probes shipped** to resolve the blocked ones empirically:
        [04_smart_notifications_probes.txt](common/on_actions/04_smart_notifications_probes.txt)
        logs `SNW_PROBE|` lines naming every scope that actually exists on
        each of these on_actions, guarded with `?=` so a missing scope is
        skipped rather than erroring. Delete once the scope names are
        known and the filtering is built.
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
      [smart_notifications_l_english.yml](localization/english/smart_notifications_l_english.yml)) —
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
      [gui/message_settings.gui](gui/message_settings.gui)), with an
      existing "sort by Notification Type" column the player can already
      click — but the DEFAULT (unsorted) order was never confirmed (could
      be alphabetical, native registration order, file definition order,
      or something else), and a real section-divider would need actual
      GUI work. Don't attempt without
      first confirming what's realistic — this list's sort/grouping
      behavior hasn't been investigated at all yet.
- [ ] **Visually distinguish elevated (watched) notifications — parked
      2026-09-07 per the user until the watchlist selector and the base
      filtering changes are confirmed working.** Per-message presentation
      levers confirmed available in `common/messages/`: `color`
      (`good`/`neutral`/`bad` — `bad` renders red, the closest thing to
      the user's "border it in red" idea), `texture` (a distinct icon),
      and `on_created_soundeffect` (a distinct sound). Cheap to add to the
      `_watched` message variants once the rest is stable; deliberately
      not built yet to avoid tuning presentation on top of behaviour that
      is still being fixed.
- [ ] **Auto-pin diplomatic plays involving watched countries in the
      "Ongoing Diplomatic Plays" outliner — requested 2026-09-08, longer
      term, real blocker found, not scoped for now.** The user's ask: a
      play genuinely involving a watched country should show in that
      right-side widget automatically, the same way it already
      auto-shows for plays the player is a committed participant of.
      Investigated the mechanism: a play shows there only if
      `DiplomaticPlay.IsPinnedInOutliner` is true (confirmed in
      [gui/outliner_ongoing_types.gui](gui/outliner_ongoing_types.gui)),
      toggled today only via the star icon in
      [gui/diplomatic_play_panel.gui](gui/diplomatic_play_panel.gui)
      (`onclick = "[DiplomaticPlay.TogglePinInOutliner]"`). **Real
      blocker:** `TogglePinInOutliner`/`IsPinnedInOutliner` are GUI-only —
      confirmed via an exhaustive grep of the game's own `effects.log`
      and `triggers.log`, zero hits for either — there is no
      script-callable effect to set this from an on_action the way we've
      set everything else in this mod. This matches the exact same wall
      Phase 3 hit and gave up on for the country-panel pin button
      (`Country.TogglePinInOutliner`, same GUI-only pattern, see the
      "Country Panel Bookmark Button — dropped" entry under Phase 3
      above). Not automatically ruled impossible — a scripted_gui might
      be able to invoke a GUI-scope function the way
      `watchlist_sgui.txt` does for the Watchlist checkbox, but that
      pattern is GUI-click-triggers-script, the opposite direction of
      what's needed here (script-event-triggers-GUI-function) — genuinely
      unresearched, don't assume it's the same trick. Real workaround
      available to the player today, no mod change needed: click the
      star icon on any play's own detail panel to pin it manually.

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

- [x] **Toast/popup spam audit — built 2026-09-07, results pending.** Per
      the user, live playtesting kept surfacing toasts about countries
      they have no reason to care about (a Perak revolution, a
      decentralized rebel faction using Increase Relations, ...), and
      asked for a systematic log of everything currently rendering as
      toast/popup so it's possible to see, from real data, which ones are
      worth downgrading for unwatched countries — rather than reacting to
      individual screenshots one at a time.
      Built via a one-off script (not by reading vanilla's ~45k-line
      message/on_action files by hand, per CLAUDE.md's Token Budget rule):
      cross-referenced every one of the 95 message keys currently set to
      `notification_type = toast`/`popup` in
      [00_messages.txt](common/messages/00_messages.txt) against every
      vanilla on_action that posts it. Findings:
      - **45 keys are posted from a real, hookable on_action.** ~17 were
        already covered by
        [01_smart_notifications_logger.txt](common/on_actions/01_smart_notifications_logger.txt)'s
        existing `SNW_LOG` taps (not duplicated). The other 28 on_actions
        are newly hooked in
        [05_smart_notifications_toast_popup_audit.txt](common/on_actions/05_smart_notifications_toast_popup_audit.txt),
        each writing a plain `SNW_TOAST_AUDIT|<key>` line — deliberately
        no `is_player`/country-name scoping attempted anywhere (root scope
        types vary too much across 28 on_actions — Character, Country,
        Treaty, Formation... — to safely guess a shared accessor, per
        CLAUDE.md's "never guess" rule). Vanilla's own gating conditions
        are mirrored where they exist (`on_acquired_technology`,
        `on_new_ruler`, `on_country_default`'s two loops) so counts aren't
        inflated relative to what the player actually saw.
      - **44 keys have NO moddable hook at all** — fired from native
        engine code directly, same category as the already-documented
        uncountable keys below. Notably every `power_bloc_*` and
        `law_notification_*` key, `election_results`,
        `country_revolution`, `country_secession`,
        `invasion_started_against_us`, `resource_discovered`. Can't be
        counted or filtered by script; manual observation only.
      **To read results after a session:**
      ```bash
      grep "SNW_TOAST_AUDIT\|SNW_LOG" "Documents/Paradox Interactive/Victoria 3/logs/debug.log" \
        | sed -E 's/.*(SNW_TOAST_AUDIT|SNW_LOG)\|//' | sort | uniq -c | sort -rn
      ```
      Note `SNW_LOG`'s existing hooks predate this audit and were curated
      for Phase 1's original review, not this one — some of what it counts
      (the diplo-play events) has since been replaced by this mod's own
      watched/quiet keys and no longer renders as a toast the way it did
      when that logger was built, so treat those specific counts as "how
      often the underlying event happens", not "how often the player saw
      a toast".
      **Delete this file once the user has reviewed a real session's
      counts and decided which keys are worth watchlist-gating next** —
      same lifecycle as the other temporary probes/taps in this section.
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

## UNVERIFIED before the next release — event context feature

Merged into Smart Notifications 2026-09-14 as
`localization/replace/english/smart_notifications_event_context_l_english.yml`.
**No version bump yet**: two of its branches have never been observed
rendering in game, and the convention is to bump only for something new and
*confirmed working*.

Confirm both, then bump and tag:

1. **State-scoped effects, the `in <state>` form.** Still unconfirmed.
   Expect `+5.0% of Czech Pops (1.2M nationwide) in Bohemia (2.1M
   inhabitants) become more Radical`. Neither `ADD_RADICALS_IN_STATE_THIRD`
   nor `ADD_LOYALISTS_IN_STATE_THIRD` has been seen live.

   **Observed 2026-09-14 (The Great Molasses Flood, Bohemia): there is a
   THIRD rendering path we had not accounted for.** When several pop effects
   share one state scope, the engine hoists the state name into a header and
   renders each line with the BARE `ADD_RADICALS` template -- no country, no
   state, no `in ...` clause:

   ```
   Bohemia
     +5.0% of Machinists Pops (97.6K nationwide) become more Radical
     +5.0% of Engineers Pops  (15.2K nationwide) become more Radical
   ```

   Our nationwide figure renders correctly there (that is the screenshot
   above), but the `(2.1M inhabitants)` addition does not, because that
   template is never invoked. Nothing is broken; the state size simply
   cannot appear in this form. The bare `ADD_RADICALS` template binds
   neither COUNTRY nor STATE, so there is nothing else to add to it -- this
   is the ceiling for the grouped presentation, and it is where the
   "nationwide is a bit odd here" feeling comes from, since only Bohemia's
   machinists are affected.
2. **Strata-filtered effects.** An effect reading "lower/middle/upper strata
   Pops". Expect `(12.4M nationwide)`. These use `GetPlayer`, which an audit
   of all 246 strata effects showed is safe (zero apply to a foreign
   country), but the accessor chain
   `GetTrendValue(GetPlayer.Get*StrataPopulationTrend)` has never rendered.

Confirmed working: interest group, culture, religion, pop type; the
single-filter guard; zero error.log output.

## Channels posted to (and one open follow-up)

- **Vic3 Discord `#v3-mod-gallery`** — posted 2026-09-14.
- **Paradox forums** — posted 2026-09-14:
  https://forum.paradoxplaza.com/forum/threads/mod-release-smart-notifications-get-notified-only-about-the-countries-you-care-about-just-like-eu-iv.1941527/

  **OPEN: the Workshop link is still missing from that thread.** XenForo's
  anti-spam filter rejected the post with a link, and rejected a follow-up
  comment containing one too -- an account-level restriction on external
  links, not anything about the content. The thread currently carries the
  Workshop ID and mod name as plain text instead, which is findable since
  "Smart Notifications" is the only exact match in the Vic3 Workshop.

  **Retry adding the link once the account has some post history.** Do not
  keep retrying against the filter -- repeatedly tripping it risks getting
  the account flagged, which costs more than the missing link. A few genuine
  replies in the Victoria 3 forum over a few days normally lifts it.

## WANTED: tell the player which random outcome actually happened

Raised by the user 2026-09-14. Many events resolve a choice with a
`random_list` -- 60% this happens, 40% that -- and the game **never tells you
which branch fired**. You pick an option, the window closes, and you are left
to infer the result from your ledger. A small toast or feed line naming the
outcome would close that loop, and it is squarely a notification feature
rather than a UI one, so it belongs in this mod.

**Scale (measured 2026-09-14):** 317 `random_list` blocks across 94 event
files. 260 have 2 outcomes, 39 have 3, and 18 have 4-7. Example:
`1848.10` alone carries three separate blocks.

**The hard part is the same wall the event-context feature hit.** There is no
generic "an event option resolved" hook, and a `random_list` branch is plain
script inside a vanilla event file. To announce the outcome, a
`post_notification` has to be inserted **inside each branch** -- which means
overriding the vanilla event files that contain them.

That is exactly what we refused to do for the event-context feature, and for
good reason: 94 overridden event files in a *shipping* mod is a large
compatibility surface and a re-diff burden on every patch. (It is fine for the
throwaway census build, which never ships -- see
[docs/feed-census-plan.md](docs/feed-census-plan.md) -- but this feature would
have to ship.)

**Before building, answer these:**

1. Is there any hook we have not found? Check a fresh `data_types_explorer`
   dump and the on_actions list for anything that fires when an event option
   resolves. Assume no until proven; the same search came up empty for
   modifier tooltips.
2. If it needs event overrides, can it be **narrowed**? The 20-30 events a
   player actually sees every campaign (the 1848 family, agitator and election
   pulses) would cover most of the value at a fraction of the conflict
   surface. A generator like `tools/build_census_mod.py` could emit them
   mechanically from a curated allowlist.
3. What does the notification say? The branch has no name -- only its weight
   and its effects. Naming the outcome usefully probably means authoring a loc
   string per branch, which is the real cost and scales with the allowlist.

**Judgement at the time:** genuinely wanted, clearly in scope, and the most
requested-feeling gap after the event context. But it is the first feature
that would put vanilla event file overrides into a shipping build, so the
narrowing question in (2) decides whether it is worth doing at all.

## Marketing idea (not scheduled — for when the mod is closer to release)

### Post hook backlog (user ideas, unscheduled)

1. **"Updated for patch 1.x"** (user, 2026-09-14). Patch-day posts earn
   attention because players are actively checking what still works, so it
   reads as useful information rather than promotion. Pairs naturally with
   the notification-census idea below — a patch is a legitimate reason to
   re-run the measurement and publish fresh numbers.
2. **The notification census** (below) — the data-led post.
3. **Diplomacy noise alone** — already measured, needs no new work: 271
   diplomatic actions in one session, 233 of them irrelevant to the player.
   A smaller post that could go out at any time.

Framing rule agreed with the user 2026-09-14: the post must add value to
r/victoria3 on its own terms, not read as promo. The version that works
gives the findings away — including the exact Message Settings players can
change by hand — and mentions the mod only as the shortcut.

Coverage reality for any census claim. **CORRECTED 2026-09-14** -- an earlier
version of this note said "200 cheap to instrument covering 120 toast keys".
That was wrong: it counted everything under `common/`, but only
`common/on_actions/` supports the safe append-only pattern. The real split of
all 463 message keys:

| where its `post_notification` call site lives | keys | of which toast |
|---|---|---|
| `common/on_actions/` -- **safe append, no vanilla file touched** | 100 | 38 |
| other `common/` (journal entries, scripted effects, buttons) | 100 | 82 |
| `events/` only | 166 | 62 |
| **nowhere -- engine-fired, unmeasurable forever** | **103** | **41** |

So the safe-append route alone reaches only 38 of 223 toast keys (17%),
barely above the 33 already instrumented.

**The way round it:** a *throwaway measurement build* may override vanilla
files freely, because it never ships. A generator script can copy every
vanilla file containing `post_notification` (~190 of them) and insert a
`debug_log` beside each call, mechanically. That reaches everything except
the 103 engine-fired keys -- and those include the original flagship
offenders (attitude changes, conscription, mobilization, invasions,
political lobbies), so **every published figure stays a lower bound**
regardless. Defensible, and a stronger hook than a false total.

Effort: roughly half a day for the harness, one long passive play session,
an hour of analysis. Not days, as first estimated.

**Build spec written 2026-09-14: [docs/feed-census-plan.md](docs/feed-census-plan.md).**
Self-contained handoff -- a cold session needs only that file plus CLAUDE.md.
Covers the generator approach, the date-stamping, why one playthrough yields
both the vanilla and modded columns, and the coverage limits that make every
published figure a lower bound.

### Original idea

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

- [ ] **`country_revolution`/`country_secession` — confirmed 2026-09-07 to
      fire for OTHER countries' revolutions, not just the player's, no fix
      built yet.** Both are in the truly-no-moddable-hook bucket (native
      C++ code only, confirmed by an exhaustive grep across the entire
      game directory — no script anywhere, on_action or event, ever posts
      either key) — so genuine watchlist-conditional filtering is
      impossible; there's no hook to attach any logic to, period. Vanilla's
      own text ("Revolution is upon us!") reads as self-only, but the user
      directly observed it firing repeatedly for countries that weren't
      theirs (e.g. Perak) — the wording is misleading, not the behavior;
      the message's `type = civil_war` (not `country`) is also consistent
      with a broadcastable CivilWar object rather than a "your country
      only" one. **User explicitly does NOT want a blunt universal
      demotion** (unlike conscription/attitude in Phase 1) since this is
      genuinely important information for watched countries — losing it
      there isn't an acceptable tradeoff. **Proposed approach for a future
      session:** mute the vanilla key entirely (same mechanism as every
      other muted key, no hook needed for a static full-file override) and
      build a fully mod-owned replacement using the same architecture as
      the truce-expiry watcher
      ([02_smart_notifications_truce_tracker.txt](common/on_actions/02_smart_notifications_truce_tracker.txt)):
      a monthly pulse that checks specifically watched countries for
      "just entered civil war" (needs its own trigger-availability check
      first — don't assume, verify what's queryable) and posts our own
      toast only for those. Not started.
- [~] **`diplomatic_action_notification` (generic) — BUILT 2026-09-08,
      loc bug found and fixed same day via the user's screenshot, still
      not re-confirmed live.** Confirmed via a
      probe ([04_smart_notifications_probes.txt](common/on_actions/04_smart_notifications_probes.txt))
      that `scope:actor`/`scope:recipient` resolve to real country names
      on the plain `on_diplomatic_action` (unlike its still-blocked
      `_third_party_` siblings, which is a different on_action despite
      sharing a root type). Muted vanilla's `diplomatic_action_notification`
      (`none`), replaced by `smart_notifications_diplomatic_action_watched`
      (toast)/`_quiet` (feed) in
      [06_smart_notifications_diplomatic_action_filtering.txt](common/on_actions/06_smart_notifications_diplomatic_action_filtering.txt),
      elevating if EITHER the actor or recipient is watched (`OR`, no
      roster to iterate here, just the two direct parties) —
      `is_player = yes` baked into `smart_notifications_is_watched`
      already guarantees an action directed at the player always elevates.
      **The "no loc of our own, bet on native per-action-type text
      resolution" hypothesis was CONFIRMED WRONG 2026-09-08** — the
      user's screenshot showed the raw loc key name rendered on screen
      instead of real text. That resolution turned out to be tied to
      vanilla's specific key name, not the `type = diplomatic_action`
      field generically. Also tried `[ROOT.GetName]` to recover which
      specific action type fired dynamically — also confirmed wrong (a
      real `error.log` "Data error in loc string" entry). No known way to
      tell Increase Relations apart from Decrease Relations etc. from our
      own script/loc. **Fixed** by giving both replacement keys real,
      deliberately GENERIC name/desc/tooltip loc
      ([smart_notifications_l_english.yml](localization/english/smart_notifications_l_english.yml))
      — a real, accepted loss of vanilla's per-action-type wording detail
      in exchange for rendering correctly for every action type instead
      of a broken key for all of them. Also fixed a separate,
      independently-discovered bug in the same pass: the ELEVATED/QUIET
      `debug_log` lines were silently failing their own "Data error in
      loc string" from `SCOPE.sC('actor').GetCountry.GetNameNoFormatting`
      — chaining `.GetCountry` directly onto a `SCOPE.sC(...)` call isn't
      the same as `THIS.GetCountry` inside an actual re-scoped
      `scope:actor ?= { ... }` block; fixed by dropping `.GetCountry`,
      matching the plain `SCOPE.sC('actor').GetNameNoFormatting` pattern
      used everywhere else in this mod for the diplomatic_play root.
      Deleted the now-resolved `[ROOT.GetName]` experimental diagnostic.
      **Needs the user to see a real diplomatic action in-game to confirm
      the generic text now actually renders.** Once confirmed, worth
      checking whether all action types sharing this group deserve
      identical treatment or whether some (e.g. autonomy requests,
      arguably always worth seeing) should stay unconditional.
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

## Backlog: agitator invite (2026-09-09)

Two ideas from the user, for later -- NOT implemented, investigation only:

1. **Top-bar banner treatment**, like market/goods shortages show (a red
   icon near the top of the screen, distinct from the Important Actions
   list on the left). Needs investigation before assuming it's even
   possible from script: unclear whether that top-bar treatment is driven
   by the same `alert_types` system at all, or a separate/hardcoded UI
   element tied specifically to market/goods shortages. Check
   gui/ for the relevant widget and what data-binds it before promising
   this is buildable the same way the Important Actions alerts are.
2. **One-time toast when an agitator slot opens up** -- same
   edge-triggered pattern as the law-readiness and taxation-deficit
   toasts (empty_agitator_slots crossing from 0 to >=1). Simpler than
   both of those: no per-type dispatch needed (there's nothing to name --
   "a slot opened" is the whole message), likely just a single flag
   variable + monthly-pulse edge check, closer in shape to a from-scratch
   version of the truce tracker than to the law/tax toasts.

## Backlog: alliance-related notifications (2026-09-09)

User, after seeing the full notification table, flagged a real gap:
"more important notifications that may be missing, like when you lose
an ally, or when a watched country gains/loses an ally." NOT
implemented -- investigation only, for later:

1. **You lose an ally.** Need to find the actual hook -- likely an
   `alliance`-type diplomatic pact ending (broken/expired/dissolved).
   Vanilla has `alliance_action_notification_group`/
   `defensive_pact_action_notification_group` for FORMING one (confirmed
   present in this mod's messagetypes_custom.txt dump); check whether
   there's a corresponding "pact broken" message/on_action, similar to
   `diplomatic_action_break_notification_group` seen in that same dump.
   If it goes through the generic `on_diplomatic_action`-style break
   mechanism, it may already be reachable via the same
   `has_diplomatic_pact`-style checks used for the routine-relations
   carve-out this session -- worth checking before assuming a new hook
   is needed.
2. **A watched country gains/loses an ally** (third-party case, doesn't
   involve the player). Same underlying event as #1, just gated on the
   Watchlist instead of `is_player`, matching the existing
   watched/quiet pattern used everywhere else in this mod. Natural
   candidate for the SAME on_action/message pair as #1, split into a
   player-targeted vs watched-third-party branch the same way
   06_smart_notifications_diplomatic_action_filtering.txt already does.

Both should probably default to `toast` given the user's stated bar
here (losing an ally is significant; a watched country's alliance
status changing is exactly the kind of thing the Watchlist exists for).
