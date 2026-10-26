<!-- Moved word for word from CLAUDE.md on 2026-10-13 so it is read when needed, not on every turn.
     CLAUDE.md keeps every rule as a short line and points here for the reasons and the detail. -->

# The index and the log in full

Read this before editing `wiki/index.md`, a shelf, or the log.

## The two navigation files

**`wiki/index.md`** — the **router**, not the catalogue. Sections, counts, and a pointer
to each shelf. The heavy catalogues live under **`wiki/index/`** — `concepts.md`,
`summaries.md`, `overview-synthesis.md` — and are loaded one at a time, only when a
question is squarely in that section.

Tiered on 2026-08-23. `index.md` had reached ~55k tokens and was read before every
operation, against a corpus whose median page is ~1.5k: routing cost more than reading
thirty pages, and the map was growing as fast as the territory. The router is now ~9k.

**Retrieval order — search, then graph, then read:**

1. `python3 tools/search.py "<question>" --top 12` — ranks title/tags/description above
   body, so the top hits are the pages the question is *about*. ~1k tokens.
2. `export/wiki.json` for the second hop — `inbound_links`/`outbound_links` make a page's
   neighbourhood a lookup rather than another search.
3. Read the shortlist in full.

**Never load pages in order to decide which pages to load.** Context is for reasoning over
candidates; traversal is for finding them. A query should touch well under 30k tokens of
corpus.

**You update the catalogues on every ingest** — a new page's row goes on its shelf, and the
counts on the router are computed by `tools/sync_index_counts.py`, never typed.

**`wiki/log.md`** — the log's **index**. The entries themselves live in **one file per day**
at **`wiki/log/YYYY-MM-DD.md`** (e.g. `wiki/log/2026-08-13.md`). **Append every new entry to
today's file**, creating it (with the same header as the others) if it is the day's first entry,
then run `python3 tools/sync_log_index.py` — it regenerates the month index at
`wiki/log/YYYY-MM.md` from the day files, so the new day's row is never hand-typed and never
forgotten (it was, twice, before this existed — see `wiki/log.md`). Never rewrite past days —
corrections are appended as new entries. To read "the log", read today's file first, then walk
back through the month index.

Per-day, not per-month, since 2026-08-13: a month file is one append point, so two sessions working
on the same day collide every time — that conflict was resolved by hand five times before the split.
July 2026 and earlier remain single month files and were not retrofitted.

Every ingest, query, and lint pass gets one entry. Start each entry with a consistent prefix so
it stays greppable:

```
## [YYYY-MM-DD] ingest | Source Title
## [YYYY-MM-DD] query  | The question asked
## [YYYY-MM-DD] lint   | Health check
## [YYYY-MM-DD] rebuild | Derived-artifact build/rebuild (e.g. the SRPM, a published page)
## [YYYY-MM-DD] repair  | A defect fixed — the artifact restored, not advanced
```

**`rebuild` vs `repair` — the distinction matters, so keep it honest.** A `rebuild` *advances* the
artifact: a new version, a new capability, content it did not carry before. A `repair` *restores* it
to what it should already have been: a regression, a record lost in a previous rebuild, a wrong
figure, a broken link, a defect an audit found. Work that does both is logged as `rebuild`, with what
it repaired named inside the entry.

The point of the split is that **the correction rate becomes visible without a metacognition pass**.
So say plainly whose defect it was — a repair of the model's own earlier error reads `repair | …
(mine)`. A high repair count is not a failure; a repair count hidden inside `rebuild` is. Split
proposed by the 2026-08-13 metacognition pass and adopted the same day, when 74 of August's 184
entries were `rebuild` and nobody could tell how many were advances.
