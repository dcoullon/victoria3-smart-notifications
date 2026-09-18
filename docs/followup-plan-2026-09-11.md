# Implementation plan — post-launch follow-ups (2026-09-11)

Written before any code, at the user's request, to avoid the
build-test-rebuild churn of earlier sessions. Everything below is either
**VERIFIED** (read out of vanilla files / the game's own docs dump on this
machine) or **UNVERIFIED** (needs one live check). Nothing is inferred from a
`.gui` binding and then assumed to work in dynamic text — the two function
tables are kept separate per CLAUDE.md.

Specs for 2a(i) and 2a(ii) were **locked 2026-09-11** against three
screenshots from a Morocco 1836 run. 2b is locked on mechanics but still
needs an event screenshot for placement.

Three workstreams:

1. Notification **volume measurement** (feeds a Reddit follow-up post)
2. **Diplo UX** — 2a(ii) country-panel alliance rows, 2a(i) play-start prediction
3. **Event pop context** — 2b

---

## Item 1 — Volume measurement

### 1.1 Coverage audit — the sanity check

**The logger does not capture all the volume. It captures about 7%.**

| | count |
|---|---|
| Message keys defined in vanilla | **463** |
| ...grouped into Message Settings rows | 107 |
| Keys with a script-side `post_notification` call site (**hookable**) | **360** |
| Keys fired by native engine code (**permanently unmeasurable**) | **103** |
| Keys the current logger actually covers | **33** |

By tier (VERIFIED, computed from `common/messages/*.txt` cross-referenced
against every `post_notification` call site in vanilla `common/` + `events/`):

| tier | total | hookable | engine-only |
|---|---|---|---|
| toast | 223 | 182 | **41** |
| feed | 230 | 175 | **55** |
| popup | 9 | 8 | 1 |
| none | 7 | 1 | 6 |

Of the 223 toast keys — the ones that matter for a noise post — 182 are
measurable in principle and 41 never will be.

### 1.2 Why the logger can't simply be widened to 360

**Where the call sites live** (VERIFIED, files containing `post_notification`):

| location | files |
|---|---|
| `events/` | **72** |
| `common/journal_entries/` | 9 |
| `common/scripted_effects/` | 8 |
| `common/scripted_buttons/` | 4 |
| `common/on_actions/` | **2** |
| `common/diplomatic_actions/` | 2 |
| `common/character_interactions/` | 2 |

The existing logger appends an entry to a vanilla on_action, which is safe and
additive. That pattern only reaches on_action call sites. Most notifications
are posted from inside **event** bodies, and instrumenting those means
**overriding vanilla event files** — invasive, conflict-prone, and it would
have to be undone before release. **Do not do this.**

**There is no generic hook.** Checked and ruled out:

- Message definitions accept exactly 8 fields — `type`, `texture`,
  `notification_type`, `group`, `color`, `days`, `on_created_soundeffect`,
  `popup_name`. There is **no `on_created` effect**, only a sound effect.
- None of the 220 on_actions in the game's own `on_actions.log` dump is a
  notification-posted hook.

Cheap ceiling = the ~27 non-event call-site files. **Step one is to enumerate
exactly which keys those cover** — scripted, not guessed.

### 1.3 One playthrough is enough, not two

**The mod does not change how often anything fires — it changes which tier a
firing displays at.** So:

```
volume_vanilla(tier) = Σ firings(key) × [vanilla_tier(key) == tier]
volume_mod(tier)     = Σ firings(key) × [mod_tier(key)     == tier]
```

Both come from **one** firing log joined against the static tier table
`tools/compare_notification_settings.py` already produces. No vanilla control
run needed.

**The one exception:** where the mod *mutes a vanilla key and posts its own
instead* from an on_action (diplomatic actions, plays, pact breaks). There the
firing itself differs, so mod keys must be logged alongside the vanilla key
they replace, with an explicit mod-key → vanilla-key mapping. That mapping is
small and it is the part most likely to be quietly wrong — build it deliberately.

### 1.4 What to build (logging only — approved scope)

1. `tools/audit_notification_coverage.py` — for all 463 keys: vanilla tier, mod
   tier, group, call-site location, logger coverage. Makes the coverage claim
   reproducible instead of a number in a doc.
2. Extend `01_smart_notifications_logger.txt` to every **non-event** call site
   the audit finds, same append-only on_action pattern. Player-scope each hook
   only where the root type is *confirmed* a country — per
   [[v3-logger-player-scoping]], never guess a scope name for Diplomatic
   Play/Demand roots.
3. Log the mod's replacement keys with a distinct tag (`SNW_LOG|mod|<key>` vs
   `SNW_LOG|vanilla|<key>`) so the §1.3 join is unambiguous.
