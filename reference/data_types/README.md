Engine data-type dump — the authoritative list of datafunctions
===============================================================

**What this is:** Victoria 3's own dump of every registered data type and
datafunction. **The user generated it on 2026-09-14** by launching the game in
debug mode and dumping the data types from the console; the game wrote it to
`Documents/Paradox Interactive/Victoria 3/logs/data_types/`. Snapshotted here
2026-09-18 (game 1.13), because the `logs/` folder rotates and this is too
useful to lose.

**It does not appear on its own.** Nobody gets this by playing normally — it
costs a debug-mode launch, so treat the snapshot as a scarce asset rather than
something regenerable on a whim.

**Why it matters:** this repo has spent multiple playtests answering "is
`X.Y` a real function?" by trying it and reading `error.log`. That question is
answerable here, instantly, with `grep`. The dump existed for four days before
any session thought to look at it — the miss was not that it was missing, but
that nobody checked.

```bash
# does this function exist at all?
grep -rn "^State.GetNameNoFormatting$" reference/data_types/

# everything a type exposes, including what vanilla never calls
grep -oE "^MapListOption\.[A-Za-z_]+" reference/data_types/data_types_uncategorized.txt | sort -u

# every global function matching a concept
grep -hoiE "^[A-Za-z_]*DataModel[A-Za-z_]*" reference/data_types/*.txt | sort -u
```

The last one is the worked example. Asked on 2026-09-18 whether the build-all
button could count only the *buildable* states rather than the listed ones, it
returned the engine's entire datamodel API — `DataModelFirst`,
`DataModelHasItems`, `DataModelLast`, `DataModelRepeatedItem`,
`DataModelSkipFirst`, `DataModelSkipLast`, `DataModelSubSpan`,
`GetDataModelSize`, `IsDataModelEmpty` — and nothing that folds a predicate
over a datamodel. Combined with a variable system that has no arithmetic
(`Clear`, `Exists`, `HasValue`, `Set`, `SetIf`, `Toggle`), that settles the
feature as impossible in GUI, in one grep, with no playtest.

## How to read it

Flat records separated by `-----`:

```
MapListPanel.AccessValidOptions
Definition type: Function
Return type: [unregistered]
```

Five files. `data_types_script.txt`, `data_types_gui.txt` and
`data_types_common.txt` are the categorised ones;
`data_types_uncategorized.txt` is the bulk of the game's own types and is
usually the one you want.

## The one important limitation

**Absence is conclusive. Presence is not.**

If a function is not in this dump, it does not exist and no amount of trying
will make it work. But a function that *is* here can still fail in a given
context, because this engine has more than one function table (CLAUDE.md § 3,
"two separate function tables" — a `.gui` binding and script-side `[...]`
dynamic text are not the same namespace).

The worked example, again from 2026-09-18: `Country.GetName` **is** in this
dump, yet calling it from script-side dynamic text errors outright with
"Could not find data system function" — which is why CLAUDE.md § 3 mandates
`GetNameNoFormatting`. So:

- **not in the dump** → settled, do not spend a playtest on it;
- **in the dump** → it exists somewhere; whether it works *here* still needs
  the usual precedent (another call of the same kind) or a test.

## Regenerating

Costs a debug-mode game launch by the user, so ask rather than assume. Re-dump
after a game patch and re-copy: a stale dump is worse than none, because
"absence is conclusive" quietly stops being true. The snapshot above is 1.13,
and `supported_game_version` in each mod's `metadata.json` is the thing to
check it against.

Launch in debug mode, open the console with `~`, and run:

    dump_data_types

That writes the five files above. **While you are in there, also run:**

    script_docs

which prints the script-side documentation -- the effects, triggers and
scopes list. That is the other half of this repo's recurring question, since
`dump_data_types` covers the dynamic-text/GUI function tables but not script
syntax. Not captured yet as of 2026-09-18; grab it on the next debug launch.

Other dump commands that exist and may be worth a pass if a question ever
needs them: `exportbuildings` (all building type info),
`create_state_region_data`, `create_building_history`, `debugstates`,
`debugmarkets`. Source: the Victoria 3 wiki's console-commands page.
