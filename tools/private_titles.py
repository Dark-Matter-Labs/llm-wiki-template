#!/usr/bin/env python3
"""
private_titles.py — before a page goes out, name any private page whose title it mentions in plain words.

The export removes links to private pages, but not a private page's title written as ordinary text. Found by a code
audit of gurden-llm-wiki on 26 October 2026. Redacting every mention was proposed and rejected: in indy-llm-wiki one
private title is an ordinary name used in 175 pages that leave the wiki, and blacking it out would damage those pages
and announce that a private page exists by that name. So this only warns. A person reads each mention and decides:
leave it, reword it, or rename the private page.

    python3 tools/private_titles.py wiki/some-page.md [more pages]     # what to read before publishing
    python3 tools/private_titles.py --json wiki/some-page.md

It always exits 0: it is a warning for the publish-check skill, never a gate.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export  # noqa: E402

LINK = re.compile(r"\[\[[^\]]*\]\]")   # links are the export's job, and it removes them


def private_titles(wiki_dir):
    return sorted({str(fm.get("title")) for _s, _p, fm, _b in export.discover(wiki_dir)
                   if fm.get("visibility", "private") == "private" and fm.get("title")}, key=str.lower)


def mentions(text, titles):
    """[(title, count, ordinary)] for each private title written as plain words in text. `ordinary` marks a
    one-word title, which is usually an everyday word rather than the private page."""
    plain = LINK.sub(" ", text)
    out = []
    for t in titles:
        n = len(re.findall(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", plain, re.I))
        if n:
            out.append((t, n, len(t.split()) == 1))
    return sorted(out, key=lambda x: (x[2], -len(x[0])))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Name private titles mentioned in plain words in pages about to go out.")
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--wiki", default=os.path.join(os.path.dirname(HERE), "wiki"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    titles = private_titles(a.wiki)
    report = {}
    for p in a.pages:
        found = mentions(open(p, encoding="utf-8").read(), titles)
        if found:
            report[p] = [{"title": t, "mentions": n, "one_word": o} for t, n, o in found]
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not report:
        print("private titles — none mentioned in plain words.")
        return 0
    print("private titles — read each mention before this goes out (a warning, not a block):")
    for p, rows in report.items():
        print(f"  {p}")
        for r in rows:
            note = "  (one word: probably an ordinary word)" if r["one_word"] else ""
            print(f"    {r['mentions']:3}x  {r['title']}{note}")
    print("Leave it, reword it, or rename the private page. Never redact by hand in bulk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
