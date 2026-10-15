#!/usr/bin/env python3
"""
needs_you.py — what in this wiki needs its owner, in their words, each with one thing to do.

## Why this exists

Asked for on 12 October 2026, for the app: "see what needs his attention and say yes to it". The
wiki already knows each kind of item, scattered across six tools a person would have to know about:
proposals waiting (`waiting.py`), contradictions open (`contradictions.py`), quotes not found in
their source (`quote_check.py`), suggestions (`coach.py`), pages nobody has stood behind, and an
overview fallen behind its pages. This puts them in one ordered list a view can show as cards.

## The rules it keeps

- **A yes only where a yes is safe.** A proposed change is offered "Save it into your wiki" only
  when its checks have passed. One a check objects to is shown with "Look first"; one still being
  checked shows "Wait". A draft is not shown. The app re-checks before it saves, as rollout.py does.
- **Plain words.** No item says branch, merge, commit or pull request. `talking.md` is the standard.
- **About the wiki, never about people.** No item names who wrote what (knowledge, not surveillance).
- **It reads; it never acts.** Every action is carried out by the app, as the signed-in person, and
  a yes goes through GitHub's own rules.

    python3 tools/needs_you.py            # the list, for a person
    python3 tools/needs_you.py --json     # the list, for the app
    python3 tools/needs_you.py --root ../leon-llm-wiki --no-network
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OVERVIEW_BEHIND = 5        # fewer new pages than this is not yet worth a person's time
ORDER = {"proposal": 0, "contradiction": 1, "stand_behind": 2,           # say yes
         "broken": 3, "waits": 4, "questions": 5,                            # concerns
         "clash": 6, "followups": 6.5, "quotes": 7, "overview": 8, "never_proposed": 9, "suggestion": 10}   # to do
GROUP = {"proposal": "yes", "contradiction": "yes", "stand_behind": "yes",
         "broken": "concern", "waits": "concern", "questions": "concern",
         "clash": "todo", "followups": "todo", "quotes": "todo", "overview": "todo", "never_proposed": "todo", "suggestion": "todo"}


def _n(count: int, one: str, many: str) -> str:
    """'1 page', '2 pages': counts read as a person writes them, never 'page(s)'."""
    return f"{count} {one if count == 1 else many}"


def _lead(item: str) -> str:
    """An open question's headline: its bold opening if it has one, else its first short sentence."""
    m = re.match(r"\s*\*\*(.+?)\*\*", item)
    if m:
        return _plain(m.group(1))
    first = re.split(r"(?<=[.?!])\s", _plain(item), maxsplit=1)[0]
    return first if len(first) <= 90 else ""


def _plain(line: str) -> str:
    """A line from a page, as plain words: no bold, italics or links."""
    line = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), line)
    return " ".join(re.sub(r"[*_`]", "", line).split())


def _concerns(open_questions: dict | None, checks_failing: bool | None) -> list[dict]:
    out = []
    if checks_failing:
        out.append({"kind": "broken", "ref": "checks",
                    "title": "Your wiki's automatic checks are failing",
                    "why": "Until they pass, nothing new can be saved into the wiki safely.",
                    "action": {"type": "ask", "label": "Find out why, and fix it",
                               "say": "The automatic checks are failing. Find out why and fix it."}})
    oq = open_questions or {}
    waits = [w for p in oq.get("pages", []) for w in p.get("waits", [])]
    if waits:
        who = sorted({w.get("who", "someone") for w in waits})
        out.append({"kind": "waits", "ref": "waits",
                    "title": f"{_n(len(waits), 'thing', 'things')} in your pages {'waits' if len(waits) == 1 else 'wait'} on someone",
                    "why": f"Waiting on {', '.join(who)}. For example: {_plain(waits[0].get('line', ''))[:140]}",
                    "action": {"type": "ask", "label": "See what's waiting on whom",
                               "say": "Which of my pages are waiting on someone, and on whom?"}})
    total = (oq.get("totals") or {}).get("items", 0)
    if total:
        leads = [_lead(i) for p in oq.get("pages", []) for sec in p.get("sections", []) for i in sec.get("items", [])]
        firsts = [l for l in leads if l.endswith("?")][:3]
        out.append({"kind": "questions", "ref": "questions",
                    "title": f"{_n(total, 'open question', 'open questions')} across "
                             f"{_n((oq.get('totals') or {}).get('pages', 0), 'page', 'pages')}",
                    "why": ("Among them: " + " ".join(firsts)) if firsts else "Questions your pages say are still open.",
                    "action": {"type": "ask", "label": "Pick one to work on",
                               "say": "What don't we know? Help me pick one open question to work on."}})
    return out


# ---------------------------------------------------------------- the list (tested)

