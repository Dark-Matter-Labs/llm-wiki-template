---
name: notion-sync
description: Reconcile the wiki with the xCO Notion workspace. Use when someone says "do the notion sync", "does Notion match the wiki", "update the tracker", "check the option book against Notion", or after any ingest that changes the option book, the portfolio or a goal. Read-only by default; every write is named before it is made.
---

# Reconcile the wiki with Notion

There is no automatic sync and there should not be one. Notion is where the team *works* — rows
people edit in meetings, tasks, relations to Dm's own databases. The wiki is where the reasoning
is *recorded*. A machine that overwrites either one from the other destroys the thing that makes
it worth having.

So this is a **reconciliation**, not a pipeline: read both, name what differs, and make only the
changes a person would recognise as obviously right.

## The boundary — decided 2026-09-04, and it holds

When eleven missing options were added to the tracker, the decision recorded on the option-book
summary — a `private` page in the wiki that holds the budget — was:

> Each new row records its OPT code, its stage, its leads and what the book says, in prose;
> **no figures were copied into Notion**, which keeps the amounts on this page and out of a
> teamspace database.

That is the rule. **Prose and structure cross. Money does not.** The Notion workspace has a
different and wider readership than the wiki's `private` tier, and a budget line is the most
re-shareable object in the corpus. If a figure is genuinely needed in Notion, that is a decision
for Indy, made once, in the open — not a side effect of a sync.

Everything `visibility: private` stays out by default, figures or not. The CRM never crosses at
all.

## The join is a key, never a name

`Options portfolio` carries a **`Wiki page`** URL property. That is the join, and it is the only
one that works.

**Do not match rows to pages by title.** Tried on 2026-09-07 across all twenty rows and it
produced confident, wrong answers: "XO (Zero-Extraction) Copenhagen" matched a delta brief about
autopoiesis, "Arctic" matched a paper on relational sovereignty. Substring matching on a corpus of
600 pages will always find something, and something is worse than nothing here, because a wrong
link looks exactly like a right one.

If a row has no `Wiki page`, leave it empty and say so. An empty join is a visible gap; a guessed
one is a silent error.

**The URL is `https://xco-team-wiki-lens.netlify.app/p/<slug>`.** Not Vercel — those deployments
were removed on 2026-09-07 and all three links in the tracker pointed at them, dead, until they
were repointed the same day. Verify the slug exists in the shared cut before writing a link;
`private` pages are not in it and will 404 for everyone.

## Three vocabularies, one portfolio

Known, unresolved, and not this skill's to settle:

| where | ladder |
| --- | --- |
| the architecture | `Pre-option` · `Option` · `Portfolio` · `Position` (v3.1's Type ladder) |
| the budget | a funding-maturity sequence |
| Notion `Status` | `🔨 Live` · `🌱 Developing` · `🔮 Future` · `🗄 Retired` |

**Only the budget's carries money.** Do not translate between them silently. If a row's status
looks wrong against the book, report the disagreement — do not resolve it by picking one.

## How to run it

1. **Read the wiki side.** `wiki/xco-option-book-2026-summary.md` for the option book;
   `tools/goals.py` in the commons for the ledger.
2. **Read the Notion side.** Fetch the `Options portfolio` database for its schema, then query the
   rows. Read the whole set before changing anything.
3. **Report the differences** in four buckets: in the book but not the tracker · in the tracker
   but not the book · same row, disagreeing fields · rows with no `Wiki page`.
4. **Make only the obvious repairs**, naming each one: a dead host in a URL, a missing OPT code, a
   row for an option that plainly exists. Anything requiring judgement goes to the report.
5. **Log it** — `## [YYYY-MM-DD] rebuild | Notion reconciliation` — with what was written.

## Writing to Notion, carefully

- **`update_properties` is safe.** It changes named fields and leaves the rest alone.
- **`replace_content` replaces the ENTIRE page, not a selection.** It destroyed the roadmap page
  on 2026-09-07 and nearly took D-INO's fifteen child pages with it. Prefer `update_content` with
  an exact `old_str`, or `insert_content`. If you must replace, fetch the page first and keep the
  full text where you can restore it from.
- **Never delete a row.** The tracker retires rather than deletes — `🗄 Retired` with a pointer to
  where the work actually lives — which is the same treatment `status: dormant` gets in the wiki,
  and for the same reason.

## Hard rules

- **No figures into Notion.** The 2026-09-04 decision, above.
- **Nothing `private` crosses**, and the CRM never crosses at all.
- **Never guess the join.** No `Wiki page` means no link, not a plausible one.
- **Never resolve a vocabulary disagreement by choosing a side.** Declare it, as with
  `contradicts:` — a person decides.
- **Read the whole database before writing to one row.** The cost is one call and it is the
  difference between a repair and a guess.

## Connections

This skill travels the federation, so it names no page. The two it depends on are `private` in
the wiki that authored them, and a shared file carrying a private title is the thing
`contribute.py` exists to prevent.

- **The option-book summary**, wherever the budget lives — the source of the 2026-09-04
  reconciliation this continues, and of the per-option figures that must not cross.
- **The portfolio-positions statement** — the Type ladder Notion's `Type` field mirrors.
- The `contribute` skill — the same shape at the wiki↔wiki boundary: stage, propose, let a
  person merge. Notion has no pull request, which is exactly why the rules here are stricter.

If your wiki has no Notion workspace, this skill has nothing to do and should stay unused rather
than be adapted — the guards below are calibrated to one specific database and one specific
boundary decision.
