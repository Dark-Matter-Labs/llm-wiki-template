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

- log entries since the last reflection (`wiki/log/YYYY-MM-DD.md` day files; month index `wiki/log/YYYY-MM.md`) (find the previous `## [YYYY-MM-DD] reflect` entry;
  if none, use the last 7 days).
- Git history for the same window: `git log --since=<date> --stat` and diffs of `wiki/` pages
  (`git log -p -- wiki/`), so you see *what actually changed*, not just what the log claims.
- The pages touched in that window (read the current state of the ones that changed most).

## Produce `wiki/reflections/YYYY-'W'WW.md`

Frontmatter: `type: synthesis`, `title: "Weekly reflection — YYYY-Www"`, timestamp,
tags `[reflection, weekly]`, and a `visibility` that depends on which kind of wiki this is:

- **A personal wiki** → `unlisted`. It can appear on the interface without being publicly indexed.
- **A commons** (`xco-team-wiki`, `learning-system-wiki`, `power-project-wiki`) → `internal`, the cut
  every member reads. `unlisted` would push it into the public export, which in a commons carries
  nothing on purpose. A reflection here is a shared record, not a private notebook: it describes how
  the group's thinking moved, and members who read only this repo are among its readers.

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
   **Then check the corpus's own named highest-risk axiom for drift** (`wiki/axioms.md`, where the
   wiki keeps one; skip the check and say so where it does not). In this federation the standing
   example is **A1**, named 2026-08-20: did any stream, goal, commitment page or answer this week get
   framed as an action/task list with no live question behind it, rather than as a Goal/Target/Search
   inquiry? That is the named highest-risk default — the natural pull is toward writing actions, and
   doing so defeats the system's own operating logic. Say plainly whether it happened, **even if the
   answer is "no drift found"** — a clean week is worth recording, not just a caught one.
   *(Contributed upstream from michelle-llm-wiki, 2026-09-04 — the first change to travel spoke-to-source.)*
6. **Suggested attention** — max 3 items for next week.

### Then, after the six — "Eligible to contribute"

**This is not a seventh section.** The six above are a fixed contract compared across
wikis; this is a standing block appended after them, and comparison tooling should ignore it.

Run `python3 tools/contribution_prompt.py --markdown` and paste the output under an
`## Eligible to contribute` heading. That is the whole job.

Why it is here at all: the federation's down-flow got a daily cron and the up-flow got three
consent gates and no cadence, so on 19 Aug 2026 the commons held one contributed page while a
spoke sat on nine eligible ones — not because anyone declined, but because nobody was ever asked.
The reflection already runs weekly and already knows what changed, so it is the cheapest place to
put the question in front of a person.

Three things this block must never become:

- **It names candidates and stops.** Do not run `contribute.py`, do not stage a bundle, do not
  open a PR. Every consent gate stays where it is. If the week's work makes one page obviously
  worth sharing, say so in prose — and still leave the moving to a person.
- **It reports on this wiki only.** Never on what anyone else has or has not contributed. That
  would be activity-tracking, which the constitution forbids, and it would turn a prompt into a
  scoreboard.
- **It never invents certainty.** If the tool says overlap is unknown (no cached commons export),
  paste that as written. "Cannot check" is the useful answer; a number that reads as a gap when
  it is not would train people to ignore the block.

### And, where this wiki has `tools/verification.py` — "Claims awaiting verification"

Also **not a seventh section**, and also outside the compared contract. Run
`python3 tools/verification.py --sample 3` and paste the output under a
`## Claims awaiting verification` heading. Three unverified claims, one per page, weighted toward the
pages most linked to and already validated — the ones a misquote would do the most damage in. The
reflection is the cheapest weekly place to put three citations in front of the person who can check
them. Skip the block, and say so, where the tool is absent: it lives in the source wiki first and
travels once it has been used on real pages.

Two things this block must never do: **write a mark** — `{✓ …}` is a person's signature, and a model
writing it is the shortcut the whole layer exists to refuse — or **pad the three to more**. Three a
week is a habit; a backlog is a refusal.

## After writing
File it, add it to `index.md`, and log `## [YYYY-MM-DD] reflect | week YYYY-Www` in today's
day file (`wiki/log/YYYY-MM-DD.md`), then run `python3 tools/sync_log_index.py` so the month
index picks it up. The index is regenerated, never hand-typed.
*(Contributed upstream from learning-system-wiki, 2026-09-04.)*

## Rules
- Keep the six-section format stable and named exactly — it is a shared contract across wikis.
  "Eligible to contribute" sits outside that contract and does not count as a seventh.
- The contribution block never moves a page. Naming is the whole of it.
- Deviations are movements, not verdicts: describe the shift, don't grade the person.
- Default `visibility: unlisted` in a personal wiki, `internal` in a commons (see above); confirm
  with the owner if a given week's reflection should be public or private.
- Evidence discipline: what git/log show is evidence; what it *means* is inference — label inference.
