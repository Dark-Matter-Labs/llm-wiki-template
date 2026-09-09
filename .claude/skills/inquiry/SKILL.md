---
name: inquiry
description: Bring a live problem to the corpus and get back what it holds — framed as Goal → Target → Search, with hypotheses and their sources, across every commons this wiki can read. Use when the owner says "I have a problem, help me think", "what would the wiki tell us to do about…", "how would you write this contract / brief / plan given everything we know", "run an inquiry on…", or asks for hypotheses rather than a summary. The inquiry-native way of using the system, named as a skill so it can travel.
---

# Inquiry — ask the corpus what to do, not what it says

## Where this came from

Two members had been using their wikis this way for a month before anyone named it. On the
9 September 2026 INO call one of them described it plainly: *"we're actually saying, I have a
problem, I want you to help me fix this."* The worked case was a contract for a contractor
starting a position in Santiago — take the best of what the wikis hold about Many-to-Many
agreements, participatory decision-making and the legal rules those run into, and say how the
contract should be written. The corpus *"started to produce some really interesting hypotheses."*

That is a different move from `query`. A query asks what the wiki says. An inquiry brings a
live decision and asks what the wiki would have you do — and returns hypotheses, each traceable
to the pages and sources that support it, framed so the actions stay subordinate to the question
they serve. It is the skill the `office-hours` skill points toward but does not do: office-hours
sharpens an idea before you invest in it; inquiry takes a problem you already have and searches
the whole federation for an answer.

The framing borrows the Goal / Target / Search logic already in this federation's design: a
durable **Goal** (why), a versioned current-best-guess **Target** (where), and an exploratory
**Search** (hunches, hypotheses, instruments) between them, with a deliberate rule against any
middle tier. Actions are not banned — they are instruments, and belong under the Target they test.

## When it fires

- The owner brings a **decision**, not a topic: a contract to write, a brief to draft, a position
  to take, a partner to approach, a design choice to make.
- The owner asks for **hypotheses** or **options**, not a summary.
- Before finalising any answer to *what should we do*, *what's next*, or *how would you structure
  this*, run the framing check below on your own draft — the natural default, for a person or a
  model, is to write a task list with no question behind it.

## Method

1. **State the problem back, as a question.** One sentence. If the owner has given you a task
   ("write the contract"), say what the task is trying to settle ("what agreement shape lets a
   contractor in Santiago work in the Many-to-Many way without the legal exposure a plain
   grant contract avoids?"). If you cannot name the question, ask one clarifying question — do
   not invent a question to make the frame tidy.

2. **Search the whole federation, not just this wiki.** Run the local search, then search every
   commons this wiki reads (`.commons/<name>/`). Say which wikis you searched. A page a colleague
   contributed to the commons is exactly the material an inquiry exists to reach; that is what the
   commons is for.

3. **Read the shortlist and extract hypotheses.** Each hypothesis is one sentence, testable, and
   carries the pages and raw sources it rests on — with the wiki each came from, because a claim
   from a colleague's contributed page is theirs, not this wiki's. Mark which hypotheses the
   corpus *supports*, which it *complicates*, and where it is *silent*. Silence is a finding.

4. **Frame it.** Return:
   - **Goal** — the durable inquiry this problem sits under. Use an existing `type: goal` page or
     an existing Target if one fits; if none does, **say so** — a missing Goal is a finding, and
     inventing one is worse than the gap.
   - **Target** — the current live question, versioned by date.
   - **Search** — the hypotheses, each with its sources and confidence.
   - **Instruments** — the concrete actions, each stated as *what it tests*. The contract clause,
     the person to call, the draft to write. These are legitimate and necessary; they are simply
     not free-floating.
   - **What resists the frame** — a hard deadline, a funder requirement, a legal constraint. These
     stay as facts. The frame subordinates action to inquiry; it does not pretend constraints away.

5. **Check your own draft.** Before sending: does every instrument name the question it serves?
   If one just "needs doing", either find its question or say it has none.

6. **Offer to file.** A good inquiry is knowledge. Propose a `synthesis` page — `private` in a
   personal wiki, `internal` in a commons — carrying the Target, the hypotheses and their sources,
   and `derivation: derivative` or `synthesis` as appropriate. Ask first; then also propose
   whether it should travel up via `contribute`.

7. **Log it.** Append `## [YYYY-MM-DD] query | inquiry: <the question>` to today's log file and
   run `python3 tools/sync_log_index.py`. It borrows the `query` prefix on purpose: an inquiry is
   a question asked of the corpus, and the log's greppable prefixes should stay few.

## Output shape

```
The question: <one sentence>

Searched: <this wiki> · <commons 1> · <commons 2>   (say what was NOT reachable)

Goal:   <existing goal page, or "none exists — this is a gap">
Target: <the live question, dated>

Hypotheses (Search):
  H1. <one sentence>  — supported by: <page> (<wiki>), <page> (<wiki>); source: <raw/...>
  H2. <one sentence>  — complicated by: <page>; the corpus is split on this
  H3. <one sentence>  — the corpus is SILENT; this is inference, marked as such

Instruments — what each one tests:
  - <action>  → tests H1
  - <action>  → tests H2 and H3 together

What resists the frame: <constraints, stated as facts>

Offer: file this as a synthesis page? contribute it to <commons>?
```

## Rules

- **Never invent a Goal or Target.** If the corpus has none, the answer says so. A fabricated
  inquiry is worse than an honest gap, because it looks like orientation.
- **Say where every hypothesis came from, including which wiki.** A colleague's contributed page
  is theirs. Provenance is the whole basis on which a commons can be trusted.
- **Actions are not banned.** Over-correcting into refusing to name a next step is its own
  failure. The check is whether an action floats free of any question, not whether action exists.
- **Knowledge, not surveillance.** An inquiry searches pages and sources. It never answers by
  reporting what a named person has been doing, reading or writing; if the problem is really
  "what is X up to", say so and stop.
- **This skill reads; it does not decide.** It hands back hypotheses for a person to choose
  among. The `contribute` consent step is theirs; so is the contract.
- Where a wiki also carries `.claude/skills/inquiry-check/` (a member's own, on-demand framing
  check), that skill is the strict sibling of step 5 here and should be preferred for a pure
  framing pass.
