# When something goes wrong

Plain answers for the common cases. In each one, nothing is lost.

## "A check failed"

Every proposed change runs automatic checks. A failure stops the change from being saved until it is fixed. Ask
Claude: "why did the check fail?" It reads the result and fixes it, or explains what it needs from you.

If a check fails within seconds without running anything, GitHub probably did not start it. That happens when the
organisation's GitHub spending limit is reached. Claude can run the check again once GitHub is working.

## "Nothing is happening" or "it is very slow"

GitHub sometimes has outages. Checks wait in a queue, and websites stop updating. Look at
<https://www.githubstatus.com/>. When it recovers, everything waiting catches up by itself.

## "It clashes" or "it needs redoing"

Two changes touched the same file, often the day's log. Ask Claude to redo it. It brings the change up to date,
keeps both sides, and runs the checks again.

## "My change disappeared"

Nothing in the wiki is deleted to tidy up. A page can be retired, but it stays. A proposed change that was never
saved is still there. Ask Claude "what's waiting?" and it shows you.
