#!/usr/bin/env python3
"""
tag_report.py — how many tags the wiki carries, and which are the same tag written differently.

Adopted 29 September 2026 from the awesome-llm-wiki review. A practitioner who ran one of these
wikis across 880 commits reported 662 tags and found his healthiest weeks were consolidation
passes. This wiki had 1,958 distinct tags on 837 pages when it was measured, 1,203 of them used
once. A tag used once groups nothing; the same idea under three spellings splits a group in three.

It proposes merges and changes nothing. `lint` reads it, the owner approves which groups to merge,
and the edit is then a frontmatter change to the pages named. Variants are grouped only on
spelling (case, spaces, underscores, a trailing plural), never on meaning, so every group it
proposes is one a person can accept at a glance.

  python3 tools/tag_report.py
  python3 tools/tag_report.py --json
"""

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import export  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def key(tag):
    k = re.sub(r"[\s_]+", "-", tag.strip().lower())
    k = re.sub(r"[^a-z0-9-]", "", k).strip("-")
    k = re.sub(r"-+", "-", k)
    if len(k) > 4 and k.endswith("s") and not k.endswith(("ss", "us", "is")):
        k = k[:-1]
    return k


def report(root=ROOT):
    root = pathlib.Path(root)
    use = collections.Counter()
    where = collections.defaultdict(set)
    pages = 0
    for slug, _p, fm, _b in export.discover(str(root / "wiki")):
        tags = fm.get("tags") or []
        tags = tags if isinstance(tags, list) else [tags]
        if tags:
            pages += 1
        for t in tags:
            t = str(t).strip()
            if t:
                use[t] += 1
                where[t].add(slug)
    groups = collections.defaultdict(list)
    for t in use:
        groups[key(t)].append(t)
    merges = []
    for k, variants in groups.items():
        if len(variants) > 1:
            variants.sort(key=lambda t: (-use[t], t))
            merges.append({"into": variants[0], "variants": variants[1:],
                           "pages": sum(use[v] for v in variants[1:]),
                           "slugs": sorted(set().union(*(where[v] for v in variants[1:])))})
    merges.sort(key=lambda m: -m["pages"])
    once = sorted(t for t, v in use.items() if v == 1)
    return {"pages": pages, "distinct": len(use), "used_once": len(once), "singletons": once,
            "merges": merges, "top": use.most_common(15)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tag sprawl, and variants of one tag.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    r = report(args.root)
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    print(f"{r['distinct']} distinct tags on {r['pages']} pages; {r['used_once']} used on one page only.")
    print(f"{len(r['merges'])} group(s) are one tag written more than one way:")
    for m in r["merges"][:40]:
        print(f"  {m['into']}  <-  {', '.join(m['variants'])}   ({m['pages']} page(s) to retag)")
    if len(r["merges"]) > 40:
        print(f"  ... and {len(r['merges']) - 40} more (--json for all)")
    print(f"\nSpelling explains little of the sprawl. The {r['used_once']} one-page tags are the rest: lint")
    print("proposes folding them into broader tags already in use, a judgement the owner approves.")
    print("Proposals only. Nothing is retagged until the owner says which.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
