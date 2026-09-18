Smart Notifications
===================

A Victoria 3 mod living in this repo alongside `bulk_construction/` and
Build All. Own `metadata.json`, own mod id
(`smart_notifications`), own Workshop entry. It shares this repo's `tools/`,
`docs/` and `reference/` and follows the same CLAUDE.md protocol.

**Published:** [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3799284646).
Current dev version `0.40`, targeting game `1.13.*`.

**What it does:** less notification noise, an EU4-style watchlist for the
countries you actually care about, and new alerts — including one that names
the exact law worth enacting. Every message this mod adds or re-tunes stays
under the game's own Message Settings, so anything here can be turned back off
without uninstalling.

Its own documents, in this folder:

- [CHANGELOG.md](CHANGELOG.md) — what shipped, per version, in players' words.
- [TODO.md](TODO.md) — the living backlog: planned, in progress, open
  questions. Forward-looking only; closed narrative moves to
  [docs/archive/](../docs/archive/2026-09-session-log.md).
- [STORE_ASSETS_GUIDE.md](STORE_ASSETS_GUIDE.md) — the Workshop listing's
  visual assets, none of which an agent can produce.
- [STEAM_WORKSHOP_DESCRIPTION.bbcode](STEAM_WORKSHOP_DESCRIPTION.bbcode) — the
  listing text itself.

Shared documents worth reading before changing anything here: the agent
protocol in [CLAUDE.md](../CLAUDE.md), everything confirmed the hard way about
this engine in [docs/engine-notes.md](../docs/engine-notes.md), and the
watchlist design in [docs/watchlist-spec.md](../docs/watchlist-spec.md).

Validate with:

    python tools/validate_syntax.py smart_notifications

Package a release with — never upload the dev junction:

    python tools/package_release.py smart_notifications
