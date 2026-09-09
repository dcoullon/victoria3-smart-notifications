# Vanilla baseline snapshots

This folder holds **untouched, pristine copies** of vanilla game files, mirrored under
the same relative path they have inside the game install (e.g.
`1.13.x/common/messages/00_messages.txt` corresponds to
`.../Victoria 3/game/common/messages/00_messages.txt`).

Purpose: let us diff our mod files against what a fresh install actually ships,
without ever guessing or re-reading the vanilla file into an LLM context window
(see the Large File Protocol in `CLAUDE.md`).

## Every full-file override this mod ships needs a snapshot here

Confirmed real gap, found 2026-09-09: this folder only ever tracked
`common/messages/00_messages.txt`, even though this mod also fully
overrides two `.gui` files (`gui/message_settings.gui`,
`gui/politics_panel_change_law.gui`). A future Victoria 3 patch changing
either of those would go completely unnoticed -- our override would
silently keep shipping whatever it had, discarding Paradox's own
changes, with no automated signal that drift had happened. Every file
this mod fully overrides (not the additive ones under
`common/on_actions/`, `common/alert_types/`, etc. -- those never shadow
a same-named vanilla file at all) needs its own snapshot here, kept in
sync the same way. `tools/check_references.py`'s
`check_full_overrides_match_installed_vanilla` now checks this
automatically against whatever Victoria 3 install it finds locally.

## Folder naming

One subfolder per supported game version (e.g. `1.13.x`). Bump/add a new one
whenever the mod starts tracking a new major patch, and keep old ones only if
still relevant — otherwise delete them.

## How to refresh a snapshot (only when the game patches)

```bash
cp "/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/common/messages/00_messages.txt" \
   "reference/vanilla/1.13.x/common/messages/00_messages.txt"
cp "/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/gui/message_settings.gui" \
   "reference/vanilla/1.13.x/gui/message_settings.gui"
cp "/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/gui/politics_panel_change_law.gui" \
   "reference/vanilla/1.13.x/gui/politics_panel_change_law.gui"
```

Adjust the install path if Steam is installed elsewhere. Do this only right
after a game update, and only intentionally — never as a side effect of
another task. Run `python tools/validate_syntax.py` right after refreshing
these — it will now flag whether any of our full-file overrides have fallen
out of sync with the new vanilla content, so the same command that already
catches everything else also catches this.

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
