# Watchlist Notification Spec

**Status: LOCKED** (2026-09-09, explicit sign-off from the user). Every
question in §8 is resolved. Changes to this file from here need the same
kind of agreement that produced it -- the code answers to this spec, not
the other way round.

This is the behavioural spec for what the Watchlist does to notifications.
It is the reference the code answers to — where the code and this file
disagree, this file is right and the code is a bug. Engine reasons why
something can't be built live in [engine-notes.md](engine-notes.md); this
file records *what we want*, and notes constraints only where they change
the answer.

---

## 1. Purpose

> The spirit of the country selector is that toasts should contain all
> important actions towards you or involving a watched country, and only
> that.
> — the user, 2026-09-09

A notification needs **both** axes to earn a toast:

| | aimed at you / a watched country | aimed at anyone else |
|---|---|---|
| **important** | **toast** | feed |
| **routine** | feed | feed |

## 2. Scope

- **Messages only.** The alert system ("Important Actions & Alerts",
  `common/alert_types/`) is out of scope, including this mod's own
  law-commitment alert.
- **Proposals are out of scope and stay untouched.** Alliance, treaty,
  vassalage, power-bloc invites and every other `requires_approval = yes`
  action arrives through `post_proposal` → `open_popup` with an expiry
  timer, not through the message system. They have no `notification_type`
  to tune, they are already unmissable, and the user confirms that system
  works well as-is.
- **Self-focused families are out of scope** — the taxation deficit
  toast, truce expiry, law-ready alerts. They are about your own country;
  the Watchlist has no bearing on them.
- Single-player only, consistent with the rest of the mod.

## 3. Definitions

- **Watched** — on the player's Watchlist. `smart_notifications_is_watched`
  also returns true for the player themselves; that is deliberate and
  stays (see §7, D10).
- **Aimed at** — the country is the *recipient*/target of the action, not
  the actor. A watched country **acting on** a stranger is not an event
  aimed at anything you care about. This distinction is load-bearing.
- **Actively involved** (diplomatic plays) — a genuine committed
  participant (`is_diplomatic_play_participant_with`), never merely
  eligible to intervene. Already implemented correctly, after the
  Bali/Sulu toasts the user called "super painful" on 2026-09-08.
- **Tiers** — `popup` > `toast` > `feed` > `none`. The feed is not
  deletion; it is the log you skim on purpose.
- **Floor rule** — anything involving you or a watched country never goes
  below `feed`. Silence (`none`) is only for events involving neither.

## 4. Behaviour by family

Family IDs are stable — use them when discussing sequencing.

### F1 — Generic diplomatic actions (the unilateral bucket)

Covers every `requires_approval = no` diplomatic action: relations
changes, rivalry, embargo, expel diplomats, humiliation, war reparations,
support separatism, orchestrate coup, colonial claims, and the ~20
overlord/subject management actions. **These are mutually indistinguishable
at notification time** (§6), so the rule cannot depend on which one it is.

| situation | tier |
|---|---|
| aimed at **you**, actor is watched | toast |
| aimed at **you**, actor is not watched | feed |
| aimed at a **watched country**, actor is watched | toast |
| aimed at a **watched country**, actor is not watched | feed |
| aimed at anyone else | feed |

Rationale: nothing existential lives in this bucket. War arrives via F2;
subjugation and alliances via proposals (§2). The worst thing lost to the
feed is a rivalry or embargo declared by a country you are not watching.

