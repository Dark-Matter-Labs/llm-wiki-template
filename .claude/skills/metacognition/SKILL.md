---
name: metacognition
description: Observe how Indy is using the wiki and where his working loop costs him. **Fires automatically** — when a month's log carries more `repair` entries than `rebuild` (the correction rate has spiked and something upstream is wrong); after roughly every 25 log entries; and whenever a session ends having corrected its own earlier work more than twice. Use when Indy says "how am I using this", "metacognition", or "usage patterns". Reads git history and the log, names the observed working patterns, suggests concrete workflow improvements, and flags candidate patterns for the learn skill.
---

# Metacognition — how Indy uses the tool

This looks at the *use* of the wiki, not its content: the shape of Indy's working loop, and where
it costs him time or quality.

## Read
- Git history: commit cadence, iteration loops on the same file (repeated commits to one page),
  retitling events (`git log --follow`, diffs where the H1/title changes), branch/PR rhythm.
- the log (`wiki/log/YYYY-MM-DD.md`, day files indexed by `wiki/log/YYYY-MM.md`): the sequence and type of operations.

## Name the observed pattern
State the working loop you actually see. The known baseline, from Indy himself, is:

> small input → drive → systemic correction → redrive → correct → redrive (~5 iterations) →
> retitle → publish → integrate external comments.

Check whether that is still the dominant loop, and **name its cost** — e.g. "the systemic
correction at ~iteration 3 is the same correction most weeks; it's paid for five times."

## Suggest improvements
Concrete, not generic. The canonical example:
> "front-load the systemic constraint you always correct at step 3 into the first prompt."

Then **flag candidate patterns for the `learn` skill** — recurring, stable loops that could become a
verified skill. Don't create the skill here; hand the candidate to `learn` (which will ask Indy to verify).

## Output
In-chat by default. On request ("file it", "save the metacognition"), write to
`wiki/reflections/meta-<date>.md` (`type: synthesis`, `visibility: unlisted`) and log it.

## Epistemics (state this in the output)
- What git/log show — cadence, iteration counts, retitles — is **evidence**.
- *Why* Indy works that way — motivation, intent — is **inference**. Label it as inference; don't
  assert a motive as if it were logged fact.

## Rules
- Describe the loop; don't judge the person. The aim is a cheaper, sharper loop, not a report card.
- Never silently turn an observation into a skill — that is `learn`'s job, and it requires Indy's verification.
