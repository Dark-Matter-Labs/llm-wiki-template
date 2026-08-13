#!/usr/bin/env python3
"""
goals.py — the goal and commitment view, computed from the corpus.

Build Spec v2's P4. Two rules shape everything here:

**The wiki is the source of truth.** This tool only reads. It never writes to `wiki/`,
and there is no code path that does — a change to a goal or a commitment is an edit to
its page, proposed as a PR like everything else. The view is a lens, not a database.

**Progress is computed, never typed.** Nobody sets a percentage. Movement is inferred
from three signals the corpus already carries:

  * **attachment** — how many pages link to the goal (is anyone actually working near it?)
  * **commitment** — what has been committed against it, and in what state
  * **recency** — when the goal or anything committed to it last changed

A goal with commitments held against it and recent movement is live. A goal nobody has
linked to in months, with nothing committed, is stalled — and saying so is information,
not an accusation.

On `declined` and `exited`: both are **non-penalised closures**. Refusing a commitment,
or leaving one deliberately, is a valid outcome. Only `lapsed` — fell over without a
decision — counts against a goal's health. A ledger that renders a refusal as a failure
teaches people not to answer, which destroys the data it exists to collect.

Usage:
  python3 tools/goals.py                 # the view
  python3 tools/goals.py --json          # machine-readable, for the web view
  python3 tools/goals.py --stalled       # only what needs attention
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402

STALE_DAYS = 60          # no movement for this long and a live goal reads as stalled
NON_FAILURE = export.NON_FAILURE_CLOSED
OPEN_STATES = {"proposed", "held", "revised"}


def _days_since(iso):
    if not iso:
        return None
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def _last_touched(slug, wiki_dir):
    """Last commit date for the page — real movement, not the frontmatter's claim."""
    r = subprocess.run(["git", "log", "-1", "--format=%cs", "--",
                        os.path.join(wiki_dir, slug + ".md")],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def build(wiki_dir="wiki", use_git=True):
    nodes, title_to_slug = export.build_nodes(wiki_dir)

    goals = {s: n for s, n in nodes.items() if n.get("type") == "goal"}
    commitments = {s: n for s, n in nodes.items() if n.get("type") == "commitment"}

    view = {"generated": datetime.date.today().isoformat(),
            "goals": [], "orphan_commitments": [], "counts": {}}

    for slug, g in sorted(goals.items(), key=lambda kv: kv[1].get("title") or kv[0]):
        title = g.get("title")

        mine = [c for c in commitments.values() if c.get("commits_to") == title]
        by_state = {}
        for c in mine:
            by_state.setdefault(c.get("state") or "unstated", []).append(c)

        # attachment: pages pointing at the goal that are not its own commitments
        commit_slugs = {c["slug"] for c in mine}
        attached = [t for t in g.get("inbound_links", []) if t not in commit_slugs]

        # recency: the most recent movement on the goal OR anything committed to it
        dates = []
        for n in [g] + mine:
            d = _last_touched(n["slug"], wiki_dir) if use_git else n.get("timestamp")
            if d:
                dates.append(d)
        last = max(dates) if dates else None
        age = _days_since(last)

        open_n = sum(len(v) for k, v in by_state.items() if k in OPEN_STATES)
        lapsed_n = len(by_state.get("lapsed", []))
        closed_ok = sum(len(by_state.get(k, [])) for k in NON_FAILURE)

        # Health is a reading, not a score. Three states, each meaning one thing.
        if lapsed_n:
            health = "attention"
            why = f"{lapsed_n} commitment(s) lapsed — fell over without a decision"
        elif not mine:
            health = "unbacked"
            why = "no commitments — a goal nobody has committed resources to"
        elif age is not None and age > STALE_DAYS and open_n:
            health = "stalled"
            why = f"{open_n} open commitment(s), nothing has moved in {age} days"
        elif open_n:
            health = "live"
            why = f"{open_n} open commitment(s), last movement {age} days ago"
        else:
            health = "closed"
            why = f"all {closed_ok} commitment(s) closed without failure"

        view["goals"].append({
            "slug": slug, "title": title,
            "horizon": g.get("horizon"), "parent": g.get("parent"),
            "visibility": g.get("visibility"), "validation": g.get("validation"),
            "health": health, "why": why,
            "last_movement": last, "days_since": age,
            "attached_pages": len(attached),
            "commitments": {k: [{"title": c.get("title"), "slug": c["slug"],
                                 "resources": c.get("resources"), "until": c.get("until"),
                                 "visibility": c.get("visibility")}
                                for c in v] for k, v in sorted(by_state.items())},
            "counts": {"open": open_n, "lapsed": lapsed_n, "closed_ok": closed_ok},
        })

    # A commitment pointing at a goal that does not exist is a real error: somebody has
    # committed resources to something the corpus cannot name.
    goal_titles = {g.get("title") for g in goals.values()}
    for slug, c in sorted(commitments.items()):
        if c.get("commits_to") not in goal_titles:
            view["orphan_commitments"].append(
                {"slug": slug, "title": c.get("title"), "commits_to": c.get("commits_to")})

    view["counts"] = {
        "goals": len(goals), "commitments": len(commitments),
        "orphan_commitments": len(view["orphan_commitments"]),
        "unbacked": sum(1 for g in view["goals"] if g["health"] == "unbacked"),
        "stalled": sum(1 for g in view["goals"] if g["health"] == "stalled"),
        "attention": sum(1 for g in view["goals"] if g["health"] == "attention"),
    }
    return view


def render(v, only_stalled=False):
    out = []
    c = v["counts"]
    out.append(f"goals & commitments — {v['generated']}\n")
    if not c["goals"]:
        out.append("  No goals defined yet.\n")
        out.append("  A goal is a page with `type: goal`. A commitment is a page with")
        out.append("  `type: commitment`, `commits_to: \"<goal title>\"`, `resources:`, `until:`")
        out.append("  and a `state:`. Both are explicit and formal — they carry a contractual")
        out.append("  layer, which is why they are the one place the system asks for structure.")
        return "\n".join(out)

    out.append(f"  {c['goals']} goals · {c['commitments']} commitments · "
               f"{c['attention']} need attention · {c['stalled']} stalled · "
               f"{c['unbacked']} unbacked\n")

    for g in v["goals"]:
        if only_stalled and g["health"] in {"live", "closed"}:
            continue
        mark = {"attention": "!!", "stalled": " !", "unbacked": " ?",
                "live": " ·", "closed": " ✓"}[g["health"]]
        out.append(f"  {mark} {g['title']}   [{g['health']}]")
        out.append(f"       {g['why']}")
        if g["horizon"]:
            out.append(f"       horizon: {g['horizon']}   attached pages: {g['attached_pages']}")
        for state, items in g["commitments"].items():
            note = "  (non-penalised)" if state in NON_FAILURE else ""
            for it in items:
                until = f", until {it['until']}" if it["until"] else ""
                out.append(f"         {state}{note}: {it['title']}"
                           f"{' — ' + it['resources'] if it['resources'] else ''}{until}")
        out.append("")

    if v["orphan_commitments"]:
        out.append(f"  ORPHAN COMMITMENTS ({len(v['orphan_commitments'])}) — "
                   f"resources committed to a goal the corpus cannot name:")
        for o in v["orphan_commitments"]:
            out.append(f"    {o['title']} -> {o['commits_to']!r}")
        out.append("")

    out.append("  Progress here is computed from the corpus, never typed. To change a goal")
    out.append("  or a commitment, edit its page and open a PR — this view only reads.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="The goal and commitment view.")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stalled", action="store_true", help="only what needs attention")
    ap.add_argument("--no-git", action="store_true", help="use timestamps instead of git dates")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.wiki):
        print(f"error: no {args.wiki!r} directory (cwd is {os.getcwd()}).\n"
              f"       Run from the repo root.", file=sys.stderr)
        return 2

    v = build(args.wiki, use_git=not args.no_git)
    if args.json:
        print(json.dumps(v, indent=1))
    else:
        print(render(v, only_stalled=args.stalled))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
