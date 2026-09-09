# Victoria 3 Modding Agent Protocol

Detailed rationale and "how we confirmed this" for the rules below lives in
[docs/engine-notes.md](docs/engine-notes.md) — read the relevant section
there before relying on one of these in new code. This file stays a terse
checklist on purpose; don't add narrative/rationale here, add it there and
link it.

## 1. Git Authorship Rules

- Never include "Co-Authored-By", AI mentions, or session URLs in git commit messages or PR descriptions.
- Commit (and push to GitHub) every time a new feature ships — no batching multiple features into one commit.
- **Bump `.metadata/metadata.json`'s `version` by `0.01` ONLY for something genuinely new that is confirmed working** (`0.20` → `0.21`); the tenths digit is a major milestone. **Do NOT bump for bug fixes, iterations on a feature that isn't working yet, debug instrumentation, or doc-only changes** — those still get their own commit, just no version bump (revised 2026-09-07 per the user: repeated bumps for fix-attempts on the same unfinished feature make the version meaningless). See CHANGELOG.md's own header for the full convention.

## 2. Token Budget & Large File Protocol (CRITICAL)

- NEVER dump entire multi-thousand-line vanilla game files into context. Use targeted search (`grep`/`Select-String`) or a narrow line-range read instead.
- For broad exploration/schema-mapping across large vanilla files, hand the user a tailored prompt for their Gemini Gem rather than reading everything yourself (same for any other sufficiently large/open-ended task — see `docs/engine-notes.md` if unsure where the line is).

## 3. Engine & Syntax Rules

- Message configs live in `common/messages/*.txt` (NOT `notification_types` — doesn't exist; don't confuse with the unrelated `common/map_notification_types`).
- Visibility: `notification_type = none | feed | toast | popup` (NOT `window_type`).
- Player Message Settings overrides apply per `group`, not per message key, and persist until the player resets — see engine-notes.md § Override hierarchy before touching any `notification_type`.
- `post_notification = <key>` takes a bare key only, no per-call override. Situational priority needs separate keys/groups chosen in script — never force mismatched siblings into one group (triggers a "mixed Notification Types" engine warning).
- Logic (`.txt`) lives in `/common/` and `/events/`, lowercase snake_case. Layouts (`.gui`) live in `/gui/`, Jomini declarative syntax.
- Localization (`.yml`) lives in `/localization/english/`, must begin with `l_english:`.
- **UTF-8 BOM required on every modded `.txt`/`.gui`/`.yml`** — the `Write` tool doesn't add it; see engine-notes.md § BOM for the one-liner to add it after writing a new file.
- **`.json` files (`.metadata/metadata.json`) are the opposite: NO BOM, ever.** A BOM is not valid JSON syntax under a strict parser and breaks the Paradox launcher's mod metadata parsing outright. See engine-notes.md § JSON files must not have a BOM.
- Scripted GUIs in `common/scripted_guis/` MUST include `ai_is_valid = { always = no }` and `ai_chance = { base = 0 }`.
- Dynamic text (anything in `[...]` brackets — loc, tooltips, `debug_log`) uses `THIS`/`SCOPE.sX('name')`, NEVER `root`/`scope:x` — that's effect/trigger-only syntax. See engine-notes.md § Dynamic text vs. effect/trigger syntax.
- **A literal `[...]` bracket in loc text is never just text** — it's always parsed as a dynamic-text function call, no escape exists. Never use square brackets as a visual tag/decoration in a loc string; use parentheses instead. See engine-notes.md § Literal `[...]` in loc text.
- A country's name in dynamic text/loc/`debug_log` is `.GetNameNoFormatting`, **never** plain `.GetName` (the latter errors outright: "Could not find data system function"). See engine-notes.md § `GetName` is not a valid dynamic-text function.
- **A function confirmed real in a `.gui` file's own bindings (`onclick`/`text`/`widgetid`) is NOT evidence it works in dynamic text.** `.gui` bindings and script-side `[...]`/`custom_tooltip`/`debug_log` dynamic text are two separate function tables. Precedent for a dynamic-text call must come from another dynamic-text call, never from a `.gui` file. See engine-notes.md § Two separate function tables.
- The debug-logging effect is `debug_log`, not `log` (which doesn't exist) — writes to `debug.log`, not `game.log`.
- Before applying a country-only trigger (e.g. `is_player`) to a scope, confirm that scope is actually a country — several on_actions root on Diplomatic Play/Demand/Action instead. See engine-notes.md § Scope types are not all countries.
- Any brand-new message group or alert type this mod introduces (not a vanilla one we only re-tuned or split) gets a `"(SN) "` prefix on its Message-Settings-visible label (a message's `group` loc, or an alert's `_name` loc), and on any standalone in-panel UI label this mod adds to a vanilla screen (e.g. an opt-in checkbox's own text) — never on the in-game toast/popup body/desc text itself. See engine-notes.md § Tagging mod-created notifications.

## 4. Autonomous Quality Assurance

- After creating or modifying any `.txt`, `.gui`, or `.yml` file, always run:
  `python tools/validate_syntax.py`
- Fix any reported bracket/encoding issues immediately before finishing.
- `validate_syntax.py` also flags a short list of confirmed-real, repeated-mistake patterns (uncast `SCOPE.GetRootScope`, `any_X` inside an `effect`, effect keywords inside a `valid`/`limit` trigger block) — fix any of these before finishing too, same as a bracket error. See engine-notes.md § Known mistake patterns before adding a new one to that list.
- `validate_syntax.py` also runs `tools/check_references.py`: static cross-file checks (undefined `custom_tooltip` loc keys, a `GetScriptedGui` reference or a scripted-gui-shaped block outside `common/scripted_guis/`, an `alert_group` used but not declared, missing alert loc keys, and law-type-list drift across this mod's generated per-law files). These catch bug classes that previously required a live playtest to notice — add a new check there whenever a bug is found that a static scan could have caught.

## 5. Other

- Game install: `C:\Program Files (x86)\Steam\steamapps\common\Victoria 3`
- Distribution constraints (Steam/Paradox mod policy, download expectations): `docs/distribution-guidelines.md`.
- To check whether something is actually working without asking the user to test again: `python tools/scan_logs.py` filters the live `error.log`/`debug.log` down to this mod's own `SNW_*` debug lines and known engine-error signatures — never dump a full log into context instead. Slash commands `/validate-mod`, `/compare-notifications`, `/scan-logs`, `/package-release` wrap this and the other `tools/*.py` scripts for direct human use.
- **Never upload straight from the dev mod folder/junction** — the Paradox Launcher bundles its entire target directory, including this repo's `tools/`, `docs/`, `reference/`, `.git/`, and root-level docs. Run `python tools/package_release.py` first (see engine-notes.md § Never upload the dev mod folder directly) to build a clean copy at a separate mod entry, and upload from that instead.
- **Every time we're about to release a new version externally (a Workshop upload, sharing the mod outside local testing) — the user wants this called out explicitly, every time, not assumed remembered:** remind them to run `python tools/package_release.py` (or `/package-release`) and to upload from the `smart_notifications_release` folder, never the dev junction.
