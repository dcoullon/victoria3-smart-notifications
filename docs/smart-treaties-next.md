# Smart Treaties: next build

Locked 2026-11-05. Measurement run done 2026-11-10 (section 1, Results). Goal (Damien): bigger numbers and more
people enjoying the mod. Findings behind this: smart-trade-investigation.md.

## Order

Revised 2026-11-10 after the measurement run (Damien):

1. Measurement build (dev only): done for AI deals; v0.03 logs Damien's Spain
   1836 campaign for player-sized deals.
2. ~~"Treaty turned negative" alert~~: dropped, the outliner already shows
   each treaty's net.
3. Trade recommender: the top 5 goods transfers to make, in the Trade tab.
4. Opportunity alert: a rare toast from the recommender's own result.

The predictor stays as it is for now. Any change to it later must keep the
goods cards' frame rate.

## 1. Measurement build

Replaces the Reddit idea and the manual Austria check. One deal proved little:
Linz drew -35.5 in the draft, +275 on 22 July, -23.9 by January, with sell
orders flat and buy orders falling, against a model that assumed the opposite.

A dev-only mod logs every goods transfer in the world, AI deals included:
- when a treaty enters into force (`on_treaty_entered_into_force`, root is the
  treaty): both markets' price, buy orders, sell orders, imports and exports
  (`market_goods_imports`, `market_goods_exports`), plus good, quantity and
  whether it has a lane
- on `on_monthly_pulse`, the same fields for each live goods transfer

Run as an observer for about 20 game years, using `tools/log_archiver.py`,
since debug.log rotates, and an `ST_OBS|` tag added to `tools/scan_logs.py`.
`tools/build_census_mod.py` is the worked example. Python then replays the
draft's price rule on each deal's signing data and compares it to the price at
1, 3, 6, 12 and 24 months.

Questions it answers: how long until the market reacts, whether the rule's size
is right, how far ×1.25 is off with 1.15's hubs (it ran 1.31× high on the one
French lane), and whether a transfer adds to trade or just replaces what trade
centers were already moving (cf section 3). Unknown until run: how many goods
transfers the AI signs.

Accepted when: the report covers at least 30 deals, each with a signing row and
at least 6 monthly rows. Fewer than 30 means the AI rarely signs them, and the
fallback is a player run with several deals.

Same run, tagged probe: does a treaty hold a variable? Law scopes do not, and
the docs do not say for treaties. If not, the alert uses
`add_to_variable_list` on the player's country with the treaty as target.

