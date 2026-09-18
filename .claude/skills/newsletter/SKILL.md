---
name: newsletter
description: Write the monthly issue — what the wikis learned, in something people will actually read. Fires on the first working day of each month, and when the owner says "write the newsletter", "do the monthly", "what went out this month". Replaces the weekly reflection, which nobody read.
---

# The monthly newsletter

## Why this exists, and why monthly

The weekly reflection ran every Friday from week 28 to week 36. Measured on 2026-09-15:

| | |
|---|---|
| ordinary pages that ever cited a reflection, of 819 | **7** |
| of its 30 inbound links, how many came from the joker pages the same run wrote | 17 |
| times W35 and W36 were touched after being written | **1 each** |
| times W30 was touched after being written | 4 |
| workflow runs · of which failed | **15 · 5** |

Attention decayed from four touches to one. Seven pages of 819 ever cited one, and most of the
links a reflection does have were written by the same Friday run. The run
on 11 September failed and nobody noticed. It also called the model every Friday, billed outside
the Team plan.

None of that is a prose problem. **A week is not long enough to have something worth saying**, and
paying for a weekly artefact nobody reads makes it worse rather than better. So: monthly, written
properly, and sent to people rather than left in a folder to be found.

## The split — and keep it

`python3 tools/newsletter.py --json` does the arithmetic: the patterns the corpus has formed and
which have no name, the terms rising and falling in its centre, what is committed against which
goal, how much of the month was repair rather than advance, and what is still unanswered. It is
deterministic, costs nothing, and calls no model. **Start there, every time.** Do not recompute
what it already knows and do not contradict it — if a number here disagrees with the tool, the
tool is right and the draft is wrong.

Your job is the half a script cannot do: deciding what is worth saying, and saying it well.

### The corpus is at HEAD. The month is not.

`newsletter.py` computes the window. The wiki you are standing in is today's, and for a month
that closed weeks ago the two are different objects. **Every count, state and total comes from
the material, and never from reading the pages.**

The August 2026 issue was written on 18 September and said Goal 3 "carries all eleven
commitments in the ledger, ten of them held", and that one person had stood behind a goal. The
material for August said two commitments — one proposed, one held — and nobody standing behind
anything. Eleven and the endorsement were true on the day it was written and false for the month
it described: nine of those commitment pages were filed on 15 and 16 September, and the
endorsement is dated the 16th. Nothing was invented. The corpus was simply asked a question
about the present in a report about the past.

So, concretely:

- **Counts, states, dates, totals, who validated what — the material, always.** If it is not in
  `signals`, it does not go in the issue. Not from `goals.py`, not from the frontmatter, not from
  a page you happened to read.
- **Read pages for prose, never for arithmetic.** A page's own one-line description, or a
  sentence somebody actually wrote, is why you open it. Three or four pages, the ones behind the
  items you are actually using.
- **A page may have changed since the month ended.** When you quote one, you are quoting today's
  wording of it, which is fine for a line of prose and wrong for a number.

This is also most of what the issue costs. The August run took 54 turns and $1.74, and the
reading is where that went — the writing is a few hundred words.

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

## What the issue is about

**Not the movements of the wiki.** How many pages arrived, and of which type, is a changelog.
Nobody has ever wanted to read one. The counts are in the material because they set the scale of
a month, and they belong in one sentence at most.

The issue is about what the corpus is **thinking**. Five things carry that, and `newsletter.py`
gathers all five deterministically so the writing is judgement rather than arithmetic.

**Patterns, and what has no name yet.** `signals.patterns` reports the clusters the corpus has
formed and how many have no page saying what the idea is. An unnamed cluster is the most
interesting object this system produces: seven pages from seven sources that hang together
tightly, with nobody having said what holds them. Name two or three of them by their tags and
members and let the reader see the shape. If a cluster spans more than one wiki, say so, because
a pattern that travels is a different claim from one that does not.

**Anti-patterns, which are mostly in the corrections.** `signals.corrections` splits the month
into advances and repairs, and marks which repairs fixed the model's own earlier error. That
split exists so the correction rate is visible without a metacognition pass. Report it plainly,
including the share. The repeated shapes are the real content: a check that could not fire, a
mechanism that announced its failure into a log nobody reads, a number that was green for the
wrong reason. Name the shape, not only the incident. This is the section people trust most,
because almost nobody publishes theirs.

**The vectors on goals and commitments.** `signals.goals` gives, per commons, how many goals
exist, how many have nothing committed against them, what states the commitments are in, how
many goals a person has stood behind, and what moved this month. A goal with no commitment is a
statement of intent; a goal with a held commitment is a position. Say which is which.
**`declined` and `exited` are not failures.** Refusing, or leaving deliberately, is a valid
outcome, and only `lapsed` counts against a goal. Rendering the other two as failure misreports
somebody's decision.

**The trajectory of ideas.** `signals.trajectory` gives the size of the shift in the corpus's
centre across the window, and which terms rose and which fell. This is the only measurement that
says where the thinking is going rather than what it accumulated. Rising terms are usually the
month's real subject, and they often name it better than any page title does. Read the falling
list too: a term leaving the centre is a position quietly being dropped, and that is worth a
sentence.

**What is still unsettled.** `signals.unsettled` counts the questions the corpus has written down
and not answered, and which are waiting on a named person. Quote one or two verbatim. A question
stated plainly enough that a reader could answer it is the most useful thing an issue can carry.

Then, and only then, the ordinary movements, in rough order of interest: a position that changed;
a decision that closed an argument; what came in. The last of those is least surprising and goes
last, briefly.

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
   before writing anything, and read `signals` first. A signal whose tool is missing from this
   wiki says so; report the blank as a blank and never fill it with a guess.
2. **Pick the spine.** One thing this month was about. It is almost always in `signals`: a
   pattern nobody has named, a term that rose, a goal that gained or lost its backing, a shape
   the repairs kept repeating. Everything else arranges around it. If nothing stands out, say so
   in the lede — that is itself a reading of the month.
3. **Open the three or four pages behind the items you will actually use** — for their words,
   not their numbers. The tool has given you every figure already; what a page adds is a line
   worth quoting and the texture that makes a sentence true rather than plausible. See "The
   corpus is at HEAD" above: reading further costs money and imports the present into a report
   about the past.
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
