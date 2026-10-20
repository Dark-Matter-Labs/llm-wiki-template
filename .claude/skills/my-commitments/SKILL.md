---
name: my-commitments
description: "Keep the owner's open commitments current from plain statements, sorted by their categories and horizons, and refresh the views that show them. Fires on \"update my commitments\", \"that's done\", \"I'm not doing X any more\", \"I've to set up a call with…\", \"move that to next month\", \"what am I on the hook for\", \"what's on my plate this week\", \"sweep my email for things I promised\". Changes only the commitments page and the views built from it, and asks before saving."
---

# My commitments

## Why this exists

Prateek asked for it on 15 October 2026, and this skill is generalised from his `commitments-update`.
By 20 October the pattern had about 75 log entries across five wikis, most of them Prateek's and Robyn's.
Robyn rebuilt the same shape by hand, with her own categories and a triage view.
Gurden confirmed the pattern on 20 October 2026.

The point is small and practical. A person says "that's done" in plain words, and the list keeps up.

## Where the list lives

- **The commitments page.** Where the lens settings name one (`design/lens/settings.json`, `commitments.page`), use that page.
  Otherwise look for a page titled like "<Owner>'s open commitments". If there is none, propose one, `visibility: private`.
- **Its shape is the owner's.** Keep the sections and columns the page already has. Do not impose a new table.
- **Categories** are the owner's groups (a project, a stream, "Other"). Where the lens settings carry a category order, that order rules.
- **Horizons** are four bands: this week (late or chased items included), next week, within the month, and beyond.
  Deprioritised items go to beyond.

## Method

1. Run `python3 tools/waiting.py` if this is the start of the session, and say what it found.
2. Read the commitments page in full, and the lens settings where they exist.
3. Turn what the owner said into changes. Match each statement to an existing row before adding one.
   Ask one short question only if two rows could fit.
   - **Done.** Take the row out of the open table. Add a dated line under "Done".
   - **Dropped, declined or not doing.** Take the row out. Note it under its closing heading with the reason and date.
   - **Moved.** Change its date or its band. Say the new date plainly.
   - **New.** Add a row in the right category, written as its next step, with a due date where one is known.
4. **Sweep only when asked.** If the owner asks to check email, Slack, Notion, Drive or call notes, use only connectors this chat has.
   List each candidate with where it came from. The owner accepts or rejects each one. Add only the accepted ones.
5. Record the owner's words in `raw/commitments/commitments-update-YYYY-MM-DD.md`. Run `python3 tools/source_scan.py` on it where the wiki has that tool.
   Cite it from the page.
6. Refresh the lens commitments box, where this wiki's lens has one, with the `lens-refresh` skill.
   The team stand-up page is separate. It reads call summaries, not this personal list.
7. Add an `ingest` entry to today's log, run `python3 tools/sync_log_index.py`, and open the proposed change.
8. Report, then ask "Shall I merge this? That saves it into your wiki".

## Output

- One or two plain sentences on what moved: closed, added, re-dated.
- The open list as a **suggested triage**: the four bands, grouped by category inside each, with the due date on each item.
  Mark any inferred date as inferred. Most urgent first within a group, then newest.
- At most two category changes, in one line. Split a category holding more than about half the items.
  Promote a project out of "Other" once it holds two items or a fixed date within eight weeks.
  Fold a category into "Other" after two checks in a row with one item or fewer. The owner says yes or no.
  Do not raise a refused change again unless the counts change.

## Hard rules

- **The page is the owner's own, and private by default.** Never publish it, export it or share it to a commons.
  The lens box is the one exception, and only in the owner's personal lens.
- **Never add a commitment the owner did not make or accept.** An offer ("happy to", "I can", "would you like me to") is not a commitment.
  At most, note it as a softer offer that is not counted.
- **List only what the owner holds.** Never record another person's commitment in someone's list as if it were theirs, even when the owner is involved.
- **Every swept item is shown before it is listed.** Silence is not a yes. A meeting tool's suggested owner is not a yes either.
- **Done, dropped, moved and declined are all honourable closures.** Never word one as a failure.
- **Never count or compare people.** No tallies per person, no "who is behind".
- **Keep it lean.** No money figures, HR, health, personal admin or people matters. Keep each bold first phrase short, since the lens shows it.
- Change no other page. Calendar access is read-only. Never contact anyone on the owner's behalf.
- Propose, never merge without the owner's yes in this chat.

## Connections

- `crm`: relationships and follow-ups with people. A follow-up becomes a commitment only when the owner says so.
- `waiting`: proposed changes waiting for a person. That is work for the wiki, not a promise to someone.
- The `commitment` page type in CLAUDE.md is different. It records resources held against a goal, with `state:` and `tools/goals.py`.
- `rulings`: a standing instruction about how this list is kept (bands, categories, what counts) is filed there, not here.
- `lint`, `brief` and `weekly-review` may show the list. They follow the same triage and the same rules.
