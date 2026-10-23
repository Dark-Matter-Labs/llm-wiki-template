---
name: ino-check
description: Ask of any piece of work whether it knows which question it serves and what would change its mind, before it leaves a wiki. Fires automatically before a theory of change, proposal, brief, deck, contract or published page is shown to anyone outside the session, and after publish-check. On request, "run the INO check", "is this inquiry-native", "check this against INO", "does this know what it's testing". A mirror, never a gate: it reports, proposes, and leaves the decision to a person.
---

# INO check

Michelle asked for this at Medulla on 16 October 2026: a prompt, like the Joker, that asks whether a
piece of work has been checked against inquiry-native organising every time something is made.
Robyn asked for it to be built on 22 October, from section 5 of her page "Making xCO Inquiry-Native —
Rhythms, Rituals and Coding". It was built in her wiki and shared with every wiki at her agreement and
Gurden's request on 22 October 2026.

The idea underneath: an action-explicit document makes its promises explicit and leaves its learning
implied. An inquiry-native one makes its question and its hunches explicit, and says what would change
its mind. Most of what xCO writes is still the first kind. This check does not make that wrong. It
makes it visible, so the author can decide.

The script is `tools/ino_check.py`. The reading pass below is the part a script cannot do.

## When it runs

- Before any artefact leaves a wiki: a theory of change, a proposal, a brief, a pre-read, a deck, a
  contract, a published page. Run it alongside `publish-check`, and after `name-check` where this wiki has it.
- When the owner asks for it on a page or a draft.
- Not on source summaries, entities, the index or the log. Those report; they do not commit.

## The six questions

1. **Which question does this serve?** Named, or "none, and here is why the work exists".
2. **What are its hunches?** Each stated so that it could be wrong.
3. **What would change our mind?** The evidence, and who would bring it.
4. **Who stands behind it, by name?** And in which register: settled for now, our hunch, or open.
5. **When is it reopened?** A date, and the forum that decides.
6. **What can it not hold?** The knowledge that did not make it into text, and the people not in the room.

A document that fails 2, 3 and 5 is a plan. That is sometimes right, and it should know what it is.

## Method

1. **Run the script.** `python3 tools/ino_check.py <file>` on the draft. It finds the marks and says
   where. It never edits and never fails by default.
2. **Read the draft once for what the script cannot judge:**
   - Is each hunch specific enough to be wrong? "We think this will help" is not a hunch. "Match
     funding arrives within six months where the place is warm" is.
   - Is "what would change our mind" something a person could actually bring, by a date?
   - Does the name in question 4 belong to a person who has said so? A model's name never counts.
   - Does the reopen date have a forum with the right to change something?
3. **Report in six rows**, found or missing, with the evidence. Then one line: reads as an inquiry,
   reads as a plan, or in between. No score.
4. **Propose, do not insert.** For each missing mark, draft the sentence that would carry it, in the
   author's words where the page is theirs. On a page a person has stood behind (`validation: self` or
   above), show it as a provisional block, as `.claude/rules/plain-register.md` requires. On a
   `machine` page, add it and say so.
   **The mark most often missing is "what would change our mind"** (5 of 81 pieces of work in the team wiki
   on 22 October 2026). Draft it in this shape, adapted from nvk/llm-wiki's thesis mode: *What would change
   our mind: <the evidence>, which <who> could bring, by <when>.* A question page also carries a `verdict:`
   in its details: `open` until its recommit, then `supported`, `partly supported`, `contradicted`, `mixed`
   or `not enough evidence`, set by the steward and never by the model.
5. **Log it** as `## [YYYY-MM-DD] inquiry | INO check: <title>` in today's log file, with the verdict in
   one line. Skip the log entry when the check is part of a publish that already logs.

## What it is not

- Not a gate. `--strict` exists for anyone who wants one later. Nothing in CI runs it.
- Not a style check. A page can pass all six and read badly. `ai-detox` and `copywriting` do that work.
- Not a judge of the question. Whether the question is the right one is the `joker`'s work, and the
  recommit forum's decision.
