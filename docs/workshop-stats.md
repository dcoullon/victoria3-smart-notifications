# Workshop stats log

**The daily series lives in Damien's sheet "Mod subscribers daily"**
(https://docs.google.com/spreadsheets/d/161htiOAsVwNh18_1O7H3oWu1GGeOw2PPTWF0HiThJVc),
one tab per mod. This file keeps occasional readings and how to take them.

The item page shows three cumulative numbers and Steam keeps **no history**
(the `/filedetails/stats/` subpath 404s; the daily view is Steamworks
partner-side). A reading not written down is lost permanently.

**The public Steam Web API gives more than the page**, with no key:
`lifetime_subscriptions` and `lifetime_favorited` alongside current counts, so
churn (lifetime minus current) is measurable. `views` is the stats page's
"Total Unique" visitors: compared on the same day (2026-11-25) for the QoL
Essentials collection, both read 111.

QoL Essentials collection (3844524545), created 2026-11-22 5:24 PM PT: tab "QoL
collection" (sheetId 384452454), stats only (no rank, ratings or stars), added
to the noon routine as its STEP 6b on 2026-11-25; first scheduled reading
2026-11-26. 11/22 to 11/24 visitors per day are in that tab's Comment column,
read off the author's stats-page chart.

```bash
curl -s -X POST "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/" \
  -d itemcount=2 -d "publishedfileids[0]=3799284646" -d "publishedfileids[1]=3803950977"
```

Smart Notifications (3799284646):

| Date | Unique visitors | Subscribers | Lifetime subs | Favorites | Live version | Note |
|---|---|---|---|---|---|---|
| 2026-09-11 | 107 | 20 | | 10 | v0.39 | ~1 day after public launch; Reddit post at 50 upvotes / 7.2k views |
| 2026-09-15 | 664 | 201 | | 34 | v0.40 | first reading after the 0.40 upload (2026-09-14) |
| 2026-10-03 | 1639 | 415 | 461 | 60 | v0.40 | API reading, 16:38 UTC |

Build All (3803950977):

| Date | Unique visitors | Subscribers | Lifetime subs | Favorites | Live version | Note |
|---|---|---|---|---|---|---|
| 2026-10-03 | 1199 | 431 | 459 | 29 | 0.04 | API reading, 16:38 UTC; earlier days in the sheet |

The 2026-09-12..14 Smart Notifications readings exist in the sheet.

Reorder Research Queue (3841721873), published 2026-11-18 (17 Nov 5:49pm PT):
tab "Reorder research" (sheetId 2143389703), added to the noon routine
"Daily Steam Workshop stats" (trig_01HmsZwyutmcLyjqzutshKwz) on 2026-11-18;
its first scheduled reading is 2026-11-18 noon PT.

From 2026-11-18 the same routine also writes each tab's total ratings (column L,
up plus down) and Steam's star count (column M, "none" below 25 ratings). Both come
from the `total_votes` and `star_rating` fields embedded in the Workshop search
page (`browsesort=textsearch`, searching the mod's title). The up/down split is
not public without a Steam Web API key. Steam's star score appears to be
(up + 50) / (up + down + 100), 4 stars from 0.60 and 5 from 0.80: on 2026-11-18,
617 Victoria 3 items gave no counter-example (stars hidden at 24 ratings or fewer
and shown from 25, no 4-star item under 28 ratings, no 5-star item under 155).

## Dashboard and the 2026-11-25 additions

On 2026-11-25 the sheet gained three tabs, all formulas over the mod tabs:
"Dashboard" (totals, per-mod table, five charts: subscribers, new subscribers
per day, visitors per day, trailing-7-day net subs per visitor, 3-month rank),
"Events" (dated launches, Reddit posts, updates, store-page changes; the
dashboard lists the 12 latest) and "Daily series" (the chart inputs, cut at the
last day with data). Named ranges `LatestDate`, `DaysOfData` and `RankStart`
live in `'Daily series'!AA1:AA3`. Every tab must keep 9/11 on its first data
row: the formulas count rows from that date.

The same day the routine started writing three more columns on each mod tab:
N "Lifetime subscribers" (`lifetime_subscriptions`; unsubscribes = N minus D,
shown on the dashboard as a share of N), O "Steam last updated (Pacific)"
(`time_updated`; the routine also appends an "Update" row to Events when it
changes) and P "Most Popular rank (1 week)" (`days=7`). The 1-week list ranks
very differently from the 3-month one (on 2026-11-25: Reorder Research 5 and
Smart Treaties 145 by week, 87 and 3 by 3 months), so it appears to favour
recently published items; read it as launch visibility, not traffic.

Item created 2026-09-10 for the first public release. An earlier closed-beta
listing (ID `3798687130`, v0.35) was deleted and carried its own counts; they
are not continuous with these.
