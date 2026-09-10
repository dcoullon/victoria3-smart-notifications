# Watchlist Notification Spec — DRAFT, not yet locked

**Status: DRAFT.** Nothing here is built against until the user says "OK"
explicitly. Open questions are collected at the end; everything above them
is settled.

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
| play involving **you** | popup |
| play start / join side involving a **watched** country | toast |
| war start involving a **watched** country | toast |
| involving neither | feed |

Plays **you start yourself** keep today's behaviour and are explicitly not
a concern — the user confirms this works fine now.

Note the war-start row is a deliberate downgrade from today's `popup`.

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
outright (`none`); **vanilla's own default is `feed`**, and this mod
demoted them as "recurring AI opinion-drift spam".

These are inherently player-directed — vanilla's text reads "The attitude
of X towards us has worsened" — but **they cannot be filtered by the
Watchlist.** No on_action posts them: they are fired by engine code with
no moddable hook (confirmed 2026-09-09 — nothing anywhere in vanilla
`common/` references these keys except the message definitions
themselves). The only lever is the global tier, all countries at once.

So the choice is between three global settings, not a watched/unwatched
split. *(Open — see Q2.)*

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
- **D11 — one message key and one group per rule cell.** Player Message
  Settings overrides apply per *group*, not per key (CLAUDE.md § Engine &
  Syntax Rules), so a cell only stays player-adjustable if it owns its
  group outright. This also satisfies the engine's "no mixed notification
  types in one group" rule for free. Cost: one extra entry per cell in the
  player's Message Settings list, each carrying the `(SN) ` prefix. The
  benefit is that any future retune — especially muting feed noise —
  becomes a setting the player changes, not a release we ship.
- **Muting `diplo_play_start_notification` is safe** despite its text
  meaning "X started a play against us". Checked 2026-09-09: in
  single-player both it and `on_diplo_play_start_third_party` fire for the
  same event to the same viewer, and the mod posts its own notification
  from the latter — so a play declared on the player still reaches them,
  as a popup, since `is_player` counts as watched.

## 8. Open questions

**Q1 — F1. LOCKED.** Table confirmed by the user after reviewing the real
events, with the per-cell key/group requirement added as D11.

**Q2 — F6 tier. STILL OPEN, and the previous answer was based on a wrong
premise.** The user answered "toast for now", understanding it as *toast
for watched countries*. That is not available: attitude notifications have
no moddable hook, so the tier applies to **every country at once**. The
real options are:

- **(a)** `feed` — vanilla's own default. Restores visibility without
  interruption; you would see attitude shifts when you go looking.
  *(Recommended.)*
- **(b)** `toast` — every country's attitude shift toward you interrupts.
  Two tiers above vanilla's own judgement of the event, and this mod muted
  it as spam once already.
- **(c)** stay muted.

**Q3 — F9. LOCKED** as option (b): toast when the play involves you, feed
otherwise. Confirmed feasible via `on_wargoal_added`. Falls back to leaving
the family at `feed` if implementation proves awkward.

## 9. Implementation sequencing (once locked)

1. **F1 + F2** — same file, ship together, highest value.
2. **F5 + F6** — small, independent, low risk (pure tier changes plus one
   split).
3. **F9** — trivial once Q3 is answered.
4. **F3** — last. New family, and reusing vanilla's outcome wording in our
   own key is the same pattern that once rendered a raw loc key on screen,
   so it needs verifying in a live run before it is trusted.