4. Extend `tools/scan_logs.py` with a `--volume` mode that does the join.

### 1.5 Spot-check protocol

The log proves a notification *fired*, not that the player *saw* it at the tier
we think.

- Pick 6 keys: 2 toast, 2 feed, 1 `none`, 1 the mod re-tiered from vanilla.
- Short run with the logger on; note in-game start/end dates.
- Screenshot the feed (scrolled fully) at two or three fixed dates.
- Every logged firing in the window should appear at its expected tier; every
  `none` key should appear nowhere.

Two invalidators to watch: the `days` field (on 31 keys) can expire feed
entries before you scroll, and a stored Message Settings override silently
beats the mod (see [[v3-notification-override-hierarchy]]) — so the run must
start from **Reset to Default Settings**, mod off for the vanilla baseline.

---

## Item 2a(ii) — Alliances & defensive pacts on the country panel

### CORRECTION to the first draft of this plan

The earlier draft routed this through `Country.AccessActiveDiplomaticPactTypes`.
**That is wrong for alliances.** VERIFIED: alliance, defensive pact and
guarantee are **treaty articles**, not diplomatic pacts —
`common/treaty_articles/00_alliance.txt` (`alliance`, `kind = mutual`),
`01_defensive_pact.txt` (`defensive_pact`, `kind = mutual`),
`02_guarantee_independence.txt` (`guarantee_independence`, `kind = directed`).
There is no `alliance` entry under `common/diplomatic_actions/` at all. This is
exactly the change the user described ("now that defensive pacts and alliances
are parts of treaties"), and it is why the vanilla panel buries them in the
Treaties list.

### The exact insertion point

VERIFIED, `country_panel.gui:2249-2283`:

```
### TREATIES
treaties_country_list = {}

### DIPLOMATIC STATUS
flowcontainer = {
    default_header = { text = DIPLOMATIC_STATUS_HEADER }
    empty_state   = { visible = "[Not(Country.HasActiveDiplomacy)]" ... }
    diplomatic_pact_container   = {}   ← Improve Relations, Protectorate
    obligations_owed_from_container = {}
    obligations_owed_to_container   = {}
    truce_container = {}
}
```

The three new rows go **immediately before `diplomatic_pact_container = {}`**,
which is what the user asked for ("right above Improve Relations").

### Data path (all VERIFIED)

| need | binding |
|---|---|
| the country's active treaties | `Country.GetInForceTreaties` (datamodel; already used at `country_panel.gui:2303`) |
| mutual articles (alliance, defensive pact) | `Treaty.GetMutualAgreements` → item datacontext is `Article` (`country_panel.gui:2509`) |
| directed articles (guarantee) | `Treaty.GetOffers` (`:2811`), `Treaty.GetDemands` (`:3005`) |
| which article this is | `Article.HasType('alliance')` — established idiom, used ~8× in `country_panel.gui` itself |
| the counterparty | `Treaty.GetOtherCountry`, `Article.GetFirstOrSourceCountry`, `Article.GetSecondOrTargetCountry` |
| icon | `Article.GetIcon`, or the article's own `icon =` field |
| empty-row suppression | `visible = "[Not(IsDataModelEmpty(...))]"` — the pattern `diplomatic_pact_container` already uses |

### Locked spec

Three rows, each hidden entirely when it has no countries (matching the
existing rows' behaviour — the user's call: do **not** show "no allies" for now):

1. **Allies** — countries with an in-force `alliance` article
2. **Defensive Pacts** — countries with an in-force `defensive_pact` article
3. **Guaranteed By** — countries holding a `guarantee_independence` article
   *directed at* this country (direction matters: we want who would defend
   them, not who they guarantee)

Row shape mirrors `Improve Relations`: label on the left, counterparty flags on
the right, each flag tooltipped with the existing `Article`/`Treaty` tooltip.

Purpose, in the user's words: make it immediately clear **"who is obligated to
come to their help if you attack them"** — which is why guarantees belong here
alongside alliances, and why directed articles need the direction check.

### Risks

- `country_panel.gui` is **4,420 lines** and becomes a full-file override:
  conflicts with any other country-panel mod, and needs re-diffing against
  vanilla every game patch. The mod already overrides two `.gui` files, so the
  pattern exists, but this is the largest one yet.
- `(SN)` label prefix is **not** required here — this is an addition to a
  vanilla screen, not a new message group or alert, and CLAUDE.md's tagging
  rule covers Message-Settings-visible labels and standalone opt-in UI. Row
  headers for vanilla data are neither. Worth a second opinion before shipping.

---

## Item 2a(i) — Predicted joiners on the play-start screen

### Where it lives

**Not** `diplomatic_play_panel.gui` (that's the in-play panel). The screen in
screenshot 2 is the play-start confirmation popup: **`popups.gui:2927-3005`**,
driven by the `DiplomaticPlayConfirmation` object.

Current structure (VERIFIED) — three instances of one `start_diplo_play_table`
type:

| table | datamodel | header |
|---|---|---|
| Our Side | `DiplomaticPlayConfirmation.AccessInitiatorCountries` | `OUR_SIDE` |
| Enemy Side | `DiplomaticPlayConfirmation.AccessTargetCountries` | `ENEMY_SIDE` |
| Undecided | `DiplomaticPlayConfirmation.AccessUndecidedCountries` | `DIPLO_PLAY_STANCE_UNDECIDED` |

Only the Undecided table overrides columns 4/5/6 — support-initiator,
support-target, and `PREFERENCE_PREDICTION` ("Prediction").

### The prediction is already computed and exposed

This is the find that makes the feature small. VERIFIED,
`localization/english/interfaces_l_english.yml:11208`:

```
PREFERENCE_LABEL: "[SelectLocalization(DiplomaticPlayConfirmation.PredictHasPreferenceForInitiator(Country.Self), 'PREFERENCE_INITIATOR', '')]
                   [SelectLocalization(DiplomaticPlayConfirmation.PredictHasPreferenceForTarget(Country.Self),    'PREFERENCE_TARGET',    '')]"
```

So **`PredictHasPreferenceForInitiator(Country)` and
`PredictHasPreferenceForTarget(Country)` are booleans the game already
evaluates per undecided country.** The engine's own model matches the user's
description — support-A / support-B / neutrality scores, highest wins — and the
tooltip in screenshot 3 is
`DiplomaticPlayConfirmation.PredictCannotJoinOrPreferenceForInitiatorDesc(Country.Self)`,
used directly in `.gui` today.

Also available: `CanJoinInitiator(Country)` / `CanJoinTarget(Country)` (used by
the `CANNOT_SUPPORT` labels), `GetInitiatorCountry`, `GetTargetCountry`.

### Locked spec

Under **Our Side**, after the committed rows, render the undecided countries
where `PredictHasPreferenceForInitiator(Country.Self)` is true, visually
distinguished as *predicted* (dimmed / italic / a "likely" marker — not the
same weight as a committed participant). Same under **Enemy Side** with
`PredictHasPreferenceForTarget`. Each predicted row keeps the existing
Battalions / Conscripts / Ships columns so the side totals read at a glance,
and keeps the existing preference tooltip.

Countries stay in the Undecided table as they are today — this adds a
projection, it does not move rows out. When a country actually commits, vanilla
already moves it into the real side list, so the predicted entry disappears on
its own with no extra logic.

**Explicitly out of v1**, per the user: infamy-threshold prediction and any
other inference. This surfaces only what the engine already computes.

### The one thing to test first

`PredictHasPreferenceForInitiator/Target` are confirmed in **loc**, not in a
`.gui` binding. Per CLAUDE.md the two function tables are separate and
precedent does not transfer — in either direction. Mitigating evidence: the
sibling `PredictCannotJoinOrPreferenceForInitiatorDesc(Country.Self)` *is*
called directly in `.gui` (`popups.gui`, the column-4 tooltip), so both the
object and the `(Country.Self)` argument pattern work there. Risk is low but
non-zero. **Test exactly this one binding before building the rest:**

```
visible = "[DiplomaticPlayConfirmation.PredictHasPreferenceForInitiator(Country.Self)]"
```

If it fails, the fallback is to keep the condition inside a loc string via
`SelectLocalization`, exactly as `PREFERENCE_LABEL` does today.

### Parked nice-to-have

Weighted side strength. The user's point is correct — a battalion at 20 attack
is worth more than two at 10 — but **no exposed function returns an army power
score**. What exists is counts (`Country.GetBattalions`,
`DiplomaticPlay.GetTotalNumBattalionsForSide`, warships, conscripts) and
rankings (`Country.GetBattalionsRanking`). Any quality weighting would have to
be reconstructed from military formations, which is a much bigger piece of
work. Park it; revisit after v1 ships.

Also noted from screenshot 2: the Undecided list's sort order is not battalion
count (Carlist Spain's 60 sits below Portugal's 21). Adding an explicit sort is
cheap and might be worth folding in.

---

## Item 2b — Event pop context

### What the user actually needs

Events scope their pop effects three ways, and the problem is the same in all
three: *is that a lot of people or not?*

- **culture × state** — "the Bedouin people in Extremadura"
- **strata × strategic region** — "the upper class in region XX"
- **strata × country** — "the middle class across the country"

**Revised 2026-09-11 after four in-game screenshots** (Portugal 1907-08). The
dominant real shape is **interest group × state/country**, not strata. The
hover tooltip on each option already gives the percentage and the group; what
is missing is the denominator and the baseline:

- *"+5.0% of **Petite Bourgeoisie** members of Pops in **Portugal** become more Loyalist"*
- *"+5.0% of **Intelligentsia** members of Pops in **North Angola** become more Radical"*
- *"**Armed Forces** gets Government Insults Military Honor — **-2 Interest Group Approval**"*

That last one is the clearest case: `-2` against an unknown current value, when
approval has threshold effects, is not actionable. The user also wants the
IG's **clout share** inline, to know whether the group matters at all.

All of it is available in dynamic text (VERIFIED in vanilla loc):

| missing information | binding |
|---|---|
| how many people the IG is | `InterestGroup.GetPopulation`, `GetPopulationInCountryAsPercentage` |
| ...within one state | `InterestGroup.GetPoliticalStrengthInStateAsPercentage` |
| current approval (the "−2 from what?") | `InterestGroup.GetApprovalValue`, `GetApprovalRating`, `GetApprovalValueDesc` |
| clout — does this group matter | `InterestGroup.GetClout`, `GetFractionOfCloutSupportingMovement` |
| current loyalist / radical split | `GetNumLoyalists`, `GetNumRadicals`, `GetNumNeutrals` (+ `...Ratio`) |

The loyalist/radical split is the most valuable of these: for "+5% become more
Loyalist" it shows both the size of the group and the balance the delta moves,
which is the actual decision input.

**This also downgrades the region blocker.** These events scope to states
(North Angola, Extremadura) and countries (Portugal), not strategic regions —
so the one case the engine cannot answer looks rarer than feared. Confirm
against more samples before treating it as solved.

Noted for correctness: a strata is a set of jobs (upper = capitalists +
aristocrats). That does not require summing pop types — the
`Country.Get{Lower,Middle,Upper}StrataPopulationTrend` accessors return the
aggregate directly.

### The magnitudes are percentages — so head-counts are real

VERIFIED, the game's own `docs/effects.log`:

> `add_radicals` — "value is the percentage of each pop that will move towards
> radicalism. ... pop type and strata are mutually exclusive."
> **Supported Scopes:** country. (`add_radicals_in_state`: same, state scope.)

And magnitudes are plain fractions (`common/script_values/event_values.txt`):

```
small_radicals = 0.02   medium_radicals = 0.05   large_radicals = 0.1
very_large_radicals = 0.2   huge_radicals = 0.3
```

So `add_radicals = { value = medium_radicals, strata = middle }` is exactly
*5% of every middle-strata pop* — an absolute number, not a hand-wave.

### What the engine can and cannot tell us

All confirmed in vanilla **loc** (dynamic text, not `.gui` bindings):

| scope shape | binding | status |
|---|---|---|
| culture × state | `STATE.GetPopulationForCulture(CULTURE.Self)` — exact precedent at `interfaces_l_english.yml:52, 10138` | ✅ |
| culture × country | `Culture.GetPopulation`, `...AsPercentage` | ✅ |
| religion × state / country | `Religion.GetStatePopulation`, `Religion.GetPopulation` | ✅ |
| pop type × state / country | `PopType.GetStatePopulation(State.Self)`, `PopType.GetPopulation(GetPlayer)` (+% variants) | ✅ |
| strata × country | `Country.Get{Lower,Middle,Upper}StrataPopulationTrend`, `SocialClass.GetTotalPopulationIn(GetPlayer)` | ✅ |
| state total | `State.GetPopulationSize`, `SCOPE.sState('x').GetPopulationSize` | ✅ |
| strata × state | `SocialClass.GetTotalPopulationIn` — only ever called with a **country** in vanilla | ⚠️ unverified |
| **anything × strategic region** | — | ❌ **blocked** |

**The region case is genuinely blocked.** `StrategicRegion` exposes only
`AccessIncorporatedStates`, `AccessUnincorporatedStates`,
`GetTotalGDP`, `GetCountriesWithInterest`, names and interests — **no
population accessor** — and dynamic text has no aggregation, so summing across
its states is not possible in loc. "The upper class in region XX" cannot be
quantified inline. Options: fall back to the country-wide strata number with a
note, or show nothing for region-scoped effects. **Needs a product call.**

### Worked examples (real events)

**`1848.5` — "Radicals at the Gates"** (`events/1848.txt:500`):

- a) secret police — tech progress, enactment modifier, journal entry. *No pop effect.*
- b) national guard — same shape. *No pop effect.*
- c) neither (default) — `capital = { add_radicals_in_state = { value = medium_radicals } }`

