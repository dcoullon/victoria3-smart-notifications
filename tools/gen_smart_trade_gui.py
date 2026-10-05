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

# --- Draft, per article (context: ArticleDraft; Country = maintenance payer) -
D_Q = "ArticleDraft.GetQuantity"
D_GH = "ArticleDraft.GetGoods.WithMarketContext(ArticleDraft.GetFirstOrSource.GetMarket.Self)"
D_GP = "ArticleDraft.GetGoods.WithMarketContext(ArticleDraft.GetSecondOrTarget.GetMarket.Self)"
BASE = "ArticleDraft.GetGoods.GetBasePrice"


def f_imb(b, s):
    """Vanilla price rule, confirmed in game 2026-10-03 to reproduce today's
    price from buy and sell orders exactly: base x (1 + 0.75 x clamp((buy -
    sell) / min(buy, sell))). PRICE_RANGE 0.75, BUY_SELL_DIFF_AT_MAX_FACTOR 2."""
    return mul(fx(0.75), clamp1(div(sub(b, s), f"Min_CFixedPoint({b}, {s})")))


BH, SH = f"{D_GH}.GetMarketBuyOrders", f"{D_GH}.GetMarketSellOrders"
BP, SP = f"{D_GP}.GetMarketBuyOrders", f"{D_GP}.GetMarketSellOrders"
D_PH = f"{D_GH}.GetMarketPrice"
D_PP = f"{D_GP}.GetMarketPrice"
D_PH1 = add(D_PH, mul(BASE, sub(f_imb(add(BH, D_Q), SH), f_imb(BH, SH))))
D_PP1 = add(D_PP, mul(BASE, sub(f_imb(BP, add(SP, D_Q)), f_imb(BP, SP))))
D_MARGIN = mul(D_Q, sub(D_PP1, D_PH1))
D_TQ = "ArticleDraft.GetGoods.GetTradedQuantity"
D_SHIP_LO = mul(div(D_Q, D_TQ), MMP)
D_SHIP_HI = mul(D_SHIP_LO, fx(1.5))
D_NET_LO = sub(D_MARGIN, D_SHIP_HI)
D_NET_HI = sub(D_MARGIN, D_SHIP_LO)
D_BREAKEVEN = div(mul(sub(D_PP1, D_PH1), D_TQ), MMP)
D_ADJ = ("GetScriptedGui('st_markets_adjacent_sgui').IsValid(GuiScope.SetRoot("
         "ArticleDraft.GetFirstOrSource.MakeScope).AddScope('st_other', "
         "ArticleDraft.GetSecondOrTarget.MakeScope).End)")
D_SHOW = "And(ArticleDraft.HasType('goods_transfer'), Country.IsLocalPlayer)"

TOKENS = {k: v for k, v in globals().items() if k.isupper() and isinstance(v, str)
          and k not in ("REPO",)}

