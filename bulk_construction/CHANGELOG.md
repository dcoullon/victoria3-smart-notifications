# Changelog

All notable player-facing changes to this mod are recorded here, in the
[Keep a Changelog](https://keepachangelog.com/) style: grouped by version, each
version broken into **Added / Changed / Fixed / Removed**. This is the file to
copy from when writing Steam Workshop update notes -- every entry here should
already read like something a player (not a modder) can understand.

Versions follow `metadata.json`'s `version` field, using the same convention as
Smart Notifications (see that mod's CHANGELOG header): `0.XY`, hundredths
increment by `0.01` when something genuinely new ships **and is confirmed
working**; bug fixes, fix-attempts on an unfinished feature, instrumentation
and doc-only changes get a commit but no bump.

## [0.04] - 2026-09-18

### Notes for players

- **The build order follows however you have sorted the list.** Sort by
  Earnings and it builds richest-first. You pick the priority by picking the
  sort. (Confirmed in game; it was always true, it had just never been
  written down.)

### Added

- **All 11 languages Victoria 3 ships**, not just English: French, German,
  Spanish, Brazilian Portuguese, Polish, Russian, Simplified Chinese,
  Japanese, Korean and Turkish.

  Each language's words for *State*, *Building Level* and *Construction
  Queue* were taken from the game's own localization rather than translated
  afresh, so the button uses the same vocabulary as the interface around it.
  The `(Build All)` tag stays in English everywhere on purpose -- it is the
  mod's name, and its job is to say which mod added the row.

  These are not native-speaker translations. If something reads badly in your
  language, say so and it will be fixed.

### Changed

- The build button is wider (500px, was 420px) to fit translations, which run
  10-20% longer than English.

## [0.03] - 2026-09-18

### Fixed

- **The selected level (1 / 5 / 10) now actually shows as selected.** The
  highlight had never drawn: it pointed at a texture file that does not exist
  in the game, which this engine renders as nothing at all, silently.
- **The button no longer overstates how many states it will build in.** It
  reads *"in up to N states"*, and the tooltip explains that states already at
  their maximum level, or where you have no right to build, are skipped. Some
  states the panel lists cannot actually be built in — an Abroad-filtered
  panel showing 6 states may queue only 1 — and the game's interface layer
  offers modders no way to count only the buildable ones, so a ceiling plus an
  explanation is the honest version.

### Removed

- The diagnostic that counted build calls into `debug.log`. It existed to prove
  one press produced exactly one pass, which is now settled, and it was the
  only reason this mod had a `common/` folder. Removing it also closes a real
  release bug: the packaged copy stripped the log line but kept the empty
  scripted GUI and all 26 of its call sites, so a 10-level press across 44
  states would have run 440 no-op script executions in a subscriber's game.

## [0.02] - 2026-09-16

### Added

- **The build-all button.** Pick a building in the construction panel; one
  press queues it in every state the panel currently lists as valid -- foreign
  states included, because the mod reads the game's own eligibility list rather
  than re-deriving one.
- **A 1 / 5 / 10 level stepper.** Levels are queued level-by-level across
  states rather than state-by-state, so every state gets its first level before
  any gets its second. A bulk order cancelled halfway leaves the empire evenly
  covered.
- The button label counts the states it is offering, live.

### Notes for players

- **It cannot build anything you could not.** The action is the row's own **+**
  button, fired once per state; the engine silently refuses any row whose **+**
  is greyed out. Observed in testing: 44 states offered, 39 queued, the 5
  skipped being states already at their level cap.
- The count in the label means "states listed", not "states that will build" --
  hence *"where possible"* in the tooltip. The game's GUI layer offers no way
  to count a filtered list, so showing a product would have meant showing a
  wrong one.
- Normal construction queue, normal cost, no automation.

## [0.01] - 2026-09-16

Probe build, never released. Rendered a diagnostic row in the construction
panel and queued nothing, to settle the three engine unknowns the design rested
on.
