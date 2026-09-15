# Notification census — build spec

**Written 2026-09-14 as a cold-start handoff.** A session picking this up needs
no other context than this file plus CLAUDE.md. Everything below was measured
against the installed game (1.13.11), not estimated.

## Why

Two goals, one dataset:

1. **Tune the mod.** Which vanilla defaults actually fire often enough to be
   the noise problem? We have been re-tiering notifications on judgement and a
   handful of observations. This replaces that with counts.
2. **A Reddit post**, planned for the week of 2026-09-22 (deliberately spaced
   from the 2026-09-14 post to avoid looking like promotion). The framing
   agreed with the user: the post must be useful on its own — publish the
   findings and the Message Settings players can change by hand — with the mod
   mentioned only as the shortcut.

## BUILD STATUS (2026-09-14, implemented)

Steps 1-4 of "Order of work" are done. What exists now:

- `tools/build_census_mod.py` -- the generator. `--mode calibrate` (run this
  first, short) / `--mode measure` (the long run). Writes to
  `Documents/Paradox Interactive/Victoria 3/mod/smart_notifications_census/`,
  a real directory outside this repo, plus a `census_manifest.json` describing
  every call site.
- `tools/census_scope_overrides.json` -- manual scope verdicts, the place a
  calibrate run's findings get written back.
- `tools/census_report.py`, reached via `python tools/scan_logs.py --census`.

Measured, superseding the estimates below:

| | spec said | actually |
|---|---|---|
| files to override | ~190 | **99** (47 with the events allowlist) |
| call sites instrumented | -- | **400** |
| distinct keys | -- | **384** |

Three corrections to the design as specified:

1. **Player scoping, which the spec did not account for.** `post_notification`
   fires in whatever scope its call site sits in, *including AI countries*,
   and the player never sees those. A raw firing count answers "how often does
   this happen in the simulated world" -- for `diplomatic_action_notification`
   roughly 100x what a player is shown. So each call site is classified, and
   the logging is wrapped in `if = { limit = { is_player = yes } ... }` where
   the scope is confidently a country (`P` lines) and left unguarded otherwise
   (`W` lines). The classifier never guesses COUNTRY without positive
   evidence: guarding a non-country scope reproduces the exact
   `Wrong scope for trigger: diplomatic_action, expected country` error this
   project already hit once. The report keeps `P` and `W` in **separate
   tables** -- mixing them would produce a headline that cannot be defended.
2. **The mod-key -> vanilla-key mapping table is not needed.** The spec called
   it load-bearing. Running the census build *alongside* Smart Notifications
   removes it: the mod cannot suppress a vanilla `post_notification` (its only
   vanilla overrides are `common/messages/00_messages.txt` and two `.gui`
   files, none of which the census touches), so it mutes vanilla keys via
   `notification_type = none` and posts its own key in parallel. Both are
   observed directly and the mute falls out of the tier join. Nothing in the
   report rests on an inferred mapping.
3. **events/ is instrumented selectively**, not wholesale -- see below.

Load order: the census build must sit **after** Smart Notifications in the
playset, since it also overrides SN's own 161 call sites. The two mods share
no other file.

## What already exists

- `common/on_actions/01_smart_notifications_logger.txt` — hooks **32 vanilla
  on_actions**, writing `SNW_LOG|<key>` to `debug.log` for **33 message keys**.
  Append-only: it adds an `on_actions = {}` entry alongside vanilla's, never
  edits a vanilla file. Excluded from releases by `package_release.py`.
- `tools/compare_notification_settings.py --all` — prints every message group
  with its **vanilla tier vs this mod's tier**. This is the join table.
- `tools/scan_logs.py` — filters `error.log`/`debug.log` down to this mod's
  own lines. Extend rather than replace.

## Coverage reality — do not re-derive this

Of **463** vanilla message keys, by where the `post_notification` call site lives:

| call site | keys | of which toast |
|---|---|---|
| `common/on_actions/` — safe append, no vanilla file touched | 100 | 38 |
| other `common/` (journal entries, scripted effects, buttons) | 100 | 82 |
| `events/` only | 166 | 62 |
| **nowhere — engine-fired** | **103** | **41** |

Vanilla tiers overall: 223 toast, 230 feed, 9 popup, 7 none.

