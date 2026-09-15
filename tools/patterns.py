#!/usr/bin/env python3
"""patterns.py — clusters the corpus keeps forming and nobody has named.

Asked for at the Berlin meeting, 14 September 2026: *highlight emerging patterns and meta
patterns*. The house already has the definition, from Strata (DM internal note, v0.3, 12
August 2025): a **meta-pattern** is "a relationship or principle that can travel across
contexts with clear bounds", and the problem it names is **G(t) >> D(t)** — insight is
generated far faster than it is distributed and integrated. An unnamed cluster is that gap
with a shape: the corpus has built a neighbourhood and nobody has written what it is about.

WHAT IT MEASURES, AND WHY NOT SOMETHING SIMPLER

The obvious instrument is word frequency — phrases recurring across many pages. Measured on
2026-09-15 against 809 pages, the top hits were `what it argues` (438 pages), `key points`
(431) and `named entities` (174). Those are the summary template's own section headings. A
frequency detector over this corpus finds the stationery.

So the instrument is the link graph the corpus already maintains. A candidate pattern is a
cluster of pages that link to each other densely, draw on many different sources, and have
no page inside them saying what they collectively amount to.

    cohesion       how reliably these pages cluster together at all (see below)
    independence   how many DISTINCT sources feed the cluster - the guard against
                   detecting one document's vocabulary and calling it a pattern
    naming         the best synthesis/concept/overview page inside the cluster, and how
                   much of the cluster it actually touches. Low coverage is the signal.

REPRODUCIBILITY IS THE QUALITY GATE, NOT A FOOTNOTE

Louvain community detection is seeded, and a single run substantially reports its seed: on
this corpus, across five seeds, only 27 of 65 clusters reproduced and the median best-match
Jaccard was 0.79. A tool that published those would shuffle its patterns every morning.

So this runs Louvain across a fixed list of seeds and keeps only what survives: two pages
belong together if they land in the same community in at least `--agreement` of the runs.
Verified on 2026-09-15 by running the whole consensus twice over two DISJOINT seed sets
(1-24 and 101-124): 35 of 58 clusters identical, 50 of 58 recognisable, median Jaccard 1.00.
Each cluster reports its own cohesion so a soft one can be read as soft.

WHAT IT WILL NOT DO

  * It does not name the pattern. It says these pages behave like one. Naming is a
    judgement about meaning, and the same division applies here as to contradictions and
    dormancy: the machine declares, a person decides.
  * It has no `--check` and never will. Writing more pages creates more unnamed clusters,
    so a gate on this number would fail good work and get switched off. It is a sample that
    routes attention, like `verification.py --sample 3`.
  * It never reads `private`, and never reads the CRM at all - not even under
    `--include-private`. The CRM's graph IS a map of people, so its clusters are clusters of
    people, and surfacing those as "emerging patterns" is the surveillance failure the house
    rule forbids. Verified: the first prototype's densest cluster was two CRM contact pages.
  * It reports no person. `origin` names a repository; `contributed_by` is not read.

Standard library only — no networkx. See tools/community.py for why, and for the
measurement showing this implementation is conservative rather than different.

    python3 tools/patterns.py                 # the candidates, human-readable
    python3 tools/patterns.py --federation    # include the commons cuts this wiki reads
    python3 tools/patterns.py --json          # for the `patterns` skill to write from
"""
import argparse
import collections
import itertools
import json
import pathlib
import sys

import community as _c

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPORT = ROOT / "export" / "wiki.json"
COMMONS = ROOT / ".commons"

#: Louvain is seeded; one run reports its seed. See the module docstring.
SEEDS = tuple(range(1, 25))
#: Above this a community is a section of the wiki, not an idea.
COARSE = 40
#: Page types that, sitting inside a cluster, would be naming it.
NAMING_TYPES = {"synthesis", "overview", "comparison", "concept"}
#: A page outside the cluster must have at least this much of its own neighbourhood
#: inside it before it counts as naming the idea. Without it every cluster is named
#: by whichever hub page happens to touch it.
NAMING_SPECIFICITY = 0.2


def _crm(node) -> bool:
    """The CRM is a relationship map, so its clusters are clusters of people."""
    slug = node.get("slug") or ""
    return slug.startswith("crm/") or "crm" in (node.get("tags") or [])


