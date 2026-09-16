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

- a **level stepper** (1 / 5 / 10 / Max) next to the existing filters,
- a **bulk build button** reading *"Build N levels across M states"*,

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

### The one place it could leak, and the guard

The **+** button is gated by `enabled = "[MapListOption.CanClick]"`
(`:229`). **`enabled` is a widget property, not an engine check.** It stops a
human clicking a greyed-out row; it does not stop us calling `OnClick` from a
widget state. So if the panel's "valid" list can ever contain an option the
player is not currently allowed to take, firing across the whole list blindly
would do something the game said no to — the exact failure this rule exists to
prevent.

Therefore: **every firing item carries `visible = "[MapListOption.CanClick]"`,
in every version, whether or not the probe shows it is load-bearing.** The
probe measures two things about this directly — whether "valid" implies
"clickable" (counts B vs A), and whether `visible` actually prevents a
`trigger_on_create` state from firing at all (count C, which must be zero). If
C is non-zero the guard is decorative and **the GUI-native design is abandoned**,
not shipped with a weaker guard.

Two further consequences of the same rule, for later versions:

- The level stepper repeats the *same* gated pass N times. It never calls a
  "build N levels" shortcut that skips per-level revalidation, because a state
  can stop being buildable partway through a batch.
- Nothing in this mod ever touches the treasury, construction points, or
  build time — not to charge, and not to discount. Whatever the **+** costs is
  what our button costs.

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

### The panel is a 33-line type, not a 5,212-line file

The window is `build_building_map_list_panel`
(`gui/map_list_panel.gui:1091-1123`), a derived type of `map_list_panel` with
just two blockoverrides, `headers` and `item`. The filters the player sees
(Location All/Domestic/Abroad, List item, Workforce) are `construction_filters`
(`:2433`).

So the surface we touch is small even in the worst case. **Open question:** can
a mod redefine a single `type` from its own `.gui` file and have the engine take
the later definition, or must we override all 5,212 lines of
`gui/map_list_panel.gui`? Test this first — it is the difference between a
33-line patch-fragility surface and a whole-file one.

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

### A widget can fire a datafunction on creation

`state = { name = update  trigger_on_create = yes  on_finish = "[...]" }` is
vanilla, e.g. `gui/journal_entry_widgets/ep2_japan_widgets.gui:561` firing a
scripted GUI's `Execute` that way.

Combined with the point above: a container with
`datamodel = "[MapListPanel.AccessValidOptions]"` whose items call
`[MapListOption.OnClick]` on creation is a **loop over every valid state that
executes the game's own build action** — no script, no per-building-type
generation, no duplicated rules.

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

## 4. Acceptance criteria — written before the code

1. With a building selected and M states listed as valid, clicking bulk build
   queues **exactly N levels in each of those M states** and nothing anywhere
   else; the construction queue grows by exactly N×M entries.
2. Clicking it a second time queues another N×M (the semantics are "add", not
   "top up") — and **not** 2×N×M or an unbounded amount. One click, one batch.
3. Leaving the panel open after a click queues nothing further: the queue count
   is identical one second later, ten seconds later, and after a day tick.
   *(This is the runaway check — it is the criterion that matters.)*
4. The button label's M matches the number of rows visible in the list, and
   changes when the player changes the Location filter.
5. With the Abroad filter selected, the states built in are the foreign ones
   the panel lists, and construction is funded the way a single **+** click on
   that same row would fund it.
6. States under the "Failed" and "Invalid" headings are never built in, and
   neither is any state whose **+** button is greyed out (§1a).
7. Zero new `error.log` lines; zero new `.gui` errors on load.
8. **No-cheat audit:** the mod contains no `create_building`, no
   `add_building_level`, no `add_treasury` and no `add_modifier`. If the
   GUI-native route holds, the mod's only verbs are `OnClick` and
   `debug_log`. Enforced by `check_no_cheat_verbs` in
   `tools/check_references.py` on every validation run, not remembered at
   release time — and verified to fail on a planted cheat, not merely to pass.
   `start_building_construction` is deliberately **not** on that list: it
   starts a normal paid construction rather than conjuring a building, so it
   stays available if we fall back to the script route (§2).

**Automated as far as it goes, per CLAUDE.md §5:**

- (7) and the load-time GUI errors: `python tools/scan_logs.py`, no game
  interaction needed beyond a launch to the main menu.
- (1), (2), (3): a `debug_log` line per queued state is *not* available — the
  GUI-native route runs no script. Substitute: the construction queue's own
  count, read from a `tools/shot.py --region panel` screenshot before and
  after, which is a yes/no comparison rather than a judgement call.
- (4), (6): static — the label binds to `GetDataModelSize` of the same
  datamodel the list binds to, checkable by reading the file. Add a
  `check_references.py` rule asserting the two datamodel expressions match.

## 5. Explicitly out of the first build

- Any new filter of our own (the "Incorporated only" toggle, a nice-to-have) —
  the panel's existing Location filter comes for free, ours would not.
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

- **`tools/package_release.py` is hardcoded to `REPO_ROOT`** and will stage
  Smart Notifications no matter which mod it is asked for. It has to take a
  mod root before this mod can ship. Not urgent, but it is a release blocker,
  not a nice-to-have.
- No `(SN) ` prefix — that convention belongs to Smart Notifications
  (CLAUDE.md §3). This mod adds labels to a vanilla panel and needs its own
  answer before the first public build; decide at release, not now.
- Release via `package_release.py`, never the dev junction.
