# Reddit feature post: Smart Treaties 0.13 (draft, 2026-11-16)

Damien posts it. Image post with two pictures:
`smart_trade/store_assets/screenshots/06-top-trades.png` (the Trade tab's 5 suggestions)
and `07-good-best-partners.png` (a good's top 3 partners).

## Title

Pick one.

1. Victoria 3 should tell you which goods transfers make money, so my mod now lists your 5 best deals (and who will accept them)
2. Smart Treaties 0.13: your Trade tab now lists the 5 most profitable goods transfers you could propose

Option 1 follows the Build All launch title ("There should be a build all
button...", 500 upvotes, 50k views per the sheet): a player's complaint first,
the mod second.

## Body

In my Spain game, the 5 deals it found add up to about £2,100 a week.

Your market's Trade tab now lists the 5 most profitable goods transfers you could propose: what to send, to whom, how much, and the weekly profit. Each row shows the partner's base acceptance. Countries below 0 are left out (I never got one of them to accept). The treaty button opens a draft with that country, with the good already picked when you add a Goods Transfer. Each good's own panel also lists its 3 best partners.

New warning too: if a goods transfer you send loses more than £100 a week for 6 months in a row, you get a toast. Once per losing streak, in its own Message Settings group if you don't want it.

Still display only, nothing touches your economy or the AI. Achievement compatible.

Workshop: https://steamcommunity.com/sharedfiles/filedetails/?id=3814823352

If it finds you a good deal, a thumbs up on the Workshop page helps a lot !

## Rule 5 comment

Screenshot is my Spain game. The five suggestions add up to about £2,100 a week, at first-week prices.

How it works:

- Suggestions use the same price rule as the goods picker, at the most profitable quantity your partner fully accepts. Recomputed every month, when you open the tab, and on refresh.
- A draft has no shipping route yet (the game picks one when you sign), so the mod guesses from the capitals: same continent means a short lane, otherwise a long one. On Spain's real lanes, Asia cost 1.52 to 1.62 times a European lane. My first version used one flat rate and missed Japanese small arms losing £166 to £260 a week. Oops.
- The £100 / 6 months bar comes from a 1836 to 1851 test game. At £0 it warned me about silk losing £13 a week, too noisy. At £100 / 6 months it fired 3 times in 15 years: Qing hardwood twice, French hardwood once.

Single-player only. It replaces the market and goods panels, so a mod touching those will clash.

What should it suggest next ?

## Before posting

- Rule 5 wording on r/victoria3 is not checked (Reddit is blocked from the tools). Check the sidebar for whether image posts need an explanatory comment and by when.
- Self-promo limit: the sheet logs no Reddit post since the Smart Treaties launch on 10/06, so the weekly slot looks free. Check your own post history in case one is not logged.
- After posting: log it in the sheet's Comment column for Smart Treaties, and reply for the first hour.
