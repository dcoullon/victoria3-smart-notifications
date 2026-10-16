# Changelog

Player-facing changes, grouped by version (Added / Changed / Fixed / Removed),
written so they can be pasted into Steam Workshop update notes. Versions follow
`.metadata/metadata.json`'s `version`, same convention as Bulk Construction:
`+0.01` only when something genuinely new ships and is confirmed working.

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
