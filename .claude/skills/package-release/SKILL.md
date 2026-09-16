---
name: package-release
description: Build a clean, upload-only copy of the mod (just the folders Victoria 3 loads) separate from this dev repo's tooling/docs, ready to add as its own mod entry for Steam Workshop/Paradox Mods upload. Slash-command only.
disable-model-invocation: true
---

Run:

```
python tools/package_release.py
```

from the repository root. This repo hosts more than one mod; with no
argument it packages the root mod (Smart Notifications). To package a
sibling mod, name its folder:

```
python tools/package_release.py bulk_construction
```

Each mod gets its own output folder, `<mod id>_release`, and its own
launcher entry. Copies only `.metadata/`, `common/`, `events/`,
`gui/`, `localization/`, and `thumbnail.png` (if present) into
`Documents/Paradox Interactive/Victoria 3/mod/<mod id>_release`
— never the dev repo's `tools/`, `docs/`, `reference/`, `.claude/`,
`.git/`, or root-level `.md`/`.bbcode` files, which the Paradox Launcher's
Mod Tools would otherwise bundle wholesale if uploaded straight from the
dev junction.

Refuses to run if `tools/validate_syntax.py --strict` fails on the mod
being packaged — never package known-broken content, and never package
off a DEGRADED pass where the vanilla-comparison checks were skipped
because the game isn't installed (CLAUDE.md §4). Pass `--out <path>` to
write elsewhere, or `--skip-validation` to bypass the check (not
recommended).

**This does not touch the existing dev/test mod entry or its junction** —
live-editing during testing keeps working exactly as before. Add the
`<mod id>_release` folder as its own, separate entry in the
launcher's Mod Library, and upload from *that* entry, not the dev one.
Re-run this script to refresh it before each upload; it only replaces the
folders it manages, leaving any Steam/launcher bookkeeping already
written into that directory untouched.
