#!/usr/bin/env python3
"""weekly_digest.py — the week in one page, counted from the wiki's history, with no model.

The weekly rhythm in d.INO's human layer has three moments: questions on Monday, a digest on
Thursday, a reflection on Friday. On 2 November 2026 the roadmap set layers 1 to 3 working by the
end of the year, and nothing built the Thursday digest. This builds it from what the wiki already
records, so it costs nothing and runs in the wikis that hold no model key:

  * pages added this week, and pages whose BODY changed. A frontmatter-only edit is not news,
    the rule staleness.py uses for the same reason;
  * hunches added to design/lens/hunches.json, where the wiki has one;
  * commitments due in the next seven days, from the table the phone's reminders read;
  * the questions written on the pages that changed;
  * proposals waiting for a yes (waiting.py);
  * pages that moved this week and could go up to a commons that does not hold them yet
    (contribution_prompt.candidates, which applies contribute.eligible).

Sections with nothing in them are left out, and a week in which no page moved writes nothing.

VISIBILITY. In a commons the page is `internal`, and nothing on a `private` page is named: not
its title, its slug, its questions or its commitments. The test is `export.HIDE_FROM_SHARED`,
the set the colleague mirror strips. Copied text that links to a hidden page is dropped whole.
In a personal wiki the page is `private` and lists everything. CRM pages are left out
everywhere: a weekly list of who one has been in touch with is activity tracking, which the
house rules refuse.

Titles and copied text are written in quotation marks, never as [[links]]. A weekly page that
linked to everything that moved would make those pages look load-bearing to every tool that
ranks by inbound links.

    python3 tools/weekly_digest.py                                   # this week, to read
    python3 tools/weekly_digest.py --week-ending 2026-11-05 --write  # wiki/digest/2026-11-05.md
    python3 tools/weekly_digest.py --json
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import contribute  # noqa: E402
import contribution_prompt  # noqa: E402
import export  # noqa: E402
import open_questions  # noqa: E402
import staleness  # noqa: E402

ROOT = pathlib.Path(HERE).parent
WIKI = ROOT / "wiki"
OUT_DIR = WIKI / "digest"
SKIP_PREFIXES = ("index/", "log/", "digest/") + tuple(contribute.REFUSE_PATH_PREFIXES)
SKIP_SLUGS = {"index", "log"}
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
TITLE_PREFIX = "Weekly digest"
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
RAW_CITE = re.compile(r"\s*\(raw/[^)]*\)")


def git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def commit_before(day):
    """The newest commit made before midnight at the start of `day`, or '' if none."""
    return git("rev-list", "-1", f"--before={day.isoformat()} 00:00", "HEAD").strip()


def skipped(slug):
    return slug in SKIP_SLUGS or slug.startswith(SKIP_PREFIXES)


def shown(node, commons):
    """May this page be named here? Everything in a personal wiki; the shared cut in a commons."""
    if skipped(node["slug"]):
        return False
    return not commons or node.get("visibility", "private") not in export.HIDE_FROM_SHARED


def changed_pages(base, head):
    """{slug: 'added' | 'changed'} for pages whose body differs between two commits."""
    out = {}
    diff = git("diff", "--name-status", "-M", base or EMPTY_TREE, head, "--", "wiki/")
    for line in diff.splitlines():
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        if not path.endswith(".md") or status.startswith("D"):
            continue
        slug = path[len("wiki/"):-3]
        if skipped(slug):
            continue
        if status.startswith("A") or not base:
            out[slug] = "added"
            continue
        old = git("show", f"{base}:{parts[1]}")
        new = git("show", f"{head}:{path}")
        if staleness.body_of(old) != staleness.body_of(new):
            out[slug] = "changed"
    return out


def clean(text, visible_titles):
    """Copied text made safe to quote: no links, no citations, no inner quotes.

    None when it links to a page this digest may not name, so a hidden title cannot ride in on
    someone else's sentence.
    """
    for target in LINK.findall(text or ""):
        if export._norm_title(target).lower() not in visible_titles:
            return None
    text = LINK.sub(lambda m: m.group(1), text or "")
    text = RAW_CITE.sub("", text).replace('"', "'").replace("**", "")
    return " ".join(text.split())


def new_hunches(base, head, visible_titles):
    """Hunches whose id is new this week, kept only where their anchor page may be named."""
    def load(rev):
        try:
            got = json.loads(git("show", f"{rev}:design/lens/hunches.json") or "{}")
            return {h.get("id"): h for h in got.get("hunches", [])}
        except ValueError:
            return {}
    before = load(base) if base else {}
    out = []
    for hid, h in load(head).items():
        if hid in before or (h.get("anchor") or "").strip().lower() not in visible_titles:
            continue
        text = clean(h.get("hunch"), visible_titles)
        if text:
            out.append({"hunch": text, "serves": clean(h.get("serves"), visible_titles) or ""})
    return out


def due_date(cell, today):
    """2026-11-06, ~2026-11-06, 6 Nov or 6 November 2026, as the phone reads them. Else None."""
    words = cell.strip().lstrip("~").replace("·", " ").split()
    if not words:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", words[0]):
            return dt.date.fromisoformat(words[0])
        if len(words) < 2 or not words[0].isdigit():
            return None
        name = words[1].lower()
        month = next((i + 1 for i, m in enumerate(MONTHS)
                      if m == name or (len(name) == 3 and m.startswith(name))), None)
        if not month:
            return None
        if len(words) >= 3 and re.fullmatch(r"\d{4}", words[2]):
            return dt.date(int(words[2]), month, int(words[0]))
        # No year: the one that puts the date nearest today, as the phone does.
        options = []
        for y in (today.year - 1, today.year, today.year + 1):
            try:
                options.append(dt.date(y, month, int(words[0])))
            except ValueError:
                pass
        return min(options, key=lambda d: abs((d - today).days)) if options else None
    except ValueError:
        return None


def commitments_due(nodes, commons, start, visible_titles, days=7):
    """Rows of an 'open commitments' page whose Due date falls in [start, start + days)."""
    out = []
    for n in nodes.values():
        if "open commitments" not in (n.get("title") or "").lower() or not shown(n, commons):
            continue
        cols = None
        for line in (n.get("body") or "").splitlines():
            s = line.strip()
            if not s.startswith("|"):
                cols = None
                continue
            cells = [c.strip().replace("\0", "|") for c in s.replace("\\|", "\0").strip("|").split("|")]
            if cols is None:
                names = [c.lower() for c in cells]
                if "commitment" in names and "due" in names:
                    cols = (names.index("commitment"), names.index("due"))
                continue
            c, d = cols
            if max(c, d) >= len(cells) or cells[c].startswith("~~"):
                continue
            when = due_date(cells[d], start)
            if not when or not (start <= when < start + dt.timedelta(days=days)):
                continue
            bold = re.search(r"\*\*(.+?)\*\*", cells[c])
            text = clean(bold.group(1) if bold else cells[c], visible_titles)
            if text:
                out.append({"due": when.isoformat(), "commitment": text, "page": n["title"]})
    return sorted(out, key=lambda r: (r["due"], r["commitment"]))


def questions(slugs, nodes, commons, visible_titles, per_page=3, cap=10):
    """The questions written on the pages that changed this week.

    shortcut: first `per_page` items of the first `cap` pages, so a busy week stays one page;
    raise them if people ask for the full list.
    """
    out = []
    for slug in slugs:
        n = nodes.get(slug)
        path = WIKI / f"{slug}.md"
        if not n or not shown(n, commons) or not path.exists():
            continue
        page = open_questions.from_page(path) or {}
        items = [clean(it, visible_titles) for s in page.get("sections", []) for it in s["items"]]
        items = [it for it in items if it]
        if items:
            out.append({"page": n["title"], "items": items[:per_page],
                        "more": max(0, len(items) - per_page)})
    return out[:cap]


def proposals():
    """Open proposals, in waiting.py's plain words. None when GitHub cannot be asked."""
    try:
        import waiting
        slug = waiting.repo_slug()
        if not slug:
            return None
        return [p for p in waiting.open_proposals(slug) if not p["title"].startswith(TITLE_PREFIX)]
    except Exception:                                 # noqa: BLE001 — a section, not the page
        return None


