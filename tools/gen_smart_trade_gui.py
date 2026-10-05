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

D_ADJ = ("GetScriptedGui('st_markets_adjacent_sgui').IsValid(GuiScope.SetRoot("
         "ArticleDraft.GetFirstOrSource.MakeScope).AddScope('st_other', "
         "ArticleDraft.GetSecondOrTarget.MakeScope).End)")


class Market:
    """Every per-good draft formula, for one goods expression."""

    def __init__(self, g):
        gh = f"{g}.WithMarketContext(ArticleDraft.GetFirstOrSource.GetMarket.Self)"
        gp = f"{g}.WithMarketContext(ArticleDraft.GetSecondOrTarget.GetMarket.Self)"
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
        # Best quantity: computed in script (see "Best quantity, computed in
        # SCRIPT" below), capped at Accept so the AI never sees "too much".
        # Fallback when the script returns nothing: the run 8 linear estimate,
        # with the squares removed (S / B / B; fixed point overflows near 2e9).
        unsat = lambda b, s: f"And({lt(ratio(b, s), fx(1))}, {gt(ratio(b, s), fx(-1))})"
        k = mul(self.base, fx(0.75))
        slope_h = sel(unsat(self.bh, self.sh),
                      mul(k, mx(div(fx(1), safe(self.sh)), div(div(self.sh, safe(self.bh)), safe(self.bh)))), fx(0))
        slope_p = sel(unsat(self.bp, self.sp),
                      mul(k, mx(div(div(self.bp, safe(self.sp)), safe(self.sp)), div(fx(1), safe(self.bp)))), fx(0))
        q_lin = mx(fx(10), mn(div(self.edge, mx(mul(fx(2), add(slope_h, slope_p)), fx(0.0001))), self.q_accept_send))
        gain_lin = mul(q_lin, sub(self.edge, mul(add(slope_h, slope_p), q_lin)))
        q_script = self.script("st_q_best")
        ok = gt(q_script, fx(0))     # the script floors at 10 when it works
        self.q_best = sel(ok, q_script, q_lin)
        self.best_gain = sel(ok, self.script("st_best_gain"), gain_lin)
        self.script_ok = ok
        self.pays = gt(self.edge, fx(0))

    def script(self, name):
        inputs = [("st_bh", self.bh), ("st_sh", self.sh), ("st_bp", self.bp), ("st_sp", self.sp),
                  ("st_ph", self.ph), ("st_pp", self.pp), ("st_base", self.base),
                  ("st_ship", self.ship_unit), ("st_cap", self.q_accept_send)]
        chain = "".join(f".AddScope('{k}', MakeScopeValue({v}))" for k, v in inputs)
        return f"GuiScope.SetRoot(GetPlayer.MakeScope){chain}.End.ScriptValue('{name}')"

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
D_QBEST = D.q_best
D_BEST_GAIN = D.best_gain
D_QMAX_SEND, D_QACC_SEND = D.q_max_send, D.q_accept_send
D_QMAX_RECV, D_QACC_RECV = D.q_max_recv, D.q_accept_recv
# Profitable at its own best quantity, not merely on the first unit (the
# floor of 10 units can turn a positive first-unit margin into a loss).
D_PAYS = gt(D_BEST_GAIN, fx(0))
D_SHOW = "And(ArticleDraft.HasType('goods_transfer'), Country.IsLocalPlayer)"
# Same tests without relying on the widget's Country context (the goods popup).
D_MINE_SRC = "And(ArticleDraft.HasType('goods_transfer'), ArticleDraft.GetFirstOrSource.IsLocalPlayer)"
D_MINE_TGT = "And(ArticleDraft.HasType('goods_transfer'), ArticleDraft.GetSecondOrTarget.IsLocalPlayer)"

