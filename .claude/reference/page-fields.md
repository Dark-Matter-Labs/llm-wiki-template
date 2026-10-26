<!-- Moved word for word from CLAUDE.md on 2026-10-13 so it is read when needed, not on every turn.
     CLAUDE.md keeps every rule as a short line and points here for the reasons and the detail. -->

# Page fields in full: tiers, validation, dormancy, decisions, identity, contradictions, citations

Read this before setting `visibility`, `validation`, `machine_checks`, `status: dormant`, `decides:`, `same_as:`, `contradicts:`, `derivation:` or a verification mark.

### Publication tiers — `visibility` (required)

Every page carries a `visibility` tier. **Default is `private`.** The owner opts a page up
himself, or tells you in-session; never guess a page into `public`.

- **`public`** — publishable to the open web (site + public export + external channels).
- **`unlisted`** — rendered on the site but not indexed and not linked from public
  navigation. Reachable only by direct link. Good for weekly reflections and works-in-progress.
- **`internal`** — shared with **trusted colleagues** via the shared mirror repo, but
  **never on the open web** (not the Pages site, not the public JSON graph). This is the
  tier for ordinary working knowledge — concepts, entities, source summaries — that a
  colleague needs to be useful but that isn't for publication.
- **`private`** — never leaves the repo. Excluded from every export and every external
  channel (including the colleague mirror) — not just the body, but the page's title and
  any links pointing to it. Keep CRM, capital/deal specifics, term sheets, meeting
  transcripts and unpublished positions here.

When you ingest new pages, ask the owner **once per ingest** which tier applies; with no
answer, file everything `private`. The `publish-check` skill verifies a page's tier is
consistent with its content before anything ships.

### Viz-layer fields (optional — light ontology for the frontend)

These help the frontend "lens" place a page in the right view. Set them only when a page
*clearly* belongs to a layer; leave them off otherwise (an accurate blank beats a wrong tag).

- **`layer`** — `goal` (a goal space / horizon), `portfolio` (a set of options/positions),
  `mechanism` (how something works), or `sequence` (a staged/temporal view).
- **`parent`** — the exact title of the parent page, for nesting (goal spaces nest inside goal spaces).
- **`horizon`** — `near` | `mid` | `far`, for sequence/timeline views.

### Validation — who has stood behind a page (required)

`validation` is **not** `confidence`. Confidence is what the page claims about its own
evidence; validation records **who has stood behind it**. A well-sourced page nobody has
confirmed is a different object from a hunch the group has endorsed.

- **`machine`** — you wrote or filed it; nobody has confirmed it. This is the default and
  the honest state for anything new.
- **`self`** — the owner confirmed it. Requires `validated_by`.
- **`peer`** — another member confirmed it. Requires `validated_by`.
- **`collective`** — reviewed together. Requires `validated_by`.

**You may set `machine`, and propose `self`. You may never award `peer` or `collective`** —
those need a second person, and a model granting them would make the hierarchy meaningless.

A **second frontier model** reading a page is a real signal and is recorded separately, in
`machine_checks:` — never in `validation`:

```yaml
machine_checks:
  - model: gpt-5.2
    date: 2026-08-25
    verdict: agrees | disputes | unsure
    note: one line on what it actually said
```

**A machine check may move `confidence`. It may never move `validation`.** Two models
agreeing is weaker evidence than it feels like — they were trained on overlapping corpora
and fail in correlated ways, and neither has a stake in being wrong. A `disputes` entry is
a **declaration, not a resolution**, exactly like `contradicts:`: it stands until a person
decides, and may not be deleted by the model that disagrees with it. Run the `cross-check`
skill; `python3 tools/cross_check.py --check` gates it, and refuses any `validated_by`
that names something model-shaped — the one-line shortcut that would turn the whole
gravity protection into decoration.

Validation feeds the gravity weighting: unvalidated material is admitted, indexed and
searchable, but does not yet move the corpus's centre. That is the protection against a
large body of well-formed but out-of-date thinking dragging the whole model backwards.

