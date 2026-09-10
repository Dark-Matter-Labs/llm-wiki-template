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

## The shareable form

Gurden, 9 Sept evening: *"they should be easy and engaging to read — a format we can share with
people in Slack or email or a document; right now the page is too crude."* So the default output is
no longer a table. It is a short **brief**: a title, one paragraph that says what happened, four
short paragraphs with bold leads — what came in, what changed, who stood behind it, what did not
move — and one line on what the read-out cannot see. The numbers sit inside the sentences.

The same brief renders four ways, from the same computation, so the Slack message and the document
cannot disagree:

  --format text       plain prose, for email or a chat
  --format markdown   bold leads and a heading, for a wiki page or a doc
  --format slack      Slack's mrkdwn (*bold*, no headings), paste straight in
  --format html       a standalone styled page (xCO type), for sharing as a document
  --format table      the original tabular read-out, for checking the numbers
  --json              the data

`--out PATH` writes instead of printing. HTML defaults to `view/learning-outcomes.html`
(gitignored, like the goal view) and **refuses to write under `docs/` unless the audience is
`funder`**, because that directory is the open web and the internal shape names internal pages.

Usage:
  python3 tools/learning_outcomes.py                              # the brief, last 100 days, internal
  python3 tools/learning_outcomes.py --format slack --days 30     # paste into the weekly
  python3 tools/learning_outcomes.py --audience funder --format html --out view/lo-funder.html
  python3 tools/learning_outcomes.py --format table               # the numbers
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



OPT_CODE = re.compile(r"OPT-\d+")


def _detail(p: dict, max_len: int = 240) -> str:
    d = (p.get("description") or "").strip()
    if len(d) <= max_len:
        return d
    cut = d[:max_len]
    return cut[:cut.rfind(" ")] + "\u2026"


def _substance(entered, graph_pages, visible, name):
    """The content-shaped groups: what the work learned, in the corpus's own sentences.

    Rewritten 2026-09-10. The first version of this read-out reported the WIKI — pages entered,
    links added, positions changed — and Gurden was right that it told a funder nothing about
    xCO. Every page carries a one-sentence `description` written when the source was read; those
    are the product. Selection is by inbound links, so a section is the handful the corpus leans
    on rather than everything that moved.
    """
    def rank(xs, cap):
        ok = [x for x in xs if visible(x) and _detail(x)]
        ok.sort(key=lambda x: (-len(x.get("inbound_links") or []), x.get("title") or ""))
        return ([{"title": x["title"], "detail": _detail(x),
                  "weight": len(x.get("inbound_links") or [])} for x in ok[:cap]],
                max(0, len(ok) - cap))

    # The meta layer is about the WIKI, not the work: weekly reflections on how the thinking
    # moved, deltas measuring a document against the corpus, metacognition on the working loop.
    # All legitimate pages; none of them is what a funder or a colleague means by "what did xCO
    # learn". Excluding them here is the whole point of the 2026-09-10 rewrite — leaving them in
    # reintroduced the metadata through the front door. Joker challenges are NOT meta: they argue
    # against the subject matter, so they get a section of their own.
    def is_meta(x):
        sl = x.get("slug") or ""
        return (sl.startswith(("reflections/", "deltas/"))
                or "metacognition" in sl or sl.startswith("challenges/"))
    is_opt = lambda x: bool(OPT_CODE.search(f"{x.get('title','')} {x.get('description','')}"))
    by = lambda t: [x for x in entered if x.get("type") == t and not is_meta(x)]
    out = []

    def add(lead, note, xs, cap, empty):
        items, more = rank(xs, cap)
        out.append({"lead": lead, "note": note, "items": items, "more": more, "empty": empty})

    add("What we came to think",
        "Syntheses \u2014 the corpus's own attempts to say what a body of work adds up to.",
        by("synthesis"), 4,
        "No synthesis was written in this window. Material came in; nobody has yet said what it adds up to.")
    add("What moved in the portfolio",
        "Options and positions from the option book that gained or changed a page.",
        [x for x in entered if is_opt(x) and not is_meta(x)], 6,
        "No option page changed in this window.")
    add("What we now have language for",
        "Concepts named for the first time, ordered by how much of the corpus already leans on each.",
        by("concept"), 5, "No new concept was named.")
    add("Who and what came into view",
        "Organisations, people and places the work newly engages.",
        [x for x in by("entity") if not is_opt(x)], 5, "Nothing new came into view.")
    add("What the field told us", "Sources read in this window, and what each argues.",
        by("summary"), 5, "No source was read in this window.")
    add("What we argued against ourselves",
        "Counter-positions written deliberately against the corpus's own orthodoxy.",
        [x for x in entered if (x.get("slug") or "").startswith("challenges/")], 3,
        "Nobody argued the other side in this window.")

    changed = [x for x in graph_pages
               if (x.get("superseded_by") or x.get("devalued_by")) and x in entered and visible(x)]
    out.append({"lead": "What we stopped believing",
        "note": "Positions a person retired, and what replaced them. The old page stays readable; only the claim moves.",
        "items": [{"title": x["title"],
                   "detail": f"{'Superseded by' if x.get('superseded_by') else 'Downgraded by'} "
                             f"{x.get('superseded_by') or x.get('devalued_by')}. {_detail(x, 160)}",
                   "weight": len(x.get("inbound_links") or [])} for x in changed],
        "more": 0,
        "empty": "No position was retired in this window. Either what came in fitted what was "
                 "already held, or nobody has yet said otherwise."})

    thin = [x for x in graph_pages
            if x.get("confidence") == "low" and len(x.get("inbound_links") or []) >= 6]
    items, more = rank(thin, 5)
    out.append({"lead": "Where we are least sure",
        "note": "Pages the argument leans on hardest whose own evidence is weakest. Named because "
                "a read-out that omits them is a brochure.",
        "items": items, "more": more,
        "empty": "Nothing load-bearing is currently marked low-confidence."})
    return out


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
        "substance": _substance(entered, graph_pages=pages, visible=visible, name=name),
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


