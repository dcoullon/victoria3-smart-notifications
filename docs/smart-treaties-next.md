# Smart Treaties: next build

Locked 2026-11-05. Measurement build written 2026-11-10, not yet run. Goal (Damien): bigger numbers and more
people enjoying the mod. Findings behind this: smart-trade-investigation.md.

## Order

The alert and the finder are the features. Measurement comes first because the
opportunity alert and the predictor's tuning both depend on it, and it needs
one unattended run. The alert does not depend on it and can ship first.

1. Measurement build (dev only)
2. "Treaty turned negative" alert
3. Best partner panel
4. Opportunity alert, only if measurement supports it

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

Run recipe:
1. Claude starts `python tools/log_archiver.py --out <logs>/treaty_obs_archive`
   from the repo root in a Terminal panel tab; the app must stay open.
2. Launcher: a playset with only "ZZ Smart Treaties observer". No
   `-debug_mode`: `debug_log` writes without it.
3. New game 1836, started directly in observe mode, speed 5.
4. After one game year: Claude reads the log (`treaty_obs_report.py` on the
   archive) and confirms every field resolves. A broken field costs a restart
   now instead of a 20-year run.
5. Leave it to about 1856, quit, Ctrl+C the archiver, run the report.

## 2. "Treaty turned negative" alert

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

## 3. Best partner panel

Home: vanilla's per-good world market panel
(`gui/goods_world_market_panel.gui`), which already lists markets for a good
through `GoodsWorldMarketPanel.GetMarkets`, with import and export columns. Add
a column for what a transfer to that market earns and sort on it.

The maths exists: `Market` in `tools/gen_smart_trade_gui.py` takes any goods,
home and partner expression, so a row can reuse the draft formula.

- One figure per market, computed once when the row is created. A live formula
  on every row is the 60 to 6 fps bug again (engine-notes.md § GUI expressions
  run every frame).
- Marks overland partners, since those pay no shipping.
- Both directions: where to send a surplus good, and who could fill a shortage.
- Finding which goods to look at is the second half: a marker on the market
  panel's goods rows for surplus and shortage goods with a paying partner.
  Fifty-odd goods across every market may be too heavy, so size that first.

Risks to check first: a market holds several countries, so the row must name
one treaty partner, and AI acceptance needs a draft, so the panel can show
profit only. 1.15's new treaty lens may overlap: look at it before building.

**Trade centers against treaties (Damien's question, open).** He prefers £100
to the government over £100 to trade centers. What the game says: trade revenue
goes to the trade center, set by the price difference and volume, and tariffs
reduce it. So a trade center pays the treasury through tariffs and tax on what
it earns; a goods transfer pays the treasury the whole margin. A transfer also
costs treasury cash up front, needs no trade capacity, and binds for years,
while a trade center adapts by itself. Austria's sell orders staying at 10
after Linz hints that a transfer may displace trade-center imports: then part
of a treaty's profit is moved from your own trade centers to the treasury, and
is not new money. Measurement answers that. The panel keeps vanilla's import
and export columns beside our figure, so existing trade stays visible.

Accepted when: opening copper's world market panel lists each market with a
figure and overland markets marked, the top row matches a real draft with that
partner within 5%, and the frame rate stays within 5% of the panel without it.

## 4. Opportunity alert

Parked behind measurement. Austria read +£348 at today's prices and lost money
six months later, so a false "big opportunity" costs a player a 5-year binding.
Fires only if the first-week model proves reliable, starting with overland
partners, where shipping is not a guess. Script can do it: `every_market_goods`
and the order values are readable. Same limits: rare, once per good.

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