**Every row above gets its own message key and its own group** (see D11) so
each can be retuned, including muted outright, from the in-game Message
Settings without a code change. That is the mechanism for the user's
follow-on goal of thinning the *feed* later: the bottom row ("aimed at
anyone else") is the obvious mute candidate once the toast tiers are
right, and muting it is then a player setting rather than a release.

### F2 — Diplomatic plays

| situation | tier |
|---|---|
| play start / join side involving **you** | toast |
| **war start** involving **you** | popup |
| play start / join side / war start involving a **watched** country | toast |
| involving neither | feed |

**Revised 2026-09-10 to match vanilla.** The player rows first shipped as
popups across all three families; vanilla makes only the war start a popup and
leaves play start and join side as plain toasts, and the mod's popup rows
carried `popup_name = war_started` — a war layout on a play that is not yet a
war, which vanilla never does. The escalation the player wants is still there:
a play aimed at you toasts when it opens and pops up if it becomes a war.

**Pausing is not ours to set.** Vanilla messages accept exactly eight fields
(`type`, `group`, `texture`, `notification_type`, `color`,
`on_created_soundeffect`, `popup_name`, `days`) and **none of them is
`pause_game`** — checked across every vanilla message. Whether a notification
pauses is the player's own "Pause?" checkbox, stored per group in
`messagetypes_custom.txt`. So "war start should pause" is a setting the player
ticks once, not something this mod can ship, and the same applies in reverse to
un-pausing capitulation.

Plays **you start yourself** keep today's behaviour and are explicitly not
a concern — the user confirms this works fine now. The popup row means a
play *someone else* brings to you; see Q4.

Note the watched war-start row is a deliberate downgrade from today's
`popup`. Plays involving you stay `popup`.

### F3 — War outcomes

Currently `feed` and not Watchlist-aware.

| situation | tier |
|---|---|
| involving a **watched** country | toast |
| involving neither | feed |

The wording must name what was won or lost. Vanilla's own text already
does this, via
`[SCOPE.sDiplomaticPlay('diplomatic_play').GetWarOutcomeString]`, so reuse
vanilla's phrasing rather than writing our own.

Scope note: this concerns only `peace_agreement_signed_non_participant`,
the third-party key. Wars **you** are party to already fire
`peace_agreement_signed_war_leader` / `_war_participant` as popups, and
those stay untouched.

**Lower priority than F1/F2** per the user. Note this reopens Phase 2,
which was closed on the grounds that vanilla already covered the peace
announcer.

### F4 — Treaties

`treaty_entered_into_force`, `country_broke_treaty`,
`country_withdrawn_from_treaty`, `treaty_proposal_declined`,
`treaty_dissolved`, `treaty_article_removed`.

**Unchanged — stays toast, ungated.** In principle these should be gated
on the Watchlist, but the user believes they only fire for treaties
involving us, and observed volume is negligible (2 in a full session), so
the gate is not worth building. Revisit only if treaties between
uninvolved countries are ever seen toasting.

### F10 — Pact breaks

The other half of F1. `on_diplomatic_action` fires when a diplomatic action
creates a pact; `on_diplomatic_action_break` fires when one ends, and F1 only
ever specced the first. Found 2026-09-09 by the user noticing "Tibet stopped
damaging Relations" sitting in the feed when Tibet is watched and the pact was
with them.

| situation | tier |
|---|---|
| aimed at **you**, by a watched country | toast |
| aimed at a **watched country**, by a watched country | toast |
| anything else | feed |

Same rule as F1 and the same reasoning, including the actor-side test using
`smart_notifications_is_watched_not_player` — a pact you ended yourself is not
news.

**Three keys on two groups.** The two toast cells need separate keys because
their `_desc` differs (vanilla's break text assumes the reader is a party,
exactly like the creation text does), but they share a group so the family
costs two Message Settings rows rather than three. Vanilla's own
`GetActionNotificationBreakName` / `GetActionNotificationBreakDesc` supply the
accurate per-action wording — "Tibet stopped damaging Relations" — so this
family invents no text of its own for the player-facing case.

Vanilla's `diplomatic_action_break_notification` is muted in favour of these.

**Not covered, deliberately:** `diplomatic_pact_auto_break_notification`, the
other way a pact can end (a requirement stops being met). It needs no keys at
all — its vanilla text is written around `GetPlayer`, so it is already
player-scoped like F5's obligations, and raising it would be a one-line tier
change. Left at `feed` until someone asks.

### F5 — Obligations

`country_owes_obligation`, `country_owed_obligation`, and their
removed/expired variants. Currently `feed`.

**Inherently about the player** — vanilla's own text reads "We now owe an
obligation to X" and "X now owes us an obligation". No filtering needed;
this is a pure tier change.

| situation | tier |
|---|---|
| all of them (they always involve you) | toast |

### F6 — Attitude changes

`country_attitude_changed` / `_improved` / `_worsened`. Currently muted
outright (`none`); vanilla's own default is `feed`, and this mod demoted
them as "recurring AI opinion-drift spam".

These are inherently player-directed — vanilla's text reads "The attitude
of X towards us has worsened" — but **they cannot be filtered by the
Watchlist.** No on_action posts them: they are fired by engine code with no
moddable hook (confirmed 2026-09-09 — nothing anywhere in vanilla
`common/` references these keys except the message definitions
themselves). The only lever is the global tier, all countries at once.

| situation | tier |
|---|---|
| every country's attitude toward you | **feed** (un-mute, back to vanilla's default) |

