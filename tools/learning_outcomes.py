#!/usr/bin/env python3
"""
learning_outcomes.py — what did this corpus learn in a period? Computed, never typed.

## Why this exists

On the 9 September 2026 INO call Robyn asked for the artifact she said mattered most: a read-out
of learning, *"both internally to DM"* and *"to QCF as a funder or other funding partners"* —
*"what signals anyone that's going out into the field is learning about the funding landscape,
the shape of the fields that we're engaging in, the external signals"* — and was unsure whether
the same shape serves both audiences. Gurden's answer was to build it the way `goals.py` builds
health: from the corpus, with nothing typed, and let her react to a draft.

This is that draft. It refuses to define "learning outcome" as a category anyone fills in. A
learning outcome here is **movement of the corpus in a window**: what entered it, what changed
its mind, who stood behind what, and what is still open. If that is the wrong shape, the tool is
cheap to change; a hand-written outcomes report would have been expensive to change and quietly
flattering.

## What it counts, and from where

  ENTERED     pages first committed in the window, by type. A `summary` is a source read — a
              signal from the field. An `entity` is an organisation, person or place the corpus
              met. The fields those signals came from are their tags, ranked.
  MOVED       positions that changed: `contradicts:` declared, `superseded_by:` / `devalued_by:`
              set (a human closed a contradiction), and axioms whose evidence status changed
              between the start and end of the window, read from git.
  STOOD BEHIND  human validation events (`validated_at` in window, tier not `machine`) and
              per-claim verification marks `{✓ name date}` dated in window. Never a model.
  STILL OPEN  contradictions with no resolution, goals with nothing committed. Honesty about
              what did not move is part of a learning read-out or it is a brochure.

Dates come from **git** (first commit of each page; the file at the window's start revision for
axioms), not from `timestamp:` — for a Substack summary that field is the essay's publication
date, and the 2026-08-12 backfill taught this wiki what a frontmatter clock is worth.

## Two audiences, one rule

`--audience internal` (default) counts every page and may name `internal` ones.
`--audience funder` counts only `public` and `unlisted` pages and names only those.
**Neither names a `private` page.** Counts are not leaks; titles and links are. Every number
carries the field it was read from, so a reader can re-derive it, and the funder cut says what it
excluded rather than pretending the excluded pages do not exist.

This is a reading. It has no `--check` and proposes nothing; Robyn and the funders decide whether
the shape is right, and the skill that would send it anywhere does not exist yet on purpose.

Usage:
  python3 tools/learning_outcomes.py                              # last 100 days, internal
  python3 tools/learning_outcomes.py --since 2026-06-01           # a window
  python3 tools/learning_outcomes.py --audience funder            # the shareable cut
  python3 tools/learning_outcomes.py --json
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import export  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
AXIOMS = WIKI / "axioms.md"

# One 10x100 cycle, the same window goals.py uses for an endorsement.
DEFAULT_DAYS = 100
HUMAN = {"self", "peer", "collective"}
AUDIENCE_TIERS = {"internal": {"public", "unlisted", "internal"},
                  "funder": {"public", "unlisted"}}
# Verification marks: (raw/x.pdf){✓ Name 2026-09-04}
MARK = re.compile(r"\{✓\s+([^}]+?)\s+(\d{4}-\d{2}-\d{2})\}")
# Axioms Register rows: an id, and an evidence status somewhere on the card.
AXIOM_ID = re.compile(r"^#{2,4}\s+\**(A\d+)\b", re.M)
AXIOM_STATUS = re.compile(r"\b(evidenced|assumptive|contested)\b")
# Navigation, not content.
SKIP_DIRS = {"log", "index"}
SKIP_FILES = {"index.md", "log.md"}


def git(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else ""


def repo_start() -> "tuple[str, str]":
    """(sha, ISO date) of the repository's first commit — the horizon behind which git knows nothing."""
    line = git("rev-list", "--max-parents=0", "--format=%H %cs", "HEAD").strip().splitlines()
    for l in line:
        parts = l.split()
        if len(parts) == 2 and len(parts[0]) == 40:
            return parts[0], parts[1]
    return "", ""


def first_commit_dates() -> dict[str, str]:
    """rel path -> ISO date the file was first added. One git call for the whole wiki."""
    out: dict[str, str] = {}
    log = git("log", "--diff-filter=A", "--format=%x00%cs", "--name-only", "--", "wiki/")
    date = None
    for line in log.splitlines():
        if line.startswith("\x00"):
            date = line[1:].strip()
        elif line.strip() and date:
            # newest first; keep the OLDEST add for a path that was added more than once
            out[line.strip()] = date
    return out


def rev_before(day: datetime.date) -> str:
    return git("rev-list", "-1", f"--before={day.isoformat()}T00:00:00", "HEAD").strip()


def axiom_statuses(text: str) -> dict[str, str]:
    """A1 -> evidenced|assumptive|contested, read from the register's cards."""
    out: dict[str, str] = {}
    ids = list(AXIOM_ID.finditer(text))
    for i, m in enumerate(ids):
        card = text[m.end(): ids[i + 1].start() if i + 1 < len(ids) else len(text)]
        s = AXIOM_STATUS.search(card)
        if s:
            out[m.group(1)] = s.group(1)
    return out