GUI = r'''# GENERATED by tools/gen_smart_trade_gui.py. Edit the generator, not this file.
#
# Smart Trade v1, EXPLORATION BUILD (run 4, 2026-10-03). The one line tagged
# "dev" checks script against GUI; tools/package_release.py refuses to ship
# a file containing it.
#
# Redefines four small vanilla types from our own file (no vanilla file is
# copied). THE FILENAME IS LOAD-BEARING: `00_` sorts before the vanilla files
# below, and the engine keeps the first definition it reads
# (docs/engine-notes.md, "A partial .gui override works";
# check_type_overrides_sort_first enforces it).
#   goods_transfer_article        vanilla gui/treaty_panel.gui:1213
#   total_influence_cost          vanilla gui/treaty_panel.gui:756
#   article_draft_influence_cost  vanilla gui/treaty_draft_panel.gui:884
#   outliner_compact_treaty_item  vanilla gui/outliner_pinnable_types.gui:366
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
						raw_text = "Shipping: @money![@@NEG_A_SHIP@@|D+=] ([Article.GetShippingLane.GetBeginState.GetName] to [Article.GetShippingLane.GetEndState.GetName], x[@@A_DIST@@|2])"
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
				custom_tooltip_textbox = { raw_text = "Hover a goods transfer for its breakdown." }
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
					raw_text = "Shipping: @money![@@NEG_D_SHIP_LO@@|D+=] to @money![@@NEG_D_SHIP_HI@@|D+=] (short to long route)"
				}
				custom_tooltip_textbox = {
					visible = "[@@D_ADJ@@]"
					raw_text = "#bold Net: @money![@@D_MARGIN@@|D+=] a week#!"
				}
				custom_tooltip_textbox = {
					visible = "[Not(@@D_ADJ@@)]"
					raw_text = "#bold Net: @money![@@D_NET_LO@@|D+=] to @money![@@D_NET_HI@@|D+=] a week#!"
				}
				custom_tooltip_textbox = {
					visible = "[Not(@@D_ADJ@@)]"
					raw_text = "Breaks even up to route x[@@D_BREAKEVEN@@|2] (short routes x1.00)"
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
					raw_text = "Net @money![@@A_NET_LANE@@|D+=]"
				}
				textbox = {
					visible = "[And(@@A_MINE@@, Not(@@A_HAS_LANE@@))]"
					autoresize = yes
					align = nobaseline
					using = fontsize_small
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
				raw_text = "Net @money![@@T_NET_LANE@@|D+=]/wk"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}
			textbox = {
				visible = "[And(And(PdxGuiWidget.HasContext('Treaty'), Country.IsLocalPlayer), @@T_SHOW_LAND@@)]"
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				raw_text = "Net @money![@@T_NET_LAND@@|D+=]/wk"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
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
			raw_text = "Net @money![@@D_MARGIN@@|D+=]/wk"
			tooltipwidget = { smart_trade_draft_tooltip = {} }
		}
		textbox = {
			visible = "[And(@@D_SHOW@@, Not(@@D_ADJ@@))]"
			autoresize = yes
			align = right|nobaseline
			using = fontsize_small
			raw_text = "Net @money![@@D_NET_LO@@|D+=] to [@@D_NET_HI@@|D+=]"
			tooltipwidget = { smart_trade_draft_tooltip = {} }
		}
	}
}

types pinnable_outliner_items {
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

			### SMART TRADE: net to the player, left of the time remaining
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
				position = { -10 0 }
				parentanchor = right|vcenter
				autoresize = yes
				align = nobaseline
				using = fontsize_small
				raw_text = "@money![@@T_NET_LANE@@|D+=]"
				tooltipwidget = { smart_trade_treaty_tooltip = {} }
			}
			textbox = {
				visible = "[And(Not(@@T_DAYS@@), @@T_SHOW_LAND@@)]"
				position = { -10 0 }
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
 # tooltip is assembled by engine code from loc entries, so the line is
 # appended to the balance entry, which always shows (run 3 also tried the
 # temporary-expenses entry: it splits that section from its own sub-lines).
 # Vanilla's text comes first, verbatim; REPLACED_LOC_BASELINE in
 # tools/check_references.py catches a patch changing it.
 BALANCE_WITHOUT_TEMPORARY_INCOME_AND_EXPENSES:0 "\nBalance (excluding Temporary Income and Expenses): #v @money![GetPlayer.PredictBalanceWithoutTemporaryIncomeAndExpenses|D+=]#!\n#bold (Smart Trade) Net treaty income:#! #tooltippable #tooltip:[GetPlayer.GetTooltipTag],SMART_TRADE_TREATIES_TT ~@money![@@P_NET@@|D+=]#!#! (already counted above)"
 SMART_TRADE_TREATIES_TT:0 "#header Net treaty income, per week#!\nGoods you send, sale minus purchase: @money![@@P_TRADE@@|D+=]\nShipping lanes for them: @money![@@NEG_P_SHIP@@|D+=] (estimated at the short-route rate)\nMoney transfers: @money![@@P_MONEY@@|D+=]\n\nPer treaty: the Treaties list in the outliner."
'''

# Derived tokens used by the templates.
TOKENS.update({
    "NEG_A_BUY": neg(A_BUY), "NEG_A_SHIP": neg(A_SHIP),
    "PU_LANE": div(A_NET_LANE, A_Q), "PU_LAND": div(A_NET_LAND, A_Q),
    "NEG_D_SHIP_LO": neg(D_SHIP_LO), "NEG_D_SHIP_HI": neg(D_SHIP_HI),
    "NEG_P_SHIP": neg(P_SHIP),
})


def expand(text: str) -> str:
    # Longest names first so @@A_NET_LANE@@ is never clobbered by a shorter token.
    for name in sorted(TOKENS, key=len, reverse=True):
        text = text.replace(f"@@{name}@@", TOKENS[name])
    assert "@@" not in text, [l for l in text.splitlines() if "@@" in l][:3]
    return "﻿" + text


OUTPUTS = {OUT_GUI: GUI, OUT_LOC: LOC}

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