def _proposal(p: dict) -> dict | None:
    state = p.get("state", "")
    if state.startswith("a draft"):
        return None
    if state == "checked and ready":
        action = {"type": "yes", "label": "Save it into your wiki", "target": p.get("url")}
    elif state.startswith("clashes"):
        # GitHub cannot save it as it stands, so a yes would lead to a greyed-out button.
        return {"kind": "clash", "ref": p.get("number"), "title": p.get("title", "A proposed change"),
                "why": "It clashes with work saved since it was written, so it can't be saved as it is.",
                "action": {"type": "ask", "label": "Bring it up to date",
                           "say": f"My proposed change “{p.get('title', '')}” (#{p.get('number')}) clashes with work "
                                  "saved since. Bring it up to date so I can save it, and tell me if anything needs my decision."}}
    elif state.startswith("a check says"):
        action = {"type": "look", "label": "Look first: a check found a problem", "target": p.get("url")}
    else:
        action = {"type": "wait", "label": "Still being checked", "target": p.get("url")}
    return {"kind": "proposal", "ref": p.get("number"),
            "title": p.get("title", "A proposed change"),
            "why": p.get("summary") or f"Waiting since {p.get('since', 'recently')}.",
            "action": action}


def _followups(c: dict | None) -> list[dict]:
    """Counts only, from tools/crm.py counts: this page is published (locked), and a CRM name
    must never reach it, so the card says how many and the person asks Claude for who."""
    if not c:
        return []
    due = c.get("overdue", 0) + c.get("due_soon", 0)
    if due:
        late = f", {c['overdue']} of them overdue" if c.get("overdue") else ""
        title = f"{_n(due, 'follow-up is', 'follow-ups are')} due this week{late}"
    elif c.get("no_next_step"):
        title = f"{_n(c['no_next_step'], 'open relationship has', 'open relationships have')} no next step"
    else:
        return []
    return [{"kind": "followups", "ref": "followups", "title": title,
             "why": "Names stay in your wiki; this page only counts them.",
             "action": {"type": "ask", "label": "See who, with Claude", "say": "What follow-ups are due?"}}]


def build_items(waiting: dict, coach: list, contradictions: list, overview: dict,
                quotes_not_in_source: int, descriptions: dict,
                open_questions: dict | None = None, checks_failing: bool | None = None,
                followups: dict | None = None) -> list[dict]:
    items: list[dict] = _concerns(open_questions, checks_failing)
    items += _followups(followups)
    for p in (waiting or {}).get("proposals", []):
        item = _proposal(p)
        if item:
            items.append(item)

    for newer, older in contradictions:
        items.append({
            "kind": "contradiction", "ref": newer,
            "title": f"Two pages disagree: “{newer}” and “{older}”",
            "why": "They say different things about the same subject. Only a person decides which one wins; "
                   "the other stays readable, pointing to the winner.",
            "action": {"type": "decide", "label": "Choose which one wins",
                       "pages": [{"title": t, "says": descriptions.get(t, "")} for t in (newer, older)]},
        })

    if quotes_not_in_source:
        items.append({
            "kind": "quotes", "ref": "quotes",
            "title": f"{_n(quotes_not_in_source, 'quote is', 'quotes are')} not in the source they cite",
            "why": "Words in quotation marks should be the source's own. Each needs its wording fixed, "
                   "the right source named, or the quotation marks removed.",
            "action": {"type": "ask", "label": "Ask Claude to propose fixes",
                       "say": "Fix the quotes that are not in their cited source."},
        })

    if (overview or {}).get("behind", 0) >= OVERVIEW_BEHIND:
        items.append({
            "kind": "overview", "ref": "overview",
            "title": f"Your overview is {overview['behind']} pages behind",
            "why": f"Pages have arrived since it was last updated on {overview.get('since')}, so the "
                   "summary of your work no longer covers them.",
            "action": {"type": "ask", "label": "Ask for an updated overview",
                       "say": "Bring the overview up to date with the pages added since it last changed."},
        })

    unproposed = (waiting or {}).get("never_proposed") or []
    if unproposed:
        items.append({
            "kind": "never_proposed", "ref": "never_proposed",
            "title": f"{_n(len(unproposed), 'piece of work was', 'pieces of work were')} written and never put forward",
            "why": "They exist only outside the wiki. Old work is not always wanted work; a look decides.",
            "action": {"type": "ask", "label": "Ask what is in them", "say": "What's waiting for me?"},
        })

    # A suggestion that repeats an item already listed would say the same thing twice.
    covered = {"waiting": any(i["kind"] in ("proposal", "never_proposed") for i in items),
               "overview": any(i["kind"] == "overview" for i in items)}
    for s in coach or []:
        if covered.get(s.get("id")):
            continue
        items.append({
            "kind": "suggestion", "ref": s.get("id"),
            "title": s.get("text", ""),
            # The coach's own "why" is written for maintainers ("Files in raw/ that no page cites").
            # Its "text" already says it plainly, so the card carries that alone.
            "why": "",
            "action": {"type": "ask", "label": "Do this with Claude", "say": s.get("say", "")},
        })

    sb = (waiting or {}).get("stand_behind") or {}
    pages = sb.get("pages") or []
    if sb.get("available") and pages:
        top = pages[0]
        items.append({
            "kind": "stand_behind", "ref": top.get("title"),
            "title": f"Stand behind “{top.get('title')}”?",
            "why": f"{top.get('leaned_on_by', 0)} other pages lean on it, and nobody has confirmed it yet. "
                   f"{sb.get('total_unvalidated', 0)} pages here are waiting for someone to stand behind them.",
            "action": {"type": "confirm", "label": "Read it and confirm it", "page": top.get("title")},
        })

    for i in items:
        i["group"] = GROUP.get(i["kind"], "todo")
        # Other tools write "3 document(s)"; a card says "3 documents".
        i["title"] = re.sub(r"\b(\d+) (\w+)\(s\)", lambda m: m.group(1) + " " + m.group(2) + ("" if m.group(1) == "1" else "s"), i["title"])
    return sorted(items, key=lambda i: ORDER.get(i["kind"], 99))


