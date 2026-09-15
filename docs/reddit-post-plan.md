# Reddit post — plan and assets

**Target week: 2026-09-22.** Framing agreed with the user: the post must be
useful on its own to r/victoria3, not read as promotion. It gives the findings
away — including the exact Message Settings a player can change by hand — and
mentions the mod only as the shortcut.

## Two pictures (user's call, 2026-09-15)

1. **A feed full of junk.** The user takes this one themselves; no agent
   involvement needed.
2. **An actual count**, vanilla vs the mod. This is the one the census run
   produces and the one that needs building here.

## The hand-tuning reference — the heart of the post

This is what makes the post worth reading for someone who will never install
the mod. Generated from the tier join, **after** the two parser bugs fixed
2026-09-15 (see the commit "Fix two silent errors in the vanilla/mod tier join
table" — before it, this table was wrong).

Vanilla's 106 notification groups sit at: **49 feed, 45 toast, 6 popup, 6 none**.

### Safe to recommend by hand — 13 groups

The mod changes only the tier here. A reader setting these in Message Settings
gets exactly what the mod gives them.

**Quieten — toast to feed (5).** Still there, stops interrupting:

| group | vanilla | recommended |
|---|---|---|
| `harvest_condition_important` | toast | feed |
| `national_awakening_started` | toast | feed |
| `political_lobby_disbanded` | toast | feed |
| `resource_discovery` | toast | feed |
| `war_participant_in_default` | toast | feed |

**Mute outright — feed to none (4).** Noise with no decision attached:

| group | vanilla | recommended |
|---|---|---|
| `country_conscription` | feed | none |
| `foreign_political_lobby_disbanded` | feed | none |
| `harvest_condition` | feed | none |
| `diplomatic_proposal_third_party` | feed | none |

**Make LOUDER — feed to toast (4).** The part that keeps the post from reading
as "turn everything off", and the more interesting half of the argument: the
problem is misallocation, not volume alone. These are decisions with a timer
that vanilla buries in the feed:

| group | vanilla | recommended |
|---|---|---|
| `country_owed_obligation` | feed | toast |
| `country_owes_obligation` | feed | toast |
| `diplomatic_demand` | feed | toast |
| `obligation_expired` | feed | toast |

### Cannot be done by hand — 6 groups

**Do not put these in the recommendation table.** The mod mutes the vanilla
group and posts its own replacement keys, split by whether the player or a
watched country is involved. A reader who sets these to `none` by hand just
loses the notification — there is no replacement without the mod.

`diplo_play_start`, `diplo_play_start_third_party`, `diplo_play_join_side`,
`diplo_play_war_start_third_party`, `diplo_play_subject`,
`diplomatic_action_break` — plus `diplomatic_action` itself.

This is the honest "what the mod adds beyond settings" line, and it is a
stronger pitch than any volume claim: the split is conditional logic, and
Message Settings has no way to express a condition.

## What the count picture can and cannot claim

- **Firing counts** come from the instrumented census build and cover
  everything except the 103 engine-fired keys. Every published figure is a
  **lower bound** — say so in the post. See feed-census-plan.md.
- **Tiers** are not a lower bound and need no run at all: the engine writes its
  own complete resolved tier table to `messagetypes_custom.txt` on exit (128
  groups, exactly matching script). See [[v3-no-engine-notification-log]].
- The run is ~10 in-game years from 1836 as a mid-tier power, so the headline
  is a floor: *even a mid-sized country, in the calmest decade of the game.*

## Still to build

- A machine-readable export from `census_report.py` — it only prints tables.
- The chart itself, developed against synthetic log lines so it is ready when
  the run lands.
