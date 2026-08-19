#!/usr/bin/env python3
"""
contribution_prompt.py — what this wiki could contribute to its commons, and has not.

The federation was built with an asymmetry nobody decided: the down-flow got a daily
cron, and the up-flow got three consent gates and no cadence at all. Consent gates are
right — which pages reach a shared corpus is a person's decision — but a decision nobody
is ever asked to make is not consent, it is just silence. On 19 Aug 2026 the commons held
exactly one contributed page while a spoke sat on nine eligible ones, purely because
nothing ever put the question in front of anyone.

So this asks. It **names candidates and stops**: no staging, no bundle, no PR, no write of
any kind. `contribute.py` remains the only path up, with all of its refusals intact.

Safety comes from reuse, not from re-implementation
---------------------------------------------------
Eligibility is `contribute.eligible()` itself, not a second copy of its rules. That matters
more than the tidiness: a private page must never be named — not its body, not its title,
not its slug — and a second implementation of that rule is a second thing that can drift
out of step with the first. Collision state comes from the same cached commons export that
`contribute.py` reads, and when there is no cache this says "unverified" rather than
quietly implying no clash.

Ranking is by inbound links, as a proxy for how load-bearing a page is *here*. It is a
weak proxy and deliberately so: a strong one would amount to the tool deciding what is
worth sharing, which is exactly the judgment being handed to a person.

Usage:
  python3 tools/contribution_prompt.py                  # human-readable
  python3 tools/contribution_prompt.py --markdown       # for the weekly reflection
  python3 tools/contribution_prompt.py --top 5
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import contribute  # noqa: E402
import export  # noqa: E402

WIKI = os.path.join(HERE, "..", "wiki")


def targets(topo):
    """The commons this wiki contributes to. A commons that feeds none returns []."""
    return list(topo.get("contributes_to") or [])


def candidates(pages, already, top=None):
    """Eligible pages the commons does not already hold, most-linked first.

    `pages`  — {slug: {"title", "visibility", "inbound"}}
    `already`— set of titles the commons holds, or None when that cannot be checked.
    """
    unknown = already is None
    held = set() if unknown else already
    out = []
    for slug, p in pages.items():
        ok, _why = contribute.eligible(slug, {"visibility": p.get("visibility")})
        if not ok:
            continue
        if p.get("title") in held:
            continue
        out.append({"slug": slug, "title": p.get("title"),
                    "visibility": p.get("visibility"),
                    "inbound": p.get("inbound", 0),
                    "collision_unknown": unknown})
    out.sort(key=lambda c: (-c["inbound"], c["slug"]))
    return out[:top] if top else out


def read_wiki(wiki_dir):
    """{slug: {title, visibility, inbound}} from the wiki on disk."""
    # build_nodes returns (nodes, _), not a bare dict. Unpacking it wrongly is not a
    # theoretical risk: the unit tests below pass a page dict directly and never cross
    # this seam, so the first real run was the first thing to catch it.
    result = export.build_nodes(wiki_dir)
    nodes = result[0] if isinstance(result, tuple) else result
    pages = {}
    for slug, n in nodes.items():
        pages[slug] = {"title": n.get("title") or slug,
                       "visibility": n.get("visibility", "private"),
                       "inbound": len(n.get("inbound_links") or [])}
    return pages


def report(top=3, markdown=False):
    topo = contribute.topology()
    tgts = targets(topo)
    lines = []
    if not tgts:
        # A commons that contributes nowhere is not behind on anything.
        return lines, 0

    pages = read_wiki(WIKI)
    total = 0
    for name in tgts:
        already = contribute.commons_titles(name)
        cands = candidates(pages, already, top=top)
        allc = candidates(pages, already)
        total += len(allc)
        # Without a cached export there is no way to tell which of these the commons
        # already holds. How wrong a guess would be depends on the spoke: one seeded
        # from the commons overlaps almost entirely, one with original content barely
        # at all (Robyn's first ingest: 9 eligible, 8 genuinely new). So the unverified
        # branch guesses at neither — it reports the eligible count and says the
        # overlap check could not run.
        if already is None:
            head = (f"- **{name}** — cannot tell what it already holds: this wiki has no "
                    f"cached export of it, so the overlap check could not run. "
                    f"{len(allc)} page(s) are eligible here; how many are new to the "
                    f"commons is unknown."
                    if markdown else
                    f"  {name}: overlap UNKNOWN — no cached export, so the check could "
                    f"not run\n    {len(allc)} eligible here; how many are new to the "
                    f"commons is unknown")
            lines.append(head)
            continue

        if not allc:
            lines.append(f"- **{name}** — nothing eligible that it does not already hold."
                         if markdown else
                         f"  {name}: nothing eligible that it does not already hold")
            continue

        if markdown:
            lines.append(f"- **{name}** — {len(allc)} eligible page(s) it does not "
                         f"hold. Most-linked here:")
            for c in cands:
                lines.append(f"    - `{c['slug']}` — {c['inbound']} inbound "
                             f"link(s), `{c['visibility']}`")
            lines.append("    - Nothing has moved. `contribute.py` is still the only "
                         "way up, and it stages for a human to review.")
        else:
            lines.append(f"  {name}: {len(allc)} eligible, not held there")
            for c in cands:
                lines.append(f"      {c['inbound']:>3} inbound  {c['slug']}  "
                             f"[{c['visibility']}]")
    return lines, total


def main(argv=None):
    ap = argparse.ArgumentParser(description="What this wiki could contribute upward.")
    ap.add_argument("--top", type=int, default=3, help="how many to name per commons")
    ap.add_argument("--markdown", action="store_true", help="for the weekly reflection")
    args = ap.parse_args(argv)

    lines, total = report(top=args.top, markdown=args.markdown)
    if not lines:
        print("  this wiki contributes to no commons — nothing to prompt."
              if not args.markdown else
              "_This wiki contributes to no commons, so there is nothing to prompt._")
        return 0
    if not args.markdown:
        print("contribution prompt — named, not moved\n")
    print("\n".join(lines))
    if not args.markdown:
        print(f"\n  {total} eligible page(s) in total. Nothing has been staged or moved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
