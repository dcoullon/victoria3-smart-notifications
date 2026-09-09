---
name: scan-logs
description: Filter Victoria 3's error.log/debug.log for this mod's own debug_log output and known engine-error signatures, without dumping full logs into context. Slash-command only.
disable-model-invocation: true
---

Run:

```
python tools/scan_logs.py
```

from the repository root. Scans `error.log` and `debug.log` in the
default Victoria 3 logs directory
(`Documents/Paradox Interactive/Victoria 3/logs`) for:

- This mod's own tagged `debug_log` lines (`SNW_<NAME>|...`).
- Known engine-error signatures this project has hit before (see
  docs/engine-notes.md) — "Could not find data system function", "Could
  not find promote for", "This scope doesn't support variables", "Data
  error in loc string", "Promote 'GetScriptedGui' returned nullptr",
  "Unknown effect", "Failed to convert statement", missing-BOM warnings.

Options:

```
python tools/scan_logs.py --lines 50           # more lines per category
python tools/scan_logs.py --logs-dir <path>    # a beta tester's own logs folder
```

Never prints a raw log file — only matching lines, most-recent-first, per
CLAUDE.md § Token Budget & Large File Protocol. Use `--logs-dir` when a
beta tester shares their own log files for a bug report instead of
pasting a screenshot.
