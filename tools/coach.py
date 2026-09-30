#!/usr/bin/env python3
"""
coach.py — the one useful thing to suggest next, from what the wiki can actually see.

Asked for on 28 September 2026: "I want to make the wiki system more proactive." Most people using
these wikis do not know half of what they can do: that Claude can make a shareable page, which skills
their wiki carries, that a health check exists. The system already knew when something needed a
person, and only said so when asked.

The danger is the opposite failure. The recording-app plan names it: a fourth thing asking for
attention "would make all four easier to ignore." So this is built to be worth listening to:

  - Every suggestion comes from a signal in the wiki (a document never filed, an overview weeks
    behind), never from a template.
  - They are ranked, and the skill shows ONE at a time.
  - A healthy wiki gets a tip about something it can do, not an invented problem.
  - Anything the owner switches off stays off (`design/coach.json`, `{"off": ["lint", "tips"]}`).

Reads local files and git; for the waiting count in its own wiki it asks `waiting.py`, which
asks GitHub, and falls back to a local estimate when it cannot. No model, no writes.

  python3 tools/coach.py            # the top suggestion
  python3 tools/coach.py --all      # every current suggestion, ranked
  python3 tools/coach.py --json
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG_ENTRY = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s+([a-z-]+)\b", re.M)
PLACEHOLDER = ("_Replace this with", "_Not yet written._", "_Not yet written_")
NOT_REAL = {"overview.md", "axioms.md", "index.md", "log.md"}

# Tips, shown one at a time when nothing needs attention. `role` limits a tip to spokes or commons.
TIPS = [
    {"id": "tip-artifacts",
     "text": "Claude can turn anything here into a shareable web page, called an artifact: a summary for "
             "a colleague, a map, a one-pager for a meeting. It stays private to you until you share it, "
             "and updates at the same link.",
     "say": "Make this a shareable page."},
    {"id": "tip-ask",
     "text": "You can ask the wiki questions in plain words, and every answer shows where it came from.",
     "say": "What does the wiki say about ...?"},
    {"id": "tip-challenge",
     "text": "The wiki can argue with you: it builds the strongest case against a position you hold.",
     "say": "Challenge this."},
    {"id": "tip-think",
     "text": "Before you commit to a new idea, the wiki can ask you the hard questions about it first.",
     "say": "Help me think through this idea."},
    {"id": "tip-delta",
     "text": "Give the wiki someone else's paper and it will tell you where it agrees with what you "
             "already hold, where it goes further, and where it disagrees.",
     "say": "Run a delta on this."},
    {"id": "tip-brief",
     "text": "Coming back after a while? The wiki can tell you what changed while you were away.",
     "say": "Catch me up."},
    {"id": "tip-share", "role": "spoke",
     "text": "Pages you label for colleagues can be shared with your team wiki. Another member checks "
             "them before they go in.",
     "say": "What could I share with the team?"},
    {"id": "tip-google",
     "text": "The wiki can read a Google Doc or Sheet you point it at, and keep up with changes to it.",
     "say": "Read my Google sheet: <link>."},
    {"id": "tip-fix",
     "text": "Small fixes, like a typo or a date, you can make yourself on GitHub. EDITING.md shows how.",
     "say": "How do I fix a typo myself?"},
]


def _frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).split("#")[0].strip().strip('"').strip("'")
    return out


def _date(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _pages(root):
    wiki = root / "wiki"
    if not wiki.is_dir():
        return []
    out = []
    for p in sorted(wiki.rglob("*.md")):
        rel = p.relative_to(wiki)
        if rel.parts[0] in {"log", "index"}:
            continue
        out.append(p)
    return out


def _log_entries(root):
    texts = []
    for p in [root / "wiki" / "log.md", *sorted((root / "wiki" / "log").glob("*.md"))]:
        if p.exists():
            texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return [(d, kind) for d, kind in LOG_ENTRY.findall("\n".join(texts)) if _date(d)]


def _raw_files(root):
    raw = root / "raw"
    if not raw.is_dir():
        return []
    try:
        r = subprocess.run(["git", "ls-files", "raw"], cwd=root, capture_output=True, text=True, timeout=20)
        files = [f for f in r.stdout.split("\n") if f] if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError):
        files = None
    if files is None:
        files = [str(p.relative_to(root)) for p in raw.rglob("*") if p.is_file()]
    return [f for f in files if not pathlib.Path(f).name.lower().startswith(("readme", ".git"))]


DECIDES = re.compile(r"^decides:\s*\n((?:\s+-\s*.+\n?)+)", re.M)


def _decided(pages):
    """Branches a page has closed with `decides:`, the convention waiting.py already honours."""
    out = set()
    for p in pages:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---"):
            continue
        head = text[: text.find("\n---", 3) + 1]
        for block in DECIDES.findall(head):
            out |= {ln.split("-", 1)[1].strip().strip('"').strip("'") for ln in block.splitlines() if ln.strip()}
    return out


def _unmerged(root, pages=()):
    """Branches not merged into main, less the ones a page has deliberately closed."""
    try:
        r = subprocess.run(["git", "branch", "-r", "--no-merged", "origin/main"], cwd=root,
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return 0
    if r.returncode != 0:
        return 0
    decided = _decided(pages)
    names = [b.strip().replace("origin/", "", 1) for b in r.stdout.split("\n")
             if b.strip() and "->" not in b]
    return len([n for n in names if n not in decided and n != "export" and not n.startswith("google-sync/")])


def _waiting_count(root):
    """What `waiting.py` counts as waiting, or None where it cannot answer here.

    waiting.py is the authority on unsaved work: it asks GitHub which branches were proposed,
    merged or closed, and which a page has settled with `decides:`. The local count below cannot
    see closed proposals, so on 30 September it reported "4 waiting" beside waiting.py's
    "Nothing is waiting". It is only consulted for the wiki this file lives in, because
    waiting.py reads its own repository, and only when GitHub can be reached.
    """
    if pathlib.Path(root).resolve() != ROOT:
        return None
    try:
        import waiting
        slug = waiting.repo_slug()
        if not slug:
            return None
        found = waiting.never_proposed(slug)
        decided = waiting.decisions()
        return len(waiting.open_proposals(slug)) + len([r for r in found if not decided.get(r["branch"])])
    except Exception:  # no gh, no network, no permission: fall back to the local estimate
        return None


def _prefs(root):
    p = root / "design" / "coach.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except ValueError:
        return {}


def _role(root):
    try:
        return json.loads((root / "design" / "federation.json").read_text(encoding="utf-8")).get("role", "spoke")
    except (OSError, ValueError):
        return "spoke"


def _tip_applies(tip, role):
    return tip.get("role") in (None, role)


def tips(root, today, role="spoke"):
    """The applicable tips, rotated so a different one leads each day."""
    pool = [t for t in TIPS if _tip_applies(t, role)]
    k = today.toordinal() % len(pool)
    return [{**t, "priority": 10, "why": "Nothing here needs you; this is something the wiki can do."}
            for t in pool[k:] + pool[:k]]


def suggestions(root=ROOT, today=None, limit=3):
    """Current suggestions, most useful first. Each: id, priority, text, say, why, and a count if any."""
    root = pathlib.Path(root)
    today = today or datetime.date.today()
    prefs = _prefs(root)
    off = set(prefs.get("off", []))
    role = _role(root)
    pages = _pages(root)
    real = [p for p in pages if p.name not in NOT_REAL]
    metas = {p: _frontmatter(p.read_text(encoding="utf-8", errors="ignore")) for p in pages}
    out = []

    def add(sid, priority, text, say, why, count=None):
        if sid not in off:
            s = {"id": sid, "priority": priority, "text": text, "say": say, "why": why}
            if count is not None:
                s["count"] = count
            out.append(s)

    if len(real) < 3:
        add("first-documents", 100,
            "Your wiki is ready for its first documents. Paste a report, some notes or a link, and it "
            "will be summarised and connected.",
            "Please add this to the wiki.", f"{len(real)} page(s) besides the overview.")

    overview = root / "wiki" / "overview.md"
    if overview.exists():
        otext = overview.read_text(encoding="utf-8", errors="ignore")
        if any(ph in otext for ph in PLACEHOLDER):
            add("purpose", 90,
                "Your wiki doesn't yet say what it is for. One or two sentences in your own words helps "
                "every answer it gives.",
                "My wiki is for ... Please write that down as its purpose.",
                "The overview still carries the template's placeholder.")

    if len(real) >= 3:
        body = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in pages)
        unfiled = [f for f in _raw_files(root)
                   if f not in body and pathlib.Path(f).stem not in body]
        if unfiled:
            add("unfiled-sources", 80,
                f"{len(unfiled)} document(s) you added haven't been filed into the wiki yet, so questions "
                "can't draw on them.",
                "Ingest the documents that haven't been filed yet.",
                "Files in raw/ that no page cites.", count=len(unfiled))

    n, exact = _waiting_count(root), True
    if n is None:
        n, exact = _unmerged(root, pages), False
    if n:
        add("waiting", 70,
            (f"{n} piece(s) of work are waiting to be saved into your wiki." if exact else
             f"Up to {n} piece(s) of work may be waiting to be saved into your wiki."),
            "What's waiting for me?",
            "waiting.py's count." if exact else "Local estimate: branches not merged into main.", count=n)

    dates = [d for d in (_date(m.get("timestamp")) for p, m in metas.items() if p.name not in NOT_REAL) if d]
    newest = max(dates) if dates else None
    ov_date = _date(metas.get(overview, {}).get("timestamp")) if overview.exists() else None
    if len(real) >= 10 and newest and ov_date and (newest - ov_date).days > 14:
        add("overview", 50,
            f"Your overview is {(newest - ov_date).days} days behind what the wiki now holds.",
            "Update the overview.", f"Overview dated {ov_date}, newest page {newest}.")

    entries = _log_entries(root)
    lints = [_date(d) for d, k in entries if k == "lint"]
    last_lint = max(lints) if lints else None
    if len(real) >= 10 and (last_lint is None or (today - last_lint).days > 21):
        gap = f"{(today - last_lint).days} days" if last_lint else "never"
        add("lint", 40,
            "A health check finds what is out of date, what disagrees and what is missing. "
            f"The last one here: {gap}.",
            "Check the wiki.", f"Last lint entry: {last_lint or 'none'}.")

    validated = [m for m in metas.values() if m.get("validation") in ("self", "peer", "collective")]
    if len(real) >= 10 and not validated:
        add("stand-behind", 30,
            "No page here has a person's name behind it yet. Confirming the pages you agree with makes "
            "them count for more.",
            "What should I stand behind?", "No page carries validation: self, peer or collective.")

    last = max((_date(d) for d, _k in entries), default=None)
    if last and (today - last).days >= 7:
        add("catch-up", 20,
            f"It's been {(today - last).days} days since the wiki last recorded any work.",
            "Catch me up.", f"Last log entry: {last}.")

    if "tips" not in off:
        out += [t for t in tips(root, today, role) if t["id"] not in off][:1]

    out.sort(key=lambda s: -s["priority"])
    return out if limit is None else out[:limit]


def main(argv=None):
    ap = argparse.ArgumentParser(description="The next useful thing to suggest, from the wiki's own signals.")
    ap.add_argument("--all", action="store_true", help="every current suggestion, ranked")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(ROOT), help="the wiki to look at (default: this one)")
    args = ap.parse_args(argv)
    got = suggestions(root=args.root, limit=None if args.all else 1)
    if args.json:
        print(json.dumps(got, indent=2, ensure_ascii=False))
        return 0
    if not got:
        print("Nothing to suggest.")
        return 0
    for s in got:
        print(f"{s['text']}\n  Say: \"{s['say']}\"\n  (why: {s['why']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