def in_window(iso: str | None, since: datetime.date, until: datetime.date) -> bool:
    if not iso:
        return False
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return False
    return since <= d <= until


def build(since: datetime.date, until: datetime.date, audience: str = "internal") -> dict:
    tiers = AUDIENCE_TIERS[audience]
    nodes, _ = export.build_nodes(str(WIKI))
    added = first_commit_dates()

    def visible(n: dict) -> bool:
        return (n.get("visibility") or "private") in tiers

    def name(n: dict) -> str | None:
        """A title, or None when the audience may not see it. Private is never named."""
        return n["title"] if visible(n) else None

    pages = [n for s, n in nodes.items()
             if not (s.split("/")[0] in SKIP_DIRS or f"{s}.md" in SKIP_FILES)]

    # ── ENTERED ─────────────────────────────────────────────────────────────────────
    # The repository's first commit carried the whole existing corpus in at once. Those pages
    # did not "enter" in any window that contains that date — they were imported. Counting
    # them would make the first read-out claim 800 pages of learning, which is the same clock
    # failure staleness.py documents: a signal a migration can reset measures migrations.
    start_sha, start_day = repo_start()
    imported = {f"wiki/{n['slug']}.md" for n in pages
                if start_day and added.get(f"wiki/{n['slug']}.md") == start_day}
    entered = [n for n in pages
               if f"wiki/{n['slug']}.md" not in imported
               and in_window(added.get(f"wiki/{n['slug']}.md"), since, until)]
    imported_in_window = sum(1 for rel in imported
                             if in_window(start_day, since, until))
    by_type = collections.Counter(n.get("type") or "untyped" for n in entered if visible(n))
    hidden_entered = sum(1 for n in entered if not visible(n))
    fields = collections.Counter(t for n in entered if visible(n) and n.get("type") == "summary"
                                 for t in (n.get("tags") or []))
    signals = [{"title": n["title"], "tags": n.get("tags") or []}
               for n in entered if visible(n) and n.get("type") == "summary"]
    met = [n["title"] for n in entered if visible(n) and n.get("type") == "entity"]

    # ── MOVED ───────────────────────────────────────────────────────────────────────
    declared = [n for n in entered if n.get("contradicts")]
    resolved = [n for n in pages if (n.get("superseded_by") or n.get("devalued_by"))
                and in_window(n.get("timestamp"), since, until)]
    axiom_moves = []
    rev = rev_before(since) or start_sha
    axioms_baseline = "window start" if rev_before(since) else "the repository's first commit"
    if AXIOMS.exists():
        now_s = axiom_statuses(AXIOMS.read_text(encoding="utf-8", errors="replace"))
        then_text = git("show", f"{rev}:wiki/axioms.md") if rev else ""
        then_s = axiom_statuses(then_text) if then_text else {}
        for aid, status in sorted(now_s.items()):
            before = then_s.get(aid)
            if before and before != status:
                axiom_moves.append({"axiom": aid, "from": before, "to": status})
            elif not before and then_text:
                axiom_moves.append({"axiom": aid, "from": None, "to": status})

    # ── STOOD BEHIND ────────────────────────────────────────────────────────────────
    validations = [n for n in pages if (n.get("validation") in HUMAN)
                   and in_window(n.get("validated_at"), since, until)]
    marks = 0
    marks_hidden = 0
    for n in pages:
        for _who, day in MARK.findall(n.get("body") or ""):
            if in_window(day, since, until):
                if visible(n):
                    marks += 1
                else:
                    marks_hidden += 1

    # ── STILL OPEN ──────────────────────────────────────────────────────────────────
    titles = {n["title"]: n for n in pages}
    open_contradictions = []
    for n in pages:
        tgt = n.get("contradicts")
        if not tgt:
            continue
        other = titles.get(tgt)
        closed = (other and (other.get("superseded_by") or other.get("devalued_by"))) or \
                 n.get("superseded_by") or n.get("devalued_by")
        if not closed:
            open_contradictions.append((name(n), name(other) if other else None))
    goals = [n for n in pages if n.get("type") == "goal"]
    commit_targets = {n.get("commits_to") for n in pages if n.get("type") == "commitment"}
    unbacked = [g for g in goals if g["title"] not in commit_targets
                and not any(c.get("parent") == g["title"] for c in goals)]

    return {
        "window": {"since": since.isoformat(), "until": until.isoformat(),
                   "days": (until - since).days},
        "audience": audience,
        "tiers_counted": sorted(tiers),
        "repo_start": start_day or None,
        "entered": {
            "total": len(entered),
            "imported_at_repo_start_not_counted": imported_in_window,
            "by_type": dict(by_type),
            "not_shown_to_this_audience": hidden_entered,
            "fields": [{"tag": t, "sources": c} for t, c in fields.most_common(10)],
            "signals": signals,
            "met": met,
        },
        "moved": {
            "contradictions_declared": [
                {"page": name(n),
                 # the other side is named only if THAT page is visible to this audience
                 "with": name(titles[n["contradicts"]]) if n["contradicts"] in titles else None}
                for n in declared],
            "positions_closed": [{"page": name(n),
                                  "by": n.get("superseded_by") or n.get("devalued_by"),
                                  "how": "superseded" if n.get("superseded_by") else "devalued"}
                                 for n in resolved],
            "axioms": axiom_moves,
            "axioms_compared_against": rev[:8] if rev else None,
            "axioms_baseline": axioms_baseline if rev else None,
        },
        "stood_behind": {
            "validations": [{"page": name(n), "tier": n.get("validation"),
                             "at": n.get("validated_at")} for n in validations],
            "claims_verified": marks,
            "claims_verified_not_shown": marks_hidden,
        },
        "still_open": {
            "contradictions": len(open_contradictions),
            "unbacked_goals": [name(g) for g in unbacked],
            "unbacked_goals_total": len(unbacked),
        },
    }


