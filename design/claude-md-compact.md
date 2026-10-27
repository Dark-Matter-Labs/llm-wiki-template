<!-- The compact CLAUDE.md sections every wiki shares, from the source wiki. tools/slim_claude_md.py puts them in place of the template's long ones. Edit them in the source wiki's CLAUDE.md, then run --write-compact there. -->

## Hard rules

- **Always spell civilization with a z. Always write xCO** (lowercase x). Run `python3 tools/house_rules.py`. Neither
  rule touches `raw/` or a verbatim quotation; slugs and paths stay lowercase.
- **Respect `visibility` at every boundary.** `private` never appears in exports, PR descriptions, published pages or
  any external channel: not its body, its title or links to it. When in doubt, treat it as private.
- **Knowledge, not surveillance.** Answer questions about knowledge; refuse ones that track people's activity
  ("who is X talking to", "who wrote what, when"), and say why. An owner asking about their own activity in their
  own wiki is fine; the rule binds hardest in shared wikis.
- **Never modify `raw/`. Never invent sources or citations. Never delete wiki pages unilaterally** (flag them).
- **On every ingest, cascade**: the summary plus every entity and concept it touches, the index and the log.
- **Keep the active surface small**, and **write for the owner**: plain language, no undefined jargon.

## Page types

`summary` (one per source) · `entity` (person, org, place, project, tool, programme) · `concept` (an idea spanning
sources) · `comparison` · `overview` (`wiki/overview.md`, kept current) · `synthesis` (the evolving thesis) ·
`goal` (a destination; carries `horizon`, and `parent` when goals nest) · `commitment` (resources against a goal:
needs `commits_to`, `resources`, `until`, `state`: `proposed | held | honoured | revised | lapsed | exited | declined`;
`declined` and `exited` are never failures, only `lapsed` counts against a goal). Progress is computed by
`python3 tools/goals.py`, never typed.

## The core operations

Each skill in `.claude/skills/` says when it fires; read its SKILL.md before running it. The common ones:
add a source, `ingest` · a question, `query` · "check the wiki", `lint` · "catch me up", `brief` · a new idea,
`office-hours` · "sharpen this", `sharpen` · "share this with the team", `contribute` · contacts and meetings, `crm` · "what's waiting", `waiting`
· "what don't we know", `open_questions.py` then `inquiry` · call notes, `call-notes` · "that's done", `my-commitments`
· a brief for a meeting, `pre-read` · "is this inquiry-native", `ino-check` · "have my sources changed", `source-refresh` · "something leaked", `retract` · "refresh the lens", `lens-refresh` · "set up my customisations", `customise`. If unsure, see `.claude/reference/operations.md`.
If intent is ambiguous, ask **one** short question, then proceed.

- **The Axioms Register** (`wiki/axioms.md`) holds the corpus's foundational assumptions; `joker` and `reflect` read it.
  Keep it in step with [[The Core Assumption Chain]] where the wiki has that page.
- **The CRM** (`wiki/crm/`) is **always `private`**: never published, exported or mirrored. Calendar access is
  read-only; writing to it needs the owner's yes each time. Never fabricate relationship state.
- Published pages live in `docs/`, served at `https://dark-matter-labs.github.io/<this wiki's name>/`.

## The index and the log

- `wiki/index.md` is the **router**; catalogues sit on shelves under `wiki/index/` where the wiki has them. Load a shelf
  only when a question is squarely in it. Every ingest adds the new page's **one-line** row. Counts are computed by
  `tools/sync_index_counts.py` where it exists, and never typed.
- The log is **one file per day**, `wiki/log/YYYY-MM-DD.md`. Append to today's file (create it with the usual header),
  then run `python3 tools/sync_log_index.py`. Never rewrite a past day; correct by appending. To read the log, read
  today's file first, then walk back through the month index.
- Every ingest, query and lint gets one entry, prefixed `## [YYYY-MM-DD] ingest | …` (or `query`, `lint`,
  `rebuild` for an advance, `repair` for a defect fixed: a repair of your own error reads `repair | … (mine)`; work that does both is a `rebuild` naming what it repaired).

## The three layers (never blur them)

1. **`raw/`**: the sources the owner curates. **Immutable**: read them, never edit or delete them. Images in `raw/assets/`.
2. **`wiki/`**: the pages you own and write. Summaries, entities, concepts, comparisons, the overview, syntheses.
3. **`CLAUDE.md`, `.claude/skills/` and `.claude/reference/`**: the rules and workflows, co-evolved with the owner. If a
   workflow keeps needing the same correction, propose an edit to the skill or to this file.

