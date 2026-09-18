Reddit post — r/victoria3
=========================

**Check the subreddit sidebar first** for a self-promotion rule and the right
flair. Not verified: Reddit is not reachable from this session.

## Framing: feature request, not mod announcement

Damien's framing, reused from the population-count post that did well, and it
is **better than the mod-announcement version this file used to recommend**.

A mod announcement asks the reader to want a mod. A feature request asks them
to agree with a complaint, which is a far cheaper thing to give. Most of the
subreddit will never install anything; under this framing they can still
upvote, because the post is about the game, not about the mod. The mod
becomes evidence for the argument rather than the point of the post, which
also sidesteps the "another mod ad" reflex entirely.

Post the **GIF as a native upload** with the text as the post description.

## Title

> There should be a "build all" button to build power plants (or any
> building) in all your states

Keep it. Leading with power plants is right — it is the concrete, universally
felt case — and the parenthetical stops the whole thing being read as a
power-plant mod, which is a misread the Workshop page already had to fix.

## Body

> It's so tiring to manually add one level of power plants in every state
> once you discover Electricity. Ninety states, ninety clicks — and again
> every time you take new land.
>
> I ended up building it as a mod [LINK], but this really should be in the
> base game. It is one interface file; none of it needed new game logic,
> because the button the game already has does all the work.
>
> How it works: choose a building, choose which states via the normal
> location filter in the build screen (all, domestic, foreign), select 1, 5
> or 10 levels, click Build All. Boom, it's in your queue.
>
> No cheating — it presses the game's own **+** button once per state, so
> normal cost and normal queue. Achievement compatible.

### What changed from the draft, and why

- **"I build this in 3 lines" is gone.** It is the one line that could cost
  the post. The `.gui` is 167 non-comment lines, the mod is public, and this
  subreddit will look. Getting caught exaggerating in the sentence whose
  whole job is "this is so easy, why isn't it in the game" would undo the
  argument it is making.

  The replacement keeps that force and is true: **one interface file, no new
  game logic**. That is a stronger claim anyway — not "I wrote it quickly"
  but "the game already contains everything needed and simply does not
  expose it". That is the actual case for it being base-game.
- **"I build" → "I ended up building"** (tense, and it sounds less like a
  pitch).
- **Added "ninety states, ninety clicks"** — a number makes the complaint
  concrete, and it is the phrase people will quote back.
- **"no cheating" now says why** in six words. Unsupported, it reads
  defensive; with the mechanism it reads confident.

### Deliberately left out

**The sort-order behaviour** — that the queue follows however you have sorted
the list, so sorting by Earnings builds richest-first. It is the most
distinctive thing the mod does and no competing mod claims it.

It stays out of the post on purpose. The post is an argument about the base
game and should stay short; and this is the best thing to have in reserve for
the comments, where a specific clever detail earns far more than it would as
a fourth bullet nobody reads.

## Replies to have ready

Early comment velocity drives reach, so do not compose these live.

- **"Isn't this cheating?"** The reply that matters. Same + button, once per
  state; the game refuses anything you could not click yourself. Short, not
  defensive.
- **"Does it work with [other UI mod]?"** It replaces one small interface
  definition rather than the whole construction panel, so it coexists with
  most things — but anything else touching that same panel will clash. Ask
  what breaks.
- **"Can you add a Max option?"** Left out pending demand. **Watch for this
  one:** more than two requests is the signal to build it.
- **"Doesn't this break achievements/ironman?"** No. Mods do not disable
  achievements in Victoria 3; debug mode does.
- **"Why isn't this in the base game?"** — the one the framing invites. Best
  answer is the honest one: the panel already computes the list of valid
  states and already has a per-row button, so a bulk action is a UI
  affordance away.

## Timing

Roughly 13:00-16:00 UTC on a weekday catches US and EU together. Be around
for the first hour.
