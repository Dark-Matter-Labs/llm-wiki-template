#!/usr/bin/env python3
"""
view_modules.py — the data behind the full view's modules, beyond "Needs you" and the skills menu.

Asked for on 12 October 2026: a full view with "a graph view of the wiki at a glance — show big areas
but not everything, not overwhelming", an onboarding list, and modules people can choose. Each
function here returns plain data; build_needs_you_page.py puts it in the page.

- **areas** — the wiki's big areas. Pages that link to each other are grouped (Louvain modularity,
  deterministic), tiny groups are left off, and at most MAX_AREAS are shown, each named by its most
  linked page with its few most linked pages listed. Calm by design: a map of 850 dots answers nothing.
- **onboarding** — the first things that make a wiki useful, ticked from what the wiki shows.
- **moved** — what changed this week.
- **travels** — where this wiki's work goes, and what could go.
- **growth**, **work**, **trust** — the charts, added the same day on "the graphic and data viz + visuals
  representations as well": pages and sources by week, the log's work by kind, and who stands behind
  the pages. Counts only; the page draws them.

    python3 tools/view_modules.py --json
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from community import louvain_communities  # noqa: E402
MIN_AREA = 3
MAX_AREAS = 9
TOP_PAGES = 4
OFF_MAP = re.compile(r"^wiki/(crm/|log/|index/|newsletter/)")


def _key(t: str) -> str:
    return " ".join(str(t).lower().split())


def areas(nodes: list[dict]) -> dict:
    keep = [n for n in nodes if n.get("type") != "overview" and not OFF_MAP.match(n.get("path") or "")]
    by_title = {_key(n["title"]): n for n in keep}
    nbrs: dict[str, set] = {n["slug"]: set() for n in keep}
    for n in keep:
        for t in n.get("outbound_links") or []:
            o = by_title.get(_key(t))
            if o and o["slug"] != n["slug"]:
                nbrs[n["slug"]].add(o["slug"])
                nbrs[o["slug"]].add(n["slug"])
    degree = {s: len(v) for s, v in nbrs.items()}
    # community.py, the shared Louvain patterns.py uses. On indy-llm-wiki, resolution 1.0 put 448 pages in one
    # area; 1.5 gives eight or nine, and the same areas at 2. (Label propagation, tried first, made one of 417.)
    label = {p: i for i, g in enumerate(louvain_communities({n: {m: 1.0 for m in vs} for n, vs in nbrs.items()}, resolution=1.5)) for p in g}
    groups = collections.defaultdict(list)
    for s, l in label.items():
        groups[l].append(s)
    big = sorted((g for g in groups.values() if len(g) >= MIN_AREA), key=lambda g: (-len(g), min(g)))[:MAX_AREAS]
    slug_node = {n["slug"]: n for n in keep}
    out, area_of = [], {}
    for i, g in enumerate(big):
        ranked = sorted(g, key=lambda s: (-degree[s], s))
        hub = slug_node[ranked[0]]
        out.append({"id": i, "label": hub["title"], "size": len(g), "about": hub.get("description") or "",
                    "pages": [slug_node[s]["title"] for s in ranked[:TOP_PAGES]]})
        for s in g:
            area_of[s] = i
    weights = collections.Counter()
    for s, vs in nbrs.items():
        for o in vs:
            a, b = area_of.get(s), area_of.get(o)
            if a is not None and b is not None and a < b:
                weights[(a, b)] += 1
    return {"areas": out, "links": [{"a": a, "b": b, "weight": w} for (a, b), w in sorted(weights.items())],
            "pages_total": len(keep)}


def onboarding(raw_files: int, summaries: int, ops: dict, stood_behind: int, overview_written: bool) -> list[dict]:
    steps = [
        ("Say what this wiki is for", overview_written, "Help me write my overview: what this wiki is for and how I'd know it worked."),
        ("Add your first sources", raw_files >= 3, "Add this to the wiki: …"),
        ("Turn a source into pages", summaries >= 1, "Ingest the documents that haven't been filed yet."),
        ("Ask your wiki a question", ops.get("query", 0) >= 1, "What does the wiki say about …?"),
        ("Stand behind a page", stood_behind >= 1, "Which page should I stand behind first, and why?"),
        ("Challenge a position", ops.get("joker", 0) >= 1, "Challenge this: …"),
        ("Share something with the team", ops.get("contribute", 0) >= 1, "What in my wiki could go to the team, and what would that share?"),
    ]
    return [{"label": l, "done": bool(d), "say": "" if d else s} for l, d, s in steps]


def travels(federation: dict, up: dict) -> dict:
    targets = (up or {}).get("targets") or []
    return {"role": (federation or {}).get("role", "spoke"),
            "shares_into": list((federation or {}).get("contributes_to") or []),
            "reads_from": list((federation or {}).get("reads_from") or []),
            "could_go_up": sum(t.get("eligible", 0) for t in targets),
            "top": [p.get("title") for t in targets for p in (t.get("top") or [])][:3]}


def _monday(day: str) -> datetime.date:
    d = datetime.date.fromisoformat(day)
    return d - datetime.timedelta(days=d.weekday())


def growth(added: list[tuple[str, str]], today: str) -> list[dict]:
    """Cumulative pages and sources per week. `added` is (date, "page" | "source") per file."""
    if not added:
        return []
    per = collections.Counter((_monday(d), k) for d, k in added)
    week, end, out, pages, sources = min(w for w, _ in per), _monday(today), [], 0, 0
    while week <= end:
        pages, sources = pages + per[(week, "page")], sources + per[(week, "source")]
        out.append({"week": week.isoformat(), "pages": pages, "sources": sources})
        week += datetime.timedelta(days=7)
    return out


#: The log's operations in three plain kinds. Anything not named here is upkeep.
ADDING = {"ingest", "onboard"}
THINKING = {"query", "office-hours", "joker", "delta", "reflect", "synthesis", "metacognition", "brief",
            "luck", "inquiry", "patterns", "cross-check", "gravity"}
LOG_HEAD = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] ([a-z-]+)")


def work(log_lines: list[str], today: str, weeks: int = 12) -> dict:
    end = _monday(today)
    starts = [end - datetime.timedelta(days=7 * i) for i in range(weeks - 1, -1, -1)]
    rows = {w: {"week": w.isoformat(), "adding": 0, "thinking": 0, "upkeep": 0} for w in starts}
    for line in log_lines:
        m = LOG_HEAD.match(line)
        if not m or _monday(m[1]) not in rows:
            continue
        op = m[2]
        rows[_monday(m[1])]["adding" if op in ADDING else "thinking" if op in THINKING else "upkeep"] += 1
    return {"weeks": [rows[w] for w in starts]}


def trust(nodes: list[dict]) -> dict:
    v = collections.Counter(n.get("validation") or "machine" for n in nodes)
    c = collections.Counter(n.get("confidence") for n in nodes)
    return {"validation": [["Filed by Claude", v["machine"]], ["You", v["self"]], ["Others too", v["peer"] + v["collective"]]],
            "confidence": [["Low", c["low"]], ["Medium", c["medium"]], ["High", c["high"]]]}


# ---------------------------------------------------------------- reading a wiki

def _git(root, *a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True).stdout


def moved(root: pathlib.Path, nodes: list[dict], days: int = 7) -> dict:
    added = [l for l in _git(root, "log", f"--since={days}.days", "--diff-filter=A", "--name-only", "--format=", "--", "wiki/").split()
             if l.endswith(".md") and not OFF_MAP.match(l)]
    changed = {l for l in _git(root, "log", f"--since={days}.days", "--name-only", "--format=", "--", "wiki/").split()
               if l.endswith(".md") and not OFF_MAP.match(l)}
    title = {n.get("slug"): n["title"] for n in nodes}            # matched by file name: pages can sit in subfolders
    newest = [title[pathlib.PurePosixPath(p).stem] for p in dict.fromkeys(added) if pathlib.PurePosixPath(p).stem in title][:5]
    return {"days": days, "added": len(set(added)), "changed": len(changed - set(added)), "newest": newest}


def _log_lines(root: pathlib.Path) -> list[str]:
    return [l for p in (root / "wiki" / "log").glob("*.md")
            for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if LOG_HEAD.match(l)]


def _log_ops(lines: list[str]) -> collections.Counter:
    return collections.Counter(LOG_HEAD.match(l)[2] for l in lines)


def _added(root: pathlib.Path) -> list[tuple[str, str]]:
    """(date first added, page | source) for every page and source the wiki holds now."""
    # shortcut: a renamed file counts from its rename; needs the full history (fetch-depth 0 in CI).
    live = set(_git(root, "ls-files", "wiki", "raw").splitlines())
    first, day = {}, None
    for l in _git(root, "log", "--no-renames", "--diff-filter=A", "--format=@%as", "--name-only", "--", "wiki", "raw").splitlines():
        if l.startswith("@"):
            day = l[1:]
        elif l in live and not OFF_MAP.match(l) and (l.startswith("raw/") or l.endswith(".md")):
            first[l] = day            # newest first, so the last one seen is the first add
    return [(d, "source" if f.startswith("raw/") else "page") for f, d in first.items()]


def gather(root: pathlib.Path, waiting_up: dict | None = None) -> dict:
    wj = root / "export" / "wiki.json"
    # Always rebuilt: a copy left from an earlier run missed this week's pages (found 2026-10-12).
    subprocess.run(["python3", "tools/export.py"], cwd=root, capture_output=True)
    d = json.loads(wj.read_text(encoding="utf-8")) if wj.exists() else {"nodes": []}
    nodes = d["nodes"] if isinstance(d, dict) else d
    nodes = list(nodes.values()) if isinstance(nodes, dict) else nodes
    for n in nodes:
        n.setdefault("path", f"wiki/{n.get('slug')}.md")
    ov = root / "wiki" / "overview.md"
    ov_text = ov.read_text(encoding="utf-8", errors="replace") if ov.exists() else ""
    raw = [p for p in (root / "raw").rglob("*") if p.is_file() and not p.name.startswith(".")] if (root / "raw").exists() else []
    log, today = _log_lines(root), datetime.date.today().isoformat()
    fed = json.loads((root / "design" / "federation.json").read_text()) if (root / "design" / "federation.json").exists() else {}
    return {
        "map": areas(nodes),
        "onboarding": onboarding(raw_files=len(raw), summaries=sum(1 for n in nodes if n.get("type") == "summary"),
                                 ops=_log_ops(log), stood_behind=sum(1 for n in nodes if n.get("validation") in ("self", "peer", "collective")),
                                 overview_written=len(ov_text) > 1500 and "fresh wiki" not in ov_text.lower()),
        "moved": moved(root, nodes),
        "growth": growth(_added(root), today),
        "work": work(log, today),
        "trust": trust([n for n in nodes if not OFF_MAP.match(n.get("path") or "")]),
        "travels": travels(fed, waiting_up or {}),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The full view's module data for one wiki.")
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    out = gather(pathlib.Path(a.root))
    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        for ar in out["map"]["areas"]:
            print(f"{ar['size']:4d}  {ar['label']}  ({', '.join(ar['pages'][1:])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