Decided: `feed`. Toasting them would mean interrupting for every country
on the map, two tiers above vanilla's own judgement, on a family already
muted once for being spam — which would break §5's rule that nothing
un-important should toast.

**Wanted later:** toast for *watched* countries only. Blocked purely on the
missing hook, not on the design. Tracked in TODO.md — revisit if a patch
ever adds an on_action for these, or if another route to the same event
surfaces.

### F7 — Subject released

**Unchanged:** toast for watched, silent otherwise. Already matches the
spirit.

### F8 — Truce expiry

**Unchanged:** toast regardless of the other country.

### F9 — War goals

`wargoal_added` / `wargoal_removed`. Currently `feed`.

Unlike F5 these are **not** player-scoped — vanilla's text is "[war goal]
has been added for [actor]", which fires for plays you are merely
observing, so promoting them wholesale would be noisy.

| situation | tier |
|---|---|
| the play involves **you** | toast |
| any other play | feed |

Feasible: `on_wargoal_added` exists (Root = Diplomatic Play,
`scope:actor` = war goal owner), so the play's participants can be tested
with the same `is_diplomatic_play_participant_with` pattern F2 already
uses. If it turns out more awkward than that in practice, fall back to
leaving the whole family at `feed` — the user's explicit second choice.

## 5. Invariants

1. **Never silently drop anything aimed at the player.** Over-notifying is
   the safe direction to fail in.
2. **Actor and recipient are not interchangeable.** Every rule states
   which one it means.
3. **One notification per event.** Several vanilla on_action pairs fire for
   the same event and would double up; post from exactly one.
4. **Anything involving you or a watched country floors at `feed`.**
5. **Your own actions are never news.** Nothing the player initiates gets
   promoted, in any family — you already know what you just did. Concretely:
   every elevation rule tests the *actor* is not the player before firing
   (Q4).

## 6. The one engine constraint that shapes this spec

Within F1 the action type is **unknowable** at the moment the notification
is posted. Three mechanisms were tried on 2026-09-09 and all three are
closed:

1. Query the pact the action creates — not in gamestate yet at that
   instant.
2. Ask the action object — zero triggers and zero effects support
   `diplomatic_action` scope.
3. Flag the target from the action's own definition — the parser rejects
   the `effect` key that the game's own schema documents.

Full write-ups in engine-notes.md. **Do not re-attempt these without new
information.** This is why F1's rule is expressed in terms of *who* acted
rather than *what* they did.

## 7. Decisions already taken (do not reopen without reason)

- **D4** — demotions floor at `feed`, never `none`, for anything involving
  you or a watched country.
- **D5** — proposals stay untouched.
- **D7** — the Watchlist stays binary, with no size cap. More watched
  countries meaning more toasts is self-inflicted and fine.
- **D8** — messages only; alerts out of scope.
- **D10** — **no player/watched split in the shared trigger.**
  `smart_notifications_is_watched` keeps `is_player = yes` baked in. The
  few places needing three tiers check `is_player` explicitly first, which
  is how the diplomatic-action file already works. No migration, no trigger
  surgery.
