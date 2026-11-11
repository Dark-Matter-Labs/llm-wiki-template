---
name: metacognition
description: "How the owner uses the wiki and where the loop costs them. Fires when a month has more repairs than rebuilds, about every 25 log entries, or after more than two self-corrections. \"how am I using this\"."
---

# Metacognition — how the owner uses the tool

This looks at the *use* of the wiki, not its content: the shape of the owner's working loop, and where
it costs them time or quality.

## Read
- Git history: commit cadence, iteration loops on the same file (repeated commits to one page),
  retitling events (`git log --follow`, diffs where the H1/title changes), branch/PR rhythm.
- the log (`wiki/log/YYYY-MM-DD.md`, day files indexed by `wiki/log/YYYY-MM.md`): the sequence and type of operations.

## Name the observed pattern
State the working loop you actually see. The known baseline, from the owner, is:

> small input → drive → systemic correction → redrive → correct → redrive (~5 iterations) →
> retitle → publish → integrate external comments.

Check whether that is still the dominant loop, and **name its cost** — e.g. "the systemic
correction at ~iteration 3 is the same correction most weeks; it's paid for five times."

## Suggest improvements
Concrete, not generic. The canonical example:
> "front-load the systemic constraint you always correct at step 3 into the first prompt."

Then **flag candidate patterns for the `learn` skill** — recurring, stable loops that could become a
verified skill. Don't create the skill here; hand the candidate to `learn` (which will ask the owner to verify).

## Output
In-chat by default. On request ("file it", "save the metacognition"), write to
`wiki/reflections/meta-<date>.md` (`type: synthesis`, `visibility: unlisted`) and log it.

## Epistemics (state this in the output)
- What git/log show — cadence, iteration counts, retitles — is **evidence**.
- *Why* the owner works that way — motivation, intent — is **inference**. Label it as inference; don't
  assert a motive as if it were logged fact.

## Rules
- Describe the loop; don't judge the person. The aim is a cheaper, sharper loop, not a report card.
- Never silently turn an observation into a skill — that is `learn`'s job, and it requires the owner's verification.
