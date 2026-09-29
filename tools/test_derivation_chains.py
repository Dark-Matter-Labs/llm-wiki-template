#!/usr/bin/env python3
"""
test_derivation_chains.py — how far a page sits from any source.

  python3 tools/test_derivation_chains.py
"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import derivation_chains as C  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(root, slug, title, type_="synthesis", sources="[]", body="", extra=""):
    (root / "wiki").mkdir(exist_ok=True)
    (root / "wiki" / f"{slug}.md").write_text(
        f"---\ntype: {type_}\ntitle: {title}\ndescription: d\ntags: [t]\nstatus: draft\nvisibility: internal\n"
        f"confidence: low\ntimestamp: 2026-09-01\nsources: {sources}\n{extra}---\n\n{body}\n")


def rows(root, hops=2):
    return {r["title"]: r for r in C.chains(root, hops)["rows"]}


def main():
    print("derivation_chains — distance from a source\n")
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        page(root, "src", "Grounded", "summary", "[raw/report.pdf]")
        page(root, "one", "One Hop", body="Built on [[Grounded]].")
        page(root, "two", "Two Hops", body="Built on [[One Hop]].")
        page(root, "three", "Three Hops", body="Built on [[Two Hops]]. Also cited by [[Island]].")
        page(root, "island", "Island", body="Links only to [[Three Hops]].")
        page(root, "goal", "A Goal", "goal", body="Rests on [[Three Hops]].")
        page(root, "labelled", "Labelled Source", "concept", "[]", extra="derivation: source\n")
        page(root, "mixed", "Mostly Unsourced", body="[[Two Hops]], [[Three Hops]], [[Island]], [[Grounded]].")
        page(root, "alone", "Standing Alone", body="No links, no sources.")
        (root / "wiki" / "challenges").mkdir()
        page(root, "challenges/joker", "Joker Brief", body="Against [[Three Hops]] and [[Island]].")
        r = rows(root)
        check("a page that names a source is not reported", "Grounded" not in r and "Labelled Source" not in r, str(list(r)))
        check("a page one hop from a source, all of whose links are sourced, is not reported", "One Hop" not in r, str(r.get("One Hop")))
        check("a page with no source within two hops is reported with no distance",
              "Three Hops" in r and r["Three Hops"]["distance"] is None, str(r.get("Three Hops")))
        check("a cycle of unsourced pages is reported and does not loop",
              "Island" in r and r["Island"]["distance"] is None, str(r.get("Island")))
        check("a page reachable to a source but leaning mostly on unsourced pages is reported",
              "Mostly Unsourced" in r and r["Mostly Unsourced"]["distance"] == 1, str(r.get("Mostly Unsourced")))
        check("goals, commitments and overviews stand on other pages by design", "A Goal" not in r)
        check("a counterposition brief stands on other pages by design", "Joker Brief" not in r)
        un = [x["title"] for x in C.chains(root)["unlinked"]]
        check("a page with no source and no links is counted apart, not as a chain",
              "Standing Alone" in un and "Standing Alone" not in r, f"{un} / {list(r)}")
        r3 = rows(root, hops=3)
        check("widening the reach finds the source for the three-hop page",
              "Three Hops" not in r3 or r3["Three Hops"]["distance"] == 3, str(r3.get("Three Hops")))
        check("the most leaned-on unreachable page comes first",
              C.chains(root)["rows"][0]["title"] == "Three Hops", str([x["title"] for x in C.chains(root)["rows"]]))
    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