Real choice: institutional benefit vs *5% of my capital state turns radical*.
The player is told neither the 5% nor the size of their capital.

**`1848.4`** (`events/1848.txt:434`) — the better case, two options hitting
different strata:

- option 1: `add_loyalists{strata=upper, very_large}` (20%),
  `add_radicals{strata=middle, medium}` (5%), `add_radicals{strata=lower, medium}` (5%)
- option 2: `add_radicals{value=medium_radicals}` (5%, **all** pops)

Impossible to weigh "20% of upper loyal, 5% of middle and lower radical"
against "5% of everyone" without the three strata sizes — all three of which
are directly available.

### REVISED 2026-09-11 (second pass): it CAN be dynamic — 8 loc keys, not 2,227 events

Measured distribution across **all 1,376** `add_radicals`/`add_loyalists`
blocks in vanilla (so this supersedes any impression from a handful of
screenshots — strata is real but it is not the majority):

| filter | share |
|---|---|
| `pop_type` | 26.2% |
| `culture` | 24.6% |
| `strata` | 17.9% |
| *(no filter — all pops)* | 15.8% |
| `interest_group` | 11.8% |
| `religion` | 9.3% |

Scope: **country 59%, state 41%** — and **nothing else**. `add_radicals`
supports only country scope and `add_radicals_in_state` only state scope, so
**the strategic-region blocker does not apply to these effects at all.** Any
"region" phrasing the player sees comes from the event's own prose, not the
effect. That earlier blocker is closed.

