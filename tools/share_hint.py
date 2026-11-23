#!/usr/bin/env python3
"""
share_hint.py: which shared wiki a page belongs in, said once, to its owner only.

Asked for by Gurden on 23 November 2026, after the federation map showed how much good work stays private
(Robyn: "gives a clear sense of where people need particular nudging"). The nudge belongs to the person,
at the moment it is useful, never to a league table: nothing here ranks or counts people.

For each page it reads the shared wikis this wiki contributes to, from the cached shared copies in
.commons/<name>/export/wiki.shared.json, and scores how much the page is about each one:

  * a link to a page that shared wiki holds (by title), 3 points each;
  * a tag that shared wiki uses on at least two of its pages, 1 point each.

A page has a home when it links to at least one page that shared wiki holds and scores 4 or more, or links
to two of them. Tags alone never make a home: on 23 November, words like "challenge" pointed a whole series
of pages at the xCO wiki on tags only. What the person is told depends on the page's tier:

  share       internal, unlisted or public, and not yet there: "share it with <wiki>?"
  open first  private: "this looks like <wiki> material; it is private, so it stays here unless you
              mark it for colleagues first". Opening a page is a disclosure decision and the owner's;
              this only points at it.
  none        no home, already there, CRM, or the shared copy is not cached here (said, never guessed).

  python3 tools/share_hint.py SLUG [SLUG ...]        # one line per page
  python3 tools/share_hint.py --json SLUG ...
  python3 tools/share_hint.py --changed-since 7      # the pages whose body changed in the last 7 days

Reads only. Prints page titles from this wiki and names of shared wikis; nothing leaves the machine.
"""

import argparse
import collections
import datetime as dt
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contribute  # noqa: E402
import export  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, "wiki")
LINK_POINTS, TAG_POINTS, ENOUGH = 3, 1, 4
GENERIC_TAGS = {"source-summary", "summary", "concept", "entity", "synthesis", "meeting-notes", "call-notes",
                "draft", "overview", "map", "log", "digest", "d-ino", "xco", "dm", "dark-matter-labs"}


def commons_profile(name):
    """{titles, tags} for one shared wiki from its cached shared copy, or None if not cached here."""
    for path in contribute.commons_cache_paths(name):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            nodes = d.get("nodes", {})
            nodes = list(nodes.values()) if isinstance(nodes, dict) else nodes
            titles = {n["title"].strip().lower() for n in nodes if isinstance(n.get("title"), str)}
            counts = collections.Counter(t.lower() for n in nodes for t in (n.get("tags") or []) if isinstance(t, str))
            tags = {t for t, c in counts.items() if c >= 2 and t not in GENERIC_TAGS}
            return {"titles": titles, "tags": tags}
    return None


def score(page, profile):
    """(points, reasons) for how much `page` is about the shared wiki described by `profile`."""
    links = {str(x).strip().lower() for x in (page.get("outbound_links") or [])}
    hit_links = sorted(links & profile["titles"])
    hit_tags = sorted(({str(t).lower() for t in (page.get("tags") or [])} & profile["tags"]) - GENERIC_TAGS)
    points = LINK_POINTS * len(hit_links) + TAG_POINTS * len(hit_tags)
    reasons = [f"links to {len(hit_links)} of its pages"] if hit_links else []
    if hit_tags:
        reasons.append("shares the tags " + ", ".join(hit_tags[:3]))
    return points, reasons, len(hit_links)


def hint(slug, page, targets, profiles):
    """One verdict for one page: {slug, title, kind: share|open first|none, commons, why}."""
    title = page.get("title") or slug
    base = {"slug": slug, "title": title, "kind": "none", "commons": None, "why": ""}
    if any(slug.startswith(p) for p in contribute.REFUSE_PATH_PREFIXES):
        return {**base, "why": "contact cards never go to a shared wiki"}
    best = None
    for name in targets:
        prof = profiles.get(name)
        if prof is None:
            continue
        if title.strip().lower() in prof["titles"]:
            return {**base, "why": f"already in {name}"}
        pts, reasons, nlinks = score(page, prof)
        if (nlinks >= 2 or (nlinks >= 1 and pts >= ENOUGH)) and (best is None or pts > best[0]):
            best = (pts, name, reasons)
    if best is None:
        unknown = [n for n in targets if profiles.get(n) is None]
        why = ("no shared copy cached here for " + ", ".join(unknown) + "; run python3 tools/sync_commons.py") if unknown else "no clear home"
        return {**base, "why": why}
    vis = page.get("visibility", "private")
    kind = "share" if vis in contribute.CONTRIBUTABLE else "open first"
    return {**base, "kind": kind, "commons": best[1], "why": "; ".join(best[2])}


def changed_since(days):
    """Slugs of pages whose file changed in the last `days` days (from git)."""
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    out = subprocess.run(["git", "-C", ROOT, "log", f"--since={since}", "--name-only", "--format=", "--", "wiki"],
                         capture_output=True, text=True).stdout
    slugs = []
    for line in out.splitlines():
        if line.endswith(".md") and line.startswith("wiki/"):
            s = line[len("wiki/"):-3]
            if s not in slugs:
                slugs.append(s)
    return slugs


def hints(slugs, nodes=None, topo=None):
    topo = topo or contribute.topology()
    targets = list(topo.get("contributes_to") or [])
    if nodes is None:
        result = export.build_nodes(WIKI)
        nodes = result[0] if isinstance(result, tuple) else result
    profiles = {n: commons_profile(n) for n in targets}
    return [hint(s, nodes[s], targets, profiles) for s in slugs if s in nodes]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Which shared wiki a page belongs in.")
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--changed-since", type=int, metavar="DAYS")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    slugs = a.slugs or (changed_since(a.changed_since) if a.changed_since else [])
    if not slugs:
        ap.error("name pages, or use --changed-since DAYS")
    out = hints(slugs)
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    for h in out:
        if h["kind"] == "share":
            print(f"share       {h['title']} -> {h['commons']} ({h['why']})")
        elif h["kind"] == "open first":
            print(f"open first  {h['title']} -> {h['commons']} ({h['why']}); it is private, so only if you mark it for colleagues")
        else:
            print(f"none        {h['title']} ({h['why']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
