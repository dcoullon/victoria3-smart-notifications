# Better Decision Info — second mod in this repo

**Currently empty of content.** Its first feature (event tooltip enrichment)
turned out to be localization-only and was merged into Smart Notifications on
2026-09-14 — see `localization/replace/english/smart_notifications_event_context_l_english.yml`
at the repo root.

## What this folder is still for

The split line is **risk profile, not theme**:

- **Smart Notifications** (repo root) — script, plus localization overrides.
  Low patch-fragility. Live on the Workshop with real subscribers.
- **Better Decision Info** (this folder) — overrides of **large vanilla `.gui`
  files**. `country_panel.gui` is 4,420 lines and `popups.gui` 5,156; both must
  be re-diffed against vanilla after every patch, and both collide with any
  other mod touching the same screen.

A `.gui` override must sit at the exact vanilla path, so it cannot be isolated
within one mod. The mod boundary is the only isolation boundary available.

The event feature moved because it never needed a `.gui` file at all — it is
seven replaced loc keys and produces zero `error.log` output, so it does not
carry the risk this folder exists to contain.

## Planned content

From `docs/followup-plan-2026-09-11.md`:

- **2a(ii)** alliance / defensive pact / guarantee rows on the country panel
- **2a(i)** predicted joiners on the diplomatic play start screen

**Read before starting either:** the Community Mod Framework
(Workshop `3385002128`, [GitHub](https://github.com/Victoria-3-Modding-Co-op/Community-Mod-Framework))
exists specifically to deconflict mods that override GUI files, and warns that
it "will collide with other mods that touch these files". Check which files it
patches, and whether it offers an extension hook for the country panel —
building on it would beat a full-file override.

## Tooling

```
python tools/validate_syntax.py better_decision_info
```

Checks that assert Smart Notifications' own content are gated on the mod id,
so they do not fire against this folder.
