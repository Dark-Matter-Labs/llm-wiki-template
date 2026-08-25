---
name: query
description: Answer a question against the wiki. Use when the owner asks "what does the wiki say about…", "find…", "compare…", "summarise what we know about…", or any question they expect the accumulated knowledge to answer. Reads the index first, drills into relevant pages, synthesises a cited answer, and files good answers back into the wiki.
---

# Query the wiki

## Steps

1. **Search first — do not scan.** Run `python3 tools/search.py "<the question>" --top 12`.
   It ranks title, tags and description above body text, so the top hits are the pages the
   question is *about*. ~1k tokens. **Never load pages in order to decide which pages to load** —
   context is for reasoning over candidates, traversal is for finding them.

   Second hop by graph, not by catalogue: `export/wiki.json` carries `inbound_links` and
   `outbound_links`, so a page's neighbourhood is a lookup.

   `wiki/index.md` is the router — read it for the *shape* of the corpus, not to find a page.

1. **Read `wiki/index.md` first.** It's the routing file. Find the pages relevant to
   the question from their one-line summaries. Do not scan the whole wiki.

2. **Drill into the relevant pages.** Read them in full. Follow `[[links]]` to
   connected pages where they matter to the answer.

3. **If the wiki can't answer it,** say so plainly. Offer to (a) ingest a source that
   would fill the gap, or (b) do a web search if the owner wants outside information — but
   keep web-sourced material clearly separated from what the wiki actually holds.

4. **Synthesise the answer** in plain language. Cite the wiki pages and, through them,
   the raw sources. Separate what the sources say from what you infer. Flag any
   contradictions between pages rather than papering over them.

5. **Choose the right output form** for the question: prose, a comparison table, a
   short brief, a list. Match the question.

6. **File good answers back.** This is the compounding move. If the answer is a genuine
   piece of synthesis — a comparison, an analysis, a connection the owner will want again —
   write it into `wiki/` as a new `comparison` or `synthesis` page and add it to the
   index. Don't let valuable synthesis vanish into chat. Ask the owner if unsure whether to file.

7. **Log it:** append `## [YYYY-MM-DD] query | <the question>` to the current month's log file (`wiki/log/YYYY-MM.md`; see `wiki/log.md`).

## Rules
- Index first, then drill. Don't brute-force read everything.
- Never invent a citation. If it's your inference, label it.
- A filed answer must carry frontmatter and a `confidence` like any other page.