### Dormancy — pages retire, they do not die

`status: dormant` marks a page nobody stands behind and nothing references any more. It is a
**weight-and-visibility** change, not a deletion:

- The file stays, readable, at its URL. Nothing in this wiki is ever deleted to tidy up.
- Its catalogue row moves to `wiki/index/dormant.md` — out of the working shelves, still findable.
- `compute_gravity.py` stops counting it, so retired material cannot drag the corpus's centre.
- Waking it is symmetrical: drop the status, move the row back. Dormancy is a claim about now.

**Only a human sets it.** `lint` proposes candidates and never applies them — the same division
as contradictions, and for the same reason: deciding that a line of thinking is finished is a
judgement, and a model making it silently would quietly narrow the corpus.

The signal is `tools/staleness.py`, which reports when a page's **body** last changed, ignoring
frontmatter-only commits. Git mtime cannot be used: a schema backfill on 2026-08-12 rewrote all
766 pages, so every clock read the same 10 days in a wiki that started in March 2025. A signal
that a migration can reset measures migrations.

A page can also go stale without moving at all, when the pages it was built on move underneath it.
`tools/dependency_staleness.py` reports that: for every `synthesis`, `comparison` and `overview`
page it names the dependencies rewritten substantially since the page's own body last changed, and
ranks by how much of the change matters — how far the dependency moved times how hard the page
leans on it. **It has no `--check` and never will.** Dependency staleness is not created by the
author of the stale page; it appears when somebody *improves the page it rests on*, and a gate that
fails good work gets switched off. It is a sample that routes attention, like
`verification.py --sample 3`. Read its docstring before trusting a row: a `[[link]]` is not a
derivation, and churn is a proxy for meaning.

### Recording a decision about unmerged work — `decides:`

A page that settles what happens to work sitting on branches lists those branches in its
frontmatter, so a tool can tell a closed question from an open one:

```yaml
decides:
  - claude/read-this-jpwisz
```

`tools/waiting.py` reads it and moves those branches out of the waiting list. **The page's own
`validation` decides how they are reported.** A ruling at `machine` is shown as decided *and*
flagged — "nobody has stood behind that decision" — because a model closing a question is a
proposal that has been treated as settled, not a decision. A ruling carrying `validation: self`
or above with a `validated_by` is reported without the flag.

This exists because the inventory at [[Unmerged work — inventory of 85 pages that never reached main]]
closed a question on 2026-09-03, said in terms that it existed so nobody would re-derive it, and was
re-derived twelve days later by a tool that could not see decisions. An inbox that keeps re-raising
settled matters trains people to stop opening it.

### The same subject, in more than one wiki — `same_as:`

Measured 18 September 2026: of 172 entity and concept titles held by more than one wiki, 165
already carry `origin` — they are copies contributed up to a commons. Seven do not. They are
pages different people wrote independently about the same thing, with nothing joining them:
`Dark Matter Labs` in three wikis, `xCO` in three, `Muga Valley` in two.

```yaml
same_as: [michelle-llm-wiki/muga-valley, power-project-wiki/dark-matter-labs]
```

It records that two pages are about one subject, and nothing else. It does not merge, supersede
or rank, and it is **a person's judgement** — a model may propose one, the way it may declare a
`contradicts:`, and may not decide that two bodies of thinking are the same thing.

**Identity is symmetric; recording it is not.** A `private` page's title never leaves its repo,
so a more visible page naming one would publish that it exists. A page may therefore only point
at a target at least as open as itself:

| carrier | may name |
|---|---|
| `private` | anything — it never exports, so it can leak nothing |
| `internal` | `internal`, `public`, and the target must be visible in a commons cut read here |
| `unlisted` | `unlisted`, `public` — unlisted is reachable on the web by direct link |
| `public` | `public` |

