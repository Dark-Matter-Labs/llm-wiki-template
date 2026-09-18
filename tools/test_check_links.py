#!/usr/bin/env python3
"""
test_check_links.py — the properties that make a link gate worth having.

The gate exists because one wasn't there: `[[xCO Capital Formation Architecture]]` (the page is
`The xCO Capital-Formation Architecture`) passed every check in CI, and a deliberately nonexistent
target still produced *"schema check OK — 778 pages valid."*

But a link checker is easy to build badly, and a badly-built one is worse than none — it cries
wolf on prose and gets ignored. So the properties tested here are as much about **what must not be
reported** as what must:

  1. A link to a page that does not exist **is** reported. The whole point.
  2. A link inside a code span or fenced block **is not**. This corpus contains a lot of prose
     *about* wiki-links — `[[links]]`, `[[wiki-link]]`, `[[xCO:Page Title]]` — and 13 of the first
     scan's 28 hits were that. Documentation about links must not read as broken links.
  3. An **aliased** link resolves on its target, not its display text.
  4. An aliased link **inside a markdown table**, where the pipe is escaped as `\\|`, resolves.
     `CLAUDE.md` records this as one of the two ways a link silently dies.
  5. A link **wrapped across a newline** resolves. The other recorded way.
  6. The baseline suppresses known debt and **not** anything new.

Properties 3–5 are inherited rather than implemented: the checker reuses the exporter's own regex
and title normaliser, so it answers "would this edge survive the export?" rather than "does this
look like a link to me." They are tested anyway, because inheritance is a claim that can break.

  python3 tools/test_check_links.py
"""

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_links as cl  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(d, name, title, body):
    (d / name).write_text(
        f"---\ntype: concept\ntitle: {title}\ndescription: d\ntags: [t]\nstatus: draft\n"
        f"visibility: internal\nconfidence: low\nvalidation: machine\ntimestamp: 2026-08-31\n"
        f"sources: []\n---\n\n{body}\n", encoding="utf-8")


def build(tmp, body, shelf=None, router=None, logentry=None):
    root = pathlib.Path(tmp)
    wiki = root / "wiki"
    wiki.mkdir()
    page(wiki, "target.md", "A Real Target", "I exist.")
    page(wiki, "subject.md", "Subject", body)
    if shelf is not None:
        (wiki / "index").mkdir(exist_ok=True)
        (wiki / "index" / "summaries.md").write_text(shelf, encoding="utf-8")
    if router is not None:
        (wiki / "index.md").write_text(router, encoding="utf-8")
    if logentry is not None:
        (wiki / "log").mkdir(exist_ok=True)
        (wiki / "log" / "2026-09-18.md").write_text(logentry, encoding="utf-8")
    cl.ROOT, cl.WIKI, cl.BASELINE = root, wiki, root / "links-baseline.json"
    return root


def targets_reported(tmp, body):
    build(tmp, body)
    broken, _ = cl.audit()
    return sorted(b["target"] for b in broken)


