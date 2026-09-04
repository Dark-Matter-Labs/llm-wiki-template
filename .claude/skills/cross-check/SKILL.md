---
name: cross-check
description: Have a different frontier model read a page and record what it said, in `machine_checks:`. Use when the owner says "cross-check this", "get a second opinion", "what would another model say", or "check this against GPT/Gemini" — and from the validation pass when it decides enough new material has landed. A machine check may move `confidence`; it may never move `validation`.
---

# Cross-check

Have a **different frontier model** read a page and say whether it agrees, then record
what it said.

## The one rule

> **A machine check may move `confidence`. It may never move `validation`.**

`validation` records *who has stood behind a page*, and it is load-bearing: pages nobody
has confirmed are indexed and searchable but do not move the corpus's centre of gravity.
That protection is worth exactly as much as the requirement that `self`, `peer` and
`collective` mean a person. A second model is not a second person — it has no stake in
being wrong, cannot be asked what it meant in six months, and fails in ways correlated
with yours, because you were trained on overlapping corpora. Two models agreeing is
weaker evidence than it feels like.

`confidence` is different. It is a claim about how well-supported the page is, and that is
precisely what a second careful reader can speak to.

`python3 tools/cross_check.py --check` enforces this and runs in CI. It refuses any
`validated_by` that names something model-shaped.

## Running a check

**1. Pick the page.** If nobody has named one:

```
python3 tools/cross_check.py --due
```

This queues pages that are **load-bearing but weakly supported** — many inbound links,
`confidence` below high, no check on record. A wrong claim on a page 139 others depend on
propagates; a wrong claim on a leaf does not.

**2. Build the packet.** Assemble, in one block a member can paste elsewhere:

- the page in full;
- the *relevant extracts* from every file in its `sources:` — never your summary of them,
  or the second model is checking your reading rather than the source;
- this prompt:

  > Below is a wiki page and the source extracts it cites. For each factual claim on the
  > page, say whether the sources support it, contradict it, or are silent. Do not improve
  > the page. Do not add claims. End with one word — AGREES, DISPUTES, or UNSURE — and one
  > sentence saying why.

Three things make this worth doing, and all three are easy to skip: **give it the sources,
not your reading of them**; **ask it to check, not to improve** (a model asked to help will
rewrite and you will learn nothing); and **run it in a fresh context** with no access to
this wiki, so it cannot agree with you by having read you.

**3. Record the verdict** in the page's frontmatter:

```yaml
machine_checks:
  - model: gpt-5.2
    date: 2026-08-25
    verdict: agrees | disputes | unsure
    note: one line on what it actually said
```

**4. Move `confidence`, if warranted.**

| What happened | Do |
|---|---|
| Two or more different models agree, sources cited | may raise `confidence` one step |
| One model agrees | record it; change nothing |
| `unsure` | record it; change nothing |
| `disputes` | **lower `confidence`**, and `high` becomes forbidden |

Never raise to `high` on machine agreement alone. `high` means the corpus confirms it
across sources, which is a claim about evidence you can point at, not about assent.

**5. Never resolve a dispute yourself.** A `disputes` entry is a declaration, exactly like
`contradicts:` — it stands, visible, until a person decides. You may not delete a dispute
because you disagree with it. If the second model is plainly wrong about a fact, say so in
the `note` and leave the entry.

## Logging

One entry per pass:

```
## [YYYY-MM-DD] cross-check | <page title> — <model> <verdict>
```

Append it to today's day file (`wiki/log/YYYY-MM-DD.md`), then run
`python3 tools/sync_log_index.py`.

Say what the other model actually objected to, not that a check occurred. A pass that
found nothing is worth one line; a pass that found something is worth the detail.

## Cadence

`python3 tools/validation_due.py` already decides when enough new material has landed to
be worth a pass, so cost tracks use rather than the calendar. Use it to decide *whether*,
then `--due` to decide *what*.

## Hard rules

- Never write a model name into `validated_by`. CI refuses it, and the refusal is the point.
- Never let a machine check raise `validation` by any route.
- Never delete or edit a recorded check to make a page look better.
- Give the second model the sources, not your summary of them.