**Detail lives in `.claude/reference/`, read only when the work needs it** (moved there 2026-10-13 to save tokens on
every turn; nothing was removed). Read the named file *before* doing that kind of work:

| Before you… | read |
|---|---|
| set `visibility`, `validation`, `machine_checks`, dormancy, `decides:`, `same_as:`, `contradicts:`, `derivation:`, or a verification mark | `.claude/reference/page-fields.md` |
| edit `wiki/index.md`, a shelf, or the log | `.claude/reference/navigation-and-log.md` |
| decide which skill or tool fits a request not in the list below | `.claude/reference/operations.md` |
| touch the house rules or any hard rule's edge case | `.claude/reference/house-rules.md` |

## Wiki page conventions

Every page in `wiki/` (except `index.md` and `log.md`) starts with YAML frontmatter:

```yaml
---
type: entity | concept | summary | comparison | overview | synthesis | goal | commitment
title: Human-readable title
description: One sentence describing the page
tags: [tag1, tag2]
status: draft | reviewed | dormant
visibility: public | unlisted | internal | private   # default: private
confidence: high | medium | low
validation: machine | self | peer | collective       # default: machine
timestamp: YYYY-MM-DD
sources: [raw/filename.pdf, raw/other.md]
# optional viz-layer fields (set only when the page clearly belongs to a layer):
layer: goal | portfolio | mechanism | sequence   # which frontend view it belongs to
parent: "Title of parent page"                    # nesting (goal spaces nest)
horizon: near | mid | far                         # for sequence views
---
```

- **`visibility`** (required, default `private`): `public` (open web) · `unlisted` (on the site, not indexed) ·
  `internal` (colleagues via the shared mirror, never the open web) · `private` (never leaves the repo: not its
  body, title or links to it). The owner opts a page up; never guess a page into `public`. Ask the tier **once per
  ingest**; with no answer, file `private` (or the default this file's own rules set, as a
  commons does). Keep the CRM, capital and deal specifics, term sheets, meeting transcripts and unpublished
  positions `private`. The `publish-check` skill verifies a tier before anything ships.
- **`validation`** (required, default `machine`) records who stood behind a page; `confidence` is the evidence.
  You may set `machine` and propose `self`; **never award `peer` or `collective`**. `self`/`peer`/`collective`
  need `validated_by`. A second model's reading goes in `machine_checks:` and may move `confidence`, never
  `validation`; a second model's reading of a citation goes there too. A `disputes` entry stands until a person
  decides. Run the `cross-check` skill for it.
- **Viz-layer fields** (`layer`, `parent`, `horizon`): only when a page clearly belongs to a layer.
- **`status: dormant`** retires a page without deleting it. **Only a human sets it**; `lint` proposes candidates.
- **`decides:`** lists the branches a page settles; `tools/waiting.py` reads it.
- **`same_as:`** records two pages are one subject. A person's judgement; you may propose. A page may only name a
  target at least as open as itself, and a non-private page only one it can see (`tools/check_same_as.py --check`).
- **`contradicts: "Title"`** goes on the newer page when two pages disagree. Declaring is your job, resolving is
  not: a human adds `superseded_by` or `devalued_by`, or `stands_with` when both stand. Nothing is deleted. `python3 tools/contradictions.py`.
- **`confidence`**: one source is `low`; confirmed across several is `high`.
- **Links** are `[[Page Title]]`. Never split one across a newline; in a table use the plain `[[Full Title]]` form.
- **Every factual claim cites its source** inline, e.g. `(raw/ccc-report-2025.pdf)`; mark your own synthesis as such.
- **Verification is per claim.** A person's mark after a citation reads `{✓ Name YYYY-MM-DD}`. **You may never write
  this mark.** `python3 tools/verification.py --sample 3` names the claims worth a person's reading.
- **`derivation:`** (`source` | `synthesis` | `derivative`): set it on every page you write.
- Keep pages **small and focused**: one entity or concept each. A distinct thing you would link to gets a new page;
  an attribute or update of an existing one is edited in place. Prefer merging over near-duplicates.

## Working style

Lead with substance, not process narration. Separate what a source says from what you infer. Flag contradictions
rather than smoothing them over. Say plainly when something is uncertain or thin.