**Built 2026-11-10, not yet run.** Mod `smart_trade_observer/` (dev only,
junctioned into the game's mod folder like the others), report
`tools/treaty_obs_report.py` (`--selftest` passes on synthetic data). Lines:
`ST_OBS|SIGN|MON|END|...` per goods transfer article, read through script
values that copy the shipped mod's proven market reads. Two more answers
ride on it: `inscope=` says whether the sender's `every_scope_treaty` still
finds a treaty after its binding period (the alert iterates that way), and
the one-off `PROBE` line tests the lane's real merchant marine demand, which
would measure the ×1.25 route guess directly. Not measurable: the lane cost
through script values (no script link exists), so the route question rests
on that probe. Unknowns that could break it, all visible in the first game
year: `market_goods_imports`/`_exports` as values (vanilla never uses them
that way; a load error names the file), and the date and number formats
(the report parses the common ones).

Damien, 2026-11-10: in game a treaty stays listed after its binding period
and disappears only when a signatory cancels it. `inscope=` checks that the
script iterator agrees with the UI.

**First run, 2026-11-10 (v0.01, stopped after 21 game months):**
- A treaty cannot hold a variable ("This scope doesn't support variables.
  Scope: Treaty"). The alert keeps its state in a variable list on the
  player's country.
- Numbers print plain (123456.78). Prices, orders, imports and exports all
  resolved, so the market reads are sound.
- Sender, receiver and goods printed empty, with no error: names read
  through `save_scope_as` + `SCOPE.sC(...)` inside the effect came back
  blank. v0.02 reads them straight off the article
  (`THIS.GetTreatyArticle.GetSourceCountry...`), the chain that resolved in
  the probe, and logs the goods key and treaty start date.
- The lane's merchant marine demand resolved, so v0.02 logs it for every
  lane article and the report computes the real route factor against ×1.25.
- Pace: 0.94 minutes per game year at the start (computed from log
  timestamps). AI signing rate: 2 goods transfers in 21 months, about 1.1 a
  year, but with 2 events the 95% interval is 0.14 to 4.13 a year, so
  30 deals could take 7 to 217 game years. Run to the end of the game unless
  the report reaches 30 first; the plan's fallback (a player run with several
  deals) stands if the AI turns out to rarely sign them.

**Results, v0.02 observer game, 1836 to April 1869** (archive
`logs/treaty_obs_archive`; 1869 to 1892 lost when the Claude session
restarted and its archiver tab died; 1892 on is in `treaty_obs_rotated_1300`
and `treaty_obs_archive2`). All figures computed by `treaty_obs_report.py`
and two scratch scripts over 10,004 monthly rows.

| Claim | Evidence | Caveat |
|---|---|---|
| The AI signed 66 goods transfers, about 2 a year | SIGN rows with hist=0, May 1836 to Nov 1868 | 65 of 66 are 10 units, the minimum; receivers' median buy orders 19, so 10 units is about half their demand |
| The price rule reproduces each logged price | receiver side median error 0.011%, 99th pct 0.58% (n=10,078); sender median 0.009%, 99th pct 13% | a few sender rows are off by up to 24%; cause unknown |
| Goods start moving within a week of signing | sender exports up by 0.9 q at the first monthly snapshot: 55 of 55 snapshots taken 5 or more days after signing, 2 of 11 taken 1 to 4 days after | an earlier "median 19 days" read the receiver's imports, which trade-center cutbacks mask, at monthly resolution: wrong, withdrawn |
| The draft is pessimistic on both sides | orders move as the draft assumes (sender buy +1.00 per unit sent, receiver sell +1.00, medians). Mean miss, % of base: receiver price +13 to +23 above prediction, sender −6 to −18 below, horizons 1 to 24 months; split by order type (Shapley, means): the receiver's rising buy orders give +8 to +18 points of its miss, the sender's rising sell orders −3 to −11 of its miss; the rest is deals where q had not started flowing or orders moved for other reasons | medians showed the sender at 0 because most sender deals miss by nothing and a few by a lot; 19 of 66 predicted receiver prices sat on the price floor, 26 of 66 sender prices on the ceiling; tiny markets dominate |
| A predicted profit holds | 69 of 71 checks across the five horizons stayed profitable (17 distinct deals) | a predicted loss turned out profitable in 5 to 12 deals per horizon |
| Treaties stay in `every_scope_treaty` after binding ends | 5,232 of 5,235 rows with left=0 had inscope=1 | matches what Damien sees in the UI |
| ×1.25 overstates the usual sea lane | per lane: 24 of 40 at ×1.00, 11 between 1.01 and 1.25, 5 above 1.25, highest 1.63 | 40 lanes, all sea (a lane exists only when the markets do not touch; touching markets are predicted at zero shipping, `st_markets_adjacent_sgui`); AI routes, likely shorter than a player's |
| Partial, temporary displacement of trade-center imports, maybe | receivers that already imported the good (n=19 to 23): other imports fell by a median 0.4 to 0.6 per unit sent at 3 to 12 months, 0 at 24 months (n=12) | small n, means swing from −1.08 to +0.36; not a finding yet |

What it changes:
- Alert (section 2): unblocked. Iterate `every_scope_treaty`; keep the
  once-per-treaty memory in a variable list on the player's country.
- Opportunity alert (section 4): predicted profits held for small AI deals.
  Still untested at player sizes, where one deal is 50 to 500 units into a
  big market. Next: a player run signing 4 or 5 such deals, logged by the
  same observer.
- Draft route default: the data favours ×1.00 over ×1.25, with the hover
  range kept. Damien's call.
- Draft prices: both ends move less than the rule predicts, always in the
  player's favour. Not tuned until the player-size run says the same.

Run recipe:
1. Claude starts `python tools/log_archiver.py --out <logs>/treaty_obs_archive`
   from the repo root in a Terminal panel tab; the app must stay open.
2. Launcher: a playset with only "ZZ Smart Treaties observer". No
   `-debug_mode`: `debug_log` writes without it.
3. New game 1836, started directly in observe mode, speed 5.
4. After one game year: Claude reads the log (`treaty_obs_report.py` on the
   archive) and confirms every field resolves. A broken field costs a restart
   now instead of a 20-year run.
5. Leave it running, quit when the report reaches 30 deals or the game
   ends, Ctrl+C the archiver, run the report.

**Spain 1836 campaign (v0.03, from 2026-11-10).** Damien plays normally with
Smart Treaties and the observer both loaded. Monthly lines cover only his own
transfers; signings and endings cover everyone; `adj=` flags touching markets,
and the report counts any lane between touching markets as a contradiction of
the predictor's zero-shipping rule. The archiver runs as a hidden background
process into `logs/treaty_obs_spain`, so it survives the Claude app and
session restarts, but not a reboot. Useful once he has signed about 5 deals of
50 units or more, at least 2 by sea and 2 overland, each with 6 months of data.

## 2. "Goods transfer losing money" alert (built 2026-11-13, not yet run in game)

Revived after the long run: the Great Qing hardwood deal lost money every
month from September 1842 to April 1851 and Damien did not notice, although
the outliner shows each treaty's net. Rules (Damien, chosen on that run's
data): per goods article the player sends; fires after 6 monthly checks in a
row with an estimated weekly net below -50; then quiet until 6 checks in a
row at or above -50 (once per losing streak); a treaty coming into force,
renegotiation included, starts its articles afresh. On the 1836-1851 data:
Qing hardwood Nov 1836 and Feb 1843, France hardwood Feb 1846 and Feb 1848,
nothing for silk (lost 13-24 a week at worst) or tobacco. "Once per treaty"
was rejected: it would have warned in 1836 and stayed silent through
1842-1851. Files: common/script_values/st_alert_values.txt,
common/scripted_effects/st_alert_effects.txt, common/on_actions/st_alert_on_actions.txt,
common/messages/st_alert_messages.txt; state in variable lists on the
player (check_st_tna_lists_created). Shipping is the draft's estimate
(script cannot read a lane), which runs low on long routes.

