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

`summary` · `entity` · `concept` · `comparison` · `overview` · `synthesis` · `goal` · `commitment`. Each is defined in
`.claude/reference/page-fields.md`. Goal progress is computed by `python3 tools/goals.py`, never typed.

## The core operations

Each skill says in its description when it fires. Read its SKILL.md before you run it. If no skill fits, read
`.claude/reference/operations.md`. If the intent is unclear, ask **one** short question, then go on.

- **The CRM** (`wiki/crm/`) is **always `private`**: never published, exported or mirrored. Calendar access is
  read-only. Writing to a calendar needs the owner's yes each time. Never invent relationship state.
- Published pages live in `docs/`, served at `https://dark-matter-labs.github.io/<this wiki's name>/`.

## The index and the log

- `wiki/index.md` is the **router**. Every ingest adds the new page's **one-line** row to it or its shelf.
- The log is **one file per day**, `wiki/log/YYYY-MM-DD.md`. Append, never rewrite a past day, then run
  `python3 tools/sync_log_index.py`. Entry prefixes are in `.claude/reference/navigation-and-log.md`.

## The three layers (never blur them)

1. **`raw/`**: the sources the owner curates. **Immutable**: read them, never edit or delete them. They are the ground
   truth every page is checked against. Images in `raw/assets/`.
2. **`wiki/`**: the pages you own and write. They exist so the next question costs less than this one.
3. **`CLAUDE.md`, `.claude/skills/` and `.claude/reference/`**: the rules and workflows, co-evolved with the owner. If a
   workflow keeps needing the same correction, propose an edit to the skill or to this file.

**Detail lives in `.claude/reference/`, read only when the work needs it.** Nothing was removed when it moved there.
Read the named file *before* doing that kind of work:

| Before you… | read |
|---|---|
| set any page field beyond the basics below, or a verification mark | `.claude/reference/page-fields.md` |
| edit `wiki/index.md`, a shelf, or the log | `.claude/reference/navigation-and-log.md` |
| decide which skill or tool fits a request | `.claude/reference/operations.md` |
| touch the house rules or any hard rule's edge case | `.claude/reference/house-rules.md` |
| write about capital, funds, term sheets or capital calls | `.claude/reference/capital-vocabulary.md`, where it exists |
| change a file other wikis share, or a rule in `.claude/rules/` | `.claude/reference/shared-changes.md`, where it exists |

## Wiki page conventions

Every page in `wiki/` (except `index.md` and `log.md`) starts with frontmatter: `type`, `title`, `description`, `tags`,
`status`, `visibility`, `confidence`, `validation`, `timestamp`, `sources` and `derivation`. The full schema is in
`.claude/reference/page-fields.md`.

- **`visibility`** defaults to `private`. The owner opts a page up. Never guess a page into `public`. Ask the tier
  once per ingest.
- **`validation`**: you may set `machine` and propose `self`. **Never award `peer` or `collective`.**
- **Never write a verification mark** (`{✓ Name YYYY-MM-DD}`). Only a person writes one.
- **Every factual claim cites its source** inline, e.g. `(raw/ccc-report-2025.pdf)`. Mark your own synthesis as such.
- **One thing per page.** Quote exact terms, figures and dates word for word on that thing's own page. A table that
  compares things links to those pages and is never the only copy.
- **Links** are `[[Page Title]]`, never split across a line.

## Working style

Lead with substance, not process narration. Separate what a source says from what you infer. Flag contradictions
rather than smoothing them over. Say plainly when something is uncertain or thin.
