#!/usr/bin/env python3
"""
derivation_chains.py — pages built from pages built from pages, with no source underneath.

Built 29 September 2026, from a review of the Hacker News thread on Karpathy's LLM-wiki gist and
the model-collapse paper it cited (Shumailov et al., Nature 2024). The paper measures a model
retrained on its own output with the real data replaced each generation. Nothing here retrains,
and `raw/` is immutable, which is the condition the paper finds prevents collapse. The analogy that
does hold is narrower: a synthesis written from syntheses, each paraphrasing the last, drifts
from what any source said, and nothing measured how far a page sits from one.

A page is **grounded** when its `sources:` names a file in `raw/`. The `derivation:` label cannot
carry this yet (48 of 837 pages carry it), so the sources list is the signal. For each page with
no source, this walks its `[[links]]` outward and reports the distance to the nearest grounded
page, and what share of its links lead to grounded pages at all.

**A link is not a derivation.** A page can link to a page it did not build on, and cite a source
in prose without listing it. So this routes attention and decides nothing, like
`dependency_staleness.py`, and for the same reason has no `--check`: an ungrounded chain appears
when good pages are written on top of other good pages, and a gate that failed that would be
switched off. Goals, commitments and overviews stand on other pages by design and are left out.

What to do with a row is a person's call: add the source the claims rest on, label the page
`derivation: derivative` so the layer is visible, or read the chain and stand behind it.

  python3 tools/derivation_chains.py            # the ungrounded chains, most leaned-on first
  python3 tools/derivation_chains.py --hops 3 --json
"""

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import export  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
BY_DESIGN = {"goal", "commitment", "overview"}
# Folders whose pages stand on other pages by design: counterposition briefs argue against the
# corpus, newsletters and reflections report on it, and CRM records hold relationships, not claims.
BY_DESIGN_DIRS = ("challenges/", "newsletter/", "reflections/", "crm/", "deltas/")


def grounded(node):
    return node.get("derivation") == "source" or any(
        str(s).strip().startswith("raw/") for s in (node.get("sources") or []))


def nearest(nodes, start, hops):
    """(distance, path of slugs) to the nearest grounded page within `hops`, or (None, [])."""
    seen = {start}
    frontier = collections.deque([(start, [start])])
    while frontier:
        slug, path = frontier.popleft()
        if len(path) - 1 >= hops:
            continue
        for nxt in nodes[slug]["outbound_links"]:
            if nxt in seen or nxt not in nodes:
                continue
            seen.add(nxt)
            if grounded(nodes[nxt]):
                return len(path), path + [nxt]
            frontier.append((nxt, path + [nxt]))
    return None, []


def chains(root=ROOT, hops=2):
    nodes, _ = export.build_nodes(str(pathlib.Path(root) / "wiki"))
    rows = []
    for slug, n in nodes.items():
        if (grounded(n) or n.get("type") in BY_DESIGN or n.get("status") == "dormant"
                or slug.startswith(BY_DESIGN_DIRS)):
            continue
        links = [s for s in n["outbound_links"] if s in nodes]
        share = (sum(grounded(nodes[s]) for s in links) / len(links)) if links else 0.0
        dist, path = nearest(nodes, slug, hops)
        rows.append({"slug": slug, "title": n.get("title"), "type": n.get("type"),
                     "labelled": n.get("derivation"), "inbound": len(n["inbound_links"]),
                     "links": len(links), "grounded_share": round(share, 2),
                     "distance": dist, "path": [nodes[s].get("title") for s in path]})
    # A page with no source and no links is not a chain: it names nothing it rests on at all.
    # Counted apart, because the question for it is different ("where does this come from?").
    unlinked = sorted((r for r in rows if not r["links"]), key=lambda r: -r["inbound"])
    ungrounded = [r for r in rows if r["links"] and (r["distance"] is None or r["grounded_share"] < 0.5)]
    ungrounded.sort(key=lambda r: (r["distance"] is not None, -r["inbound"], r["grounded_share"]))
    return {"pages": len(nodes), "without_source": len(rows),
            "unlabelled": sum(1 for r in rows if not r["labelled"]),
            "hops": hops, "rows": ungrounded, "unlinked": unlinked}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pages far from any source.")
    ap.add_argument("--hops", type=int, default=2, help="how far to look for a grounded page (default 2)")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    r = chains(args.root, args.hops)
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    none = [x for x in r["rows"] if x["distance"] is None]
    print(f"{r['without_source']} of {r['pages']} pages name no source in raw/ "
          f"({r['unlabelled']} of them carry no derivation label).")
    print(f"{len(none)} have no grounded page within {r['hops']} link(s); "
          f"{len(r['rows']) - len(none)} more lean mostly on other unsourced pages.")
    if r["unlinked"]:
        names = ", ".join(x["title"] for x in r["unlinked"][:5])
        print(f"{len(r['unlinked'])} name no source and link to nothing, so say nothing of where they come from: {names}"
              + (" ..." if len(r["unlinked"]) > 5 else ""))
    print()
    for x in r["rows"][:args.top]:
        where = "no source within reach" if x["distance"] is None else f"nearest source {x['distance']} hop(s) away"
        print(f"  {x['title']}  [{x['type']}, {x['inbound']} page(s) lean on it]")
        print(f"      {where}; {int(x['grounded_share'] * 100)}% of its {x['links']} link(s) reach a sourced page")
    print("\nA link is not a derivation: this routes attention and decides nothing. For each row a person")
    print("chooses: add the source, label it `derivation: derivative`, or read the chain and stand behind it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