- **D12 — label vocabulary.** One word per concept across every family:
  **Involving You** / **Watched** / **Non Watched**. "Ambient" and
  "Elsewhere" are retired (user's call, 2026-09-09). Labels are kept short
  because Message Settings truncates at roughly 44 characters, and two
  cells whose labels differ only after the cut are indistinguishable in the
  list — which is what the first build shipped for the two "At a Watched
  Country, From ..." rows. The distinguishing half must land before the
  truncation point. F9 is the deliberate exception: it splits on whether
  the play involves you, with no watched dimension at all, so its second
  row reads "Other Plays" rather than "Non Watched", which would name a
  rule that does not exist.

  F1's five rows use arrow notation -- `Watched -> You`,
  `Non Watched -> Watched`, `Neither Watched` -- rather than "X from Y".
  The arrow points at whoever the action lands on, which is the thing the
  tier actually depends on; "X from Y" left the direction ambiguous (the
  user's question, 2026-09-09: "Watched from Non Watched, what does that
  mean concretely?"). It is also shorter, so every row clears the
  truncation point with room to spare.
- **D11 — one message key and one group per rule cell**, unless two cells
  are deliberately merged (see below). Player Message
  Settings overrides apply per *group*, not per key (CLAUDE.md § Engine &
  Syntax Rules), so a cell only stays player-adjustable if it owns its
  group outright. This also satisfies the engine's "no mixed notification
  types in one group" rule for free. Cost: one extra entry per cell in the
  player's Message Settings list, each carrying the `(SN) ` prefix. The
  benefit is that any future retune — especially muting feed noise —
  becomes a setting the player changes, not a release we ship.

  **Deliberate exceptions are allowed and must be declared.** Two cells the
  player would never want to adjust separately are better merged, because
  every group costs a row in an already-long list. Sharing is legal only
  when the sharers agree on `notification_type`. The one case today is F9's
  war goals: "added" and "removed" keep separate keys for their wording but
  share one group per tier, so the family shows two rows instead of four
  (user's call — "not even sure how to remove a war goal"). The second is
  F2's three "Non Watched" cells (start / join side / war start), merged to
  one row for the same reason: a play with nobody you follow in it is one
  concept, not three. Subject Released stays out of that merge because it
  is `none` rather than `feed`.

  Where a merged group's row appears in the settings list is decided by
  which of its keys is defined FIRST, since the list follows definition
  order. Keep merged keys defined after the per-family rows they sit under,
  or the shared row renders in the middle of an unrelated family. Declared in
  `WATCHLIST_SPEC_SHARED_GROUPS` in `tools/check_references.py`; anything
  sharing a group without being declared there is still an error, which is
  the accident the check exists to catch.
- **Muting `diplo_play_start_notification` is safe** despite its text
  meaning "X started a play against us". Checked 2026-09-09: in
  single-player both it and `on_diplo_play_start_third_party` fire for the
  same event to the same viewer, and the mod posts its own notification
  from the latter — so a play declared on the player still reaches them,
  as a popup, since `is_player` counts as watched.

## 8. Question log

**Q1 — F1 table. LOCKED.** Confirmed after the user reviewed the real
events from a live session; the per-cell key/group requirement went in as
D11.

**Q2 — F6 tier. LOCKED as `feed`** (un-muted from `none`). The user's
first answer was `toast`, given on the understanding it meant *toast for
watched countries* — which the missing hook makes impossible, since the
tier is global across every country. Watched-only toasting is recorded as
a wish in TODO.md.

**Q3 — F9. LOCKED** as toast when the play involves you, feed otherwise.
Feasible via `on_wargoal_added`; falls back to leaving the family at `feed`
if it proves awkward.

**Q4 — the player as actor. LOCKED** as (a): the player-as-actor is
excluded everywhere. Nothing you initiate is ever promoted, in any family.
Safe whether or not the engine even reports your own actions back to you
(across a 271-action session `on_diplomatic_action` fired zero times with
the player as actor, but that is not proof), and consistent with plays you
start yourself keeping today's behaviour.

**No open questions remain.**

## 9. Implementation plan

Designed around one constraint: **the user's time in-game is the scarce
resource.** Everything that can be proven without a playtest is proven
without one, and the playtests that remain are passive — play normally,
and the log is read afterwards rather than the user watching for toasts.

### What each change actually risks

Sorting by risk is what makes the testing cheap, because the three classes
need very different evidence:

| class | what it is | how it's verified |
|---|---|---|
| **Config-only** | a `notification_type` value change on an existing key (F4, F5, F6, F8, and F2's war-start row) | static + one glance at Message Settings. **No playtest.** |
| **Routing** | which key gets posted (F1, F2, F9) | the `SNW_FILTER` debug lines already log every decision — read from the log, no user observation |
| **New text** | a new message key whose loc must render (F1's new keys, F3) | needs the event to actually happen in-game; this is the only class that truly costs a session |

The known failure mode for the third class is the raw-loc-key-on-screen bug
(engine-notes.md § Two separate function tables) — it fails silently and
only `error.log` shows it, so every new key's first live firing must be
checked in the log, not on screen.

### Step 0 — extend the static checker first (no game)

Before writing any behaviour, teach `tools/check_references.py` to assert
this spec mechanically, so a violation fails the build rather than a
playtest:

- every F1 cell has a key, and every such key sits **alone** in its group
  (D11), so Message Settings can retune each independently;
- every mod-created group has an `(SN) `-prefixed loc label;
- no group mixes notification types (already an engine warning, worth
  catching statically);
- each new key has all four loc keys present (`_group`, `_name`, `_desc`,
  `_tooltip`) — the missing-loc bug class this project has hit repeatedly.

This is the highest-leverage step: it converts most of what would otherwise
be "check it in-game" into `python tools/validate_syntax.py`.

### Step 1 — F1 + F2 (one build, one passive session)

The big one, and the only step needing real play. F1 becomes five keys and
five groups per D11; F2 changes the watched war-start tier and adds the
player-as-actor exclusion (Q4).

Both are in files that already log every decision, so the verification is:
the user plays a normal session, then the log is checked for (a) each F1
cell firing with the right key, (b) zero `error.log` loc failures from the
five new keys.

**Coverage is the risk, not correctness.** From the last session's numbers,
four of the five F1 cells fire freely (220 elsewhere, 26 at a watched
country, 6 at the player). The fifth — *aimed at you, actor watched* —
depends on a watched country happening to act on the player. To avoid
waiting on chance: before playing, add to the Watchlist two or three
countries that acted on the player recently (Sulu, Kokand, Nawanagar,
Luang Prabang, Burma and Banjar all did last session). That turns the rare
cell into a near-certain one.

Note F2 may well produce **no** diplo play events at all — the last
session had zero. That is fine and expected: F2's changes are config-only
plus one trigger, and are not blocked on observing a play.

### Step 2 — F5 + F6 + F8 (no session of its own)

Pure tier changes on existing vanilla keys, no routing, no new text:

- F5 obligations → `toast`
- F6 attitude → `feed` (un-mute)
- F8 truce expiry → unchanged, confirm only

Ship these **in the same build as Step 1** so they ride along on the same
session. Verification is a single look at the Message Settings screen to
confirm the groups read as intended.

### Step 3 — F9 war goals

New hook (`on_wargoal_added`), so scope availability is unproven. Build it
with the decision logged the same way F1 does, and let it ride on whatever
session comes next — no dedicated test. If war goals do not occur, nothing
is lost; the fallback (leave at `feed`) is one line.

### Step 4 — F3 war outcomes, last

New family and new keys, and it reuses vanilla's outcome wording
(`GetWarOutcomeString`) in our own key — the exact pattern that once
rendered a raw loc key on screen. Needs its own confirmation in `error.log`
on first firing, and third-party peace deals are not frequent. Lowest
priority per the user; do not let it hold up Steps 1–3.

### Release

Version bump only once a step is confirmed working, per CLAUDE.md — not
per build. Then `python tools/package_release.py` and upload from
`smart_notifications_release`, never the dev junction. **Note the live
Workshop build is already behind:** v0.37 shipped before the actor/recipient
split, so it still mutes actions aimed at watched countries.

### Summary of what the user actually has to do

1. Add a few likely-active countries to the Watchlist (30 seconds).
2. Play one normal session.
3. Glance at Message Settings once to confirm the group labels.

Everything else is read from `debug.log` and `error.log` afterwards.
