---
name: waiting
description: Say what needs a person right now, without using git's vocabulary. Fires on "what's waiting for me", "what needs me", "anything outstanding", "what have I missed", "is there anything to review". Built for the person who does not know git and should not have to.
---

# What's waiting

## Why this exists

Asked at the Berlin meeting, 14 September 2026: *how do we make this work for people who do
not know git?* The measurement said the answer was not a better explanation of git.

On 2026-09-15 one wiki in this federation had **61 branches**. **Thirty-seven had never had a pull request
opened for them at all** — the oldest from 4 July — carrying **66 pages that existed there and
nowhere else.** Nothing was broken. No check had failed. The review queue was empty, which is
precisely why nobody looked: the work sat in the one place the system never shows anyone.

A person who does not know what a branch is cannot go looking on a branch. The only surface
they are taught is the proposal, and these never became one.

## The rule of this skill

**Never say *branch*, *commit*, *rebase*, *remote*, *HEAD* or *checkout*.** Not once. If the
answer seems to need one of those words, the answer is wrong — say what is in the work, when
it was written, and what clicking will do.

| instead of | say |
| --- | --- |
| "there's an unmerged branch" | "some work was written and never put forward" |
| "the PR has a failing check" | "a check says something is wrong with this one" |
| "merge the pull request" | "say yes to it" |
| "it's behind main" | "it was written before some other changes; it may need a fresh look" |
| "resolve the conflict" | "this one overlaps with something that changed since — I can redo it" |

## Method

1. **Run `python3 tools/waiting.py`.** It does the counting. Do not do it by hand, and do not
   contradict it — if a number here disagrees with the tool, the tool is right.
2. **Lead with the total, not the list.** "Sixty-six pages are sitting in work nobody ever put
   forward" is the sentence. The table is the detail behind it.
   **Lead with the lines the wiki does not have, not with the new pages.** "0 new pages" is not
   "nothing to lose": on 2026-09-23 it sat over a 180-line rewrite of an existing page, and
   nearly got that work set aside unread. A rewrite is not a new page.
3. **Offer to look, not to act.** For anything old, offer to read it and say what it contains
   and whether it still holds — that is genuinely useful and costs the owner nothing.
4. **Never propose, merge, or delete anything on your own.** See below.
5. If asked to deal with one, read that work, summarise what it would add **in plain
   language**, say whether it still fits the corpus as it now stands, and let the owner
   decide. A two-month-old page may have been superseded; say so if it has.

## The refusals, and why

- **You do not open the proposals.** Thirty-seven pieces of unfinished thinking are not
  thirty-seven things somebody wants published. Sweeping them in would be a machine deciding
  what a person meant to keep.
- **You do not delete the work either.** "Tidying up" an old piece of work destroys the only
  copy. Nothing in this wiki is ever deleted to tidy up, and that rule binds hardest where the
  material is somebody's abandoned draft.
- **You do not rank or compare people.** The report is per repository. Who wrote what, and how
  much, is not a question this system answers.

## The surface that matters

This skill is the version for someone already in a conversation. The real one is
`.github/workflows/waiting.yml`, which keeps a single GitHub Issue up to date every Monday —
one page, one URL, always current, readable by someone who knows nothing about any of this.
If you are explaining the system to a newcomer, point at the issue, not at this skill.
