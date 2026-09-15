#!/usr/bin/env python3
"""newsletter.py — the month's material, gathered across this wiki and the commons it reads.

This is the cheap half of the monthly newsletter, and the split is the whole design.

**Why the weekly reflection is being replaced.** It ran every Friday, called the Claude API on
each run — billed outside the Team plan — and produced eight reflections between weeks 28 and 36.
Measured on 2026-09-15, across that whole run:

    ordinary pages citing a reflection (of 819)                     7
    of the 30 inbound links, how many came from the joker pages
      the same weekly run wrote                                    17
    times W35 and W36 were touched after being written              1 each
    times W30 was touched after being written                       4
    workflow runs                                                  15
    of which failed                                                 5   (33%)

Attention decayed from four touches to one, seven ordinary pages of 819 ever cited one, and the
most recent run, 11 September, failed with nobody noticing. A weekly artefact almost nobody reads
is not a
communication problem to solve with better prose; it is a cadence problem, and paying a model
every Friday to produce it makes it worse rather than better.

**So the work is split.** This script does the arithmetic: it gathers what actually happened in a
month, deterministically, with no model and no cost. The `newsletter` skill then writes the issue
from that material — once a month instead of once a week, with a person reading it before it goes
anywhere. Four times less model spend, and the expensive step is the one that needs judgement.

What this deliberately does NOT do:

  * It does not rank people. A leaderboard of contributions has been asked for and it is a real
    idea, but a per-person ranking inside a shared instance is activity tracking of named
    colleagues, which the house rule forbids — "knowledge, not surveillance ... binds hardest in
    the team wiki and every shared instance". Counts are reported per WIKI, which is what the
    federation diagram already shows publicly. If the group wants a leaderboard, that is a
    decision for people to take with their eyes open, not a default a tool ships with.
  * It does not send anything. Delivery needs credentials and a list of recipients; both belong
    to a person.
  * It does not touch `private` material. It reads the same boundary-filtered cuts the lens does.

    python3 tools/newsletter.py                  # last complete month, human-readable
    python3 tools/newsletter.py --month 2026-08  # a specific month
    python3 tools/newsletter.py --json           # the material, for the skill to write from
"""
import argparse
import calendar
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMMONS = ROOT / ".commons"


def last_complete_month(today=None):
    """The month before this one. A newsletter about a month still running is a guess."""
    today = today or dt.date.today()
    first_of_this = today.replace(day=1)
    end = first_of_this - dt.timedelta(days=1)
    return end.year, end.month


def month_window(year, month):
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, 1), dt.date(year, month, last)


def read_out(wiki_dir, since, until):
    """Ask a wiki's own learning_outcomes for the window. None when it cannot answer.

    Shelling out rather than importing: each wiki carries its own copy of the tool, and the
    copy that belongs to a corpus is the one that should read it.
    """
    tool = wiki_dir / "tools" / "learning_outcomes.py"
    if not tool.exists():
        return None
    try:
        out = subprocess.run(
            [sys.executable, str(tool), "--since", since.isoformat(),
             "--until", until.isoformat(), "--audience", "internal", "--json"],
            cwd=wiki_dir, capture_output=True, text=True, timeout=180)
        if out.returncode != 0:
            return {"error": (out.stderr or "").strip().splitlines()[-1:] or ["failed"]}
        return json.loads(out.stdout)
    except Exception as exc:                      # noqa: BLE001 — a wiki that cannot answer
        return {"error": [str(exc)]}              # is reported, never silently dropped


def commons_cuts():
    """The commons this wiki reads down, from the gitignored cache sync_commons.py fills."""
    found = {}
    if not COMMONS.is_dir():
        return found
    for cut in sorted(COMMONS.rglob("wiki.shared.json")):
        name = cut.relative_to(COMMONS).parts[0]
        try:
            d = json.loads(cut.read_text(encoding="utf-8"))
        except Exception:                          # noqa: BLE001
            continue
        found[name] = d if isinstance(d, list) else d.get("nodes", d.get("pages", []))
    return found


