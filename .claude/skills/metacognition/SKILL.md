---
name: metacognition
description: "How the owner uses the wiki and where the loop costs them. \"how am I using this\", \"usage patterns\", or when coach suggests it."
---

# Metacognition — how the owner uses the tool

This looks at the *use* of the wiki, not its content: the shape of the owner's working loop, and where
it costs them time or quality. `coach` suggests it when a month has more repairs than rebuilds in the log.
Offer it yourself after more than two self-corrections in one session.

## Read
- Git history: commit cadence, iteration loops on the same file (repeated commits to one page),
  retitling events (`git log --follow`, diffs where the H1/title changes), branch/PR rhythm.
- the log (`wiki/log/YYYY-MM-DD.md`, day files indexed by `wiki/log/YYYY-MM.md`): the sequence and type of operations.
- Artifacts built from the wiki: shareable pages, decks, published pages, and the review and comments they drew.
  **Building an artifact counts as asking the wiki.** People often ask what the wiki knows by building something
  from it, which others then review and comment on. That loop belongs in the picture, not only queries.

## Name the observed pattern
State the working loop you actually see. Read the baseline from this wiki's own log and git history, not
from another wiki. If an earlier metacognition page exists here, compare with it. As an example of the shape
only, Indy's loop in his own wiki was:

> small input → drive → systemic correction → redrive → correct → redrive (~5 iterations) →
> retitle → publish → integrate external comments.

Check whether this wiki's loop has held or changed, and **name its cost** — e.g. "the systemic
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