**The 103 engine-fired keys can never be measured.** No `post_notification`
call site exists anywhere in `common/` or `events/`, so there is nothing to
hook. They include the original suspected worst offenders —
`country_attitude_improved/changed/worsened`, `country_conscription`,
`country_mobilization`, all four `invasion_*`, both `political_lobby_disbanded*`
and `foreign_political_lobby_disbanded*`, `harvest_condition_started_in_market`.
Confirmed by exhaustive grep, twice. **Do not spend time trying again** — and
do not let a published figure imply these are included.

Consequence: **every number this produces is a lower bound.** Say so in the
post. It is defensible and a better hook than a total that can be picked apart.

## Design

### 1. Generator, not hand-written hooks

The safe append-only pattern reaches just 38 of 223 toast keys. The way past
that: **a measurement build never ships, so it may override vanilla files
freely.**

Write `tools/build_census_mod.py` that:

- reads the installed vanilla tree (`common/`, `events/`) for every file
  containing `post_notification` (~190 files),
- copies each into a **separate throwaway mod folder** (e.g. `census_build/`,
  its own `.metadata/metadata.json`, its own junction),
- inserts a `debug_log` beside every `post_notification = <key>` call,
- is re-runnable and idempotent.

**This mod is never packaged, never uploaded, never merged into Smart
Notifications.** It exists to be run once and thrown away. Add it to
`.gitignore` or keep only the generator, not its output.

### 2. Log the date with every firing

The single change that turns a total into a finding. Emit:

```
SNW_CENSUS|<key>|<year>
```

so volume can be plotted per decade. The expected result — that notification
volume climbs steeply as the world industrialises and fills with countries — is
something nobody has published, and it is a far better hook than one number.
Use the same `debug_log` effect the existing logger uses (**`debug_log`, not
`log`** — `log` does not exist; output goes to `debug.log`, not `game.log`).

### 3. One playthrough gives both columns

The mod changes **which tier a notification displays at**, not how often it
fires. So:

```
volume_vanilla(tier) = Σ firings(key) × [vanilla_tier(key) == tier]
volume_mod(tier)     = Σ firings(key) × [mod_tier(key)     == tier]
```

Both come from the same instrumented run joined against
`compare_notification_settings.py`. **No vanilla control run is needed.**

**The one exception**, and the part most likely to be quietly wrong: where this
mod *mutes a vanilla key and posts its own key instead* from an on_action —
the diplomatic-action family, diplomatic plays, and pact breaks. There the
firing itself differs. Build an explicit mod-key → vanilla-key mapping table
and treat it as load-bearing; do not infer it from names.

### 4. Analysis

Extend `tools/scan_logs.py` with a `--census` mode that reads the run's
`debug.log` and prints:

- firings per key, ranked
- firings per year / per decade, and the growth curve
- the vanilla-vs-mod tier totals from the join above
- counts split into *measured* vs *known-unmeasurable*, so the lower-bound
  caveat is visible in the output rather than remembered later

## Rider: the actor-axis measurement (TODO.md open question 3a)

Added 2026-09-15 at the user's request — "we should measure it first... would be
great if we can do both at the same time". The census run is a long passive
session; question 3(a) needs the same kind of session. One run, both datasets,
no second launch.

`common/on_actions/07_smart_notifications_actor_axis_probe.txt` appends its own
on_action to `on_diplomatic_action` (it does not edit the shipping
`06_..._diplomatic_action_filtering.txt`) and posts nothing. For every
diplomatic action that currently reaches a **toast** — aimed at the player, or
aimed at a watched country — it writes the verdict of three candidate rules,
each independently so all three can be compared from one run:

| rule | would quiet when |
|---|---|
| `rank` | actor is below `major_power` |
| `relevance` | actor has no `has_diplomatic_relevance` to the recipient |
| `type` | actor is not a `recognized` country |

All three triggers were checked against the installed game's `triggers.log`
before the file was written, not generalised from a sibling on_action.

Read it with:

```bash
python tools/scan_logs.py --actor-axis
```

which prints, per cell, how many of the toasts you actually received each rule
would have silenced, plus the actors that reached you most often — because the
percentage alone does not answer the question. The rule judges the sender, not
the message, so whatever it silences it silences completely, including a
rivalry declaration from a small country. The top-actors list is what makes
that trade-off concrete.

