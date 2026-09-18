Engine data-type dump — the authoritative list of datafunctions
===============================================================

**What this is:** Victoria 3's own dump of every registered data type and
datafunction, written by the game itself into
`Documents/Paradox Interactive/Victoria 3/logs/data_types/`. Snapshotted here
2026-09-18 from a dump the game wrote on 2026-09-14 (game 1.13). Copied into
the repo because the `logs/` folder is rotated and cleared, and this is too
useful to lose.

**Why it matters:** this repo has spent multiple playtests answering "is
`X.Y` a real function?" by trying it and reading `error.log`. That question is
answerable here, instantly, with `grep`.

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

The game writes these in debug mode. Re-dump after a game patch and re-copy;
a stale dump is worse than none, since "absence is conclusive" stops being
true. The snapshot above is 1.13.
