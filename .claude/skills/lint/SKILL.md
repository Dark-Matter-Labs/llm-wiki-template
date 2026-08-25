---
name: lint
description: Run a health check over the wiki. Use when the owner says "check the wiki", "is it healthy", "clean up", "what's stale", or periodically after several ingests. Finds contradictions, stale claims, orphan pages, missing pages, missing cross-references, and schema problems, then produces a report. Never deletes or rewrites content unilaterally.
---

# Lint the wiki

A wiki rots when maintenance lags. This pass keeps it healthy. You **report and
propose**; you do not delete pages or rewrite content without the owner's approval. You
MAY fix frontmatter metadata when the correct value is unambiguous.

## Checks (run in order)

1. **Schema integrity.** Find pages missing required frontmatter fields (`type`,
   `title`, `description`, `tags`, `status`, `confidence`, `timestamp`, `sources`).
   Repair where the correct value is certain; flag where it's uncertain.

2. **Staleness / contradiction.** Surface the oldest pages by `timestamp`. For each,
   check whether newer sources now contradict or supersede it. Flag; propose specific
   updates; don't apply unilaterally. Pay special attention to `confidence: low` pages —
   they most need re-examination as sources accumulate.

3. **Coverage gaps.** Scan pages for things mentioned repeatedly (people, orgs,
   concepts, tools) that lack their own page. List them; don't auto-create.

4. **Overview drift.** Compare `wiki/overview.md`'s timestamp against the newest pages.
   If it lags by more than one ingest cycle, flag it as drifted and propose the update.

5. **Orphans.** Find pages with zero inbound `[[links]]`. Suggest which existing pages
   should link to them.

6. **Duplicates.** Find pages with near-identical titles or content. List them for
   the owner to approve a merge. Never merge or delete without approval.

7. **Dormancy candidates.** Run `python3 tools/staleness.py --older-than 42 --json` and cross it
   with the graph. A candidate is **all three** of: body untouched for the threshold,
   `confidence: low`, and one inbound link or fewer. Report them; never set `status: dormant`
   yourself.

   **State the baseline before the count.** The threshold only means something once repo history
   substantially exceeds it — in a young wiki "untouched 42 days" means "arrived in the first
   bulk ingest", which is youth, not death. If history is under about twice the threshold, say
   the pass is not yet informative rather than presenting a list.

## Output

Produce a plain-language report:

```
# Wiki health check — YYYY-MM-DD
Overall: 🟢 healthy / 🟡 needs attention / 🔴 problems

1. Schema — …
2. Staleness & contradictions — …
3. Coverage gaps — …
4. Overview drift — …
5. Orphans — …
6. Duplicates — …

Suggested next steps (which need your approval):
1. …
```

Then append `## [YYYY-MM-DD] lint | <one-line status>` to the current month's log file (`wiki/log/YYYY-MM.md`; see `wiki/log.md`).

## Hard rules
- Never delete a page without explicit approval.
- Never rewrite page *content* in a lint pass — only repair unambiguous frontmatter.
- Flag, propose, wait.