def load_nodes(federation: bool, include_private: bool):
    """Local pages, plus the commons cuts when asked. Returns (nodes, provenance)."""
    if not EXPORT.exists():
        print(f"no export at {EXPORT} — run `python3 tools/export.py` once", file=sys.stderr)
        raise SystemExit(2)
    raw = json.loads(EXPORT.read_text(encoding="utf-8"))
    nodes = raw["nodes"] if isinstance(raw, dict) else raw
    for n in nodes:
        n["origin"] = n.get("origin") or ROOT.name
    prov = {"local": {"wiki": ROOT.name, "pages": len(nodes)}, "commons": {}}

    if federation:
        for cut in sorted(COMMONS.rglob("wiki.shared.json")):
            name = cut.relative_to(COMMONS).parts[0]
            try:
                d = json.loads(cut.read_text(encoding="utf-8"))
            except Exception:                                    # noqa: BLE001
                prov["commons"][name] = {"error": "unreadable cut"}
                continue
            got = d["nodes"] if isinstance(d, dict) else d
            # A page with no `origin` was written in the commons itself, so the commons
            # IS its origin. Left as None it reads as a wiki called "None" and, worse,
            # counts as a distinct context in the `travels` test.
            for n in got:
                n["origin"] = n.get("origin") or name
            counted = dict(collections.Counter(n["origin"] for n in got))

            # Material that flowed UP from here and came back is not another context.
            # Without this the commons returns 611 of this wiki's own pages, each
            # clusters with its own mirror, and every such cluster reports "spans 2
            # wikis" — a cross-wiki pattern manufactured out of one wiki. Caught on
            # 2026-09-15 when the same page title appeared twice inside one cluster.
            own = sum(1 for n in got if n["origin"] == ROOT.name)
            got = [n for n in got if n["origin"] != ROOT.name]
            # Slugs may collide with local ones, so namespace them.
            for n in got:
                n["slug"] = f"{name}::{n.get('slug')}"
            nodes.extend(got)
            prov["commons"][name] = {
                "pages_in_cut": sum(counted.values()),
                "read": len(got),
                "skipped_our_own": own,
                "origins": counted,
            }

    kept, dropped = [], collections.Counter()
    for n in nodes:
        if _crm(n):
            dropped["crm"] += 1
            continue
        if n.get("visibility") == "private" and not include_private:
            dropped["private"] += 1
            continue
        kept.append(n)
    prov["excluded"] = dict(dropped)
    prov["included_private"] = bool(include_private)
    return kept, prov


def build_graph(nodes):
    by = {n["slug"]: n for n in nodes}
    edges = [(n["slug"], t) for n in nodes
             for t in (n.get("outbound_links") or []) if t in by]
    return _c.from_edges(by, edges), by


def consensus(graph, resolution: float, agreement: float, seeds=None):
    """Clusters that survive reseeding. Returns [(pages, cohesion)], cohesion in 0..1.

    Two pages are joined when they land in the same community in at least `agreement` of
    the runs; a cluster's cohesion is the mean agreement over its pairs, so a cluster held
    together by bare-threshold pairs reads as weaker than one nothing ever splits.
    """
    seeds = seeds or SEEDS
    pair = collections.Counter()
    for seed in seeds:
        for c in _c.louvain_communities(graph, resolution=resolution, seed=seed):
            if len(c) > COARSE:
                continue
            for a, b in itertools.combinations(sorted(c), 2):
                pair[(a, b)] += 1

    joined = {}
    for (a, b), hits in pair.items():
        if hits / len(seeds) >= agreement:
            joined.setdefault(a, {})[b] = 1.0
            joined.setdefault(b, {})[a] = 1.0

    out = []
    for comp in _c.components(joined):
        if not 4 <= len(comp) <= 30:
            continue
        pairs = [pair[(a, b)] / len(seeds)
                 for a, b in itertools.combinations(sorted(comp), 2)]
        out.append((frozenset(comp), sum(pairs) / len(pairs) if pairs else 0.0))
    return out


#: Tried in order when no --resolution is given. Modularity's resolution term scales
#: with the graph's total edge count, so a value tuned on 809 pages shatters a 60-page
#: wiki into singletons — and the tool would then report "no patterns" rather than "wrong
#: setting", which is the same silence as having no instrument at all.
RESOLUTION_LADDER = (0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0)


