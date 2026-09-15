# Reddit post — three proposals

**Drafted 2026-09-15 for a post later in the week (r/victoria3).**

## What we can and cannot claim, as of today

This matters more than the creative direction, so it goes first.

**Safe to publish.** All measured, all reproducible:

| claim | figure |
|---|---|
| Notification keys in the game | **468** |
| Fired by engine code with no script hook (so unmoddable *and* uncountable) | **103** |
| Vanilla tier split, by notification group (106 groups) | 49 feed, 45 toast, 6 popup, 6 none |
| `diplo_play_declare_neutrality_notification` firings, 1908-1918 | **8,410**, and vanilla shows **none** of them |
| Of 44 feed entries observed in busy moments, share that were engine-fired | **20 (45%)** |
| Of those same 44, share that were interest-group churn | **9** |
| Groups a player can usefully re-tier by hand | **13** |

**NOT safe to publish yet.** The "-90% fewer interruptions" figure. See
docs/feed-census-plan.md § "The P column is not a display count": 94% of the
vanilla interrupting count comes from an iterator that records the player being
*involved* in a diplomatic play, not the engine *showing* them anything. A
pure-vanilla observation test settles it. **Until then every proposal below
avoids that number**, and each notes where it would slot in if the test
supports it.

---

## Proposal A — "Here are the settings, you don't need my mod"

**Title:** *I logged every notification Victoria 3 fired across a 10-year
campaign. Here are the 13 Message Settings I'd change, and why.*

**Images**
1. A fully-scrolled feed at a busy moment — the real one from the Portugal
   run, where 9 of 16 entries are interest groups gaining and losing
   "Influential" and "Powerful".
2. A plain table: the 13 groups, current tier -> suggested tier, grouped as
   Quieten / Mute / **Make louder**.

**Body:** open with the feed screenshot and one line — *this is four in-game
days.* Give the 13 settings immediately, no preamble. Explain the three
buckets, spending most words on the **louder** four (obligations, diplomatic
demands) because that is the surprising half. Close with two paragraphs: what
still cannot be fixed by settings (103 engine-fired keys; the watchlist logic
Message Settings has no way to express), and one line that a mod exists.

**Why it works.** It is a genuinely useful post that costs the reader nothing,
and the "make some *louder*" angle immediately separates it from "turn stuff
off" content. The mod becomes the obvious next click rather than the pitch.

**Risk.** Lowest ceiling of the three — a settings list is useful, not
exciting. Mitigated by the screenshot doing the emotional work up front.

---

## Proposal B — "The game is hiding most of it from you"

**Title:** *Victoria 3 fired 8,410 notifications at my country in ten years and
showed me none of them. I instrumented the game to find out what else it isn't
telling me.*

**Images**
1. A chart: firings per notification key, log scale, with the tier each one
   displays at as the bar colour — the shape alone shows a long tail the player
   never sees.
2. The feed screenshot.
3. Optional: the `docs/engine-fired-keys.md` table as an image, or linked.

**Body:** lead with the neutrality-declaration number as a curiosity, not a
complaint — the engine is doing a *lot* of bookkeeping and vanilla already
hides most of it, which is the interesting part. Then the twist: of the
notifications that *do* reach you, a large share come from a set of 103 keys
fired by engine code that no mod can hook, and the single biggest cluster
reaching the feed is interest-group churn. Finish on method — how it was
measured, that every figure is a lower bound, and why.

**Why it works.** The strongest title of the three, and it is a genuine
finding rather than a complaint. r/victoria3 has an audience that enjoys
engine internals, and "here is what the game does under the hood" earns
goodwill that a tuning post does not.

**Risk.** Needs a real chart to land, and the framing must stay curious rather
than critical — "look what I found" not "look how bad this is". Hardest of the
three to write well.

---

## Proposal C — "The bug nobody knows about"

**Title:** *If you mobilize an army without a general, your front silently
stops advancing — and the game never tells you.*

**Images**
1. Before: the army, mobilized, no general, front unmoving.
2. After: the red top-bar alert.

**Body:** short. The failure mode, why it is easy to miss (nothing is *wrong*,
the front just does not move), how to check, and that an alert can be added.
Then broaden by one paragraph: this is one of several places the game's
notification layer has a gap, here is the data, here is the mod.

**Why it works.** Most immediately useful to the most people, and the most
likely to draw "wait, is THAT what happened to me?" comments — which is the
engagement the other two have to work for. Shortest to write.

**Risk.** Thinnest on its own, and needs verification that this is genuinely
unflagged in vanilla rather than something the UI hints at elsewhere. Reads as
a mod advert if the broadening paragraph is not carefully done.

---

## Recommendation

**Lead with A, hold B for the patch-day slot.**

A is the safest to publish this week: it is complete, it needs no figure that
the pending vanilla test could overturn, and the give-it-all-away framing was
the agreed rule. B is stronger but wants the chart built and ideally the
"-90%" number verified so it can carry a second act; it also pairs naturally
with an "Updated for patch 1.x" post, which the TODO already flags as the
highest-value slot.

C works as a comment reply or a follow-up rather than a standalone.

**Before any of them ship:** run `python tools/package_release.py` and upload
from `smart_notifications_release`, never the dev junction.
