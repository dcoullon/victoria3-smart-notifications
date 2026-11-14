"""Simulate the Research Queue move rule against the engine behaviour the
probe observed, over random valid queues built from the game's real tech
data (docs/research-queue-investigation.md, run 3 design).

Engine model (run 2): RemoveFromQueue also removes every queued dependent;
AddToQueueWithUnlocks appends the tech after any unqueued, unresearched
prerequisites. The rule under test, identical to tools/rq_probe_report.py:

    up to f   : the dragged tech X and its prerequisites stay; every other
                tech at position >= f is sent to the back, in queue order
    down to f : X, every tech at position > f, and every dependent of X are
                sent to the back, in queue order

Checks per drop: the result equals the expected order, stays valid (every
tech after its queued prerequisites), loses no tech, and puts X at slot f
or right beside the techs travelling with it.

Usage: python tools/rq_simulate.py [--trials N]
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_research_queue_probe import ancestor_pairs, prereq_edges, shown_count  # noqa: E402


def main() -> int:
    trials = int(sys.argv[sys.argv.index("--trials") + 1]) if "--trials" in sys.argv else 4000
    anc: dict[str, set[str]] = {}
    for p, t in ancestor_pairs():
        anc.setdefault(t, set()).add(p)
    direct: dict[str, list[str]] = {}
    for p, t in prereq_edges():
        direct.setdefault(t, []).append(p)
    techs = sorted({k for pair in ancestor_pairs() for k in pair})
    n = shown_count()
    rng = random.Random(1)
    runs = fails = 0

    for _ in range(trials):
        researched = set(rng.sample(techs, rng.randint(0, 60)))
        researched |= {a for t in list(researched) for a in anc.get(t, ())}

        def add(t: str, q: list[str]) -> None:  # AddToQueueWithUnlocks
            if t in q or t in researched:
                return
            for p in sorted(direct.get(t, [])):
                add(p, q)
            q.append(t)

        def valid(q: list[str]) -> bool:
            return all(a in q[:j] or a in researched for j, t in enumerate(q) for a in anc.get(t, ()))

        queue: list[str] = []
        for t in rng.sample([t for t in techs if t not in researched], rng.randint(2, 6)):
            add(t, queue)
        shown = min(n, len(queue))
        for x in range(1, len(queue) + 1):
            for d, f in [("up", f) for f in range(1, min(x, shown + 1))] + \
                        [("down", f) for f in range(x + 1, shown + 1)]:
                runs += 1
                X = queue[x - 1]
                if d == "up":
                    members = [t for p, t in enumerate(queue, 1)
                               if p >= f and t != X and t not in anc.get(X, set())]
                    travel = sum(1 for t in queue[f - 1:x - 1] if t in anc.get(X, set()))
                    slot = f - 1 + travel
                else:
                    members = [t for p, t in enumerate(queue, 1)
                               if t == X or p > f or X in anc.get(t, set())]
                    slot = f - 1 - sum(1 for t in queue[x:f] if X in anc.get(t, set()))
                expected = [t for t in queue if t not in members] + members
                q = list(queue)
                for m in members:
                    if m in q:
                        gone = {m} | {t for t in q if m in anc.get(t, set())}
                        q = [t for t in q if t not in gone]
                    add(m, q)
                if not (q == expected and valid(q) and sorted(q) == sorted(queue) and q.index(X) == slot):
                    fails += 1
                    if fails <= 3:
                        print(f"FAIL {queue} x={x} {d} {f}\n  got      {q}\n  expected {expected}")
    print(f"{runs} simulated drops, {fails} fail")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