**The mechanism.** The effect tooltip is not hand-written per event — the
engine renders it from **eight overridable loc keys**
(`interfaces_l_english.yml:584-593`):

```
ADD_RADICALS:3        "$VALUE|-=1%$ of $FILTER_DESC$ become more [concept_radical]"
ADD_RADICALS_FIRST:3  "$VALUE|-=1%$ of $FILTER_DESC$ in [COUNTRY.GetNameNoFlag] become more [concept_radical]"
ADD_RADICALS_THIRD:3  "$VALUE|-=1%$ of $FILTER_DESC$ in [COUNTRY.GetName] become more [concept_radical]"
ADD_RADICALS_IN_STATE_THIRD: "$VALUE|-=1%$ of $FILTER_DESC$ in [STATE.GetName] become more [concept_radical]"
(+ the four ADD_LOYALISTS equivalents)
```

A mod can override a loc key. Overriding these eight changes the tooltip for
**every one of the 1,376 effect blocks at once** — no per-event work, no event
file overrides, and it keeps working for events added in future patches.

**What is in scope inside the template:** `$VALUE$` (the percentage),
`$FILTER_DESC$`, and `[COUNTRY]` / `[STATE]`.

**CORRECTION — an earlier pass claimed `$FILTER_DESC$` was engine-rendered and
the subgroup therefore unknowable. That was wrong.** `$FILTER_DESC$` resolves
to `POP_EFFECT_FILTER`, itself an overridable loc key, and it proves the filter
objects are live scopes in this context (`effects_l_english.yml:577-582`):

