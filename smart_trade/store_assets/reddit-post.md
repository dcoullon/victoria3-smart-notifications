Reddit post: r/victoria3
========================

Check the sidebar for the self-promotion rule and flair before posting.

## Framing

Same as Build All: a complaint about the base game, with the mod as the
evidence. Readers can upvote "the game should show this" without wanting a
mod.

## Title

> Goods transfer treaties can cost you thousands a week, and the game never shows it

Alternative, if you want the question form:

> Why doesn't the game tell you what a goods transfer treaty earns or costs you ?

## Images (gallery, in this order)

1. `screenshots/01-picker.png`: the goods picker with a green profit on each card, and Net, Best, Max, 👍 under the slider.
2. `screenshots/02-draft-hover.png`: the breakdown before you sign (sale minus purchase, shipping, net).
3. `screenshots/04-treasury.png`: "(ST) Net treaty income" in the money tooltip.
4. `screenshots/03-treaty.png`: net per treaty and per good once signed.

## Body

> When you send goods in a treaty, your treasury buys them at home, sells them in your partner's market, and pays the shipping lane. Every week, for years. None of it is on screen: not before you sign, not after.
>
> Coffee to Austria in my game: the default quantity is 347 units, which loses £5.12K a week. 60 units makes +£321.
>
> I ended up building it as a mod [LINK]. Before you sign, every good shows its best weekly profit, and picking one starts at that quantity instead of the default. After you sign, you get the net per treaty and per good, and the total in the treasury tooltip.
>
> Display only, no cheating: the buttons move the slider like you would. Achievement compatible, all 11 languages.
>
> This really should be in the base game. Which goods do you send in treaties ?

## Replies to have ready

**"What's the game's default quantity ?"**
A quarter of the slider when the AI isn't interested in the good (24% to 25% in 3 out of 3 cases I checked). When the AI wants it, the game seems to use its own AI suggestion instead (3% to 4% in 2 cases). Neither looks at profit.

**"Why do the AI thumbs on the cards say no ?"**
The game scores each card at its own default quantity, often far more than the partner wants. Mods can't change that scoring. Pick the good and the acceptance updates for the real quantity.

**"How accurate is the shipping ?"**
Exact once signed: it reads the real shipping lane. Before signing the game hasn't picked a route, so drafts assume a medium-length one (×1.25 of the shortest). Overland partners pay nothing, and the draft says "No shipping".

**"How does Best work ?"**
It climbs the quantity while each extra unit still adds profit after shipping, using the game's own price rule, and keeps going past the partner's shortage only while their acceptance of that good stays positive.

**"Isn't sending goods good for my economy anyway ?"**
It can be: it raises prices for your producers. The mod only counts the treasury side, which is the part the game never shows. If you take a loss on purpose, at least you know its size.

**"Multiplayer ?"**
Display works, but the treaty totals count every human's sends. Single-player for now.

**"Does it work with [other mod] ?"**
It replaces the goods transfer picker, the treaty article cells, the outliner's treaty rows and two lines of the treasury tooltip. Anything else is fine.
