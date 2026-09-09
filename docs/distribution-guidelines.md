# Distribution constraints: Steam Workshop & Paradox mod policy

Researched 2026-09-03 while investigating why a prior-art mod got pulled from
Steam. This is reference material, not code — treat it as a constraint list
to check before every release, not something to implement.

## What actually happened to "Better War & Diplo Notifications"

[Workshop ID 2887390170](https://steamcommunity.com/sharedfiles/filedetails/?id=2887390170) —
similar scope to our Phase 1/2 (elevated diplomatic/war/leader-death
notifications to toasts with custom sound cues). Its page states only the
generic boilerplate: *"This item has been removed from the community because
it violates Steam Community & Content Guidelines."* **No specific violated
rule is disclosed publicly** — Steam doesn't publish that.

Best available hypothesis, not confirmed: its description mentions it
"included sound effects" (i.e. bundled audio, not just reusing vanilla
`event:/SFX/...` references). Bundling third-party audio without clear
distribution rights is a common, plausible cause of takedowns. Our mod
currently only ever *points at* vanilla's own existing sound events in
`on_created_soundeffect` — we've bundled no third-party asset of any kind —
so this specific risk doesn't currently apply to us. Keep it that way (see
constraints below).

Before removal, it had (as of its last-visible state): **1,694 subscribers,
8,937 unique visitors, 95 favorites**, posted Nov 11 2022 (three weeks after
Vic3's Oct 2022 launch) and last updated Dec 5 2022.

## Realistic download/subscriber expectations

The Victoria 3 Steam Workshop holds roughly **10,585 items** total (snapshot
2026-09-03) — a mature, crowded, long-tail library four years post-launch.
The one data point we have (1.7k subscribers) came from a mod published
during launch-month hype, when Workshop browsing traffic was at its peak —
not a representative baseline for a mod published now.

**Takeaway:** don't anchor expectations on that number. A QoL/notification
mod released today, with no promotion beyond the Workshop page itself, more
realistically lands in the tens-to-low-hundreds of subscribers unless it's
cross-posted (Reddit r/victoria3, Discord, a YouTube mod-spotlight) or fills
a gap enough people are actively searching for.

## Steam Workshop rules (Valve, applies to all Workshop-enabled games)

- You must certify the content is your own work or something you have the
  right to distribute — no infringing on the game publisher's or any third
  party's IP.
- No hate speech, discriminatory material, sexual/pornographic content, or
  real/disturbing depictions of violence.
- No depictions of real political, controversial, or religious figures/events
  used for harassment.
- No exploits, backdoors, elevated-access tricks, or anything that crashes or
  forces other players' clients/connections.
- Prohibited/mature content must be marked with Steam's content descriptors
  if included at all (not relevant to a notification-tuning mod).

## Paradox's Mod/UGC Policy (authoritative: [legal.paradoxplaza.com/mod-policy](https://legal.paradoxplaza.com/mod-policy))

- **Non-commercial only**, and UGC "shall not contain any material which is
  unlawful, infringing, inappropriate, or violates any contracts or common
  sense."
- **Must be free and freely available — no paywalls.** Donations (Patreon or
  similar) are explicitly allowed.
- **Third-party IP is entirely our responsibility** — Paradox "is not always
  the owner of the intellectual property" and won't vouch for anything we
  include that isn't ours or vanilla's.
- We keep rights only to "the new, original content you create" (our own
  script/localization text); by publishing, we grant Paradox a nonexclusive,
  royalty-free, sublicensable, irrevocable, perpetual license to use,
  reproduce, modify, and commercially exploit it — standard for Paradox UGC,
  no special action needed on our part.
- **No attribution or compensation is owed to us**, and Paradox can restrict
  or remove our mod at their sole discretion.

## Concrete constraints this sets for our mod

- [ ] **Never bundle third-party assets** (audio, images, fonts) we don't
      have clear rights to. Every asset reference in our files should point
      at something already in the vanilla game (as all our current
      `texture`/`on_created_soundeffect` entries do) or something we made
      ourselves from scratch.
- [ ] **Never monetize** — no paid tiers, no "unlock via purchase." Donation
      links (Patreon, Ko-fi) are fine if we ever want them, separate from the
      mod itself.
- [ ] Keep the Workshop page description/tags professional and apolitical —
      not a functional risk for this mod's scope, but cheap insurance against
      a Code-of-Conduct dispute.
- [ ] Don't rely on Paradox/Steam to explain a takedown if one ever happens —
      as seen above, the page just shows boilerplate. Keep our own git
      history (this repo) as the record of what we shipped and why, so we're
      not solely dependent on the Workshop page surviving.

## Confirmed 2026-09-08: `common/messages/00_messages.txt` is a full-file override, not additive

Checked directly (diffed our copy against vanilla's own file) before
writing the Workshop compatibility text: our file is a **complete copy**
of vanilla's `00_messages.txt` (202 top-level message definitions, same
count as vanilla) with our own notification-tuning changes applied
in-place throughout — not a small additive file the way
`common/alert_types/` works. This is by design (Phase 1's whole premise),
but it has a real compatibility consequence worth remembering at every
future release: **any other mod that also fully replaces this same file
will silently conflict** — last-loaded wins for the entire file, with no
merge of the two mods' changes. Document this in the Workshop page's
Compatibility section every time it's updated, and re-check this file
against vanilla's latest copy after any Victoria 3 patch that touches
notification defaults (a patch could add new messages we'd otherwise be
silently missing, since our copy doesn't inherit vanilla's own updates
automatically).
