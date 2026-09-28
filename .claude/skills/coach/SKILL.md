---
name: coach
description: Suggest the one useful next thing, so people discover what their wiki can do. Fires automatically at the start of a session (after the waiting check) and at the end of a finished task, and when someone asks "what can you do", "what should I do next", "any tips", or "how do I get more out of this". Also where to turn it down: "stop suggesting that", "fewer tips".
---

# Coach: suggest the next useful thing

Asked for on 28 September 2026: *"I want to make the wiki system more proactive."* Most people using
these wikis do not know that Claude can make a shareable page, which skills their wiki carries, or
that a health check exists. The wiki already knew when something needed a person. It only said so
when asked.

The risk is the opposite failure, and it is the one that killed the last input app: a system that
nags gets ignored, and then nothing it says is heard. So this skill has one discipline above all
others. **One suggestion at a time, from a real signal, after the work the person asked for.**

## Where the suggestions come from

`python3 tools/coach.py` reads the wiki and ranks what it finds. It uses no model and no network, and
it writes nothing. `--all` lists everything, `--json` for reading it yourself.

| signal | what it offers | say |
|---|---|---|
| fewer than three real pages | add the first documents | "Please add this to the wiki." |
| the overview still has the template's purpose | write the purpose | "My wiki is for …" |
| sources in `raw/` that no page cites | file them | "Ingest the documents that haven't been filed yet." |
| work on branches not merged, less any a page has closed with `decides:` | save it | "What's waiting for me?" |
| the overview more than 14 days behind the newest page | update it | "Update the overview." |
| no health check in 21 days | run one | "Check the wiki." |
| no page with a person's name behind it | stand behind a few | "What should I stand behind?" |
| no work recorded in 7 days | catch up | "Catch me up." |
| nothing needs attention | one tip, rotating daily | (in the tip) |

In a long-lived local clone, run `git fetch --prune` first, or stale branch records inflate the
"waiting" count. A cloud session starts from a fresh copy and does not need it. Where `waiting.py`
answers, trust its count over the coach's.

## When to say something

**At the start of a session.** After `waiting.py` (the finishing rule), run `coach.py`. If it returns
anything, mention the top suggestion once, in a sentence, **after you have done what the person came
for**. Never before, and never instead of it.

**At the end of a finished task.** Offer one next step that follows from what just happened, drawn
from the list below. If the task ended with "Shall I merge this?", the suggestion comes after that
question, in the same message, as one line.

| what just happened | the natural next step |
|---|---|
| a source was ingested | ask a question of it; or share it with the team, if it is labelled for colleagues |
| an answer, summary or map someone else would want to read | make it a shareable page (an artifact) |
| several ingests since the last health check | "check the wiki" |
| a synthesis or strong position was written | "challenge this", or a second opinion ("cross-check this") |
| someone else's paper or report came in | "run a delta" on it |
| a meeting was discussed | log it with the `crm` skill, if this wiki has one |
| the person is weighing a new idea | "help me think through this" (`office-hours`) |
| a Google Doc or Sheet was mentioned | the `google-sync` skill, if this wiki has it |

**Only suggest a skill this wiki has.** Check `.claude/skills/` and the routing table in `CLAUDE.md`,
because wikis differ: a commons has no `crm`, a top commons has no `contribute`.

**When asked** "what can you do?", give the five or six skills most useful to this person in plain
words, each with the sentence that starts it, not the full list.

## Artifacts: what to tell people

Most people have never heard of them, so explain once, plainly, when it first fits.

- **What it is:** a web page Claude makes and hosts on claude.ai, from anything in the conversation: a
  summary, a map, a table, a one-pager for a meeting, a small interactive tool.
- **Who sees it:** only the person who made it, until they share it from the page's **Share** menu.
  They can share with named people or with everyone at Dark Matter Labs.
- **It stays current:** asking for a change updates the same link, so a shared page does not go stale.
- **Where to find them:** claude.ai/code/artifacts lists every page they have made.
- **How to start:** "Make this a shareable page."

**The boundary holds here too.** Before making a page from wiki content, check the labels of the pages
it draws on. Material from a `private` page is fine in an artifact only the person sees, and must not
go into one they share. Say so if it applies. For a page meant for the open web, the `publish-web`
skill (where this wiki has it) is the route, after `publish-check`. If this session cannot make
artifacts, say so and offer the alternative.

## The rules that keep it worth hearing

- **One suggestion per reply, at most.** Never a list of tips unless the person asked for one.
- **Never interrupt a task** to suggest something. Suggestions go at the end.
- **Never repeat a suggestion declined in this session.** "No", "not now" or silence all count.
- **Never act on a suggestion without a yes.** Suggesting "check the wiki" is not running a lint.
- **Never invent a problem.** If `coach.py` finds nothing, a tip is the most you offer.
- **Honour "stop suggesting that".** Add its id (for example `lint`, `stand-behind`, `tip-artifacts`,
  or `tips` for every tip) to `"off"` in `design/coach.json`. Create the file if needed, as
  `{"off": [...]}`, on a branch, and ask "Shall I merge this?" as usual. It stays off until they say
  otherwise.
- **Speak in the person's words, not the system's.** "Save it into your wiki", not "merge the branch".

## Connections

- `.claude/rules/finishing.md`: opens every session with what is waiting, and ends work with "Shall I
  merge this?". This skill adds one next step to both.
- The `waiting` skill: the authoritative account of unsaved work.
- The `lint`, `brief`, `joker`, `cross-check`, `delta`, `office-hours`, `contribute` and `publish-web`
  skills: most suggestions point at one of them.