Accepted when: an article losing more than 50 a week for 6 monthly checks
posts one toast naming the good, partner and weekly loss (ST_TNA|FIRE), and
nothing more until it recovers for 6 checks (ST_TNA|REARM); no toast for an
article losing less, for goods the player receives, or twice in one streak;
ST_TNA|RESET shows whether a renegotiation fires on_treaty_entered_into_force.

### Earlier spec (dropped 2026-11-10, kept for reference)

The outliner already shows each treaty's net. Kept for reference:

A monthly check on `on_monthly_pulse_country`, player only. Mods get decade,
five-year, half-yearly, yearly and monthly pulses, no weekly one, so "N weeks"
means consecutive monthly checks. Monthly suits this anyway.

- Judged on goods only, using the treasury line's shipping estimate. Money
  articles are ignored, or Zhytomyr (-£5.9K, a £6K gift) would always fire.
- Only goods the player sends, because only those touch the treasury.
- Significantly negative: losing at least £100 a week (Damien, 2026-11-05).
  Linz at £23.9 stays silent, by design.
- Fires on the 3rd consecutive negative check, 9 to 13 weeks. Any good check
  resets the count, so a one-week dip cannot fire it.
- Fires even while the treaty is bound: renegotiating can reduce the quantity.
- Once per treaty, never again.
- A toast, muteable through its own "(ST) ..." group in Message Settings.
  Body: the treaty, net per week, binding time left (`remaining_binding_period`).
- All 11 languages.

Accepted when: a goods treaty that loses over the threshold for 3 monthly
checks posts one toast. Nothing appears for: a treaty that recovers before the
3rd check, a second time on the same treaty, AI-only treaties, a treaty where
only the money article loses, goods the player receives. Verified by tagged
`debug_log` lines through scan_logs, then one look at the toast.

