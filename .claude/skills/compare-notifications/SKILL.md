---
name: compare-notifications
description: Diff this mod's notification defaults against vanilla and the current player's live override file, per notification group. Slash-command only.
disable-model-invocation: true
---

Run:

```
python tools/compare_notification_settings.py
```

from the repository root. Prints, per notification `group`, any
disagreement between vanilla's script default
(`reference/vanilla/<version>/common/messages/*.txt`), this mod's current
default (`common/messages/*.txt`), and the player's live override
(`Documents/Paradox Interactive/Victoria 3/messagetypes_custom.txt`), if
one exists.

Pass `--all` to print every group instead of only disagreements:

```
python tools/compare_notification_settings.py --all
```

Never loads these files into context directly — this is a plain
regex-based parser with small, structured output (see the script's own
docstring and CLAUDE.md § Token Budget & Large File Protocol).
