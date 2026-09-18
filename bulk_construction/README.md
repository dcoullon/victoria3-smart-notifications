Build All: Bulk Construction, One Click
=======================================

A separate Victoria 3 mod living in this repo alongside Smart Notifications and
`better_decision_info/`. Own `metadata.json`, own mod id (`bulk_construction`),
own Workshop entry. It shares this repo's `tools/` and `reference/` and follows
the same CLAUDE.md protocol.

**It does not cheat.** Its button is the game's own build button, pressed for
you -- normal queue, normal cost, nothing the player could not have clicked
themselves. That rule is enforced on every validation run by
`check_no_cheat_verbs` in `tools/check_references.py`, not remembered at
release time. See spec section 1a.

**What it does:** in the construction panel you already use -- pick a building
from the bottom bar, the "select in which State to build" list opens -- it adds
a 1 / 5 / 10 level stepper and one button that queues that building in every
state the panel is currently listing as valid.

Design, locked scope, engine findings and acceptance criteria:
[docs/bulk-construction-spec.md](../docs/bulk-construction-spec.md).
Player-facing history: [CHANGELOG.md](CHANGELOG.md).

Current state: **feature-complete, confirmed in a live game 2026-09-16.** All
six acceptance criteria in spec section 4 passed against a real construction
queue. The whole mod is two files -- one `.gui` and one `.yml`; there is no
`common/` any more, because the diagnostic scripted GUI that used to live there
was removed once the mechanism was proven.

Validate with:

    python tools/validate_syntax.py bulk_construction --strict

Package for upload with (never upload the dev junction):

    python tools/package_release.py bulk_construction
