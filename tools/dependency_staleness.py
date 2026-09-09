#!/usr/bin/env python3
"""
dependency_staleness.py — has the ground moved under a page that was built on other pages?

## Why this exists

`CLAUDE.md` names three derivations: `source` (a reading of one source), `synthesis` (across
several), and `derivative` — "built only from other wiki pages, with no direct source — **the layer
where drift hides**." It names the layer and then measures nothing about it. `staleness.py` says
when a page's own body last moved. `check_sources.py` says a cited file exists. Neither can answer
the question the derivative layer actually raises:

    page B's body changed — which pages rested on B and have not been revisited since?

The idea is borrowed from LangChain's OpenWiki (read 2026-09-09, see
`wiki/deltas/openwiki-okf-2026-09-09.md`), which pins every claim to a content hash of its evidence
so a code change mechanically marks the claim stale. We do not need hashes: `staleness.py` already
computes each page's last *body* change, and `export.py` already holds the link graph. Both halves
existed; nobody had joined them.

## The naive version was measured and thrown away

The obvious predicate — *A links B, and B's body moved after A's did* — was implemented first and
run across the corpus:

    7,667 resolved edges · 3,239 of them stale by that test (42%) · 717 of 801 pages affected

That is not a defect report, it is a description of a living wiki: new work happens, and every page
that points at a page still being written trips the test. A signal that fires on 42% of the corpus
routes no attention at all. Two narrower anchors were tried and also measured nothing, which is
worth recording so nobody tries them again:

  * **`sources:` entries naming a wiki page** — the honest derivation edge. There are **zero** in
    this corpus, and `derivation:` is set on 13 pages of 746. The field is currently decoration.
  * **`validated_at` as the anchor** — ask whether the ground moved under a *dated human
    endorsement*, which would be the sharpest question of all. Every page in this wiki is
    `validation: machine`. Zero human validations, so zero rows. (The check is written anyway and
    fires the moment one exists; see `--anchor validation`.)

## What it measures instead

Two restrictions, each of which earns its place:

1. **The pool is the derivative layer, by `type`.** A `synthesis`, `comparison` or `overview` page
   is by definition built out of other pages — the joker challenges and delta briefs in this corpus
   are all `type: synthesis`. A `summary` page rests on a source in `raw/`, not on its neighbours,
   so a moving neighbour says nothing about it. Pool: 82 pages, 1,434 edges, 375 stale (26%).
   `--all` lifts this and prints the 42% warning, because occasionally you want the wide view.

2. **The change has to be substantial.** `churn` is the fraction of the target's body lines that
   differ between the target as it stood at the source page's last body change and the target now.
   A neighbour gaining a Connections line is not drift; a neighbour rewritten by half is. Measured
   on the pool: median churn 0.07, 82 pairs at or above 0.25, 47 at or above 0.4.

Rows are ranked by **churn × reliance**, where reliance is the share of the source page's links that
point at this target. A page with four links leans on each of them; a page with forty does not.

## What it deliberately is not

**There is no `--check` gate, and that is a decision rather than an omission.** Dependency staleness
is not introduced by the author of the stale page — it appears when somebody *improves the page it
rests on*, which is exactly the work this wiki wants. A gate would fail the person who did the good
thing, and a gate that fails good work gets switched off. This is a sample that routes attention,
the same instrument shape as `verification.py --sample 3`: three a week is a habit, three hundred is
a refusal.

The honest limits, stated rather than assumed away:

  * **A `[[link]]` is not a derivation.** It says *related*, which is weaker than *built on*. Until
    `sources:` carries wiki pages, the link graph is the only edge available and it over-reports.
  * **Churn is a proxy for meaning.** Half a page rewritten may leave every claim about it intact,
    and one changed word may invalidate the lot. This ranks; it never concludes.
  * A hub the whole corpus points at (`axioms`, `exstitutions`) will recur across many rows. That is
    a finding, not noise — a joker challenge argues against the Axioms Register, so a register that
    moved by half since the challenge was filed is precisely the thing worth knowing — but read the
    `in` column before treating a row as specific to one page.

Usage:
  python3 tools/dependency_staleness.py                # the report, top 20
  python3 tools/dependency_staleness.py --sample 3     # the weekly habit
  python3 tools/dependency_staleness.py --churn 0.4    # only substantial movement
  python3 tools/dependency_staleness.py --all          # every page type (see the 42% warning)
  python3 tools/dependency_staleness.py --anchor validation   # ground moved under an endorsement
  python3 tools/dependency_staleness.py --json
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import export  # noqa: E402
import staleness  # noqa: E402

# This travels to eleven repositories; `export.py` and `staleness.py` do not — they are each
# wiki's own, outside the shared layer, and free to drift. Checked here rather than left to
# surface as an AttributeError three functions deep, because a shared tool that fails
# illegibly in a sibling is a tool that gets deleted there instead of reported.
_REQUIRED = {"export": ("build_nodes", "extract_links"), "staleness": ("body_of", "compute")}
_missing = [f"{m}.{a}" for m, attrs in _REQUIRED.items()
            for a in attrs if not hasattr({"export": export, "staleness": staleness}[m], a)]
if _missing:
    sys.exit("dependency_staleness needs " + ", ".join(_missing)
             + " — this wiki's export.py/staleness.py are older than the shared tool. "
               "Run the design-system sync, or update them from the source wiki.")

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"

# The derivative layer, by declared type. A `summary` rests on raw/, not on its neighbours;
# an `entity` accretes biography. These three are built out of other pages by definition.
DERIVATIVE_TYPES = {"synthesis", "comparison", "overview"}

DEFAULT_CHURN = 0.25
# Under a day apart is one working session touching both pages, not drift between them.
DEFAULT_MIN_GAP = 1
HUMAN_VALIDATION = {"self", "peer", "collective"}


def git(*args: str) -> "tuple[str, bool]":
    """Return (stdout, ok). `ok` is False for a non-zero exit, which `git show` uses for
    'this path did not exist at that revision' — distinct from a file that was empty."""
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return p.stdout, p.returncode == 0


# Keyed caches, module-level rather than default-argument, so a test (or any caller that
# repoints ROOT at another repository) can clear them. A default-argument dict would silently
# carry one repository's commit lookups into the next.
_REV_CACHE: "dict[int, str]" = {}
_BODY_CACHE: "dict[tuple, str | None]" = {}


def reset_caches() -> None:
    _REV_CACHE.clear()
    _BODY_CACHE.clear()


def rev_at(ts: int) -> str:
    """The commit that was HEAD at `ts`, or "" when `ts` predates the repository.

    `@<unix>` is git's explicit raw-timestamp form. A bare integer happens to parse the same way
    today, but only by luck of git's date heuristics, and a wiki that outlives its git repo (this
    one does — pages date from March 2025, the repo from 2026-07-03) will hand this function
    timestamps with no commit behind them. Those return "" and are counted, not guessed at.
    """
    if ts not in _REV_CACHE:
        out, _ = git("rev-list", "-1", f"--before=@{int(ts)}", "HEAD")
        _REV_CACHE[ts] = out.strip()
    return _REV_CACHE[ts]


def body_at(rev: str, slug: str) -> "str | None":
    """The page's body at a revision, or None when the page did not exist there."""
    key = (rev, slug)
    if key not in _BODY_CACHE:
        out, ok = git("show", f"{rev}:wiki/{slug}.md")
        _BODY_CACHE[key] = staleness.body_of(out) if ok else None
    return _BODY_CACHE[key]


