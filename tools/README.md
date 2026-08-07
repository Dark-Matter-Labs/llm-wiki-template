# Tools

Small helper scripts Claude can shell out to. **The owner never runs these directly** —
they exist so Claude can operate on the wiki efficiently. They have no required
dependencies for the base case and run in a fresh Claude Code cloud environment.

## search.py
Dependency-free keyword search over `wiki/`. Useful once the wiki outgrows the point
where reading `index.md` is enough. Claude runs it to find candidate pages.

```
python tools/search.py "your query"
python tools/search.py "your query" --top 5
```

## pdf_to_md.py
Converts a PDF in `raw/` into a companion markdown file so Claude can read and
summarise it during ingest. The original PDF is never modified. Uses `pymupdf4llm`
if available (best quality), falls back to `pypdf`.

```
python tools/pdf_to_md.py raw/some-report.pdf
```

If a converter isn't installed, the script prints the one-line pip command. In Claude
Code on the web, Claude can install it into the session with:
```
pip install pymupdf4llm --break-system-packages
```

---

## The boundary tooling

These enforce the `visibility` tiers. They are stdlib-only so they run in CI with no
install step, and they are the reason publishing is safe to automate.

### export.py
Validates frontmatter and builds the JSON graph a frontend reads.

```
python3 tools/export.py --check   # schema gate: every page valid, every [[link]] resolves
python3 tools/export.py           # writes export/wiki.json + export/wiki.public.json
```

`wiki.public.json` has private **and** internal pages fully stripped — bodies, titles, and
links pointing to them. `wiki.json` contains everything and is for local use only; CI never
pushes it.

It also carries a **split-link tripwire**: a `[[wiki link]]` broken across a newline won't
resolve, and silently produces a dead link. `--check` fails on these.

### export_shared.py
Builds the colleague-readable markdown cut (public + unlisted + internal). Rebuilds
frontmatter from a field whitelist, redacts links to private pages, drops a private
`parent:`, and generates a fresh index — so a private page leaks nothing, not even its title.

### classify_internal.py
Proposes which `private` pages are ordinary working knowledge that could become `internal`.
**Dry run by default**; deny-wins (any sensitivity signal keeps a page private).

```
python3 tools/classify_internal.py --verbose   # read every line of this
python3 tools/classify_internal.py --apply     # only after the owner approves
```

Run it from the repo root, not from `tools/` — it exits with an error rather than reporting
a misleading "0 pages found".

### scan_public_leaks.py
Matches `tools/sensitive_terms.txt` against every public surface — all of `docs/` plus every
`public`/`unlisted` page. Runs in CI as a hard gate on the Pages deploy and the mirror publish.

```
python3 tools/scan_public_leaks.py
```

⚠ Read the warning at the top of `sensitive_terms.txt` before adding terms: the file is
versioned, so writing a secret into it to block the secret also publishes the secret.

### The tests
Prove the invariants hold. Run all three before trusting a boundary change:

```
python3 tools/test_export.py          # private never reaches the public graph
python3 tools/test_export_shared.py   # private never reaches the colleague mirror
python3 tools/test_internal_tier.py   # internal reaches the mirror, never the web
```

### make_social_card.py
Generates `docs/assets/social-card.png` — the Open Graph link-preview image every published
page points at. Published pages are shared as URLs, so this card is the first thing most
people see; without it a shared link renders as a bare text row.

```
python3 tools/make_social_card.py --eyebrow "ACME · RESEARCH" \
  --line1 "Your one-line" --line2 "statement here." --url "acme.github.io/wiki"
```

It ships one shared, generic card rather than per-page images — deliberately, so that an
`unlisted` page's title never leaks into a chat preview. Requires Pillow.
