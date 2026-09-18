Bulk Construction — spec
========================

Written 2026-09-16. Supersedes the entry-point question left open in
[electrification-mod-spec.md](electrification-mod-spec.md) §1b, and widens that
mod's scope from power plants to every building type. That document stays as
the record of the power-plant-specific engine findings (there is only one power
plant; fuel is a production method, not a build-time choice); this one is the
design we build.

**Separate mod, sibling folder in this repo** (`bulk_construction/`, alongside
`better_decision_info/`), own `metadata.json`, own Workshop entry, shares
`tools/` and `reference/`.

## 1. What it does

In the construction panel the player already uses — pick a building from the
bottom bar, the "select in which State to build" list opens — add:

- a **level stepper** (1 / 5 / 10) below the existing filters,
- a **bulk build button** reading *"Queue N levels in the M states below"*,

which queues N levels of the selected building in every state the panel is
currently listing as valid, through the normal construction queue, at normal
cost.

## 1a. The no-cheat guarantee

**Hard rule, restated by the user 2026-09-16 and binding on every version of
this mod: we fix the UX, we do not change the rules of the game.** No
`create_building`, no instant buildings, no free buildings, no bypassing tech,
laws, cost or the queue.

The architecture makes this structural rather than a promise. The action we
fire, `MapListOption.OnClick`, is *literally the same call the row's **+**
button makes* — `gui/map_list_panel.gui:230`, inherited unchanged by the
construction row. We do not reimplement building, pricing, funding or
eligibility, so there is nothing to get wrong in our favour: N clicks of our
button and N clicks of the player's **+** are the same N calls.

### Where it could have leaked, and why it does not — settled in game

The **+** button is gated by `enabled = "[MapListOption.CanClick]"` (`:229`),
and **`enabled` is a widget property, not an engine check**. It stops a human
clicking a greyed-out row; it does not stop us calling `OnClick` from a widget
state. The obvious mitigation — put `visible = "[MapListOption.CanClick]"` on
the firing widget — turned out not to work either: `visible` gates nothing at
all (§3).

So for a while this mod had an ungated action and a fake guard. What resolves
it is not a guard we wrote but a fact about the engine, measured in a live
game on 2026-09-16:

> The button offered **44** states. **39** were queued. The 5 skipped were rows
> whose `+` is greyed out because they are at their level cap.

**`MapListOption.OnClick` validates internally and silently refuses an option
the player could not click.** Vanilla's own `+` greys out on existing *plus
queued* levels, so that check already accounts for pending queue items, and a
multi-level press cannot overshoot a cap either.

That is a stronger guarantee than anything we could have written, and it is the
reason the design survives: we iterate `AccessValidOptions`, never the Failed
or Invalid lists, and the engine refuses whatever is left that it should.

Two consequences that still bind:

- The level stepper repeats the *same* call N times. It never reaches for a
  "build N levels" shortcut that would skip the engine's per-call check.
- Nothing in this mod touches the treasury, construction points or build time
  — not to charge, and not to discount. Whatever the **+** costs is what our
  button costs.

### Locked scope (user decisions, 2026-09-16)

| question | decision |
|---|---|
| Where it lives | Sibling folder in this repo, separate Workshop entry |
| Semantics | **Add N levels everywhere** the player could build it — not "top up to N", not "only empty states" |
| First shippable build | Button + all building types + level stepper + live count |
| Abroad / foreign states | **In**, by reusing the panel's own valid-option list rather than re-deriving eligibility |

The abroad decision is the one that sets the architecture: we do not write our
own eligibility rules, we drive the list the game already computed.

## 2. Engine findings (verified 2026-09-16 against the 1.13 game files)

### One 35-line type, redefined from our own file — the filename is load-bearing

The window is `build_building_map_list_panel`
(`gui/map_list_panel.gui:1091-1123`), a derived type of `map_list_panel` with
just two blockoverrides, `headers` and `item`. The filters the player sees
(Location All/Domestic/Abroad, List item, Workforce) are `construction_filters`
(`:2433`).

**A mod can redefine that one type from its own `.gui` file — if its filename
sorts first.** The engine keeps the FIRST definition of a type that it reads,
and files are read in name order. `00_bulk_construction_map_list.gui` sorts
ahead of vanilla's `map_list_panel.gui` and wins.