def choose_resolution(graph, agreement: float):
    """Pick the resolution that puts the most pages into idea-sized stable clusters.

    The objective is PAGES COVERED, not clusters found. Maximising the count rewards
    shattering: on this corpus the count climbs all the way to 16.0 while coverage peaks
    at 4.0 and then falls as real groups break below the size floor. Coverage has a knee;
    the count does not.

    Swept with a short seed list because this only has to rank the ladder; the winner is
    then re-run over the full list. Deterministic — fixed ladder, and ties go to the
    lower resolution, which merges rather than splits.
    """
    best, best_cov = RESOLUTION_LADDER[0], -1
    for res in RESOLUTION_LADDER:
        cov = sum(len(c) for c, _ in consensus(graph, res, agreement, seeds=SEEDS[:6]))
        if cov > best_cov:
            best, best_cov = res, cov
    return best


def score(cluster, cohesion, graph, by):
    """Everything a person needs to decide whether this is worth naming."""
    # Sorted, not set order. A frozenset iterates in hash order, which varies per
    # process, so two naming pages tied on reach handed the title to whichever came
    # first that run — the output changed between runs of the same corpus. For a tool
    # whose whole claim is reproducibility that is the worst possible defect, and the
    # wrapped `diff` called the files identical while five md5s disagreed.
    members = [by[s] for s in sorted(cluster)]
    sources = {src for m in members for src in (m.get("sources") or [])}
    origins = collections.Counter(m.get("origin") for m in members)

    # The naming page is searched across the WHOLE corpus, not only inside the cluster.
    # Until 2026-09-15 it was looked for among the members, which reported eleven clusters
    # as unnamed when the corpus had named most of them: these clusters are built largely
    # out of source summaries, and the concept page that names the idea sits one hop away,
    # outside the group. "Nobody has said what this is" was the headline claim of the whole
    # tool and it was wrong for two clusters in three.
    #
    # A hub is not a name. `Civilizational Optionality` carries 169 inbound links and brushes
    # most clusters in the corpus, so reach alone would hand it the title everywhere. A
    # candidate must therefore also be SPECIFIC: at least a fifth of its own neighbourhood
    # has to lie inside the cluster. Ties are broken by specificity, then by title, so the
    # answer does not depend on iteration order.
    best, touched, best_spec = None, 0, 0.0
    cl = set(cluster)
    for m in sorted(by.values(), key=lambda x: x.get("title") or x["slug"]):
        if m.get("type") not in NAMING_TYPES:
            continue
        near = set(m.get("outbound_links") or []) | set(m.get("inbound_links") or [])
        if not near:
            continue
        reach = len(near & cl)
        if not reach:
            continue
        spec = reach / len(near)
        if spec < NAMING_SPECIFICITY and m["slug"] not in cl:
            continue
        if (reach, spec) > (touched, best_spec):
            best, touched, best_spec = m, reach, spec

    # Ties in `most_common` are broken by insertion order, which follows set iteration
    # and so follows PYTHONHASHSEED: the CLUSTERS were stable run to run but the tags
    # naming them were not, which is the half a reader actually recognises. Sort the
    # ties by name so the same cluster is described the same way every time.
    tags = collections.Counter(t for m in members for t in (m.get("tags") or []))
    ranked = [t for t, _ in sorted(tags.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {
        "pages": len(cluster),
        "cohesion": round(cohesion, 3),
        "density": round(_c.density(graph, cluster), 3),
        "distinct_sources": len(sources),
        "wikis": dict(sorted(origins.items(), key=lambda kv: (-kv[1], kv[0]))),
        "travels": len(origins) > 1,           # Strata's test: does it cross contexts?
        "naming_page": best.get("title") if best else None,
        "naming_coverage": round(touched / len(cluster), 3),
        "naming_is_a_member": bool(best and best["slug"] in cl),
        "naming_specificity": round(best_spec, 3),
        "tags": ranked[:6],
        "members": sorted(m.get("title") or m["slug"] for m in members),
        "member_slugs": sorted(m["slug"] for m in members),
    }


def gather(federation=False, include_private=False, resolution=None, agreement=0.9):
    nodes, prov = load_nodes(federation, include_private)
    graph, by = build_graph(nodes)
    chosen = resolution if resolution is not None else choose_resolution(graph, agreement)
    rows = [score(c, coh, graph, by) for c, coh in consensus(graph, chosen, agreement)]
    # Unnamed first, then independent, then cohesive. A cluster with a page already
    # covering half of it is integrated — it is not what was asked for.
    # A total order, ending on the member list: two clusters tied on every score
    # would otherwise swap places between runs and the output would still differ.
    rows.sort(key=lambda r: (r["naming_coverage"], -r["distinct_sources"],
                             -r["cohesion"], r["members"]))
    return {
        "corpus": prov,
        "settings": {"seeds": len(SEEDS), "resolution": chosen, "agreement": agreement,
                     "resolution_chosen_automatically": resolution is None},
        "graph": {"pages": len(graph),
                  "links": sum(len(v) for v in graph.values()) // 2},
        "candidates": rows,
    }


def render(m) -> str:
    out, c = [], m["corpus"]
    out.append(f"emerging patterns — {c['local']['wiki']}")
    out.append(f"  {m['graph']['pages']} pages · {m['graph']['links']} links · "
               f"consensus over {m['settings']['seeds']} runs at "
               f"{m['settings']['agreement']:.0%} agreement")
    out.append(f"  resolution {m['settings']['resolution']}"
               + (" (chosen for this corpus)" if m["settings"]
                  ["resolution_chosen_automatically"] else " (set by hand)"))
    if c["excluded"]:
        out.append("  excluded: " + ", ".join(f"{v} {k}" for k, v in c["excluded"].items()))
    if c["included_private"]:
        out.append("  !! PRIVATE PAGES INCLUDED — this output is not shareable")
    out.append("")

    unnamed = [r for r in m["candidates"] if r["naming_coverage"] < 0.5]
    out.append(f"  {len(unnamed)} cluster(s) with no page naming them, of "
               f"{len(m['candidates'])} stable clusters")
    out.append("")
    for r in unnamed[:12]:
        travels = f" · spans {len(r['wikis'])} wikis" if r["travels"] else ""
        out.append(f"  [{r['pages']} pages] {', '.join(r['tags'][:4])}{travels}")
        out.append(f"     cohesion {r['cohesion']:.2f} · density {r['density']:.2f} · "
                   f"{r['distinct_sources']} distinct sources")
        if r["naming_page"]:
            out.append(f"     nearest naming page: {r['naming_page'][:64]} "
                       f"(touches {r['naming_coverage']:.0%})")
        else:
            out.append("     nearest naming page: none — nothing here names the group")
        for t in r["members"][:4]:
            out.append(f"       · {t[:68]}")
        if len(r["members"]) > 4:
            out.append(f"       · … and {len(r['members']) - 4} more")
        out.append("")

    if c["commons"]:
        out.append("  federation reach:")
        for name, d in c["commons"].items():
            if "error" in d:
                out.append(f"     {name}: {d['error']}")
                continue
            og = ", ".join(f"{v} from {k}" for k, v in
                           sorted(d["origins"].items(), key=lambda kv: -kv[1])[:4])
            out.append(f"     {name}: {d['pages_in_cut']} pages — {og}")
            out.append(f"       read {d['read']}; skipped {d['skipped_our_own']} that "
                       f"came from here (our own material returning is not another context)")
        out.append("")

    out.append("  These are candidates, not patterns. A cluster is evidence that the corpus")
    out.append("  keeps putting these pages together; what it MEANS is a person's call, and")
    out.append("  naming one is how it stops being emergent.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Clusters the corpus formed and nobody named.")
    ap.add_argument("--federation", action="store_true",
                    help="also read the commons cuts cached in .commons/")
    ap.add_argument("--include-private", action="store_true",
                    help="owner's local reading only; output is stamped unshareable")
    ap.add_argument("--resolution", type=float, default=None,
                    help="higher splits finer; default picks the value that finds the "
                         "most idea-sized clusters in THIS corpus")
    ap.add_argument("--agreement", type=float, default=0.9,
                    help="fraction of runs two pages must share a cluster in (0..1)")
    ap.add_argument("--json", action="store_true", help="emit the material as JSON")
    a = ap.parse_args(argv)
    if not 0 < a.agreement <= 1:
        print(f"--agreement must be in (0, 1], got {a.agreement}", file=sys.stderr)
        return 2
    m = gather(a.federation, a.include_private, a.resolution, a.agreement)
    print(json.dumps(m, indent=2) if a.json else render(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
