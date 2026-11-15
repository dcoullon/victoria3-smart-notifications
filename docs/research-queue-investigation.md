# Research Queue Reorder: investigation and probe

Started 2026-11-13. Goal: drag and drop to reorder the research queue,
limited to the techs shown in the tech panel (not the overflow pop-up), with
a prerequisite check (a tech's prerequisites must be researched or ahead of
it in the queue).

## What we know (sourced)

- No existing mod does this (Workshop search, 2026-11-13; Paradox Mods and
  the Paradox forum could not be searched). Vanilla 1.15.1 has: click =
  research now, shift-click or "+" = add to end, X = remove.
- Paradox listed "rearrange the order of the queue" as a goal in Dev Diary
  #70 (14 Dec 2022); the queue shipped in 1.2 without it. 1.13 added
  drag-and-drop to the construction queue only.
- The engine has no "move tech to position" command. `Technology` exposes
  `AddToQueue`, `AddToQueueWithUnlocks`, `RemoveFromQueue`, `Research`,
  `ResearchWithUnlocks` (reference/data_types). The construction queue's
  drag-and-drop works because `ConstructionQueueElement.MoveToIndex` exists.
- Script cannot touch the queue (no effect besides
  `start_research_random_technology`).
- Drag-and-drop GUI plumbing exists: `draggable_behavior`, `drop_target`,
  `GetDraggedDatacontext` (gui/construction_queue.gui:354).
- The shown list is `GetResearchQueueTop`, sized by the define
  `TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT = 5`; the rest is
  `GetResearchQueueBottom`, shown only in a pop-up.