def churn_between(then: str, now: str) -> float:
    """Fraction of lines that differ, 0.0 (identical) to 1.0 (nothing survives).

    Line-level and order-aware, so a section moved wholesale reads as unchanged rather than as a
    total rewrite. `autojunk` is off: it heuristically ignores lines that recur often, and in a
    wiki those are the frontmatter-adjacent and list lines that carry the content.
    """
    a, b = then.splitlines(), now.splitlines()
    if not a and not b:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    changed = sum(max(i2 - i1, j2 - j1)
                  for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")
    return changed / max(len(a), len(b), 1)


def _iso_to_ts(value) -> "int | None":
    try:
        d = datetime.date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None
    return int(datetime.datetime(d.year, d.month, d.day,
                                 tzinfo=datetime.timezone.utc).timestamp())


def anchor_of(slug: str, node: dict, ages: dict, mode: str) -> "int | None":
    """When this page was last stood behind — the moment a moving dependency starts to matter.

    `body` (default): the page's own last body change. Everything after that is ground the page
    has not seen. `validation`: the date a person put their name to it, which is the sharper
    question and currently returns nothing in this wiki because nothing is human-validated.
    """
    if mode == "validation":
        if node.get("validation") not in HUMAN_VALIDATION:
            return None
        return _iso_to_ts(node.get("validated_at"))
    return ages.get(f"wiki/{slug}.md")


def audit(*, pool_all: bool = False, anchor: str = "body",
          min_churn: float = DEFAULT_CHURN,
          min_gap: int = DEFAULT_MIN_GAP) -> "tuple[list[dict], dict]":
    """Every (page, dependency) pair whose dependency moved substantially since the anchor."""
    nodes, _ = export.build_nodes(str(WIKI))  # WIKI is module-level: tests repoint it
    ages = staleness.compute()
    bodies = {s: staleness.body_of((WIKI / f"{s}.md").read_text(encoding="utf-8"))
              for s in nodes}

    title_to_slug = {n["title"]: sl for sl, n in nodes.items()}
    stats = {"pages": 0, "edges": 0, "moved": 0, "unmeasurable": 0, "same_session": 0}
    rows: list[dict] = []

    for slug, node in sorted(nodes.items()):
        if not pool_all and node.get("type") not in DERIVATIVE_TYPES:
            continue
        base = anchor_of(slug, node, ages, anchor)
        if base is None:
            continue
        stats["pages"] += 1

        # Repeated links count: a page that points at one target four times leans on it.
        targets = [t for t, _ in export.extract_links(bodies[slug])]
        by_slug: dict[str, int] = {}
        for t in targets:
            ts_ = title_to_slug.get(t)
            if ts_ and ts_ != slug:
                by_slug[ts_] = by_slug.get(ts_, 0) + 1
        total_links = sum(by_slug.values())
        if not total_links:
            continue

        rev = rev_at(base)
        for tgt, hits in by_slug.items():
            stats["edges"] += 1
            moved = ages.get(f"wiki/{tgt}.md")
            if moved is None or moved <= base:
                continue
            stats["moved"] += 1
            gap_days = int((moved - base) / 86400)
            if gap_days < min_gap:
                # Both pages moved inside the same day — almost always one working session
                # updating a page and its neighbour together, which is the opposite of drift.
                stats["same_session"] += 1
                continue
            then = body_at(rev, tgt) if rev else None
            if then is None:
                # The dependency did not exist at the anchor (or the anchor predates the repo).
                # Nothing to compare against, so it is counted rather than scored as a total rewrite.
                stats["unmeasurable"] += 1
                continue
            churn = churn_between(then, bodies[tgt])
            if churn < min_churn:
                continue
            reliance = hits / total_links
            rows.append({
                "page": slug,
                "page_title": node["title"],
                "dependency": tgt,
                "dependency_title": nodes[tgt]["title"],
                "churn": round(churn, 3),
                "reliance": round(reliance, 3),
                "weight": round(churn * reliance, 4),
                "gap_days": gap_days,
                "links_here": hits,
                "of_links": total_links,
                "dependency_inbound": len(nodes[tgt]["inbound_links"]),
            })

    rows.sort(key=lambda r: (-r["weight"], r["page"], r["dependency"]))
    return rows, stats


def group_by_dependency(rows: "list[dict]") -> "list[dict]":
    """One entry per moved dependency, carrying the pages that rest on it.

    The flat pair list is dominated by hubs: the Axioms Register alone accounts for most rows,
    because every joker challenge argues against it. That is one finding repeated fourteen times,
    not fourteen findings, and a report that reads as fourteen teaches the reader to skim.
    """
    groups: "dict[str, dict]" = {}
    for r in rows:
        g = groups.setdefault(r["dependency"], {
            "dependency": r["dependency"],
            "dependency_title": r["dependency_title"],
            "dependency_inbound": r["dependency_inbound"],
            "churn": r["churn"],          # the largest reach back, i.e. the oldest dependant
            "pages": [],
        })
        g["churn"] = max(g["churn"], r["churn"])
        g["pages"].append(r)
    out = list(groups.values())
    for g in out:
        g["pages"].sort(key=lambda r: -r["weight"])
        g["weight"] = round(sum(r["weight"] for r in g["pages"]), 4)
    out.sort(key=lambda g: (-g["weight"], g["dependency"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Pages built on other pages whose ground has since moved.")
    ap.add_argument("--churn", type=float, default=DEFAULT_CHURN, metavar="F",
                    help=f"minimum fraction of the dependency rewritten (default {DEFAULT_CHURN})")
    ap.add_argument("--min-gap", type=int, default=DEFAULT_MIN_GAP, metavar="DAYS",
                    help="ignore pairs closer together than this (default 1: same-session edits)")
    ap.add_argument("--top", type=int, default=8, metavar="N",
                    help="how many moved dependencies to show (default 8)")
    ap.add_argument("--pairs", action="store_true",
                    help="the flat page/dependency list instead of grouping by dependency")
    ap.add_argument("--sample", type=int, default=0, metavar="N",
                    help="the weekly habit: the N heaviest pairs, one per page")
    ap.add_argument("--all", action="store_true",
                    help="every page type, not just the derivative layer")
    ap.add_argument("--anchor", choices=("body", "validation"), default="body")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rows, stats = audit(pool_all=args.all, anchor=args.anchor,
                        min_churn=args.churn, min_gap=args.min_gap)

    if args.sample:
        seen, picked = set(), []
        for r in rows:
            if r["page"] in seen:
                continue
            seen.add(r["page"])
            picked.append(r)
            if len(picked) == args.sample:
                break
        rows = picked
        args.pairs = True

    if args.json:
        print(json.dumps({"stats": stats, "rows": rows}, indent=2))
        return 0

    pool = "every page type" if args.all else "the derivative layer (synthesis/comparison/overview)"
    anchored = ("the last human endorsement" if args.anchor == "validation"
                else "each page\u2019s last body change")
    print(f"dependency staleness \u2014 {pool}, anchored on {anchored}\n")
    print(f"  {stats['pages']} page(s) \u00b7 {stats['edges']} dependency edge(s) \u00b7 "
          f"{stats['moved']} moved since the anchor")
    skipped = []
    if stats["same_session"]:
        skipped.append(f"{stats['same_session']} same-session")
    if stats["unmeasurable"]:
        skipped.append(f"{stats['unmeasurable']} not measurable")
    if skipped:
        print("  set aside: " + ", ".join(skipped))
    print(f"  {len(rows)} pair(s) at or above churn {args.churn:.2f}\n")

    if args.all:
        print("  NOTE: across every page type the bare 'dependency moved' test fires on ~42% of\n"
              "  edges. That is a living wiki, not a defect. Read the churn column, not the count.\n")

    if not rows:
        print("  nothing above the threshold." if stats["edges"] else
              "  no pages in this pool carry an anchor \u2014 nothing measurable.")
        return 0

    if args.pairs:
        for r in rows[:max(args.top, len(rows) if args.sample else args.top)]:
            print(f"  {r['weight']:>6.3f}  {r['page']}")
            print(f"          rests on {r['dependency']} "
                  f"\u2014 {r['churn'] * 100:.0f}% rewritten in the {r['gap_days']}d since "
                  f"({r['links_here']} of this page's {r['of_links']} links point at it)")
        print("\n  weight = churn \u00d7 lean. This ranks; it never concludes.")
        return 0

    groups = group_by_dependency(rows)
    for g in groups[:args.top]:
        cited = "cited by {} page(s) corpus-wide".format(g["dependency_inbound"])
        print(f"  {g['dependency']}  \u2014 up to {g['churn'] * 100:.0f}% rewritten, {cited}")
        for r in g["pages"][:6]:
            print(f"      {r['gap_days']:>4}d behind  {r['page']}  "
                  f"({r['links_here']}/{r['of_links']} of its links)")
        if len(g["pages"]) > 6:
            print(f"      \u2026 and {len(g['pages']) - 6} more page(s) resting on it")
        print()
    if len(groups) > args.top:
        print(f"  \u2026 and {len(groups) - args.top} more moved dependenc(ies)\n")
    print("  Each block is one dependency that moved and the pages written against the older\n"
          "  version. 'cited by N corpus-wide' high means a hub: the move is real, but the row\n"
          "  is less specific to any one page. This ranks; it never concludes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
