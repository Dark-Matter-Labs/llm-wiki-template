---
name: validation
description: "Clear pages waiting for validation, ask the owner about critical ones, and take a page to the team properly. \"clear the validation backlog\", \"what needs my sign-off\", \"take this to the team\"."
---

# Validation

## Why this exists

On 19 November 2026 Gurden said "no one is validating anything". That day, 4,668 of the 4,737 pages in
the 43 local wikis were at `machine`. No page was at `peer` or `collective`. So most pages now get `self`
by default. A short list of critical pages asks the owner. Team validation is rare and done in the open.
The rule is in `.claude/reference/page-fields.md`, under Validation. Read it first.

## 1. Clear the backlog (own wiki only)

1. Run `python3 tools/validation_sweep.py --totals`. Tell the owner the three counts in one line.
2. Run `python3 tools/validation_sweep.py`. Read the `ask` rows. Do not list the `self` rows.
3. Ask one question: "Shall I mark the N ordinary pages as yours by default? Any of them can go back to machine later."
4. On a yes, run `python3 tools/validation_sweep.py --apply`. Propose the change as usual.
5. Then ask about the critical pages, as in part 2.

In a commons, run the dry run only. Never apply it there. A person in that commons decides.

## 2. Ask about critical pages

1. Group the critical pages by reason: a budget, a commitment, a named person, contested, a decision.
2. Ask once per group, with the titles. For example: "These 12 pages set budgets. Do you stand behind them as written?"
3. Offer three answers: yes to all, one by one, or not now.
4. On a yes, set `validation: self`, `validated_by` to the owner's login and `validated_at` to today. Add no `validation_note`.
5. With no answer, change nothing. The pages stay at `machine` and show in what is waiting.

Ask about one group per session, unless the owner asks for more.

## 3. Team validation (rare)

Use it only when someone asks for it, or when a commons page will speak for the team. That means money the
team spends, a public statement in the team's name, several people's time, or a change to the team's rules.
A `private` page never goes to the team. Raise its tier first, with `publish-check`.

1. **Name one person to call the outcome.** The owner names them. In a commons with no answer, ask the steward.
2. **Set a deadline.** Use seven days, or the next team meeting if that is later.
3. **Add a "Team check" section to the page.** Say what is being confirmed, the deadline and who calls it.
4. **Add a "Disagreements" section to the page.** Start it with one line: "Objections stay here, in the person's words."
5. **Draft the Slack message for the owner to post.** Never post it yourself.

   > Team check: <page title> (<link>)
   > What we are confirming: <one sentence>.
   > Please read it by <deadline>. Reply here: agree, agree with a change (say what), or object (say why).
   > Objections go on the page under Disagreements, in your words. <Name> calls the outcome at <meeting>.

6. **Draft one agenda line for the next team meeting.** That is the xCO stand-up, the OS call, or the commons' own meeting.
   The owner adds it where that meeting keeps its agenda.
7. **Record each objection under Disagreements.** Name the person and the date, and add any reply. Never delete one.
8. **Record the outcome under Team check.** Use agreed, agreed with changes, not agreed, or still open. Add the date and who called it.
9. **Let the person change the field.** On agreed, the named person sets `validation: peer` for one other member, or
   `collective` for the meeting, with `validated_by` and `validated_at`. `EDITING.md` shows how.
10. **Log it:** `## [YYYY-MM-DD] decision | Team check: <title>, <outcome>`.

"Still open" is a valid outcome. The person who calls it records what the group said. They do not pick a side.
A disagreement stays on the page. Nothing is averaged away.

## Hard rules

- Never award `peer` or `collective`. Never write a verification mark.
- Never post to Slack, send email or change a calendar. Draft it, and the owner sends it.
- Never apply the sweep in a commons, or in another person's wiki.
- Never delete an objection.
- Keep every page's `visibility`. A private title never goes in a draft for the team.
