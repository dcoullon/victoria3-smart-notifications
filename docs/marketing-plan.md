# Marketing plan, from 2026-11-16

Goal: more Workshop subscribers across the three mods. Checked facts behind
it: memory `v3-workshop-growth-facts`, the marketing sheet "Mod subscribers
daily", and Steam's item stats pages.

## What drives subscribers (measured)

- **Most Popular is the main channel.** Smart Treaties reached its first
  screen on 2026-10-30 and daily visitors went from 35 to 106; at 6th place
  plus 0.12 they reached 237, and 302 over 11/12 to 15.
- **Reddit is a small direct channel.** Smart Treaties' launch post brought
  about 130 visitors that day; Build All's about 104. Its value is the
  subscribers and ratings it feeds into the ranking.
- **Stars come from rating count, not only sentiment.** Steam's star score
  appears to be (up + 50) / (up + down + 100), 4 stars from 0.60, 5 from
  0.80 (an unofficial Steam guide; it matches all three of our mods).
  Build All: 32 up / 1 down, 0.617, 4 stars; Smart Treaties 64 / 0, 0.695.
  Smart Notifications is at 3 stars with 26 up / 2 down (score 0.594): two
  more positive ratings would make it 4 stars. Smart Treaties needs 150
  positive ratings (no negatives) for 5 stars.
- **r/victoria3 allows one self-promotional post per week.**

## Checklist

Due by Friday 2026-11-20 (checked by the scheduled task "marketing-plan-check"):

- [x] Reddit feature post for Smart Treaties 0.13 (suggestions and the losing-deal
      alert), Monday 11/16, US morning (about 6 to 9 AM Pacific). Concrete
      benefit in the title, a Rule 5 comment that adds information, a rating
      ask at the end, an hour of replies. Log it in the sheet's Comment column.
      Posted by Damien, 11/16. Logged in the sheet's 11/16 row (J70, "new
      reddit post"), checked 11/20.
- [x] Paste `smart_trade/STEAM_WORKSHOP_DESCRIPTION.schinese.bbcode` into Steam's
      Simplified Chinese description slot (the English one is already live).
      Done by Damien, 11/16.
- [ ] Smart Notifications to 4 stars: add a one-line rating ask and a link to
      Smart Treaties at the bottom of its description (and of Build All's),
      in English and Chinese.
      11/16: English added to both repo copies (`smart_notifications/` and
      `bulk_construction/STEAM_WORKSHOP_DESCRIPTION.bbcode`, "My other mods"
      plus a thumbs-up line); not yet pasted into Steam. Neither mod has a
      Chinese description on Steam yet (the schinese page shows English).
      11/20 check: English rating ask and Smart Treaties link are live on both
      Steam pages. Smart Notifications still shows 3 stars (28 ratings), Build
      All 4 stars (33 ratings). Goal not met yet.
- [x] Track the Most Popular position of Smart Treaties daily in the sheet.
      Done: the 11/17 noon run wrote column K by itself (Smart Treaties 3,
      Build All 26, Smart Notifications 77).
      Automated from 11/16: the noon routine "Daily Steam Workshop stats"
      (trig_01HmsZwyutmcLyjqzutshKwz) writes each mod's rank in the
      past-three-months view to column K of its tab. Tick once a scheduled
      run has filled column K. Ranks read by hand on 11/16 at 10:53 PT:
      Smart Treaties 4, Build All 27, Smart Notifications 75.
      11/16: routine reworked so stats are written before the rank (a rank
      failure can't cost a day of stats), rank read by curl. WebFetch is out:
      it needs a human approval every run. Test run 2:22 PM: stats fine, rank
      failed because the routine's environment (env_011111111111111111111117)
      proxy refuses steamcommunity.com. K70 filled by hand from a local
      read at 2:20 PM (4 / 27 / 75).
      Fixed 11/16: env_011111111111111111111117 is a built-in environment,
      absent from the user's list and not editable. Routine moved to "Default"
      (env_01DDc2w1p8arUs1cwkkgm1wZ, network access Full). Test run 2:34 PM
      reached both api.steampowered.com and steamcommunity.com and wrote
      ranks 4 / 27 / 75 to K70. Partial routine updates through the API
      replace job_config.ccr whole: send events and session_context with
      any environment change, or the prompt is wiped.
- [ ] Answer at least one existing thread on each topic, with a link to the
      mod (saved searches below).
- [ ] Draft the trade guide (below).

Later:

- [ ] Trade guide, "How goods transfers make or lose money": re-check the
      shipping formula on 1.15 in game first. Publish as a Steam Guide
      (any time) and as a Reddit post no earlier than Monday 11/23.
- [ ] AI deals data post, at least a week after the guide, once the UK
      observer runs are in (`docs/reddit_treaty_charts/`).
- [ ] Optional: one short message each to Generalist Gaming (ModCon Show) and
      Andy's Paradox (mod lists), linking the Reddit post. Unverified reach.
- [ ] Discord: post once in the mod-showcase channel of each Victoria 3 server
      Damien is in (find out which exist and allow it), on the day of each
      Reddit post. Not measurable (no referrer data); keep it to that.
- [ ] PDX ModCon: community-run showcase of Paradox mods (CK3, Imperator,
      Victoria 3), streamed on YouTube, with its own Discord. Last one found:
      June 2025. Find the next edition's application date and apply with all
      three mods.

Dropped: wiki pages (only two converters have one on vic3.paradoxwikis.com),
a shorter Smart Treaties title (Damien, 11/16), Paradox Mods cross-publishing,
a "[1.15]" title prefix.

## Saved searches for existing threads

- Steam: https://steamcommunity.com/app/529340/discussions/search/?q=goods+transfer
- Steam: https://steamcommunity.com/app/529340/discussions/search/?q=notifications
- Steam: https://steamcommunity.com/app/529340/discussions/search/?q=build+all+states
- Reddit: https://www.reddit.com/r/victoria3/search/?q=goods+transfer&restrict_sr=1&sort=new
- Reddit: https://www.reddit.com/r/victoria3/search/?q=notifications&restrict_sr=1&sort=new
- Reddit: https://www.reddit.com/r/victoria3/search/?q=power+plants+every+state&restrict_sr=1&sort=new

The Reddit ones also work as RSS feeds: replace `/search/?` with `/search.rss?`.
