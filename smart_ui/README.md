# Smart UI (working title) — second mod in this repo

A **separate Victoria 3 mod**, developed in this repo alongside Smart
Notifications but shipped as its own Workshop item.

## Why it is separate

The split line is **risk profile, not theme**:

- **Smart Notifications** (repo root) — script under `common/` and `events/`,
  plus small self-contained `.gui` files. Live on the Workshop with real
  subscribers. Low conflict risk.
- **Smart UI** (this folder) — overrides of **large vanilla `.gui` files**
  (`country_panel.gui` is 4,420 lines, `popups.gui` 5,156). High conflict risk
  with other UI mods, and needs re-diffing against vanilla after every game
  patch.

A `.gui` override must sit at the exact vanilla path (`gui/country_panel.gui`),
so it **cannot** be isolated in a subfolder within one mod. The mod boundary is
the only clean isolation boundary available — which is the whole reason this
folder exists.

Shipping these overrides inside Smart Notifications would hand every existing
subscriber a 4,420-line file override they never asked for, and any patch
breakage in it would break the mod that is already live.

## Merging back later

Deliberately kept easy, and it is the safe direction: copy `gui/`, `common/`
and `localization/` into the parent mod, merge the two `metadata.json` files,
done. **The reverse is not easy** — splitting a mod that already has
subscribers means a new Workshop item, lost subscriber count, and stranded
player settings. Starting separate preserves both options; starting merged
forecloses one.

## Scope

Everything here comes from `docs/followup-plan-2026-09-11.md`:

- **2a(ii)** alliance / defensive pact / guarantee rows on the country panel
- **2a(i)** predicted joiners on the diplomatic play start screen
- **2b** population and interest-group context in the event window

## Tooling

Shared with the parent mod, not duplicated:

```
python tools/validate_syntax.py smart_ui
```

`SHIP_DIRS` in `tools/package_release.py` is an allowlist
(`.metadata`, `common`, `events`, `gui`, `localization`) resolved from the repo
root, so this folder is **not** picked up when packaging Smart Notifications.
Packaging this mod needs its own target — not yet wired up, and not needed
until there is something to upload.

## Deployment

Junctioned into the game's mod folder the same way the parent mod is:

```
mklink /J "%USERPROFILE%\Documents\Paradox Interactive\Victoria 3\mod\smart_ui" "<repo>\smart_ui"
```

Then add it to the active Playset in the Paradox Launcher — Mod Library alone
is not enough.