# ---------------------------------------------------------------- gathering (reads the wiki)

def _run_json(root: pathlib.Path, args: list[str]):
    p = subprocess.run([sys.executable, *args], cwd=root, capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1) if m else "").split("\n"):
        f = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if f:
            out[f.group(1)] = f.group(2).strip().strip("\"'")
    return out


def _descriptions(root: pathlib.Path) -> dict:
    out = {}
    for p in (root / "wiki").rglob("*.md"):
        fm = _frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        if fm.get("title"):
            out[fm["title"]] = fm.get("description", "")
    return out


def _contradictions(root: pathlib.Path) -> list:
    code = ("import json,sys; sys.path.insert(0,'tools'); import contradictions as c; "
            "o,_,_ = c.analyse(c.load('wiki')); print(json.dumps(o))")
    p = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)
    try:
        return [tuple(x) for x in json.loads(p.stdout)]
    except ValueError:
        return []


def _overview(root: pathlib.Path) -> dict:
    git = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True).stdout.strip()
    last = git("log", "-1", "--format=%H %ad", "--date=short", "--", "wiki/overview.md").split()
    if len(last) < 2:
        return {}
    added = git("log", f"{last[0]}..HEAD", "--diff-filter=A", "--name-only", "--format=", "--", "wiki/")
    pages = [l for l in added.splitlines() if l.endswith(".md") and not re.match(r"wiki/(index|log)", l)]
    return {"behind": len(pages), "since": last[1]}


def _summary(url: str) -> str:
    """The proposal's own first paragraph, as plain text: it is written to lead with what was learned."""
    p = subprocess.run(["gh", "pr", "view", url, "--json", "body", "-q", ".body"], capture_output=True, text=True)
    para = next((b for b in re.split(r"\n\s*\n", p.stdout.strip()) if b and not b.startswith(("#", "🤖"))), "")
    para = re.sub(r"^\s*[-*]\s+", "", para, flags=re.M)
    para = re.sub(r"([.!?:;])\n", r"\1 ", para).replace("\n", "; ")
    para = re.sub(r"[*_`]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", para)
    text = " ".join(para.split())
    if len(text) <= 280:
        return text
    cut = text[:280].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def gather(root: pathlib.Path, network: bool = True) -> list[dict]:
    waiting = _run_json(root, ["tools/waiting.py", "--json"]) if network else {}
    waiting = waiting or {}
    if network:
        for p in waiting.get("proposals", []):
            p["summary"] = _summary(p["url"])
    quotes = _run_json(root, ["tools/quote_check.py", "--json"]) or []
    missing = sum(1 for q in quotes if q.get("verdict") == "not-found")
    return build_items(waiting=waiting, coach=_run_json(root, ["tools/coach.py", "--json"]) or [],
                       contradictions=_contradictions(root), overview=_overview(root),
                       quotes_not_in_source=missing, descriptions=_descriptions(root),
                       open_questions=_run_json(root, ["tools/open_questions.py", "--json"]) or {},
                       followups=_run_json(root, ["tools/crm.py", "counts", "--json"]) if (root / "tools" / "crm.py").exists() and (root / "wiki" / "crm").is_dir() else None,
                       checks_failing=_checks_failing(root) if network else None)


def _checks_failing(root: pathlib.Path) -> bool | None:
    """Whether the latest automatic checks on the saved version failed. None when GitHub can't say."""
    p = subprocess.run(["gh", "run", "list", "--branch", "main", "--workflow", "Wiki checks", "--limit", "1",
                        "--json", "conclusion", "-q", ".[0].conclusion"], cwd=root, capture_output=True, text=True)
    return None if p.returncode else p.stdout.strip() == "failure"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="What in this wiki needs its owner, each with one thing to do.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--no-network", action="store_true", help="skip proposals, which need GitHub")
    a = ap.parse_args(argv)
    items = gather(pathlib.Path(a.root), network=not a.no_network)
    if a.json:
        print(json.dumps({"wiki": pathlib.Path(a.root).resolve().name, "items": items}, indent=2, ensure_ascii=False))
        return 0
    if not items:
        print("Nothing needs you right now.")
    for i in items:
        print(f"• {i['title']}\n    {i['why']}\n    → {i['action']['label']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
