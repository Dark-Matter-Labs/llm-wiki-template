# How to finish a piece of work

**In a personal wiki (`role: spoke`), finish the work in the session that started it.**

1. Make the change on a branch and push it. The branch and the pull request are the undo point and the record.
2. Say what changed, in plain language, leading with what was learned rather than which files moved.
3. **Ask once, in the session: "Shall I merge this?"**, saying what it means: "That saves it into your wiki".
   One question. Merge on a yes.
4. If the answer is no, or there is no answer, leave it. Never send the owner to github.com to merge.

**In a commons (`role: commons`), propose and stop.** A second person approves there; `contribute.py` exists for it.

**Open the session with what is already waiting:** run `python3 tools/waiting.py` before new work and say what it found.

**Offer one next step, and only one.** At the start, after the waiting check, run `python3 tools/coach.py` and
mention its top suggestion once, after doing what the person came for. At the end of a finished task, offer one
next step, after "Shall I merge this?". The `coach` skill says how. Never a list of tips, never mid-task, never a
repeat of one declined, never acting on a suggestion without a yes.

**This is not auto-merge.** Nothing merges without a person saying yes in that session. If the change is large or
contested, say so and let the pull request sit.

The reasons and examples behind these rules are in `.claude/reference/rules-in-full.md`.
