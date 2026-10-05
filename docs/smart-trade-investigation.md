# Trade treaty P&L mod: investigation (2026-10-03, game 1.13.11)

## TLDR

- **Nothing shows it today.** Vanilla splits each goods transfer across three budget tooltips and never joins them. No Workshop or Paradox Mods mod does it either.
- **Your own save shows why it matters.** The Austria treaty books +£34.6K/week of sales and most likely loses about £3.9K/week once shipping is counted (cf § 1).
- **Demand:** about 6 Steam threads complain specifically about treaty cost or shipping visibility. The adjacent demand is much bigger: Trade Partners, a units-only trade UI mod, has 12,703 subscribers after 128 days.
- **Feasible as a read-only GUI mod**, the same pattern as Build All. Every engine function it needs exists in the 1.13 dump.
- **Name: Smart Trade** (Damien's decision, 2026-10-03), matching Smart Notifications. Unused on the Workshop. "Smart" usually means automation there, so the Workshop title and first line must say it only displays (cf § 5).
- **Workshop lesson:** about 75% of each mod's subscribers to date arrived in launch week. Have everything ready before the first upload.

## 1. Does vanilla already show it?

No. Your screenshots (1918-04-11 and 04-14) confirm how a goods transfer is booked. Your treasury buys the goods in your market and sells them in the partner's market. Both legs are yours, so each treaty is state arbitrage. The three halves live in three places:

| Leg | Where vanilla shows it | Granularity |
|---|---|---|
| Sale in partner market | Budget > Treaties (income) > Treaty Goods Transfer Income | per good, per partner |
| Purchase in home market | Budget > Treaties (expense) > Treaty Goods Transfer Expense | per good, per partner |
| Shipping | Budget > Shipping Lanes | per lane; one lane can carry several goods |

Neither the treaty draft picker nor the market Trade tab fills the gap. The picker shows each market's balance (tools +1.02K for you, −3.92K for Germany) and a quantity slider, with no prices, freight or net. The Trade tab covers world-market trade, which is private trade-center business, so it never touches the treasury.

Your treaties, computed from the tooltips (`treaty_pnl.py` in the session scratchpad):

| Treaty | Sales | Purchases | Shipping | Net/week |
|---|---|---|---|---|
| Tools → Germany, 703/wk | 31.0K | 26.3K | none listed | +4.7K |
| Coffee → Persia, 21/wk | 1.21K | 777 | 256 | +177 |
| Dye 131 + tools 687 → Austria | 34.6K | ≈29.9K (assumption) | 8.52K | ≈ −3.9K |

Assumption: the Austria purchase figure equals the rise in the Treaties expense line between your two dates (28.3K → 58.2K). That rise probably also includes a higher price on the German tools, because buying 687 more tools at home pushes up the price you pay for both treaties.

Germany profits mainly because it has no sea lane. Without shipping, Austria would net +4.65K.

Open oddity: the Shipping Lanes **total** stayed at −10.3K after the Austria lane appeared at −8.52K. My hypothesis: `GetPortConnectionExpenses` is last week's actual while `PredictTreatyIncome` is live.

## 2. Player demand

- **Direct complaints (Steam General Discussions):**
  - about 6 threads, 1 to 10 comments each;
  - two clusters: after 1.9 (June to July 2025, "do I pay for treaty goods?") and after 1.13 (May 2026, shipping costs nobody could see in advance);
  - representative thread: [Shipping lane cost](https://steamcommunity.com/app/529340/discussions/0/841753826211045524/) (2026-05-12), where a reply asks for any way to see a lane's merchant marine need before signing;
  - three Paradox forum threads, titles only (the forum's bot check blocked reading them).
- **Adjacent demand:** [Trade Partners](https://steamcommunity.com/sharedfiles/filedetails/?id=3733651973) has 12,703 current and 13,841 lifetime subscribers since 2026-05-27 (Steam API, today). At least 8 of its comments say it belongs in the base game. It shows units only, no money.
- **Counter-signal:**
  - some players call goods transfers diplomatic sweeteners rather than profit tools;
  - Paradox has patched part of the visibility (lane cost share breakdown in 1.13.7, efficiency trend and shortage alert in 1.13.9).
- **Gap:** Reddit was unreachable from every tool, and r/victoria3 is the main venue. A search there for "goods transfer" and "shipping lane cost" before committing would take you two minutes.

My read: the pain is real and recurring, with low volume. The Reddit hook is strong, because the screenshot shows a loss vanilla hides.

## 3. Existing mods

No mod shows per-good, per-partner money or predicts treaty profit. About 25 Workshop searches and Paradox Mods were checked.

| Mod | Subscribers | What it does | Overlap |
|---|---|---|---|
| Trade Partners | 12,703 | import/export partner charts | units only, no money |
| GORA UI+ | 9,887 | wider market panels, budget Capital tab, bundles Trade Partners | no P&L; **edits the budget panel**, so compatibility matters |
| Advanced Market Panel | 4,983 | supply/demand tables, risk reports | unverified, description shows no money per partner |
| National Budget Charts | 223 | budget pie charts | category level only |

## 4. How to build it

**Definition (MVP):** the treasury effect of goods-transfer treaties. Private trade-center profit on the world market is out of scope; it is not the player's money, and mixing the two would give a number nobody can check against the budget.

**Architecture:** GUI only, read-only. No script, no save-game state, no possible cheat (the repo-wide "mods never cheat" rule). The same pattern as `bulk_construction/`: one `.gui` file plus loc.

**Data chain**, every link confirmed in `reference/data_types/` and used by vanilla GUI:

- `Country.GetInForceTreaties` → `Treaty.GetAllArticles` → filter `Article.HasType('goods_transfer')`
- `Article.GetGoods`, `Article.GetQuantity`, `Article.GetSourceCountry`
- price per market: `Goods.WithMarketContext(<market>).GetMarketPrice` (vanilla's draft picker uses exactly this)
- `Article.GetShippingLane` → `ShippingLane.GetMerchantMarineDemandRaw`, `ShippingLane.GetEffectivenessRaw`
- merchant marine price: `GetGoods('merchant_marine').WithMarketContext(<market>).GetMarketPrice`
- arithmetic: `Multiply_CFixedPoint`, `Subtract_CFixedPoint`, `Divide_CFixedPoint`

**How shipping is decided** (confirmed in game 2026-10-03 unless marked):

- **Overland or by sea.** The deciding test is whether the two **markets** are adjacent, not the two countries. Vanilla's `goods_transfer` article allows a transfer when both sides have a port OR `market = { is_adjacent_to_market = scope:other_country.market }`, and its non-fulfillment rule exempts adjacent markets from the supply-network check (`common/treaty_articles/13_goods_transfer.txt`). An adjacent pair gets no lane and pays no shipping. Germany fits: its market touches Portugal's in Africa (Damien's observation).
- **Lane cost = merchant-marine demand × the home market's merchant-marine price.** Demand = Σ (quantity ÷ the good's `traded_quantity`) × distance multiplier. Vanilla's own breakdown for the Austria lane reads "+29.4 from 147 Dye (1 per 5 traded)", "+22.4 from 112 Coffee (1 per 5 traded)", "Travel Distance 528: ×1.00 (+×0.15 per expected distance)". The good's `convoy_cost_multiplier` is not applied (goods.md says it is for military supply). The rates live in `common/goods/00_goods.txt`: tools, dye and coffee 5, wood 10, grain 12.
- **Distance multiplier.** ×1.00 up to the expected distance of 1000 (`SEA_DISTANCE_EXPECTED_TRAVEL_DISTANCE`), then +0.15 per expected distance (`SHIPPING_LANE_MERCHANT_MARINE_COST_SCALING`). Lisbon to Genoa is 528 (×1.00); Lisbon to the Gulf of Oman via Suez comes out at ×1.17 (4.92 ÷ 4.2). Whether the step above 1000 is continuous is unconfirmed; Persia's breakdown would settle it.
- **Endpoints.** The lane starts at the home market capital (Estremadura: capital yes, hub no), even when a colony port is far closer. It ends at a port in the partner market, not its capital: Piemonte for Austria (hub no), Bampur for Persia (hub yes). Consistent with "the partner-market port nearest the start" (Damien's reading); unverified as a rule.
- **Effectiveness.** Since 1.9.3, goods-transfer income and expense scale with lane effectiveness (patch notes, 2025-06-25). Both observed lanes ran at 1.00 despite 100% supply network usage, so the scaling is still untested.
- **1.15 (open beta "1.14").** Multiple world-market hubs per market area, a bonus dev diary due the week of 2026-10-05, and hubs re-routing around tolls (Open Beta Update 4, 2026-09-30). Endpoints may move. So the mod reads endpoints from the lane (`GetBeginState`/`GetEndState`) and never hard-codes them.

For a signed treaty the mod reads the lane's own figures. A lane carrying several goods splits exactly: each good's share is its own quantity ÷ `traded_quantity`, the entries vanilla's breakdown lists.

**Draft prediction.** No distance is available to mods (cf run 1 results) and vanilla shows no merchant-marine prediction for a draft (run 2). The multiplier is narrow, though: ×1.00 within 1000 and ×1.17 for Lisbon to Persia via Suez. So the draft shows:

- margin at current market prices: quantity × (partner price − home price);
- zero shipping when the markets are adjacent, detected through a scripted GUI whose `is_shown` evaluates `is_adjacent_to_market` (untested);
- otherwise shipping at ×1.00 to ×1.50, a range meant to cover the longest routes (assumption, to revisit as more lanes are read);
- breakeven multiplier = (partner price − home price) × `traded_quantity` ÷ merchant-marine price. Below 1.0 the good loses on any sea route;
- later, first-order price impact from the price formula (`PRICE_RANGE` 0.75, `BUY_SELL_DIFF_AT_MAX_FACTOR` 2). Trade centers arbitrage part of it away, so label it an upper bound.

On Damien's treaties: coffee → Persia breaks even at ×1.90 and runs at ×1.17 (+162/week); dye → Austria at ×1.07, runs at ×1.00 (+104); coffee → Austria at ×0.24 (−896, a loss at any distance).

**Design v1** (proposed 2026-10-03; mockup `docs/smart-trade-design-mockup.png`):

Revised the same day after Damien's review:

1. **Signed treaty, treaty panel.** The headline is the treaty's net to the player, positive or negative, in the treaty header. Hover: one block per good the player sends (sale, purchase, shipping with lane and multiplier, net, per-unit net, saving per unit renegotiated away). No distance verdict: a signed lane's distance is known. Goods the partner sends cost the player's treasury nothing and show nothing. If the treaty total cannot be computed (see constraints), each article shows its own net instead.
2. **Treasury tooltip (top bar money).** One "Net treaty income" line, labelled as already counted in the lines above. Hover: treaties with a non-zero impact, one row each, split into net trade (goods transfers) and money transfers; no per-good rows, so late-game treaty counts do not flood it. That tooltip is assembled by engine code from loc entries (`TEMPORARY_EXPENSES_BREAKDOWN`, `BALANCE_WITHOUT_TEMPORARY_INCOME_AND_EXPENSES`...), so the line is added by extending one entry via `localization/replace`, with no GUI file copied. The temporary-expenses entry may only show when temporary expenses exist; test which entry is always present.
3. **Draft.** A predicted net tag on each goods transfer article plus the hover breakdown, both built for Damien to judge in game. Needs a redefinition of vanilla's `article_draft` type (about 600 lines), so it gets a drift check against vanilla like Smart Notifications' full overrides.

The Budget panel's Treaties tooltips are left alone.

**Why the draft cannot show an exact number:** the route length is computed inside the engine and exposed to neither GUI nor script, and after the first weeks the economy reacts (trade centers, production) in ways no mod can simulate. What it can do: first-week price impact from buy and sell orders and the price rule, and shipping exact at ×1.00 for any partner port within 1000 of the home capital, with a long-route figure beside it.

**v2 backlog (Damien's ideas, 2026-10-03):**

- Sort the goods picker by predicted profit, so the most profitable goods surface first (`ArticleDraft.SortGoods` exists; parameters unknown).
- A smarter default quantity: the profit-maximising one, settable through `ArticleDraft.SetQuantity`. Vanilla's default often exceeds the receiving market's deficit.
- Show what the AI actually values: its acceptance formula is readable in `common/treaty_articles/13_goods_transfer.txt`, and vanilla's "AI will accept" reading is often wrong at the default quantity.
- A verdict per good inside the goods picker.
- (2026-10-05) Default quantity = the one that maximises the player's gain while the AI still accepts; plain max gain if that is too hard. The picker's AI yes/no should then reflect that quantity. Goods ordered by expected max gain, ideally only those the AI accepts.
- (later) Show which countries need no shipping lane (markets that border the player's), since overland is what makes goods transfers pay.

**Why sea transfers rarely pay (2026-10-05):** shipping costs one merchant marine per `traded_quantity` units, and Paradox set `traded_quantity` roughly inverse to price. At base merchant-marine price (50) every good's shipping costs 17% to 28% of its own base value (tools 25%, automobiles 17%), so a sea transfer needs a price gap of about a fifth of the good's value just to break even. Cheaper merchant marine is the lever: at the floor price (12.5) the same 960 tools to Austria go from about −£6.4K to +£1.2K a week.

**Vanilla's quantity and acceptance logic** (`common/treaty_articles/13_goods_transfer.txt`, read 2026-10-05):

- **Allowed range:** at least 10; at most the smaller of the partner market's import cap and the sender market's export cap, minus what treaties already move (`quantity_max_value`).
- **Suggested quantity** (`ai.quantity_input_value`): starts from the AI's export value minus the partner's import value, capped at about 35% of the partner market's consumption, floor 10. It ignores the partner's shortage. That the player's default slider comes from it is an inference: 960 tools was 4% of the 25,764 maximum.
- **What a receiving AI accepts:** its score rises with quantity up to its market's shortage + 10 (buy orders minus sell orders, plus 10), scaled by its import value and consumption and capped. Every unit beyond loses 0.3 points. So a default sized off consumption routinely overshoots the shortage, which is why the AI thumbs disagree with the deal you actually propose.
- **The thumbs on each goods card** come from `TreatyDraft.GetArticleTypeAcceptanceWithGood(type, country, goods)`, which takes no quantity: the engine evaluates its own. A mod cannot make them follow another quantity; the article's own acceptance figure does update live with the quantity.
- **Sorting** (`ArticleDraft.SortGoods`) accepts only vanilla's keys (`'name'`, `'own_price'`, `'other_balance'`...), so goods cannot be ordered by gain.

**Best quantity (built 2026-10-05, run 6 tests it):** the profit-maximising quantity of the linearised first-week gain, (price gap minus shipping per unit) ÷ (2 × combined price slope), where each slope is the price rule's derivative at today's buy and sell orders (zero where the price sits at its cap). It is capped at the partner's shortage + 10, so it never triggers the AI's "too much" penalty, and floored at 10. A "Best: N" button under the draft's Net sets it through `ArticleDraft.SetQuantity`; each goods card shows the estimated weekly gain at its own best quantity.

**Draft treaty total:** not feasible as built. GUI expressions cannot sum the draft's articles, and script cannot see drafts at all (no `MakeScope` on `TreatyDraft` or `ArticleDraft` in the dump). Signed treaties have a total because script iterates in-force articles.

**Before publishing:** remove the "dev" line from the goods-transfer hover (Damien's reminder, 2026-10-05); `tools/package_release.py` refuses to package while it is there.

**Constraints found while designing:**

- GUI expressions cannot sum over a list, so both totals need `GetPlayer.MakeScope.ScriptValue(...)` (vanilla uses it in loc and GUI) with a script value iterating `any_scope_treaty` / `every_scope_article`. Script has no absolute price value, only `market_goods_pricier` / `market_goods_cheaper` against base price, so prices are rebuilt from base prices generated out of `common/goods/00_goods.txt`; lane shipping in script is unverified. Without it, v1 shows rows only.
- The money-transfer articles of a treaty would join the treaty total the same way.

**Acceptance criteria (v1):**

- With a goods transfer in force where the player is the source, its article shows net per week; the hover's sale, purchase and shipping match vanilla's budget lines within display rounding (3 significant figures), and shipping matches the lane's line times the good's share.
- An overland article shows shipping 0 labelled "overland", not blank.
- An article the player receives shows who pays and no net.
- The budget table lists exactly the goods transfers the player sends; nothing appears when there are none.
- A draft chip changes when the good or quantity changes, and shows zero shipping for an adjacent market.

**First build is an exploration run** (mechanism partly unknown): `smart_trade/gui/00_smart_trade_debug.gui`. Hovering a goods transfer in the treaty panel prints our candidates next to vanilla's own budget text, one tagged line each (A1, B2...), so a few screenshots settle all of these:

1. purchase price: home market price (B2) vs origin-state price (C9), and whether lane effectiveness (C3) scales it;
2. sale price: partner market price (B5) vs destination-state price (C10);
3. shipping: merchant-marine demand × merchant-marine price, market (C6) vs state (C8);
4. MULT and the distance multiplier, from vanilla's own breakdown behind C4;
5. lane endpoints: capital or world-market hub on each end (B6, C2);
6. which lane accessor works: `Article.GetShippingLane` (C) or `Treaty.GetShippingLaneOf` (D1, D2);
7. whether nested arithmetic renders in `raw_text` (E1);
8. whether vanilla predicts a draft's merchant marine (G5 to G7, on the draft's influence cost cell);
9. whether the Shipping Lanes total lags a week (F3 against the lane lines).

**Exploration run 1 results (2026-10-03, game date 1918-04-19, paused):**

- **All three legs use market prices.** Coffee → Persia: 21 × home market price 37.69 = 791.51 (vanilla line: 791); 21 × partner market price 57.81 = 1,214.03 (vanilla: 1.21K); merchant-marine demand 4.92 × home market merchant-marine price 52.91 = 260.56 (vanilla: −260). The state-price candidates (C8, C9, C10) all miss.
- **Lane effectiveness was 1.00**, so whether it scales the flows is still untested.
- **Vanilla totals add up.** Goods-transfer income lines sum to 43.19K (vanilla 43.2K), expense lines to 36.12K (36.1K). The Shipping Lanes total (13,106) now includes the Austria lane, so the earlier 10.3K was a lag until the weekly tick.
- **Austria (recreated: dye 147, coffee 112):** +104 (dye) and −896 (coffee) per week, −792 together; vanilla's lines give −790. Germany +4.7K, Persia +162. (An earlier split of −325 / −466 wrongly applied coffee's convoy multiplier.)
- **Lane endpoints:** both start at Portugal's market capital (Estremadura). Persia's ends at its world-market hub (Bampur), Austria's at a non-hub port (Piemonte, run 2), so the end is not simply the partner's hub.
- **GUI:** nested arithmetic renders in `.gui` `raw_text` (E1 = 422.52), unlike the loc case in Build All. `Article.GetShippingLane` works, as does `Treaty.GetShippingLaneOf(<source country>)` (D2). `GetShippingLaneOf(<article>)` returns null (D1).
- **The engine reads coffee as traded_quantity 5, convoy multiplier 0.5** (B3). Run 2's breakdown showed only the traded quantity matters.
- **Run 2 (same day):** vanilla's breakdown confirmed the formula (cf "How shipping is decided"); the draft's G3/G4 prices resolve; vanilla's draft effects say only "transfers N goods every week" (G5) and G6/G7 are empty, so vanilla has no merchant-marine prediction for drafts.
- **No travel distance is available to mods.** The script docs (`Documents/.../Victoria 3/docs/triggers.log`) have only military distance triggers, and the GUI exposes only camera-dependent screen positions. So a draft cannot compute its distance, not even a worst case from the partner's capital.

**Exploration run 3 (v1 build, 2026-10-03):** `gui/00_smart_trade.gui` (generated by `tools/gen_smart_trade_gui.py`), script values in `common/script_values/`, the adjacency bridge in `common/scripted_guis/`, and the treasury line in `localization/replace/`. It answers, in one run:

1. Do the script values work at all, and which price reconstruction matches the GUI (dev X1, X1b)?
2. Do script margins equal the GUI's and, summed, vanilla's treaties income minus expense (X2, X5, X6)?
3. Does the treaty header chip render on the signed-treaty panel only?
4. Which treasury entry shows the line, (A) temporary expenses or (B) balance, and does nested arithmetic render in loc (B)? Does the per-treaty hover widget register?
5. Does the adjacency bridge say yes for Germany and no for a sea partner (Y3)?
6. Does vanilla's price rule reproduce today's price from buy and sell orders (Y1, Y2)? If not, the first-week price uses only the rule's change, which is what the build already does.
7. Do mutual articles' influence cells keep their size inside the new wrapper?

**Risks:** 1.15 (in open beta as "1.14") adds several world-market hubs and touches routing; treaty accounting looks untouched, but `budget_panel.gui` may change.

## 5. Name

**Decided: Smart Trade**, mod id `smart_trade` (folder `smart_trade/`). The id is permanent from the first upload; the display title is not.

- **Availability:** 0 hits on the Victoria 3 Workshop, none on Paradox Mods. A RimWorld mod of that name is an auto-trader.
- **Mitigation for the automation reading:** on this Workshop "Smart" mostly means automation (Smart Economy auto-sets tariffs, Smart AI Construction, Smart Private Economy). So the Workshop title carries a subtitle that says it reports, e.g. "Smart Trade: Treaty Profit per Good", and the description's first line says it changes nothing in the game.
- **Alternatives considered:** Trade Ledger, Trade Profits, Trade Margins, Trade Breakdown, all unused.

## 6. Discovery

- **Reddit:** reuse the feature-request framing that worked for Build All, with the Austria case as the image: the budget books £34.6K a week of sales on a treaty that loses about £3.9K.
- **Timing:** post on the upload day; launch week decides most of the outcome (cf § 7).

## 7. What the Workshop stats say

Sources: Damien's sheet "Mod subscribers daily" to 2026-09-25, plus a Steam API reading today. Computed in `stats.py` (session scratchpad).

| | Smart Notifications | Build All |
|---|---|---|
| Subscribers today | 415 | 431 |
| Lifetime subscribers | 461 | 459 |
| Churn (lifetime − current) | 10.0% | 6.1% |
| Lifetime subs / visitors | 28.1% | 38.3% |
| Favorites / subscribers | 14.5% | 6.7% |
| Subs at day 7 / day 15 | 309 / 401 | 328 / 431 |
| Share of today's subs reached by day 7 | 74% | 76% |

- **Launch week decides it.** Both mods had about 75% of today's subscribers by day 7, and their age-aligned curves are close (309 vs 328 at day 7).
- **A self-explaining title converts better.** Build All turns 38% of visitors into subscribers, Smart Notifications 28%.
- **Steam's own lists probably drove Build All, not Reddit.** Its Reddit day brought 104 visitors (0.2% of the post's 50k views). Then visits accelerated to 215/day on days 6 and 7, while a Reddit post would be decaying. Inference only: Steam gives no referrer data.
- **A link in the R5 comment reaches few readers.** Smart Notifications' R5 comment drew 2.2k views against 56k for the post (3.9%).
- **Churn is low** for both mods.
- **The sheet has had no readings since 09-25.** Blank rows produce bogus −1603 / −401 deltas, and the 09-20 and 09-24 rows are interpolations. The Steam API call in `docs/workshop-stats.md` returns everything needed, including lifetime subscribers.

## Next steps

1. Check Reddit for "goods transfer" and "shipping lane cost" (2 min, you).
2. Done 2026-10-03: `smart_trade/` scaffolded and junctioned, exploration build `gui/00_smart_trade_debug.gui` written (§ 4).
3. One exploration run (recipe in the commit that added the build).
4. Build v1 against the confirmed formulas; one confirmation run; ship.