This cost two playtests to learn. An identical earlier attempt named
`zz_bulk_construction_types.gui` sorted *after* vanilla and silently lost: it
parsed with zero errors, was the only mod enabled, and the panel simply
rendered vanilla's version — no warning, no duplicate-type error, nothing. The
conclusion drawn at the time ("there is no partial `.gui` override in this
engine") was **wrong**, and a whole-file override of all 5,212 lines was
written and shipped before the real rule was found.

What found it was reading the **Community Mod Framework**, which does exactly
this and names its files `00_MPM_building_browser_panel.gui`. The lesson is
cheap to state: before inventing a mechanism, look at what a shipped framework
already does.

The whole-file override is gone. The patch-fragility surface is now this one
type. `check_bc_gui_filename_still_sorts_first` fails the build if the file is
ever renamed, because a rename is the one edit that breaks this mod without
breaking anything else.

### The game hands us the eligibility list for free

`MapListPanel.AccessValidOptions` is a datamodel of `MapListOption`, and each
option carries:

- `MapListOption.OnClick` — the exact thing the row's **+** button calls, i.e.
  "queue this building in this state";
- `MapListOption.CanClick`, `GetStateData.GetState`, `GetBuildingData`.

The panel also separates `AccessFailedOptions` and `AccessInvalidOptions` —
states where the build is not currently possible. **Valid = what the player
could click right now**, which is exactly the chosen semantics, and it already
accounts for domestic vs. abroad, investment rights, technology, laws,
resources and urbanisation without us restating any of it.

`GetDataModelSize(MapListPanel.AccessValidOptions)` gives M for the button
label. `MapListBuildingPanel.GetBuildingType` gives the selected building, and
`MapListBuildingPanel.HasFilter` / `SetFilter` expose the panel's own filter
state.

### Firing must be hand-triggered, never on creation

A widget state can run a datafunction, and the tempting form is
`state = { trigger_on_create = yes  on_finish = "[...]" }` (vanilla:
`gui/journal_entry_widgets/ep2_japan_widgets.gui:561`). **Do not use it here.**
Items in a live datamodel are recreated whenever the panel rebuilds, so that
form fires on every rebuild, unprompted — measured at 777 firings in one short
session (§3).

The working form is a *named* state with `on_start` and no `trigger_on_create`,
fired by the button with `PdxGuiTriggerAllAnimations('<name>')` (vanilla:
`gui/character_panel.gui:582`). Measured: one press, one pass, 123 firings
against a panel reading "valid 123", nothing before or after.

The level stepper is built on this directly: each row carries states
`bc_build_1 … bc_build_10`, and the button for N triggers the first N of them.
Because a trigger sweeps all rows before the next one fires, levels are queued
**level-by-level across states** rather than state-by-state — every state gets
its first level before any gets its second. Confirmed in game, and the better
behaviour: a bulk order cancelled halfway leaves the empire evenly covered.

### What the script route would have cost

Worth recording, because it is the fallback if the above misbehaves.
`start_building_construction = building_X`
(`common/effect_localization/00_state_region_effects_loc.txt:27`, used in
`events/agitators_events/agitators_election_events.txt:6841`) takes a **bare
literal key** — it cannot take a variable. Since `can_construct_building` is
likewise literal-only, a script implementation needs **one generated scripted
GUI per building type** (104 building types in `common/buildings/`) plus 104
`EqualTo_string(BuildingType.GetKey, ...)` dispatch branches in the `.gui`, and
`every_scope_state` only ever iterates states you own — so the abroad case would
be out of reach anyway. The GUI-native route is strictly better if it works.

## 3. The one real risk: runaway iteration

`AccessValidOptions` is a live datamodel. Queueing a building changes the panel,
the datamodel refreshes, widgets are recreated, `trigger_on_create` fires
again — and the mod queues buildings every frame until the treasury is gone.
`datamodel_reuse_widgets = yes` on this panel makes the recreation behaviour
less predictable, not more.

This is the thing that could damage a player's save, so it is designed for
before it is written:

- the auto-click container is **only instantiated while a one-shot GUI variable
  is set**, and the container's own creation clears that variable
  (`GetVariableSystem.Clear`) — a latch, not a flag;
- the N-level repeat is N sequential passes of the same latch, never a
  free-running loop;
- first test is on a throwaway save, paused, with a small country.

If the latch cannot be made reliable, fall back to the script route in §2 and
drop the abroad case to Phase 2. **Do not ship a version that can fire twice.**

## 4. Acceptance criteria — confirmed in-game 2026-09-16

All verified by the user in a live game, against a real construction queue.

1. **Queues exactly the chosen levels, in the government queue.** Levels = 1
   queued one level per buildable state, in the right order. Confirmed.
2. **Level stepper works, and interleaves.** Levels = 5 queued 5 per state,
   ordered level-by-level across states rather than all of one state then the
   next — i.e. every state gets its first level before any gets its second.
   That falls out of triggering `bc_build_1` across all rows, then
   `bc_build_2`, and it is the behaviour we want: a bulk order that is
   cancelled halfway still leaves the empire evenly covered.
3. **It cannot build where the player could not.** The button offered 44
   states; 39 were queued. The 5 skipped were rows whose `+` is greyed out
   because they are at their level cap. **`MapListOption.OnClick` validates
   internally** — it silently refuses an option the player could not click.

   This is the finding that retires the guard problem in §1a. `visible` never
   gated anything (see §3), so no GUI-side guard was available — and none is
   needed, because the engine enforces it. Vanilla's own `+` greys out on
   existing *plus queued* levels, so the cap check already accounts for
   pending queue items and a multi-level press cannot overshoot a cap.
4. **The displayed count is a ceiling, not a promise.** 44 shown, 39 built;
   and in an Abroad-filtered panel on 2026-09-18, 6 shown and 1 built. A
   listed row can still refuse: `MapListPanel.AccessValidOptions` is what the
   panel lists, but `MapListOption.CanClick` is the per-row "this one will
   actually build" flag, and it can be false on a listed row.

   **A filtered count is impossible in GUI. Settled 2026-09-18 against the
   engine's own datafunction dump** (`reference/data_types/`), which replaced
   the earlier inference from vanilla usage. The complete datamodel API is
   nine functions and not one folds a predicate over the rows; `SkipLast`
   was the only one the vanilla-usage survey had missed, and it does not
   help. Accumulating per row fails too: `GetVariableSystem` has no
   arithmetic, and a widget `state` has no condition field, so "run only
   where `CanClick`" has no form. See engine-notes § The GUI layer cannot
   count a filtered datamodel.

   So the button reads **"Queue N levels in up to M states"** (changed
   2026-09-18 after the user pointed out that "in 6 states" oversells a panel
   where 5 are locked), and the tooltip names what gets skipped and why. The
   number is honest as a ceiling; there is no honest exact number available.
5. **One press is one pass.** Measured before `OnClick` was wired in: 123
   firings against a panel reading "valid 123", in a single burst, nothing
   before or after. See §3 for what the rejected design did instead.
6. Zero `error.log` lines attributable to this mod.

## 5. Explicitly out of the first build

- Any new filter of our own (the "Incorporated only" toggle, a nice-to-have) —
  the panel's existing Location filter comes for free, ours would not.
- **A "Max" level option.** Deferred 2026-09-16 by the user: wait until the
  mod has been used in a real game and players have asked for it after public
  launch, rather than guess at the right ceiling now. There is also no GUI
  path to a per-state cap, so it would have to be an arbitrary large number.
- A queue-cost preview or treasury warning. The player can cancel a queue.
- Private-funding variant (`start_privately_funded_building_construction`
  exists, but the GUI-native route inherits whatever funding the row's **+**
  uses, which is the correct default).
- Touching Smart Notifications in any way.

## 6. Naming and distribution

**Title, chosen 2026-09-16: `Build All: Bulk Construction, One Click`.**
(Mod id stays `bulk_construction` — internal, and painful to change after a
publish.)

Why, from a Workshop search survey the same day:

- *"build all button"* is the community's own phrase for this feature — it is
  the wording of the most-linked request thread on the Vic3 forums, and the
  Gemini report independently surfaced it. Nothing on the Workshop claims it.
  `Build All`, `Bulk Build` and `Mass Construction` were all unclaimed.
- The category's top mods (`Auto-Apply PMs`, `Controllable Private
  Construction`, `Supply Chain Semi-Auto Builder`, `Expanded Building List`)
  all use plain functional names. Clever names lose here.
- The subtitle earns the other high-traffic keywords (*bulk*, *construction*)
  and, deliberately, pushes back on the category's autobuild association:
  this shelf is crowded with `Autobuild` and `Semi-Auto Builder` entries, and
  anything that reads as automated invites "is this a cheat?". *One Click*
  says player-driven. §1a says the rest.
- The title is pure ASCII on purpose. The launcher's metadata parser is the
  one component here already known to be picky about encoding (a BOM breaks
  it outright), so no em dash.

Remaining distribution work:

- ~~`tools/package_release.py` is hardcoded to `REPO_ROOT`~~ — **fixed
  2026-09-16.** `python tools/package_release.py bulk_construction` now stages
  this mod into `bulk_construction_release`. (It also turned up a separate
  pre-existing blocker: Smart Notifications could not be packaged at all,
  because the census-freshness check rejected the release staging copy. Also
  fixed.)
- **Mod tag: `(Build All) `**, decided 2026-09-16, on the stepper label and on
  the build button — the two labels this mod adds to a vanilla panel. Not
  `(SN) `, which belongs to Smart Notifications (CLAUDE.md §3).
  **Parentheses, never square brackets.** `[Build All]` was the first
  proposal, and a literal `[...]` in loc is always parsed as a dynamic-text
  call with no escape available — it would have rendered the button blank,
  the same failure as the nested arithmetic in §4. Guarded by
  `check_bc_loc_has_no_bracket_decoration`.
- Release via `package_release.py`, never the dev junction.