def worth_sharing(moved_nodes, topo, top=5):
    """Per commons: pages that moved this week, may go up, and are not there yet.

    Only this week's pages, so the section changes from week to week. `held` is None when this
    run has no copy of the commons; that is said, never guessed.
    """
    pages = {n["slug"]: {"title": n["title"], "visibility": n.get("visibility", "private"),
                         "inbound": len(n.get("inbound_links") or [])} for n in moved_nodes}
    out = []
    for name in contribution_prompt.targets(topo):
        held = contribute.commons_titles(name)
        if held is None:
            out.append({"commons": name, "held_unknown": True, "pages": []})
            continue
        cands = contribution_prompt.candidates(pages, held)
        if cands:
            out.append({"commons": name, "held_unknown": False,
                        "pages": [c["title"] for c in cands[:top]], "more": max(0, len(cands) - top)})
    return out


def gather(week_ending, online=True):
    since = week_ending - dt.timedelta(days=6)
    head = commit_before(week_ending + dt.timedelta(days=1)) or "HEAD"
    base = commit_before(since)
    topo = contribute.topology()
    commons = topo.get("role") == "commons"
    nodes, _ = export.build_nodes(str(WIKI))
    visible_titles = {(n.get("title") or "").strip().lower()
                      for n in nodes.values() if shown(n, commons)}
    moved = changed_pages(base, head)
    rows = {"added": [], "changed": []}
    for slug, how in sorted(moved.items()):
        n = nodes.get(slug)
        if n and shown(n, commons):
            rows[how].append({"title": n["title"], "type": n.get("type") or "page",
                              "description": clean(n.get("description"), visible_titles) or ""})
    m = {"week_ending": week_ending.isoformat(), "since": since.isoformat(),
         "visibility": "internal" if commons else "private",
         "added": rows["added"], "changed": rows["changed"],
         "hunches": new_hunches(base, head, visible_titles),
         "commitments_due": commitments_due(nodes, commons, week_ending, visible_titles),
         "questions": questions(sorted(moved), nodes, commons, visible_titles)}
    m["quiet"] = not (m["added"] or m["changed"] or m["hunches"])
    # GitHub is asked only when there is a page to write, and never by the tests.
    m["proposals"] = proposals() if online and not m["quiet"] else None
    m["worth_sharing"] = worth_sharing([nodes[s] for s in sorted(moved) if s in nodes], topo)
    return m


