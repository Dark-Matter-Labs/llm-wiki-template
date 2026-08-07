# Wiki index

The catalogue of every page in this wiki. Claude reads this **first** when answering a
question, and updates it on **every** ingest. Treat it as a routing file — it exists so
nobody (human or model) has to scan the whole wiki to find something.

Each entry is one line: a link, its type, and a one-line summary of what's on the page.

> **New wiki?** Everything below the examples is empty on purpose. Add a source to `raw/`
> and say *"ingest this"* — Claude writes the summary page, cascades the cross-references,
> and files the entry here. See [SETUP.md](../SETUP.md) if you haven't finished setup.

---

## Map of the wiki

- **[Overview](overview.md)** — the big-picture map of what this wiki knows.
- **[Axioms Register](axioms.md)** — the foundational assumptions the work rests on.
- **[Log](log.md)** — the dated record of every ingest, query, and health check.

---

## Examples _(delete once you have real content)_

- **[Greenline programme — briefing note](examples/greenline-summary.md)** — `summary` —
  a fictional outcomes-based financing programme, included to show what an ingested
  source looks like.
- **[Outcomes-based financing](examples/outcomes-based-financing.md)** — `concept` —
  the concept page the example summary cascades into.

Say *"delete the example files"* once you've added real sources.

---

## Concepts

_Nothing yet._

## Entities

People, organisations, places, projects, tools, programmes.

_Nothing yet._

## Source summaries

One per ingested document in `raw/`.

_Nothing yet._

## Comparisons

_Nothing yet._

## Syntheses

The evolving "what it all means so far" pages.

_Nothing yet._

## Challenges & reflections

Counterposition briefs from `joker` live in `challenges/`; weekly reflections in
`reflections/`. Both directories are created on first use.

_Nothing yet._