C_QBEST = C.q_best
C_MINE = "And(ArticleDraft.HasType('goods_transfer'), ArticleDraft.GetFirstOrSource.IsLocalPlayer)"
C_GAIN = C.best_gain
# Only goods that gain at their own best quantity (run 7: dye showed -0.76,
# because the first unit paid but the floor of 10 units did not).
C_SHOW = (f"And(And(ArticleDraft.HasType('goods_transfer'), "
          f"ArticleDraft.GetFirstOrSource.IsLocalPlayer), {gt(C_GAIN, fx(0))})")

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
# Smart Trade v1, EXPLORATION BUILD (run 6, 2026-10-05). Lines tagged "dev"
# check our maths against the engine; tools/package_release.py refuses to ship
# a file containing them.
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
				custom_tooltip_textbox = { raw_text = "dev: script margin [Article.MakeScope.ScriptValue('st_article_margin')|2] vs GUI [@@A_MARGIN@@|2]; script home price [Article.MakeScope.ScriptValue('st_article_home_price')|2] / a [Article.MakeScope.ScriptValue('st_article_home_price_a')|2] / b [Article.MakeScope.ScriptValue('st_article_home_price_b')|2] vs GUI [@@A_PH@@|2]" }
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
				custom_tooltip_textbox = {
					visible = "[@@D_PAYS@@]"
					raw_text = "Best: [@@D_QBEST@@|0] a week, about @money![@@D_BEST_GAIN@@|D+=]. [ArticleDraft.GetSecondOrTarget.GetNameNoFormatting] wants up to [@@D_QAI@@|0]."
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
				custom_tooltip_textbox = { raw_text = "About @money![@@C_GAIN@@|D+=] at [@@C_QBEST@@|0] a week, the most profitable amount [ArticleDraft.GetSecondOrTarget.GetNameNoFormatting] still wants (estimate). Picking this good starts at that quantity." }
			}
		}
	}

	type smart_trade_best_button = button {
		using = default_button
		size = { 46 22 }
		enabled = "[ArticleDraft.CanBeModified]"
		block "action" {
			onclick = "[ArticleDraft.SetQuantity(@@D_QBEST@@)]"
		}
		block "tip" {
			tooltip = "SMART_TRADE_BEST_TT"
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
					margin_top = -3
					raw_text = "Net @money![@@A_NET_LANE@@|D+=]"
				}
				textbox = {
					visible = "[And(@@A_MINE@@, Not(@@A_HAS_LANE@@))]"
					autoresize = yes
					align = nobaseline
					using = fontsize_small
					margin_top = -3
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
				margin_top = -3
				raw_text = "Net @money![@@T_NET_LANE@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}
			textbox = {
				visible = "[And(And(PdxGuiWidget.HasContext('Treaty'), Country.IsLocalPlayer), @@T_SHOW_LAND@@)]"
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				margin_top = -3
				raw_text = "Net @money![@@T_NET_LAND@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}

			### SMART TRADE, draft only: the partner's market borders ours
			textbox = {
				visible = "[@@H_SHOW@@]"
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				margin_top = -3
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
 SMART_TRADE_TREATIES_TT:0 "#header Net treaty income, per week#!\nGoods you send: @money![@@P_TRADE@@|D+=]\nTheir shipping: @money![@@NEG_P_SHIP@@|D+=] (estimate)\nMoney transfers: @money![@@P_MONEY@@|D+=]\nShipping is paid in merchant marine at your market price; more ports lower it.\nPer treaty: see the outliner's Treaties list."
 SMART_TRADE_BEST_TT:0 "Set the quantity to [@@D_QBEST@@|0], the most profitable volume."
 SMART_TRADE_MAX_SEND_TT:0 "Set the quantity to [@@D_QMAX_SEND@@|0], filling [ArticleDraft.GetSecondOrTarget.GetNameNoFormatting]'s shortage without going over your surplus."
 SMART_TRADE_ACCEPT_SEND_TT:0 "Set the quantity to [@@D_QACC_SEND@@|0] for the highest acceptance."
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
						### SMART TRADE: best weekly gain for this good (estimate)
						textbox = {
							visible = "[@@C_SHOW@@]"
							parentanchor = top|left
							position = { 5 2 }
							autoresize = yes
							align = nobaseline
							using = fontsize_small
							raw_text = "@money![@@C_GAIN@@|D+=]"
							tooltipwidget = { smart_trade_card_tooltip = {} }
						}'''

# 2. The card's own click: vanilla picks the good; we then set the best
#    quantity, so the default IS the best quantity (Damien's option 1). On
#    goods that do not pay, or that the partner sends, it re-sets whatever
#    quantity the pick produced, which leaves vanilla's default in place.
PICK_ANCHOR = 'onclick = "[ArticleDraft.SetGood(Goods.Self)]"'
PICK_BEST = PICK_ANCHOR + '''
						### SMART TRADE: start from the best quantity
						onclick = "[ArticleDraft.SetQuantity(Select_CFixedPoint(@@C_MINE@@, @@C_QBEST@@, ArticleDraft.GetQuantity))]"'''

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
					blockoverride "action" { onclick = "[ArticleDraft.SetQuantity(@@D_QACC_SEND@@)]" }
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

PICKER_TYPES = [
    ("article_input_goods_list", [(CARD_ANCHOR, CARD_CHIP), (PICK_ANCHOR, PICK_BEST)]),
    ("selected_goods_and_amount", [(ROW_ANCHOR, ROW_BEST)]),
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


# --- Best quantity, computed in SCRIPT ---------------------------------------
# The GUI has no variables, so the corrected optimum written as one GUI
# expression is 142,364 characters. Script can store intermediate results
# (save_temporary_scope_value_as inside a limit, the same trick the treaty
# totals use), so the GUI passes the inputs in as value scopes and reads one
# number back:
#   GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('st_bh', MakeScopeValue(...))
#       ...AddScope('st_cap', ...).ScriptValue('st_q_best')
# Inputs: st_bh st_sh (home buy/sell orders), st_bp st_sp (partner), st_ph
# st_pp (today's prices), st_base, st_ship (shipping per unit), st_cap.
#
# Method (checked in Python against brute force on five market shapes,
# 2026-10-05): a linear first guess from the price rule's slopes at today's
# orders, then one Newton step using the exact prices and slopes at that
# guess. Within ~1% of the true optimum in every case, including the one the
# linear guess alone gets badly wrong (partner price already at its cap:
# linear recommends a loss of ~8K/wk, one step finds +7.8K vs a best of +7.9K).
# Squares are avoided (S / B / B, not S / (B x B)): fixed point overflows
# around 2 billion, i.e. buy orders above ~46K units.

OUT_SCRIPT = REPO / "smart_trade" / "common" / "script_values" / "smart_trade_best_quantity.txt"


def sv(*ops):
    return "{ " + " ".join(ops) + " }"


def sv_min(a, b): return sv(f"value = {a}", f"max = {b}")      # min(a, b)
def sv_max(a, b): return sv(f"value = {a}", f"min = {b}")      # max(a, b)


def sv_ratio(b, s):
    """(buy - sell) / min(buy, sell): the price rule's imbalance."""
    return sv(f"value = {b}", f"subtract = {s}", f"divide = {sv_max(sv_min(b, s), 0.01)}")


def sv_clamp1(x): return sv(f"value = {x}", "min = -1", "max = 1")


def sv_slope_home(b, s):
    """Price rise per unit bought: k x max(1/S, S/B/B)."""
    return sv(f"value = {sv_max(sv('value = 1', f'divide = {sv_max(s, 0.01)}'), sv(f'value = {s}', f'divide = {sv_max(b, 0.01)}', f'divide = {sv_max(b, 0.01)}'))}",
              "multiply = scope:st_k")


def sv_slope_partner(b, s):
    """Price fall per unit supplied: k x max(B/S/S, 1/B)."""
    return sv(f"value = {sv_max(sv(f'value = {b}', f'divide = {sv_max(s, 0.01)}', f'divide = {sv_max(s, 0.01)}'), sv('value = 1', f'divide = {sv_max(b, 0.01)}'))}",
              "multiply = scope:st_k")


def save(name, value):
    return f"save_temporary_scope_value_as = {{ name = {name} value = {value} }}"


def step(*saves):
    """An if-block whose limit only saves values (run in order, always true)."""
    body = "\n\t\t\t".join(saves)
    return f"\tif = {{\n\t\tlimit = {{\n\t\t\t{body}\n\t\t}}\n\t\tadd = 0\n\t}}"


def zero_if_capped(slope, ratio):
    return (f"\tif = {{ limit = {{ OR = {{ scope:{ratio} >= 1 scope:{ratio} <= -1 }} "
            f"{save(slope, 0)} }} add = 0 }}")


def prices_at(q, tag):
    """Save st_rh{tag} st_rp{tag} st_ph{tag} st_pp{tag} for quantity q."""
    bh_q = sv("value = scope:st_bh", f"add = {q}")
    sp_q = sv("value = scope:st_sp", f"add = {q}")
    return [
        step(save(f"st_rh{tag}", sv_ratio(bh_q, "scope:st_sh")),
             save(f"st_rp{tag}", sv_ratio("scope:st_bp", sp_q))),
        step(save(f"st_ph{tag}", sv("value = scope:st_ph", f"add = {sv(f'value = {sv_clamp1(f'scope:st_rh{tag}')}', f'subtract = {sv_clamp1('scope:st_rh0')}', 'multiply = scope:st_k')}")),
             save(f"st_pp{tag}", sv("value = scope:st_pp", f"add = {sv(f'value = {sv_clamp1(f'scope:st_rp{tag}')}', f'subtract = {sv_clamp1('scope:st_rp0')}', 'multiply = scope:st_k')}"))),
    ]


def clamp_q(x): return sv(f"value = {x}", "max = scope:st_cap", "min = 10")


SCRIPT_LINES = [
    "# GENERATED by tools/gen_smart_trade_gui.py. Edit the generator, not this file.",
    "# Best weekly quantity for a goods transfer the player sends, and its gain.",
    "# See the generator's comment block for inputs and method. Read-only.",
    "",
    "st_q_best = {",
    "\tvalue = 0",
    step(save("st_k", sv("value = scope:st_base", "multiply = 0.75")),
         save("st_rh0", sv_ratio("scope:st_bh", "scope:st_sh")),
         save("st_rp0", sv_ratio("scope:st_bp", "scope:st_sp"))),
    step(save("st_slh", sv_slope_home("scope:st_bh", "scope:st_sh")),
         save("st_slp", sv_slope_partner("scope:st_bp", "scope:st_sp"))),
    zero_if_capped("st_slh", "st_rh0"),
    zero_if_capped("st_slp", "st_rp0"),
    step(save("st_q1", clamp_q(sv(f"value = {sv('value = scope:st_pp', 'subtract = scope:st_ph', 'subtract = scope:st_ship')}",
                                  f"divide = {sv_max(sv('value = scope:st_slh', 'add = scope:st_slp', 'multiply = 2'), 0.0001)}")))),
    *prices_at("scope:st_q1", "1"),
    step(save("st_slh1", sv_slope_home(sv("value = scope:st_bh", "add = scope:st_q1"), "scope:st_sh")),
         save("st_slp1", sv_slope_partner("scope:st_bp", sv("value = scope:st_sp", "add = scope:st_q1")))),
    zero_if_capped("st_slh1", "st_rh1"),
    zero_if_capped("st_slp1", "st_rp1"),
    step(save("st_d1", sv("value = scope:st_slh1", "add = scope:st_slp1")),
         save("st_spread1", sv("value = scope:st_pp1", "subtract = scope:st_ph1", "subtract = scope:st_ship"))),
    step(save("st_q2", clamp_q(sv("value = scope:st_q1",
                                  f"add = {sv(f'value = {sv('value = scope:st_spread1', f'subtract = {sv('value = scope:st_q1', 'multiply = scope:st_d1')}')}', f'divide = {sv_max(sv('value = scope:st_d1', 'multiply = 2'), 0.0001)}')}")))),
    "\tvalue = scope:st_q2",
    "}",
    "",
    "st_best_gain = {",
    "\tvalue = 0",
    # Recomputed here rather than trusting temporary values saved inside the
    # nested st_q_best call to survive into this one.
    step(save("st_qb", "st_q_best")),
    step(save("st_k", sv("value = scope:st_base", "multiply = 0.75")),
         save("st_rh0", sv_ratio("scope:st_bh", "scope:st_sh")),
         save("st_rp0", sv_ratio("scope:st_bp", "scope:st_sp"))),
    *prices_at("scope:st_qb", "b"),
    "\tvalue = scope:st_qb",
    "\tmultiply = { value = scope:st_ppb subtract = scope:st_phb subtract = scope:st_ship }",
    "}",
    "",
]
SCRIPT = "\n".join(SCRIPT_LINES)

OUTPUTS = {OUT_GUI: GUI + picker_block(), OUT_LOC: LOC, OUT_SCRIPT: SCRIPT}

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
