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

**How shipping is decided** (game files, 1.13.11, unless marked):

- **Overland or by sea.** The deciding test is whether the two **markets** are adjacent, not the two countries. Vanilla's `goods_transfer` article allows a transfer when both sides have a port OR `market = { is_adjacent_to_market = scope:other_country.market }`, and its non-fulfillment rule exempts adjacent markets from the supply-network check (`common/treaty_articles/13_goods_transfer.txt`). An adjacent pair gets no lane and pays no shipping. That fits Germany: no lane listed, presumably because the German market reaches Portugal through a member next to it (unverified which).
- **Lane cost.** Merchant marine demand × merchant marine price. Vanilla's own breakdown tooltip lists one entry per good, "N from Q goods (1 per MULT traded)", plus a "Travel Distance D: ×V (+×M per expected distance)" multiplier (loc `SHIPPING_LANE_CONVOY_COST_GOOD_ENTRY`, `SHIPPING_LANE_BREAKDOWN_TRAVEL_DISTANCE`). Defines: +0.15 per 1000 travel distance beyond the first 1000 (`SHIPPING_LANE_MERCHANT_MARINE_COST_SCALING`, `SEA_DISTANCE_EXPECTED_TRAVEL_DISTANCE`).
- **MULT is the unknown.** The defines still say 1 merchant marine per unit, but 1.13.7 (2026-05-27) "reduced Merchant Marine cost for ... goods transfer treaties". At 1 per unit your Austria lane would need a distance factor of 0.83 even at the floor merchant-marine price (12.5), below the minimum of 1.0. A candidate that fits both your lanes: MULT = the good's `traded_quantity` (5 for tools, dye and coffee) with coffee's `convoy_cost_multiplier` 0.5 applied, at a merchant-marine price near 40. That gives distance factors of 1.30 (Austria) and 3.05 (Persia), a 4.9 distance ratio, plausible for Lisbon to Genoa against Lisbon to the Gulf of Oman via Suez (my estimate). A fit, not a confirmation.
- **Endpoints.** Both your lanes start in Estremadura (Lisbon, your market capital), even for Persia, where Portuguese India is far closer. So the start is the market capital or its world-market hub, not the nearest port. The ends, Piemonte and Bampur, are neither partner's capital. That fits "the partner's port closest to the start", unverified.
- **Effectiveness.** Since 1.9.3, goods-transfer income and expense scale with lane effectiveness (patch notes, 2025-06-25). Your supply network showed 100% usage, so effectiveness may be below 1.
- **1.15 (open beta "1.14").** Multiple world-market hubs per market area, a bonus dev diary due the week of 2026-10-05, and hubs re-routing around tolls (Open Beta Update 4, 2026-09-30). Endpoints may move. So the mod reads endpoints from the lane (`GetBeginState`/`GetEndState`) and never hard-codes them.

For a signed treaty the mod reads the lane's own figures. For a draft it needs the formula, which is what the exploration build pins down.

**A lane carrying several goods:** split its cost by each good's share of units carried. Austria's 8.52K splits 131 : 687 between dye and tools.

**Draft prediction (v2).** The lane does not exist before signing, and no GUI function exposes the distance between two states. So the draft shows:

- margin before shipping at current prices: quantity × (partner price − home price);
- predicted shipping from the formula once MULT is confirmed, with the distance factor taken from vanilla's own prediction if the draft exposes one (exploration lines G5 to G7 test for a "Will use N merchant marine between X and Y" text), else from a live lane to the same partner, else shown as the floor (factor 1.0) and labelled "at least";
- breakeven shipping per unit, which equals the margin per unit;
- later, first-order price impact from the price formula (`PRICE_RANGE` 0.75, `BUY_SELL_DIFF_AT_MAX_FACTOR` 2). Trade centers arbitrage part of it away, so label it an upper bound.
- Market adjacency (overland, zero shipping) is not exposed to GUI either; a scripted GUI's `is_shown` trigger can evaluate `is_adjacent_to_market` for it.

**Placement:** v1 adds one per-treaty table (rows per good: units, sale, purchase, shipping share, net; treaty subtotal) inside the Treaties tooltip, via a partial `00_`-prefixed override of only the tooltip type (cf engine-notes.md § A partial `.gui` override works). That avoids replacing `budget_panel.gui`, which GORA UI+ also edits.

**Acceptance criteria (write before code):**

- With any goods transfer in force where the player is the source, the Treaties tooltip shows one row per good with units, sale, purchase, shipping share and net, plus a treaty subtotal.
- Sales summed over rows match vanilla's "Treaty Goods Transfer Income" within display rounding (3 significant figures); purchases match "Treaty Goods Transfer Expense"; each lane's shipping matches its Shipping Lanes line.
- A treaty with no lane (overland) shows shipping 0, not blank.
- No table appears when the player has no goods transfers.

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
- **Austria (recreated: dye 147, coffee 112):** −325 and −466 per week, −790 together, matching vanilla's lines. Germany +4.7K, Persia +162.
- **Persia's lane ends at Persia's world-market hub** (Bampur, hub = yes, not the capital) and starts at Portugal's market capital (Estremadura, capital = yes, hub = no).
- **GUI:** nested arithmetic renders in `.gui` `raw_text` (E1 = 422.52), unlike the loc case in Build All. `Article.GetShippingLane` works, as does `Treaty.GetShippingLaneOf(<source country>)` (D2). `GetShippingLaneOf(<article>)` returns null (D1).
- **The engine reads coffee as traded_quantity 5, convoy multiplier 0.5** (B3). If merchant-marine demand is qty ÷ traded_quantity × convoy multiplier × distance factor, coffee's base is 2.1 and Persia's distance factor is 2.34 (travel distance about 9,950); Austria's is 1.28 (about 2,840). Vanilla's breakdown behind C4 will confirm.
- **No travel distance is available to mods.** The script docs (`Documents/.../Victoria 3/docs/triggers.log`) have only military distance triggers, and the GUI exposes only camera-dependent screen positions. So a draft cannot compute its distance, not even a worst case from the partner's capital.

**Draft prediction, revised: breakeven distance.** Margin per unit and the per-unit shipping base are both computable before signing, so the draft shows the distance factor at which the deal stops paying:

    breakeven factor = (partner price − home price) × traded_quantity ÷ (convoy multiplier × merchant-marine price)

Coffee → Persia breaks even at ×3.80 and runs at ×2.34: profitable. Dye → Austria breaks even at ×1.07 and runs at ×1.28: a loss. Coffee → Austria breaks even at ×0.49: a loss at any distance. Below 1.0 means the deal loses even overland-adjacent by sea, which needs no distance at all to judge. Next to it, the draft lists the factors of the player's existing lanes ("your lane to Piemonte runs ×1.28") as reference points, plus vanilla's own prediction text if the draft has one (G5 to G7, untested).

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