The report logic was verified against synthetic log lines before the run, so a
blank result means the probe did not fire, not that the analysis is wrong.

`07_` is in `package_release.py`'s `DEV_ONLY_FILES`, so it cannot ship.

## Run parameters — DECIDED 2026-09-15 (the user)

| | decision | consequence |
|---|---|---|
| span | **~10 in-game years** from 1836 | No growth curve. The headline becomes one total, not a trend. |
| country | **mid-tier** (Sweden / Belgium class) | Not the noisiest country, so the number cannot be dismissed as cherry-picked. |
| build | `--mode measure --events all --sources all` | 109 files, 596 call sites, 526 distinct keys. |
| playset | **Census+SN** (SN at position 0, census at 1) | Required: the actor-axis rider lives in SN, and `--sources all` overrides SN's files. |

**The framing this implies.** A decade from a mid-sized power is a *floor*, not
a worst case: "even a mid-tier country, in the calmest decade of the game, gets
N notifications." That is harder to attack than a Great Britain total, and it
compounds with the coverage caveat below — both push the same direction, so the
post makes one honest claim (this is a lower bound) rather than two.

**Extending to 1849 was offered and is worth taking if the run is going well**:
three more in-game years, and it captures the Spring of Nations, the densest
notification moment in the game.

**Known weakness, do not overstate in the post.** At this span a mid-tier power
may see only ~20-40 diplomatic actions aimed at it. The actor-axis rider's
"would have silenced N of M toasts" is therefore *indicative, not precise*. The
top-actors list still does its job; the percentage should not be quoted as one.

## Order of work

1. ~~`tools/build_census_mod.py` + the throwaway mod folder.~~ DONE.
2. NEXT — **the calibrate run**: verify on a short run that `SNW_CENSUS|` lines
   actually appear, that the game loads 109 overridden vanilla files without new
   `error.log` noise, that the P/W scope verdicts hold, and that the actor-axis
   probe binds `scope:actor`. **One run, four questions** — do not serialise
   these. **Verify the instrument before trusting it** — a blank result usually
   means the tap is broken, not that nothing fired.

   **No `-debug_mode` needed** (settled 2026-09-15): `debug_log` writes
   unconditionally. `-debug_mode` only unlocks the console, and it costs Steam
   achievements. Earlier guidance here and in `census_report.py`'s hint text
   said the opposite; it was never verified.

   **No tier screenshots needed either.** The spot-check in
   `docs/followup-plan-2026-09-11.md` §1.5 existed because a firing log does
   not prove the player saw it at the tier we claim. The engine answers that
   itself: `messagetypes_custom.txt` enumerates every group's resolved tier on
   exit (128 groups, exactly matching script — zero difference either way). Diff
   that file instead of asking anyone to look at a feed.
3. ~~The mod-key → vanilla-key mapping table for the split families.~~ NOT
   NEEDED — see BUILD STATUS correction 2.
4. ~~`scan_logs.py --census`.~~ DONE.
5. The measure run, per the table above.
6. Analysis, then the tuning decisions and the post.

## Rules that apply

- `python tools/validate_syntax.py` after touching any `.txt`/`.gui`/`.yml`.
- UTF-8 **BOM** on every modded `.txt`; **never** on `.json`.
- The census build gets its own mod id and junction. Never add it to the
  Smart Notifications playset entry, and never let `package_release.py` see it.
- Changing a `notification_type` default now costs something: a player's stored
  setting overrides the mod until they press Reset to Default Settings, so any
  retune that comes out of this needs a line in the release notes.

## ~~Open question~~ — RESOLVED 2026-09-15: instrument all of `events/`

Whether to also instrument `events/` wholesale. **Yes.** Measured, not
estimated:

| build | files overridden | call sites | distinct keys |
|---|---|---|---|
| `--events recurring --sources all` | 47 | 400 | 384 |
| `--events all --sources all` | **109** | **596** | **526** |

+142 keys for 62 more overridden files, and the events bucket holds 62 toast
keys — the single largest unmeasured slice. The load-noise worry the original
question raised is not resolved by reasoning about it: **the calibrate run is
the load test**, which is why the calibrate build is made at the exact config
the measure run will use rather than at a smaller one. If the load is bad, that
is what the calibrate run is for and the fallback to `--events recurring` costs
one rebuild.
