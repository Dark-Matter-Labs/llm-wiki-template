#!/usr/bin/env python3
"""
test_tag_report.py — one tag written several ways is found; different tags are never merged.

  python3 tools/test_tag_report.py
"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tag_report as T  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(root, slug, tags):
    p = root / "wiki" / f"{slug}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\ntype: concept\ntitle: {slug}\ndescription: d\ntags: [{', '.join(tags)}]\nstatus: draft\n"
                 "visibility: internal\nconfidence: low\ntimestamp: 2026-09-01\nsources: []\n---\n\nBody.\n")


def main():
    print("tag_report — spelling variants of one tag, and how many tags stand alone\n")
    check("case, spaces and underscores are one key", T.key("Transaction Costs") == T.key("transaction_cost") == "transaction-cost")
    check("a trailing plural is one key", T.key("funders") == T.key("funder"))
    check("a word ending in -ss is not singularised", T.key("process") == "process")
    check("different words are different keys", T.key("options") != T.key("optionality"))
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        page(root, "a", ["funder", "cof"])
        page(root, "b", ["funder", "COF"])
        page(root, "c", ["funders", "optionality"])
        page(root, "d", ["options"])
        r = T.report(root)
        into = {m["into"]: m for m in r["merges"]}
        check("the most-used spelling is the one kept", "funder" in into and into["funder"]["variants"] == ["funders"], str(into))
        check("the pages to retag are named", into.get("funder", {}).get("slugs") == ["c"], str(into.get("funder")))
        check("case variants are grouped", "cof" in into or "COF" in into, str(into))
        check("optionality and options are never merged", not any("optionality" in m["variants"] + [m["into"]] and
              "options" in m["variants"] + [m["into"]] for m in r["merges"]), str(r["merges"]))
        (root / "design").mkdir()
        (root / "design" / "tags.json").write_text('{"keep_apart": [["funder", "funders"]]}')
        check("a group the owner kept apart is not proposed again",
              not any(m["into"] == "funder" for m in T.report(root)["merges"]), str(T.report(root)["merges"]))
        check("one-page tags are counted and listed", r["used_once"] == len(r["singletons"]) and "optionality" in r["singletons"], str(r))
    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
