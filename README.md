# Victoria 3 mods

One repo, one folder per mod, shared tooling.

| folder | mod | status |
|---|---|---|
| [`smart_notifications/`](smart_notifications/) | **Smart Notifications** — an EU4-style country watchlist, less notification noise, and new alerts including one that names the exact law worth enacting | published, [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3799284646) |
| [`bulk_construction/`](bulk_construction/) | **Build All: Bulk Construction, One Click** — one button queues a building in every state the construction panel is showing, at normal cost through the normal government queue | working, not yet published |

Each mod folder is self-contained — its own `.metadata/`, its own script
directories, and its own README, changelog, backlog and Workshop assets. A
folder here is exactly what gets published, and nothing else.

Shared across all of them: `tools/` (validation, packaging, log scanning,
screenshots), `docs/` (engine notes and per-mod specs), `reference/` (pristine
vanilla snapshots for diffing), `.claude/` (skills).

## Working on these

Agent protocol and the rules that matter: [CLAUDE.md](CLAUDE.md). The "why"
behind each rule, and everything confirmed the hard way about this engine:
[docs/engine-notes.md](docs/engine-notes.md).

```bash
python tools/validate_syntax.py --strict            # every mod
python tools/validate_syntax.py bulk_construction   # just one
```

```bash
python tools/package_release.py smart_notifications
```

The mod argument to `package_release.py` is required, and you upload from the
`<mod id>_release` folder it writes — never from the dev junction.
