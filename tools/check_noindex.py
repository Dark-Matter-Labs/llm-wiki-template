#!/usr/bin/env python3
"""
check_noindex.py — a page published `unlisted` must actually carry `noindex`.

## What this checks, and why it is worth a gate

`unlisted` has a definition in CLAUDE.md: rendered on the site, **not indexed**, and not
linked from public navigation. Reachable only by direct link. It is the tier used for
work that is finished enough to send someone and not meant to be found.

Two of those three properties are enforced by not linking the page. The third is a
`<meta name="robots" content="noindex">` in the file, and nothing checked it.

Found 2026-09-21 while renaming two published pages. `wiki/aae-rebuild.md` says, in a
blockquote at the top of the page:

    Published (unlisted). A cleaned public rendering is served by GitHub Pages at
    docs/aae.html ... reachable by direct link, not indexed and not in the site
    navigation.

`docs/aae.html` had no robots meta at all. The corpus made a specific, written promise
about an artefact and the artefact did not keep it. Two more were in the same state.

## What it does NOT do, because the first version did and was wrong

The obvious rule is: find the page's record in `wiki/`, read its `visibility:`, and
require `noindex` wherever that says `internal` or `private`. That rule produced **42
findings, and about 39 of them were noise.** A wiki page and the page published from it
are different objects and their tiers legitimately differ: a `private` working page can
produce a public paper, and several here do. `wiki/camden-nutrition-risk-model.md` says
so in its own frontmatter comment — "source page unlisted; published PUBLICLY".

So this checks a **claim**, not an inference. Somebody wrote down that a particular file
was published unlisted or not indexed; this asks whether that is true. A claim nobody
verifies is the failure this whole corpus keeps finding, and this is one more instance of
it rather than a new kind of rule.

False positives are kept out by two things, and it is worth naming which does the work.

  * **The claim is narrow.** It must say the *published page* is unlisted or unindexed:
    "published unlisted", "not indexed", "noindex", "reachable by direct link". A bare
    `visibility: unlisted` in frontmatter is a fact about the wiki page and is not
    matched, which is what keeps the three "source page unlisted; published PUBLICLY"
    pages out. An explicit guard for that phrase was written first and then removed: it
    was dead code, killing it changed no answer anywhere in the corpus, and no mutation
    could reach it.
  * **Catalogues and the log are skipped.** A shelf row reading `_(unlisted)_` describes
    the wiki page, and a log entry describes what was true on the day.

## Usage

    python3 tools/check_noindex.py            # the reading
    python3 tools/check_noindex.py --check    # exit 1 on a broken promise
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WIKI = ROOT / "wiki"

#: A claim that a named published file is unlisted or unindexed.
CLAIM = re.compile(r"(published\s+\**unlisted|not\s+indexed|noindex|reachable\s+by\s+direct\s+link)",
                   re.I)
#: A reference to a published file.
REF = re.compile(r"docs/([A-Za-z0-9._-]+\.html)")
#: What satisfies the claim.
NOINDEX = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', re.I)


def _pages():
    """Wiki pages whose statements are about artefacts, not about themselves."""
    for p in sorted(WIKI.rglob("*.md")):
        rel = p.relative_to(WIKI).as_posix()
        if rel.startswith("log/") or rel.startswith("index/") or rel == "index.md":
            continue
        yield p


def claims(root: pathlib.Path | None = None) -> dict[str, tuple[str, str]]:
    """{published file: (the page that claims it, the line)} for every unlisted claim."""
    global ROOT, DOCS, WIKI
    if root is not None:
        ROOT = pathlib.Path(root); DOCS = ROOT / "docs"; WIKI = ROOT / "wiki"
    found: dict[str, tuple[str, str]] = {}
    for p in _pages():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            for name in REF.findall(line):
                if CLAIM.search(line):
                    found.setdefault(name, (p.relative_to(ROOT).as_posix(), line.strip()))
    return found


def broken(root: pathlib.Path | None = None) -> list[tuple[str, str, str]]:
    out = []
    for name, (src, line) in sorted(claims(root).items()):
        f = DOCS / name
        if not f.exists():
            continue                            # nothing published; not this gate's business
        if not NOINDEX.search(f.read_text(encoding="utf-8", errors="replace")):
            out.append((name, src, line))
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not DOCS.is_dir():
        print("noindex check — no docs/ in this repo, nothing published to check")
        return 0
    all_claims = claims()
    bad = broken()
    print(f"noindex — {len(all_claims)} page(s) recorded as unlisted, {len(bad)} without a robots meta")
    if not bad:
        print("\n  every page the corpus calls unlisted says so to a crawler too.")
        return 0
    print()
    for name, src, line in bad:
        print(f"  docs/{name}")
        print(f"      {src} says: {line[:112]}")
    print(f"\n  Add to the <head> of each:")
    print(f'      <meta name="robots" content="noindex, nofollow">')
    print(f"  Or, if the page is meant to be found, correct the claim on the page that makes it.")
    return 1 if "--check" in argv else 0


if __name__ == "__main__":
    raise SystemExit(main())
