---
name: pre-read
description: Build a short, sourced, versioned brief for one meeting or one audience from what the wiki already holds, with the audience's tier checked. Use when the owner says "make a pre-read for…", "brief me before…", "a one-pager for the investors", "something to send ahead of the workshop", "what should they read before Thursday", or "pull together what we know for the session on…". Proposes the brief as a page or a document. Never sends it.
---

# Pre-read

## Why this exists

A pre-read is the most common thing owners ask the wiki to write for other people. By 20 October 2026, seven
wikis held 103 such entries: workshop and convening briefs, investor one-pagers, "Pre-read for the 5 November
session". The same faults recurred. A brief went to the wrong tier, claims lost their sources, and gaps were
filled with guesses.

Generalised from Prateek's `dossier` and `context-dossier` and Gurden's `synthesis-brief`. A pre-read is smaller
than a dossier. It serves one meeting or audience and uses only what the wiki holds. Gurden verified the pattern on
20 October 2026.

## Method

1. **Name the reader and the purpose.** If either is unclear, ask one question: "Who reads this, and what decision
   or conversation is it for?" If both are clear, say your reading in one line and go on.
2. **Set the tier from the audience.** Say it in one line.

   | audience | may use |
   |---|---|
   | the owner alone | any page, private included |
   | colleagues in Dark Matter Labs | `public`, `unlisted` and `internal` pages |
   | anyone outside Dark Matter Labs | `public` pages only, in plain framing |

3. **Find the material.** Run `python3 tools/search.py "<topic>" --top 12`. Use `export/wiki.json` for the next hop.
   Then read the shortlist in full. Grep a large `raw/` source and read only the sections that matter.
4. **Drop what the tier does not allow,** before you write. Check each page's `visibility`. When in doubt, leave it out.
5. **For anything about capital,** follow `.claude/rules/capital-vocabulary.md` first, where this wiki has it. Use the shared terms and link them.
6. **Write the brief** (shape below). Every claim cites a wiki page as `[[Page Title]]` or a source as `(raw/…)`.
   - Mark your own synthesis as synthesis.
   - Where sources disagree, show both. Do not choose.
   - Where the wiki does not know something, write a `[placeholder]` saying what is missing. Never fill it in.
7. **Check it.**
   - Plain register: 25 words or fewer per sentence, no semicolons, active voice.
   - Run `python3 tools/house_rules.py` where this wiki has it.
   - For a brief leaving Dark Matter Labs, run the `publish-check` skill. Fix what it finds, or tell the owner.
8. **Propose it.** Do one of these, as the owner prefers:
   - a wiki page (`type: synthesis`, `derivation: synthesis`), with its index row and a `query` entry in today's log
   - a document through a document connector, where this wiki has one
   Make a draft, open a proposed change, and ask: "Shall I merge this? That saves it into your wiki."

## Output

A brief of one to two pages. Its header:

> **Pre-read v1.0 · <meeting or audience> · <d Mon yyyy>**
> For: <who reads it>. Serves: <the decision or conversation>. Tier: <public | internal | private>.

Then these parts, in order:

1. **In short:** three to five lines a reader can take into the room.
2. **What we know:** short sections, each claim cited.
3. **What we do not know yet:** the `[placeholders]`, as questions.
4. **Questions for the meeting,** where the purpose calls for them.
5. **Sources:** every page and `raw/` file cited.
6. **What was left out, and why:** for example "three internal pages, by tier" or "one claim with no source".
   Never name a private page here when the brief is not private.
7. **Version history:** v1.0 first. A correction makes v1.1. A new audience or meeting makes v2.0.

Lead the reply to the owner with what the brief says, then what it left out.

## Hard rules

- **Never invent a fact, figure, date, name or status.** A gap stays a `[placeholder]`.
- **Outside Dark Matter Labs, public material only.** No private pages, CRM entries, contact names, money figures
  or deal terms, unless the owner decides it in this chat for this brief. Record that decision in the brief's details.
- **The CRM is always private.** Its content may appear only in a brief for the owner alone, kept `private`.
- **A brief may not link a page less open than itself.** Describe the idea in plain words and cite the `raw/` source instead.
- **The page's own `visibility` matches its audience.** Default `private`. The owner opts it up. Never guess `public`.
- **Never send it.** No email, message, post or share. The owner sends it.
- **Knowledge, not surveillance.** A pre-read covers ideas and work. Refuse to report what people have been doing.
- Never edit `raw/`. Never write a verification mark.

## Connections

- `query`: answers one question. A pre-read gathers answers for one audience.
- `publish-check`: the gate for any brief that leaves Dark Matter Labs.
- `.claude/rules/capital-vocabulary.md`: the shared capital terms.
- `.claude/rules/plain-register.md` and `ai-detox`: the writing rules.
- `publish-web`: if the owner wants the brief as a web page, after `publish-check`.
- `dossier`, where a wiki has it: for a fuller page gathered from sources beyond the wiki.
- `.claude/rules/finishing.md`: how to ask "Shall I merge this?".
