---
name: validate-mod
description: Run this repo's static validator (syntax, encoding, known mistake patterns, cross-file references) over the mod's script/loc files. Slash-command only.
disable-model-invocation: true
---

Run:

```
python tools/validate_syntax.py
```

from the repository root. This runs both `validate_syntax.py` (bracket
balance, UTF-8 BOM, known-good regression invariants, known mistake
patterns) and `tools/check_references.py` (undefined `custom_tooltip` loc
keys, misplaced `scripted_gui` definitions, unregistered `alert_group`s,
missing alert loc keys, law-type-list drift), which it calls
automatically.

Report the PASS/FAIL output verbatim. On FAIL, fix the reported issues
before considering any change finished — per CLAUDE.md § Autonomous
Quality Assurance, this is already run after every file edit as standard
practice; this skill exists for a human to invoke it directly between
agent turns.
