# Export contract

The stable, versioned contract between this wiki and the frontend **lens** that renders it.
Produced by `tools/export.py`. The lens should build against this document, not against
individual wiki pages.

**`schema_version`: `1.0`** — carried in `meta.schema_version` of every export. Any change to
the shape below **bumps this version**. Consumers should check it and fail loudly on a major mismatch.

---

## Files

| File | Contents | Deployed? |
|------|----------|-----------|
| `export/wiki.json` | **Everything** — every page including `private`. | No. Stays in the repo / `export` branch. Never served to the public web. |
| `export/wiki.public.json` | **Public + unlisted only.** Every `private` page is fully removed (node, title, and all link edges to/from it), and private link markup is stripped from published bodies. `unlisted` pages are included and flagged. | Yes — this is the only file safe to serve publicly. |

Both files are produced together and are byte-identical in shape (same schema); they differ only
in which nodes and edges are present.

---

## Top-level shape

```json
{
  "meta": {
    "schema_version": "1.0",
    "kind": "full" | "public",
    "exported_at": "ISO-8601 UTC timestamp",
    "node_count": 287,
    "counts_by_type": { "summary": 171, "concept": 74, "...": 0 },
    "counts_by_visibility": { "private": 285, "unlisted": 1, "public": 1 }
  },
  "nodes": [ Node, Node, ... ]   // sorted by slug
}
```

## Node

```json
{
  "id": "madrid",                    // == slug; stable identifier
  "slug": "madrid",                  // path under wiki/ without .md (may contain "/", e.g. "examples/greenline-summary")
  "title": "Madrid",                 // human title (frontmatter title)
  "type": "entity",                  // entity | concept | summary | comparison | overview | synthesis
  "layer": "portfolio" | null,       // goal | portfolio | mechanism | sequence | null (optional)
  "parent": "Title of parent" | null,// nesting (optional)
  "horizon": "near" | null,          // near | mid | far | null (optional, sequence views)
  "tags": ["madrid", "place"],
  "confidence": "high",              // high | medium | low
  "visibility": "public",            // public | unlisted   (never "private" in the public file)
  "timestamp": "2026-07-10",
  "description": "One-sentence description.",
  "sources": ["raw/....pdf"],        // provenance (best-effort parse; not load-bearing)
  "body": "markdown string\n",       // full page body (markdown, after frontmatter)
  "outbound_links": ["other-slug"],  // resolved [[wiki-links]] -> slugs (unresolved/external links dropped)
  "inbound_links": ["some-slug"]     // reverse edges, computed over the node set in THIS file
}
```

### Notes for consumers
- **`id` / `slug`** are the join key for edges. `outbound_links` / `inbound_links` are arrays of slugs.
- **Edges are scoped to the file.** In `wiki.public.json`, `inbound_links`/`outbound_links` are
  recomputed over the public node set only — they never reference a private slug.
- **Links** come from `[[Title]]` / `[[Title|display]]` in the body, resolved via title→slug.
  Links that don't resolve to a page (external references, deliberate "write-later" markers) are
  **not** emitted as edges.
- **Optional fields** (`layer`, `parent`, `horizon`) are `null` when unset. Don't assume presence.
- **Navigation/stub files** (`index.md`, `log.md`, folder `README.md`s) have no frontmatter and are
  **not** nodes.

---

## Visibility semantics (the guarantee)

- **`private`** — excluded from `wiki.public.json` entirely: no node, no title, no inbound or
  outbound edge referencing it; and any `[[link]]` to it in a published body is neutralized
  (piped display kept, bare link redacted). This invariant is enforced by `tools/export.py` and
  tested by `tools/test_export.py::test_private_leaks_nothing`.
- **`unlisted`** — present in `wiki.public.json`, flagged `"visibility": "unlisted"`. The lens
  should render it but **must not** list it in public navigation or emit it to indexers/sitemaps.
- **`public`** — present and freely renderable/indexable.

The exporter guarantees the *structured graph* carries no private node or edge. It does not police
incidental prose (a public page mentioning a name in plain text) — that is the `publish-check`
skill's job before a page is made public.

---

## Change policy

- Additive, backward-compatible changes (new optional field) → bump minor (`1.0` → `1.1`).
- Breaking changes (rename/remove a field, change an edge representation) → bump major (`1.0` → `2.0`)
  and note the migration here.
- The lens should read `meta.schema_version` and refuse to render on a major mismatch.

### History
- **1.0** (2026-07) — initial contract: nodes with viz-layer fields + resolved link edges; two-file
  full/public split with the private-strip invariant.
