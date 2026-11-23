"""Smart Treaties: one price model everywhere, checked without the game.

    python tools/check_price_model.py           all checks (about a minute)
    python tools/check_price_model.py --quick   fewer shapes (validate_syntax)

The model and its search live in tools/gen_st_recommender.py's Python mirror
(sides(), gain(), marginal(), port()). This evaluates what the generators
actually wrote and compares it with that mirror, on random market shapes with
real prices on and off vanilla's price rule:

1. GUI formulas (tools/gen_smart_trade_gui.py Market): first-week prices,
   gain and marginal at random quantities, equal to the mirror.
2. GUI searches: the Best button's onclick sequence (register) and the goods
   card's creation path (lazy_pick, then that decade's best_gain_leaf), against
   brute force over [10, min(cap, home ceiling)] plus the cap.
3. Script: the generated st_rec_values.txt and st_rec_search effect,
   interpreted, against port() (same quantity) and brute force.

Added 2026-11-19 with the price model (rollback tag st-before-price-ratio):
before it, nothing tested the GUI's searches against brute force.
"""
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_smart_trade_gui as G  # noqa: E402
import gen_st_recommender as R  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MOD = REPO / "smart_trade"


# ---------------------------------------------------------------------------
# GUI expression evaluator (the CFixedPoint data functions the generator uses)
# ---------------------------------------------------------------------------
H, P = "H", "P"
ACC = re.compile(r"G\.WithMarketContext\((H|P)\)\.(GetMarketBuyOrders|GetMarketSellOrders|GetMarketPrice)")
NAMES = {("H", "GetMarketBuyOrders"): "bh", ("H", "GetMarketSellOrders"): "sh",
         ("P", "GetMarketBuyOrders"): "bp", ("P", "GetMarketSellOrders"): "sp",
         ("H", "GetMarketPrice"): "ph", ("P", "GetMarketPrice"): "pp"}
FUNCS = {
    "Add_CFixedPoint": lambda a, b: a + b,
    "Subtract_CFixedPoint": lambda a, b: a - b,
    "Multiply_CFixedPoint": lambda a, b: a * b,
    "Divide_CFixedPoint": lambda a, b: a / b if b else 0.0,
    "Negate_CFixedPoint": lambda a: -a,
    "Abs_CFixedPoint": abs,
    "Min_CFixedPoint": min,
    "Max_CFixedPoint": max,
    "LessThan_CFixedPoint": lambda a, b: a < b,
    "GreaterThan_CFixedPoint": lambda a, b: a > b,
    "Select_CFixedPoint": lambda c, a, b: a if c else b,
    "Select_CString": lambda c, a, b: a if c else b,
    "And": lambda a, b: a and b,
    "Or": lambda a, b: a or b,
    "Not": lambda a: not a,
    "FixedPointToInt": lambda a: int(round(a)),
    "ToString_int32": str,
    "True": lambda: True,
    "False": lambda: False,
}


_STATES = {}


def chain_states():
    """Every state of the generated creation chain: name -> its on_start lines."""
    if not _STATES:
        for name, body in re.findall(r"name = (st_\w+)\n((?:\t*on_start = \"\[.*?\]\"\n)*)", G.lazy_widgets()):
            _STATES[name] = re.findall(r'on_start = "\[(.*?)\]"', body)
    return _STATES


