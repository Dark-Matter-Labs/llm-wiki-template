#!/usr/bin/env python3
"""
contradictions.py — keep contradictions from sitting silent.

`lint` already *finds* contradictions between pages. Until now nothing made them
resolve, so a corpus could hold two incompatible positions indefinitely and still look
healthy. the owner's requirement (7 Aug 2026):

    "When we see contradictions in the database, that tells me you said something which
     is contradictory. But what it doesn't tell me is — are you superseding that
     contradiction? Are you devaluing it?"

So a contradiction is **declared** on a page and must **close** one of two ways:

    superseded  — the new position wins; the old page carries `superseded_by: <title>`
    devalued    — the new input loses; it carries `devalued_by: <title>`

Both write frontmatter, so a resolution is versioned, diffable and reviewable like
everything else. Neither deletes anything: the losing side stays readable, with a
pointer. Plurality is preserved; silence is not.

Frontmatter grammar
-------------------
    contradicts: "Title of the page this disagrees with"     # declares it
    superseded_by: "Title"    # this page lost; that one replaced it
    devalued_by:   "Title"    # this page lost; that one outranks it

Usage:
  python3 tools/contradictions.py            # report open + closed
  python3 tools/contradictions.py --check    # exit 1 if any is incoherent
  python3 tools/contradictions.py --open     # only the ones still needing a decision
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402


def load(wiki_dir):
    """title -> {slug, contradicts, superseded_by, devalued_by}"""
    by_title = {}
    for slug, _path, fm, _body in export.discover(wiki_dir):
        t = fm.get("title")
        if not isinstance(t, str) or not t:
            continue
        by_title[t] = {
            "slug": slug,
            "contradicts": fm.get("contradicts"),
            "superseded_by": fm.get("superseded_by"),
            "devalued_by": fm.get("devalued_by"),
        }
    return by_title


def analyse(by_title):
    """Return (open_list, closed_list, problem_list)."""
    open_, closed, problems = [], [], []

    for title, p in sorted(by_title.items()):
        other = p["contradicts"]
        if not other:
            continue

        if other not in by_title:
            problems.append((title, f"contradicts a page that does not exist: {other!r}"))
            continue
        if other == title:
            problems.append((title, "contradicts itself"))
            continue

        o = by_title[other]
        # Closed if EITHER side has recorded a loss against the other.
        this_lost = p["superseded_by"] == other or p["devalued_by"] == other
        that_lost = o["superseded_by"] == title or o["devalued_by"] == title

        if this_lost and that_lost:
            problems.append((title, f"both sides record a loss against the other ({other!r}) "
                                    "— a contradiction cannot be closed twice"))
        elif this_lost:
            how = "superseded" if p["superseded_by"] == other else "devalued"
            closed.append((title, f"{how} by {other!r}"))
        elif that_lost:
            how = "superseded" if o["superseded_by"] == title else "devalued"
            closed.append((other, f"{how} by {title!r}"))
        else:
            open_.append((title, other))

    # A resolution pointing nowhere is worse than none: it looks settled and isn't.
    for title, p in sorted(by_title.items()):
        for field in ("superseded_by", "devalued_by"):
            target = p[field]
            if target and target not in by_title:
                problems.append((title, f"{field} points at a page that does not exist: {target!r}"))
            elif target == title:
                problems.append((title, f"{field} points at itself"))

    return open_, closed, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description="Report and check contradiction closure.")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--check", action="store_true", help="exit 1 on incoherent state")
    ap.add_argument("--open", dest="only_open", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.wiki):
        print(f"error: no {args.wiki!r} directory (cwd is {os.getcwd()}).\n"
              f"       Run from the repo root.", file=sys.stderr)
        return 2

    by_title = load(args.wiki)
    open_, closed, problems = analyse(by_title)

    print(f"contradictions — {len(by_title)} pages scanned\n")

    if open_:
        print(f"OPEN — needs a decision ({len(open_)})")
        for title, other in open_:
            print(f"  {title}")
            print(f"    contradicts: {other}")
            print(f"    close it by adding, to whichever page loses:")
            print(f"      superseded_by: \"<the winning title>\"   (the new position replaces it)")
            print(f"      devalued_by:   \"<the winning title>\"   (the input is downgraded)")
        print()
    elif not args.only_open:
        print("OPEN — none. Every declared contradiction has been resolved.\n")

    if not args.only_open and closed:
        print(f"CLOSED ({len(closed)})")
        for title, how in closed:
            print(f"  {title} — {how}")
        print()

    if problems:
        print(f"INCOHERENT ({len(problems)})")
        for title, msg in problems:
            print(f"  {title}: {msg}")
        print()

    if args.check and problems:
        print("FAILED: contradiction state is incoherent.")
        return 1
    if not problems:
        print("Contradiction state is coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
