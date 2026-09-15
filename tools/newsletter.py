#!/usr/bin/env python3
"""newsletter.py — the month's material, gathered across this wiki and the commons it reads.

This is the cheap half of the monthly newsletter, and the split is the whole design.

**Why the weekly reflection is being replaced.** It ran every Friday, called the Claude API on
each run — billed outside the Team plan — and produced eight reflections between weeks 28 and 36.
Measured on 2026-09-15, across that whole run:

    inbound links to any reflection, from anywhere in the corpus    0
    times W35 and W36 were touched after being written              1 each
    times W30 was touched after being written                       4
    workflow runs                                                  15
    of which failed                                                 5   (33%)

Attention decayed from four touches to one, nothing ever cited a reflection, and the most recent
run — 11 September — failed with nobody noticing. A weekly artefact nobody reads is not a
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
    out.append("  This is material, not an issue. `newsletter` writes the issue from it —")
    out.append("  and a person reads that before it goes anywhere.")
    return "\n".join(out)


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