def _n(n: int, one: str, many: str | None = None) -> str:
    """'1 source' / '4 sources' — the plural is the one thing prose cannot get wrong."""
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def wiki_name() -> str:
    """This wiki's name from its git remote — a commons reads 'the xCO commons', a spoke its own name."""
    out = git("remote", "get-url", "origin").strip()
    name = out.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git") if out else "this wiki"
    return {"xco-team-wiki": "the xCO commons", "learning-system-wiki": "the learning-system commons",
            "power-project-wiki": "the power-project commons"}.get(name, name)


def narrative(v: dict, who: str | None = None) -> dict:
    """The brief, as parts, for every format to lay out.

    Rewritten 2026-09-10 around CONTENT. Gurden: *"they should show insights and learnings coming
    from contents of the wiki, and not metadata about the wiki. The funders and DM team want to
    learn about the xCO work; the wiki is just a tool in the middle."* So each section is a
    handful of pages with the one-sentence description written when the source was read, and the
    page counts moved to `assembly` at the end — kept, because a reader deciding whether to trust
    the brief deserves them, but no longer the first thing anyone reads.
    """
    who = who or wiki_name()
    w, e, s_, o = v["window"], v["entered"], v["stood_behind"], v["still_open"]
    since, until = _fmt_date(w["since"]), _fmt_date(w["until"])
    sections = list(v["substance"])

    # goals belong with the work, not the tooling
    sections.append({
        "lead": "What is aimed at but unresourced",
        "note": "Goals with no commitment of people or money against them.",
        "items": [{"title": g, "detail": "", "weight": 0} for g in o["unbacked_goals"] if g],
        "more": 0,
        "empty": "Every goal has something committed against it."})

    counts = {x["lead"]: len(x["items"]) for x in sections}
    parts = []
    for lead, word, plural in (("What the field told us", "source", "sources"),
                               ("What moved in the portfolio", "option in the book touched", "options in the book touched"),
                               ("What we now have language for", "concept named", "concepts named"),
                               ("What we came to think", "synthesis written", "syntheses written")):
        k = counts.get(lead, 0)
        if k:
            parts.append(f"{k} {word if k == 1 else plural}")
    themes = [("AI" if f["tag"] == "ai" else f["tag"]) for f in e["fields"][:4]]
    if parts:
        lede = (f"Between {since} and {until}, {who} took in {_join(parts)}"
                + (f", mostly around {_join(themes)}" if themes else "")
                + ". What follows is what that amounted to, in the corpus's own words.")
    elif e.get("not_shown_to_this_audience"):
        # An empty funder brief beside a full internal one does not mean nothing happened. Saying
        # only "nothing entered" would let a reader conclude xCO was idle, which is false and the
        # most damaging thing this read-out could do. Name the boundary instead.
        lede = (f"Between {since} and {until}, "
                f"{_n(e['not_shown_to_this_audience'], 'page')} entered {who} and none of "
                f"{'it is' if e['not_shown_to_this_audience'] == 1 else 'them are'} public or "
                f"unlisted \u2014 so this shape has nothing to show. That is a fact about what "
                f"has been opened up, not about what was done. The internal shape of this same "
                f"brief is not empty.")
    else:
        lede = (f"Between {since} and {until}, nothing new entered {who}. "
                f"That is itself a reading of the period.")

    caveat = ("Every line above is a page's own one-sentence description, written when the source "
              "was read \u2014 not a summary generated for this brief. "
              + ("Internal pages are named; private pages are never named."
                 if v["audience"] == "internal" else
                 "Only public and unlisted material is named; internal working pages are excluded, "
                 "and private pages are never named."))

    assembly = [("pages dated in the window", str(e["total"])),
                ("not shown to this audience", str(e.get("not_shown_to_this_audience", 0))),
                ("validated by a person", str(len(s_["validations"]))),
                ("claims checked against a source", str(s_["claims_verified"])),
                ("contradictions still open", str(o["contradictions"]))]

    return {"title": f"What {who} learned \u2014 {since} to {until}",
            "lede": lede, "sections": sections, "caveat": caveat, "assembly": assembly}