```
POP_EFFECT_FILTER: "[AddLocalizationIf(InterestGroup.IsValid, 'POP_EFFECT_FILTER_INTEREST_GROUP')]
                    [AddLocalizationIf(Culture.IsValid,       'POP_EFFECT_FILTER_CULTURE')]
                    [AddLocalizationIf(Religion.IsValid,      'POP_EFFECT_FILTER_RELIGION')]
                    [AddLocalizationIf(PopType.IsValid,       'POP_EFFECT_FILTER_POP_TYPE')]
                    [AddTextIf(Not(EqualTo_string('none', '$STRATA$')), Concatenate(Localize('$STRATA$'), ' '))]
                    [Concept('concept_pop', '$concept_pops$')]"
POP_EFFECT_FILTER_INTEREST_GROUP: "[InterestGroup.GetName] members of "
POP_EFFECT_FILTER_CULTURE:        "[Culture.GetName] "
POP_EFFECT_FILTER_RELIGION:       "[Religion.GetName] "
POP_EFFECT_FILTER_POP_TYPE:       "[PopType.GetName] "
```

So `InterestGroup`, `Culture`, `Religion` and `PopType` are all bound objects
(each with `.IsValid` to test which one applies), `$STRATA$` is a string
(`'none'` when unset), and the parent template adds `COUNTRY` / `STATE`.

**Every one of the six filter shapes therefore has a population accessor** —
all confirmed present in vanilla loc:

| filter | share | accessor |
|---|---|---|
| `pop_type` | 26.2% | `PopType.GetPopulation(COUNTRY)` / `PopType.GetStatePopulation(STATE)` |
| `culture` | 24.6% | `Culture.GetPopulation` / `Culture.GetStatePopulation` |
| `strata` | 17.9% | `COUNTRY.Get{Lower,Middle,Upper}StrataPopulationTrend`, selected off `$STRATA$` |
| *(none)* | 15.8% | `COUNTRY.GetTotalPopulation` / `STATE.GetPopulationSize` |
| `interest_group` | 11.8% | `InterestGroup.GetPopulation` |
| `religion` | 9.3% | `Religion.GetPopulation` / `Religion.GetStatePopulation` |

