---
name: reflect
description: Weekly reflection on how the thinking deviated. Use when the owner says "run the weekly reflection" or "what deviated this week". Also runs automatically on the Friday schedule. Reads the log and git history since the last reflection and files a structured reflection to wiki/reflections/.
---

# Reflect — weekly deviations of thought

A standing weekly look at **how the thinking moved** — what shifted, what it connects to, what
early signals bear on it, and what the owner kept correcting. The format is fixed on purpose:
reflections from different people's wikis will later be compared, so **keep the six sections and
their order stable.**

## Read (the window)

- log entries since the last reflection (`wiki/log/YYYY-MM.md`; index at `wiki/log.md`) (find the previous `## [YYYY-MM-DD] reflect` entry;
  if none, use the last 7 days).
- Git history for the same window: `git log --since=<date> --stat` and diffs of `wiki/` pages
  (`git log -p -- wiki/`), so you see *what actually changed*, not just what the log claims.
- The pages touched in that window (read the current state of the ones that changed most).

## Produce `wiki/reflections/YYYY-'W'WW.md`

Frontmatter: `type: synthesis`, `visibility: unlisted` (so it can appear on the interface without
being publicly indexed), `title: "Weekly reflection — YYYY-Www"`, timestamp, tags `[reflection, weekly]`.

Body — **exactly these sections, in this order:**

1. **Deviations of thought** — up to 10. For each: what shifted, *from what, to what*. Cite the pages (`[[links]]`).
2. **Connections to the wider world** — what each deviation connects to outside the wiki. Web search
   is allowed here; **keep wiki-knowledge and web-knowledge clearly separated** (label which is which).
3. **Early signals** — weak signals supporting *or* undermining each deviation. Honest about strength.
4. **Counterpositions** — invoke the `joker` method briefly per major deviation (one rival orthodoxy
   each, not a full brief). Link any full `joker` briefs that already exist.
5. **Reinforcement patterns / gravitational corrections** — what did the owner repeatedly correct this week?
   A recurring correction is a **gravity worth naming**: say plainly whether it means the *schema needs
   updating* or an *assumption is being resisted* — and which.
6. **Suggested attention** — max 3 items for next week.

## After writing
File it, add it to `index.md`, and log `## [YYYY-MM-DD] reflect | week YYYY-Www`.

## Rules
- Keep the six-section format stable and named exactly — it is a shared contract across wikis.
- Deviations are movements, not verdicts: describe the shift, don't grade the person.
- Default `visibility: unlisted`; confirm with the owner if a given week's reflection should be public or private.
- Evidence discipline: what git/log show is evidence; what it *means* is inference — label inference.
