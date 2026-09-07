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