def card_chain(m, route, mine=True, gui_vars=None, seen=None):
    """Walk the goods card's generated creation chain (lazy_widgets) state by
    state, as the game would, for a card on `route` ('l' land, 's' near sea,
    'f' far sea). Returns the stored figure (whole units) or None.
    mine=False: the player receives the good. gui_vars: the GUI variables
    other than the card's own (the stored route), shared between calls to
    play several cards of one list; None starts empty. seen(line) is called
    with every on_start line run, before it is evaluated."""
    states = chain_states()
    mk = dict(G.LAZY_MARKETS)[route]
    extra = [(G.C_MINE, "True()" if mine else "False()"), (G.ONCE_KEY, "'key'"), (G.ROUTE_KEY, "'route'")]
    env = gui_env(m)
    env["mmp"] = m["ship"] / (G.ROUTE_FAR if route == "f" else G.ROUTE_NEAR)
    gv = {} if gui_vars is None else gui_vars
    todo = [G.LAZY_STEP1]
    for _ in range(40):
        step = todo.pop(0)
        if seen:
            seen(step)
        step = step.replace(G.D_ADJ, "True()" if route == "l" else "False()")
        step = step.replace(G.D_FAR, "True()" if route == "f" else "False()")
        for a, b in extra:
            step = step.replace(a, b)
        step = re.sub(r"GetVariableSystem\.Exists\('(\w+)'\)",
                      lambda x: "True()" if x[1] in gv else "False()", step)
        step = re.sub(r"GetVariableSystem\.HasValue\('(\w+)', '(\w+)'\)",
                      lambda x: "True()" if gv.get(x[1]) == x[2] else "False()", step)
        t = re.fullmatch(r"PdxGuiWidget\.FindChild\('\w+'\)\.TriggerAnimation\((.*)\)", step)
        if t:
            name = gui_eval(t[1], env, mk)
            if name == "st_none":
                return None
            # A triggered state runs after the rest of the current one.
            todo += states[name]
            continue
        s = re.fullmatch(r"GetVariableSystem\.Set\('(\w+)', (.*)\)", step)
        assert s, step[:120]
        if s[1] == "key":
            return float(gui_eval(s[2], env, mk))
        gv[s[1]] = gui_eval(s[2], env, mk)
    raise RuntimeError("chain did not end")


def gui_eval(expr, env, market=None, extra=()):
    """Evaluate one generated expression. env: bh sh bp sp ph pp base tq mmp q.
    market: a Market built with other names than G/H/P (e.g. the cards'
    LAZY_MARKETS), whose accessor strings are substituted; extra: further
    (text, replacement) pairs, applied first."""
    s = expr
    for a, b in extra:
        s = s.replace(a, b)
    if market is not None:
        for attr in ("bh", "sh", "bp", "sp", "ph", "pp", "base", "tq"):
            s = s.replace(getattr(market, attr), "@" + attr)
    s = ACC.sub(lambda m: "@" + NAMES[(m[1], m[2])], s)
    s = s.replace(G.MMP, "@mmp").replace("G.GetBasePrice", "@base").replace("G.GetTradedQuantity", "@tq")
    s = s.replace("ArticleDraft.GetQuantity", "@q")
    pos = 0

    def parse():
        nonlocal pos
        if s[pos] == "'":
            end = s.index("'", pos + 1)
            lit = s[pos + 1:end]
            pos = end + 1
            return float(lit[len("(CFixedPoint)"):]) if lit.startswith("(CFixedPoint)") else lit
        if s[pos] == "@":
            m = re.match(r"@(\w+)", s[pos:])
            pos += m.end()
            return env[m[1]]
        m = re.match(r"(\w+)\(", s[pos:])
        if not m:
            raise ValueError(f"cannot parse at {s[pos:pos + 80]!r}")
        pos += m.end()
        args = []
        while s[pos] != ")":
            while s[pos] == " ":
                pos += 1
            args.append(parse())
            while s[pos] == " ":
                pos += 1
            if s[pos] == ",":
                pos += 1
                continue
            if s[pos] == ")":
                break
            raise ValueError(f"unexpected {s[pos:pos + 40]!r}")
        pos += 1
        if m[1] not in FUNCS:
            raise ValueError(f"unknown function {m[1]}")
        return FUNCS[m[1]](*args)

    out = parse()
    if pos != len(s):
        raise ValueError(f"trailing text {s[pos:pos + 40]!r}")
    return out


def gui_env(m, q=10.0):
    # Shipping per unit = mmp / tq x route; route 1 (same continent), tq 1.
    return dict(bh=m["bh"], sh=m["sh"], bp=m["bp"], sp=m["sp"], ph=m["ph"], pp=m["pp"],
                base=m["base"], tq=1.0, mmp=m["ship"], q=q)


def gui_market(m):
    """The GUI's Market for a shape: overland when shipping is 0, else by sea."""
    if m["ship"] == 0:
        return G.Market("G", home=H, partner=P, adj=True, far=False)
    return G.Market("G", home=H, partner=P, adj=False, far=False)


def shape(rnd, deviate):
    m = R.random_shape(rnd, deviate)
    m["cap"] = max(10.0, m["bp"] - m["sp"] + 10)   # the GUI's cap: the AI's shortage + 10
    return m


def brute(m):
    hi = max(10.0, min(m["cap"], R.home_ceiling(m)))
    xs = [10 + i * (hi - 10) / 4000 for i in range(4001)] + [m["cap"]]
    return max(R.gain(m, x) for x in xs)