- `GetTechnology('key')` works in vanilla GUI and loc, so a generated
  prerequisite table is possible (prerequisites are `unlocking_technologies`
  in common/technology/technologies/*.txt).

## The workaround being probed

Move X to slot k. Send to the back, in queue order (run 3 rule; runs 1
and 2 used the same rule without the travelling prerequisites/dependents):

- up: every tech at position >= k except X and its prerequisites
- down: X, every tech at position > k, and every dependent of X

Built by `tools/gen_research_queue_probe.py` into `research_queue/` (dev
only); checked offline by `tools/rq_simulate.py`.

## Acceptance criteria for run 1 (written before the run)

Verdicts come from `python tools/rq_probe_report.py` unless marked "look".

| # | Question | Pass | Fail tells us |
|---|---|---|---|
| H1 | Drag/drop plumbing works on queued techs | a `drop\|x\|k` line per drop | no line: the drag or drop never fired; `drop\|noop`: positions outside the ladder |
| H2 | Which position the current research has, and whether the shown list counts it | read from the before-dump | (informational) |
| H3 | The chain fires once per member, in queue order | `fire_top` lines = the member set, in order, then `fire_tail` for every overflow tech | wrong set or order: commands apply mid-chain, or trigger order is not widget order |
| H4 | A drop produces the right order | report says PASS for each drop | FAIL with the diff; LOST lists techs that fell out of the queue |
| H5 | Research progress survives remove and re-add | look: the number bottom-left of a moved tech is unchanged | progress reset: the whole approach is dead |
| H6 | Two commands in one click run in order (B button) | report says PASS for `back` | tech lost or unmoved |
| H7 | What "research now" (N button) does to a queued tech | recorded: where it went, where the old current research went | (informational, decides whether "drop on first slot" can use it) |
| H8 | What the engine does with a tech queued ahead of its own prerequisite | recorded from the after-dump of the dependency step in the recipe | (informational: decides how much the prerequisite check must do) |
| H9 | Tech names render in debug_log via `SCOPE.sT('t').GetName` | `pos` lines carry readable names | blank or error.log line: switch to another accessor |

## Recipe for run 3

(Earlier recipes are in git history.) Use a throwaway save; the probe really
moves your queue. Relaunch the game to load the new build.

1. Load the save, pause, open the Technology panel.
2. For S7, first: click a tech to research it, unpause a few weeks so it
   gains progress, then click a different tech. Do this before building the
   queue, since a plain click empties it.
3. Shift-click techs until the "+N" button appears (8 or more). Include two
   chains, e.g. Socialism (queues Labor Movement) and Film (queues Realism
   and Camera). Shift-click the tech from step 2 back in too.
4. Drag, one at a time:
   a. a dependent ahead of its prerequisite (its prerequisite should come
      along and land just before it);
   b. a prerequisite behind its dependent (the dependent should come along);
   c. a tech into a gap, and one into the space after the last tech;
   d. open the "+N" pop-up and drag one of its techs onto the row;
   e. the tech from step 2, anywhere.
5. F12 once at the end (S7's progress numbers).
6. Tell me when done. A relaunch is safe: the game keeps the previous five
   logs, and the report reads them.

Then I run `python tools/rq_probe_report.py` and `python tools/scan_logs.py`.

## Results

### Run 1 (2026-11-13, 1861 Spain save)

Read from `rq_probe_report.py`; the raw lines are in debug.5.log as of
2026-11-14 (the game rotates its logs, keeping five). Only 3 techs were
queued, so nothing sat in the overflow pop-up.

| # | Verdict | Evidence |
|---|---|---|
| H1 | PASS | 14 `drop|x|k` lines, none `noop` |
| H2 | partly | queued techs dump as positions 1..3; the current research never appeared in a dump. Vanilla shows the badge only for position > 0 (tech_tree.gui:1165), so unqueued and current techs are <= 0. Whether the 5 shown slots include the current research is still open (needs 6+ queued) |
| H3 | PASS for shown techs | every drop's `fire_top` lines were exactly the member set, in queue order. Overflow re-queue (`fire_tail`) not exercised |
| H4 | PASS 14 of 14 | full log re-read from debug.5.log on 2026-11-14 (a first read mid-session had caught one drop half-written) |
| H5 | not tested | every queued tech had 0 progress |
| H6 | PASS 5 of 5 | B (remove then re-add in one click) moved the tech to the back |
| H7 | recorded | N (ResearchWithUnlocks on a queued tech) emptied the queue all 3 times: after-dump empty, and the user saw the techs disappear. Research cannot be used for "drop on first" |
| H8 | not tested | no queued pair had a prerequisite link. Superseded: the next build blocks such drops instead of observing them |
| H9 | PASS with markup | `GetName` renders, wrapped in tooltip markup (`TechnologyTooltip <name>`); the report strips it |

User feedback: drops only land when released over the middle of the target
tech. Moving a tech "just a little" ahead of or behind another should be
enough.

Engine facts found while designing the fix (data_types, no run needed):
- `GuiCurrentDrag` exists only inside `drag_widget`, and its `CVector2f`
  positions expose no X accessor, so the drop slot cannot be computed from
  the cursor. Drop zones have to be widgets.
- `GetTechnology('key')` returns a Technology, `GetNameNoFormatting` a
  CString, `Concatenate3/4` and `GetVariableSystem.Set/Get/Exists/Clear`
  exist: a prerequisite table keyed by tech names can be built in the GUI.
  Vanilla English tech names are unique (178 techs, 220 prerequisite links).

### Run 2 attempt (2026-11-13, launch at 18:21)

The new build loaded cleanly (the panel override registered, nothing of ours
in error.log), but the session logged no RQ_PROBE line at all and its
screenshots show Smart Treaties, not the tech panel. Either no drag was made
in that launch, or no drop landed on any target. Not counted as a run.

### Run 2 design

- Each shown tech gets a 14px drop gap on its left meaning "insert here",
  and a zone right of the last shown tech means "after the last shown".
  A drop on a tech icon keeps run 1's meaning: moving left lands before it,
  moving right lands after it. The whole row is tiled with no dead space.
- Prerequisite check before any command runs: the GUI builds a set of
  `prerequisite>dependent` name pairs from the game's tech files, records
  the shown techs' names by position, and every tech the move would cross
  checks itself against the dragged one. Moving up, a crossed tech must not
  be a prerequisite of the dragged tech; moving down (or to the end), the
  dragged tech must not be a prerequisite of a crossed one. Crossing is
  enough: a chain Y -> A -> X with Y queued forces A to sit between them.
- A blocked drop changes nothing and shows "X needs Y first" in red next to
  the row for a few seconds.
- The N and B probe buttons are gone (answered). The progress readout stays
  for H5.

Limitation: techs added by other mods are not in the table, so the check
lets them through.

### Run 2 acceptance criteria (written before the code)

| # | When | Pass | Read from |
|---|---|---|---|
| R1 | a tech is dropped in the gap just left of an earlier shown tech | it lands right before that tech | report PASS |
| R2 | a tech is dropped in the gap just right of a later shown tech, or on its icon | it lands right after that tech | report PASS |
| R3 | a tech is dropped right of the last shown tech, with 6+ techs queued | it becomes the last shown; the overflow order is unchanged | report PASS (also covers H3's overflow part) |
| R4 | a dependent is dropped ahead of its queued prerequisite | nothing moves; a `blocked` line names the prerequisite; the red message shows | report PASS + look |
| R5 | a prerequisite is dropped behind its queued dependent | nothing moves; `blocked` line; message | report PASS |
| R6 | a queued tech with progress above 0 is moved | its progress number is unchanged | look (H5) |
| R7 | the whole run | no line naming this mod's files in error.log | scan_logs |
| H2 | 6+ techs queued | the number of `pos` lines says how many queued techs the row shows | report |

### Run 2 (2026-11-14, launch at 14:55)

19 drops: 3 pass, 15 fail, 1 cut off at the end of the log. User saw techs
dropped from the queue, the "needs" message appear only sometimes, a warning
on Socialism while it sat correctly behind Labor Movement, and the queue
moving in unexpected ways. Every one traces to two engine facts:

1. **Triggered GUI states run later, in widget-tree order, not call order.**
   `PdxGuiTriggerAllAnimations` and `TriggerAnimation` only mark a state as
   pending; its `on_start` runs when the widget is next visited, walking the
   tree. `GetVariableSystem` calls and expression evaluation run at once.
   Evidence: in `drop|3|2` the `blocked|Realism` line was logged before
   `fire_top|Realism`, yet the move ran, because the go/blocked decision had
   been evaluated before the check state ran. The names step was just as
   late, so the check compared against the previous drop's names (the
   Socialism warning). And the overflow list sits after the controller in the
   tree, so `fire_tail` ran before `fire_top` (every drop with an overflow).
2. **Removing a tech from the queue also removes its queued dependents.**
   Film (needs Camera) vanished each time Camera was re-queued; Political
   Agitation (needs Socialism, Corporatism, Anarchism) and Mass Propaganda
   (needs Political Agitation, Film) the same. So vanilla's X button already
   removes a tech's dependents with it.

H2 answered: the row shows 5 queued techs (5 `pos` lines with 6+ queued);
the current research is not one of them. Dragging works on the row; it does
not from the "+N" pop-up, which the probe never made draggable.

### Run 3 design: move together, one pass

Moving a tech takes its queued prerequisites (up) or dependents (down) with
it. Both reduce to one pass: some techs stay in place and every other tech
from the drop point onward is sent to the back, in queue order.

- up to slot f: the dragged tech X and its prerequisites (direct or
  indirect) stay; every other tech at position >= f goes to the back.
- down to slot f (the end zone is down to the last shown slot): X, every
  tech at position > f, and every dependent of X go to the back; the rest
  stays.

The queue never leaves a valid order, and a cascade never loses a tech:
every dependent of a tech sent back is itself sent back later in the pass.
Nothing is blocked any more, so the message goes.

Ordering fixes from run 2:
- No step waits on another state's result. The dragged tech's name is
  recorded when the drag starts (a `trigger_on_create` state in the drag
  widget); the drop is refused if it does not match the dropped tech, so a
  stale name can only cancel a move, never misdirect one. The pair table
  (now 1,182 direct and indirect pairs) is built when the panel is created
  and again on each drop, from a widget that sits before the row in the tree.
- The controller sits before the row and the overflow list after it, so the
  pass visits the shown techs before the overflow ones.
- Dropping a tech from the "+N" pop-up onto the row: the pop-up reuses the
  vanilla type `queued_technology`, so the drag moves into that type.

### Run 3 acceptance criteria (written before the code)

| # | When | Pass | Read from |
|---|---|---|---|
| S1 | any drop | the after-order equals the expected order computed by the report from the before-order and the game's prerequisite data; no tech is lost | report PASS per drop |
| S2 | a dependent is dropped ahead of its queued prerequisite | the prerequisite moves with it and lands right before it | report PASS + `x|` line |
| S3 | a prerequisite is dropped behind its queued dependent | the dependent moves with it and lands right after it | report PASS |
| S4 | 6+ techs queued, any drop | overflow techs keep their order behind the row (`fire_top` lines all before `fire_tail`) | report |
| S5 | a tech in the "+N" pop-up is dragged onto the row | it lands at that slot, its queued prerequisites with it | report PASS |
| S6 | every drop | a `x|<name>` line names the dragged tech; no `drop|badx`; about one `dragstart` line per drag (a burst at panel open would mean the name is recorded at the wrong time) | report |
| S7 | a queued tech with progress above 0 is moved | its progress number is unchanged | look (H5) |
| S8 | the whole run | nothing naming this mod's files in error.log | scan_logs |

The move rule was checked offline before the run: `python tools/rq_simulate.py`
simulates it against the engine behaviour above (cascade on remove, add with
prerequisites) over random valid queues from the real tech data: 215,029
drops, 0 fail. That covers the rule, not the GUI wiring, which only a launch
tests.

The recorded name is overwritten by every drag and never cleared (a first
build cleared it a second after each drop, which refused a drag started
inside that second).

### Run 3 (2026-11-14, about 15:40 to 15:56, played in French)

10 of 10 complete drops PASS (one more cut off by the log's end while the
game ran). The first drop was the dependency case: Pumpjacks dragged ahead
of Steam Donkey, its prerequisite, which correctly stayed in front of it.
The report first marked it FAIL because it only knew English names; it now
reads every game language. `dragstart`: 14 lines for 11 drops plus 3 drags
that ended nowhere, so the name is recorded at drag start (S6 PASS, no
`badx`). Nothing of ours in error.log (S8 PASS).

Not covered: S3 (a prerequisite dragged behind its dependent) and S7
(progress) never came up in game; S3 is covered by `rq_simulate.py` only.

User feedback:
- a "0" under each tech: the probe's progress readout, not vanilla. Now shown
  only when progress is above 0.
- dragging from the "+N" pop-up does nothing. Log: three `dragstart` lines
  for the pop-up tech, no drop line of any kind (not even `noop` or `badx`),
  nothing in error.log, so the release never reached a drop target. The
  pop-up's techs now get a button instead (vanilla's move-left icon,
  bottom-left, pop-up only) that moves the tech into the row's last slot
  with its queued prerequisites; the drag is back on the row only.

### Run 4 acceptance criteria

| # | When | Pass | Read from |
|---|---|---|---|
| T1 | the pop-up button is clicked on a tech | a `drop|up|5` with `x|` naming it; it lands at slot 5, or right after its prerequisites in the pop-up | report PASS |
| T2 | a prerequisite is dragged behind its queued dependent (S3) | the dependent comes along, right after it | report PASS |
| T3 | a tech with progress above 0 is moved (S7) | its number shows and is unchanged after the move | look |
| T4 | no progress anywhere | no number under any tech | look |