def arrivals(nodes, since, until):
    """Pages dated inside the window, by the wiki they came from.

    Per WIKI, never per person — see the module docstring. `origin` is stamped by
    contribute.py and names a repository; `contributed_by` names a human and is not read here.
    """
    by_origin = {}
    for n in nodes:
        ts = str(n.get("timestamp") or "")[:10]
        if not (since.isoformat() <= ts <= until.isoformat()):
            continue
        by_origin[n.get("origin") or "(written here)"] = \
            by_origin.get(n.get("origin") or "(written here)", 0) + 1
    return dict(sorted(by_origin.items(), key=lambda kv: -kv[1]))


def _tool(path, args, cwd=None, timeout=300):
    """Run one of this repo's own tools and parse its JSON. None when it is not here.

    Every signal below is optional by design. A wiki without the tool gets the section as a
    stated blank rather than as a guess, and the newsletter says which it was.
    """
    tool = (cwd or ROOT) / path
    if not tool.exists():
        return None
    try:
        r = subprocess.run([sys.executable, str(tool)] + list(args),
                           cwd=str(cwd or ROOT), capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode != 0:
            return {"error": (r.stderr or "").strip().splitlines()[-1:] or ["failed"]}
        return json.loads(r.stdout)
    except Exception as exc:                          # noqa: BLE001
        return {"error": [str(exc)]}


def patterns_now():
    """Clusters the corpus has formed, and which of them nobody has named.

    An unnamed cluster is the most interesting object this system produces: a set of pages
    that hang together tightly enough to be one idea, with no page saying what the idea is.
    `patterns.py` excludes private material and the CRM before it starts.
    """
    d = _tool("tools/patterns.py", ["--json"])
    if not d or "error" in d:
        return d
    cands = d.get("candidates") or []
    unnamed = [c for c in cands if not c.get("naming_page")]
    travels = [c for c in cands if c.get("travels")]
    def brief(c):
        return {"pages": c.get("pages"), "cohesion": c.get("cohesion"),
                "distinct_sources": c.get("distinct_sources"),
                "tags": (c.get("tags") or [])[:5],
                "wikis": list(c.get("wikis") or {}),
                "members": (c.get("members") or [])[:4]}
    return {
        # Say what was in scope. `travelling_between_wikis: 0` means something very
        # different when no commons was read than when three were, and a reader cannot
        # tell the two apart from the number.
        "corpus": d.get("corpus"),
        "clusters": len(cands),
        "unnamed": len(unnamed),
        "travelling_between_wikis": len(travels),
        "settings": d.get("settings"),
        "largest_unnamed": [brief(c) for c in
                            sorted(unnamed, key=lambda c: -(c.get("pages") or 0))[:5]],
        "travelling": [brief(c) for c in travels[:3]],
    }


def trajectory(since, until):
    """Which terms rose and which fell across the window, and by how much.

    This is the one measurement that says what the corpus is MOVING TOWARDS rather than what
    it accumulated. `|V|` is the size of the shift; the terms are what moved.
    """
    g = ROOT / ".claude" / "skills" / "gravity" / "compute_gravity.py"
    if not g.exists():
        return None
    try:
        r = subprocess.run(
            [sys.executable, str(g), "series",
             "--dates", f"{(since - dt.timedelta(days=1)).isoformat()},{until.isoformat()}"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    except Exception as exc:                          # noqa: BLE001
        return {"error": [str(exc)]}
    if r.returncode != 0:
        return {"error": (r.stderr or "").strip().splitlines()[-1:] or ["failed"]}
    out = {"snapshots": [], "magnitude": None, "rising": [], "falling": []}
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("[") and "pages=" in line:
            out["snapshots"].append(line)
        elif "|V|=" in line:
            try:
                out["magnitude"] = float(line.split("|V|=")[1].split()[0])
            except Exception:                         # noqa: BLE001
                pass
        elif line.startswith("rising:"):
            out["rising"] = [w.strip() for w in line.split(":", 1)[1].split(",") if w.strip()]
        elif line.startswith("falling:"):
            out["falling"] = [w.strip() for w in line.split(":", 1)[1].split(",") if w.strip()]
    return out


COMMIT_STATES = ("proposed", "held", "honoured", "revised", "lapsed", "exited", "declined")


def goal_vectors(cuts, since, until):
    """Where the goals are, and whether anything is actually committed against them.

    Read from the commons cuts rather than from a sibling checkout, because a commons is
    where goals live and a CI runner has no siblings on disk. `declined` and `exited` are
    NOT failures — refusing, or leaving deliberately, is a valid outcome and the schema says
    so. Only `lapsed` counts against a goal.
    """
    out = {}
    for name, nodes in cuts.items():
        goals = [n for n in nodes if n.get("type") == "goal"]
        commits = [n for n in nodes if n.get("type") == "commitment"]
        if not goals and not commits:
            continue
        backed = {c.get("commits_to") for c in commits if c.get("commits_to")}
        states = {s: sum(1 for c in commits if (c.get("state") or "") == s)
                  for s in COMMIT_STATES}
        moved = [{"page": c.get("title"), "state": c.get("state")}
                 for c in commits
                 if since.isoformat() <= str(c.get("timestamp") or "")[:10] <= until.isoformat()]
        out[name] = {
            "goals": len(goals),
            "commitments": len(commits),
            "goals_with_nothing_committed": sum(1 for g in goals
                                                if g.get("title") not in backed),
            "commitment_states": {k: v for k, v in states.items() if v},
            "stood_behind_by_a_person": sum(1 for g in goals
                                            if (g.get("validation") or "machine") != "machine"),
            "moved_this_month": moved,
            "horizons": {h: sum(1 for g in goals if g.get("horizon") == h)
                         for h in ("near", "mid", "far")},
        }
    return out


def corrections(since, until):
    """How much of the month was advancing the work, and how much was putting it back.

    The log's `rebuild` / `repair` split exists so the correction rate is visible without a
    metacognition pass, and `(mine)` marks a repair of the model's own earlier error. A high
    repair count is not a failure; a repair count nobody can see is.
    """
    kinds = {"ingest": 0, "query": 0, "lint": 0, "rebuild": 0, "repair": 0}
    mine = 0
    titles = {"repair": [], "rebuild": []}
    for f in sorted((ROOT / "wiki" / "log").glob("*.md")):
        stem = f.stem
        if len(stem) == 7:                            # a pre-split month file, YYYY-MM
            if not (since.isoformat()[:7] <= stem <= until.isoformat()[:7]):
                continue
        elif not (since.isoformat() <= stem <= until.isoformat()):
            continue
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*(\w+)\s*\|\s*(.*)$", line)
            if not m:
                continue
            day, kind, title = m.group(1), m.group(2).lower(), m.group(3).strip()
            if not (since.isoformat() <= day <= until.isoformat()):
                continue
            if kind in kinds:
                kinds[kind] += 1
            if kind == "repair" and "(mine)" in title:
                mine += 1
            if kind in titles and len(titles[kind]) < 6:
                titles[kind].append(title[:110])
    total = kinds["rebuild"] + kinds["repair"]
    return {
        "entries": kinds,
        "repairs_of_my_own_error": mine,
        "repair_share": round(kinds["repair"] / total, 3) if total else None,
        "examples": titles,
    }


def unsettled():
    """What the corpus has not answered. Private material dropped before it is counted."""
    d = _tool("tools/open_questions.py", ["--shareable", "--json"])
    if not d or "error" in d:
        return d
    pages = d.get("pages") or []
    return {
        "totals": d.get("totals"),
        "contradictions_open": len(d.get("contradictions") or []),
        "most_asked": [{"page": p.get("title"),
                        "questions": sum(len(s.get("items") or []) for s in p.get("sections") or []),
                        "first": next((it for s in (p.get("sections") or [])
                                       for it in (s.get("items") or [])), None)}
                       for p in sorted(pages, key=lambda x: -sum(
                           len(s.get("items") or []) for s in x.get("sections") or []))[:5]],
        "waiting_on_a_person": [{"page": p.get("title"),
                                 "who": sorted({w.get("who") for w in p.get("waits") or []})}
                                for p in pages if p.get("waits")][:5],
    }


def gather(year, month):
    since, until = month_window(year, month)
    material = {
        "month": f"{year}-{month:02d}",
        "label": f"{calendar.month_name[month]} {year}",
        "window": {"since": since.isoformat(), "until": until.isoformat()},
        "home": {"wiki": ROOT.name, "read_out": read_out(ROOT, since, until)},
        "commons": {},
        "federation": {},
    }
    for name, nodes in commons_cuts().items():
        material["commons"][name] = {
            "nodes_in_cut": len(nodes),
            "arrived_this_month": arrivals(nodes, since, until),
        }
        sib = ROOT.parent / name
        if sib.is_dir():
            material["commons"][name]["read_out"] = read_out(sib, since, until)

    # The signals. These are the point of the issue: what the corpus is thinking, what it has
    # not named, where it is moving, what is actually committed, and what it had to correct.
    # The counts above say how much arrived, which is the least surprising thing about a month.
    cuts = commons_cuts()
    material["signals"] = {
        "patterns": patterns_now(),
        "trajectory": trajectory(since, until),
        "goals": goal_vectors(cuts, since, until),
        "corrections": corrections(since, until),
        "unsettled": unsettled(),
    }

    # One honest federation-level number rather than a scoreboard.
    total = sum(sum(c["arrived_this_month"].values()) for c in material["commons"].values())
    material["federation"] = {
        "commons_read": list(material["commons"]),
        "pages_dated_this_month_across_the_commons": total,
    }
    return material


def render(m):
    w, out = m["window"], []
    out.append(f"newsletter material — {m['label']}  ({w['since']} to {w['until']})")
    out.append("")
    home = m["home"]["read_out"]
    if not home:
        out.append(f"  {m['home']['wiki']}: no learning_outcomes.py — nothing to gather")
    elif "error" in home:
        out.append(f"  {m['home']['wiki']}: could not read — {home['error'][0][:90]}")
    else:
        ent = home.get("entered", {})
        out.append(f"  {m['home']['wiki']}")
        out.append(f"     {ent.get('total', 0)} page(s) entered · "
                   f"{', '.join(f'{k} {v}' for k, v in (ent.get('by_type') or {}).items()) or '—'}")
        sub = [s for s in home.get("substance", []) if s.get("items")]
        out.append(f"     {len(sub)} section(s) with something in them, of "
                   f"{len(home.get('substance', []))}")
        sb, so = home.get("stood_behind", {}), home.get("still_open", {})
        out.append(f"     stood behind by a person: {len(sb.get('validations', []))} · "
                   f"claims checked: {sb.get('claims_verified', 0)} · "
                   f"unbacked goals: {so.get('unbacked_goals_total', 0)}")
    out.append("")
    for name, c in m["commons"].items():
        out.append(f"  {name} — {c['nodes_in_cut']} page(s) in the cut it shares")
        if c["arrived_this_month"]:
            for origin, n in c["arrived_this_month"].items():
                out.append(f"     {n:3d} dated this month, from {origin}")
        else:
            out.append("     nothing dated this month")
    out.append("")
    out.append(f"  {m['federation']['pages_dated_this_month_across_the_commons']} page(s) dated "
               f"this month across {len(m['commons'])} commons")
    out.append("")
    out += _render_signals(m.get("signals") or {})
    out.append("  This is material, not an issue. `newsletter` writes the issue from it —")
    out.append("  and a person reads that before it goes anywhere.")
    return "\n".join(out)


def _render_signals(s):
    """The half of the read-out that is about thinking rather than about volume."""
    out = []

    def missing(name, v):
        if v is None:
            out.append(f"  {name}: the tool for this is not in this wiki")
            return True
        if isinstance(v, dict) and "error" in v:
            out.append(f"  {name}: could not be read — {str(v['error'][0])[:70]}")
            return True
        return False

    p = s.get("patterns")
    if not missing("PATTERNS", p):
        scope = (p.get("corpus") or {}).get("commons") or {}
        out.append(f"  PATTERNS — {p['clusters']} cluster(s) hold together, "
                   f"{p['unnamed']} of them with no page saying what the idea is")
        out.append(f"     read across this wiki and {len(scope)} commons; "
                   f"{p['travelling_between_wikis']} cluster(s) span more than one wiki")
        for c in p.get("largest_unnamed", [])[:3]:
            out.append(f"     unnamed, {c['pages']} page(s), {c['distinct_sources']} source(s): "
                       f"{', '.join(c['tags'][:4])}")
    out.append("")

    tr = s.get("trajectory")
    if not missing("TRAJECTORY", tr):
        out.append(f"  TRAJECTORY — the corpus centre moved |V|={tr.get('magnitude')}")
        out.append(f"     rising:  {', '.join(tr.get('rising', [])[:8])}")
        out.append(f"     falling: {', '.join(tr.get('falling', [])[:8])}")
    out.append("")

    g = s.get("goals") or {}
    out.append("  GOALS AND COMMITMENTS")
    if not g:
        out.append("     no goal or commitment page in any commons this wiki reads")
    for name, v in g.items():
        out.append(f"     {name}: {v['goals']} goal(s), {v['commitments']} commitment(s), "
                   f"{v['goals_with_nothing_committed']} with nothing committed against them")
        out.append(f"        states: {v['commitment_states'] or 'none'} · "
                   f"stood behind by a person: {v['stood_behind_by_a_person']} of {v['goals']}")
        for mv in v["moved_this_month"][:4]:
            out.append(f"        moved this month: {mv['state']} — {str(mv['page'])[:60]}")
    out.append("")

    c = s.get("corrections")
    if not missing("CORRECTIONS", c):
        e = c["entries"]
        share = f"{round(c['repair_share'] * 100)}%" if c["repair_share"] is not None else "n/a"
        out.append(f"  CORRECTIONS — {e['rebuild']} advance(s), {e['repair']} repair(s), "
                   f"{share} of the work was putting something back")
        out.append(f"     {c['repairs_of_my_own_error']} of those repaired the model's own "
                   f"earlier error")
        for ex in c["examples"]["repair"][:3]:
            out.append(f"     repaired: {ex[:84]}")
    out.append("")

    u = s.get("unsettled")
    if not missing("UNSETTLED", u):
        tt = u.get("totals") or {}
        out.append(f"  UNSETTLED — {tt.get('items', 0)} question(s) written down across "
                   f"{tt.get('pages', 0)} page(s), {tt.get('waits', 0)} waiting on a person")
        for q in u.get("most_asked", [])[:3]:
            if q.get("first"):
                out.append(f"     {str(q['first'])[:88]}")
    out.append("")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gather a month's newsletter material.")
    ap.add_argument("--month", help="YYYY-MM; default is the last complete month")
    ap.add_argument("--json", action="store_true", help="emit the material as JSON")
    a = ap.parse_args(argv)
    if a.month:
        try:
            year, month = (int(x) for x in a.month.split("-"))
            month_window(year, month)
        except Exception:                          # noqa: BLE001
            print(f"not a month: {a.month!r} — expected YYYY-MM", file=sys.stderr)
            return 2
    else:
        year, month = last_complete_month()
    material = gather(year, month)
    print(json.dumps(material, indent=2) if a.json else render(material))
    return 0


if __name__ == "__main__":
    sys.exit(main())
