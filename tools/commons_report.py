#!/usr/bin/env python3
"""
commons_report.py — say what the commons holds, from this spoke's cached copy.

The down flow of the federation is **reference, not copy**. The sync workflow drops the
commons' export graph into `.commons/` (gitignored), and this reports what is there so a
session can tell at a glance what the shared canon covers without cloning it into `wiki/`.

Two authoritative copies of a page drifting apart is the failure that kills federated
systems. Nothing here writes to `wiki/`, and nothing should.

Usage:
  python3 tools/commons_report.py
  python3 tools/commons_report.py --overlap    # what this spoke and the commons both cover
"""

import argparse
import collections
import json
import os
import sys

# Prefer the SHARED cut. `internal` is the commons' default tier and exists precisely
# for team members reading from their own spokes; the public cut hides it, which showed
# a spoke less than half the shared canon without saying so. Fall back to the public cut
# if a commons has not published a shared one yet — fewer pages is a degraded read, not
# a broken one.
# A spoke may contribute to more than one commons, so the cache is per-commons:
# .commons/<name>/export/. The flat .commons/export is the pre-2026-08-21 layout and is
# still read as a fallback, because a cache written by an older sync is a degraded read
# rather than a broken one.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contribute  # noqa: E402


def declared_commons():
    """The commons this wiki reads, from design/federation.json."""
    return list(contribute.topology().get("contributes_to") or [])


def cache_dirs(name):
    return [os.path.join(".commons", name, "export"), os.path.join(".commons", "export")]


def load_commons(name):
    """(nodes, which_cut, which_dir) — or (None, None, None) if there is no cache."""
    for d in cache_dirs(name):
        for cut in ("wiki.shared.json", "wiki.public.json"):
            path = os.path.join(d, cut)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                nodes = data.get("nodes", {})
                nodes = list(nodes.values()) if isinstance(nodes, dict) else nodes
                return nodes, cut, d
    return None, None, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="What the commons holds, from the local cache.")
    ap.add_argument("--overlap", action="store_true",
                    help="titles this spoke and the commons both have")
    args = ap.parse_args(argv)

    targets = declared_commons()
    if not targets:
        print("This wiki contributes to no commons (design/federation.json lists none).")
        return 0

    missing = [t for t in targets if load_commons(t)[0] is None]
    if len(missing) == len(targets):
        print(f"No commons cache for {', '.join(targets)}. Run the 'Sync the commons'\n"
              "workflow, or work without it — this spoke does not depend on the commons\n"
              "to function.")
        return 0
    for t in missing:
        print(f"note: no cache for {t} — it is declared but has not been synced.\n")

    for name in targets:
        nodes, cut, _d = load_commons(name)
        if nodes is None:
            continue
        if len(targets) > 1:
            print(f"=== {name} ===")
        report_one(nodes, cut, args)
    return 0


def report_one(nodes, cut, args):
    print(f"commons: {len(nodes)} pages readable from this spoke  [{cut}]")
    if cut == "wiki.public.json":
        print("  note: reading the PUBLIC cut — the commons has not published a shared\n"
              "  one, so anything marked `internal` there is invisible here.\n")
    else:
        print()
    by_type = collections.Counter(n.get("type") or "untyped" for n in nodes)
    for t, c in by_type.most_common():
        print(f"  {c:>4}  {t}")

    if args.overlap:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import export  # noqa: E402
        mine = {fm.get("title") for _s, _p, fm, _b in export.discover("wiki")
                if isinstance(fm.get("title"), str)}
        theirs = {n.get("title") for n in nodes if isinstance(n.get("title"), str)}
        both = sorted(mine & theirs)
        print(f"\n  {len(both)} title(s) exist in BOTH this spoke and the commons.")
        if both:
            print("  That is the two-canons risk. For each: reference the commons copy and")
            print("  delete the local one, or declare a contradiction if you genuinely disagree.")
            for t in both[:15]:
                print(f"    {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
