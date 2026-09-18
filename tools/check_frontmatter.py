#!/usr/bin/env python3
"""Every page's frontmatter must be readable by a standard YAML parser.

Found 2026-09-18: 28 pages across four wikis carried a title or description with an
unquoted colon, which YAML reads as a nested mapping rather than as text —

    title: Planetary Civics Inquiry: A New Framework for Planetary Futures

Nothing was broken inside the federation. Every tool here parses frontmatter with a
forgiving regex, so the graph, the links and the exports were all correct: the export
carried the same node count before and after the repair, and not one title changed.
What could not read them was anything standard.

That is the whole argument for this gate. A wiki whose case is machine-readable
structure cannot have pages only its own machines can read, and the failure is silent
by construction — no tool here would ever complain. It cost an hour the day it was
found: a parser written to measure cross-wiki identity skipped the unreadable pages
without a word and reported nineteen dangling provenance links that did not exist.

This is a hard gate rather than a ratchet. Unlike prose, there is no defensible level
of unparseable frontmatter to hold the line at, and the fix is always the same: quote
the value.

    python3 tools/check_frontmatter.py            # report
    python3 tools/check_frontmatter.py --check    # exit 1 if any page fails
"""
from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"


def pages():
    if not WIKI.exists():
        return
    for p in sorted(WIKI.rglob("*.md")):
        yield p


def frontmatter(raw: str):
    """The frontmatter block, or None when the file carries none.

    A page without frontmatter is not this gate's business — `index.md` and `log.md`
    are exempt by design, and the schema checks own that question.
    """
    if not raw.startswith("---"):
        return None
    end = raw.find("\n---", 3)
    if end < 0:
        return None
    return raw[4:end]


def failures():
    out = []
    for p in pages():
        block = frontmatter(p.read_text(encoding="utf-8", errors="ignore"))
        if block is None:
            continue
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            lines = block.split("\n")
            line = lines[mark.line] if mark and mark.line < len(lines) else ""
            # +2, not +1: the block handed to YAML starts after the opening `---`, so its
            # line 0 is the file's line 2. Reported as +1 at first, which sent the reader
            # one line up from the fault; caught by the test rather than by rereading it.
            out.append((p, str(exc).split("\n")[0], (mark.line + 2) if mark else None, line.strip()))
            continue
        if parsed is not None and not isinstance(parsed, dict):
            out.append((p, f"frontmatter is {type(parsed).__name__}, not a mapping", None, ""))
    return out


def main(argv) -> int:
    check = "--check" in argv
    bad = failures()
    total = sum(1 for p in pages() if frontmatter(p.read_text(encoding="utf-8", errors="ignore")) is not None)

    if not bad:
        print(f"frontmatter OK — {total} page(s) parse as YAML.")
        return 0

    print(f"frontmatter — {len(bad)} of {total} page(s) a standard YAML parser cannot read\n")
    for p, why, line, text in bad:
        where = f" (line {line})" if line else ""
        print(f"  {p.relative_to(ROOT)}{where}")
        print(f"     {why}")
        if text:
            print(f"     {text[:100]}")
    print(
        "\n  Almost always an unquoted value containing a colon. Wrap it in double quotes,\n"
        "  keeping any trailing `#` comment outside them. Nothing here will notice these\n"
        "  pages are unreadable — every tool in this repo parses frontmatter loosely — but\n"
        "  anything standard will fail on them."
    )
    return 1 if check else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
