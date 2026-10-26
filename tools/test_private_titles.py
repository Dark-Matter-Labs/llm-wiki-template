#!/usr/bin/env python3
"""test_private_titles.py — a private title in plain words is named, a link or a public title is not, and nothing
is ever changed: the tool only warns."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import private_titles as pt  # noqa: E402


def page(d, slug, title, vis, body):
    open(os.path.join(d, slug + ".md"), "w").write(
        f"---\ntype: concept\ntitle: {title}\ndescription: d\ntags: [t]\nstatus: draft\nvisibility: {vis}\n"
        f"confidence: low\ntimestamp: 2026-10-26\nsources: []\n---\n\n{body}\n")


def main():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok &= bool(cond)

    with tempfile.TemporaryDirectory() as d:
        page(d, "deal", "Secret Deal Alpha", "private", "x")
        page(d, "capital", "Capital", "private", "x")
        page(d, "open", "Open Note", "public", "x")
        body = "We discussed secret deal alpha at length. See [[Secret Deal Alpha]]. Capital matters. Open Note too."
        page(d, "out", "Going Out", "public", body)
        before = open(os.path.join(d, "out.md")).read()
        titles = pt.private_titles(d)
        found = pt.mentions(before, titles)
        check("only private titles are listed", titles == ["Capital", "Secret Deal Alpha"])
        check("a private title in plain words is named, ignoring case", ("Secret Deal Alpha", 1, False) in found)
        check("a link is not counted: the export already removes it", dict((t, n) for t, n, _ in found)["Secret Deal Alpha"] == 1)
        check("a one-word title is marked as probably ordinary, and listed last", found[-1] == ("Capital", 1, True))
        check("a public title is never named", all(t != "Open Note" for t, _n, _o in found))
        check("part of a longer word is not a mention", pt.mentions("Capitalism and decapitalised", ["Capital"]) == [])
        check("it always exits 0 and changes nothing",
              pt.main([os.path.join(d, "out.md"), "--wiki", d]) == 0 and open(os.path.join(d, "out.md")).read() == before)
    print("\nall passed" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
