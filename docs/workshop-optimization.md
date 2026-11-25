# Workshop optimization: what moves downloads

Running log of what we have learned about getting Steam Workshop
subscribers for a mod, from four Victoria 3 mods. Goal: enough checked
material to publish an article on optimizing a mod for Workshop downloads.

**Rules for adding a learning.** Every entry names its source (sheet tab and
row, file, URL, with the date read) and says how strong it is:

- **Measured**: read directly from data we hold.
- **Inferred**: a pattern in the data with no direct test.
- **Hypothesis**: a plausible idea not yet tested. Say what would test it.

A learning that a later reading contradicts gets corrected here, not deleted:
the wrong turn is useful material for the article.

Main data source: Damien's sheet "Mod subscribers daily"
(https://docs.google.com/spreadsheets/d/161htiOAsVwNh18_1O7H3oWu1GGeOw2PPTWF0HiThJVc),
one tab per mod, one row per day at noon Pacific since 2026-09-11, filled by the
routine described in [workshop-stats.md](workshop-stats.md). "Sheet, Smart
treaties 11/24" below means that tab, the row dated 11/24.

## What Steam lets you measure

- **Measured.** The item page shows three cumulative numbers and Steam keeps no
  public history; a reading not written down is lost. Source:
  [workshop-stats.md](workshop-stats.md) (the `/filedetails/stats/` subpath 404s).
- **Measured.** The key-free Web API (`ISteamRemoteStorage/GetPublishedFileDetails`)
  also returns `lifetime_subscriptions`, `lifetime_favorited` and `time_updated`,
  so churn (lifetime minus current subscribers) is measurable. Smart Treaties
  on 2026-11-25: 4,571 current, 4,833 lifetime. Source: API call 2026-11-25.
- **Inferred.** The API's `views` is the page's "Unique visitors": it continues
  the sheet's hand-read page values smoothly. Not yet compared on the same day.
  Source: [workshop-stats.md](workshop-stats.md).
- **Measured.** Steam gives no traffic source and no visitor language. Every
  channel effect below is read from day-level timing, so anything that happens
  on the same day is confounded.

## Where visitors come from

- **Measured. The "Most Popular" browse view (past three months) is the main
  channel.** Smart Treaties reached its first screen on 2026-10-30 and daily
  visitors went from 35 (10/29) to 100 (10/30) and 138 (10/31). Source: sheet,
  Smart treaties 10/29 to 10/31, column G, and the 10/30 comment "enters most
  popular first screen". [marketing-plan.md](marketing-plan.md) gives "35 to
  106"; the sheet reads 100 for 10/30 as of 2026-11-25.
- **Measured. Rank and daily visitors on the same day**, 2026-11-24: Smart
  Treaties rank 4, 208 visitors; Build All rank 32, 24; Smart Notifications rank
  85, 11. Source: sheet, each tab's 11/24 row, columns G and K.
- **Measured. New items get a separate boost.** Reorder Research Queue had 147
  visitors on 11/24 while ranked 132 in Most Popular, more than Build All at
  rank 32. It was in the hub's "Items / In the past week" carousel, which is the
  top 20 of `browsesort=trend&days=7` and favours items with votes relative to
  their own history. Source: sheet, Reorder research 11/19 (comment "enters the
  top weekly (rank 18)") and 11/24; carousel check 2026-11-18 in memory
  `v3-workshop-growth-facts`.
- **Measured. A Reddit launch post brings about 100 to 130 visitors on the day.**
  Smart Treaties 10/6 to 10/7: 130; Build All 9/19: 104. Its larger value is the
  subscribers and ratings that then lift the ranking. Source: sheet, column G of
  those rows; [marketing-plan.md](marketing-plan.md).
- **Measured. A post that goes viral is a different order of size.** Smart
  Notifications' "show population" post (9/14, about 1,500 upvotes and 56k views
  by 9/15) brought 342 visitors that day and 313 two days later. Source: sheet,
  Smart notifs 9/14 and 9/16, comment on 9/14.
- **Measured.** r/victoria3 allows one self-promotional submission per week.
  Source: subreddit sidebar seen through a mirror (rule number unconfirmed),
  memory `v3-workshop-growth-facts`.

## What turns a visitor into a subscriber

- **Measured. Lifetime conversion differs widely between mods**, 2026-11-24:
  Smart Treaties 54%, Reorder Research Queue 41%, Build All 40%, Smart
  Notifications 27%. Source: sheet, column F of each tab's 11/24 row.
- **Hypothesis.** The gap tracks how concrete the promise is in the title and
  first line (a money figure or a click saved, versus "smart" filtering).
  Untested; a title or first-line change on Smart Notifications with the
  others as controls would test it.
- **Measured. Stars appear only from 25 total ratings.** Across the top 180
  past-week Victoria 3 items on 2026-11-18, every item with 24 or fewer ratings
  showed no stars and every item with 25 or more did. Source: memory
  `v3-workshop-growth-facts`; [workshop-stats.md](workshop-stats.md).
- **Inferred. The star score looks like (up + 50) / (up + down + 100)**, with 4
  stars from 0.60 and 5 from 0.80. A positive-only mod therefore needs 150 up
  votes for 5 stars. No counter-example among 617 Victoria 3 items on
  2026-11-18; the formula comes from an unofficial Steam guide. Source:
  [workshop-stats.md](workshop-stats.md), [marketing-plan.md](marketing-plan.md).
- **Measured. The browse grid cuts titles above about 438 px wide at 1920
  pixels.** Smart Treaties' title needs 457 px and is cut. Damien kept it
  (2026-11-16). Source: memory `v3-workshop-growth-facts`.

## Translated Workshop pages

Steam lets an item carry a title and description per language; a viewer sees
the one matching their Steam client language (`?l=schinese` serves the Chinese
one). Source: live item pages, checked 2026-11-16 and 2026-11-25.

- **Measured. No effect of the Chinese page on Smart Treaties could be
  separated from noise.** Chinese went live around 2026-11-12. Over 11/12 to
  11/15, Smart Treaties' conversion rose 3.2 to 9.4 points depending on the
  window, but it was already rising before 11/12 (the same comparison cut at
  11/6 to 11/11 gives +3.1 to +8.7 points). Against Build All (never
  translated), the gap ranges from 3.3 to 10.9 points, and the same comparison
  gave gaps at least as large in 4 of 23 windows with no translation change. Visitors rose on all mods those days,
  so no traffic effect either. Source: tab "Chinese test" in the proposal copy
  https://docs.google.com/spreadsheets/d/1m_X8qzF8RKoiW4ZCvfc3aBL3SWQXZAvYdy4lxsUcmn0,
  built 2026-11-25 from the sheet's columns B, G, H.
- **Measured.** If the whole 9.4-point rise came from Chinese-speaking
  visitors making up 22% of traffic, they would have had to convert at about
  93%, against about 50% before. So most of the rise was something else.
  Source: same tab, computed 2026-11-25.
- **Measured.** 0 of 46 Workshop comments across the four mods contain
  Chinese, Japanese, Korean or Cyrillic characters. Those players may comment
  elsewhere.
  Source: Steam comment threads, read 2026-11-25.
- **Measured. Steam-wide language shares, October 2026:** English 39.0%,
  Simplified Chinese 22.0%, Russian 10.1%, Spanish (Spain) 4.8%, Portuguese
  (Brazil) 4.5%, German 2.9%, Japanese 2.5%, French 2.4%. These cover all Steam
  users, not Victoria 3 players, and swing a lot month to month (Simplified
  Chinese moved 9.4 points from September). Source: Steam Hardware & Software
  Survey, read 2026-11-25. No Victoria 3 split was available: the reviews API
  redirected, and the review histogram returned the same 48,997 total for every
  language.
- **Hypothesis, test running.** A Russian page on Smart Treaties alone, with
  the other three mods as controls. Detecting a 4-day effect smaller than about
  10 points is unlikely, so read it over two weeks with the same placebo check.
  See "Open tests".

## Open tests

| Test | Live from | Controls | How to read it | Status |
|---|---|---|---|---|
| Russian title and description on Smart Treaties | paste date, logged in the sheet's Comment column | Build All, Smart Notifications, Reorder Research Queue | "Chinese test" tab method: 7 and 14 days before vs after, plus the placebo rows | description ready in `smart_trade/STEAM_WORKSHOP_DESCRIPTION.russian.bbcode`, not pasted |
| Cross-links between the mods ("My other mods") | 2026-11-16 to 11-20 | none clean (all four changed together) | not separable from the 11/16 Reddit post | logged only |
