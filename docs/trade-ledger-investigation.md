# Trade treaty P&L mod: investigation (2026-10-03, game 1.13.11)

## TLDR

- **Nothing shows it today.** Vanilla splits each goods transfer across three budget tooltips and never joins them. No Workshop or Paradox Mods mod does it either.
- **Your own save shows why it matters.** The Austria treaty books +£34.6K/week of sales and most likely loses about £3.9K/week once shipping is counted (cf § 1).
- **Demand:** about 6 Steam threads complain specifically about treaty cost or shipping visibility. The adjacent demand is much bigger: Trade Partners, a units-only trade UI mod, has 12,703 subscribers after 128 days.
- **Feasible as a read-only GUI mod**, the same pattern as Build All. Every engine function it needs exists in the 1.13 dump.
- **Name:** "Smart Trade" is unused, but on this Workshop "Smart" means automation. I recommend **Trade Ledger**.
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

**Shipping must be read from the lane, not modelled.** The defines give 1 merchant marine per unit, +15% per 1000 travel distance beyond the first 1000 (`SHIPPING_LANE_MERCHANT_MARINE_COST_SCALING`, `SEA_DISTANCE_EXPECTED_TRAVEL_DISTANCE`). Your Austria lane would need a distance factor of 0.83 even at the floor merchant-marine price (12.5), and the formula's minimum is 1.0. Something else scales it, most likely lane effectiveness (1.9.3 made goods-transfer flows scale with it). So existing treaties use the lane's own figures.

**A lane carrying several goods:** split its cost by each good's share of units carried. Austria's 8.52K splits 131 : 687 between dye and tools.

**Draft prediction (v2).** Shipping is unknowable before signing because the lane does not exist yet. The draft can still show:

- margin before shipping at current prices: quantity × (partner price − home price);
- breakeven shipping per unit, which equals that margin per unit;
- actual shipping per unit on any live lane to the same partner, as a reference;
- later, first-order price impact from the price formula (`PRICE_RANGE` 0.75, `BUY_SELL_DIFF_AT_MAX_FACTOR` 2). Trade centers arbitrage part of it away, so label it an upper bound.

**Placement:** v1 adds one per-treaty table (rows per good: units, sale, purchase, shipping share, net; treaty subtotal) inside the Treaties tooltip, via a partial `00_`-prefixed override of only the tooltip type (cf engine-notes.md § A partial `.gui` override works). That avoids replacing `budget_panel.gui`, which GORA UI+ also edits.

**Acceptance criteria (write before code):**

- With any goods transfer in force where the player is the source, the Treaties tooltip shows one row per good with units, sale, purchase, shipping share and net, plus a treaty subtotal.
- Sales summed over rows match vanilla's "Treaty Goods Transfer Income" within display rounding (3 significant figures); purchases match "Treaty Goods Transfer Expense"; each lane's shipping matches its Shipping Lanes line.
- A treaty with no lane (overland) shows shipping 0, not blank.
- No table appears when the player has no goods transfers.

**First build is an exploration run** (mechanism partly unknown). A dev-only panel prints our candidates next to vanilla's own text, so one screenshot settles all of these:

1. purchase price: home market price vs origin-state price, with and without lane effectiveness;
2. sale price: partner market price vs destination-state price;
3. shipping: lane merchant-marine demand × merchant-marine price, market vs state price;
4. whether the Shipping Lanes total lags a week;
5. whether the data chain resolves inside the budget tooltip context at all.

**Risks:** 1.15 (in open beta as "1.14") adds several world-market hubs and touches routing; treaty accounting looks untouched, but `budget_panel.gui` may change.

## 5. Name

- **"Smart Trade":** 0 hits on the Victoria 3 Workshop, none on Paradox Mods. A RimWorld mod of that name is an auto-trader, and on this Workshop "Smart" mostly means automation (Smart Economy auto-sets tariffs, Smart AI Construction, Smart Private Economy). Players would expect it to trade for them.
- **Trade Ledger** (recommended): 0 hits, matches a search for "trade", and "ledger" says it reports.
- **Other free names:** Trade Profits, Trade Margins, Trade Breakdown, Smart Trade Ledger (keeps the brand).
- **Mod id:** it is permanent from the first upload; the display title is not. Pick the folder name (`trade_ledger/` at the repo root, next to `bulk_construction/`) before scaffolding.

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
2. Pick the name; I scaffold `trade_ledger/` (or your choice) and write the exploration build.
3. One exploration run: open the budget's Treaties tooltip with your current save, take one screenshot.
4. Build v1 against the confirmed formulas; one confirmation run; ship.