Of the 22 possible edges among those seven subjects, 17 are legal and five are refused; every
refusal is an internal or unlisted page reaching for a private one. A non-private page must also
be able to *see* its target, because asserting that a page exists in a repository you cannot read
is not a claim this wiki can stand behind.

Gated by `python3 tools/check_same_as.py --check`, and carried into the export so the reading
interfaces can traverse it — safe by construction, since a node that survives a cut can only name
pages at least as open as itself.

### Contradictions must resolve, never sit silent

When two pages genuinely disagree, declare it on the newer page:

```yaml
contradicts: "Title of the page this disagrees with"
```

Declaring is your job; **resolving is not**. A contradiction closes only when a human adds,
to whichever page loses, either `superseded_by: "Title"` (the new position replaces it) or
`devalued_by: "Title"` (the input is downgraded). Nothing is deleted either way — the losing
page stays readable with a pointer, so plurality is preserved and only the silence is removed.
**Or both stand.** When a person decides there is no single truth, either page carries
`stands_with: "Title"` and neither loses (Leon, 16 October 2026). It closes the contradiction just as
firmly; recording both a winner and "both stand" for one pair is incoherent, and the check says so.
Run `python3 tools/contradictions.py` to see what is open.

- **`confidence`** reflects how well-supported the page is. A page built from one
  source is `low`; a synthesis confirmed across several sources is `high`. This lets
  the lint pass find pages that need re-examination when new sources arrive.
- **Cross-links** use `[[Page Title]]` wiki-link style so the graph stays navigable.
  Two ways a link silently dies, both found in the 2026-08-10 lint: **never split a wiki-link across
  a newline** (the schema check now catches this), and **never use an aliased link inside a markdown
  table** — the `|` has to be escaped as `\|` for the table, which breaks the alias parse and drops
  the edge from the graph without any visible error. In a table, use the plain `[[Full Title]]` form.
- **Every factual claim cites its source** inline, e.g. `(raw/ccc-report-2025.pdf)`.
  If a claim comes from your own synthesis rather than a source, mark it clearly as
  synthesis so the owner can tell what is grounded vs. inferred.
- **Verification is per claim, never per page** (decided 2026-09-04, from Indy's question). A
  citation says a source exists; it does not say the source supports the claim. When a *person* has
  read the cited passage and it holds, the claim carries a mark **immediately after its citation**:
  `(raw/ccc-report-2025.pdf){✓ Indy 2026-09-04}` — who read it, and when. **You may never write
  this mark.** A model confirming a model's citation is the same shortcut `validated_by` refuses,
  and `python3 tools/verification.py --check` refuses any mark naming something model-shaped; a
  second model's reading of a citation goes in `machine_checks:` with a verdict on the citation.
  *Verification* (is the claim true to its source?) and *validation* (who stands behind the page?)
  are two vocabularies on purpose — share a field and the second becomes a proxy for the first.
  Reading every citation is the cost that killed footnotes, so the instrument is the sample:
  `python3 tools/verification.py --sample 3` names the three unverified claims carrying the most
  weight — most-linked pages, weighted up where the page is already validated — one per page. That
  list, weekly, is the whole ask.
- **`derivation:`** is an optional frontmatter field you *do* set, at ingest, because it is the one
  thing about a page's provenance you can know: `source` (a reading of one source), `synthesis`
  (across several), or `derivative` (built only from other wiki pages, with no direct source — the
  layer where drift hides). Checked by `verification.py --check`; the drift itself is reported by
  `tools/dependency_staleness.py`. Set it on every page you write — at 13 of 746 it is currently
  decoration, and the wiki cannot honestly claim a derivative layer it has not labelled.
- Keep pages **small and focused**. One entity or concept per page. Prefer merging a
  new idea into an existing page over creating a near-duplicate.

### New page vs. edit-in-place
- **New page** when it is a distinct entity or concept you would link to from elsewhere.
- **Edit in place** when it is an attribute or update of something that already exists.
