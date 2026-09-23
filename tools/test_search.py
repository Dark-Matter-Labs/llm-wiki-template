#!/usr/bin/env python3
"""
test_search.py — prove the ranker routes a plain-English question to the same page as the
keyword it is really asking about, and prove it has not been taught to ignore real words.

The bug this was written against, measured in dm-llm-wiki on 2026-09-22: of six questions
asked both conversationally and as keywords, three conversational forms returned a
different page, and the difference was always filler. "what does Dm think about property"
ranked a page titled "What this wiki holds" first, because "what" was scored as a content
term and there were five other filler terms diluting the one word — "property" — that
carried the question. CLAUDE.md puts search.py first in the retrieval order, so a wrong
first hop costs the whole query.

The second half of this file matters more than the first. A stop list is a blunt
instrument, and the cheap way to make questions route well is to stop so many words that
the corpus's own vocabulary disappears with them. Most of the checks below are therefore
guards: words that LOOK like filler and are load-bearing here (care, value, beyond,
options, work, state, power, rights), and the proof that a term ubiquitous in one wiki is
still full-weight in a wiki where it is rare.

Usage:  python3 tools/test_search.py
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import search as S  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

#: The stop list as it stood before 2026-09-22, for the mutation checks. Putting this back
#: must make the routing checks fail; if it does not, they are not testing the fix.
OLD_STOP = set("the a an and or of to in for on is are was were be with as at by from "
               "this that it its".split())

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
    if not ok:
        FAILED.append(name)


# --------------------------------------------------------------------------------------
# A fixture in the shape of the corpus that produced the bug: a small wiki where one term
# ("dm") is on every page, one page is titled as a question, and the page the question is
# actually about names its subject only in its tags and body.
# --------------------------------------------------------------------------------------
PAGES = {
    "what-this-wiki-holds.md": dict(
        title="What does this wiki hold, and how does it decide",
        description="The boundary decided at the first ingest: what Dm holds here and "
                    "what it does not, and who gets to say so.",
        tags="[boundary, scope, governance]",
        body="Dm decided this at the first ingest. Dm holds the organisational layer and "
             "Dm does not hold the people material. What Dm thinks about anything else "
             "is recorded elsewhere, and Dm says so plainly.",
    ),
    "eight-philosophies.md": dict(
        title="The eight philosophies of Lee",
        description="Six things Dm wants to go beyond and two that replace them, each "
                    "stated as a question rather than a programme.",
        tags="[property, labour, value, beyond]",
        body="Dm says the economy must go beyond property. Property is the first "
             "philosophy and the private contract is the third. Dm treats property as "
             "the deep code beneath the rest.",
    ),
    "circulation-tiers.md": dict(
        title="Circulation tiers",
        description="Dm already has a five-step publication ladder for its documents.",
        tags="[circulation, visibility, publication]",
        body="Dm carries a field called Circulation with five values. Dm maps them onto "
             "the wiki's four tiers.",
    ),
    "care-and-value.md": dict(
        title="Care, value and the work of the state",
        description="What Dm means by the care economy, and why value is not price.",
        tags="[care, value, work, state, power, rights, options]",
        body="Dm holds that care is work. Dm argues value beyond price, and that the "
             "state has options here. Power and rights follow from that.",
    ),
}
# Padding, so "dm" really is on every page and the interrogatives really are common.
for i in range(6):
    PAGES[f"filler-{i}.md"] = dict(
        title=f"A note on what Dm does, number {i}",
        description=f"What Dm did in week {i}, and how it was decided.",
        tags="[notes]",
        body="Dm did some work. What Dm does next is not decided. How Dm decides is "
             "written down elsewhere, and who decides is too.",
    )


def build_fixture(root):
    wiki = pathlib.Path(root) / "wiki"
    wiki.mkdir(parents=True)
    for name, p in PAGES.items():
        (wiki / name).write_text(
            "---\n"
            f"type: concept\ntitle: {p['title']}\n"
            f'description: "{p["description"]}"\n'
            f"tags: {p['tags']}\n"
            "visibility: internal\n---\n\n"
            f"# {p['title']}\n\n{p['body']}\n",
            encoding="utf-8")
    return wiki


def top_page(wiki, query, n=1):
    saved = S.WIKI_DIR
    try:
        S.WIKI_DIR = wiki
        ranked = S.score(S.read_pages(), query)
    finally:
        S.WIKI_DIR = saved
    return [pg["path"].name for _, pg in ranked[:n]]


def main():
    # ---- the stop list is language, and only language -------------------------------
    for w in ("what", "when", "where", "which", "who", "whom", "whose", "why", "how",
              "does", "did", "do", "about", "think", "thinks", "make", "makes", "made",
              "gets", "got", "know", "says", "just", "also", "very", "really"):
        check(f"filler is stopped: {w}", w in S.STOP)

    # The guard, and the half of this file that decides whether the fix was worth making.
    # Each of these is a real query term in this federation.
    for w in ("care", "value", "values", "beyond", "option", "options", "optionality",
              "work", "state", "power", "right", "rights", "need", "needs", "want",
              "wants", "thinking", "thought", "making", "means", "meaning", "decision",
              "decides", "published", "publication", "property", "commons", "gravity"):
        check(f"a real term is NOT stopped: {w}", w not in S.STOP)

    check("a question tokenizes down to the terms that carry it",
          S.tokenize("what does Dm think about property") == ["dm", "property"],
          str(S.tokenize("what does Dm think about property")))
    check("...and the keyword form of the same question is a subset",
          set(S.tokenize("property")) <= set(S.tokenize("what does Dm think about property")))
    check("an explicit stop set can be passed in",
          S.tokenize("what is this", stop=frozenset()) == ["what", "is", "this"])

    # ---- ubiquity damping is corpus-relative, not a second stop list ------------------
    check("a rare term is untouched", S.ubiquity_damp(5, 100) == 1.0)
    check("a term on exactly half the pages is untouched", S.ubiquity_damp(50, 100) == 1.0)
    check("a term on three quarters is halved", abs(S.ubiquity_damp(75, 100) - 0.5) < 1e-9)
    check("a term on every page floors, and never reaches zero",
          S.ubiquity_damp(100, 100) == S.UBIQUITY_MIN > 0)
    check("damping is monotone in document frequency",
          all(S.ubiquity_damp(d, 100) >= S.ubiquity_damp(d + 1, 100) for d in range(100)))
    check("an empty corpus does not divide by zero", S.ubiquity_damp(0, 0) == 1.0)
    # This is why the ubiquitous term is damped rather than stopped: in a wiki where it is
    # rare it must still carry full weight, and a stop list cannot know which wiki it is in.
    check("the SAME term is full-weight where it is rare",
          S.ubiquity_damp(300, 840) == 1.0 and S.ubiquity_damp(37, 37) == S.UBIQUITY_MIN,
          "'dm' is background in dm-llm-wiki and a query term everywhere else")

    with tempfile.TemporaryDirectory() as t:
        wiki = build_fixture(t)

        # ---- the measured failure, and its keyword control --------------------------
        conv = "what does Dm think about property"
        check("a question routes to the page it is about",
              top_page(wiki, conv) == ["eight-philosophies.md"],
              str(top_page(wiki, conv, 3)))
        check("...to the same page as its keyword form",
              top_page(wiki, conv) == top_page(wiki, "property"))
        check("a question-shaped TITLE does not win on its question words",
              "what-this-wiki-holds.md" not in top_page(wiki, conv, 2))
        check("the keyword control is unmoved",
              top_page(wiki, "circulation visibility tiers") == ["circulation-tiers.md"])
        check("a term stopped as filler cannot be searched for, and that is the trade",
              top_page(wiki, "care work") == ["care-and-value.md"],
              "...but the content words around it must still route")

        # A question made only of function words has nothing to rank on. The CLI must say
        # THAT, rather than "no matches", which reads as a claim about the wiki instead of
        # a claim about the question. Checked at the command below.
        check("an all-filler question ranks nothing",
              top_page(wiki, "what is this about?", 3) == [])

        # ---- MUTATION: put the old stop list back; the routing checks must fail -------
        saved = S.STOP
        try:
            S.STOP = OLD_STOP
            mutant = top_page(wiki, conv, 3)
        finally:
            S.STOP = saved
        check("MUTATION — the old stop list reproduces the measured bug",
              mutant[0] == "what-this-wiki-holds.md",
              f"expected the old wrong answer, got {mutant}")
        check("MUTATION — and the keyword form was never broken, then or now",
              top_page(wiki, "property") == ["eight-philosophies.md"])

        # ---- MUTATION: switch damping off; the ubiquitous term regains its vote ------
        def weight_of(term):
            saved_w = S.WIKI_DIR
            try:
                S.WIKI_DIR = wiki
                pages = S.read_pages()
            finally:
                S.WIKI_DIR = saved_w
            n = len(pages)
            df = sum(1 for p in pages if term in set(p["tokens"]))
            return S.ubiquity_damp(df, n), df, n

        damp, df, n = weight_of("dm")
        check("'dm' is on every fixture page", df == n and n == len(PAGES), f"{df}/{n}")
        check("...so it is damped to the floor", damp == S.UBIQUITY_MIN)

        saved_min, saved_thr = S.UBIQUITY_MIN, S.UBIQUITY_THRESHOLD
        try:
            S.UBIQUITY_MIN, S.UBIQUITY_THRESHOLD = 1.0, 1.0
            check("MUTATION — with damping off, a term on every page votes at full weight",
                  S.ubiquity_damp(n, n) == 1.0)
        finally:
            S.UBIQUITY_MIN, S.UBIQUITY_THRESHOLD = saved_min, saved_thr

    # ---- the command still works on this repo ---------------------------------------
    # The question is built from this repo's own pages, because this file travels to every
    # wiki. It used to ask for "civilization options" and expect three rows, which holds only
    # in the corpora that have those pages: the day it first travelled it failed in 13 of 19.
    title = None
    for p in sorted((HERE.parent / "wiki").rglob("*.md")):
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$",
                      p.read_text(encoding="utf-8", errors="ignore"), re.M)
        if m:
            title = m.group(1)
            break
    if title is None:
        print("  SKIP  the CLI against the real wiki — this wiki has no titled pages yet")
    else:
        r = subprocess.run([sys.executable, str(HERE / "search.py"), title, "--top", "3"],
                           capture_output=True, text=True)
        check("the CLI runs against the real wiki", r.returncode == 0, (r.stderr or "").strip())
        rows = r.stdout.strip().splitlines()
        check("...and prints ranked rows, finding a page by its own title",
              1 <= len(rows) <= 3, f"{title!r} -> {r.stdout.strip()[:200]}")

    r = subprocess.run([sys.executable, str(HERE / "search.py"), "zzqqxvfhk"],
                       capture_output=True, text=True)
    check("a query with no matches is not an error", r.returncode == 0)
    check("...and says so in terms of the query", "No matches" in r.stdout)

    r = subprocess.run([sys.executable, str(HERE / "search.py"), "what is this about?"],
                       capture_output=True, text=True)
    check("an all-filler query is answered about the QUESTION, not about the wiki",
          r.returncode == 0 and "stop word" in r.stdout and "No matches" not in r.stdout,
          r.stdout.strip())

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: {', '.join(FAILED)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