**A literal "≈ XXk people affected" is computable in 100% of cases**, since
`$VALUE$` is the fraction and vanilla already does loc-side arithmetic with
`Multiply_CFixedPoint`. One override of `POP_EFFECT_FILTER` (or of the four
sub-keys) reaches every event, journal entry and decision that uses these
effects — and `KILL_POPULATION*` shares the same `$FILTER_DESC$`, so war and
disaster tooltips improve for free.

**Three things to test before building:**

1. Is `$VALUE$` reachable inside `POP_EFFECT_FILTER`? `$STRATA$` is, so
   parameters do pass through — but if not, do the append in the eight parent
   templates instead, where `$VALUE$` certainly exists and the filter scopes
   should still be bound.
2. Can `STATE.Self` / `COUNTRY.Self` be passed as a function argument
   (`PopType.GetStatePopulation(STATE.Self)`)? Same open question as before.
3. Does a mod's `ADD_RADICALS` override beat vanilla's? The keys carry a `:3`
   version suffix — confirm whether load order or that number decides.

**To verify first:** that a mod's `ADD_RADICALS` override actually wins over
vanilla's (Paradox loc keys carry a `:3` version suffix; confirm whether load
order or the version number decides, and match it).

**Consequence for the event-window strip below:** largely redundant if the
tooltip override lands, since the numbers arrive exactly where the player is
already looking. Build the loc override first and re-evaluate the strip after.

### What the cheap version is, concretely

**A population context strip in the event window.** One `eventwindow.gui`
override. No event files touched, no loc keys overridden, works across all
2,227 events automatically. It shows, for the player's country: lower / middle
/ upper strata head-counts and shares, plus total population; and where the
event carries a state scope, that state's population.

It does **not** say what each option does. It supplies the denominator, so
"middle strata" stops being an abstraction.

### Why inline per-option numbers stay parked

`EventOption` exposes **no effect introspection** (VERIFIED, `eventwindow.gui`:
only `GetText`, `GetDesc`, `IsEnabled`, `Select`, `IsHighlightedOption`,
`IsDefaultOption`). Nothing in `.gui` or script can ask an option what it would
do. Hand-authoring is the only route: **2,227 events**, **1,376**
`add_radicals`/`add_loyalists` occurrences across **192 files**, and every
overridden loc key silently freezes against future patches.

**Middle path worth considering after the strip ships:** hand-author the 10–20
highest-traffic events only (the 1848 family and similar), where the numbers
matter most and the player sees them every campaign. Finite and maintainable.

### Tests to run before building

1. Can `SCOPE.sState('x')` be passed **as a function argument** —
   `[GetPopType('farmers').GetStatePopulation(SCOPE.sState('target_state').Self)]`?
   No vanilla precedent. Country-scoped strata numbers don't depend on it.
2. Does `SocialClass.GetTotalPopulationIn` accept a **state**, or country only?
3. Does an event's loc actually have the scopes in context at option-render
   time, or only at fire time?

All three are one short playthrough with a scratch loc key, not three sessions.

### Still needed from the user

- A screenshot of an event with several pop-affecting options, mid-game, to
  place the strip without crowding the option buttons.

---

## Repo structure — decided and built 2026-09-11

Everything in items 2a and 2b ships as a **second mod**, `better_decision_info/`, developed
in this repo on branch `better-decision-info`. Full rationale in
[multi-mod-split.md](multi-mod-split.md); the short version:

- **The split line is risk profile, not theme.** Script and small
  self-contained `.gui` stay in Smart Notifications. Overrides of large vanilla
  `.gui` files (`country_panel.gui` 4,420 lines, `popups.gui` 5,156,
  `eventwindow.gui` 631) go in the new mod. So 2b goes there too, despite the
  argument that events are a kind of notification — the question that matters
  is what breaks when Paradox patches the event window.
- **A `.gui` override must sit at the exact vanilla path**, so it cannot be
  isolated in a subfolder inside one mod. The mod boundary is the only
  isolation boundary available.
- **Merging back later is easy; splitting later is not.** Copy the folders
  across and merge two `metadata.json` files. Splitting a mod that already has
  subscribers costs a new Workshop item, the subscriber count, and every
  player's stored settings. Starting separate keeps both options open.

Built: branch `better-decision-info`, `better_decision_info/.metadata/metadata.json` (no BOM, verified),
a placeholder loc file (BOM, verified), and an NTFS junction at
`Documents/Paradox Interactive/Victoria 3/mod/better_decision_info`. Still needs adding to
the active Playset in the launcher before it will load.

