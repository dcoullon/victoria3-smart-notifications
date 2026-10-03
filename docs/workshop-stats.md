# Workshop stats log

**The daily series lives in Damien's sheet "Mod subscribers daily"**
(https://docs.google.com/spreadsheets/d/161htiOAsVwNh18_1O7H3oWu1GGeOw2PPTWF0HiThJVc),
one tab per mod. This file keeps occasional readings and how to take them.

The item page shows three cumulative numbers and Steam keeps **no history**
(the `/filedetails/stats/` subpath 404s; the daily view is Steamworks
partner-side). A reading not written down is lost permanently.

**The public Steam Web API gives more than the page**, with no key:
`lifetime_subscriptions` and `lifetime_favorited` alongside current counts, so
churn (lifetime minus current) is measurable. `views` appears to be the
page's "Unique Visitors" (it continues the sheet's page readings smoothly), but
nobody has yet compared the two on the same day; do that once before relying on it.

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

Item created 2026-09-10 for the first public release. An earlier closed-beta
listing (ID `3798687130`, v0.35) was deleted and carried its own counts; they
are not continuous with these.
