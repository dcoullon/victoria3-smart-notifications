# Changelog

Player-facing changes, grouped by version (Added / Changed / Fixed / Removed),
written so they can be pasted into Steam Workshop update notes. Versions follow
`.metadata/metadata.json`'s `version`, same convention as Bulk Construction:
`+0.01` only when something genuinely new ships and is confirmed working.

## [0.15] - lighter goods cards

### Changed
- The goods list does less work when it opens: a card for a good that pays
  takes 30-49% fewer steps to work out its figure, and a card for a good
  that does not pay, or that you receive, takes almost none.
- Goods cards look for the best quantity up to 10,000 units a week, down
  from 1,000,000. Deals that large are rare; above that a card may read
  low. The Best button is unchanged.

### Fixed
- A goods card could promise more than the Best button reaches, mostly a
  small market facing a partner short of a lot of that good. The card now
  stops where Best does.

## [0.14] - real prices

### Fixed
- Suggested goods transfers now include a good you already send to that
  country, when sending more in a new treaty would pay. Before, one coffee
  treaty with a partner hid every other coffee deal with them, even the most
  profitable one on the list.

### Changed
- The goods cards, the Best button and the suggested transfers now start from
  each market's real price, as the treaty's own figure already did. They used
  to rebuild prices from supply and demand alone, which misjudged deals with a
  market whose real price sits away from that (the game raises the price of
  goods under a monopoly, for example): one suggestion showed about +330 a
  week for a deal that earned about 60.
- Clicking the "goods transfer losing money" notification now opens that
  treaty.
- The market panel keeps game 1.15.2's own changes: the recentred trade
  capacity box, "None" in empty import and export charts, and the two-row
  sort buttons on the world market tab.

## [0.13] - which deals to make

### Added
- Suggested goods transfers in the market panel's Trade tab: the 5 most
  profitable deals you could propose, recomputed every month, when you open
  the tab and on refresh, in a section you can collapse. Each row shows the partner's
  base acceptance (details on hover), and partners below 0 are left out.
  The treaty button at the start of a row opens a treaty with that country,
  with the good already picked when you add a Goods Transfer.
- Each good's panel (your market's tab) lists the 3 best countries to send
  that good to, in the same form.
- A warning when a goods transfer you send has lost more than £100 a week,
  6 months in a row.
  Once per losing streak; renegotiating the treaty resets it. Its own
  "(ST) Goods Transfer Losing Money" group in Message Settings.

### Changed
- The treasury tooltip leaves out "(ST) Net treaty income" while it is £0.
- Shipping estimates for drafts depend on the route: within a continent they
  assume a short lane, between continents a long one (measured: up to 1.6
  times the short-lane cost). Signed treaties still use the real lane.

## [0.12] - game version 1.15

### Added
- Copper, the new good in 1.15. Shipping on copper now uses the game's rate of
  1 merchant marine per 5 units.

### Fixed
- Treaty rows in the outliner show 1.15's "binding period on hold" marker, and
  the net moves left so the two do not overlap.

## [0.11] - goods list frame rate

### Fixed
- The goods transfer picker no longer drops the frame rate while it is open
  (reported: 60 down to 6-11 fps, paused or not). Each good's best weekly
  profit is now worked out once when the list opens, not on every frame. In
  testing: 74 fps, against 78 with the figures switched off.

### Changed
- Goods card figures are whole numbers (+2677 rather than +2.67K), and stay
  as they were when the list opened until you reopen it.
- The goods card estimate is within about 2% of the true best (was 1.3%).

## [0.10] - first public release

### Added
- **Before you sign:** every good in the goods transfer picker shows its best
  weekly profit. Picking a good starts at its most profitable quantity.
- **Three buttons under the slider:** Best (most profit while the partner
  still accepts the good), Max (fills their shortage without going over your
  surplus), 👍 (the highest acceptance at the lowest cost). For goods the
  partner sends: Max and 👍.
- Live Net under the slider, with sale, purchase and shipping on hover;
  "No shipping" when your markets border each other.
- **After you sign:** net per treaty in the outliner (total on the Treaties
  header), net per good in the treaty panel, and "(ST) Net treaty income" in
  the treasury tooltip.
- All 11 languages Victoria 3 ships. Terms come from the game's own text;
  these are not native-speaker translations.
