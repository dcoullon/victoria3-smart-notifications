Why this repo holds several mods
================================

Moved here 2026-09-18 from `better_decision_info/README.md`, when that folder
was deleted. It had been the canonical explanation of the split and was cited
from `tools/check_references.py`, `tools/validate_syntax.py` and
`tools/scan_logs.py`, so it needed somewhere to live that was not a mod.

## The split line is risk profile, not theme

One git repo, several mod folders, each with its own `metadata.json`, mod id
and Workshop entry. What separates them is **how badly a game patch can break
them**, not what they are about:

- **Smart Notifications** — script plus localization overrides. Low
  patch-fragility. Live on the Workshop with real subscribers.
- **Build All** (`bulk_construction/`) — one redefined `.gui` *type*, about 35
  lines, from a file whose name sorts before vanilla's. Also low fragility,
  and deliberately so: see engine-notes § *A partial `.gui` override works*.
- **Anything that overrides a large vanilla `.gui` file wholesale** — the
  category `better_decision_info/` existed to contain. `country_panel.gui` is
  4,420 lines and `popups.gui` 5,156. Both must be re-diffed against vanilla
  after every patch, and both collide with any other mod touching the same
  screen.

A whole-file `.gui` override must sit at the exact vanilla path, so it cannot
be isolated *within* a mod. **The mod boundary is the only isolation boundary
available**, which is the whole reason the split exists: a subscriber to the
low-risk mod should not inherit the high-risk one's patch exposure.

## Why the folder went

`better_decision_info/` never shipped anything. Its one feature, event tooltip
enrichment, turned out to be localization-only — seven replaced loc keys, no
`.gui` file, zero `error.log` output — so it did not carry the risk the folder
existed to contain, and it moved into Smart Notifications on 2026-09-14.

That left an empty mod folder reserving a mod id for work that may never
happen. Deleted 2026-09-18. The reasoning above outlives it, because the rule
applies to whatever comes next, and `git log -- better_decision_info` still
has the folder if it is ever wanted back.

## If that work is ever picked up

The deferred items are **2a(ii)** (alliance / defensive pact / guarantee rows
on the country panel) and **2a(i)** (predicted joiners on the diplomatic play
start screen), specified in
[followup-plan-2026-09-11.md](followup-plan-2026-09-11.md).

**Read this before starting either.** The Community Mod Framework (Workshop
`3385002128`,
[GitHub](https://github.com/Victoria-3-Modding-Co-op/Community-Mod-Framework))
exists specifically to deconflict mods that override GUI files, and warns that
it "will collide with other mods that touch these files". Check which files it
patches and whether it offers an extension hook for the country panel —
building on it beats a full-file override.

That pointer has already paid for itself once: reading the same framework is
what produced the `00_`-filename rule that Build All depends on, after two
playtests had concluded — wrongly — that partial `.gui` overrides were
impossible.