`check_no_cheat_verbs` must still pass: this adds notifications and bookkeeping
variables, and nothing that changes the game.

## 3. Trade recommender (decided 2026-11-10, replaces the best partner panel)

Up to 5 rows at the top of the market panel's Trade tab (1.15): "Send 40 Wine
to Austria: about £180 a week". Deal view, not country view: the goods picker
already answers "what should I send to this country".

- **Goods:** only goods the player's market can spare: sell orders above buy
  orders by at least 10 (vanilla's minimum transfer). A good shows only if its
  best deal is meaningful (below).
- **Quantity:** the draft's own best-profit quantity, capped by what the AI
  accepts (its shortage + 10) and by the player's surplus. That computation
  lives in GUI formulas today, and the GUI cannot hand numbers to script
  (engine-notes.md § The GUI cannot pass a number to a script value), so it is
  ported to script values. A Python check compares the port with the GUI
  method on random market shapes before it ships; target within 2%.
- **Meaningful:** the list has no bar since 2026-11-13 (Damien): the top 5
  profitable deals show, however small. In his Spain game, tobacco to France
  at £486 a week mattered against a net income of −£2.3K. The alert's bar
  (start 5% of weekly income, `income`) is still an assumption.
- **Empty states:** before the first scan (mod just added to a save) the
  block says it computes when the month turns and points at the refresh
  button; after a scan with no profitable deal it says so.
- **Game start and load (Damien, 2026-11-13):** a scan from
  `on_game_started_after_lobby` ran before the markets were filled in
  (pairs=0, 8 s after the lobby; a refresh 33 s later on the same day found
  378) and was dropped. Hooks on zero-size widgets in the market block (a
  `trigger_on_create` state, then a `_show` state) never fired either (no
  INIT lines, runs 3 and 4). Now a forced scan each time the Trade tab
  opens (Damien's call), two ways, each tagged: `OPEN_TAB`, an extra
  onclick on vanilla's Trade tab button, and `OPEN_SHOW`, a `_show` state
  on vanilla's Trade section, whose visibility flips with the tab. No
  on_action fires on load; the save holds the last scan.
- **Scan dates (Damien, run 4):** the "monthly" pulse runs every 30 days
  from the country's own offset (Spain 1836: 23 Jan, 22 Feb, 24 Mar ... 20
  Oct, 19 Nov), so updates drift through the month. Expected; the tab-open
  scan makes it matter less.
- **Base acceptance (Damien, 2026-11-13):** after the partner's name, in
  brackets: "Great Britain (-33)". Vanilla's `static_treaty_acceptance`
  evaluated from the partner's side (`st_rec_acc`), the player passed as
  `scope:other_country` through `global_var:st_rec_player`. Confirmed run 3:
  the value matches the draft's (Great Britain -31 to -33 in 1836); run 4:
  the hover shows vanilla's lines. The filter first read a value each AI
  country stored on its own monthly pulse, which lagged (Great Britain at
  -41 still listed on 23 January). Now the scan computes each market
  owner's acceptance itself at its start: `st_rec_acc_scan`, vanilla's
  formula copied at generation time with its `root` references read from
  `scope:st_rec_eval` (the partner). Per good, the best partner at or above
  -10 is kept, so a good loses its partner and not its row: coffee went
  from Great Britain (847/week) to Portugal or Russia (about 250).
- **Churn (Damien's question, run 3):** the January to February change was
  mostly that filter taking effect (Great Britain and France stored their
  values on 30 and 26 January, after the 23 January scan). February to
  April the top 4 held: sugar to Austria, tobacco and coffee to Russia, wine
  to Brazil. Candidate pairs fell 378 to 248 (-34%) as the 1836 economy
  settled.
- **Section (Damien, 2026-11-13):** a collapsible section header (vanilla's
  `section_header_button`, as Build All's), open by default, so the goods
  list below can get the room back. The refresh button sits on the header.
- **Rows (Damien, 2026-11-13):** a treaty button, then "Send 55 [icon]
  Coffee to [flag] Great Britain (-33): ~£866/week", on one line. `GetName`
  draws the flag and the clickable name (engine-notes § `GetName`). The
  button opens a new treaty draft with the partner
  (`OpenTreatyDraftPanelForNewDraft`, vanilla's "Draft a treaty" entry,
  same icon).
- **Pre-selecting the good in the draft, last try (Damien, 2026-11-13):**
  the treaty button leaves the good in the GUI variable `st_rec_good`; the
  goods picker (a) selects that good's card at the best quantity when it is
  created in a Goods Transfer the player sends (`ST_REC|PICK|go` logs it),
  and (b) outlines the card with vanilla's selection frame while the key is
  set. The first try also matched the partner by `GetIDString`; run 3
  probes showed the right card, source and target, and that check never
  passing, so it is gone. If neither works, drop it for good.
- **Acceptance:** vanilla's `static_treaty_acceptance` (root = partner,
  `scope:other_country` = player; its treaty-options lookups are guarded with
  `exists`/`?=`) plus the goods article's own score at that quantity
  (`13_goods_transfer.txt`, `inherent_accept_score`), total at least 0.
  Relations alone are the wrong filter: the Netherlands at Poor relations and
  Cautious attitude scored −7 base, and 109 furniture added +7 (Damien's
  screenshots, 2026-11-10). Computed only for the most profitable candidates,
  in order, until 5 pass, because it is the expensive part.
- **Partner:** one country per good. Within a market, the member with the
  highest acceptance (usually the owner); prices are per market.
- **Nice to have:** the same good again if the surplus left after the first
  deal still supports a meaningful one, assuming deals are made in order.
- **When:** once a month for the player (`on_monthly_pulse_country`), stored in
  variables on the player's country, plus a refresh button. The GUI reads
  stored values only, so nothing runs per frame (engine-notes.md § GUI
  expressions run every frame).
- **Cost:** pre-filter each (good, market) pair on its first-unit margin
  (partner price above ours plus shipping) before the full search, and
  measure the monthly tick with the tick probe before shipping.

**Built 2026-11-10, not yet run in game.** `tools/gen_st_recommender.py`
writes the script (values, trigger, scan effect with one block per good, the
monthly hook, the refresh button's scripted GUI) and forks vanilla's
`market_panel` type into `gui/00_smart_trade_market.gui` with the block under
the trade capacity line (since 1.15.1, which replaced the country's trade
capacity line with a market-wide box: at the end of the Trade tab's capacity
section, under that box or the selected hub's). Changes from the spec above, all Damien's
(2026-11-10): acceptance is not computed (partners only need to be at peace
with the player); everything vanilla's goods_transfer article requires is
checked (reachable market, ports or touching markets, supply network, customs
union, import and export caps, no duplicate good between the two). The port
of the Best search matches brute force: 0 of 1,426 profitable random market
shapes more than 2% short, worst 0.99% (`--selftest`). It stops at the AI's
shortage + 10, where the Best button can climb further by reading the draft's
live acceptance, which script cannot see. Each scan writes
`ST_REC|SCAN|...` (pairs checked, pairs searched, threshold) and one
`ST_REC|ROW|...` per suggestion, for checking against the draft. Not built
yet: the opportunity alert, the same good twice. Before release: the Workshop
description's "stores nothing in your save" stops being true (the player's
country keeps the 5 suggestions in variables). Removing the mod mid-campaign
leaves those variables unread in the save, the same as Smart Notifications'
country variables, whose description already says "safe to add or remove
mid-campaign". Suggested wording: "Save-safe. Add or remove it mid-campaign;
it keeps its suggestions in your save, and they sit there unused if you
remove it."

Next iterations (Damien, 2026-11-10), after the first in-game check:
- A smarter "enough surplus" than 10 units, which is small for most goods.
- Allow a partner already receiving that good when adding volume is the
  best option (today any existing transfer of the good between the two
  excludes the pair).

Accepted when: in the Spain campaign the tab shows at most 5 rows; for each,
the draft with that partner and quantity shows the same weekly profit within
2% and a thumbs-up; no row for a good with under 10 surplus, a loss, or a
profit under the threshold; the monthly tick stays within noise of the mod
without it. Checked by a tagged `debug_log` per row (script's figures) against
one look at the draft for the top row.

**Trade centers against treaties (Damien's question, open).** He prefers £100
to the government over £100 to trade centers. What the game says: trade revenue
goes to the trade center, set by the price difference and volume, and tariffs
reduce it. So a trade center pays the treasury through tariffs and tax on what
it earns; a goods transfer pays the treasury the whole margin. A transfer also
costs treasury cash up front, needs no trade capacity, and binds for years,
while a trade center adapts by itself. Austria's sell orders staying at 10
after Linz hints that a transfer may displace trade-center imports: then part
of a treaty's profit is moved from your own trade centers to the treasury, and
is not new money. Measurement answers that. The Trade tab keeps vanilla's
import and export rows below the suggestions, so existing trade stays visible.

**Run 5 (2026-11-13):** rows filled on opening the Trade tab (OPEN_TAB
scanned, OPEN_SHOW skipped the same day: both hooks work, the guard holds),
the treaty button's draft opened with the good selected (PICK|go x3), 60 fps
capped throughout. Then (Damien): partner cutoff raised from -10 to 0, since
no partner under it could be brought to accept; and a good's own panel, on
the player's market tab, lists that good's 3 best partners, same rows and
section UX. That list is computed for one good when its panel shows it
(`st_rec_scan_one`, about 1/50 of a full scan; partners' acceptance is
computed at most once a day, `st_rec_acc_fresh`), keyed on good and day in
the GUI variable `st_rec_one_key`, so switching goods or a new day rescans.
Hooks, run 6: neither fired on opening (only a refresh click scanned); the
`trigger_on_create` state fired once at startup, with no good, and logged
"Promote 'AddScope' returned nullptr". The same lesson as the market panel:
panels are built at startup, so only a real visibility change fires. Now
three tagged routes: ONE_OPEN, a `_show` state in the window's
`animation_state_block` (vanilla fills that slot the same way in
building_browser_panel.gui, a second `_show` with an on_start next to the
window's own); ONE_SWITCH, the "Looking for partners" line's `_show`, for a
switch of good in the open panel; ONE_REFRESH, the button. Not yet run.

**Long run, 1836 to August 1851 (2026-11-13), from the observer archive:**
- Acceptance filter: Great Britain was listed only on 1 January 1836 and
  then not until 1839 (the 23 January 1836 scan already left it out), and
  Damien sees the row figures match the treaty draft. A first reading that
  the scan-time copy computes too high compared France's figure with run 3,
  a different campaign: wrong, withdrawn. Open: why the 1 January scan of a
  new game let Great Britain through (first day only).
- Goods panel scans on opening: 3 of 3 (ONE_OPEN). Trade tab: OPEN_TAB.
- Suggestions churn about 1 row in 5 per monthly scan; steadiest picks tea
  to Russia, wine to Brazil, tobacco and sugar to France.
- The suggested Great Qing hardwood deal ("44, about 535 a week", April
  1836, signed 5 May): recomputed from the observer's monthly rows as the
  outliner computes net, 134 of 184 monthly snapshots negative; positive on
  balance to August 1842 (about +9K), then negative every month from
  September 1842 (Qing's price fell from the 70.00 ceiling to 42.70) until
  Damien cancelled it after April 1851: 109 months, median -477 a week,
  about -264K (monthly snapshots x 52/12 weeks, an estimate). He did not
  notice it was negative although the outliner shows each treaty's net.
  The route cost on this lane ran 1.56x the draft's per-unit estimate
  (draft assumes 1.25).
- So the dropped "treaty turned negative" alert (section 2) is back on the
  table, with one change: as specced (once per treaty) it would have fired
  in August 1837 and stayed silent through the 9-year loss. It needs to
  re-arm after a recovery, or be a persistent alert while the loss lasts.

**Save safety, confirmed 2026-11-13 (Damien):** a save made with the mod loads
and plays with the mod disabled. The Workshop line changes anyway, since the
mod now keeps values in the save (WORKSHOP_UPDATE_DRAFT.md, edit 5).

**Performance review before release (2026-11-13, Damien: fans run a lot with
the game on).** Read from the code, nothing measured yet:
- Script, per in-game month: every monthly hook in the three published mods
  checks `is_player` first, so about 200 AI countries cost one check each.
  The recommender scans once a month for the player, plus on opening the
  Trade tab; a same-day guard (`st_rec_fresh`, 1 day) stops a second scan
  from the second hook or a reopened tab, and the refresh button always
  scans. The observer (dev only) walks the world's treaties once a month.
  Earlier tick-probe result: no measurable cost from the published mods
  (2026-10-07, see smart-trade-investigation.md).
- Per frame (every binding of a visible widget reruns each frame, paused or
  not): the outliner's treaty rows, always on screen, evaluate the
  per-treaty script values (`st_treaty_margin`, `st_treaty_money`,
  `st_treaty_has_lane`) about 15 times per row per frame, mostly because six
  layout branches repeat the same "has a figure" test. Each value walks
  the treaty's few articles. Estimate, from the picker's fitted 1 to 6 us
  per step: about 1 to 4 ms per frame with 3 to 10 treaties. Fixable by
  nesting the branches so the test runs once per row; not done before
  measuring, since that layout took several runs to get right.
- Fixed: the suggestion rows showed acceptance through a live ScriptValue
  (vanilla's formula, 5 rows, every frame while the Trade tab is open); they
  now read the value the scan stores on each partner.
- Fine: the draft panel's large bindings are almost all onclick and
  creation-state code (run once), and its per-frame text runs only while a
  Goods Transfer draft is open.

Measurement run before release: Steam's FPS counter (no debug mode), paused,
same save, each screen with and without the three mods: the map with the
outliner's treaties open and closed, the market panel's Trade tab. Then the
tick probe at speed 5 for about 15 in-game months, with and without mods.

## 4. Opportunity alert

From the recommender's monthly result, no extra search. A toast in its own
"(ST) ..." Message Settings group, all 11 languages:
- at most once a year (Damien: once a month is spam; 6 to 12 months);
- only when the top suggestion clears the alert threshold (start 5% of weekly
  income);
- never twice for the same good and partner.

The AI run supports it with a caveat: predicted profits held in 69 of 71
checks, but on 10-unit deals. The Spain run checks player-sized deals.

Accepted when: over 10 game years of the Spain campaign it fires at most 10
times, never twice for one good and partner, and every alert matches a row
the recommender showed that month.

## Rejected (Damien, 2026-11-05)

- Prediction on signed treaties: keeps the issue top of mind for little value.
- A treaty ledger: the outliner already shows each net.
- `[1.15]` in the title.
- Changing the draft hover's wording.
- A wider `1.*` version string.

## Not builds

- **Chinese description:** Steam's edit page has a language selector (Damien's
  screenshot, Build All). Paste a Simplified Chinese title and description
  there; English stays as it is. Steam's API docs confirm per-language text
  but not which language a viewer gets. Check after pasting: the page with
  `?l=schinese`, and the normal page still English. Conversion is 45 to 52%
  and the sheet cannot split by language, so compare 7 days before and after
  and expect a noisy read.
- **Reddit:** shelved. Revisit when measurement has a finding worth posting.
- **Launch hypothesis (Damien):** first-week downloads depend on placement in
  the Workshop's "Items in the past week" carousel. Check on the next launch.
- **Ratings:** Damien is open to one line in the description asking for a
  rating. Whether ratings feed the ranking is unverified.
- **Rank tracking:** dropped (Damien, 2026-11-05). The Most Popular list is on
  steamcommunity.com, which cloud routines cannot reach, and he wants this
  flow in the cloud. `api.steampowered.com` does work there, so a Steam Web API
  key might get a ranking through `IPublishedFileService/QueryFiles`, but
  nobody has checked that it matches the Workshop home page. The
  `/filedetails/stats/` page is not public either.
