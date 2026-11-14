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

Move X (old position x) to final position k. Send to the back, in queue
order:

- up (x > k): every tech at position >= k except X
- down (x < k): X, then every tech at position > k
- after the last shown tech (run 2): X only

Every overflow tech is always re-queued too, so it stays behind. Built by
`tools/gen_research_queue_probe.py` into `research_queue/` (dev only).

## Acceptance criteria (written before the run)

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

## Recipe for run 2

(Run 1's recipe is in git history, commit e10d71f.) Use a throwaway save;
the probe really moves your queue. The game must be relaunched to pick up
the new build.

1. Load the save, pause, open the Technology panel.
2. For R6, first: click a tech to research it, unpause for a few weeks so it
   gains progress, then click a different tech (A stops). Do this before
   building the queue, since a plain click empties it.
3. Shift-click techs until the "..." overflow button appears (7 or more).
   Include one tech whose prerequisite you have not researched, so the game
   queues the prerequisite right before it. Shift-click the tech from step 2
   back in too.
4. Drag, one at a time:
   a. a tech leftwards, released in the gap just left of an earlier tech;
   b. a tech rightwards, released just right of a later tech;
   c. a tech into the empty space right of the last shown tech;
   d. the dependent from step 3 ahead of its prerequisite (should refuse,
      with "X needs Y first" in red right of the row);
   e. the prerequisite behind its dependent (should refuse);
   f. the tech from step 2, anywhere.
5. F12 while the red message shows, and once at the end.
6. Tell me before relaunching the game: a relaunch replaces debug.log.

Then I run `python tools/rq_probe_report.py` and `python tools/scan_logs.py`.

## Results

### Run 1 (2026-11-13, 1861 Spain save)

Read from `rq_probe_report.py` before the game was restarted (a restart
replaces debug.log, so the raw lines are gone; read the report before
relaunching next time). Only 3 techs were queued, so nothing sat in the
overflow pop-up.

| # | Verdict | Evidence |
|---|---|---|
| H1 | PASS | 15 `drop|x|k` lines, none `noop` |
| H2 | partly | queued techs dump as positions 1..3; the current research never appeared in a dump. Vanilla shows the badge only for position > 0 (tech_tree.gui:1165), so unqueued and current techs are <= 0. Whether the 5 shown slots include the current research is still open (needs 6+ queued) |
| H3 | PASS for shown techs | every drop's `fire_top` lines were exactly the member set, in queue order. Overflow re-queue (`fire_tail`) not exercised |
| H4 | PASS 14 of 14 | the 15th drop's lines were cut off mid-write (game still running when read), not a wrong order |
| H5 | not tested | every queued tech had 0 progress |
| H6 | PASS | B (remove then re-add in one click) moved the tech to the back |
| H7 | recorded | N (ResearchWithUnlocks on a queued tech) emptied the queue: after-dump empty, and the user saw the techs disappear. Research cannot be used for "drop on first" |
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
