---
name: rulings
description: "File the owner's standing ruling as a numbered decision, link it to the skill or rule it changes, and check drafts against open rulings. Fires when the owner gives a lasting instruction: \"from now on…\", \"always…\", \"never…\", \"make that a rule\", \"remember this for next time\", \"I've decided that…\", \"stop doing X\", \"that rule no longer applies\". Also on \"what rules have I set\" and \"which of my rules applied here\"."
---

# Rulings

## Why this exists

Prateek gives his wiki standing instructions and has them filed as numbered rules, 58 of them by 17 October 2026.
His log carries 87 decision entries. Ocean Studio keeps nine the same way. Robyn started a decisions log on 18 October.
This skill is generalised from Prateek's practice. Gurden confirmed the pattern on 20 October 2026.

A ruling said once in chat is lost by the next session. A numbered ruling with its source is read every time.

## What a ruling is

- A **standing instruction** from the owner about how the wiki is kept, written or styled. In a commons, from a named person.
- It is **quoted in their words**, with the date and who gave it.
- It **says what it changes**: a skill, a page convention, a style, a word to use or avoid.
- A one-off choice ("use the blue chart for this deck") is not a ruling. Do it, and do not file it.

## Where rulings live

- **The owner's words:** `raw/decisions/<short-slug>-YYYY-MM-DD.md`. A new source, never edited after.
- **The numbered list:** where this wiki already has one, add to it. Prateek's is in `instructions/wiki-rules.md`.
  Where it has none, propose `.claude/reference/rulings.md`, with one line in CLAUDE.md that says to read it before drafting.
- **The pointer back:** the skill, reference file or convention the ruling changes gets one line, "Ruling N (date): …".

## Method

1. **Hear it as a ruling.** If the owner's words could be a one-off, ask one short question: "Is that for every time, or just this one?"
2. **Check it against the hard rules** in CLAUDE.md and the shared rules in `.claude/rules/`. If it conflicts, say so plainly and do not file that part.
3. **Check it against open rulings.** If it changes an earlier ruling, say which one. The earlier one becomes superseded.
4. **Record the words** in `raw/decisions/`. Run `python3 tools/source_scan.py` on the file where the wiki has that tool.
5. **Add the ruling** with the next number. Use this form:
   `N. **Short title** (ruled DD Month YYYY, by Name). What to do, in one or two plain sentences (raw/decisions/<file>.md).`
   Never reuse a number. Never renumber.
6. **Mark a superseded ruling** in place: "Superseded by ruling M (date)." Keep its text. Never delete it.
7. **Add the pointer back** in the place it changes.
8. **Log it:** `## [YYYY-MM-DD] rebuild | Ruling N: <short title>`, then run `python3 tools/sync_log_index.py`.
9. Open the proposed change, say in one line what the ruling now does, and ask "Shall I merge this? That saves it into your wiki".

## When drafting

Before any page, deck, message or reply the owner will read:

1. Scan the open rulings for ones that touch this kind of work.
2. Follow them.
3. Say in one line which applied, by number: "Followed rulings 45 and 51." Say nothing if none did.
4. If two rulings pull in different directions, follow the newer one and say so. Ask only if it still matters.

## Output

- After filing: the ruling as written, its number, what it changes, and any ruling it supersedes.
- On "what rules have I set": the open rulings by number and title, newest first, with superseded ones listed apart.

## Hard rules

- **Only a person makes a ruling.** Claude may propose one ("Shall I make that a standing rule?"). It is filed only on a clear yes.
- **Never invent or paraphrase a ruling into something new.** The quote in `raw/decisions/` is the ruling. The numbered line summarises it.
- **A ruling never overrides the hard rules in CLAUDE.md.** Visibility, never editing `raw/`, verification marks and the house spellings all stand.
- **A ruling binds this wiki only.** A change to a shared rule in `.claude/rules/` is a system-wide change. Say so and follow `.claude/rules/shared-changes.md`.
- **Superseded rulings stay listed.** History is kept. Nothing is deleted to tidy up.
- **Respect visibility.** A ruling about a private matter keeps its words private. A public page never quotes it.
- **Knowledge, not surveillance.** A ruling may not ask Claude to track what other people do.
- Propose, never merge without the owner's yes in this chat.

## Connections

- `learn` turns a recurring pattern into a new skill, once the owner verifies it. A ruling is one instruction, said once, that changes how existing work is done.
  A cluster of rulings about one kind of work may become a skill through `learn`, with the owner's yes.
- `.claude/rules/` files are federation-wide and change only through the shared-changes route. Rulings are this wiki's own.
- `decides:` on a page settles a question about unmerged work. A ruling sets how future work is done.
- A decisions log of project decisions (what was decided about the work itself) is a wiki page, not a ruling list.
- `my-commitments` follows the rulings about how the commitments list is kept.
