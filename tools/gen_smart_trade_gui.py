"""Build Smart Trade's GUI and treasury-line loc from readable templates.

The GUI has no variables, so every number is one nested expression, often
300+ characters (a first-week price after the transfer is ~10 levels deep).
Writing those by hand is how typos survive. Each formula is defined once by
name (@@NAME@@ tokens) and expanded into the templates.

Writes:  smart_trade/gui/00_smart_trade.gui
         smart_trade/localization/replace/english/smart_trade_treasury_l_english.yml

Usage:  python tools/gen_smart_trade_gui.py           (writes both)
        python tools/gen_smart_trade_gui.py --check   (exit 1 if stale)
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_GUI = REPO / "smart_trade" / "gui" / "00_smart_trade.gui"
OUT_LOC = REPO / "smart_trade" / "localization" / "replace" / "english" / "smart_trade_treasury_l_english.yml"


def mul(a, b): return f"Multiply_CFixedPoint({a}, {b})"
def div(a, b): return f"Divide_CFixedPoint({a}, {b})"
def sub(a, b): return f"Subtract_CFixedPoint({a}, {b})"
def add(a, b): return f"Add_CFixedPoint({a}, {b})"
def neg(a): return f"Negate_CFixedPoint({a})"
def fx(v): return f"'(CFixedPoint){v}'"
def gt0(a): return f"GreaterThan_CFixedPoint({a}, {fx(0)})"
def nz(a): return f"GreaterThan_CFixedPoint(Abs_CFixedPoint({a}), {fx(0)})"
def clamp1(a): return f"Max_CFixedPoint(Min_CFixedPoint({a}, {fx(1)}), {fx(-1)})"


MMP = "GetGoods('merchant_marine').WithMarketContext(GetPlayer.GetMarket.Self).GetMarketPrice"

# --- Signed treaty, per article (context: Article) -------------------------
A_Q = "Article.GetQuantity"
A_PH = "Article.GetGoods.WithMarketContext(Article.GetSourceCountry.GetMarket.Self).GetMarketPrice"
A_PP = "Article.GetGoods.WithMarketContext(Article.GetTargetCountry.GetMarket.Self).GetMarketPrice"
A_SALE = mul(A_Q, A_PP)
A_BUY = mul(A_Q, A_PH)
A_MARGIN = mul(A_Q, sub(A_PP, A_PH))
A_LANE_MM = "Article.GetShippingLane.GetMerchantMarineDemandRaw"
A_UNITS = "Article.MakeScope.ScriptValue('st_article_lane_units')"
T_UNITS_A = "Article.GetTreaty.MakeScope.ScriptValue('st_treaty_lane_units')"
A_SHIP = mul(div(A_UNITS, T_UNITS_A), mul(A_LANE_MM, MMP))
A_NET_LANE = sub(A_MARGIN, A_SHIP)
A_NET_LAND = A_MARGIN
A_HAS_LANE = gt0("Article.MakeScope.ScriptValue('st_article_has_lane')")
A_DIST = div(A_LANE_MM, T_UNITS_A)
A_MINE = "Article.GetSourceCountry.IsLocalPlayer"

# --- Signed treaty, totals (context: Treaty) -------------------------------
T_MARGIN = "Treaty.MakeScope.ScriptValue('st_treaty_margin')"
T_MONEY = "Treaty.MakeScope.ScriptValue('st_treaty_money')"
T_SHIP = mul("Treaty.GetShippingLaneOf(GetPlayer.Self).GetMerchantMarineDemandRaw", MMP)
T_HAS_LANE = gt0("Treaty.MakeScope.ScriptValue('st_treaty_has_lane')")
T_GOODS_LANE = sub(T_MARGIN, T_SHIP)
T_NET_LANE = add(T_GOODS_LANE, T_MONEY)
T_NET_LAND = add(T_MARGIN, T_MONEY)
T_ANY = f"Or({nz(T_MARGIN)}, {nz(T_MONEY)})"
T_SHOW_LANE = f"And({T_ANY}, {T_HAS_LANE})"
T_SHOW_LAND = f"And({T_ANY}, Not({T_HAS_LANE}))"
T_DAYS = "NotZero(Treaty.GetBindingDaysLeft)"

# --- Player totals (treasury line; context: any, uses GetPlayer) -----------
P_DIFF = sub("GetPlayer.PredictTreatyIncome", "GetPlayer.PredictTreatyExpenses")
P_MONEY = "GetPlayer.MakeScope.ScriptValue('st_player_treaty_money')"
P_TRADE = sub(P_DIFF, P_MONEY)
P_SHIP = mul("GetPlayer.MakeScope.ScriptValue('st_player_lane_units')", MMP)
P_NET = sub(P_DIFF, P_SHIP)

# --- Draft maths, shared by the article and every goods card ---------------
# Context: ArticleDraft (+ TreatyDraft). `g` is the goods expression without a
# market context: "ArticleDraft.GetGoods" for the article, "Goods" for a card.

def sel(c, a, b): return f"Select_CFixedPoint({c}, {a}, {b})"
def lt(a, b): return f"LessThan_CFixedPoint({a}, {b})"
def gt(a, b): return f"GreaterThan_CFixedPoint({a}, {b})"
def mn(a, b): return f"Min_CFixedPoint({a}, {b})"
def mx(a, b): return f"Max_CFixedPoint({a}, {b})"
def safe(a): return mx(a, fx(0.01))


def ratio(b, s):
    return div(sub(b, s), safe(mn(b, s)))


def f_imb(b, s):
    """Vanilla price rule, confirmed in game 2026-10-03 to reproduce today's
    price from buy and sell orders exactly: base x (1 + 0.75 x clamp((buy -
    sell) / min(buy, sell))). PRICE_RANGE 0.75, BUY_SELL_DIFF_AT_MAX_FACTOR 2."""
    return mul(fx(0.75), clamp1(ratio(b, s)))


# Route multiplier assumed for drafts that go by sea (Damien, 2026-10-05):
# the middle of x1.00 (under 1000 travel distance) and x1.50 (long routes),
# on the view that most partners whose markets do not touch ours are far.
ROUTE_EST = 1.25

# Best-quantity search shapes (see Market.chain / Market.register).
CHAIN_DECADES = 5          # 10 to 1,000,000 units
CHAIN_POINTS = 10          # points per decade: 10 -> worst 1.31% low, 8 -> 2.04%
# Acceptance search (Market.accept_search): one walk per acceptance value
# 1..KMAX. The quantity score tops out near 10 x 1.375 (pricier) x 1.25
# (AI strategy) = 17.2, so 18 covers it; above that the button keeps
# vanilla's top of range. 17 power-of-two steps reach down from 131,071.
ACCEPT_KMAX = 18
ACCEPT_STEPS = 17
REGISTER_FACTORS = [2 ** e for e in (12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0.5, 0.25, 0.125, 0.0625, 0.03125)]

D_ADJ = ("GetScriptedGui('st_markets_adjacent_sgui').IsValid(GuiScope.SetRoot("
         "ArticleDraft.GetFirstOrSource.MakeScope).AddScope('st_other', "
         "ArticleDraft.GetSecondOrTarget.MakeScope).End)")


class Market:
    """Every per-good draft formula, for one goods expression."""

    def __init__(self, g, home="ArticleDraft.GetFirstOrSource.GetMarket.Self",
                 partner="ArticleDraft.GetSecondOrTarget.GetMarket.Self"):
        gh = f"{g}.WithMarketContext({home})"
        gp = f"{g}.WithMarketContext({partner})"
        self.bh, self.sh = f"{gh}.GetMarketBuyOrders", f"{gh}.GetMarketSellOrders"
        self.bp, self.sp = f"{gp}.GetMarketBuyOrders", f"{gp}.GetMarketSellOrders"
        self.ph, self.pp = f"{gh}.GetMarketPrice", f"{gp}.GetMarketPrice"
        self.base, self.tq = f"{g}.GetBasePrice", f"{g}.GetTradedQuantity"
        # Shipping per unit on a short route (x1.00); zero overland.
        self.ship_unit = sel(D_ADJ, fx(0), mul(div(MMP, self.tq), fx(ROUTE_EST)))
        # First-unit margin after shipping: the deal pays only if this is > 0.
        self.edge = sub(sub(self.pp, self.ph), self.ship_unit)
        # "h" is always the SENDER's market, "p" the receiver's (the article's
        # source and target), whichever side the player is on.
        #
        # What the AI accepts (common/treaty_articles/13_goods_transfer.txt,
        # inherent_accept_score): an AI RECEIVING goods scores quantity up to
        # its shortage + 10 and loses 0.3 per unit beyond; an AI SENDING goods
        # scores quantity up to 30% of its surplus + 10 and loses 0.25 per unit
        # beyond (x6 for grain, x3 for fish, meat, fruit, groceries).
        # "Accept" = the top of that range: the most quantity the AI still
        # fully values. "Max" = Accept, capped by what the player's own market
        # can spare (sending) or use (receiving): Damien's min(their need, our
        # side), 2026-10-05. Both floored at vanilla's minimum of 10.
        self.q_accept_send = mx(fx(10), add(sub(self.bp, self.sp), fx(10)))
        self.q_max_send = mx(fx(10), mn(self.q_accept_send, sub(self.sh, self.bh)))
        self.q_accept_recv = mx(fx(10), add(mul(fx(0.3), sub(self.sh, self.bh)), fx(10)))
        self.q_max_recv = mx(fx(10), mn(self.q_accept_recv, add(sub(self.bp, self.sp), fx(10))))
        self.q_ai = self.q_accept_send
        self.cap = self.q_accept_send
        self.k = mul(self.base, fx(0.75))
        # Where the marginal gain JUMPS down: the partner's price leaves its
        # ceiling (supply passes half its demand) or ours leaves its floor
        # (demand passes half our supply). The best quantity often sits
        # exactly there, so these are always tried as candidates.
        self.kinks = [sub(div(self.bp, fx(2)), self.sp), sub(div(self.sh, fx(2)), self.bh)]
        # Profitable at its own best quantity <=> profitable at 10 units: the
        # margin per unit only falls as quantity grows, so if 10 units lose,
        # so does every larger quantity (and 10 is vanilla's minimum).
        self.pays10 = gt(self.gain(fx(10)), fx(0))

    # Best quantity, GUI only (run 10 proved the GUI cannot hand values to a
    # script value: docs/engine-notes.md). Two methods, both checked in
    # Python against brute force on 5,000 random market shapes (2026-10-05):
    #   chain()     the best GAIN, for display: find the decade the optimum is
    #               in from the sign of the marginal gain, then the max over 11
    #               points in it plus the kinks and the cap. Worst 1.31% low.
    #   register()  the best QUANTITY, for buttons: the draft's own quantity
    #               is the only variable the GUI has, so a click climbs it in
    #               ratio steps (x4096 down to x1.02) while the marginal gain
    #               stays positive, then tries the cap and the kinks. 0.76% of
    #               shapes more than 2% short, all at kinks below 20 units
    #               where whole units cost a few pounds. Relies on GetQuantity
    #               reading back a SetQuantity from the same click (run 11).
    def rh(self, q):
        return ratio(add(self.bh, q), self.sh)

    def rp(self, q):
        return ratio(self.bp, add(self.sp, q))

    def spread(self, q):
        """Partner price minus home price after q units move (price rule)."""
        return mul(self.k, sub(clamp1(self.rp(q)), clamp1(self.rh(q))))

    def gain(self, q):
        return mul(q, sub(self.spread(q), self.ship_unit))

    def marginal(self, q):
        """d gain / d q: spread - shipping - q x (price slopes). A slope is
        zero while that price sits at its cap. k first, then divide, so
        small slopes keep their precision."""
        b, s = add(self.bh, q), add(self.sp, q)
        free = lambda r: lt(f"Abs_CFixedPoint({r})", fx(1))
        slope_h = sel(free(self.rh(q)), mx(div(self.k, safe(self.sh)),
                                          div(div(mul(self.k, self.sh), safe(b)), safe(b))), fx(0))
        slope_p = sel(free(self.rp(q)), mx(div(div(mul(self.k, self.bp), safe(s)), safe(s)),
                                          div(self.k, safe(self.bp))), fx(0))
        return sub(sub(self.spread(q), self.ship_unit), mul(q, add(slope_h, slope_p)))

    def best_gain_leaf(self, lo, hi):
        """Max gain over one decade [lo, hi]: 11 points, the kinks and the
        cap clamped into it. Points past the cap do not count."""
        cands = []
        for i in range(CHAIN_POINTS + 1):
            p = fx(round(lo * 10 ** (i / CHAIN_POINTS), 3))
            g = self.gain(p)
            cands.append(g if i == 0 else sel(gt(p, self.cap), fx(-10000000), g))
        # The kinks and the cap are tried wherever they fall: any quantity
        # from 10 to the cap is a real option, inside this decade or not.
        for x in self.kinks:
            cands.append(sel(gt(x, self.cap), fx(-10000000), self.gain(mx(x, fx(10)))))
        cands.append(self.gain(self.cap))
        best = cands[0]
        for c in cands[1:]:
            best = mx(best, c)
        return best

    def chain(self):
        """Nested containers, one per decade: decade d is entered only when
        the marginal gain is still positive at its start (and the cap allows
        it); the deepest one entered shows its leaf."""
        def enter(lo):
            return f"And({lt(fx(lo), self.cap)}, {gt(self.marginal(fx(lo)), fx(0))})"
        out = ""
        for d in reversed(range(CHAIN_DECADES)):
            lo, hi = 10 * 10 ** d, 10 * 10 ** (d + 1)
            leaf_vis = "" if d == CHAIN_DECADES - 1 else f'\n\tvisible = "[Not({enter(hi)})]"'
            leaf = ("textbox = {" + leaf_vis + "\n\tautoresize = yes\n\talign = nobaseline\n"
                    "\tusing = fontsize_small\n\talwaystransparent = yes\n"
                    f'\traw_text = "@money![{self.best_gain_leaf(lo, hi)}|D+=]"\n}}')
            body = leaf + ("\n" + out if out else "")
            vis = "" if d == 0 else f'\tvisible = "[{enter(lo)}]"\n'
            out = "container = {\n" + vis + "\t" + body.replace("\n", "\n\t") + "\n}"
        return out

    def register(self, guard=None, reset=True):
        """onclick statements that leave the draft at the best quantity.
        reset=False climbs from wherever the quantity already is (the
        acceptance button: from the smallest fully-accepted quantity)."""
        q = "ArticleDraft.GetQuantity"
        g = (lambda c: f"And({guard}, {c})") if guard else (lambda c: c)
        out = []
        if reset:
            out.append(f"ArticleDraft.SetQuantity({sel(guard, fx(10), q) if guard else fx(10)})")
        for f in REGISTER_FACTORS:
            t = mx(add(q, fx(1)), mul(q, fx(round(f, 5))))
            ok = f"And(Not({gt(t, self.cap)}), {gt(self.marginal(t), fx(0))})"
            out.append(f"ArticleDraft.SetQuantity({sel(g(ok), t, q)})")
        out.append(f"ArticleDraft.SetQuantity({sel(g(gt(self.marginal(self.cap), fx(0))), self.cap, q)})")
        for kk in self.kinks:
            near = f"And({gt(kk, q)}, Not({gt(kk, mn(self.cap, add(mul(q, fx(1.2)), fx(2))))}))"
            ok = f"And({near}, {gt(self.gain(kk), self.gain(q))})"
            out.append(f"ArticleDraft.SetQuantity({sel(g(ok), kk, q)})")
        # One more unit if it pays: whole-unit rounding left tobacco at 19
        # where 20 earned a little more (run 11).
        up = add(q, fx(1))
        ok = f"And(Not({gt(up, self.cap)}), {gt(self.gain(up), self.gain(q))})"
        out.append(f"ArticleDraft.SetQuantity({sel(g(ok), up, q)})")
        return out

    def past_cap(self, guard=None):
        """Best may go past shortage + 10 while the partner's net acceptance
        of this good stays positive (Damien, run 12: tea at 104 is +9 from
        quantity, -3 "too high", still +5). Runs after register(): if the
        profit was still rising at the cap, climb on in powers of two, and
        step back from any quantity the game's own acceptance figure puts at
        0 or below. A step back is allowed only above the cap, so a good the
        AI never wanted (acceptance <= 0 at the cap) stays where it was."""
        q = "ArticleDraft.GetQuantity"
        acc = "ArticleDraft.GetAcceptance(TreatyDraft.GetRightCountry.Self)"
        g = (lambda c: f"And({guard}, {c})") if guard else (lambda c: c)
        above = gt(q, add(self.cap, fx(0.5)))
        out = []
        for e in range(ACCEPT_STEPS - 1, -1, -1):
            d = fx(2 ** e)
            up = add(q, d)
            out.append(f"ArticleDraft.SetQuantity({sel(g(gt(self.marginal(up), fx(0))), up, q)})")
            out.append(f"ArticleDraft.SetQuantity({sel(g(f'And(Not(GreaterThan_int32({acc}, {chr(39)}(int32)0{chr(39)})), {above})'), sub(q, d), q)})")
        return out

    def accept_search(self):
        """onclick statements for the thumbs-up when the PLAYER sends: the
        smallest quantity that still gets the AI's full acceptance, then the
        profit climb from there (so a profitable good ends at the larger of
        that and Best).

        Why a search: the AI's quantity score (13_goods_transfer.txt,
        receiver block) is min(q, shortage + 10) x import value / 2 /
        consumption, capped at min(import value / 2, 10), so it stops rising
        well before the shortage + 10 that vanilla's range ends at (run 11:
        tools gave +12 at 300 and at 2,330, for -2.45K vs -37K a week). The
        import value is engine-only, so the cap point cannot be computed;
        the game's own acceptance figure is read instead.

        How, without variables: start at shortage + 10 (full acceptance A),
        then walk down in powers of two, keeping a step while acceptance
        stays at A. A is not stored anywhere, so there is one copy of the
        walk per possible A (1..ACCEPT_KMAX), each moving only while the
        acceptance equals its own A. A copy for a higher A, run before any
        step, must not undo a step that never happened: its "step back" is
        allowed only once the quantity has left shortage + 10."""
        q = "ArticleDraft.GetQuantity"
        acc = "ArticleDraft.GetAcceptance(TreatyDraft.GetRightCountry.Self)"
        # The button carries datacontext = the partner's market, so these
        # 612 statements can use the short names (the file is ~40% smaller).
        g = "ArticleDraft.GetGoods.WithMarketContext(Market.Self)"
        shortage = sub(f"{g}.GetMarketBuyOrders", f"{g}.GetMarketSellOrders")
        # "Has left shortage + 10": q < cap - 0.999, written without the
        # cap's Max(10, ...) (when the cap is 10 no step can move anyway).
        # 0.999, not less: if the game keeps whole units, the start is
        # floor(cap), up to 0.999 below cap, and must still read as "not
        # moved" (simulated: 0.9 sent 14 of 150 cases to 65,000+ units).
        moved = lt(add(q, fx(-9.001)), shortage)
        out = [f"ArticleDraft.SetQuantity({self.cap})"]
        for k in range(ACCEPT_KMAX, 0, -1):
            for e in range(ACCEPT_STEPS - 1, -1, -1):
                d = fx(2 ** e)
                down = sub(q, d)
                out.append(f"ArticleDraft.SetQuantity({sel(f'And(EqualTo_int32({acc}, {chr(39)}(int32){k}{chr(39)}), {gt(down, fx(9.9))})', down, q)})")
                out.append(f"ArticleDraft.SetQuantity({sel(f'And(LessThan_int32({acc}, {chr(39)}(int32){k}{chr(39)}), {moved})', add(q, d), q)})")
        return out + self.register(reset=False)

    def ph1(self, q):
        return add(self.ph, mul(self.base, sub(f_imb(add(self.bh, q), self.sh), f_imb(self.bh, self.sh))))

    def pp1(self, q):
        return add(self.pp, mul(self.base, sub(f_imb(self.bp, add(self.sp, q)), f_imb(self.bp, self.sp))))

    def margin(self, q):
        return mul(q, sub(self.pp1(q), self.ph1(q)))

    def gain_short(self, q):
        """First-week gain on a short route (exact price rule)."""
        return sub(self.margin(q), mul(q, self.ship_unit))



D = Market("ArticleDraft.GetGoods")
C = Market("Goods")
D_Q = "ArticleDraft.GetQuantity"
D_PH1, D_PP1 = D.ph1(D_Q), D.pp1(D_Q)
D_MARGIN = D.margin(D_Q)
D_TQ = D.tq
D_SHIP_LO = mul(div(D_Q, D_TQ), MMP)
D_SHIP_HI = mul(D_SHIP_LO, fx(1.5))
D_SHIP_MID = mul(D_SHIP_LO, fx(ROUTE_EST))
D_NET_LO = sub(D_MARGIN, D_SHIP_HI)
D_NET_HI = sub(D_MARGIN, D_SHIP_LO)
D_NET_MID = sub(D_MARGIN, D_SHIP_MID)
D_QAI = D.q_ai
D_QMAX_SEND, D_QACC_SEND = D.q_max_send, D.q_accept_send
D_QMAX_RECV, D_QACC_RECV = D.q_max_recv, D.q_accept_recv
# Profitable at its own best quantity, not merely on the first unit (the
# floor of 10 units can turn a positive first-unit margin into a loss).
D_PAYS = D.pays10
D_SHOW = "And(ArticleDraft.HasType('goods_transfer'), Country.IsLocalPlayer)"
# Same tests without relying on the widget's Country context (the goods
# popup), and only once a good is picked (run 11: the row showed "Net -80.1"
# and the buttons beside "Select a Good").
D_MINE_SRC = ("And(And(ArticleDraft.HasType('goods_transfer'), ArticleDraft.HasInputValue('goods')), "
              "ArticleDraft.GetFirstOrSource.IsLocalPlayer)")
D_MINE_TGT = ("And(And(ArticleDraft.HasType('goods_transfer'), ArticleDraft.HasInputValue('goods')), "
              "ArticleDraft.GetSecondOrTarget.IsLocalPlayer)")

C_MINE = "And(ArticleDraft.HasType('goods_transfer'), ArticleDraft.GetFirstOrSource.IsLocalPlayer)"
# Only goods that gain at their own best quantity (run 7: dye showed -0.76,
# because the first unit paid but the floor of 10 units did not).
C_SHOW = f"And({C_MINE}, {C.pays10})"
# The chain is only ever shown for a good the PLAYER sends, inside a type
# whose datacontext is the partner's market: shorter names, ~12% smaller.
C_CHAIN = Market("Goods", home="GetPlayer.GetMarket.Self", partner="Market.Self").chain()
# Picking a good lands where Best would (Damien: the default IS Best),
# including past the cap while acceptance stays positive.
C_PICK_ONCLICKS = "\n".join(f'onclick = "[{s}]"' for s in C.register(C_MINE) + C.past_cap(C_MINE))
# Best and thumbs-up only show when the player sends, and both buttons carry
# datacontext = the partner's market: short names again.
DB = Market("ArticleDraft.GetGoods", home="GetPlayer.GetMarket.Self", partner="Market.Self")
D_BEST_ONCLICKS = "\n".join(f'onclick = "[{s}]"' for s in DB.register() + DB.past_cap())
D_ACCEPT_ONCLICKS = "\n".join(f'onclick = "[{s}]"' for s in DB.accept_search())

# Draft header: does the partner's market border ours? (Context: Country is
# one side of the header, TreatyDraft present.)
H_ADJ = ("GetScriptedGui('st_markets_adjacent_sgui').IsValid(GuiScope.SetRoot("
         "Country.MakeScope).AddScope('st_other', "
         "TreatyDraft.GetOtherCountry(Country.Self).MakeScope).End)")
H_SHOW = f"And(And(PdxGuiWidget.HasContext('TreatyDraft'), Not(Country.IsLocalPlayer)), {H_ADJ})"

MM_NOTE = ("Shipping costs 1 merchant marine per [{tq}|0] units, at @money![" + MMP +
           "|2] each in your market. More ports at home lower that price.")
A_MM_NOTE = MM_NOTE.format(tq="Article.GetGoods.GetTradedQuantity")
D_MM_NOTE = MM_NOTE.format(tq=D_TQ)

TOKENS = {k: v for k, v in globals().items() if k.isupper() and isinstance(v, str)
          and k not in ("REPO",)}

GUI = r'''# GENERATED by tools/gen_smart_trade_gui.py. Edit the generator, not this file.
#
# Smart Treaties (id smart_trade). Any line tagged raw_text = "dev..." is an
# exploration probe; tools/package_release.py refuses to ship a file with one.
#
# Redefines five vanilla types from our own file. THE FILENAME IS
# LOAD-BEARING: `00_` sorts before the vanilla files below, and the engine
# keeps the first definition it reads (docs/engine-notes.md, "A partial .gui
# override works"; check_type_overrides_sort_first enforces it).
#   goods_transfer_article        vanilla gui/treaty_panel.gui:1213
#   total_influence_cost          vanilla gui/treaty_panel.gui:756
#   article_draft_influence_cost  vanilla gui/treaty_draft_panel.gui:884
#   outliner_compact_treaty_item  vanilla gui/outliner_pinnable_types.gui:366
#   article_input_goods_list      vanilla gui/right_click_menu.gui:10047,
#       copied verbatim from the installed game at generation time with one
#       insertion (the gain figure on each goods card), so a patch that
#       changes it makes the generator's --check fail until regenerated.
#
# Read-only: no effect is called anywhere. Numbers: the SENDING treasury buys
# at its own market price, sells at the partner's, and pays the lane's
# merchant marine at its own market price (docs/smart-trade-investigation.md).

# @constants are file-scoped: ours must equal vanilla's @entry_width
# (gui/outliner_pinnable_types.gui:1); check_st_entry_width_matches_vanilla.
@st_entry_width = 350

types smart_trade_types {
	type smart_trade_article_tooltip = RegularTooltip {
		blockoverride "tooltip_content" {
			flowcontainer = {
				direction = vertical
				minimumsize = { 380 -1 }

				custom_tooltip_textbox = { raw_text = "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] a week to [Article.GetTargetCountry.GetNameNoFormatting]#!" }
				custom_tooltip_textbox = {
					visible = "[Not(@@A_MINE@@)]"
					raw_text = "Paid for by [Article.GetSourceCountry.GetNameNoFormatting]. No cost to you."
				}
				flowcontainer = {
					direction = vertical
					visible = "[@@A_MINE@@]"
					custom_tooltip_textbox = { raw_text = "Sale: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])" }
					custom_tooltip_textbox = { raw_text = "Purchase: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])" }
					custom_tooltip_textbox = {
						visible = "[@@A_HAS_LANE@@]"
						raw_text = "Shipping: @money![@@NEG_A_SHIP@@|D+=] ([Article.GetShippingLane.GetBeginState.GetName] to [Article.GetShippingLane.GetEndState.GetName])"
					}
					custom_tooltip_textbox = {
						visible = "[Not(@@A_HAS_LANE@@)]"
						raw_text = "Shipping: none, the markets touch"
					}
					custom_tooltip_textbox = {
						visible = "[@@A_HAS_LANE@@]"
						raw_text = "#bold Net: @money![@@A_NET_LANE@@|D+=] a week#! (@money![@@PU_LANE@@|2+=] a unit)"
					}
					custom_tooltip_textbox = {
						visible = "[Not(@@A_HAS_LANE@@)]"
						raw_text = "#bold Net: @money![@@A_NET_LAND@@|D+=] a week#! (@money![@@PU_LAND@@|2+=] a unit)"
					}
					custom_tooltip_textbox = {
						visible = "[@@A_HAS_LANE@@]"
						raw_text = "@@A_MM_NOTE@@"
					}
				}
			}
		}
	}

	type smart_trade_treaty_tooltip = RegularTooltip {
		blockoverride "tooltip_content" {
			flowcontainer = {
				direction = vertical
				minimumsize = { 300 -1 }

				custom_tooltip_textbox = { raw_text = "#header Net to your treasury, per week#!" }
				custom_tooltip_textbox = {
					visible = "[@@T_HAS_LANE@@]"
					raw_text = "Goods you send: @money![@@T_GOODS_LANE@@|D+=] (after shipping)"
				}
				custom_tooltip_textbox = {
					visible = "[Not(@@T_HAS_LANE@@)]"
					raw_text = "Goods you send: @money![@@T_MARGIN@@|D+=]"
				}
				custom_tooltip_textbox = { raw_text = "Money transfers: @money![@@T_MONEY@@|D+=]" }
			}
		}
	}

	type smart_trade_draft_tooltip = RegularTooltip {
		blockoverride "tooltip_content" {
			flowcontainer = {
				direction = vertical
				minimumsize = { 380 -1 }

				custom_tooltip_textbox = { raw_text = "#header [ArticleDraft.GetGoods.GetName], [ArticleDraft.GetQuantity|0] a week to [ArticleDraft.GetSecondOrTarget.GetNameNoFormatting]#!" }
				custom_tooltip_textbox = { raw_text = "Sale minus purchase: @money![@@D_MARGIN@@|D+=] (@money![@@D_PP1@@|2] vs @money![@@D_PH1@@|2] a unit, first-week prices)" }
				custom_tooltip_textbox = {
					visible = "[@@D_ADJ@@]"
					raw_text = "Shipping: none, the markets touch"
				}
				custom_tooltip_textbox = {
					visible = "[Not(@@D_ADJ@@)]"
					raw_text = "Shipping: ~@money![@@NEG_D_SHIP_MID@@|D+=] (@money![@@NEG_D_SHIP_LO@@|D+=] to @money![@@NEG_D_SHIP_HI@@|D+=] by route length, known once signed)"
				}
				custom_tooltip_textbox = {
					visible = "[@@D_ADJ@@]"
					raw_text = "#bold Net: @money![@@D_MARGIN@@|D+=] a week#!"
				}
				custom_tooltip_textbox = {
					visible = "[Not(@@D_ADJ@@)]"
					raw_text = "#bold Net: ~@money![@@D_NET_MID@@|D+=] a week#!"
				}
				flowcontainer = {
					visible = "[@@D_PAYS@@]"
					spacing = 4
					custom_tooltip_textbox = { raw_text = "Best: about" }
					smart_trade_best_gain = { datacontext = "[ArticleDraft.GetGoods]" }
					custom_tooltip_textbox = { raw_text = "a week (Best button). [ArticleDraft.GetSecondOrTarget.GetNameNoFormatting] accepts up to [@@D_QAI@@|0]." }
				}
				custom_tooltip_textbox = {
					visible = "[Not(@@D_PAYS@@)]"
					raw_text = "No quantity makes a profit."
				}
				custom_tooltip_textbox = {
					visible = "[Not(@@D_ADJ@@)]"
					raw_text = "@@D_MM_NOTE@@"
				}
			}
		}
	}

	type smart_trade_card_tooltip = RegularTooltip {
		blockoverride "tooltip_content" {
			flowcontainer = {
				direction = vertical
				minimumsize = { 300 -1 }
				custom_tooltip_textbox = { raw_text = "The most you can earn a week sending [Goods.GetName] to [ArticleDraft.GetSecondOrTarget.GetNameNoFormatting], at the most profitable quantity they accept (estimate). Picking it starts at that quantity." }
			}
		}
	}

	# Best weekly gain for the good in the Goods context (see
	# Market.chain in the generator). Used on the goods cards, and with
	# datacontext = "[ArticleDraft.GetGoods]" for the good being drafted.
	# The Market context sits on an inner container so that an instance's
	# own datacontext (the Goods) adds to it instead of replacing it.
	type smart_trade_best_gain = container {
		container = {
			datacontext = "[ArticleDraft.GetSecondOrTarget.GetMarket]"
			@@C_CHAIN@@
		}
	}

	type smart_trade_best_tip = RegularTooltip {
		blockoverride "tooltip_content" {
			flowcontainer = {
				spacing = 4
				custom_tooltip_textbox = { raw_text = "Set the quantity to the most profitable volume, about" }
				smart_trade_best_gain = { datacontext = "[ArticleDraft.GetGoods]" }
				custom_tooltip_textbox = { raw_text = "a week." }
			}
		}
	}

	type smart_trade_best_button = button {
		using = default_button
		size = { 46 22 }
		enabled = "[ArticleDraft.CanBeModified]"
		block "action" {
			@@D_BEST_ONCLICKS@@
		}
		block "tip" {
			tooltipwidget = { smart_trade_best_tip = {} }
		}

		flowcontainer = {
			parentanchor = center
			spacing = 2

			# The "acceptance" buttons show vanilla's own thumbs-up (the icon
			# the goods cards use for "AI likes this") instead of a word.
			icon = {
				block "thumb" {
					visible = no
				}
				parentanchor = vcenter
				size = { 16 16 }
				texture = "gfx/interface/icons/generic_icons/approval_icon.dds"
			}

			textbox = {
				parentanchor = vcenter
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				block "label" {
					raw_text = "Best"
				}
			}
		}
	}
}

types treaty_panel_types {
	# Vanilla body (gui/treaty_panel.gui:1213-1241) with the amount moved into
	# a vertical flow so the net can sit on its own line under it.
	type goods_transfer_article = widget {
		visible = "[Article.HasType('goods_transfer')]"
		size = { 145 40 }
		using = tooltip_ne

		tooltipwidget = {
			smart_trade_article_tooltip = {}
		}

		flowcontainer = {
			datacontext = "[Article.GetGoods]"
			parentanchor = vcenter
			spacing = 2

			icon = {
				parentanchor = vcenter
				size = { 30 30 }
				texture = "[Goods.GetTexture]"
			}

			flowcontainer = {
				direction = vertical
				parentanchor = vcenter

				textbox = {
					autoresize = yes
					align = nobaseline
					max_width = 110
					using = elide_fontsize_min
					text = "TREATY_SELECTED_ARTICLE_AMOUNT"

					block "text_format" {
						default_format = "#black"
					}
				}

				textbox = {
					visible = "[And(@@A_MINE@@, @@A_HAS_LANE@@)]"
					autoresize = yes
					align = nobaseline
					using = fontsize_small
					margin_top = 1
					raw_text = "Net @money![@@A_NET_LANE@@|D+=]"
				}
				textbox = {
					visible = "[And(@@A_MINE@@, Not(@@A_HAS_LANE@@))]"
					autoresize = yes
					align = nobaseline
					using = fontsize_small
					margin_top = 1
					raw_text = "Net @money![@@A_NET_LAND@@|D+=]"
				}
			}
		}
	}

	# Vanilla body (gui/treaty_panel.gui:756-807) with the influence chip put
	# in a vertical flow so the treaty's net sits under it on the signed-treaty
	# panel (Treaty context) instead of pushing into the header's middle box.
	type total_influence_cost = hbox {
		minimumsize = { 64 -1 }
		using = tooltip_ne
		tooltip = "TREATY_TOTAL_INFLUENCE_COST"

		block "expand_before" {}

		vbox = {
			hbox = {
				margin = { 0 2 }
				spacing = 2

				block "horizontal_margins" {
					margin_left = 2
					margin_right = 5
				}

				background = {
					using = entry_bg_simple_solid

					block "background_alpha" {
						alpha = 0.4
					}

					block "background_margin" {
						margin_left = 10
					}
				}

				### INFLUENCE ICON
				icon = {
					size = { 25 25 }
					texture = "gfx/interface/icons/topbar/influence_icon.dds"
				}

				### INFLUENCE COST
				textbox = {
					autoresize = yes
					align = nobaseline
					using = elide_fontsize_min
					max_width = 35

					block "text_minimumsize" {}

					block "influence_number" {
						raw_text = "#v [Treaty.GetCost(Country.Self)|0]#!"
					}
				}
			}

			### SMART TRADE: the treaty's net to the player
			textbox = {
				visible = "[And(And(PdxGuiWidget.HasContext('Treaty'), Country.IsLocalPlayer), @@T_SHOW_LANE@@)]"
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				margin_top = 3
				raw_text = "Net @money![@@T_NET_LANE@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}
			textbox = {
				visible = "[And(And(PdxGuiWidget.HasContext('Treaty'), Country.IsLocalPlayer), @@T_SHOW_LAND@@)]"
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				margin_top = 3
				raw_text = "Net @money![@@T_NET_LAND@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}

			### SMART TRADE, draft only: the partner's market borders ours
			textbox = {
				visible = "[@@H_SHOW@@]"
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				margin_top = 3
				raw_text = "No shipping"
				tooltip = "SMART_TRADE_OVERLAND_TT"
			}
		}

		block "expand_after" {
			expand = {}
		}
	}
}

types treaty_draft_panel_types {
	# Vanilla's cell (gui/treaty_draft_panel.gui:884-892) wrapped in a vbox so
	# the predicted net can sit under it. The cell's Country is the article's
	# maintenance payer, which for a goods transfer is the sender.
	type article_draft_influence_cost = vbox {
		layoutpolicy_horizontal = expanding

		article_influence_cost = {
			blockoverride "influence_cost_alpha" {
				alpha = "[TransparentIfZero(ArticleDraft.GetCostFor(Country.Self))]"
			}

			blockoverride "influence_cost_text" {
				raw_text = "#v [ArticleDraft.GetCostFor(Country.Self)|0]#!"
			}
		}

		textbox = {
			visible = "[And(@@D_SHOW@@, @@D_ADJ@@)]"
			autoresize = yes
			align = right|nobaseline
			using = fontsize_small
			margin_bottom = 4
			raw_text = "Net @money![@@D_MARGIN@@|D+=]"
			tooltipwidget = { smart_trade_draft_tooltip = {} }
		}
		textbox = {
			visible = "[And(@@D_SHOW@@, Not(@@D_ADJ@@))]"
			autoresize = yes
			align = right|nobaseline
			using = fontsize_small
			margin_bottom = 4
			raw_text = "Net ~@money![@@D_NET_MID@@|D+=]"
			tooltipwidget = { smart_trade_draft_tooltip = {} }
		}
	}
}

types pinnable_outliner_items {
	# Vanilla body (gui/outliner_pinnable_types.gui:1660-1671); added: the
	# estimated net of all treaties after the group's title, the same figure
	# as the treasury tooltip's (ST) line.
	type outliner_treaties = pinnable_outliner_group {
		datacontext = "[Outliner.AccessCategory('treaties')]"

		blockoverride "title_text" {
			raw_text = "[OutlinerEntry.GetTitle]  ~@money![@@P_NET@@|D+=]"
		}

		blockoverride "fixedgridbox_cell_size" {
			addcolumn = @st_entry_width
			addrow = 30
		}

		blockoverride "item" {
			treaty_outliner_item = {}
		}
	}

	# Vanilla body (gui/outliner_pinnable_types.gui:366-439); added: the
	# treaty's net to the player at the right, left of the time remaining.
	# Names get a narrower max width only on rows that show a net.
	type outliner_compact_treaty_item = flowcontainer {
		direction = vertical

		tooltipwidget = {
			FancyTooltip_Treaty = {}
		}

		# TREATY NAME & DURATION
		widget = {
			block "size" {
				size = { @st_entry_width 30 }
			}

			background = {
				using = fade_center_colored_black
			}

			### NAME
			flowcontainer = {
				position = { 5 0 }
				parentanchor = vcenter
				spacing = 5

				### LEFT COUNTRY FLAG
				tiny_flag_no_interact = {
					parentanchor = vcenter
					datacontext = "[Treaty.GetLeftCountry]"

					blockoverride "tooltip" {}
				}

				### RIGHT COUNTRY FLAG
				tiny_flag_no_interact = {
					parentanchor = vcenter
					datacontext = "[Treaty.GetRightCountry]"

					blockoverride "tooltip" {}
				}

				textbox = {
					visible = "[And(@@T_DAYS@@, Not(@@T_ANY@@))]"
					parentanchor = vcenter
					autoresize = yes
					align = nobaseline
					using = elide_fontsize_min
					max_width = 230
					margin_left = 2
					text = "[Treaty.GetNameNoFormatting]"
				}
				textbox = {
					visible = "[And(@@T_DAYS@@, @@T_ANY@@)]"
					parentanchor = vcenter
					autoresize = yes
					align = nobaseline
					using = elide_fontsize_min
					max_width = 165
					margin_left = 2
					text = "[Treaty.GetNameNoFormatting]"
				}
				textbox = {
					visible = "[And(Not(@@T_DAYS@@), Not(@@T_ANY@@))]"
					parentanchor = vcenter
					autoresize = yes
					align = nobaseline
					using = elide_fontsize_min
					max_width = 260
					margin_left = 2
					text = "[Treaty.GetNameNoFormatting]"
				}
				textbox = {
					visible = "[And(Not(@@T_DAYS@@), @@T_ANY@@)]"
					parentanchor = vcenter
					autoresize = yes
					align = nobaseline
					using = elide_fontsize_min
					max_width = 195
					margin_left = 2
					text = "[Treaty.GetNameNoFormatting]"
				}
			}

			### SMART TRADE: net to the player, one column for every row, left of
			### the time remaining. Never further right: the pin star appears
			### there on hover (run 4, Damien's screenshot).
			textbox = {
				visible = "[And(@@T_DAYS@@, @@T_SHOW_LANE@@)]"
				position = { -52 0 }
				parentanchor = right|vcenter
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				raw_text = "@money![@@T_NET_LANE@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}
			textbox = {
				visible = "[And(@@T_DAYS@@, @@T_SHOW_LAND@@)]"
				position = { -52 0 }
				parentanchor = right|vcenter
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				raw_text = "@money![@@T_NET_LAND@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}
			textbox = {
				visible = "[And(Not(@@T_DAYS@@), @@T_SHOW_LANE@@)]"
				position = { -52 0 }
				parentanchor = right|vcenter
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				raw_text = "@money![@@T_NET_LANE@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}
			textbox = {
				visible = "[And(Not(@@T_DAYS@@), @@T_SHOW_LAND@@)]"
				position = { -52 0 }
				parentanchor = right|vcenter
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				raw_text = "@money![@@T_NET_LAND@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}

			textbox = {
				visible = "[@@T_DAYS@@]"
				position = { -20 0 }
				align = nobaseline
				parentanchor = right|vcenter
				autoresize = yes
				using = elide_fontsize_min
				max_width = 25
				text = "[LabelingHelper.GetRemainingDuration(Treaty.GetBindingPeriodEndGameDate.Self, '_SHORT')]"
			}
		}
	}
}
'''

LOC = r'''l_english:
 # GENERATED by tools/gen_smart_trade_gui.py. Edit the generator, not this file.
 # Smart Trade: "Net treaty income" in the top-bar treasury tooltip. That
 # tooltip is assembled by engine code from loc entries. Damien wants the line
 # at the end of the revenue lines (2026-10-05), so it is PREPENDED to the
 # expenses header: "Fixed National Expenses" when the tooltip splits fixed
 # and temporary, "National Expenses" otherwise (presumably never both; run 5
 # checks). Appending to a section header instead puts the line between the
 # header and its own sub-lines (run 3). Vanilla's text follows, verbatim;
 # REPLACED_LOC_BASELINE in tools/check_references.py catches a patch changing it.
 FIXED_EXPENSES_BREAKDOWN:0 "#bold (ST) Net treaty income:#! #tooltippable #tooltip:[GetPlayer.GetTooltipTag],SMART_TRADE_TREATIES_TT ~@money![@@P_NET@@|D+=]#!#!\n\n#bold Fixed National Expenses:#! #tooltippable #tooltip:[GetPlayer.GetTooltipTag],TOTAL_EXPENSES_BREAKDOWN,TotalExpensesTooltip #bold #N @money!-[GetPlayer.GetWeeklyFixedExpenses|D-]#!#!#!#!"
 EXPENSES_BREAKDOWN:0 "#bold (ST) Net treaty income:#! #tooltippable #tooltip:[GetPlayer.GetTooltipTag],SMART_TRADE_TREATIES_TT ~@money![@@P_NET@@|D+=]#!#!\n\n#bold National Expenses:#! #tooltippable #tooltip:[GetPlayer.GetTooltipTag],TOTAL_EXPENSES_BREAKDOWN,TotalExpensesTooltip #bold #N @money!-[GetPlayer.GetWeeklyExpenses|D-]#!#!#!#!"
 SMART_TRADE_TREATIES_TT:0 "#header Net treaty income#!\nGoods you send: @money![@@P_TRADE@@|D+=]\nShipping lane costs: @money![@@NEG_P_SHIP@@|D+=] (estimate)\nMoney transfers: @money![@@P_MONEY@@|D+=]\nShipping is paid in merchant marine at your market price; more ports lower it.\nSee the outliner's treaty list for details."
 SMART_TRADE_MAX_SEND_TT:0 "Set the quantity to [@@D_QMAX_SEND@@|0], filling [ArticleDraft.GetSecondOrTarget.GetNameNoFormatting]'s shortage without going over your surplus."
 SMART_TRADE_ACCEPT_SEND_TT:0 "Set the quantity for the highest acceptance, at the best profit or the smallest loss."
 SMART_TRADE_MAX_RECV_TT:0 "Set the quantity to [@@D_QMAX_RECV@@|0], filling your shortage without going over what [ArticleDraft.GetFirstOrSource.GetNameNoFormatting] spares."
 SMART_TRADE_ACCEPT_RECV_TT:0 "Set the quantity to [@@D_QACC_RECV@@|0] for the highest acceptance."
 SMART_TRADE_OVERLAND_TT:0 "Your markets border each other: goods transfers go overland and pay no shipping."
'''

# --- Goods picker: vanilla types copied from the installed game ------------
# Each is copied verbatim at generation time with named insertions, so a game
# patch that changes them makes --check fail (the output would differ) and an
# insertion point that disappears makes generation fail outright.
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")
PICKER_SRC = GAME / "gui" / "right_click_menu.gui"

# 1. Each goods card: the estimated best weekly gain, top-left.
#    The goods icon is shrunk 45 -> 38px and lowered 5 -> 14px so the figure
#    in the top-left corner no longer overlaps it (run 7 screenshot). This
#    is grid_button's own "entire_icon_button" block with only those numbers
#    changed (vanilla gui/right_click_menu.gui, type grid_button); the card's
#    "texture" override still lands in the inner block "texture".
CARD_ANCHOR = 'blockoverride "additional_widgets" {'
CARD_CHIP = '''blockoverride "entire_icon_button" {
						button = {
							name = "interaction_icon"
							size = { 60 60 }
							position = { 0 13 }
							gfxtype = buttongfx
							parentanchor = hcenter
							alwaystransparent = yes

							block "highlight_glow" {}

							button = {
								size = { 40 40 }
								parentanchor = hcenter
								alwaystransparent = yes

								block "texture" {
									texture = "gfx/interface/icons/generic_icons/generic_concept_icon.dds"
								}
							}
						}
					}

					''' + CARD_ANCHOR + '''
						### SMART TRADE: best weekly gain for this good (estimate).
						### The figures inside are hover-transparent, so this
						### fixed-size widget carries the tooltip.
						widget = {
							visible = "[@@C_SHOW@@]"
							parentanchor = top|left
							position = { 5 2 }
							size = { 60 16 }
							tooltipwidget = { smart_trade_card_tooltip = {} }
							smart_trade_best_gain = {}
						}'''

# 2. The card's own click: vanilla picks the good; we then climb the
#    quantity to the best one (Market.register), so the default IS the best
#    quantity (Damien's option 1), for every good the player sends. For goods
#    the partner sends every step re-sets the quantity it already has.
PICK_ANCHOR = 'onclick = "[ArticleDraft.SetGood(Goods.Self)]"'
PICK_BEST = PICK_ANCHOR + '''
						### SMART TRADE: start from the best quantity
						@@C_PICK_ONCLICKS@@'''

# 3. The quantity row under the goods: a Best button next to "/ week", for
#    after the player has moved the slider (Damien's option 3).
ROW_ANCHOR = 'text = "SLASH_PER_WEEK"\n\t\t\t\t}\n\t\t\t}'
ROW_BEST = ROW_ANCHOR + '''

			### SMART TRADE: its own row under the quantity
			flowcontainer = {
				parentanchor = hcenter
				spacing = 4
				margin_top = -2

				### SMART TRADE: live net at the current quantity, then the
				### Best and Max buttons. Shown for every good the player sends,
				### profitable or not (Damien: consistent UX; the player may
				### take a loss on purpose).
				textbox = {
					visible = "[And(@@D_MINE_SRC@@, @@D_ADJ@@)]"
					parentanchor = vcenter
					autoresize = yes
					align = nobaseline
					using = fontsize_small
					raw_text = "Net @money![@@D_MARGIN@@|D+=]"
					tooltipwidget = { smart_trade_draft_tooltip = {} }
				}
				textbox = {
					visible = "[And(@@D_MINE_SRC@@, Not(@@D_ADJ@@))]"
					parentanchor = vcenter
					autoresize = yes
					align = nobaseline
					using = fontsize_small
					raw_text = "Net ~@money![@@D_NET_MID@@|D+=]"
					tooltipwidget = { smart_trade_draft_tooltip = {} }
				}
				### Goods the player sends: Best, Max, Accept
				smart_trade_best_button = {
					visible = "[@@D_MINE_SRC@@]"
					parentanchor = vcenter
					datacontext = "[ArticleDraft.GetSecondOrTarget.GetMarket]"
				}
				smart_trade_best_button = {
					visible = "[@@D_MINE_SRC@@]"
					parentanchor = vcenter
					blockoverride "action" { onclick = "[ArticleDraft.SetQuantity(@@D_QMAX_SEND@@)]" }
					blockoverride "label" { raw_text = "Max" }
					blockoverride "tip" { tooltip = "SMART_TRADE_MAX_SEND_TT" }
				}
				smart_trade_best_button = {
					visible = "[@@D_MINE_SRC@@]"
					parentanchor = vcenter
					datacontext = "[ArticleDraft.GetSecondOrTarget.GetMarket]"
					blockoverride "action" {
						@@D_ACCEPT_ONCLICKS@@
					}
					blockoverride "label" { raw_text = "" }
					blockoverride "thumb" { visible = yes }
					blockoverride "tip" { tooltip = "SMART_TRADE_ACCEPT_SEND_TT" }
				}
				### Goods the partner sends: Max, Accept (no treasury effect)
				smart_trade_best_button = {
					visible = "[@@D_MINE_TGT@@]"
					parentanchor = vcenter
					blockoverride "action" { onclick = "[ArticleDraft.SetQuantity(@@D_QMAX_RECV@@)]" }
					blockoverride "label" { raw_text = "Max" }
					blockoverride "tip" { tooltip = "SMART_TRADE_MAX_RECV_TT" }
				}
				smart_trade_best_button = {
					visible = "[@@D_MINE_TGT@@]"
					parentanchor = vcenter
					blockoverride "action" { onclick = "[ArticleDraft.SetQuantity(@@D_QACC_RECV@@)]" }
					blockoverride "label" { raw_text = "" }
					blockoverride "thumb" { visible = yes }
					blockoverride "tip" { tooltip = "SMART_TRADE_ACCEPT_RECV_TT" }
				}
			}'''

# 4. The row's own height: vanilla's 70 holds the goods and the quantity;
#    our button row needs 22 more, or it runs into the divider below (run 10
#    screenshot). The popup is a vertical flowcontainer, so the rest moves down.
ROW_SIZE_ANCHOR = 'size = { 400 70 }'
ROW_SIZE = 'size = { 400 92 }  # SMART TRADE: was 70, +22 for the button row'

PICKER_TYPES = [
    ("article_input_goods_list", [(CARD_ANCHOR, CARD_CHIP), (PICK_ANCHOR, PICK_BEST)]),
    ("selected_goods_and_amount", [(ROW_SIZE_ANCHOR, ROW_SIZE), (ROW_ANCHOR, ROW_BEST)]),
]


def copy_vanilla_type(lines, name, inserts):
    import re
    start = next(i for i, l in enumerate(lines) if l.strip().startswith(f"type {name} "))
    depth = 0
    for i in range(start, len(lines)):
        stripped = re.sub(r"#.*", "", lines[i])
        depth += stripped.count("{") - stripped.count("}")
        if depth == 0:
            end = i
            break
    body = "\n".join(lines[start:end + 1])
    for anchor, replacement in inserts:
        assert body.count(anchor) == 1, f"vanilla {name} changed shape near {anchor!r}; review the insertion"
        body = body.replace(anchor, replacement, 1)
    return (f"\t# Vanilla {name}, copied verbatim at generation time from\n"
            f"\t# gui/right_click_menu.gui:{start + 1}-{end + 1}, with Smart Trade insertions.\n"
            f"{body}\n")


def picker_block() -> str:
    lines = PICKER_SRC.read_text(encoding="utf-8-sig").split("\n")
    return ("\ntypes article_input_types {\n"
            + "\n".join(copy_vanilla_type(lines, n, ins) for n, ins in PICKER_TYPES)
            + "}\n")

# Derived tokens used by the templates.
TOKENS.update({
    "NEG_A_BUY": neg(A_BUY), "NEG_A_SHIP": neg(A_SHIP),
    "PU_LANE": div(A_NET_LANE, A_Q), "PU_LAND": div(A_NET_LAND, A_Q),
    "NEG_D_SHIP_LO": neg(D_SHIP_LO), "NEG_D_SHIP_HI": neg(D_SHIP_HI),
    "NEG_D_SHIP_MID": neg(D_SHIP_MID),
    "NEG_P_SHIP": neg(P_SHIP),
})


def expand(text: str) -> str:
    # Longest names first so @@A_NET_LANE@@ is never clobbered by a shorter token.
    for name in sorted(TOKENS, key=len, reverse=True):
        text = text.replace(f"@@{name}@@", TOKENS[name])
    assert "@@" not in text, [l for l in text.splitlines() if "@@" in l][:3]
    return "﻿" + text


# The script-value best quantity (smart_trade_best_quantity.txt, runs 9-10)
# is gone: the GUI cannot pass values into a script value. Without .End the
# inputs arrive as 'none'; with .End the expression fails to parse ("Could
# not find promote for 'End'"). check_no_gui_value_passing blocks a return.

OUTPUTS = {OUT_GUI: GUI + picker_block(), OUT_LOC: LOC}

if __name__ == "__main__":
    stale = []
    for path, template in OUTPUTS.items():
        want = expand(template)
        if "--check" in sys.argv:
            have = path.read_text(encoding="utf-8") if path.is_file() else ""
            if have != want:
                stale.append(path.relative_to(REPO).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(want, encoding="utf-8")
            print(f"wrote {path.relative_to(REPO)} ({len(want.splitlines())} lines)")
    if "--check" in sys.argv:
        if stale:
            print(f"STALE vs generator: {', '.join(stale)}; rerun tools/gen_smart_trade_gui.py.")
            sys.exit(1)
        print("OK: Smart Trade GUI and treasury loc match the generator.")
