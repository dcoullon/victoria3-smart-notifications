# Smart Treaties + Trade Partners compatibility

Reported 2026-11-27 by Kropotkin on the Smart Treaties Workshop page (they
translate Trade Partners into Spanish and run the "Dense UI" collection).

## The conflict

Trade Partners (Workshop 3733651973, github.com/alcah/victoria3-tradepartners,
13,717 subscribers on its Workshop page 2026-11-27) and Smart Treaties both
redefine vanilla's `market_panel` type, each as a full copy with its own
insertions. The engine keeps the first definition it reads, in filename order
(engine-notes.md, "A partial .gui override works"). `00_smart_trade_market.gui`
sorts before `00_trade_partners_market_panel.gui`, so Smart Treaties should win
and Trade Partners' charts disappear without a log line. Inferred from the
engine note, not yet observed with both mods loaded.

Trade Partners' data refresh for a player comes only from GUI calls to
`trade_partners_scripted_gui` (its monthly on_action runs only in observer
mode), so Smart Treaties cannot copy their block as is: for players without
Trade Partners, that call would target a scripted GUI that does not exist.

## The fix (option 1, shared hook type)

Their side (PR drafted, not opened): the whole Trade tab block, meaning the
wrapper, the 5 second `recalc_trade` state and `trade_partners_charts`, moves
into one type, `trade_partners_world_market_block`, in
`00_trade_partners_charts.gui`. Their panel calls it in one line. The commit is
saved as [trade-partners-compat.patch](trade-partners-compat.patch) (apply on
their master `bc42847` with `git am`; branch name `world-market-block-type`).
The panel-level `_show` state stays in their
panel.

Our side (not built yet):

1. `tools/gen_st_recommender.py` inserts `trade_partners_world_market_block = {}`
   in our `market_panel` copy at the spot Trade Partners uses: inside the
   world market imports/exports section, right after the import pie chart
   block, before that section's closing braces.
2. A new `smart_trade/gui/zz_smart_trade_tp_fallback.gui` declares
   `type trade_partners_world_market_block = widget {}`. It sorts after
   their `00_trade_partners_charts.gui`, so theirs wins when loaded.
3. A static check in `tools/check_references.py` that the hook line is in the
   generated panel and the fallback type exists.

## Acceptance criteria

- Both mods enabled (their PR branch as a local mod): the market panel's Trade
  tab shows Trade Partners' import and export charts and the Smart Treaties
  suggestions box; the charts update within 5 seconds of opening the tab.
- Smart Treaties alone: the Trade tab looks as today and `error.log` has no
  line containing `trade_partners`.
- Trade Partners branch alone: charts show as on the current Workshop version.

## PR text (in Damien's voice, to open from a fork of alcah/victoria3-tradepartners)

Title: Move the trade tab charts into one type so other market panel mods can include them

> Hey,
>
> I'm the author of Smart Treaties (https://steamcommunity.com/sharedfiles/filedetails/?id=3814823352). Kropotkin reported that our 2 mods conflict, and they're right. Both redefine `market_panel`, and the engine keeps the first definition it reads. `00_smart_trade_market.gui` sorts first, so your charts disappear when both mods are enabled.
>
> This PR changes nothing on its own. It moves the chart block (the wrapper, the 5 second refresh and `trade_partners_charts`) into one new type, `trade_partners_world_market_block`, in `00_trade_partners_charts.gui`. Your market panel calls it in one line.
>
> On my side, the Smart Treaties market panel would call `trade_partners_world_market_block = {}` at the same spot, with an empty fallback of the same name in a file that sorts after yours. With Trade Partners loaded, your type wins and the charts show. Without it, the fallback draws nothing.
>
> 2 asks:
>
> 1) Merge this, or the same idea your own way.
> 2) Keep the type name stable (if it changes, Smart Treaties falls back to the empty type and your charts disappear again).
>
> The `_show` refresh at the top of your panel stays as is. When the Smart Treaties panel is the one loaded, the charts still refresh on creation and every 5 seconds through the state inside the block.
>
> Tested: [fill in after the playtest]
>
> Thanks,
> Damien
