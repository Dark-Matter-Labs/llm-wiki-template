#!/usr/bin/env python3
"""
classify_internal.py — propose which `private` pages could become `internal`.

`internal` = readable by trusted colleagues through the shared mirror, never on the
open web. Most of the corpus (concepts, entities, source summaries of Dm's own papers)
is working knowledge a colleague needs. A minority is genuinely sensitive and must stay
`private` regardless.

This script PROPOSES; it does not rewrite anything unless you pass --apply. The default
is a dry-run report, because changing a page's visibility is a disclosure decision and
belongs to the owner.

The rule is deliberately conservative — **deny wins over allow**. A page stays private if
it matches any sensitivity signal, even if it otherwise looks like ordinary knowledge.

Usage:
  python3 tools/classify_internal.py             # dry-run report
  python3 tools/classify_internal.py --verbose   # list every page and its verdict
  python3 tools/classify_internal.py --apply     # rewrite frontmatter (private -> internal)
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402

# --- Sensitivity signals: ANY match keeps a page private. -------------------- #

# Whole areas that are never colleague-shareable.
DENY_PATH_PREFIXES = ("crm/",)

# Tags that mark sensitive material.
DENY_TAGS = {
    "crm", "contact", "account", "capital", "fundraising", "deal",
    "internal", "term-sheet", "transcript", "meeting", "personal",
}

# Title/description/body signals — money, confidentiality, unpublished positions.
#
# These are the GENERIC signals that travel with the template. They deliberately contain
# no project-specific strategy vocabulary: this file is versioned, and in an open repo a
# deny-list is itself a disclosure — it tells a reader exactly what you consider sensitive.
#
# ADD YOUR OWN below once the wiki has real content, and keep them broad enough to be
# non-revealing (prefer `\bproject atlas\b` over the secret the project is about). If a
# term is so sensitive that naming it here is itself a leak, put it in a PRIVATE wiki page
# and rely on the tier default instead — do not encode it in a versioned file.
DENY_PATTERNS = [
    r"\bterm sheet\b", r"\bnot for publication\b", r"\bconfidential\b",
    r"\bmeeting transcript\b", r"\bworking call\b", r"\bnot an offer\b",
    r"\bunder embargo\b", r"\bdo not circulate\b",
    # Currency figures — usually a deal or budget specific. Widen/narrow as needed.
    r"[£$€]\s?\d",
]

# Page types eligible for `internal` — every one still passes the deny rules above.
# `synthesis` is included deliberately: your own cross-corpus arguments are exactly what a
# colleague needs to follow the reasoning, and the sensitivity screen (money tags, currency
# figures, term sheets) already catches the ones that must stay home.
ALLOW_TYPES = {"concept", "entity", "summary", "comparison", "synthesis", "overview"}


def _blob(fm, body):
    # Strip [[wiki-link]] markup before matching. A page that merely LINKS to a
    # sensitive page (e.g. an ordinary concept page citing a private deal page by
    # title) is not itself sensitive — and the link is redacted at export anyway if
    # the target stays private. Matching link text produced false positives.
    body = re.sub(r"\[\[[^\]]*\]\]", " ", body)
    # Scan the WHOLE body. An earlier version truncated to body[:4000], which let a
    # sensitive term deep in a long page escape the screen entirely — the Axioms
    # Register was promoted despite a restructuring mention at ~char 28,000. Deny
    # rules must see everything they are meant to deny.
    return " ".join([
        str(fm.get("title", "")), str(fm.get("description", "")), body
    ]).lower()


def classify(slug, fm, body):
    """Return (verdict, reason). verdict in {'internal', 'keep-private', 'skip'}."""
    vis = fm.get("visibility")
    if vis != "private":
        return "skip", f"already {vis}"

    if any(slug.startswith(p) for p in DENY_PATH_PREFIXES):
        return "keep-private", "CRM / relationship data"

    tags = {str(t).strip().lower() for t in (fm.get("tags") or [])}
    hit = tags & DENY_TAGS
    if hit:
        return "keep-private", f"sensitive tag: {', '.join(sorted(hit))}"

    text = _blob(fm, body)
    for pat in DENY_PATTERNS:
        if re.search(pat, text):
            return "keep-private", f"sensitive signal: /{pat}/"

    if fm.get("type") not in ALLOW_TYPES:
        return "keep-private", f"type '{fm.get('type')}' — not routine working knowledge"

    return "internal", f"routine {fm.get('type')} — working knowledge"


def set_visibility_internal(path):
    """Rewrite the page's visibility line private -> internal, preserving any comment."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    new, n = re.subn(r"(?m)^visibility:\s*private\b", "visibility: internal", text, count=1)
    if n:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new)
    return bool(n)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Propose private -> internal reclassification.")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--apply", action="store_true", help="actually rewrite frontmatter")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    # Fail loudly rather than reporting a misleading "0 / 0 / 0": if the wiki dir is
    # missing or empty, the usual cause is running from tools/ instead of the repo root.
    if not os.path.isdir(args.wiki):
        print(f"error: wiki directory not found: {args.wiki!r}\n"
              f"       (cwd is {os.getcwd()})\n"
              f"       Run this from the repo root:  python3 tools/classify_internal.py\n"
              f"       or point at the wiki:         --wiki /path/to/wiki",
              file=sys.stderr)
        return 2

    pages = list(export.discover(args.wiki))
    if not pages:
        print(f"error: no pages with frontmatter found under {args.wiki!r} — nothing to classify.",
              file=sys.stderr)
        return 2

    promote, keep, skip = [], [], 0
    for slug, path, fm, body in pages:
        verdict, reason = classify(slug, fm, body)
        if verdict == "skip":
            skip += 1
        elif verdict == "internal":
            promote.append((slug, path, reason))
        else:
            keep.append((slug, reason))

    print(f"already public/unlisted/internal : {skip}")
    print(f"private -> INTERNAL (proposed)   : {len(promote)}")
    print(f"private -> stays PRIVATE         : {len(keep)}")

    if args.verbose:
        print("\n-- would become internal --")
        for s, _p, r in promote:
            print(f"  {s}  ({r})")
        print("\n-- stays private --")
        for s, r in keep:
            print(f"  {s}  ({r})")
    else:
        from collections import Counter
        print("\nreasons pages stay private:")
        for r, c in Counter(r for _s, r in keep).most_common(12):
            print(f"  {c:>4}  {r}")

    if args.apply:
        n = sum(1 for _s, p, _r in promote if set_visibility_internal(p))
        print(f"\nAPPLIED: {n} pages rewritten private -> internal.")
        print("Re-run tools/export.py --check and the leak tests before committing.")
    else:
        print("\n(dry run — nothing changed. Pass --apply to rewrite.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
