---
name: retract
description: Remove a leaked value (a secret, a private page's title, a person's name) from every copy in the wiki, without Claude ever seeing it. Fires on "something leaked", "remove this everywhere", "retract this", "I pasted a password", "a private title is on a public page", "scrub this name".
---

# Retract a leaked value

## Why this exists

A leak is rare and urgent: a password pasted into a source, a private page's title on a shared page, a name
someone asked to have removed. The value can sit in many places at once: a page, a saved source, an export,
the published site. Adapted on 23 October 2026 from nvk/llm-wiki's retract command, and agreed by Gurden that day.

## The rule that shapes everything

**Claude never sees the value.** Not in the chat, not in a command, not in a diff. A person types it into a
hidden prompt in their own terminal. Claude works from the tool's report, which lists files and counts only.

## Method

1. **Say what will happen, in plain words.** The tool finds every copy, shows where, and changes nothing until
   asked. If the owner pastes the value into the chat anyway, do not repeat it, do not use it, and say so. If it
   is a secret, it should be rotated now whatever else happens.
2. **The person runs the dry run.** Give them this, to run from the wiki's folder:
   `python3 tools/retract.py`
   They type the value at the hidden prompt. It lists each file and how many copies, never the value.
3. **Read the list with them.** It may include `raw/`, which is otherwise never edited: a leak is the one
   exception, and it is the person's decision. Binary files (PDFs, images) are listed for them to replace or
   remove by hand.
4. **The person applies it:** `python3 tools/retract.py --apply`. Every text copy becomes `[RETRACTED]`, and the
   tool re-scans. It ends `verified` or `incomplete`, with where.
5. **Propose the change.** Commit the changed files by name, on a branch. Do not open or quote the diff: its
   removed lines hold the value. Write the proposed change's description from the tool's report only.
6. **A past day's log** changed by this fails the history guard. Only a person adds the `approved-removal`
   label. Never add it yourself.
7. **Say what is still to do**, in this order: rotate a secret; rebuild and lock the lens (it is encrypted, so
   the tool cannot search it); run the same in any wiki or commons that received a copy; git history still holds
   the old text, and rewriting it is an admin's decision.
8. **Log it** without the value: `## [YYYY-MM-DD] repair | retraction: N copies in M files`.

## Hard rules

- Never ask for the value in the chat, never put it in a command line, a file, a log or a description.
- Never read the diff of a retraction.
- Never add the `approved-removal` label.
- Never claim it is gone from git history, the lens, or another wiki.
- Nothing merges without a person's yes in this chat.

## Connections

- `tools/retract.py` and its test.
- `publish-check` and `tools/scan_public_leaks.py` find what should not be public. This removes it.
- `tools/check_history.py`: the history guard that a past log's change must pass.
- `lens-refresh`: to rebuild and lock the lens afterwards.
