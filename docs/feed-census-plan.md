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

## Order of work

1. `tools/build_census_mod.py` + the throwaway mod folder and its junction.
2. Verify on a short run that `SNW_CENSUS|` lines actually appear, and that the
   game loads with ~190 overridden vanilla files without new `error.log` noise
   beyond the expected. **Verify the instrument before trusting it** — a blank
   result usually means the tap is broken, not that nothing fired.
3. The mod-key → vanilla-key mapping table for the split families.
4. `scan_logs.py --census`.
5. One long passive session (the real cost, and the user's time not the
   agent's). Ideally 1836 → 1900+ for the growth curve.
6. Analysis, then the tuning decisions and the post.

## Rules that apply

- `python tools/validate_syntax.py` after touching any `.txt`/`.gui`/`.yml`.
- UTF-8 **BOM** on every modded `.txt`; **never** on `.json`.
- The census build gets its own mod id and junction. Never add it to the
  Smart Notifications playset entry, and never let `package_release.py` see it.
- Changing a `notification_type` default now costs something: a player's stored
  setting overrides the mod until they press Reset to Default Settings, so any
  retune that comes out of this needs a line in the release notes.

## Open question for the user

Whether to also instrument `events/`. It is the largest bucket (166 keys, 62
toast) and the generator handles it at no extra effort — but it means
overriding 190-odd vanilla event files in the measurement build, which will
produce a noisy load. Worth doing for completeness; worth checking the load
time and `error.log` before committing to it.
