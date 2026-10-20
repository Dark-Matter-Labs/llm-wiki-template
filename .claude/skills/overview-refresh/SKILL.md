---
name: overview-refresh
description: Bring the wiki's overview up to date with the pages added since it was last rewritten, and propose the change. Fires on "update the overview", "refresh the overview", "the overview is out of date", "bring the overview up to date", "what's the big picture now", or when a lint report names overview drift.
---

# Overview refresh

## Why this exists

The overview says what the wiki has learned. It drifts as new pages arrive. Lint step 4 notices
the drift but does not fix it. By 20 October 2026, eleven wikis had done the fix by hand, 13 times.
Georgia's log reads "Overview brought up to date with 30 pages added since 2026-09-28". Gurden
confirmed the pattern on 20 October 2026.

The refreshes that worked made an argument, not a list. They named new through-lines, answered
or added open questions, and left declared contradictions open.

## Method

1. **Read the overview and its details.** Note its `visibility`, `validation`, `timestamp` and
   sections. Read this wiki's CLAUDE.md for any rule about the overview.
2. **Find the date it was last rewritten.** Run `python3 tools/staleness.py --json` and read the
   overview's row. That date counts body changes only. Use it, not `timestamp` alone.
3. **List what changed since.** List pages added since that date:
   `git log --diff-filter=A --since=<date> --name-only --format= -- wiki/`.
   Where this wiki has `tools/dependency_staleness.py`, run it too. It names pages the overview
   leans on that were rewritten since.
4. **Read in triage order.** Read each new page's `description` and `visibility` first. Read in
   full only the pages that change the picture. Say how many you read in full.
5. **Check each page's tier before you use it.** The overview may name only pages at least as open
   as itself. A non-private overview never names, quotes or links a private page, and never uses its
   title. Describe the idea in plain words instead, and cite the `raw/` source where there is one.
6. **Rewrite around the argument.** Keep the sections that still serve. Aim for:
   - what the wiki is for, in a few lines
   - through-lines: claims that run across several pages, each cited
   - where the thinking sits now
   - open questions, with declared contradictions left open (`python3 tools/contradictions.py`)

   Fold dated "where the work moved" sections into the through-lines. Do not add another one.
   Cut catalogue paragraphs, because the index already lists pages. Keep it short, and no longer
   than it was unless the owner asks. Mark your own synthesis as synthesis. Keep every hedge.
7. **Keep the owner's wording where they stood behind it.** If `validation` is `self`, `peer` or
   `collective`, do not overwrite. Write each change as a provisional block at its target, as
   `.claude/rules/plain-register.md` says:

   > **[PROVISIONAL / proposed]** <id> · <target> · proposed by <agent> · <date>
   > ~~current~~ → **proposed**
   > Why: one reason.

   Treat a passage the owner wrote by hand the same way, even on a `machine` page. Only a named
   person adopts a change.
8. **Update the details.** Set `timestamp` to today. Never change `visibility`, and never raise
   `validation`.
9. **Run the checks this wiki has.** Run `tools/house_rules.py`, `tools/quote_check.py --check
   wiki/overview.md` and `tools/check_links.py`. If the overview is `public` or `unlisted`, also run
   `tools/scan_public_leaks.py`.
10. **Log it.** Append to today's log:
    `## [YYYY-MM-DD] rebuild | Overview brought up to date with N pages added since <date>`.
    Add one short paragraph on the new through-lines and questions. Then run
    `python3 tools/sync_log_index.py`.
11. **Propose the change.** Put the work on its own branch and open a pull request. In a personal
    wiki, ask once: "Shall I merge this? That saves it into your wiki". In a commons, propose and stop.

## Output

Tell the owner, in plain words and in this order:

1. What the overview now says that it did not say before: new through-lines, questions answered, new questions.
2. How many new pages it now places, and any it leaves out, with the reason (private, or too thin).
3. How many changes wait as provisional blocks, if the page was validated.
4. The question "Shall I merge this?", in a personal wiki.

## Hard rules

- **Private stays private.** A non-private overview never names, quotes or links a private page.
- **Never overwrite validated wording.** Use provisional blocks. Only a named person adopts one.
- **Never resolve a contradiction** in the overview. Name it as open.
- **Never add a fact** that the pages do not state, and never invent a citation.
- **Never change `visibility` or raise `validation`.**
- **An argument, not a catalogue.** The overview argues and routes. The index lists.
- **Nothing merges without a person's yes** in this chat.

## Connections

- `lint`: step 4 detects overview drift. This skill fixes it.
- `ingest`: step 6 updates the overview for one source. This skill does it across many.
- `tools/staleness.py`, `tools/dependency_staleness.py`, `tools/contradictions.py` and `tools/search.py`.
- `brief`: "catch me up" reads the overview first.
- `publish-check`: run it before a non-private overview is published.
- `cross-check`: a second model's reading of the new through-lines, if the owner wants one.
