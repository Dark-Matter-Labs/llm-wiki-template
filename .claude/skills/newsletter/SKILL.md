---
name: newsletter
description: Write the monthly issue — what the wikis learned, in something people will actually read. Fires on the first working day of each month, and when the owner says "write the newsletter", "do the monthly", "what went out this month". Replaces the weekly reflection, which nobody read.
---

# The monthly newsletter

## Why this exists, and why monthly

The weekly reflection ran every Friday from week 28 to week 36. Measured on 2026-09-15:

| | |
|---|---|
| inbound links to any reflection, from anywhere in the corpus | **0** |
| times W35 and W36 were touched after being written | **1 each** |
| times W30 was touched after being written | 4 |
| workflow runs · of which failed | **15 · 5** |

Attention decayed from four touches to one. Nothing in the corpus ever cited a reflection. The run
on 11 September failed and nobody noticed. It also called the model every Friday, billed outside
the Team plan.

None of that is a prose problem. **A week is not long enough to have something worth saying**, and
paying for a weekly artefact nobody reads makes it worse rather than better. So: monthly, written
properly, and sent to people rather than left in a folder to be found.

## The split — and keep it

`python3 tools/newsletter.py --json` does the arithmetic: what entered, what moved, what is stuck,
per wiki and per commons. It is deterministic, costs nothing, and calls no model. **Start there,
every time.** Do not recompute what it already knows and do not contradict it — if a number here
disagrees with the tool, the tool is right and the draft is wrong.

Your job is the half a script cannot do: deciding what is worth saying, and saying it well.

## The voice

**Run two skills before you write a word, and again over the draft.**

- **`ai-detox`** governs the sentences. Plain prose, short sentences, no bullet lists, no bold in
  prose, no em dashes, no closing offer, no recap paragraph, and a list of banned words and
  phrases. A newsletter that reads as machine-written undoes the thing it is reporting.
- **`dm-style-guide`** governs the stance. Systems-minded, inquiry-led, quietly hopeful. Plain and
  precise about radical ideas. Hope without hype. It also carries the two house spellings, which
  are gated on deploy.

Where they seem to conflict, `ai-detox` wins on sentence mechanics and `dm-style-guide` wins on
stance. Both ban hype, so that overlap is not a conflict.

Then the things particular to this artefact, which neither skill covers:

Written for a colleague who has been busy and missed a month. Not for a funder, not for a file.

**Lead with the most interesting thing that happened**, not with the period covered. "Nobody can
save the salmon" is an opening. "In August, the corpus grew by 128 pages" is not.

**Six hundred words is generous.** If a section has nothing in it, cut the section. Do not write
"no change this month" eight times.

**Three things properly told beats eleven listed.** The rest is in the wiki and always was.

**Name what is stuck, not only what moved.** A newsletter that only reports progress is a
brochure, and people stop believing it by the third issue.

**Quote the corpus.** A page's own one-line description, or a line somebody actually said in a
session, beats any summary you would write of it.

## What earns a place

In rough order of interest:

1. **A position that changed** — somebody now thinks something different, and why.
2. **A decision taken**, especially one that closed an argument.
3. **A thing that broke and what it taught.** The repair log is the most trusted section you have,
   because nobody else publishes theirs.
4. **A question nobody has answered yet**, stated plainly enough that a reader could answer it.
5. **What came in** — sources, concepts, options. Last, and briefly, because it is the least
   surprising part.

## Hard rules

- **Nothing `private`.** Not its body, not its title, not a link to it, not a paraphrase. The
  material from `newsletter.py` is already boundary-filtered; do not go around it to the raw wiki
  for a better anecdote.
- **No ranking of people.** A contributions leaderboard has been asked for and it is a real idea,
  but a per-person ranking inside a shared instance is activity tracking of named colleagues —
  "knowledge, not surveillance … binds hardest in the team wiki and every shared instance". Report
  per **wiki**, which is what the federation diagram already shows publicly. If the group decides
  it wants a leaderboard, that is a decision people take with their eyes open, not a default the
  newsletter ships with.
- **Never invent a number.** Every figure comes from `newsletter.py` or from a tool you ran and
  can name. If you cannot source it, cut the sentence.
- **Say when a month was quiet.** A thin month reported honestly is worth more than a padded one,
  and the reader can tell the difference anyway.
- **You do not send it.** See below.

## Method

0. **Load `ai-detox` and `dm-style-guide`.** Before drafting, not after. Retro-fitting a voice
   onto a finished draft produces a draft with a voice fitted onto it.
1. **Gather.** `python3 tools/newsletter.py --json` for the last complete month. Read it fully
   before writing anything.
2. **Pick the spine.** One thing this month was about. Everything else arranges around it. If
   nothing stands out, say so in the lede — that is itself a reading of the month.
3. **Check the material against the corpus** for the three or four items you will actually use.
   The tool gives you counts and descriptions; read the pages behind them so the sentences are
   true rather than plausible.
4. **Write it.** Markdown, in `wiki/newsletter/YYYY-MM.md`, `visibility: internal` unless the
   owner says otherwise, `type: synthesis`.
5. **Produce the sending formats** with `python3 tools/learning_outcomes.py --format slack` and
   `--format html` for the window, and put the HTML at `docs/newsletter/YYYY-MM.html` only if the
   issue is `public`. An `internal` issue never goes in `docs/`.
6. **Open a PR and stop.** The owner reads it, edits it, and sends it. A newsletter that a model
   can mail to the team without a person reading it first is a mailing list nobody consented to.
7. **Run the draft back through `ai-detox`.** The mechanical half is the banned words. The half
   that matters is the shapes: the recap paragraph, the closing offer, the rule of three, the
   "not X but Y", the sentence whose only job is to say the last one mattered.
8. **Log it** — `## [YYYY-MM-DD] rebuild | newsletter — <month>` — and run
   `python3 tools/sync_log_index.py`.

## Sending it, when a person decides to

This skill does not send. When somebody does, the operational facts below are from
`newsletter-publishing` by Joe Amditis (`jamditis/claude-skills-journalism`), and they are the
part of that skill worth having here. The rest of it — list segmentation, A/B testing subject
lines, engagement dashboards — is for a publication chasing an audience, and importing it would
invite exactly the marketing behaviour `dm-style-guide` bans.

- **Authenticate the domain.** SPF, DKIM and DMARC. Since February 2024 Gmail and Yahoo enforce
  bulk-sender requirements, and mail that fails them is filtered rather than bounced, which means
  nobody tells you.
- **Keep the complaint rate under 0.3%.** That is the threshold the same rules impose. On a list
  of sixty colleagues it is not a metric to optimise; it is a number that should be zero, and
  anything else means the list is wrong.
- **One-click unsubscribe** has to work, on an internal list as much as a public one.

Two things follow for this newsletter specifically. It goes to people who did not ask for it, so
the first issue says who is sending it and how to stop receiving it. And a colleague list is not
a subscriber list: nobody is acquired, nobody is reengaged, and there is no campaign.

## What this skill will not do

- Send email, post to Slack, or notify anyone. Delivery needs a recipient list and credentials,
  and both belong to a person.
- Write an issue for a month still running.
- Rank, score, or compare named people.
- Fill a quiet month with padding to look busy.
