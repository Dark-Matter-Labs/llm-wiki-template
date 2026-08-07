# Log — index

The dated record of everything that happens in this wiki: every ingest, query, lint pass,
brief, reflection, and rebuild.

**The entries themselves live in one file per month**, at `wiki/log/YYYY-MM.md`. That split
exists for a practical reason: a single log file is the single biggest source of merge
conflicts when more than one session is running, because every session appends to the same
last line. Monthly files make same-day collisions rare and cross-month collisions impossible.

## Rules

- **Append** new entries to the **current month's file**, creating it if the month is new,
  and add the new month to the list below.
- **Never rewrite a past month.** Corrections are appended as new entries, not edits — the
  log is a record of what happened, including what was got wrong.
- To read "the log", read the **current month first**, then earlier months as needed.

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
