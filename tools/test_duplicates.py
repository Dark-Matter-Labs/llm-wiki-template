#!/usr/bin/env python3
"""
test_duplicates.py — candidates for a person to judge, with the one rule that is never a
judgement: two versions of a thing are never folded.

  python3 tools/test_duplicates.py
"""

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import duplicates as D  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(root, rel, title, type_="concept", extra=""):
    p = root / "wiki" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\ntype: {type_}\ntitle: \"{title}\"\ndescription: d\ntags: [t]\nstatus: draft\n"
                 f"visibility: internal\nconfidence: low\ntimestamp: 2026-09-01\nsources: []\n{extra}---\n\nBody.\n")


def pairs(root, key="within"):
    return {(r["a"], r["b"], r["verdict"]) for r in D.candidates(root)[key]}


def verdicts(root, key="within"):
    return {frozenset((r["a"], r["b"])): r["verdict"] for r in D.candidates(root)[key]}


def main():
    print("duplicates — propose, never merge\n")
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        page(root, "cocf.md", "Civilization Options Capability Fund")
        page(root, "cocf-acr.md", "Civilization Options Capability Fund (COCF)")
        page(root, "wg.md", "The Witnessing Grammar")
        page(root, "wg3.md", "The Witnessing Grammar (v3.0)")
        page(root, "p1.md", "Being Human, Part One")
        page(root, "p2.md", "Being Human, Part Two")
        page(root, "cof.md", "Civilization Options Fund")
        page(root, "salmon.md", "Nobody Can Save the Salmon")
        page(root, "x-summary.md", "Nobody Can Save the Salmon (Summary)", type_="summary")
        page(root, "crm/acct.md", "Salmon Trust (account)", type_="entity")
        page(root, "trust.md", "Salmon Trust", type_="entity")
        page(root, "a.md", "Alpha Standard")
        page(root, "a2.md", "Alpha Standard Restated", extra='same_as: ["Alpha Standard"]\n')
        v = verdicts(root)

        check("a title and its acronym form are a fold candidate",
              v.get(frozenset(("Civilization Options Capability Fund", "Civilization Options Capability Fund (COCF)"))) == "fold?", str(v))
        check("a page and a versioned copy of it are never folded",
              v.get(frozenset(("The Witnessing Grammar", "The Witnessing Grammar (v3.0)"))) == "never fold", str(v))
        check("Part One and Part Two are never folded",
              v.get(frozenset(("Being Human, Part One", "Being Human, Part Two"))) == "never fold", str(v))
        check("a title inside a longer one is a check, not a fold",
              v.get(frozenset(("Civilization Options Fund", "Civilization Options Capability Fund"))) in (None, "check"), str(v))
        check("a summary and the page it summarises are not a candidate",
              frozenset(("Nobody Can Save the Salmon", "Nobody Can Save the Salmon (Summary)")) not in v, str(v))
        check("a CRM record and the knowledge page about the same organisation are not a candidate",
              not any("Salmon Trust (account)" in k for k in v), str(v))
        check("pages already joined with same_as are not a candidate",
              frozenset(("Alpha Standard", "Alpha Standard Restated")) not in v, str(v))
        check("unrelated titles are never paired",
              not any("Nobody Can Save the Salmon" in k and "Alpha Standard" in k for k in v))

        cache = root / ".commons" / "xco-team-wiki" / "export"
        cache.mkdir(parents=True)
        (cache / "wiki.shared.json").write_text(json.dumps({"nodes": [
            {"slug": "sal", "title": "Nobody Can Save The Salmon (v2)", "type": "concept"},
            {"slug": "same", "title": "Salmon Trust", "type": "entity"},
            {"slug": "copy", "title": "The Witnessing Grammar", "type": "concept"}]}))
        a = D.candidates(root)["against_commons"]
        check("a near-duplicate in the commons is found", any(r["commons"] == "xco-team-wiki" for r in a), str(a))
        check("a commons copy of a page here does not repeat a within-wiki pair",
              not any(r["b"] == "The Witnessing Grammar" for r in a), str(a))
        check("the same title in the commons is not reported (seeded or contributed copies)",
              not any(r["b"] == "Salmon Trust" and r["a"] == "Salmon Trust" for r in a), str(a))

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
