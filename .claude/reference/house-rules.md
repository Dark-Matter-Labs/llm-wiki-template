<!-- Moved word for word from CLAUDE.md on 2026-10-13 so it is read when needed, not on every turn.
     CLAUDE.md keeps every rule as a short line and points here for the reasons and the detail. -->

# The two house rules and the hard rules in full

## Hard rules

### The two house rules (xco-style-guide#11)

These are orthographic and non-negotiable, so they come before everything else:

1. **Always spell civilization with a z**, never an s.
2. **Always write xCO** — lowercase x, uppercase CO.

Rule 1 is a deliberate exception to the rest of the house's British spelling: *optionality*,
*manoeuvre* and *organising* keep their s; *civilization* does not. That is precisely the kind
of rule nobody remembers, so it is checked rather than trusted — run
`python3 tools/house_rules.py` (or `--fix`). It is a gate on every deploy.

Neither rule touches `raw/`, which is immutable: a source that says "civilisation" said that,
and correcting it would falsify the record. Verbatim blockquotes are left alone for the same
reason — they are someone else's words. Slugs, paths, domains, handles and CSS variables stay
lowercase (`xco-style-guide`, `docs/xco.md`, `--xco-tokens`); only prose is corrected. A file
that must be exempt can carry the marker `house-rules: ignore-file`.

- **Respect `visibility` at every boundary.** Content marked `private` never appears in
  exports, in PR descriptions of public repos, in published web pages, or in any external
  channel — not its body, its title, or links pointing to it. When in doubt, treat as private.
- **Knowledge, not surveillance (Indy's rule, 7 Aug 2026).** Answer questions about
  *knowledge* freely; refuse questions that *track people's activity* — "what has the owner
  been doing", "who is X talking to", "who wrote/read what, when". If a query is really
  activity-tracking dressed as a knowledge question, pause and say why: this system must
  never work as quasi-surveillance on anyone. (An owner querying their own activity in their own
  wiki is fine — the rule protects people from *each other's* queries, and binds hardest
  in the team wiki and every shared instance.)
- **Never modify `raw/`.** Read-only, always.
- **Never invent sources or citations.** If you don't have a source for a claim,
  either mark it as your own synthesis or say you don't know. Do not fabricate.
- **Never delete wiki pages unilaterally.** Flag duplicates/orphans in a lint pass
  and let the owner approve removals.
- **On every ingest, cascade.** A single source typically touches 5–15 pages
  (the new summary, plus updates to every entity/concept it mentions, plus index and log).
  Under-updating cross-references is the main way the wiki rots. Do the bookkeeping.
- **Keep the active surface small.** Merge and simplify rather than accumulate.
- **Write for the owner, not for yourself.** Plain language, clear structure, no jargon
  unless the source uses it and you've defined it.
