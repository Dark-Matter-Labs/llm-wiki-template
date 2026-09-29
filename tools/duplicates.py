#!/usr/bin/env python3
"""
duplicates.py — pairs of pages that may be about the same thing, for a person to decide.

Adopted 29 September 2026 from the awesome-llm-wiki review. Two ideas, both cheap:

  * **Two stages** (graphwiki). A deterministic pass proposes candidates by title; a judgement
    decides each one. A single similarity threshold does badly here, because pages that are
    related but distinct often look more alike than true restatements do.
  * **Fold, or never fold** (sage-wiki). A restatement ("Civilization Options Capability Fund"
    and "... (COCF)") is a merge candidate. Two versions of one thing ("The Witnessing Grammar"
    and "... (v3.0)") are never merged, however alike they look: they are linked, and if one
    replaces the other, a person records `superseded_by`.

This proposes and never merges, renames or deletes. `lint` reads it; the model judges each pair
against the page bodies; the owner decides. Pairs already joined (`same_as`, `superseded_by`,
`devalued_by`, a summary and the entity it summarises) are left out.

Against the commons it reads the cached cut in `.commons/<name>/export/`, so a page here that
duplicates one the group already holds, under a slightly different title, is found too.

  python3 tools/duplicates.py
  python3 tools/duplicates.py --json
"""

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import export  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
STOP = {"the", "a", "an", "of", "and", "for", "in", "on", "to", "as", "at", "by", "with", "from", "its"}
VERSION = re.compile(r"\bv(?:ersion)?\s*\.?\s*\d+(?:\.\d+)*[a-z]?\b|\b(?:part|volume|vol|edition|issue)\s+[\w-]+\b"
                     r"|\b(?:19|20)\d{2}(?:-\d{2}){0,2}\b|\b(?:first|second|third|fourth|fifth)\s+(?:edition|statement|draft)\b",
                     re.I)
PAREN = re.compile(r"\s*\(([^)]*)\)\s*")


def versions(title):
    return {re.sub(r"\s+", " ", v.lower().replace("version", "v")).replace("v ", "v").strip()
            for v in VERSION.findall(title)}


def core(title):
    """The title with versions, bracketed asides and filler removed, as a set of word tokens."""
    t = VERSION.sub(" ", PAREN.sub(" ", title or ""))
    toks = [w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP]
    return frozenset(toks)


def related(a, b):
    """How two titles relate: 'same', 'contained' or None. Never similarity alone."""
    ca, cb = core(a), core(b)
    if not ca or not cb:
        return None
    if ca == cb:
        return "same"
    small, big = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
    if len(small) >= 2 and small <= big and len(big) - len(small) <= 2:
        return "contained"
    inter = len(ca & cb)
    if inter >= 3 and inter / len(ca | cb) >= 0.75:
        return "contained"
    return None


def verdict(a, b, how):
    va, vb = versions(a), versions(b)
    if va != vb:
        return "never fold", "different versions of one thing: link them, and a person records superseded_by if one replaces the other"
    if how == "same":
        return "fold?", "may say the same thing twice: merge into one page if the bodies agree"
    # One title inside another is as often a different thing ("Civilization Options Fund" and
    # "... Capability Fund") as the same one. That is the judgement stage 2 exists for.
    return "check", "related titles: read both; most such pairs are distinct, some are restatements"


def _local(wiki_dir):
    pages = []
    for slug, _p, fm, _b in export.discover(str(wiki_dir)):
        if not isinstance(fm.get("title"), str) or slug.startswith(("log/", "index/")):
            continue
        linked = set()
        for key in ("same_as", "superseded_by", "devalued_by", "contradicts", "parent"):
            v = fm.get(key)
            for x in (v if isinstance(v, list) else [v] if v else []):
                linked.add(str(x).strip().strip('"').lower())
        pages.append({"slug": slug, "title": fm["title"], "type": fm.get("type"),
                      "status": fm.get("status"), "origin": fm.get("origin"), "linked": linked})
    return pages


def _commons(root):
    out = []
    for f in sorted((root / ".commons").glob("*/export/wiki.shared.json")):
        try:
            nodes = json.loads(f.read_text(encoding="utf-8")).get("nodes", [])
        except (OSError, ValueError):
            continue
        nodes = list(nodes.values()) if isinstance(nodes, dict) else nodes
        name = f.parent.parent.name
        out += [{"wiki": name, "slug": n.get("slug"), "title": n.get("title"), "type": n.get("type")}
                for n in nodes if isinstance(n.get("title"), str)]
    return out


def _joined(p, q):
    if q["title"].lower() in p["linked"] or p["title"].lower() in q.get("linked", set()):
        return True
    # a summary and the entity or concept it summarises are two pages on purpose
    return "summary" in {p.get("type"), q.get("type")} and p.get("type") != q.get("type")


def candidates(root=ROOT):
    root = pathlib.Path(root)
    # CRM records sit beside the knowledge page about the same organisation on purpose: the
    # record is private and holds the relationship, the page holds what is known.
    local = [p for p in _local(root / "wiki")
             if p.get("status") != "dormant" and not p["slug"].startswith("crm/")]
    within, against = [], []
    for i, p in enumerate(local):
        for q in local[i + 1:]:
            how = related(p["title"], q["title"])
            if how and not _joined(p, q):
                v, why = verdict(p["title"], q["title"], how)
                within.append({"a": p["title"], "b": q["title"], "a_slug": p["slug"], "b_slug": q["slug"],
                               "match": how, "verdict": v, "why": why})
    for p in local:
        for c in _commons(root):
            if c["title"] == p["title"]:
                continue  # the same page, seeded or contributed; same_as covers independent ones
            how = related(p["title"], c["title"])
            if how and not _joined(p, c):
                v, why = verdict(p["title"], c["title"], how)
                against.append({"a": p["title"], "b": c["title"], "commons": c["wiki"], "a_slug": p["slug"],
                                "match": how, "verdict": v, "why": why})
    return {"within": within, "against_commons": against}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pages that may be about the same thing.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    got = candidates(args.root)
    if args.json:
        print(json.dumps(got, indent=2, ensure_ascii=False))
        return 0
    for label, key in (("In this wiki", "within"), ("Against the commons", "against_commons")):
        rows = got[key]
        print(f"{label}: {len(rows)} candidate pair(s)")
        for r in rows:
            where = f"  [{r['commons']}]" if "commons" in r else ""
            print(f"  {r['verdict']:<11} {r['a']}\n              {r['b']}{where}")
    print("\nCandidates only. Read both pages before proposing anything; a person decides.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
