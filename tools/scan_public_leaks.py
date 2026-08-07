#!/usr/bin/env python3
"""
scan_public_leaks.py — tripwire against sensitive material on any PUBLIC surface.

Public surface =
  * every text file under docs/  (the published GitHub Pages site — open internet), and
  * every wiki page whose `visibility` is `public` or `unlisted` (shareable tiers).

It matches each never-public term from tools/sensitive_terms.txt (case-insensitive)
against those surfaces and reports every hit with file:line. Exit code:
  0 = clean, 1 = at least one sensitive term found, 2 = usage/config error.

This is a backstop for the PUBLICATION boundary. The real "only the owner can read it"
guarantee is the ACCESS boundary (repo lock-down) — see SHARING-AND-ACCESS.md.

Usage:
  python3 tools/scan_public_leaks.py                 # scan; nonzero exit on any hit
  python3 tools/scan_public_leaks.py --list          # show what would be scanned
  python3 tools/scan_public_leaks.py --terms FILE    # custom term list
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402  (split_frontmatter)

TEXT_EXT = {".html", ".md", ".markdown", ".css", ".js", ".json", ".svg", ".txt", ".xml"}
DEFAULT_TERMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sensitive_terms.txt")


def load_terms(path):
    terms = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            terms.append(s)
    return terms


def public_wiki_pages(wiki_dir):
    """Yield paths of wiki pages whose visibility is public or unlisted."""
    for root, _dirs, files in os.walk(wiki_dir):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                fm, _body = export.split_frontmatter(fh.read())
            if fm and fm.get("visibility") in ("public", "unlisted"):
                yield path


def docs_files(docs_dir):
    for root, _dirs, files in os.walk(docs_dir):
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() in TEXT_EXT:
                yield os.path.join(root, fn)


def surfaces(docs_dir, wiki_dir):
    paths = []
    if os.path.isdir(docs_dir):
        paths.extend(docs_files(docs_dir))
    if os.path.isdir(wiki_dir):
        paths.extend(public_wiki_pages(wiki_dir))
    return sorted(set(paths))


def scan(paths, terms):
    patterns = [(t, re.compile(re.escape(t), re.IGNORECASE)) for t in terms]
    hits = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    for term, pat in patterns:
                        if pat.search(line):
                            hits.append((p, i, term, line.strip()[:160]))
        except (UnicodeDecodeError, OSError):
            continue
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan public surfaces for never-public terms.")
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--terms", default=DEFAULT_TERMS)
    ap.add_argument("--list", action="store_true", help="list scanned surfaces and exit")
    args = ap.parse_args(argv)

    paths = surfaces(args.docs, args.wiki)
    if args.list:
        for p in paths:
            print(p)
        print(f"\n{len(paths)} public surfaces would be scanned.")
        return 0

    if not os.path.exists(args.terms):
        print(f"error: terms file not found: {args.terms}", file=sys.stderr)
        return 2
    terms = load_terms(args.terms)
    if not terms:
        print("warning: no terms configured; nothing to scan for.", file=sys.stderr)
        return 0

    hits = scan(paths, terms)
    if hits:
        print(f"LEAK CHECK FAILED — {len(hits)} sensitive-term hit(s) on public surfaces:\n",
              file=sys.stderr)
        for p, line, term, excerpt in hits:
            print(f"  {p}:{line}  «{term}»", file=sys.stderr)
            print(f"      {excerpt}", file=sys.stderr)
        print("\nRemove the sensitive content from these PUBLIC surfaces, or if a match is a "
              "false positive, refine the term in tools/sensitive_terms.txt.", file=sys.stderr)
        return 1

    print(f"public leak check OK — {len(paths)} public surfaces clean "
          f"of {len(terms)} sensitive term(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