def render(v: dict) -> str:
    w, e, m, s, o = v["window"], v["entered"], v["moved"], v["stood_behind"], v["still_open"]
    aud = v["audience"]
    L = [f"learning outcomes — {w['since']} → {w['until']} ({w['days']} days) · audience: {aud}",
         f"  counted: pages at {', '.join(v['tiers_counted'])}. Private pages are never named; "
         f"{'internal pages are not named for a funder.' if aud == 'funder' else 'internal pages are named.'}",
         ""]
    L.append(f"WHAT ENTERED — {e['total']} page(s) first committed in the window"
             + (f" ({e['not_shown_to_this_audience']} not shown to this audience)"
                if e["not_shown_to_this_audience"] else ""))
    if e.get("imported_at_repo_start_not_counted"):
        L.append(f"  not counted: {e['imported_at_repo_start_not_counted']} page(s) carried in by the "
                 f"repository's first commit on {v['repo_start']} — imported, not learned in this window")
    for t, c in sorted(e["by_type"].items(), key=lambda kv: -kv[1]):
        L.append(f"    {c:>4}  {t}")
    if e["fields"]:
        L.append("  signals from the field, by tag on the sources read:")
        for f in e["fields"]:
            L.append(f"    {f['sources']:>4}  {f['tag']}")
    if e["met"]:
        L.append(f"  met: {', '.join(e['met'][:12])}" + (" …" if len(e["met"]) > 12 else ""))
    L.append("")
    L.append("WHAT MOVED — positions that changed")
    L.append(f"    {len(m['contradictions_declared']):>4}  contradiction(s) declared")
    for c in m["contradictions_declared"][:8]:
        L.append(f"          {c['page'] or '(not shown)'}  ⟂  {c['with'] or '(not shown)'}")
    L.append(f"    {len(m['positions_closed']):>4}  position(s) closed by a person")
    for c in m["positions_closed"][:8]:
        L.append(f"          {c['page'] or '(not shown)'} — {c['how']} by {c['by']}")
    L.append(f"    {len(m['axioms']):>4}  axiom(s) changed evidence status"
             + (f"  (vs the register at {m['axioms_baseline']}, {m['axioms_compared_against']})"
                if m["axioms_compared_against"] else "  (no register history to compare)"))
    for a in m["axioms"][:10]:
        L.append(f"          {a['axiom']}: {a['from'] or 'new'} → {a['to']}")
    L.append("")
    L.append("WHO STOOD BEHIND WHAT")
    L.append(f"    {len(s['validations']):>4}  page(s) validated by a person")
    for x in s["validations"][:8]:
        L.append(f"          {x['page'] or '(not shown)'}  ({x['tier']}, {x['at']})")
    L.append(f"    {s['claims_verified']:>4}  claim(s) verified against their source"
             + (f"  (+{s['claims_verified_not_shown']} on pages not shown)" if s["claims_verified_not_shown"] else ""))
    L.append("")
    L.append("STILL OPEN — what did not move")
    L.append(f"    {o['contradictions']:>4}  contradiction(s) with no resolution")
    L.append(f"    {o['unbacked_goals_total']:>4}  goal(s) with nothing committed"
             + (": " + "; ".join(g for g in o["unbacked_goals"] if g) if any(o["unbacked_goals"]) else ""))
    L.append("")
    L.append("  Computed from the corpus — first-commit dates from git, statuses from frontmatter,")
    L.append("  axioms from the register at the window's two ends. Nothing here was typed. If the")
    L.append("  shape is wrong, change the tool; do not hand-edit the numbers.")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="What the corpus learned in a window.")
    ap.add_argument("--since", help="ISO date; default: --days ago")
    ap.add_argument("--until", help="ISO date; default: today")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--audience", choices=sorted(AUDIENCE_TIERS), default="internal")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    until = datetime.date.fromisoformat(args.until) if args.until else datetime.date.today()
    since = datetime.date.fromisoformat(args.since) if args.since else until - datetime.timedelta(days=args.days)
    if not WIKI.is_dir():
        print("no wiki/ directory — run from the repo root", file=sys.stderr)
        return 2
    v = build(since, until, args.audience)
    print(json.dumps(v, indent=1, ensure_ascii=False) if args.json else render(v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
