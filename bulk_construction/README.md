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

Current state: **feature-complete, confirmed in a live game 2026-09-16 and
again on the release build 2026-09-18.** All six acceptance criteria in spec
section 4 passed against a real construction queue. There is no `common/` any
more -- the diagnostic scripted GUI that used to live there was removed once
the mechanism was proven -- so the mod is one `.gui`, eleven `.yml` files and
a thumbnail.

Localized into every language the game ships (see `localization/`).
Terminology comes from vanilla's own `concept_state`,
`concept_building_level` and `concept_construction_queue` rather than from
translating English afresh; three guesses would have been wrong if it had not
(Polish *Obszar administracyjny*, Russian *Область*, Turkish *Vilayet*).
Three checks keep the set honest: `check_translations_match_english` (key and
datafunction parity), `check_bc_button_labels_fit` (no label outgrows the
button) and the language-folder/header check in `validate_syntax.py`.

Validate with:

    python tools/validate_syntax.py bulk_construction --strict

Package for upload with (never upload the dev junction):

    python tools/package_release.py bulk_construction