def _fmt_date(iso: str) -> str:
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def _numbers(v: dict) -> list[tuple[str, str]]:
    e, m, s, o = v["entered"], v["moved"], v["stood_behind"], v["still_open"]
    return [("pages entered", str(e["total"])),
            ("sources read", str(e["by_type"].get("summary", 0))),
            ("positions changed", str(len(m["contradictions_declared"]) + len(m["positions_closed"]) + len(m["axioms"]))),
            ("stood behind by a person", str(len(s["validations"]) + s["claims_verified"])),
            ("goals with nothing committed", str(o["unbacked_goals_total"]))]


def _lay(n: dict, bold, bullet: str) -> str:
    out = [bold(n["title"]), "", n["lede"], ""]
    for sec in n["sections"]:
        out.append(bold(sec["lead"]))
        if not sec["items"]:
            out.append(f"  {sec['empty']}")
        else:
            for i in sec["items"]:
                out.append(f"  {bullet} {i['title']}" + (f" \u2014 {i['detail']}" if i["detail"] else ""))
            if sec["more"]:
                out.append(f"  {bullet} \u2026 and {sec['more']} more")
        out.append("")
    out.append(n["caveat"])
    return "\n".join(out)


def render_text(v: dict) -> str:
    return _lay(narrative(v), lambda x: x, "-")


def render_markdown(v: dict) -> str:
    n = narrative(v)
    out = [f"### {n['title']}", "", n["lede"], ""]
    for sec in n["sections"]:
        out += [f"**{sec['lead']}**", ""]
        if not sec["items"]:
            out.append(f"- _{sec['empty']}_")
        else:
            for i in sec["items"]:
                out.append(f"- **{i['title']}**" + (f" \u2014 {i['detail']}" if i["detail"] else ""))
            if sec["more"]:
                out.append(f"- _\u2026 and {sec['more']} more_")
        out.append("")
    out.append(f"_{n['caveat']}_")
    return "\n".join(out)


def render_slack(v: dict) -> str:
    """Slack mrkdwn: *bold*, no headings, no nested markup."""
    return _lay(narrative(v), lambda x: f"*{x}*", "\u2022")


