# How to finish a piece of work

Measured across the ten wikis on 22 September 2026: **90 branches that are not `main`, and 2 open
pull requests.** In `indy-llm-wiki`, **57 of 63 branches carried commits that were never merged**, the
oldest from early July, one of them twenty commits deep. Not one of them was blocked on review. The
review queue was empty the whole time.

That is not people failing to merge. It is work that nothing ever asked about again.

## The cause

A session ends in two different places. Claude's ends at "pushed a branch, opened a pull request".
The owner's ends when they stop typing. Nothing joins the two, so the merge has to happen later, on
github.com, which is not where they were.

The pull-request-then-stop rule is borrowed from code review, where a **second person** approves. In a
personal wiki there is no second person. The review that matters already happened in the conversation,
while the work was being explained. Sending the owner to a web form to re-approve what they just
watched being written adds a step and subtracts nothing.

## The rule

**In a personal wiki (`role: spoke`), finish the work in the session that started it.**

1. Make the change on a branch and push it, exactly as now. The branch and the pull request are the
   undo point and the record; keep both.
2. Say what changed, in plain language, leading with what was learned rather than which files moved.
3. **Ask once, in the session: "Shall I merge this?"** One question. Merge on a yes.
4. If the answer is no, or there is no answer, leave it. An unmerged branch is a legitimate outcome;
   an unmerged branch nobody was ever asked about is not.

**In a commons (`role: commons`), keep proposing and stopping.** A contribution to a shared wiki is
the one case where a second person genuinely does approve, and `contribute.py` exists for it. Nothing
in this rule touches that path.

**Open the session with what is already waiting.** Before new work, run
`python3 tools/waiting.py` and say what it found. The owner should not have to know the tool exists,
or that a thing called a branch is holding their work.

## What this rule is not

**It is not auto-merge.** Nothing merges without a person saying yes in that session. The whole claim
this system makes is that a person decides; a job that merged knowledge changes on a schedule would
break that quietly, which is the worst way to break it. `waiting.py` reports and never acts, and that
stays true.

**It is not a reason to skip the summary.** Merging faster is only an improvement if the person
understood what they were merging. If the change is large or contested, say so and let the pull
request sit.

## The lesson worth carrying into any future interface

The accept step has to live where the work happens. An application with nicer buttons that still
sends people somewhere else to approve will reproduce this exact backlog. That is the design
constraint, not the terminal.
