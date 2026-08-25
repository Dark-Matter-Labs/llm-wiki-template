#!/usr/bin/env python3
"""
measure_scale.py — the meter that decides when plain text stops being enough.

Build Spec v2's P2. The strategy for scaling is agreed; the point of this tool is that the
*move* between stages is triggered by a measurement rather than a worry. Run it monthly,
record the line in the log, and build Stage B only when a tripwire actually fires.

A note on honesty, because two of the metrics the spec first named turned out not to be
measurable from where it claimed:

  * "pages read per query, from log entries" — the log records that a query happened, not
    how many pages it took. Measuring that needs session instrumentation nobody has built.
    The substitute here is **search discrimination**: run a fixed probe set through the
    keyword search and see how many pages score close to the top. When a typical question
    stops separating a handful of pages from the rest, routing has degraded — which is the
    thing "pages read per query" was a proxy for anyway, and this one is computable.
  * "cascade miss rate, from lint findings" — lint is a model-driven skill; its findings
    are prose, not a series. The computable neighbour is **routing gaps**: pages you cannot
    reach from the index. Note this measures REACHABILITY, not direct listing — the index
    is a router, and large sets are deliberately routed through a hub page. Counting those
    as gaps fires a tripwire on a design decision; the first version of this tool did
    exactly that and reported a 39.6% failure that was really one deliberate choice.

Everything reported here is measured. Nothing is estimated.

Usage:
  python3 tools/measure_scale.py              # the reading
  python3 tools/measure_scale.py --log        # append one line to the current month's log
  python3 tools/measure_scale.py --json
"""

import argparse
import datetime
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export   # noqa: E402
import search   # noqa: E402

# Tripwires. Crossing one is a prompt to look, not an instruction to build.
#
# The router tripwire counts TOKENS, not lines, and that correction was paid for. Until
# 2026-08-25 it read `index.md is > 1500 lines`. At its worst the index was **523 lines
# and 221,676 characters** — about 55,000 tokens, read before every single operation
# against a corpus whose median page is under 1,000. The meter read "523, fine." The rows
# had grown, not multiplied, and a line count cannot see that. A tripwire that cannot fire
# on the failure it exists to catch is worse than no tripwire: it issues assurance.
T_ROUTER_TOKENS = 15000   # what routing costs before the first useful token is read
T_ROUTING_GAP = 0.05      # >5% of pages missing from the index = the cascade is slipping
T_DISCRIM = 25            # a typical query no longer separates a handful from the rest
T_ORPHANS = 0.15          # >15% unreachable by link = the graph is not doing its job

# A fixed probe set. Fixed is the point: the same questions every month, so the number
# means something across readings. Drawn from the corpus's actual subject matter.
PROBES = [
    "cascading risk and tipping points",
    "outcome based financing for a place",
    "how is optionality preserved",
    "capital formation architecture",
    "governance of a shared commons",
    "what does validation mean here",
    "bioregional stewardship",
    "liability and insurance pricing",
]


def measure(wiki_dir="wiki"):
    m = {"date": datetime.date.today().isoformat()}

    pages = list(export.discover(wiki_dir))
    m["pages"] = len(pages)

    words = [len(re.findall(r"\S+", body)) for _s, _p, _fm, body in pages]
    m["words_total"] = sum(words)
    m["words_median"] = int(statistics.median(words)) if words else 0

    # --- routing -----------------------------------------------------------
    # The router is what every operation pays for; the shelves are opt-in. So the COST
    # metric reads the router alone, and the COVERAGE metric reads router + shelves —
    # they are one catalogue for "is this page listed?" and two different things for
    # "what does routing cost?". Conflating them is how `sync_index_counts.py` went blind
    # to 356 pages the day the index was tiered.
    index_path = os.path.join(wiki_dir, "index.md")
    router_text = open(index_path, encoding="utf-8").read() if os.path.exists(index_path) else ""
    m["index_lines"] = router_text.count("\n") + 1 if router_text else 0
    m["router_tokens"] = len(router_text) // 4

    shelf_dir = os.path.join(wiki_dir, "index")
    shelves = sorted(f for f in os.listdir(shelf_dir) if f.endswith(".md")) \
        if os.path.isdir(shelf_dir) else []
    index_text = "\n".join([router_text] + [
        open(os.path.join(shelf_dir, f), encoding="utf-8").read() for f in shelves])
    m["shelves"] = len(shelves)

    titles = {fm.get("title") for _s, _p, fm, _b in pages if isinstance(fm.get("title"), str)}
    listed = {t.strip() for t in re.findall(r"\[\[([^\]|#]+)", index_text)}

    # Reachability, not direct listing. The index is a ROUTER: large sets are
    # deliberately routed through a hub page (the 257 Substack summaries hang off one
    # hub, and the index says so) precisely to keep the router skimmable. Counting
    # those as gaps fires a tripwire on a design decision — so a page counts as
    # reachable if the index links it, or if any page the index links reaches it.
    nodes_r, _t2s_r = export.build_nodes(wiki_dir)
    title_of = {s: n.get("title") for s, n in nodes_r.items()}

    # A catalogue may link by wiki-link OR by ordinary markdown path — the template wikis
    # ship an index written entirely as `[Overview](overview.md)`. Reading only `[[...]]`
    # reported 100% of their pages unlisted, which is a false alarm about a file format,
    # not a finding about routing. Both forms are links; count both.
    for href in re.findall(r"\]\(([^)]+?\.md)\)", index_text):
        slug = href.split("/")[-1][:-3]
        if slug in title_of and isinstance(title_of[slug], str):
            listed.add(title_of[slug])

    reachable = set(listed)
    for s, n in nodes_r.items():
        if title_of.get(s) in listed:
            for tgt in n.get("outbound_links", []):
                t = title_of.get(tgt) if tgt in nodes_r else tgt
                if isinstance(t, str):
                    reachable.add(t)
    missing = {t for t in titles if t and t not in reachable}
    m["routing_gaps"] = len(missing)
    m["routing_gap_rate"] = round(len(missing) / max(1, len(titles)), 3)
    m["_missing_sample"] = sorted(missing)[:5]

    # --- graph -------------------------------------------------------------
    nodes = nodes_r          # already built above; 713 pages is not worth doing twice
    orphans = [s for s, n in nodes.items() if not n.get("inbound_links")]
    m["orphans"] = len(orphans)
    m["orphan_rate"] = round(len(orphans) / max(1, len(nodes)), 3)
    out_counts = [len(n.get("outbound_links", [])) for n in nodes.values()]
    m["links_mean_out"] = round(sum(out_counts) / max(1, len(out_counts)), 1)

    # --- search discrimination ---------------------------------------------
    # For each probe: how many pages score within 60% of the top hit? A small number
    # means the search still separates; a large one means everything looks relevant.
    sp = search.read_pages()
    near = []
    for q in PROBES:
        res = search.score(sp, q)
        if not res:
            near.append(0); continue
        top = res[0][0] if isinstance(res[0], tuple) else None
        if top is None or not top:
            near.append(len(res)); continue
        near.append(sum(1 for r in res if (r[0] if isinstance(r, tuple) else 0) >= 0.6 * top))
    m["discrimination_mean"] = round(sum(near) / max(1, len(near)), 1)
    m["discrimination_max"] = max(near) if near else 0

    return m


