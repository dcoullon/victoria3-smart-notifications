# Changelog

All notable player-facing changes to this mod are recorded here, in the
[Keep a Changelog](https://keepachangelog.com/) style: grouped by version,
each version broken into **Added / Changed / Fixed / Removed**. This is the
file to copy from when writing Steam Workshop update notes — every entry here
should already read like something a player (not a modder) can understand.

For planned/in-progress work, see [TODO.md](TODO.md) instead — items move here
only once they've actually shipped in a version.

Versions follow `metadata.json`'s `version` field. **Versioning convention
(adopted 2026-09-07):** `0.XY` — the tenths digit (`0.1`, `0.2`, `0.3`...)
marks a major milestone; the hundredths digit increments by `0.01` when
something genuinely new ships **and is confirmed working**. Bug fixes,
repeated attempts at a feature that isn't working yet, debug
instrumentation and doc-only changes get a commit but **no** version bump
(revised 2026-09-07 — bumping on every fix-attempt for the same
unfinished feature made the number meaningless). Not full semver; this
mod hasn't reached a 1.0 concept of "breaking changes" yet.

## [0.40] — 2026-09-14

No settings reset needed. This release changes no notification tiers — it only
adds information to event tooltips.

### Added

- **Event choices now tell you how many people they affect.** Vanilla says
  "+10.0% of Czech Pops become more Radical" and leaves you to guess whether
  that is a rounding error or a catastrophe. It now reads "+10.0% of Czech
  Pops (3.83M nationwide) become more Radical". Works for cultures, religions,
  interest groups, professions and strata, on every event, journal entry and
  decision that moves pops — and on war and famine death tolls too.
- **State-scoped choices also show the state's population**, so "in Bohemia
  (2.1M inhabitants)" tells you whether the place being affected matters.

### Known limitations

- The figure is **nationwide**. Roughly 39% of these effects apply to a single
  state, and the game does not expose the size of a group *within* a state to
  mods — so the number is an upper bound in those cases, which is why it says
  "nationwide" rather than pretending otherwise.
- Effects that combine two filters (a culture *and* a profession, say — about
  5% of them) show **no** figure, because the affected group is the overlap of
  the two and no number for that exists. Better to say nothing than to show a
  confident wrong answer.

## [0.39] — 2026-09-10

Notification fixes only. **No settings reset needed for this one** — nothing
about which tier a notification uses has changed, only which notifications
reach you at all.

### Fixed

- **Diplomatic plays involving countries on your Watchlist were mostly not
  reaching you.** If a watched country opened a play against somebody else —
  the single thing the Watchlist exists to surface — you would usually see
  nothing. Plays declared directly on you always worked, which is why this took
  a while to spot. Anyone running v0.38 has been missing most of them.
- **A native uprising against a watched country no longer interrupts you.**
  These fire constantly against colonial powers, and two arriving together read
  as the same notification twice. An uprising against *you* still toasts, and a
  watched country attacking a decentralized one still toasts — only the
  uprisings themselves are quieted.

## [0.38] — 2026-09-10

**If you played an earlier version, open Message Settings and press
"Reset to Default Settings" once.** This release retunes a lot of notification
priorities, and any setting you changed by hand overrides the mod until you
reset. The game will remind you in-game once per campaign.

### Added

- **A diplomatic play declared on you now reaches you.** Previously it could
  produce no notification at all -- the single worst thing a notification mod
  can do, and it is fixed. A play aimed at you toasts when it opens and shows
  a full-screen popup if it turns into a war.
- **Pact endings are filtered like pact beginnings.** A watched country ending
  an arrangement with you (or with another country you watch) now toasts
  instead of being buried in the feed with everything else.
- **Third-party diplomatic proposals are silenced.** Two countries proposing,
  accepting, declining or breaking an arrangement between themselves is never
  something you can act on.
- **The Watchlist shows each country's power rank and world ranking**, laid
  out like the game's own at-peace ledger, so you can tell a great power from
  an obscure minor at a glance while choosing who to follow.

### Changed

- **Diplomatic actions aimed at you are now sorted by who did them.** An
  action from a country you watch toasts; the same action from a country you
  do not watch goes to the feed. This is what finally quiets the constant
  "someone improved relations with you" traffic without hiding anything that
  matters.
- **A watched country acting on a stranger no longer toasts.** Only actions
  aimed AT you or AT a country you watch do. One session had 51 of the former;
  they were the bulk of the noise.
- Obligations you are owed or owe now toast, rather than sitting in the feed.
- Attitude changes towards you are visible in the feed again, instead of being
  muted outright.
- Sway offers, war-participant defaults, harvest conditions and resource
  discoveries all moved to the feed after a session showed them firing 93, 69
  and dozens of times respectively.
- Every notification this mod adds now appears together at the end of the
  Message Settings list, grouped by family, so its rows are findable.

### Fixed

- Notification tooltips that rendered as raw text instead of a description.
- A double full-screen popup when a war started involving you.
- The game no longer stops pausing when a war involving you breaks out. An
  earlier version replaced that notification with its own and could not carry
  the base game's pause setting across; it is handed back to the base game
  now, so the pause works out of the box again.
- You are no longer told about a diplomatic play you started yourself.

### Removed

- The permanently-silent "Subject Released, Non Watched" row, which existed
  only to be switched on and never was.
- The mod's own war goal notifications. They existed to highlight a goal added
  to a play you are in, but war goals can only be added while a play is still
  in its opening phases -- so every one of them was simply a demand arriving as
  the play opened, and highlighting those was noise. The base game's handling
  is back, unchanged.

## [0.37] — 2026-09-09

### Changed

- **A watched country taking a diplomatic action against someone else
  (not you) no longer pops a toast.** A live session showed this firing
  51 times — a watched great power acting on some unrelated minor, over
  and over — which is screen-interruption spam, not the "worth
  interrupting you for" case this mod exists to surface. It's still in
  the notification feed with the accurate, specific wording, so you can
  skim what a watched country has been up to whenever you want.
  Anything aimed at **you** still toasts, unchanged.
- A watched country's subject being **released** now pops a toast
  instead of only appearing in the feed — a small enough event not to
  deserve a full popup, but a real change to a country you're
  deliberately tracking. The unwatched version stays silent.

## [0.36] — 2026-09-09

### Changed

- **Diplomatic action notifications now show the real, specific wording,
  confirmed working end-to-end in a live session.** A country taking a
  diplomatic action against you (increasing/damaging relations, a
  rivalry, an embargo, an autonomy change, etc.) now shows the actual
  action in the toast title (e.g. "Kokand improving Relations") with the
  full detail in the body (current relation standing, their attitude
  towards you, and so on) — matching the quality of vanilla's own
  notifications, instead of a generic "X has taken a diplomatic action
  involving Y."
- This also permanently fixes the earlier double-notification issue for
  actions directed at you: you'll now see exactly one notification,
  with full detail, for that case.

## [0.35] — 2026-09-09

### Added

- **One-time toasts, confirmed working end-to-end in a live session**:
  the Law Ready to Enact alert now also fires a toast naming the
  specific law and its law group the moment it becomes ready, and the
  Taxation Deficit alert now fires a toast naming the specific state the
  moment it enters deficit — both independent of the persistent alert's
  own dismiss state, so a second (different) law or state becoming ready
  while the alert is already showing/dismissed for an earlier one no
  longer goes unnoticed.

### Fixed (2026-09-09, same version — see versioning convention above)

- A diplomatic action directed at you could show two notifications for
  the same event. Fixed for good in [0.36](#036--2026-09-09) below —
  see that entry for the final behavior.
- Empires with many states entering a taxation deficit at once (e.g.
  newly incorporated territory) could produce a wall of one-time toasts,
  one per state. Now capped at 3 concurrent — the persistent alert is
  unaffected and still reflects every affected state.
- The first-load toast now points directly to the Watchlist tab and is
  shorter.
- Added a one-time toast prompting Watchlist setup if it's ever found
  empty (mainly relevant to saves from before this mod was added).

## [0.34] — 2026-09-08

### Added

- **Agitator Invite Available alert** — flags when you have an empty
  agitator slot and at least one exiled character eligible to agitate
  for you, so the Invite Exile opportunity doesn't go unnoticed.
- **States with a Taxation Deficit alert** — flags any incorporated state
  where tax collection can't keep up with government spending, grouped
  into a single stacked entry when it's happening in more than one state
  at once.
- **Law Ready to Enact alert** — an opt-in, per-law "notify me" checkbox
  on each law's detail panel in the Politics screen. Flag any laws you're
  working toward, and this alert lights up once that specific law's next
  checkpoint has better odds of succeeding than stalling — telling you by
  name which law and which law group, so you know exactly what to go
  enact. Confirmed working end-to-end in a live session, including the
  specific-law-name and law-group text in the alert's own tooltip.

### Fixed

- Player Message Settings and law-panel labels this mod adds now
  consistently carry an `(SN)` tag so they're identifiable at a glance
  against vanilla rows.

## [0.33] — 2026-09-08

### Added

- **Relational notification filtering — now confirmed working end-to-end
  in-game.** A diplomatic play starting, a country joining a side, a play
  escalating to war, and a subject breaking free all now correctly stay
  quiet unless a Watchlist country (or you) is a genuine participant —
  confirmed against multiple real plays during a live session, including
  ones with no connection to the Watchlist at all (correctly stayed
  quiet) and ones where a Watchlist country turned out to be legitimately
  involved as an overlord or backer (correctly elevated).

### Fixed

- Two real bugs found via live playtesting and fixed the same day:
  notifications for an unrelated country's internal revolution/secession
  could incorrectly pop up just because a Great Power on the Watchlist
  was merely *eligible* to intervene, not actually involved; and some
  diplomatic play notifications could fire several times in a row for the
  same event.

## [0.32] — 2026-09-07

### Added

- **Country Watchlist selector — now working end-to-end** (confirmed
  in-game). A Watchlist tab in Message Settings with five views: Watched,
  Great Powers, Neighbors (grouped by continent), Rivals, and Add a
  Country. Each row has a checkbox, and each tab has Select All /
  Deselect All acting on everything shown in that tab. Great
  Powers/neighbours/rivals are populated automatically at the start of a
  new campaign.
- Decentralized countries are excluded from the Watchlist throughout —
  watching one isn't meaningful, and they were the source of Select All
  appearing to skip entries.

### Changed

- The "Add a Country" view is now called **All Countries**.
- The Watched tab has only a Deselect All button; its Select All was
  removed (on a list defined as "everything already watched" it had no
  sensible meaning, and in practice just watched most of the world).

## [0.31] — 2026-09-07

### Added

- Diagnostic logging (`SNW_PROBE` lines in `debug.log`) for the
  third-party notifications whose internals aren't documented, so the
  filtering for them can be built on observed data rather than guesswork.
  No player-visible change.

## [0.30] — 2026-09-07

### Fixed

- Select All / Deselect All on the Watchlist's **Neighbors** and
  **Rivals** tabs did nothing at all — they were the only bulk actions
  that needed to know which country you are, and the way they asked for
  that didn't work. They now use a reliable reference to your country.
  (The Great Powers and Watched tabs were unaffected, which is why only
  those two tabs misbehaved.)

## [0.29] — 2026-09-07

### Added

- Debug logging of relational notification decisions (`SNW_FILTER` lines
  in `debug.log`), recording whether each diplomatic play was elevated or
  quieted and which countries were involved — for tuning during testing.

## [0.28] — 2026-09-07

### Fixed

- The Watchlist's Neighbors tab was listing countries that aren't
  actually your neighbours, which in turn made Select All and Deselect
  All look broken on that tab — they were correct, the list wasn't. The
  Rivals tab had the same underlying flaw. Both now check against your
  own country directly.

## [0.27] — 2026-09-07

### Changed

- Watchlist tab: Deselect All now clears every country shown in that tab,
  full stop — it previously only removed that specific reason a country
  was watched, which could leave a country checked (correctly, but
  confusingly) if it was also watched a different way.
- The Watched tab now has its own Select All (refreshes the whole
  watchlist against your current Great Powers/neighbors/rivals) and
  Deselect All (clears the entire watchlist) buttons.

## [0.26] — 2026-09-07

### Fixed

- The Watchlist tab's Neighbors list no longer renders with overlapping,
  garbled text — its four continent groups now stack properly instead of
  drawing on top of each other.

### Added

- The Watched list now shows small tags next to each country explaining
  *why* it's watched (Great Power / Neighbor / Rival / manually added),
  so it's clear when a country stays checked after a category's Deselect
  All because it's also watched for a different reason.

## [0.25] — 2026-09-07

### Added

- The Watchlist now actually affects notifications: a diplomatic play
  starting, someone joining a side, or a play turning into war is now
  toast/popup only when a country you're watching (or you) is involved —
  otherwise it stays in the quiet background feed.

### Changed

- As a result of the above, dominions/subjects auto-joining their
  overlord's side no longer spam a toast for every single one — only
  when the play itself involves someone you're watching.

## [0.24] — 2026-09-07

### Fixed

- Checking a country from the Great Powers, Neighbors, or Rivals list now
  correctly records *why* it's watched, instead of always recording it as
  a manual addition — this was causing that category's Deselect All to
  silently skip countries you'd hand-checked from it.

### Changed

- The Watchlist tab's Neighbors list, which can get long for a
  colonial-holding country, is now grouped by continent (Europe / Africa
  / Asia / Americas) instead of one long flat list.

## [0.23] — 2026-09-07

### Added

- **Select All / Deselect All** buttons on the Watchlist tab's Great
  Powers, Neighbors, and Rivals sections — bulk-add or bulk-remove every
  country currently matching that category in one click, without
  affecting countries watched for a different reason.

### Changed

- The Watchlist tab's **Neighbors** and **Rivals** sections now show
  everyone currently matching that category (adjacent to you / a
  declared rival), not just countries flagged earlier — so a newly
  neighboring or newly rivaled country shows up immediately instead of
  needing a manual re-add.

## [0.20] — 2026-09-07

First real commit to version control — everything up to and including this
point had only ever existed as the repo's initial skeleton. Rolls up
Phases 0–1 plus the first two pieces of Phase 3; see [TODO.md](TODO.md) for
what's still in progress (the Country Watchlist tab in Message Settings is
present but has a known unresolved bug — checkbox state doesn't visibly
toggle — so it's not listed as shipped below).

### Added

- A one-time "Smart Notifications active" toast when starting a campaign,
  confirming the mod is loaded. Can be muted from Message Settings like any
  other notification.
- Two new Message Settings categories, split out from vanilla groups so
  siblings that deserve different priority can actually have it: **Invasion
  (Against Us)** and **Subject Released (Ours)**.
- A new **Truce Expired** notification: a toast when a truce with another
  country runs out, naming which country. Confirmed working in a live game
  2026-09-06.
- A new **top-ribbon alert** for when an amendment on one of your active
  laws can be repealed without contesting a fresh enactment vote — vanilla
  computes this condition already but never surfaced it. (Not yet
  confirmed in a live game — see TODO.md.)

### Changed

- Elevated to `toast` (from `feed`): `country_swayed`, `sway_offer_accepted`,
  `reverse_sway_offer_accepted`, `sway_offer_rejected`,
  `reverse_sway_offer_rejected`, `diplomatic_demand_accepted`,
  `diplomatic_demand_rejected`, `invasion_started_against_us` (now its own
  group), `diplo_play_subject_released_overlord_notification` (now its own
  group) — diplomatic/military events worth surfacing without blocking
  input.
- Demoted to `feed` (from `toast`): `national_awakening_started`,
  `political_lobby_disbanded`, `political_lobby_disbanded_with_reason`,
  `invasion_started`, `invasion_succeeded`, `invasion_failed`,
  `diplo_play_subject_released_notification` — historical/planned/
  third-party events that don't need center-screen attention.
- Muted entirely (`none`): `country_attitude_improved`,
  `country_attitude_changed`, `country_attitude_worsened`,
  `country_conscription`, `harvest_condition_started_in_country`,
  `harvest_condition_started_in_market`, `foreign_political_lobby_disbanded`,
  `foreign_political_lobby_disbanded_with_reason` — high-frequency,
  low-agency noise (harvest conditions alone fired 106 times in a single
  test session, with zero player agency over the weather).
