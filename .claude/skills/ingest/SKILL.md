---
name: ingest
description: Add a new source to the wiki. Use whenever the owner drops a document into raw/ or says "add this", "ingest", "here's a new report/paper/article", or pastes/links content they want filed. Reads the source, writes a summary page, and cascades updates across all affected entity, concept, index, and log pages.
---

# Ingest a source

The single most important operation. Done well, the wiki compounds. Done lazily
(summary only, no cascade), the wiki rots. Do the full cascade every time.

## Steps

1. **Locate the source.** It will be in `raw/`. If the owner pasted or linked something
   that isn't saved yet, save it into `raw/` first (with a clear filename), because
   raw is the source of truth. For images referenced by a document, note them —
   read the text first, then view specific images separately if you need them.

2. **Read it fully.** Don't skim. Extract: what it argues, key facts and figures,
   people/orgs/places/projects/tools it names, concepts it introduces or touches,
   and anything that contradicts or confirms what the wiki already holds.

3. **Discuss briefly with the owner.** Give them 3–5 key takeaways in plain language
   before you start filing, so they can steer what to emphasise. Keep it short.
   **Ask the visibility tier once, here** — "Should these pages be public, unlisted, internal
   or private?" If there is no answer, file everything at **this wiki's default tier**: `private`
   in a personal wiki (it can be opted up later), `internal` in a commons — a commons is shared by
   construction, and a page left `private` there is a page the other members cannot see. Apply the
   same tier to every page created or updated in this ingest unless told otherwise.

4. **Write the summary page** at `wiki/<slug>-summary.md` with full frontmatter
   (`type: summary`, `visibility:` set from step 3, the source in `sources:`, a
   `confidence` reflecting how much corroboration exists). Cite the source inline on
   factual claims. **Set the viz-layer fields** (`layer`, and `parent`/`horizon` where
   they apply) *only when the page clearly belongs to a layer* — a goal space, a
   portfolio, a mechanism, or a sequence. Leave them off when it's not obvious; an
   accurate blank beats a wrong tag.

5. **Cascade — this is the part people skip.** For every entity and concept the
   source names:
   - If a page exists, update it: add the new facts, add a `[[link]]` to the summary,
     bump its `timestamp`, and adjust `confidence` if the new source corroborates or
     challenges it. If it contradicts an existing claim, **flag the contradiction on
     the page** rather than silently overwriting.
   - If no page exists and it's something you'd link to from elsewhere, create it.
   - Add `[[wiki-links]]` in both directions so the graph stays connected.

6. **Update `wiki/overview.md`** if this source shifts the big picture.

7. **Update the catalogue** — add every new page with a **genuinely one-line** summary
   under the right category. This is mandatory.

   The index is tiered: `wiki/index.md` is the router, and the rows live on shelves under
   `wiki/index/` (`concepts.md`, `summaries.md`, `overview-synthesis.md`). A new concept
   row goes on the concepts shelf; the small sections are still inline on the router.
   Then run `python3 tools/sync_index_counts.py` — the counts are computed, never typed.
   *(That tool carries a router-specific pattern block and so exists only in the wikis whose
   index is tiered. Where it is absent, the index has no computed counts to sync — skip it.)*

   **One line means one line.** The rows drifted to a median of 294 characters and a worst
   case of 4,400 before the split, which is how the catalogue became a second corpus and
   routing came to cost more than reading. A row exists to let a reader decide whether to
   open the page — not to save them the trip.

8. **Append to the today's log file (`wiki/log/YYYY-MM-DD.md`; see `wiki/log.md`):** `## [YYYY-MM-DD] ingest | <Source Title>` plus a
   one-line note of what it touched (e.g. "new summary + updated 4 entities, 2 concepts").

9. **Report back in plain language.** Tell the owner what you learned and what pages
   changed, framed so his PR review is easy. Lead with the knowledge, not the filenames.

## Rules
- Never edit `raw/`.
- Never fabricate a citation. Mark your own synthesis as synthesis.
- Prefer merging into an existing page over creating a near-duplicate.
- One source can and usually should touch many pages. That's correct, not excessive.
- **Default new pages to `visibility: private`.** Only mark `public`/`unlisted` when the owner
  says so. When you update an *existing* page during the cascade, keep its current
  `visibility` — never quietly change a page's tier.
