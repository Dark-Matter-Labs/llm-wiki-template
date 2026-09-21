#!/usr/bin/env python3
"""
test_check_noindex.py — the promise, and the three false-positive classes.

Most of this file is about what the gate must NOT flag, because the first design of it
flagged 42 pages and about 39 were noise. That version inferred the answer from the
record page's `visibility:` field, which is wrong: a wiki page and the page published
from it are different objects and their tiers legitimately differ. A `private` working
page can produce a public paper, and several here do.

So the gate checks a written claim instead, and these cases pin the boundary of what
counts as one.

  python3 tools/test_check_noindex.py
"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_noindex as cn   # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


HEAD = '<!doctype html><html><head><meta charset="utf-8">{extra}</head><body>x</body></html>'
NOINDEX = '<meta name="robots" content="noindex, nofollow">'


def world(tmp, pages, docs):
    """pages: {relpath under wiki/: text}   docs: {name.html: extra head markup}"""
    root = pathlib.Path(tmp)
    for rel, text in pages.items():
        p = root / "wiki" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    for name, extra in docs.items():
        (root / "docs" / name).write_text(HEAD.format(extra=extra), encoding="utf-8")
    return root


def main():
    print("check_noindex — a written promise, checked against the artefact\n")

    # THE ONE IT EXISTS FOR.
    root = None
    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"a.md": "Published **unlisted** at `docs/a.html` (2026-07-17).\n"},
                     {"a.html": ""})
        bad = cn.broken(root)
        check("a page claimed unlisted with no robots meta is caught",
              [b[0] for b in bad] == ["a.html"], str(bad))

    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"a.md": "Published **unlisted** at `docs/a.html`.\n"},
                     {"a.html": NOINDEX})
        check("...and the same page carrying one is clean", cn.broken(root) == [], str(cn.broken(root)))

    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"a.md": "reachable by direct link, not indexed: `docs/a.html`\n"},
                     {"a.html": ""})
        check("'not indexed' counts as the claim too", len(cn.broken(root)) == 1)

    # ── the false-positive classes ────────────────────────────────────────────────────
    # 1. THE ONE THAT MATTERS. A bare `visibility: unlisted` is a fact about the WIKI page.
    #    Three real pages carry exactly this shape and say "published PUBLICLY" beside it,
    #    and a broader claim pattern flagged all three. What keeps them out is that the
    #    claim must be about the published page, not the presence of the word "unlisted".
    #    An explicit guard for the phrase "published PUBLICLY" was written first and then
    #    deleted: no mutation could kill it, and removing it changed no answer in the
    #    corpus. Dead defensive code that a mutation cannot reach is not protection.
    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"a.md": "visibility: unlisted   # source page unlisted; published "
                                 "PUBLICLY at docs/a.html\n"},
                     {"a.html": ""})
        check("a frontmatter 'visibility: unlisted' is not a claim about the published page",
              cn.broken(root) == [], str(cn.broken(root)))

    # 2. A catalogue row's _(unlisted)_ describes the WIKI page, not the artefact.
    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"index/concepts.md": "- [[A]] — a thing, see docs/a.html _(unlisted)_\n"},
                     {"a.html": ""})
        check("a catalogue row saying unlisted is not a claim about the artefact",
              cn.broken(root) == [], str(cn.broken(root)))

    # 3. The log records what was true then, not what must be true now.
    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"log/2026-07-17.md": "published unlisted at docs/a.html\n"},
                     {"a.html": ""})
        check("a log entry is not a live claim", cn.broken(root) == [], str(cn.broken(root)))

    # ── two boundaries ────────────────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"a.md": "Just a page about docs/a.html with no claim either way.\n"},
                     {"a.html": ""})
        check("a page nobody called unlisted is not this gate's business",
              cn.broken(root) == [], str(cn.broken(root)))

    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"a.md": "Published **unlisted** at `docs/gone.html`.\n"}, {})
        check("a claim about a file that was never published is not a finding",
              cn.broken(root) == [], str(cn.broken(root)))

    # index, nofollow — present but the wrong directive — must still be caught.
    with tempfile.TemporaryDirectory() as t:
        root = world(t, {"a.md": "Published **unlisted** at `docs/a.html`.\n"},
                     {"a.html": '<meta name="robots" content="index, nofollow">'})
        check("a robots meta that does not say noindex is still a finding",
              len(cn.broken(root)) == 1, str(cn.broken(root)))

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
