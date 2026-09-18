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

STANDARD LIBRARY ONLY, and the irony is the point. The first version of this file
imported `yaml` and turned CI red in all eleven repos — the same failure `tools/
community.py` records for `networkx`, in a codebase with no requirements.txt, no pip
step and ~90 tools that run on a bare Python. A dependency added here is a dependency
eleven wikis must install before anything runs.

So it detects the failure class directly rather than by parsing: a top-level plain
scalar containing a colon-space, or ending in a colon, is invalid YAML with no
exceptions — `key: A Title: With a Colon` is a mapping whose key is `A Title`. Quoted,
flow and block scalars are left alone. This cannot be over-eager, because there is no
document in which an unquoted plain scalar may contain ": ".

It is checked against the real parser in `tools/test_check_frontmatter.py`, which
compares this verdict with `yaml.safe_load` over every page wherever PyYAML happens to
be installed, and skips only that comparison when it is not.

    python3 tools/check_frontmatter.py            # report
    python3 tools/check_frontmatter.py --check    # exit 1 if any page fails
"""
from __future__ import annotations

import pathlib
import re
import sys

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


TOP_LEVEL = re.compile(r"^([A-Za-z_][\w-]*):[ \t]+(.*)$")


def _plain_value(rest: str) -> str | None:
    """The plain scalar on this line, or None when YAML will not read it as one.

    Quoted, flow (`[`, `{`) and block (`|`, `>`) values are somebody else's problem and
    are legal with colons inside. A plain value ends at " #", which starts a comment.
    """
    v = rest.strip()
    if not v or v[0] in "\"'[{|>&*!":
        return None
    i = v.find(" #")
    if i >= 0:
        v = v[:i].rstrip()
    return v or None


def faults(block: str):
    """Every line YAML would refuse, as (line-number-within-block, text, why)."""
    out = []
    for i, line in enumerate(block.split("\n")):
        if line.startswith("- "):
            # A sequence where the schema wants a mapping. Legal YAML, useless here, and
            # every reader downstream expects `fm["title"]`.
            out.append((i, line, "frontmatter is a sequence, not a mapping"))
            return out
        if not line or line[0] in " \t#":
            continue                                    # nested, blank or comment
        m = TOP_LEVEL.match(line)
        if not m:
            continue
        value = _plain_value(m.group(2))
        if value is None:
            continue
        if ": " in value or "\t" in value:
            out.append((i, line, "a plain value cannot contain a colon followed by a space"))
        elif value.endswith(":"):
            out.append((i, line, "a plain value cannot end with a colon"))
    return out


def failures():
    out = []
    for p in pages():
        block = frontmatter(p.read_text(encoding="utf-8", errors="ignore"))
        if block is None:
            continue
        for idx, line, why in faults(block):
            # +2, not +1: the block starts after the opening `---`, so its line 0 is the
            # file's line 2. Reported as +1 at first, which sent the reader one line up
            # from the fault; caught by the test rather than by rereading it.
            out.append((p, why, idx + 2, line.strip()))
    return out


def main(argv) -> int:
    check = "--check" in argv
    bad = failures()
    total = sum(1 for p in pages() if frontmatter(p.read_text(encoding="utf-8", errors="ignore")) is not None)

    if not bad:
        print(f"frontmatter OK — {total} page(s) parse as YAML.")
        return 0

    pages_bad = len({p for p, *_ in bad})
    print(f"frontmatter — {pages_bad} of {total} page(s) a standard YAML parser cannot read\n")
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
