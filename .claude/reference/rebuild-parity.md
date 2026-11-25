# Rebuild parity: count what went in, count what came out

Read this whenever an artifact with a countable set of records is rebuilt, ported, split or merged: a published
page, a lens, a model, a log. Also on "did anything get lost" or "check parity". `live-page`, `lens-refresh` and
`publish-web` point here.

Rebuilds lose things. A rebuild re-derives an artifact from an understanding of it, and any record the
understanding did not hold is dropped without a sound. Nothing errors and the page still renders. In August 2026
this correction was paid for four times in one week, every time because nobody counted.

## Method

1. **Name the record set before rebuilding.** What is the countable unit: nodes, rows, episodes, parties, slides,
   sources? Most artifacts have more than one. List each.
2. **Take the counts and the ids from the version being replaced.** Read the file on disk or in git
   (`git show HEAD:path`), not your memory or a summary of it. Prefer stable ids to positions.
3. **Take the same counts from the rebuild.**
4. **Compare by id and report it openly**, in the commit or the log entry:
   > `199 party records in, 199 out · 28 nodes in, 28 out · 63 sources in, 63 out`

   and if a count is down:
   > `199 party records in, 194 out — missing: P-041, P-052, P-088, P-104, P-131`
5. **A count that is down blocks the ship** until the records are restored, or the drop is logged as a decision
   with a reason. "I rebuilt it and it looks right" is not a reason.
6. **A count that is up is also a finding.** Records the source never had are inventions until sourced. Say where
   they came from.

## Output

One line per record set in the commit message and the log entry: the counts, and the ids of anything missing. When
everything is level, say so. A silent pass looks the same as no check.

## Rules

- **Never report parity you did not compute.** An impression from reading both versions is not a count.
- Count from the artifact, not from its documentation. The page describing a model is not evidence about the model.
- Positions are not ids. If the record set has no stable ids, say so. That is the finding, and it means the next
  rebuild cannot be checked either.
- This checks completeness, not quality. It says only that the rebuild did not quietly become smaller.
- Splits and merges count too. The 13 August 2026 log split checked 184 entries in and 184 out, by content hash.
