# Log — index

The dated record of everything that happens in this wiki: every ingest, query, lint pass,
brief, reflection, and rebuild.

**The entries themselves live in one file per day**, at `wiki/log/YYYY-MM-DD.md`, with
`wiki/log/YYYY-MM.md` as that month's **index**. The split exists for a practical reason: a
single append point is the biggest source of merge conflicts when more than one session is
running. A monthly file still collides every time two sessions work on the same day, which
is the common case — daily files make that impossible too.

## Rules

- **Append** new entries to **today's file**, creating it if it is the day's first entry, then
  run `python3 tools/sync_log_index.py` — it regenerates the month index from the day files,
  so the row is never hand-typed and never forgotten.
- **Never rewrite a past day.** Corrections are appended as new entries, not edits — the
  log is a record of what happened, including what was got wrong.
- To read "the log", read **today's file first**, then walk back through the month index.

## Entry format

Each entry starts with a consistent prefix so the log stays greppable:

```
## [YYYY-MM-DD] ingest  | Source Title
## [YYYY-MM-DD] query   | The question asked
## [YYYY-MM-DD] lint    | Health check
## [YYYY-MM-DD] rebuild | Derived-artifact build/rebuild
```

## Months

- [2026-08](log/2026-08.md)
