"""Simulate the Research Queue move rule against the engine behaviour the
probe observed, over random valid queues built from the game's real tech
data plus synthetic techs from "another mod" that the mod's prerequisite
table does not know (docs/research-queue-investigation.md).

Engine model (run 2): RemoveFromQueue also removes every queued dependent;
AddToQueueWithUnlocks appends the tech after any unqueued, unresearched
prerequisites. The rule under test, identical to the generated GUI and to
tools/rq_probe_report.py, with X the dragged tech moved to slot f:

    up to f   : refused if X is not in the table. Otherwise X and its known
                prerequisites stay; every other tech at position >= f is sent
                to the back, in queue order
    down to f : X, every tech at position > f, and every tech after X that
                depends on it (known) or is not in the table are sent to the
                back, in queue order

Synthetic techs follow the common mod pattern: each requires one or two of
the game's techs, sometimes another synthetic one. Mods that change the
game's own techs' prerequisites are out of scope (the table would be wrong).

Checks per drop: the result equals the expected order, stays valid (every
tech after its queued prerequisites), loses no tech, and, when every tech
involved is known, puts X at slot f or right beside the techs travelling
with it.

Usage: python tools/rq_simulate.py [--trials N] [--modded N]
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_research_queue_probe import ancestor_pairs, known_techs, prereq_edges, shown_count  # noqa: E402


def arg(name: str, default: int) -> int:
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main() -> int:
    trials, n_mod = arg("--trials", 4000), arg("--modded", 40)
    known = known_techs()
    gui_anc: dict[str, set[str]] = {}
    for p, t in ancestor_pairs():
        gui_anc.setdefault(t, set()).add(p)
    direct: dict[str, list[str]] = {}
    for p, t in prereq_edges():
        direct.setdefault(t, []).append(p)
    rng = random.Random(7)
    modded: list[str] = []
    for i in range(n_mod):
        reqs = rng.sample(known, rng.randint(1, 2))
        if modded and rng.random() < 0.3:
            reqs.append(rng.choice(modded))
        direct[f"mod_{i}"] = reqs
        modded.append(f"mod_{i}")
    memo: dict[str, set[str]] = {}

    def true_anc(t: str) -> set[str]:
        if t not in memo:
            memo[t] = set()
            for p in direct.get(t, ()):
                memo[t] |= {p} | true_anc(p)
        return memo[t]

    known_set = set(known)
    n = shown_count()
    rng = random.Random(1)
    runs = fails = refused = 0

    for _ in range(trials):
        researched = set(rng.sample(known, rng.randint(0, 60)))
        researched |= {a for t in list(researched) for a in true_anc(t)}

        def add(t: str, q: list[str]) -> None:  # AddToQueueWithUnlocks
            if t in q or t in researched:
                return
            for p in sorted(direct.get(t, [])):
                add(p, q)
            q.append(t)

        def valid(q: list[str]) -> bool:
            return all(a in q[:j] or a in researched for j, t in enumerate(q) for a in true_anc(t))

        queue: list[str] = []
        for t in rng.sample([t for t in known + modded if t not in researched], rng.randint(2, 7)):
            add(t, queue)
        shown = min(n, len(queue))
        for x in range(1, len(queue) + 1):
            for d, f in [("up", f) for f in range(1, min(x, shown + 1))] + \
                        [("down", f) for f in range(x + 1, shown + 1)]:
                runs += 1
                X = queue[x - 1]
                ga = lambda t: gui_anc.get(t, set())  # noqa: E731
                if d == "up":
                    if X not in known_set:
                        refused += 1
                        continue
                    members = [t for p, t in enumerate(queue, 1) if p >= f and t != X and t not in ga(X)]
                    slot = f - 1 + sum(1 for t in queue[f - 1:x - 1] if t in ga(X))
                else:
                    members = [t for p, t in enumerate(queue, 1)
                               if t == X or p > f or (p > x and (X in ga(t) or t not in known_set))]
                    slot = f - 1 - sum(1 for t in queue[x:f] if X in ga(t) or t not in known_set)
                expected = [t for t in queue if t not in members] + members
                q = list(queue)
                for m in members:
                    if m in q:
                        gone = {m} | {t for t in q if m in true_anc(t)}
                        q = [t for t in q if t not in gone]
                    add(m, q)
                ok = q == expected and valid(q) and sorted(q) == sorted(queue)
                if all(t in known_set for t in queue):
                    ok = ok and q.index(X) == slot
                if not ok:
                    fails += 1
                    if fails <= 3:
                        print(f"FAIL {queue} x={x} {d} {f}\n  got      {q}\n  expected {expected}")
    print(f"{runs} simulated drops ({n_mod} synthetic techs from another mod in the pool), "
          f"{fails} fail, {refused} refused (an unknown tech dragged up)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