**Tooling is now mod-aware.** `tools/check_references.py` gained
`read_mod_id()` and `nested_mod_roots()`; the five checks that assert Smart
Notifications' own content exists (law-type dispatch, full-override match, both
watchlist-spec checks, `(SN)` label tagging) plus `check_known_good()` in
`validate_syntax.py` are gated on the mod id — **not** the folder name, so a
rename cannot silently disable them. `_iter_mod_files()` excludes nested mod
roots so the parent's checks never judge the sibling's files.

Verified after gating: both roots pass; `check_known_good` and
`check_watchlist_spec_tiers` still execute for Smart Notifications; called
directly against `better_decision_info` the watchlist check still produces its 46 errors,
proving it is gated rather than broken; the parent scan sees 0 sibling files.

`SHIP_DIRS` in `package_release.py` is an allowlist resolved from the repo
root, so `better_decision_info/` cannot leak into a Smart Notifications release. Packaging
the second mod needs its own target — not wired up, not needed until there is
something to upload.

## Probe run — how to test 2b's mechanics (built 2026-09-12)

`better_decision_info/localization/english/better_decision_info_probe_l_english.yml` answers all five
open mechanics questions in **one** playthrough. Throwaway file; delete before
anything ships.

**Reading the output.** Every probe prints a static `(Tn…)` marker beside its
dynamic value, because the two failure modes look identical otherwise:

| what you see | what it means |
|---|---|
| `(T2a poptype=1.2M)` | works |
| `(T2a poptype=)` — marker, no value | scope bound, **function** wrong |
| no `(T2a` marker at all | the `AddLocalizationIf` guard was false, or the override lost |
| no `(T1)` prefix anywhere | **mod loc cannot override engine templates** — stop, 2b is dead in this form |

**What each probe settles:**

- **T1 / T4** — override precedence. T1 matches vanilla's `:3`, T4 deliberately
  uses `:4`. Both appear → load order decides, version suffix cosmetic. Only T4
  → the number decides. Neither → overriding engine templates is impossible.
- **T1a–T1e** — `COUNTRY` scope, the three strata accessors, and whether
  `$STRATA$` passes through as a string.
- **T2a–T2d** — whether `PopType` / `InterestGroup` / `Culture` / `Religion`
  are live scopes inside `POP_EFFECT_FILTER`, and whether `$VALUE$` reaches it.
- **T3a–T3c** — `STATE` scope, and **can `STATE.Self` be passed as a function
  argument**. No vanilla precedent; gates the 41% of pop effects that are
  state-scoped. T3a working while T3b fails isolates arg-passing as the cause.
- **T4a / T4b** — loc-side arithmetic with `$VALUE$` as an operand, which is
  what turns "5% of 12.4M" into "about 620k".
- **T5** — `InterestGroup` bound in `ADD_MODIFIER_THIRD` behind an
  `IsValid` guard: the answer to "−2 approval, but −2 from *what*?"

**Blast radius warning.** T5 overrides `ADD_MODIFIER_THIRD`, which renders for
**every** `add_modifier` in the game — countries, states, characters, buildings,
not just interest groups. The `InterestGroup.IsValid` guard is what should keep
the marker off non-IG modifiers. If modifier tooltips break generally, that
guard is the cause; disable the mod and the game is unaffected.

**Fastest route to the tooltips:** fire events with known filter shapes from
the console rather than waiting for them —

| event | filter shape | probes exercised |
|---|---|---|
| `1848.4` | strata (upper/middle/lower), country | T1, T1b–d, T4 |
| `1848.5` | no filter, state (capital) | T3a |
| `dreyfus_events` (religion, state) | religion, state | T2d, T3 |
| `agitator_law_events_2` | interest_group, country | T2b, T5 |

Hover each option; the effect lines are in the option tooltip.

## Status at end of 2026-09-12 — pick up here

Branch `better-decision-info`. The whole event feature lives in one file:
`better_decision_info/localization/replace/english/bdi_replace_probe_l_english.yml`.

**Confirmed working in game, values cross-checked against the game's own
panels (not just "it rendered"):**

| line | example | verified against |
|---|---|---|
| subgroup size on a pop effect | `+2.0% of Rural Folk members of Pops (1.23M strong) in Portugal` | Rural Folk panel: 1.2M |
| interest-group standing on a modifier | `-5 Interest Group Approval (Currently +2 with 6% clout)` | sidebar: +2 / 6.6% |
| state scale on a modifier | `North Angola (703K people, 1% of the country) gets...` | — |

**Settled negatives — do not re-attempt without new evidence:**

