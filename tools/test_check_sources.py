#!/usr/bin/env python3
"""
test_check_sources.py — a page's declared sources are read the way the page wrote them.

Written 2026-10-12, when check_sources.py went from this wiki to all of them. A first run across
the federation found two ways the reader under-counted: a `sources:` written as a block list was
skipped entirely (four pages), and a quoted filename containing a comma would have been split in
two. Both make the check quieter than the corpus, which is the wrong direction for a check.

  python3 tools/test_check_sources.py
"""

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_sources  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(sources_block, body="Body.\n"):
    return f"---\ntitle: T\n{sources_block}\nvisibility: private\n---\n{body}"


def main():
    print("check_sources — declared sources are read as written\n")
    ds = check_sources.declared_sources

    check("a one-line list is read", ds(page("sources: [raw/a.md, raw/b.pdf]")) == ["raw/a.md", "raw/b.pdf"])
    check("a block list is read", ds(page("sources:\n  - raw/a.md\n  - \"raw/b c.pdf\"")) == ["raw/a.md", "raw/b c.pdf"],
          str(ds(page("sources:\n  - raw/a.md\n  - \"raw/b c.pdf\""))))
    got = ds(page('sources: ["raw/Report, 2025 edition.pdf", raw/x.md]'))
    check("a quoted filename with a comma stays whole", got == ["raw/Report, 2025 edition.pdf", "raw/x.md"], str(got))
    check("only raw/ paths count as sources", ds(page("sources: [raw/a.md, tools/export.py, https://x.org]")) == ["raw/a.md"])
    check("an empty list is no sources", ds(page("sources: []")) == [])
    check("a 'sources:' line in the body is not frontmatter",
          ds(page("sources: [raw/a.md]", "Notes\nsources:\n  - raw/not-this.md\n")) == ["raw/a.md"])

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "wiki").mkdir()
        (root / "raw" / "sub").mkdir(parents=True)
        (root / "tools").mkdir()
        (root / "raw" / "here.md").write_text("x")
        (root / "raw" / "sub" / "moved.md").write_text("x")
        (root / "wiki" / "p.md").write_text(page("sources:\n  - raw/here.md\n  - raw/moved.md\n  - raw/gone.pdf"))
        check_sources.ROOT, check_sources.WIKI, check_sources.RAW = root, root / "wiki", root / "raw"
        check_sources.BASELINE = root / "tools" / "sources-baseline.json"
        r = check_sources.audit()
        check("a file in raw/ resolves", r["ok"] == 1, str(r))
        check("a file that moved is path drift, found by name", [x["found_at"] for x in r["drift"]] == ["raw/sub/moved.md"], str(r["drift"]))
        check("a file nowhere is absent", [x["cited"] for x in r["absent"]] == ["raw/gone.pdf"], str(r["absent"]))
        check("--check fails on an absent file not yet recorded", check_sources.main(["--check"]) == 1)
        check("--update-baseline records it", check_sources.main(["--update-baseline"]) == 0
              and json.loads(check_sources.BASELINE.read_text())["absent"] == ["raw/gone.pdf"])
        check("--check passes once it is recorded", check_sources.main(["--check"]) == 0)

    # Found 2026-10-12 in indy-llm-wiki: a folder in raw/ carries a non-breaking space after a
    # dash, and five pages cite it with an ordinary space. The citation is right; the folder name
    # has an invisible quirk, and raw/ is never renamed. Spaces of either kind, and the two
    # Unicode spellings of one accented letter, are the same path to a reader.
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "wiki").mkdir()
        (root / "raw" / "Proposal – Indy, Kirsten").mkdir(parents=True)
        (root / "raw" / "Proposal – Indy, Kirsten" / "doc.pdf").write_text("x")
        (root / "raw" / "Café notes.md").write_text("x")
        (root / "wiki" / "p.md").write_text(page('sources: ["raw/Proposal – Indy, Kirsten/doc.pdf", "raw/Café notes.md"]'))
        check_sources.ROOT, check_sources.WIKI, check_sources.RAW = root, root / "wiki", root / "raw"
        r = check_sources.audit()
        check("a citation differing only by an invisible space or an accent's spelling resolves",
              r["ok"] == 2 and not r["drift"] and not r["absent"], str(r))

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