def brute_top(m, unit=False):
    """The most a search may show: brute force plus the exact kinks and
    limit inside [10, limit], so a kink between two sampled points is never
    mistaken for a search promising too much. unit=True also allows one unit
    past the limit (within the cap): the Best button and the suggestions end
    with "one more unit if it pays" (run 11, tobacco 19 against 20), which
    can step just past our price ceiling at small quantities."""
    hi = max(10.0, min(m["cap"], R.home_ceiling(m)))
    exact = [x for x in (m["bp"] / 2 - m["sp"], m["sh"] / 2 - m["bh"], hi) if 10 <= x <= hi]
    if unit:
        exact.append(min(hi + 1, max(hi, m["cap"])))
    return max([brute(m)] + [R.gain(m, x) for x in exact])


# ---------------------------------------------------------------------------
# Paradox script: values and the search effect, interpreted
# ---------------------------------------------------------------------------
TOKEN = re.compile(r'"[^"]*"|[{}]|\?=|>=|<=|!=|[=<>]|[^\s{}=<>?]+')


def parse_script(text):
    text = re.sub(r"#[^\n]*", "", text)
    toks = TOKEN.findall(text)
    pos = 0

    def block():
        nonlocal pos
        items = []
        while pos < len(toks) and toks[pos] != "}":
            key = toks[pos]
            op = toks[pos + 1]
            pos += 2
            if toks[pos] == "{":
                pos += 1
                val = block()
                pos += 1
            else:
                val = toks[pos]
                pos += 1
            items.append((key, op, val))
        return items

    return block()


