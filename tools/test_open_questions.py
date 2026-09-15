#!/usr/bin/env python3
"""
test_open_questions.py — prove it gathers only what somebody wrote, and leaks nothing.

Two risks. It could invent questions out of prose, which would fill the list with things nobody
asked and make it worthless within a week. Or it could carry private material into a report
somebody pastes into a channel. Most of the cases below are about the second.

Usage:  python3 tools/test_open_questions.py
"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import open_questions as Q  # noqa: E402

PAGE = """---
type: concept
title: {title}
visibility: {vis}
timestamp: 2026-09-01
---

# {title}

Body text. Nobody has settled this, and it is not a question.

{extra}
"""


def write(d, name, title, vis, extra=""):
    (d / name).write_text(PAGE.format(title=title, vis=vis, extra=extra), encoding="utf-8")


def run(build, **kw):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "wiki").mkdir()
        build(root / "wiki")
        old = (Q.ROOT, Q.WIKI)
        Q.ROOT, Q.WIKI = root, root / "wiki"
        try:
            return Q.gather(**kw)
        finally:
            Q.ROOT, Q.WIKI = old


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
        if not ok:
            fails.append(name)

    SECTION = "## Open questions\n\n- Who pays for the continuity coupon?\n- What is the bound?\n"

    m = run(lambda w: write(w, "a.md", "Alpha", "internal", SECTION))
    check("an Open questions section is gathered", m["totals"]["items"] == 2, str(m["totals"]))

    # The thing that would ruin it: guessing. "Nobody has settled this" is in every fixture.
    m = run(lambda w: write(w, "a.md", "Alpha", "internal"))
    check("prose is never read as a question", m["totals"]["pages"] == 0)

    m = run(lambda w: write(w, "a.md", "Alpha", "internal", "Left for _(Indy to confirm)_ here.\n"))
    check("an explicit wait is gathered", m["totals"]["waits"] == 1)
    check("...and the person is named", m["pages"][0]["waits"][0]["who"] == "Indy")

    # A heading ends the section. Otherwise one page's questions swallow the rest of it.
    m = run(lambda w: write(w, "a.md", "Alpha", "internal",
                            SECTION + "\n## Something else\n\n- not a question\n"))
    check("the section stops at the next heading", m["totals"]["items"] == 2, str(m["totals"]))

    # --- the leak, which is the one that matters --------------------------------------
    def both(w):
        write(w, "pub.md", "Public one", "internal", SECTION)
        write(w, "priv.md", "Private one", "private", SECTION + "Left for Indy to confirm.\n")

    m = run(both)
    check("private material is included by default, for the owner",
          any(p["visibility"] == "private" for p in m["pages"]))

    m = run(both, shareable=True)
    vis = {p["visibility"] for p in m["pages"]}
    check("--shareable drops every private page", "private" not in vis, str(vis))
    check("...and drops its waits with it", m["totals"]["waits"] == 0)
    check("...and drops its questions with it", m["totals"]["items"] == 2, str(m["totals"]))
    blob = Q.render(m)
    check("...and the rendered report says private was excluded", "private material excluded" in blob)
    check("...and never prints a private page's title", "Private one" not in blob)

    # A page with no visibility set defaults to private, per the schema default.
    m = run(lambda w: (w / "x.md").write_text(
        "---\ntype: concept\ntitle: Unmarked\n---\n\n" + SECTION, encoding="utf-8"),
        shareable=True)
    check("a page with no visibility is treated as private", m["totals"]["pages"] == 0,
          "the schema default is private, and a missing tier must not read as public")

    # --- scope ------------------------------------------------------------------------
    def with_log(w):
        write(w, "a.md", "Alpha", "internal", SECTION)
        (w / "log").mkdir()
        write(w / "log", "2026-09-01.md", "A day", "internal", SECTION)
        (w / "index").mkdir()
        write(w / "index", "concepts.md", "Shelf", "internal", SECTION)

    m = run(with_log)
    check("log files and index shelves are not scanned", m["totals"]["pages"] == 1,
          str([p["path"] for p in m["pages"]]))

    # --- the refusal ------------------------------------------------------------------
    src = pathlib.Path(__file__).resolve().parent.joinpath("open_questions.py").read_text()
    check("no --check flag exists", '"--check"' not in src,
          "having open questions is the normal state of a corpus that is thinking")

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