def verdict(m):
    """Which tripwires have fired, with the number that fired them."""
    fired = []
    if m["router_tokens"] > T_ROUTER_TOKENS:
        fired.append(f"routing costs ~{m['router_tokens']:,} tokens before the first "
                     f"useful one (> {T_ROUTER_TOKENS:,})")
    if m["routing_gap_rate"] > T_ROUTING_GAP:
        fired.append(f"{m['routing_gaps']} pages missing from the index "
                     f"({m['routing_gap_rate']:.1%} > {T_ROUTING_GAP:.0%})")
    if m["discrimination_mean"] > T_DISCRIM:
        fired.append(f"a typical query returns {m['discrimination_mean']} near-top pages "
                     f"(> {T_DISCRIM})")
    if m["orphan_rate"] > T_ORPHANS:
        fired.append(f"{m['orphans']} orphan pages ({m['orphan_rate']:.1%} > {T_ORPHANS:.0%})")
    return fired


def main(argv=None):
    ap = argparse.ArgumentParser(description="Measure whether the corpus has outgrown plain text.")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--log", action="store_true", help="append a reading to the current month's log")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.wiki):
        print(f"error: no {args.wiki!r} directory (cwd is {os.getcwd()}).\n"
              f"       Run from the repo root.", file=sys.stderr)
        return 2

    m = measure(args.wiki)
    fired = verdict(m)

    if args.json:
        print(json.dumps({**m, "tripwires_fired": fired}, indent=1))
        return 0

    print(f"scale reading — {m['date']}\n")
    print(f"  corpus          {m['pages']} pages, {m['words_total']:,} words "
          f"(median page {m['words_median']})")
    print(f"  routing cost    ~{m['router_tokens']:,} tokens "
          f"({m['index_lines']} router lines + {m['shelves']} shelves)"
          f"   (tripwire > {T_ROUTER_TOKENS:,})")
    print(f"  routing gaps    {m['routing_gaps']} pages unlisted "
          f"({m['routing_gap_rate']:.1%})   (tripwire > {T_ROUTING_GAP:.0%})")
    if m["_missing_sample"]:
        print(f"                  e.g. {', '.join(m['_missing_sample'][:3])}")
    print(f"  discrimination  {m['discrimination_mean']} near-top pages per query, "
          f"max {m['discrimination_max']}   (tripwire > {T_DISCRIM})")
    print(f"  graph           {m['orphans']} orphans ({m['orphan_rate']:.1%}), "
          f"{m['links_mean_out']} outbound links/page   (tripwire > {T_ORPHANS:.0%})")
    print()
    if fired:
        print(f"TRIPWIRE FIRED ({len(fired)}) — look at Stage B in Build Spec v2:")
        for f in fired:
            print(f"  - {f}")
        print("\n  Firing is a prompt to look, not an instruction to build.")
    else:
        print("  No tripwire fired. Stage A is still adequate — build nothing.")

    if args.log:
        line = (f"\n## [{m['date']}] measure | scale reading\n\n"
                f"{m['pages']} pages / {m['words_total']:,} words · index {m['index_lines']} lines · "
                f"routing gaps {m['routing_gaps']} ({m['routing_gap_rate']:.1%}) · "
                f"discrimination {m['discrimination_mean']} · "
                f"orphans {m['orphans']} ({m['orphan_rate']:.1%}). "
                + ("Tripwires fired: " + "; ".join(fired) + "."
                   if fired else "No tripwire fired; Stage A adequate.") + "\n")
        month = os.path.join(args.wiki, "log", m["date"][:7] + ".md")
        if not os.path.exists(month):
            print(f"\nerror: no log file for this month ({month}).", file=sys.stderr)
            return 2
        with open(month, "a", encoding="utf-8") as fh:
            fh.write(line)
        print(f"\n  appended a reading to {month}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
