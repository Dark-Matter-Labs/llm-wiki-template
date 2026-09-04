---
name: rebuild-parity
description: Count a rebuilt artifact's records against the version it replaces, before it ships. Fires automatically whenever an artifact carrying a countable record set is rebuilt, reskinned, regenerated, ported to a new register, or split — atlas nodes, register rows, party records, watchpoints, portfolio entries, slides, table rows. Also on request ("did anything get lost", "check parity", "is it all still there").
---

# Rebuild parity — count what went in, count what came out

Rebuilds lose things. Not through carelessness about the whole, but because a rebuild re-derives an
artifact from an understanding of it, and any record the understanding didn't hold gets dropped
silently. Nothing errors. The page still renders. The loss is only found later, by someone reading
the old version alongside the new one.

This skill exists because that correction was paid for four times in one week
(`the lost canvas records carried forward`, `restore the enabling constraint as something that
binds`, `restore the dropped party records`, `carry the four canvas losses forward`) — every time,
because nobody counted. Verified as a pattern by Gurden, 2026-08-13.

## Method

1. **Name the record set before rebuilding.** What is the countable unit — nodes, rows, episodes,
   watchpoints, parties, slides, sources? Most artifacts have more than one; list each.

2. **Take the count and the ids from the version being replaced.** From the file as it is on disk or
   in git (`git show HEAD:path`), not from memory of it, and not from the summary of it. Prefer stable
   ids over positions.

3. **Take the same counts from the rebuild.**

4. **Diff by id and report in the open**, in the commit or the log entry:
   > `199 party records in, 199 out · 28 nodes in, 28 out · 63 sources in, 63 out`

   and if it is down:
   > `199 party records in, 194 out — missing: P-041, P-052, P-088, P-104, P-131`

5. **A count that is down blocks the ship** until either the records are restored or the drop is
   stated as a decision, with a reason, in the log. "I rebuilt it and it looks right" is not a reason.

6. **A count that is up is also a finding.** Records the source never had are inventions until
   sourced; say where they came from.

## Output

One line per record set in the commit message and the log entry — the counts, and the ids of anything
missing. When everything is level, say so explicitly; a silent pass is indistinguishable from not
having checked.

## Rules

- **Never report parity you did not compute.** Reading both versions and forming an impression is not
  a count.
- Count from the artifact, not from its documentation. The wiki page describing a model is not
  evidence about the model.
- Positions are not ids. If the record set has no stable ids, say so — that is itself the finding,
  and it means the next rebuild cannot be checked either.
- This is a completeness check, not a quality check. Parity says nothing about whether the rebuild is
  better; it says only that it did not quietly become smaller.
- Applies to splits and merges too, where it is easiest to check and easiest to get wrong: the
  2026-08-13 log split verified 184 entries in, 184 out, by content hash.
