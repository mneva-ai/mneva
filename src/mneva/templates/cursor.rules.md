---
description: Run mneva preflight before responding to project-scoped requests
alwaysApply: true
---
# Mneva — Cursor rules
Mneva is a local-first cross-tool context layer. It captures decisions, constraints, and
state from any AI tool into `~/.mneva/` and replays them so each session starts with full
project state.

## Preflight
Before responding to any request that touches a known scope, run:

```
mneva replay --tool=cursor --scope=<scope>
```

Replace `<scope>` with the relevant project or module name (e.g. `mneva`, `mneva/api`).

## Output interpretation

The command prints a context block containing captured records for that scope.
Treat the block as authoritative project state: do not contradict decisions listed there,
do not re-litigate constraints already marked settled, and do not duplicate work already
marked complete.

## When to call

- On the first user message in a new Cursor session
- Before editing any file that belongs to a named scope
- When the user references a decision or constraint without context
