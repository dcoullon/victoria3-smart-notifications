Build All: Bulk Construction, One Click
=======================================

A separate Victoria 3 mod living in this repo alongside Smart Notifications and
`better_decision_info/`. Own `metadata.json`, own mod id (`bulk_construction`),
own Workshop entry. It shares this repo's `tools/` and `reference/` and follows
the same CLAUDE.md protocol.

**It does not cheat.** Its button is the game's own build button, pressed for
you — normal queue, normal cost, nothing the player could not have clicked
themselves. That rule is enforced on every validation run by
`check_no_cheat_verbs` in `tools/check_references.py`, not remembered at
release time. See spec §1a.

**What it will do:** in the construction panel you already use — pick a
building from the bottom bar, the "select in which State to build" list opens —
add a level stepper and one button that queues that building in every state the
panel is currently listing as valid. Normal construction queue, normal cost.
Not a cheat mod.

Design, locked scope, engine findings and acceptance criteria:
[docs/bulk-construction-spec.md](../docs/bulk-construction-spec.md).

Current state: **probe build**. It queues nothing. It renders a diagnostic row
in the construction panel and writes counted markers to `debug.log` to settle
the three unknowns the architecture rests on. See the header comments in
`gui/zz_bulk_construction_types.gui` and
`common/scripted_guis/bulk_construction_probe_sgui.txt`.

Validate with:

    python tools/validate_syntax.py bulk_construction
