#!/usr/bin/env python3
"""
test_ino_check.py — the INO check's edge cases.

house-rules: ignore-file

  python3 tools/test_ino_check.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ino_check import check_text, verdict  # noqa: E402

PLAN = """---
type: summary
title: A plan
visibility: private
validation: machine
---
# A plan

We will deliver three workshops by March and a report after each.
"""

INQUIRY = """---
type: question
title: Can a question organise the week?
steward: Robyn
recommit: 2026-11-20
---
# Can a question organise the week?

## Hypotheses
1. Questions can lead the stand-up. Silent: untested.

## What would change our mind
A month in which nothing anyone did named a question.

What this page cannot hold: who felt free to speak.
"""

QUOTED = """---
title: Quoting someone
---
> Our hunch is that this could be wrong, recommit on 2026-11-20.

Nothing of our own here.
"""

HTML = """<html><body><h1>A brief</h1><p>Version 1.0 · last updated on 22 October 2026, by Robyn.</p>
<h2>Our hunches</h2><p>The seas can be wrong about this.</p><p>Review point: 16 December 2026.</p>
<p>The figures are unsourced and for the convening to test.</p><p>It serves the question of carried risk.</p></body></html>"""


def test_plan():
    r = check_text(PLAN)
    v, missing = verdict(r)
    assert v.startswith("reads as a plan"), v
    assert set(missing) >= {"hunches", "mind", "reopen"}, missing


def test_inquiry():
    r = check_text(INQUIRY)
    v, missing = verdict(r)
    assert not missing, (v, missing)
    assert r["who"]["evidence"] == "`steward:` in the page's details"
    assert r["reopen"]["evidence"] == "`recommit:` in the page's details"


def test_blockquotes_do_not_count():
    r = check_text(QUOTED)
    assert not r["hunches"]["found"]
    assert not r["reopen"]["found"]


def test_html():
    r = check_text(HTML, is_html=True)
    v, missing = verdict(r)
    assert not missing, (v, missing)


def test_not_confirmed_steward_does_not_count():
    r = check_text(INQUIRY.replace("steward: Robyn", "steward: Not confirmed"))
    assert r["who"]["evidence"] != "`steward:` in the page's details"


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ino-check tests OK — {n} case(s)")
