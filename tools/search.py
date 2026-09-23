#!/usr/bin/env python3
"""
search.py — a tiny, dependency-free keyword search over the wiki.

At small scale (a few hundred pages), wiki/index.md is enough and you rarely need this.
As the wiki grows, this gives Claude a fast way to find candidate pages without reading
everything. It uses a simple TF-IDF ranking over the markdown files in wiki/.

Usage (Claude shells out to this; Indy never runs it directly):
    python tools/search.py "climate finance outcomes"
    python tools/search.py "permissioning" --top 5

Ask it questions, not keywords. "what does Dm think about property" and "property" route
to the same page, because the interrogatives and filler are stopped before ranking and a
term that sits on nearly every page in this particular wiki is weighted down rather than
counted as content. See the note above STOP for the measurement that forced both.

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

# Two different problems, kept apart on purpose.
#
# STOP is about LANGUAGE: words that carry no topic in any corpus. The damping below is
# about THIS corpus: words that are perfectly good topics but happen to sit on nearly
# every page here. Conflating them is how a search stops working when it is copied to
# another wiki — "dm" is background noise in dm-llm-wiki and a real query term everywhere
# else, so it must never be stopped, only weighted down where it is in fact ubiquitous.
#
# Measured in dm-llm-wiki on 2026-09-22: of six conversationally-phrased questions, three
# returned the wrong page. "what does Dm think about property" ranked
# wiki/what-this-wiki-holds.md above the philosophies page, because "what", "does",
# "think" and "about" were scored as content and outvoted the single term ("property")
# that carried the question. The whole system is built for people who type plain English,
# and CLAUDE.md puts this tool first in the retrieval order, so a diluted first hop costs
# the entire query.
#
# The list below is deliberately in two tiers. Closed-class function words are safe
# anywhere. Open-class filler is not, so each one is here because it appeared in a
# measured failure, and words that look like filler but are load-bearing in this
# federation are excluded by name: care, value, values, beyond, option, options,
# optionality, work, state, power, right, rights, need, needs, want, wants, thinking,
# thought, making, means, meaning.
STOP = set("""
    a an the this that these those it its
    and or but nor if then than because while though although
    of to in for on at by with as into onto upon over under between through
    about across after before during against within without
    is are was were be been being am
    do does did doing done
    has have had having
    can could will would shall should may might must
    i me my mine we us our ours you your yours
    he him his she hers they them their theirs
    what when where which who whom whose why how
    no not all any some each every both other another same
    more most less least few many much several
    there here now so such very just also really actually quite simply

    think thinks say says said tell tells told
    make makes made get gets got know knows
""".split())


def tokenize(text, stop=None):
    # `stop=None` rather than `stop=STOP`: a default argument binds once, at definition
    # time, so the latter would quietly ignore any later reassignment of STOP — including
    # the one test_search.py makes to prove the old stop list reproduces the old bug. A
    # mutation test that cannot mutate is a test that always passes.
    stop = STOP if stop is None else stop
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in stop and len(t) > 1]


# A term on more than half the pages is describing the corpus, not the question. Rather
# than stopping it — which would break the same query in a wiki where the term is rare —
# taper its weight from full at the threshold down to UBIQUITY_MIN when it is on every
# page. The floor is not zero: a one-word query for a ubiquitous term must still rank
# something, and since every page is damped identically it ranks them in the same order.
UBIQUITY_THRESHOLD = 0.5
UBIQUITY_MIN = 0.15


def ubiquity_damp(df, n):
    """Weight multiplier for a term appearing in `df` of `n` pages."""
    if n <= 0:
        return 1.0
    frac = df / n
    if frac <= UBIQUITY_THRESHOLD:
        return 1.0
    return max(UBIQUITY_MIN, (1.0 - frac) / (1.0 - UBIQUITY_THRESHOLD))


def read_pages():
    pages = []
    for p in sorted(WIKI_DIR.rglob("*.md")):
        # Catalogues are navigation, not content. wiki/index/ joined this list on
        # 2026-08-23 when the index was tiered: those files list every description in
        # the corpus, so without this they outrank every real page on every query.
        if p.name in ("index.md", "log.md") or p.parent.name in ("log", "index"):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        def field(name):
            m = re.search(rf"^{name}:\s*(.+)$", text, re.MULTILINE)
            return m.group(1).strip().strip('"') if m else ""
        pages.append({
            "path": p, "text": text,
            "desc": field("description"),
            "title": field("title"),
            "tags": field("tags"),
            "tokens": tokenize(text),
        })
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
    idf = {t: (math.log((N + 1) / (df.get(t, 0) + 1)) + 1)
              * ubiquity_damp(df.get(t, 0), N)
           for t in q_tokens}

    # Field weights. Body TF-IDF alone ranked long essays above the concept page a
    # question was actually about — which is why nothing used this tool and every
    # query went through the 55k-token index instead. What a page IS lives in its
    # title, tags and description; the body is for recall, not for precision.
    W_TITLE, W_TAGS, W_DESC, W_BODY = 6.0, 3.0, 2.0, 1.0

    results = []
    for pg in pages:
        tf = Counter(pg["tokens"])
        length = len(pg["tokens"]) or 1
        body = sum((tf.get(t, 0) / length) * idf[t] for t in q_tokens)

        title_t = set(tokenize(pg["title"]))
        tags_t = set(tokenize(pg["tags"]))
        desc_t = set(tokenize(pg["desc"]))
        hits = lambda field: sum(idf[t] for t in q_tokens if t in field) / len(q_tokens)

        s = (W_TITLE * hits(title_t) + W_TAGS * hits(tags_t)
             + W_DESC * hits(desc_t) + W_BODY * body)

        # All query terms in the title is almost always the page being asked for.
        if title_t and all(t in title_t for t in q_tokens):
            s *= 2.0
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

    # A question made entirely of function words ("what is this about?") has nothing to
    # rank on. Say that, rather than "no matches", which reads as a claim about the wiki
    # instead of a claim about the question.
    if not tokenize(args.query) and tokenize(args.query, stop=frozenset()):
        print(f"Every term in {args.query!r} is a stop word — there is nothing to search "
              f"for. Add the subject of the question.")
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