def render_html(v: dict) -> str:
    """A standalone page in the xCO type that survives being emailed. Light and dark, no script."""
    import html as _h
    n = narrative(v)
    secs = ""
    for sec in n["sections"]:
        body = ("<p class=\"empty\">" + _h.escape(sec["empty"]) + "</p>" if not sec["items"]
                else "<ul>" + "".join(
                    f"<li><b>{_h.escape(i['title'])}</b>"
                    + (f" \u2014 {_h.escape(i['detail'])}" if i["detail"] else "") + "</li>"
                    for i in sec["items"])
                + (f"<li class=\"more\">\u2026 and {sec['more']} more</li>" if sec["more"] else "")
                + "</ul>")
        secs += (f"<section><h2>{_h.escape(sec['lead'])}</h2>"
                 f"<p class=\"note\">{_h.escape(sec['note'])}</p>{body}</section>")
    asm = " \u00b7 ".join(f"{_h.escape(val)} {_h.escape(k)}" for k, val in n["assembly"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_h.escape(n['title'])}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=Inter:wght@400;500&display=swap">
<style>
:root{{--bg:#f6f4ee;--ink:#1f1e1b;--muted:#5d5a52;--faint:#8a877d;--line:rgba(31,30,27,.14)}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1d1d1b;--ink:#efece4;--muted:#b8b4aa;--faint:#7e7b72;--line:rgba(239,236,228,.14)}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 'Crimson Pro',Georgia,serif}}
main{{max-width:42rem;margin:0 auto;padding:3.5rem 1.5rem 4rem}}
.eyebrow{{font:500 11px/1 'Inter',system-ui,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}}
h1{{font-weight:400;font-size:2rem;line-height:1.15;letter-spacing:-.01em;margin:.6rem 0 1.2rem}}
h2{{font-weight:400;font-size:1.35rem;margin:2.4rem 0 .2rem}}
.lede{{font-size:1.15rem;line-height:1.55}}
.note{{font:400 13px/1.5 'Inter',system-ui,sans-serif;color:var(--muted);margin:.2rem 0 .9rem}}
ul{{list-style:none;padding:0;margin:0}}
li{{border-left:2px solid var(--line);padding:0 0 0 1rem;margin:0 0 .9rem}}
li b{{font-family:'Inter',system-ui,sans-serif;font-size:15px;font-weight:500}}
.empty{{border-left:2px solid var(--line);padding-left:1rem;color:var(--muted)}}
.more,.caveat{{font:400 13px/1.5 'Inter',system-ui,sans-serif;color:var(--faint)}}
.caveat{{margin-top:2.4rem;padding-top:1rem;border-top:1px solid var(--line);color:var(--muted)}}
.asm{{margin-top:.6rem;font:400 12px/1.5 'Inter',system-ui,sans-serif;color:var(--faint)}}
</style></head><body><main>
<div class="eyebrow">Learning outcomes \u00b7 {_h.escape(v['audience'])} shape</div>
<h1>{_h.escape(n['title'])}</h1>
<p class="lede">{_h.escape(n['lede'])}</p>
{secs}
<p class="caveat">{_h.escape(n['caveat'])}</p>
<p class="asm">How this was assembled: {asm}.</p>
</main></body></html>
"""


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
    ap.add_argument("--format", choices=("text", "markdown", "slack", "html", "table"), default="text")
    ap.add_argument("--out", metavar="PATH", help="write here instead of printing (html defaults to view/learning-outcomes.html)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    until = datetime.date.fromisoformat(args.until) if args.until else datetime.date.today()
    since = datetime.date.fromisoformat(args.since) if args.since else until - datetime.timedelta(days=args.days)
    if not WIKI.is_dir():
        print("no wiki/ directory — run from the repo root", file=sys.stderr)
        return 2
    v = build(since, until, args.audience)
    if args.json:
        print(json.dumps(v, indent=1, ensure_ascii=False))
        return 0
    text = {"text": render_text, "markdown": render_markdown, "slack": render_slack,
            "html": render_html, "table": render}[args.format](v)
    out = args.out or ("view/learning-outcomes.html" if args.format == "html" else None)
    if not out:
        print(text)
        return 0
    dest = (ROOT / out).resolve()
    # docs/ is served to the open web. The internal shape names internal pages; it does not go there.
    if args.audience != "funder" and (ROOT / "docs") in dest.parents:
        print(f"refusing to write the {args.audience} shape under docs/ — that directory is the open web. "
              f"Use --audience funder, or another --out.", file=sys.stderr)
        return 2
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    print(f"wrote {dest.relative_to(ROOT)} ({len(text):,} chars, {args.format}, {args.audience})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
