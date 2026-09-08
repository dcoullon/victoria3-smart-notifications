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
marks a major milestone; the hundredths digit increments by `0.01` on every
commit that ships a new feature (however small — "added a new
notification" counts), so `0.20` → `0.21` → `0.22`. Not full semver; this
mod hasn't reached a 1.0 concept of "breaking changes" yet.

## [0.33] — 2026-09-07

### Removed

- The GP/NB/RV/MA source tags on the Watched list.

### Added

- Temporary diagnostic buttons and logging on the Watchlist tab, to
  determine why Select All has never worked. To be removed once fixed.

## [0.32] — 2026-09-07

### Fixed

- The Watchlist's Neighbors tab showed only the four continent headers
  with no countries under them — a regression introduced in 0.30.

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
