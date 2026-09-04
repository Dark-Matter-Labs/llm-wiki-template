---
name: delta
description: Measure the delta between an incoming document and the wiki's current position — where it agrees, extends, diverges, or contradicts, and by how much. Use when the owner says "run a delta", "measure this against the wiki", "where does this sit / move us", "diff this paper against our position", or before deciding whether/how to ingest a collaborator's paper, an external report, a page coming down from the centre, or another member's wiki page. A delta is a signal of movement, not a verdict; it informs, it never auto-merges.
---

# Delta — movement between a document and the wiki's position

A delta reads an **incoming document** against what this wiki **currently holds and assumes**, and
says where the two agree, extend each other, diverge, or contradict — and how far apart they sit.
**A delta is neither good nor bad; it is a signal of movement.** It routes attention and informs a
decision (ingest? push back? update an axiom?); it never decides, and never merges the incoming
position on its own.

It is the *position/contact* companion to the `gravity` skill (which measures the corpus's mass and
trajectory). `gravity eval` gives the trajectory read (ahead of / behind the motion); `delta` gives
the contact ledger (which pages and axioms it touches, and how). Use both when it matters.

## Steps

1. **Locate the incoming document.** A raw draft in `raw/`, an external report, a collaborator's
   paper, or another wiki's exported page — any file path. If a member pasted it, save it somewhere first
   (a raw/ file if it will likely be ingested, otherwise the scratchpad). Delta measures *before*
   ingest, so the document need not be in the wiki.

2. **Run the instrument** (deterministic, stdlib only) from the repo root:
   ```
   python3 .claude/skills/delta/compute_delta.py <path> [--top 8] [--axioms 5]
   ```
   It reports: `radial r` (alignment with the corpus mass), `novelty n` (distance to the nearest
   page), the **nearest pages** (the contact surface), the **axioms** it bears on, and its
   **distinctive pull** (top offset terms). Optionally also run `gravity eval <path>` for the
   ahead/behind-the-motion read. If it warns the file self-matches (~1.0), you're measuring a doc
   already in the wiki — use the raw/external original instead.

3. **Read the contact surface.** Actually open the top nearest pages and the touched axiom cards in
   [[Axioms Register]]. The numbers locate contact; only reading tells you its *kind*.

4. **Classify each meaningful contact** as one of — be specific about the exact claim/axiom touched:
   - **agree** — says what the wiki already holds (confirms the mass).
   - **extend** — builds beyond a held position in the same direction, without conflict (new
     territory the corpus was already moving toward).
   - **diverge** — a different emphasis, frame, or priority; not opposed, but a different heading.
   - **contradict** — directly opposes a held claim or an axiom. These are the precious ones —
     name them plainly; do not smooth them.
   (Rough correspondence to `gravity`: agree ≈ high-r/behind; extend ≈ ahead of motion;
   diverge ≈ orthogonal/novel; contradict ≈ drag against the motion.)

5. **Quantify the movement, without valorising either side.** How far does the incoming position sit
   from ours (novel vs on-corpus), and in which direction does it pull (from the offset terms +
   the classified contacts)? Say it plainly; do not grade the document as good or bad.

6. **Write the delta brief** to `wiki/deltas/<slug>-<YYYY-MM-DD>.md` (see structure below),
   `visibility: private` in a personal wiki, `internal` in a commons —
   in a commons `private` would hide it from the very people it is for; in a personal wiki
   `internal` would send it to the colleague mirror, a wider audience than this warrants.
   It is a reading of someone's material for the people who
   have to decide about it, and in this commons that is every member. It does not leave the repo:
   not to the open web, and not up to the centre without the `contribute` consent loop. If the
   document's author would object to *these* readers seeing your reading of it, that is a reason
   to raise it with them, not a reason to hide the brief from the group. Cite the document and the
   pages/axioms it touches with `[[links]]`.

7. **Never auto-merge.** If a contact suggests the wiki should move (a new axiom, a revised page,
   a flagged contradiction), **propose** it for a member to decide — the `ingest` skill does the merge, the
   `joker` skill argues the counter-case, the `reflect`/`gravity` skills track whether it moved the
   corpus. Delta only surfaces the movement.

8. **Log it.** Append `## [YYYY-MM-DD] delta | <document> vs the wiki` with a one-line reading to
   today's day file (`wiki/log/YYYY-MM-DD.md`), then run `python3 tools/sync_log_index.py`.

## Delta brief structure (keep stable — deltas will be compared across documents and, later, wikis)

```
# Delta — <document title> vs the wiki — YYYY-MM-DD
Source: <path/url>.  Position: r=<radial>, novelty=<n> — <one-line plain reading>.

## Contact ledger
- **[[Page or Axiom]]** — agree | extend | diverge | contradict — <the specific claim, one line>.
- …

## Net movement
Where the incoming position pulls (toward / away from what), and how far. Evidence = the terms and
classified contacts; inference = what it means — label which is which.

## If adopted (not a recommendation)
What would change in the wiki — pages to update, axioms to revisit, contradictions to resolve —
stated as consequences, not a decision.

## Open questions
What to verify, what the instrument can't see (paraphrase vs synonym), where a person must judge.
```

## Rules
- **A delta is movement, not a verdict.** Describe the shift; don't rank the document or the person.
- **Never auto-merge or auto-update** wiki content from a delta. It informs; a member (via `ingest`) decides.
- **Label evidence vs inference.** What the instrument and text show is evidence; what it means is inference.
- **Ordinal, under Rσ.** The numbers route attention; they certify nothing. Axiom cosines are tiny in
  absolute terms — read the *ranking*, not the value, and always confirm by reading the card.
- The stable brief format is deliberate — it's the unit a future multi-author phase compares across wikis.
