# Vanilla baseline snapshots

This folder holds **untouched, pristine copies** of vanilla game files, mirrored under
the same relative path they have inside the game install (e.g.
`1.13.x/common/messages/00_messages.txt` corresponds to
`.../Victoria 3/game/common/messages/00_messages.txt`).

Purpose: let us diff our mod files against what a fresh install actually ships,
without ever guessing or re-reading the vanilla file into an LLM context window
(see the Large File Protocol in `CLAUDE.md`).

## Folder naming

One subfolder per supported game version (e.g. `1.13.x`). Bump/add a new one
whenever the mod starts tracking a new major patch, and keep old ones only if
still relevant — otherwise delete them.

## How to refresh a snapshot (only when the game patches)

```bash
cp "/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/common/messages/00_messages.txt" \
   "reference/vanilla/1.13.x/common/messages/00_messages.txt"
```

Adjust the install path if Steam is installed elsewhere. Do this only right
after a game update, and only intentionally — never as a side effect of
another task.

## How to compare our mod file against vanilla

Never `Read`/`cat` the whole file to compare by eye. Use `diff`, which only
surfaces the changed lines:

```bash
diff -u "reference/vanilla/1.13.x/common/messages/00_messages.txt" \
        "common/messages/00_messages.txt"
```

Or, to see it against what the currently installed game ships right now
(useful right after a patch, before refreshing the snapshot above):

```bash
diff -u "/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/common/messages/00_messages.txt" \
        "common/messages/00_messages.txt"
```

Every entry in `common/messages/00_messages.txt` that we've deliberately
changed from vanilla should carry an inline `#` comment explaining why (see
existing examples tagged `Project 1 (Quiet Feed & Dominion War Mute)`), so a
future diff is self-explanatory without needing this file at all.