def main():
    print("check_links — report the dead, and nothing else\n")
    saved = (cl.ROOT, cl.WIKI, cl.BASELINE)
    try:
        with tempfile.TemporaryDirectory() as t:
            check("a link to a page that does not exist is reported",
                  targets_reported(t, "See [[No Such Page]].") == ["No Such Page"])

        with tempfile.TemporaryDirectory() as t:
            check("a link to a page that does exist is not",
                  targets_reported(t, "See [[A Real Target]].") == [])

        with tempfile.TemporaryDirectory() as t:
            check("a link inside an inline code span is not reported",
                  targets_reported(t, "Cross-reference with `[[links]]` throughout.") == [])

        with tempfile.TemporaryDirectory() as t:
            check("a link inside a fenced block is not reported",
                  targets_reported(t, "Example:\n\n```\n[[Some Template Placeholder]]\n```\n") == [])

        with tempfile.TemporaryDirectory() as t:
            check("an aliased link resolves on its target, not its display",
                  targets_reported(t, "See [[A Real Target|something else entirely]].") == [])

        with tempfile.TemporaryDirectory() as t:
            check("an aliased link with a broken target is still caught",
                  targets_reported(t, "See [[No Such Page|nice words]].") == ["No Such Page"])

        with tempfile.TemporaryDirectory() as t:
            # CLAUDE.md: inside a table the pipe must be escaped, which breaks a naive alias parse.
            check("an aliased link in a table, pipe escaped, resolves",
                  targets_reported(t, "| a | b |\n|---|---|\n| [[A Real Target\\|shown]] | x |") == [])

        with tempfile.TemporaryDirectory() as t:
            # CLAUDE.md: never split a wiki-link across a newline. It still resolves.
            check("a link wrapped across a newline resolves",
                  targets_reported(t, "See [[A Real\nTarget]] for more.") == [])

        with tempfile.TemporaryDirectory() as t:
            root = build(t, "See [[No Such Page]] and [[Another Dead One]].")
            cl.BASELINE.write_text(json.dumps({"unresolved": [
                {"page": "wiki/subject.md", "target": "No Such Page"}]}), encoding="utf-8")
            broken, _ = cl.audit()
            base = cl.load_baseline()
            new = [b for b in broken if (b["page"], b["target"]) not in base]
            check("the baseline suppresses known debt",
                  "No Such Page" not in [b["target"] for b in new])
            check("the baseline does not suppress a new one",
                  [b["target"] for b in new] == ["Another Dead One"],
                  f"{[b['target'] for b in new]}")
        # ---- the catalogues are checked; the log is not -------------------------------
        #
        # Until 2026-09-18 `SKIP_DIRS` held "index" as well as "log", so the shelves and the
        # router — the most link-dense files in any of these wikis, about half of every
        # wiki-link — were the only ones nobody checked. Two pages were removed from the
        # commons that day, this reported zero unresolved, and two catalogue rows were still
        # pointing at the deleted titles.
        with tempfile.TemporaryDirectory() as t:
            build(t, "nothing here.", shelf="- [[A Dead Shelf Row]] — gone.\n")
            broken, _ = cl.audit()
            check("a dead link in a catalogue shelf is reported",
                  [b["target"] for b in broken] == ["A Dead Shelf Row"], str(broken))

        with tempfile.TemporaryDirectory() as t:
            build(t, "nothing here.", router="# Index\n\n- [[A Dead Router Row]] — gone.\n")
            broken, _ = cl.audit()
            check("a dead link in the router is reported",
                  [b["target"] for b in broken] == ["A Dead Router Row"], str(broken))

        # The log is appended and never rewritten. A link in it to something since renamed
        # records what was true that day, and correcting it would falsify the record.
        with tempfile.TemporaryDirectory() as t:
            build(t, "nothing here.", logentry="## [2026-09-18] note\n\n[[A Page Since Renamed]]\n")
            broken, _ = cl.audit()
            check("a dead link in a log entry is left alone", broken == [], str(broken))

        with tempfile.TemporaryDirectory() as t:
            build(t, "nothing here.", shelf="- [[A Real Target]] — fine.\n",
                  router="# Index\n\n- [[A Real Target]] — fine.\n")
            broken, total = cl.audit()
            check("live catalogue links resolve and are counted",
                  broken == [] and total >= 2, f"broken={broken} total={total}")

        # MUTATION: put "index" back in SKIP_DIRS and the shelf case must stop reporting.
        with tempfile.TemporaryDirectory() as t:
            build(t, "nothing here.", shelf="- [[A Dead Shelf Row]] — gone.\n")
            saved_skip = cl.SKIP_DIRS
            try:
                cl.SKIP_DIRS = {"index", "log"}
                broken, _ = cl.audit()
            finally:
                cl.SKIP_DIRS = saved_skip
            check("mutant misses the dead shelf row", broken == [], str(broken))

    finally:
        cl.ROOT, cl.WIKI, cl.BASELINE = saved

    print()

    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