def long_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1].capitalize()} {d.year}"


def render(m):
    span = f"{long_date(m['since'])} to {long_date(m['week_ending'])}"
    title = f"{TITLE_PREFIX}, week ending {long_date(m['week_ending'])}"
    out = ["---", "type: synthesis", f'title: "{title}"',
           f'description: "What changed in this wiki from {span}, counted from its history by a script with no model."',
           "tags: [digest, weekly-rhythm, d-ino]", "status: draft", f"visibility: {m['visibility']}",
           "confidence: high", "validation: machine", "derivation: derivative",
           f"timestamp: {m['week_ending']}", "sources: []", "---", "", f"# {title}", "",
           f"From {span}. Written by `tools/weekly_digest.py` from this wiki's history, with no model. "
           "It lists what moved and does not judge it."]
    if m["visibility"] == "internal":
        out.append("It names no private page.")
    out.append("")

    def section(heading, items):
        if items:
            out.extend([f"## {heading}", ""] + items + [""])

    def page_line(p):
        tail = f': "{p["description"]}"' if p["description"] else ""
        return f'- "{p["title"]}", {p["type"]}{tail}'

    section(f"New pages ({len(m['added'])})", [page_line(p) for p in m["added"]])
    section(f"Pages that changed ({len(m['changed'])})",
            [f'- "{p["title"]}", {p["type"]}' for p in m["changed"]])
    section(f"Hunches added ({len(m['hunches'])})",
            [f'- "{h["hunch"]}"' + (f' Serves: "{h["serves"]}".' if h["serves"] else "")
             for h in m["hunches"]])
    section("Commitments due in the next seven days",
            [f'- {long_date(c["due"])}: "{c["commitment"]}"' for c in m["commitments_due"]])
    q = []
    for p in m["questions"]:
        q.append(f'- On "{p["page"]}":')
        q += [f'    - "{it}"' for it in p["items"]]
        if p["more"]:
            q.append(f"    - and {p['more']} more on that page")
    section("Questions on the pages that changed", q)
    section("Waiting for a yes", [f'- [#{p["number"]}]({p["url"]}) "{clean(p["title"], set()) or "untitled"}": '
                                  f'{p["state"]}, opened {p["since"]}' for p in m["proposals"] or []])
    share = []
    for t in m["worth_sharing"] or []:
        if t["held_unknown"]:
            share.append(f"- To `{t['commons']}`: not checked, because this run had no copy of it.")
            continue
        more = f", and {t['more']} more" if t["more"] else ""
        share.append(f"- To `{t['commons']}`: " + ", ".join(f'"{x}"' for x in t["pages"]) + f"{more}.")
    section("Moved this week, and could go up", share)
    return "\n".join(out).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="This wiki's week, counted from its history.")
    ap.add_argument("--week-ending", help="YYYY-MM-DD, the last day of the week; default today")
    ap.add_argument("--json", action="store_true", help="the material as JSON")
    ap.add_argument("--write", action="store_true", help="write wiki/digest/<week-ending>.md")
    a = ap.parse_args(argv)
    try:
        week_ending = dt.date.fromisoformat(a.week_ending) if a.week_ending else dt.date.today()
    except ValueError:
        print(f"not a date: {a.week_ending!r}, expected YYYY-MM-DD", file=sys.stderr)
        return 2
    m = gather(week_ending)
    if a.json:
        print(json.dumps(m, indent=2))
        return 0
    if m["quiet"]:
        print(f"No page moved between {m['since']} and {m['week_ending']}: no digest written.")
        return 0
    page = render(m)
    if not a.write:
        print(page)
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{m['week_ending']}.md"
    path.write_text(page, encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
