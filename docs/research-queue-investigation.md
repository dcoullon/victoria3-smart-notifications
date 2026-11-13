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

Drop X (old position x) on slot k. Send to the back, in queue order:

- up (x > k): every tech at position >= k except X
- down (x < k): X, then every tech at position > k

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

## Recipe for the run

Use a throwaway save; the probe really moves your queue.

1. Enable "Research Queue Reorder - Dev (probe)" in the launcher. Start or
   load any game, pause, open the Technology panel.
2. Queue about 9 techs so the pop-up has some (shift-click). Include one
   tech whose prerequisite you have not researched, so the game queues the
   prerequisite right before it, and make sure both sit in the shown row.
3. Drag the last shown tech onto the first shown one. Then drag the first
   shown one onto the last.
4. Drag the dependent tech from step 2 onto its own prerequisite.
5. Click B on any shown tech, then N on another.
6. Take one screenshot (F12) of the queue row before step 3 and one after
   step 5 (for H5's progress numbers). Close the game or not, either way.

Then I run `python tools/rq_probe_report.py` and `python tools/scan_logs.py`.

## Results

(not run yet)
