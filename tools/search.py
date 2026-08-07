#!/usr/bin/env python3
"""
search.py — a tiny, dependency-free keyword search over the wiki.

At small scale (a few hundred pages), wiki/index.md is enough and you rarely need this.
As the wiki grows, this gives Claude a fast way to find candidate pages without reading
everything. It uses a simple TF-IDF ranking over the markdown files in wiki/.

Usage (Claude shells out to this; the owner never runs it directly):
    python tools/search.py "climate finance outcomes"
    python tools/search.py "permissioning" --top 5

Output: ranked list of matching pages with their one-line description and score.
No external packages required — runs in a fresh cloud environment as-is.
"""

import argparse
import math
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

WIKI_DIR = Path(__file__).resolve().parent.parent / "wiki"
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP = set("the a an and or of to in for on is are was were be with as at by from this that it its".split())


def tokenize(text):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP and len(t) > 1]


def read_pages():
    pages = []
    for p in sorted(WIKI_DIR.rglob("*.md")):
        # index.md and the log (log.md + the wiki/log/ monthly files) are catalogues,
        # not content pages.
        if p.name in ("index.md", "log.md") or p.parent.name == "log":
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        desc = ""
        m = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        if m:
            desc = m.group(1).strip()
        pages.append({"path": p, "text": text, "desc": desc, "tokens": tokenize(text)})
    return pages


def score(pages, query):
    q_tokens = tokenize(query)
    if not q_tokens:
        return []
    N = len(pages) or 1
    df = defaultdict(int)
    for pg in pages:
        for t in set(pg["tokens"]):
            df[t] += 1
    idf = {t: math.log((N + 1) / (df.get(t, 0) + 1)) + 1 for t in q_tokens}

    results = []
    for pg in pages:
        tf = Counter(pg["tokens"])
        length = len(pg["tokens"]) or 1
        s = sum((tf.get(t, 0) / length) * idf[t] for t in q_tokens)
        # small boost if query terms appear in the description/title
        if any(t in tokenize(pg["desc"]) for t in q_tokens):
            s *= 1.5
        if s > 0:
            results.append((s, pg))
    results.sort(key=lambda x: x[0], reverse=True)
    return results


def main():
    ap = argparse.ArgumentParser(description="Keyword search over the wiki.")
    ap.add_argument("query", help="search query")
    ap.add_argument("--top", type=int, default=8, help="number of results")
    args = ap.parse_args()

    if not WIKI_DIR.exists():
        print(f"No wiki/ directory found at {WIKI_DIR}", file=sys.stderr)
        sys.exit(1)

    pages = read_pages()
    if not pages:
        print("Wiki is empty — nothing to search. Ingest a source first.")
        return

    ranked = score(pages, args.query)
    if not ranked:
        print(f"No matches for: {args.query!r}")
        return

    rel = WIKI_DIR.parent
    for s, pg in ranked[: args.top]:
        path = pg["path"].relative_to(rel)
        line = f"{s:6.3f}  {path}"
        if pg["desc"]:
            line += f"  —  {pg['desc']}"
        print(line)


if __name__ == "__main__":
    main()