- **The multiplied "about 24K" figure is impossible.** `$VALUE$` lives in the
  parent template; the filter objects live in `POP_EFFECT_FILTER`; neither
  context sees the other's half. Five candidate parameter names were tried
  for the magnitude inside `POP_EFFECT_FILTER` and all echoed their own
  names. `$STRATA$` does not reach the parent either.
- **`interest_group_approval_add` cannot see its interest group** — modifier
  labels render in a `Container` context (error.log, verbatim).
- **Multi-filter effects (68 of 1376, 4.9%) must show nothing.** The affected
  group is an intersection no accessor exposes; `And4` guards now suppress
  the size line for them.
- **Strata membership is hierarchy-dependent**, so a hardcoded profession sum
  would be wrong for Japan (Edo) and British India (caste), and decisions can
  switch a country mid-game. No accessor detects the active hierarchy.

**Open, in priority order:**

1. `(s11 state=… laborers=…)` on a strata modifier label — is `State` in
   scope there? Expected to fail for the same reason `interest_group_approval_add`
   did. If it fails, the "lower strata in this state" idea is closed.
2. `(s9 … strong)` — no strata-filtered *pop* effect has been seen in game
   yet. Uses `GetPlayer`, which the event audit showed is safe (0 of 246
   strata effects apply to a foreign country).
3. **Culture case, the original motivating example** — a culture in your
   country takes a hit and you cannot tell how big that culture is. 294
   culture-only effects exist, so the size line should fire. Good targets:
   `acceptance_events.1`, `algeria_events.1`, `agitator_legal_events.23`;
   richest files are `00_ip3_hungary_events.txt` (25), `poland_events.txt`
   (24), `algeria_events.txt` (17).
4. **Longer log run.** The interest-group guard writes a `FetchData failed`
   line whenever a modifier's subject is not an interest group — 1275 in one
   earlier session, 0 in a short one. Play long enough to see whether it
   accumulates. It matters because `scan_logs.py` is how we judge Smart
   Notifications' health, and this could bury real errors. Must be resolved
   before ship.

**Before ship, regardless:** strip every `(s#)` tag, rename the probe file to
something non-throwaway, and decide the `(SN)`-equivalent tagging convention
for this mod (CLAUDE.md's rule is written for Smart Notifications).

### 2026-09-14: the log question is answered, and it blocks shipping

A longer session settled it. `error.log` reached **1018 lines, ~1000 of them
ours**. Every render of `ADD_MODIFIER_THIRD` for a subject that is not a State
(or not an InterestGroup) writes four lines:

```
No context supplied (Use SetDataContext), wanted context of type 'State'
for 'State.IsValid'
FetchData failed for 'AddLocalizationIf(State.IsValid, 'BDI_STATE_STANDING')'
```

255 failed evaluations in one session — **204 State, 51 InterestGroup**. The
guard is correct on screen; the scope is simply *absent* rather than invalid
for other subject types, so it cannot be evaluated at all.

**Why this blocks ship:** it would fill every player's `error.log`, and
`scan_logs.py` is how we judge Smart Notifications' health — this could bury
real errors in the mod that is already live.

**Ruled out:** vanilla has no scope-existence guard (its only `Exists()` is
`GetVariableSystem.Exists`, for GUI variables), and there are no
subject-typed modifier templates — only `ADD_MODIFIER` / `_FIRST` / `_THIRD`.

**(s12) is a guard-form bake-off**: `AddLocalizationIf` (the known-bad
baseline), `AddTextIf`+`Localize`, and `SelectLocalization` with an empty
else, each pointing at its own key so `error.log` names whichever still fail.
A form passes only if it renders **and** its key is absent from the log
afterwards.

**If none passes, it is a product decision, not a technical one:**

| option | keeps | costs |
|---|---|---|
| Drop the modifier-line features | the pop-effect size line, which has **no** spam (POP_EFFECT_FILTER always binds its scopes) | loses interest-group standing and state scale |
| Keep them and accept the noise | everything | ~1000 log lines per session, in every player's install |
| Keep only interest-group standing | the explicitly-requested feature | still ~51 failures per session |

The first option is the only cleanly shippable one, and it still leaves a real
feature — the size line was the original goal.

## Suggested order

1. **Item 1 logging** — `audit_notification_coverage.py` first (pure analysis,
   no game changes; tells us whether widening the logger is worth it).
2. **2a(ii)** — smallest real feature, highest poll support, spec fully locked,
   no unverified mechanic. Best candidate to start.
3. **2a(i)** — one binding to test, then build; spec locked.
4. **2b** — after the three tests above, and after the event screenshot.

Item 1's feed-trimming decision (which of the 42 feed groups, if any, drop to
`none`) is deliberately **not** in this plan: per
[docs/watchlist-spec.md](watchlist-spec.md) the feed is the log you skim on
purpose, not a tier to empty, and that is a product call the volume data should
inform rather than precede.