class Script:
    def __init__(self):
        vals = parse_script((MOD / "common/script_values/st_rec_values.txt").read_text(encoding="utf-8-sig"))
        effs = parse_script((MOD / "common/scripted_effects/st_rec_effects.txt").read_text(encoding="utf-8-sig"))
        self.values = {k: v for k, _, v in vals}
        self.effects = {k: v for k, _, v in effs}
        self.var = {}

    def num(self, x, temps):
        if isinstance(x, list):
            return self.run_value(x, {})
        if re.fullmatch(r"-?\d+(\.\d+)?", x):
            return float(x)
        if x.startswith("var:"):
            return self.var[x[4:]]
        if x.startswith("scope:"):
            return temps[x[6:]]
        return self.value(x)

    def cond(self, items, temps):
        for k, op, v in items:
            a, b = self.num(k, temps), self.num(v, temps)
            ok = {">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b, "=": a == b, "!=": a != b}[op]
            if not ok:
                return False
        return True

    def run_value(self, items, temps, acc=0.0):
        for k, op, v in items:
            if k == "value":
                acc = self.num(v, temps)
            elif k == "add":
                acc += self.num(v, temps)
            elif k == "subtract":
                acc -= self.num(v, temps)
            elif k == "multiply":
                acc *= self.num(v, temps)
            elif k == "divide":
                d = self.num(v, temps)
                acc = acc / d if d else 0.0
            elif k == "min":
                acc = max(acc, self.num(v, temps))
            elif k == "max":
                acc = min(acc, self.num(v, temps))
            elif k == "save_temporary_value_as":
                temps[v] = acc
            elif k == "if":
                limit = next(x for kk, _, x in v if kk == "limit")
                if self.cond(limit, temps):
                    acc = self.run_value([i for i in v if i[0] != "limit"], temps, acc)
            elif k.startswith("scope:") or k in ("market", "global_var:st_rec_player"):
                raise KeyError(f"input value read in a test: {k}")
            else:
                raise KeyError(f"unsupported script value op {k}")
        return acc

    def value(self, name):
        return self.run_value(self.values[name], {})

    def run_effect(self, items):
        for k, op, v in items:
            if k == "set_variable":
                d = {kk: vv for kk, _, vv in v}
                self.var[d["name"]] = self.num(d["value"], {})
            elif k == "if":
                limit = next(x for kk, _, x in v if kk == "limit")
                if self.cond(limit, {}):
                    self.run_effect([i for i in v if i[0] != "limit"])
            elif v == "yes" and k in self.effects:
                self.run_effect(self.effects[k])
            else:
                raise KeyError(f"unsupported effect {k}")

    def search(self, m):
        """st_rec_try_partner's inputs (minus the scope reads) and search."""
        self.var = dict(st_rec_bh=m["bh"], st_rec_sh=m["sh"], st_rec_bp=m["bp"], st_rec_sp=m["sp"],
                        st_rec_ph=m["ph"], st_rec_pp=m["pp"], st_rec_ship=m["ship"], st_rec_cap=m["cap"])
        for n in ("kh", "kp", "hc", "lim"):
            self.var[f"st_rec_{n}"] = self.value(f"st_rec_in_{n}")
        self.var["st_rec_t"] = 10.0
        if self.value("st_rec_gain") <= 0:
            return None
        self.run_effect(self.effects["st_rec_search"])
        return self.var["st_rec_q"]

    def gain(self, m, t):
        self.var.update(st_rec_t=t)
        return self.value("st_rec_gain")


# ---------------------------------------------------------------------------
def rel(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1.0)


def run(n):
    ok = True
    sc = Script()

    # 1. GUI formulas equal the mirror.
    worst = 0.0
    rnd = random.Random(1)
    for i in range(n):
        m = shape(rnd, i % 2 == 1)
        mk = gui_market(m)
        for _ in range(4):
            q = 10 ** rnd.uniform(1, 4)
            env = gui_env(m, q)
            ph, pp, *_ = R.sides(m, q)
            scale = max(ph, pp, 1.0)
            # Gain and marginal compared per unit, against the price level: 4/3
            # is written 1.33333, a 1e-5 relative difference that a large q
            # turns into whole pounds on a gain near zero.
            for got, want in ((gui_eval(mk.ph1("ArticleDraft.GetQuantity"), env) / scale, ph / scale),
                              (gui_eval(mk.pp1("ArticleDraft.GetQuantity"), env) / scale, pp / scale),
                              (gui_eval(mk.gain("ArticleDraft.GetQuantity"), env) / q / scale,
                               R.gain(m, q) / q / scale),
                              (gui_eval(mk.marginal("ArticleDraft.GetQuantity"), env) / scale,
                               R.marginal(m, q) / scale)):
                worst = max(worst, abs(got - want))
    good = worst < 1e-4
    ok &= good
    print(f"[{'ok' if good else 'FAIL'}] GUI prices, gain and marginal vs the mirror: worst gap {worst:.2e} of the price")

    # 1a. The goods cards' two shortcuts (2026-11-20) equal their plain form:
    # Market.rises(a, b) is gain(b) > gain(a), Market.over_lim(p) is p > lim.
    # Shapes with the home ceiling at or below 10 included (sh small).
    bad = tried = 0
    rnd = random.Random(4)
    for i in range(n):
        m = shape(rnd, i % 2 == 1)
        if i % 4 == 0:
            m["sh"] = rnd.uniform(1, 12)
        mk, env = gui_market(m), gui_env(m)
        lim = gui_eval(mk.lim, env)
        for _ in range(4):
            a = round(10 ** rnd.uniform(1, 4), 3)
            b = round(a * 10 ** (1 / G.CHAIN_POINTS), 3)
            ga, gb = R.gain(m, a), R.gain(m, b)
            if abs(gb - ga) > 1e-4 * max(abs(ga), abs(gb), 1.0):     # float noise decides ties
                tried += 1
                bad += gui_eval(mk.rises(a, b), env) != (gb > ga)
            if abs(a - lim) > 1e-3:
                tried += 1
                bad += gui_eval(mk.over_lim(a), env) != (a > lim)
    ok &= bad == 0
    print(f"[{'ok' if bad == 0 else 'FAIL'}] card shortcuts (rises, over_lim) equal gain(b) > gain(a) and p > lim: "
          f"{tried - bad} of {tried}")

    # 1b. Script formulas equal the mirror.
    worst = 0.0
    rnd = random.Random(2)
    for i in range(n):
        m = shape(rnd, i % 2 == 1)
        sc.search(m) if False else None
        sc.var = dict(st_rec_bh=m["bh"], st_rec_sh=m["sh"], st_rec_bp=m["bp"], st_rec_sp=m["sp"],
                      st_rec_ph=m["ph"], st_rec_pp=m["pp"], st_rec_ship=m["ship"], st_rec_cap=m["cap"])
        sc.var["st_rec_kh"] = sc.value("st_rec_in_kh")
        sc.var["st_rec_kp"] = sc.value("st_rec_in_kp")
        for _ in range(4):
            q = 10 ** rnd.uniform(1, 4)
            sc.var["st_rec_t"] = q
            ph, pp, *_ = R.sides(m, q)
            scale = max(ph, pp, 1.0)
            worst = max(worst, abs(sc.value("st_rec_gain") - R.gain(m, q)) / q / scale,
                        abs(sc.value("st_rec_marginal") - R.marginal(m, q)) / scale)
    good = worst < 1e-4
    ok &= good
    print(f"[{'ok' if good else 'FAIL'}] script gain and marginal vs the mirror: worst gap {worst:.2e} of the price")

    # 2 and 3. Searches against brute force, prices on and off the rule.
    for deviate in (False, True):
        label = "real prices off the rule" if deviate else "real prices on the rule"
        rnd = random.Random(3)
        stats = {k: [0, 0, 0.0, 0.0] for k in ("Best button", "card figure", "suggestion scan")}
        same_q = chain_same = chain_n = 0
        for _ in range(n):
            m = shape(rnd, deviate)
            mk = gui_market(m)
            if R.gain(m, 10) <= 0:
                continue
            b = brute(m)
            if b < 0.01:   # under a penny a week: float noise decides "profitable"
                continue
            top, top1 = brute_top(m), brute_top(m, unit=True)
            # Best button: the onclick sequence, quantity carried click to click.
            q = 10.0
            for stmt in mk.register():
                inner = stmt[len("ArticleDraft.SetQuantity("):-1]
                q = gui_eval(inner, gui_env(m, q))
            got = {"Best button": R.gain(m, q)}
            # Card: the decade lazy_pick names, the half half_up picks, then
            # that half's best figure.
            env = gui_env(m)
            name = gui_eval(mk.lazy_pick("x"), env)
            d = int(name[len("st_x"):])
            half = "b" if gui_eval(mk.half_up(10 * 10 ** d), env) else "a"
            leaf = gui_eval(mk.best_gain_leaf(10 * 10 ** d, 100 * 10 ** d, half), env)
            got["card figure"] = leaf
            # The chain the generator writes, walked state by state, must store
            # that same figure (rounded down to whole units).
            # Twice with the same GUI variables: the first card of a list
            # runs the border tests, the next reads the stored route.
            route, gv = "l" if m["ship"] == 0 else "s", {}
            fig, fig2 = card_chain(m, route, gui_vars=gv), card_chain(m, route, gui_vars=gv)
            chain_same += fig is not None and fig == fig2 and int(fig) == int(round(leaf - 0.5))
            chain_n += 1
            # Script: interpreted st_rec_search.
            qs = sc.search(m)
            got["suggestion scan"] = R.gain(m, qs) if qs is not None else 0.0
            # Same choice as port(), by gain: the script writes its step factors
            # to 5 decimals, so quantities differ in the 4th decimal.
            qp = R.port(m)
            if qs is not None and qp is not None and rel(R.gain(m, qs), R.gain(m, qp)) < 1e-5:
                same_q += 1
            for k, g in got.items():
                gap = (b - g) / b
                s = stats[k]
                s[0] += 1
                s[1] += gap > 0.02
                s[2] = max(s[2], gap)
                t = top if k == "card figure" else top1
                s[3] = max(s[3], (g - t) / t)
        # The card shows the best of 8 points per decade: historically up to
        # 2.04% low (CHAIN_POINTS), so it gets 3%. The searches get 2%.
        # None may show more than the best within the limit: the card did,
        # by up to 245 times, until 2026-11-20 (Market.kink_gains).
        for k, (tested, short, worst, over) in stats.items():
            limit = 0.03 if k == "card figure" else 0.02
            bad = worst > limit if k == "card figure" else short > 0
            ok &= not bad
            print(f"[{'FAIL' if bad else 'ok'}] {k}, {label}: {tested} shapes, {short} more than 2% "
                  f"below brute force, worst {100 * worst:.2f}%")
            bad = over > 1e-4
            ok &= not bad
            print(f"[{'FAIL' if bad else 'ok'}] {k} never above the best within the limit"
                  f"{'' if k == 'card figure' else ' (+1 unit)'}, {label}: worst {100 * max(over, 0):.3f}% above")
        good = chain_same == chain_n
        ok &= good
        print(f"[{'ok' if good else 'FAIL'}] card creation chain as generated stores that figure, {label}: "
              f"{chain_same} of {chain_n}")
        good = same_q == stats["suggestion scan"][0]
        ok &= good
        print(f"[{'ok' if good else 'FAIL'}] suggestion scan picks port()'s quantity, {label}: "
              f"{same_q} of {stats['suggestion scan'][0]}")
    return ok


if __name__ == "__main__":
    n = 300 if "--quick" in sys.argv else 2000
    sys.exit(0 if run(n) else 1)
