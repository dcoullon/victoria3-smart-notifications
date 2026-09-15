One-Click Electrification — spec for a separate mod
===================================================

Written 2026-09-15. **Separate mod, not part of Smart Notifications** —
different audience, different risk profile, and a second Workshop entry is a
second shot at discovery.

Origin: the user's own idea, recorded in the WIP doc as "One button to build
power plant in all states", and Purgii's Reddit comment about menu-diving.

## 1. What it does

**One click queues one Power Plant in every state where the player could build
one right now, at normal cost, through the normal construction queue.**

Explicitly **not** a cheat mod. No instant buildings, no free buildings, no
bypassing tech, laws or the queue. This constraint decides the whole design
and must not be relaxed — the audience overlaps with Smart Notifications'
subscribers, and a cheat reputation would damage both.

## 2. Key engine findings (all verified 2026-09-15)

### There is only one power plant building

`building_power_plant` (`common/buildings/06_urban_center.txt:71`), group
`bg_power`. Fuel type is a **production method**, chosen after the building
exists: `pmg_base_building_power_plant` → `pm_early_power_plant`,
`pm_coal-fired_plant`, `pm_oil-fired_plant`.

So the game exposes **no plant-type choice at build time**, and neither should
we. The user's recollection was right. This removes the single biggest design
question.

Its own gating:

```
unlocking_technologies = { electrical_generation }
possible = { owner = { NOT = { has_law_or_variant = law_type:law_industry_banned } } }
```

### `start_building_construction` is the honest primitive

State-scope effect, confirmed at runtime in vanilla events
(`agitators_election_events.txt:6841`, `land_ownership_law_events.txt:1577`).
Its own effect localization is `START_BUILDING_CONSTRUCTION: "Start building
[BuildingType.GetName] in [State.GetName]"` — it **starts a construction**, it
does not conjure a building.

**Do not use `create_building`.** It exists and is easier, but it creates a
finished building instantly and free. That is the cheat path.

### `can_construct_building` lets us follow the game's rules instead of copying them

`can_construct_building = building_X` is a confirmed real **state-scope
trigger**, used by vanilla exactly the way this mod needs, e.g.
`common/script_values/india_values.txt:3`:

```
every_scope_state = {
    limit = { can_construct_building = building_cotton_plantation }
    add = this.free_arable_land
}
```

This is the answer to "don't duplicate the game's logic, just follow it".
Whatever the game requires — technology, laws, urbanisation, resources,
ownership — is inside that one trigger. **Never hand-roll a tech check.**

### Vanilla already defines "does this state need a power plant"

The power plant's own `ai_value` block carries the exact condition:

```
NOR = {
    has_building = building_power_plant
    any_scope_building = {
        is_building_type = building_power_plant
        is_under_construction = yes
    }
}
```

Reuse it verbatim. It handles "already has one" and "one is already queued" in
one go — the second is what stops a double-click queueing two.

### Decisions give a player-facing UI with **zero `.gui` override**

`common/decisions/` is a real Vic3 feature with its own panel
(`gui/decisions_panel.gui`). A decision is country-scoped and needs only
`is_shown`, `possible`, `when_taken`, `ai_chance`
(`common/decisions/000_decisions_help.txt`).

This is the single most important finding for scoping: **the MVP needs no GUI
file at all**, so it has no file-override compatibility surface and no
re-diff burden on patches. That is a categorically cheaper mod than anything
in this repo so far.

Two free wins from the decision system:

- **No cooldown field exists** — decisions are repeatable by default. One-time
  behaviour is opt-in via a variable guard (see `revive_olympic_games_decision`).
  Repeatable is exactly what this needs: click again when tech or borders change.
- **`EFFECT_SUMMARY`** auto-generates the tooltip's effect description from the
  effect block, so the player may see what will be built before clicking. Worth
  checking how it renders over an `every_scope_state` loop — it could be
  excellent or unreadable.

## 3. MVP

```
sn_electrify_all_states_decision = {
    is_shown  = { has_technology_researched = electrical_generation }
    possible  = { any_scope_state = { <the vanilla needs-a-plant condition> } }
    when_taken = {
        every_scope_state = {
            limit = {
                can_construct_building = building_power_plant
                NOR = {
                    has_building = building_power_plant
                    any_scope_building = {
                        is_building_type = building_power_plant
                        is_under_construction = yes
                    }
                }
            }
            start_building_construction = building_power_plant
        }
    }
    ai_chance = { value = 0 }
}
```

`ai_chance = { value = 0 }` is mandatory — the AI must never take this (the
same spirit as CLAUDE.md's scripted-GUI rule).

### Acceptance criteria — write them before the code

- With the tech and at least one eligible state, the decision is visible and
  enabled; taking it queues exactly one Power Plant in **every** eligible
  state and **none** anywhere else.
- Taking it twice in a row queues nothing the second time (the
  `is_under_construction` guard).
- Without `electrical_generation`, the decision does not appear.
- Under `law_industry_banned`, nothing is queued (via `can_construct_building`,
  not a hand-written law check).
- Zero new `error.log` lines.

Checked by: a `SNW_*`-style `debug_log` line per queued state, read back with
`scan_logs.py`, plus one human look at the construction queue. Most of this is
verifiable in a single session.

## 4. Open questions to resolve before building

1. **Does `start_building_construction` validate, or force?** If it queues
   regardless of `can_construct_building`, our `limit` is doing all the work
   and must be right. If it validates internally, the `limit` is belt and
   braces. Either way keep the `limit`; but knowing which decides whether a
   bad `limit` fails loudly or silently.
2. **How many levels does one call queue?** Assumed 1. Confirm before
   promising "one power plant per state".
3. **Does `EFFECT_SUMMARY` render usably** over an `every_scope_state` loop, or
   does it produce a wall of text? Decides whether the tooltip needs a
   hand-written `_tooltip` loc instead.
4. **Where does the decision appear, and is it discoverable?** The decisions
   panel is not somewhere Vic3 players look often. If discoverability is bad,
   the fallback is a button on a vanilla panel — which costs a `.gui` override
   and changes the mod's risk profile entirely. Check this **before** building,
   because it decides whether the "no GUI override" advantage is real.
5. **Construction queue cost.** Queueing 20 plants at once could wreck a
   budget. Decide whether that is the player's problem (probably yes — it is a
   queue they can cancel) or whether the tooltip should state the count.

## 5. Phase 2 — after the MVP works

- **Filters**: incorporated vs unincorporated states; only states already
  urbanised; only states above a population threshold.
- **Foreign states via investment rights.** The user explicitly wants this.
  Needs its own investigation: the game routes foreign construction through
  the investment pool, and it is not established that
  `start_building_construction` works in a state the player does not own, nor
  that `can_construct_building` evaluates correctly there. Note the user's own
  point — the *hosting* country needs the technology, not the investor. Treat
  as unknown until probed.
- **Multiple levels at once** — needs finding (2) answered first.

## 6. Naming and distribution

- Separate `metadata.json`, separate Workshop entry.
- The `(SN) ` tagging rule in CLAUDE.md §3 belongs to Smart Notifications; this
  mod needs its own prefix convention if it ever adds labels to vanilla panels.
  The MVP adds no labels to vanilla panels at all.
- Same release discipline applies: `python tools/package_release.py` and upload
  from the clean folder, never a dev junction.
