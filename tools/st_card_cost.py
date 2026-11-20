"""Smart Treaties: what one goods card costs to create, counted without the game.

    python tools/st_card_cost.py

Each card computes its figure once, on creation, through the chain of
animation states tools/gen_smart_trade_gui.py writes (lazy_widgets). This
walks that chain as the game would, on random market shapes, and counts the
data-function steps of every on_start it runs: one per call and one per
dotted link (`Goods.WithMarketContext(X).GetMarketPrice` is 2 + X's own).
The plumbing is left out: each `FindChild(..).TriggerAnimation(Select_CString(`
wrapper (5 steps) and each `GetVariableSystem.Set(` (2 steps). That is the
count the 0.14 notes quote (3,367 to 4,690 a paying sea card).

A path depends only on the route and on the decade the best quantity falls
in, so every shape of one decade costs the same; the table shows the range
seen, per decade, for a card the player sends by sea (the dearest route), and
the cards that stop early. `IsValid` (the border tests, about 45 steps each
by the 2026-10-16 fit) is listed apart: the count gives it 2.
"""
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_price_model as C  # noqa: E402
import gen_smart_trade_gui as G  # noqa: E402
import gen_st_recommender as R  # noqa: E402

WRAP = re.compile(r"PdxGuiWidget\.FindChild\('\w+'\)\.TriggerAnimation\(Select_CString\(")


def steps(expr):
    calls = len(re.findall(r"\b[A-Z]\w*\(", expr))
    links = len(re.findall(r"\.\w+", expr))
    plumbing = 5 * len(WRAP.findall(expr)) + 2 * expr.count("GetVariableSystem.Set(")
    return calls + links - plumbing


def walk(m, route, mine=True, gui_vars=None):
    """Run one card's chain (check_price_model.card_chain) and count it:
    (steps, IsValid calls, the stored figure or None). gui_vars: shared
    between cards of one list (the stored route); None for the list's first."""
    seen = []
    fig = C.card_chain(m, route, mine, {} if gui_vars is None else gui_vars, seen.append)
    return sum(steps(x) for x in seen), sum(x.count(".IsValid(") for x in seen), fig


def decade(m):
    """The decade the card's search ends in, from the reference pick."""
    mk = C.gui_market(m)
    name = C.gui_eval(mk.lazy_pick("x"), C.gui_env(m))
    return int(name[len("st_x"):])


def big_shape(rnd, deviate):
    """Markets up to 10 million orders, so the best quantity reaches the top
    decades (random_shape stops at 10,000 and never gets past 10,000 units)."""
    m = C.shape(rnd, deviate)
    scale = 10 ** rnd.uniform(1, 3)
    for k in ("bh", "sh", "bp", "sp"):
        m[k] *= scale
    m["cap"] = max(10.0, m["bp"] - m["sp"] + 10)
    rule = lambda b, s: m["base"] * (1 + 0.75 * R.clamp1(R.imb(b, s)))
    m["ph"], m["pp"] = rule(m["bh"], m["sh"]), rule(m["bp"], m["sp"])
    return m


def main(n=1500):
    rnd = random.Random(11)
    paying = {}
    stop = {}
    for i in range(n):
        for deviate in (False, True):
            m = (big_shape if i % 3 == 2 else C.shape)(rnd, deviate)
            m["ship"] = m["ship"] or 1.0          # by sea: the dearer route
            gv = {}
            first = walk(m, "s", gui_vars=gv)            # the list's first card
            later = walk(m, "s", gui_vars=gv)            # the route already stored
            if first[2] is None:
                key = "first unit loses" if m["pp"] - m["ph"] - m["ship"] <= 0 else "10 units lose"
                stop.setdefault(key, []).append((first, later))
            else:
                paying.setdefault(decade(m), []).append((first, later))

    def rng(xs):
        return f"{min(xs):,}" if min(xs) == max(xs) else f"{min(xs):,} to {max(xs):,}"

    def line(label, runs):
        f, l = [r[0][0] for r in runs], [r[1][0] for r in runs]
        same = runs[0][0][1] == runs[0][1][1] and f == l
        tail = (f"{rng(f)} steps, {runs[0][0][1]} IsValid" if same else
                f"{rng(f)} steps and {runs[0][0][1]} IsValid as the list's first card, "
                f"{rng(l)} and {runs[0][1][1]} after")
        print(f"  {label}: {tail} ({len(runs)} shapes)")
    print("Card the player sends by sea (the dearest route): steps from creation to the stored figure")
    for d in sorted(paying):
        line(f"best quantity {10 * 10 ** d:,} to {100 * 10 ** d:,}", paying[d])
    for k in sorted(stop):
        line(f"{k}, no figure", stop[k])
    rnd = random.Random(12)
    runs = []
    for _ in range(50):
        m, gv = C.shape(rnd, False), {}
        runs.append((walk(m, "s", False, gv), walk(m, "s", False, gv)))
    line("player receives, no figure", runs)
    print(f"Creation chain text (lazy_widgets): {len(G.lazy_widgets()):,} characters")


if __name__ == "__main__":
    main()
