#!/usr/bin/env python3
"""
test_cross_check.py — prove the one rule that makes machine checking safe.

A second frontier model reading a page is a real signal and worth recording. It is not
validation. The `validation` ladder is load-bearing — unvalidated pages are indexed but
do not move the corpus's centre of gravity — and that protection survives exactly as long
as the rungs above `machine` require a person.

So the property under test is the shortcut that would destroy it in one line:

    validation: peer
    validated_by: [gpt-5]

Everything else here is schema hygiene.

  python3 tools/test_cross_check.py
"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cross_check as cc  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def write(wiki, name, fm_extra):
    (wiki / name).write_text(
        f"---\ntype: concept\ntitle: {name[:-3]}\ndescription: d\ntags: [t]\n"
        f"status: draft\nvisibility: internal\nvalidation: machine\n"
        f"timestamp: 2026-08-25\nsources: []\n{fm_extra}---\n\nBody.\n", encoding="utf-8")


def run(fm_extra):
    """Audit a one-page wiki carrying `fm_extra` in its frontmatter."""
    tmp = tempfile.mkdtemp()
    root = pathlib.Path(tmp)
    wiki = root / "wiki"
    wiki.mkdir()
    write(wiki, "p.md", fm_extra)
    saved = (cc.ROOT, cc.WIKI)
    cc.ROOT, cc.WIKI = root, wiki
    try:
        return cc.audit()
    finally:
        cc.ROOT, cc.WIKI = saved


def main():
    print("cross_check — a model may move confidence, never validation\n")

    for name in ("gpt-5", "Claude Opus 5", "gemini-3-pro", "some-llm", "grok-4"):
        problems, _ = run(f'confidence: medium\nvalidated_by: [{name}]\n')
        check(f"validated_by: [{name}] is refused",
              any("looks like a model" in p for p in problems), f"{problems}")

    problems, _ = run('confidence: medium\nvalidated_by: [Indy Johar]\n')
    check("validated_by: [Indy Johar] is accepted", problems == [], f"{problems}")

    problems, stats = run(
        'confidence: medium\nmachine_checks:\n  - model: gpt-5.2\n'
        '    date: 2026-08-25\n    verdict: agrees\n    note: reads the same\n')
    check("a well-formed machine check is accepted",
          problems == [] and stats["checks"] == 1, f"{problems} {stats}")

    problems, _ = run(
        'confidence: medium\nmachine_checks:\n  - model: gpt-5.2\n'
        '    date: 2026-08-25\n    verdict: endorses\n')
    check("a verdict outside the vocabulary is refused",
          any("is not one of" in p for p in problems), f"{problems}")

    problems, _ = run(
        'confidence: medium\nmachine_checks:\n  - model: gpt-5.2\n'
        '    date: last Tuesday\n    verdict: agrees\n')
    check("a non-ISO date is refused", any("YYYY-MM-DD" in p for p in problems), f"{problems}")

    problems, _ = run(
        'confidence: medium\nmachine_checks:\n  - date: 2026-08-25\n    verdict: agrees\n')
    check("a check with no model named is refused",
          any("has no model" in p for p in problems), f"{problems}")

    problems, stats = run(
        'confidence: high\nmachine_checks:\n  - model: gpt-5.2\n'
        '    date: 2026-08-25\n    verdict: disputes\n    note: the source says otherwise\n')
    check("a disputed page cannot also claim confidence: high",
          any("confidence: high while a machine check disputes" in p for p in problems),
          f"{problems}")
    check("the dispute is counted, not silently dropped",
          stats["disputed"] == 1, f"{stats}")

    problems, _ = run(
        'confidence: medium\nmachine_checks:\n  - model: gpt-5.2\n'
        '    date: 2026-08-25\n    verdict: disputes\n')
    check("a dispute at medium confidence stands without complaint",
          problems == [], f"{problems}")

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
