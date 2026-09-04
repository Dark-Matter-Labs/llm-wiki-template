---
name: query
description: Answer a question against the wiki. Use when the owner asks "what does the wiki say about…", "find…", "compare…", "summarise what we know about…", or any question they expect the accumulated knowledge to answer. Reads the index first, drills into relevant pages, synthesises a cited answer, and files good answers back into the wiki.
---

# Query the wiki

## Hard rule — knowledge, not surveillance

Before anything else: if the question is really about *tracking a person's activity* —
"what has the owner done this week", "who is X talking to", "who touched this page" — pause
and decline, explaining the rule (CLAUDE.md: knowledge yes, tracking people no). A person
querying their **own** activity in their **own** wiki is fine. When in doubt, ask what
knowledge they're actually after and answer that instead.

## Steps

1. **Search first — do not scan.** Run `python3 tools/search.py "<the question>" --top 12`.
   It ranks by title, tags and description before body text, so the top few hits are
   usually the pages the question is about. This costs ~1k tokens and replaces reading a
   catalogue. **Never load pages in order to decide which pages to load.**

   Then, for the second hop, follow the graph rather than the catalogue: `export/wiki.json`
   carries `inbound_links`/`outbound_links` per page, so a page's neighbourhood is a lookup,
   not another search.

   `wiki/index.md` is the router — sections, counts and a pointer per shelf, ~9k tokens. Read
   it when you need to know the *shape* of the corpus. The heavy catalogues under
   `wiki/index/` are shelves: load one only when the question is squarely in that section,
   and never more than one. Reading all of them is the thing this replaced.

2. **Read the shortlist in full.** Follow `[[links]]` to connected pages where they
   matter to the answer — that is the graph hop, and it is cheaper than another search.

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

7. **Log it:** append `## [YYYY-MM-DD] query | <the question>` to the today's log file (`wiki/log/YYYY-MM-DD.md`; see `wiki/log.md`).

## Rules
- Index first, then drill. Don't brute-force read everything.
- Never invent a citation. If it's your inference, label it.
- A filed answer must carry frontmatter and a `confidence` like any other page.
