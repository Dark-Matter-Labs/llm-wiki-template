#!/usr/bin/env python3
"""crm.py — follow-ups, one-line logging and lead finding for the private CRM in wiki/crm/.

Built on 15 October 2026, after an audit found the CRM's fields were there and nothing read them:
in this wiki all 17 cards had no owner, no last-contact date and no next step, every stage was a
seeded default, and no tool listed what was due. A field nobody reads is a field nobody fills.

    python3 tools/crm.py due [--within 7] [--json]       what is overdue, due soon, or has no next step
    python3 tools/crm.py counts --json                  the same as numbers only (for the Needs-you page)
    python3 tools/crm.py log CARD --kind meeting --note "what happened" \\
        [--date YYYY-MM-DD] [--next "the next step" --due YYYY-MM-DD --why "the reason"] \\
        [--stage active] [--owner "Name"]
    python3 tools/crm.py leads [--top 12] [--json]       organisations the wiki knows with no card yet
    python3 tools/crm.py not-a-lead "Page title"         mark a page as this wiki's own work, never a lead

Rules it keeps (from the crm skill):
- It never contacts anyone and drafts nothing to send.
- It never invents relationship state: a field is set only when the person says so.
- `counts` returns numbers only, never a name, because the Needs-you page is published (locked).
- Every card stays `visibility: private`; this tool refuses to write one that is not.
- In a shared wiki (a commons) it logs nothing and finds no leads: contacts live in a personal wiki.
  The tool travels to every wiki with the shared layer, so the rule is kept in code, not by omission.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

STAGES = {"unset", "prospect", "active", "dormant", "committed", "closed"}
KINDS = {"meeting", "call", "email", "message", "event", "note"}
OPEN_STAGES = {"prospect", "active", "committed"}    # stages where a next step is expected
QUIET_DAYS = 90                                       # no contact for this long, while open, is "gone quiet"
SKIP_FILES = {"index.md", "log.md"}
SKIP_DIRS = {"index", "log"}
OURS_TAGS = {"dark-matter-labs", "xco"}
PLACE_TAGS = {"place", "geography"}
OWN_WORK = pathlib.Path("design") / "crm.json"   # this wiki's own work: {"own_work": [titles], "own_work_tags": [tags]}
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


# ---------------------------------------------------------------- reading

def is_commons(root: pathlib.Path) -> bool:
    try:
        return json.loads((root / "design" / "federation.json").read_text(encoding="utf-8")).get("role") == "commons"
    except (OSError, ValueError):
        return False


COMMONS_REFUSAL = ("crm: this is a shared wiki, and contacts never live in one. "
                   "Log relationships and find leads in your personal wiki.")


def frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter, body); empty frontmatter when there is none."""
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    return (parts[1], parts[2]) if len(parts) >= 3 else ("", text)


def field(fm: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+?)\s*$", fm, re.M)
    return m.group(1).split("#")[0].strip().strip('"') if m else ""


def tags_of(fm: str) -> set[str]:
    m = re.search(r"^tags:\s*\[(.*?)\]", fm, re.M)
    return {t.strip().strip('"').lower() for t in m.group(1).split(",") if t.strip()} if m else set()


def as_date(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def cards(root: pathlib.Path) -> list[dict]:
    out = []
    for kind in ("contacts", "accounts"):
        for p in sorted((root / "wiki" / "crm" / kind).glob("*.md")):
            fm, body = frontmatter(p.read_text(encoding="utf-8"))
            nxt = field(fm, "next_action") or "unset"
            due = as_date(field(fm, "next_action_due"))
            if due is None and nxt != "unset":        # older cards put the date inside next_action
                m = DATE.search(nxt)
                due = as_date(m.group(1)) if m else None
            out.append({
                "kind": kind[:-1], "slug": p.stem, "title": field(fm, "title") or p.stem,
                "path": p.relative_to(root).as_posix(),
                "stage": field(fm, "crm_stage") or "unset", "owner": field(fm, "crm_owner") or "unset",
                "last_contact": as_date(field(fm, "last_contact")),
                "next_action": nxt, "due": due,
                "links": {m.strip() for m in re.findall(r"\[\[([^\]|#]+)", body)},
            })
    return out


# ---------------------------------------------------------------- what is due

def due(all_cards: list[dict], today: dt.date, within: int = 7) -> dict:
    soon = today + dt.timedelta(days=within)
    row = lambda c: {"title": c["title"], "path": c["path"], "stage": c["stage"], "owner": c["owner"],
                     "next_action": c["next_action"], "due": c["due"].isoformat() if c["due"] else None,
                     "last_contact": c["last_contact"].isoformat() if c["last_contact"] else None}
    open_cards = [c for c in all_cards if c["stage"] not in ("closed", "dormant")]
    overdue = sorted((c for c in open_cards if c["due"] and c["due"] < today), key=lambda c: c["due"])
    upcoming = sorted((c for c in open_cards if c["due"] and today <= c["due"] <= soon), key=lambda c: c["due"])
    no_next = [c for c in all_cards if c["stage"] in OPEN_STAGES and c["next_action"] == "unset"]
    quiet = [c for c in all_cards if c["stage"] in OPEN_STAGES and c["last_contact"]
             and (today - c["last_contact"]).days > QUIET_DAYS]
    return {"today": today.isoformat(), "within_days": within,
            "overdue": [row(c) for c in overdue], "due_soon": [row(c) for c in upcoming],
            "no_next_step": [row(c) for c in no_next], "gone_quiet": [row(c) for c in quiet],
            "stage_unset": sum(1 for c in all_cards if c["stage"] == "unset"),
            "cards": len(all_cards)}


def counts(report: dict) -> dict:
    """Numbers only. This is what may reach the (locked) Needs-you page: never a name."""
    return {k: len(report[k]) for k in ("overdue", "due_soon", "no_next_step", "gone_quiet")} | {
        "cards": report["cards"]}


# ---------------------------------------------------------------- logging

def find_card(root: pathlib.Path, ref: str) -> pathlib.Path:
    ref_l = ref.strip().lower().removesuffix(".md")
    hits = [c for c in cards(root) if c["slug"].lower() == ref_l or c["title"].lower() == ref_l]
    if not hits:
        hits = [c for c in cards(root) if ref_l in c["title"].lower()]
    if len(hits) != 1:
        names = ", ".join(c["title"] for c in hits[:5]) or "none"
        raise SystemExit(f"crm: '{ref}' matched {len(hits)} cards ({names}). Use the card's file name.")
    return root / hits[0]["path"]


def set_field(fm: str, name: str, value: str) -> str:
    line = f"{name}: {value}"
    if re.search(rf"^{name}:", fm, re.M):
        return re.sub(rf"^{name}:.*$", lambda _: line, fm, count=1, flags=re.M)
    return fm.rstrip("\n") + "\n" + line + "\n"


def one_line(text: str) -> str:
    return " ".join((text or "").split())


def log(path: pathlib.Path, *, kind: str, note: str, when: dt.date, today: dt.date,
        nxt: str | None = None, due_on: dt.date | None = None, why: str | None = None,
        stage: str | None = None, owner: str | None = None) -> str:
    """Append a dated interaction and update the card's fields. Returns the line written."""
    note = one_line(note)
    if not note:
        raise SystemExit("crm: --note is empty; say what happened.")
    if kind not in KINDS:
        raise SystemExit(f"crm: --kind must be one of {', '.join(sorted(KINDS))}.")
    if stage and stage not in STAGES:
        raise SystemExit(f"crm: --stage must be one of {', '.join(sorted(STAGES))}.")
    if when > today:
        raise SystemExit("crm: an interaction cannot be dated in the future; use --next for plans.")
    if due_on and not nxt:
        raise SystemExit("crm: --due needs --next (a date with no step is a default, not a plan).")
    text = path.read_text(encoding="utf-8")
    fm, body = frontmatter(text)
    if field(fm, "visibility") != "private":
        raise SystemExit(f"crm: {path.name} is not visibility: private; fix that before logging to it.")

    entry = f"- {when.isoformat()} · {kind} · {note}"
    lines = body.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip().startswith("**Interactions"))
    except StopIteration:
        nxt_i = next((i for i, l in enumerate(lines) if l.strip().startswith("**Next")), len(lines))
        lines[nxt_i:nxt_i] = ["**Interactions.**", "", ""]
        start = nxt_i
    end = start + 1
    while end < len(lines) and not lines[end].startswith("**") and not lines[end].startswith("#"):
        end += 1
    block = [l for l in lines[start + 1:end] if not re.match(r"^- _.*_\s*$", l)]   # drop the placeholder
    while block and not block[-1].strip():
        block.pop()
    block.append(entry)
    lines[start + 1:end] = block + [""]
    body = "\n".join(lines)

    last = as_date(field(fm, "last_contact"))
    fm = set_field(fm, "last_contact", max(filter(None, [last, when])).isoformat())
    fm = set_field(fm, "timestamp", today.isoformat())
    if stage:
        fm = set_field(fm, "crm_stage", stage)
    if owner:
        fm = set_field(fm, "crm_owner", f'"{one_line(owner)}"')
    if nxt:
        step = one_line(nxt) + (f" (why: {one_line(why)})" if why else "")
        fm = set_field(fm, "next_action", '"' + step.replace('"', "'") + '"')
        fm = set_field(fm, "next_action_due", due_on.isoformat() if due_on else "unset")
        body = re.sub(r"^\*\*Next\.\*\*.*$", lambda _: f"**Next.** {step}" + (f" By {due_on.isoformat()}." if due_on else ""),
                      body, count=1, flags=re.M)
    path.write_text("---" + fm + "---" + body, encoding="utf-8")
    return entry


# ---------------------------------------------------------------- leads

def own_work(root: pathlib.Path) -> tuple[set[str], set[str]]:
    """The titles and tags that mark this wiki's own work, lowercased, from design/crm.json.

    A project page carries domain tags, like an organisation's, so exclusion by OURS_TAGS alone
    offered Prateek his own projects as leads (16 October 2026). Each wiki names its own work here.
    """
    path = root / OWN_WORK
    if not path.exists():
        return set(), set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"crm: {OWN_WORK} is not valid JSON ({e}). Fix it, or delete it to start again.")
    low = lambda key: {str(x).strip().lower() for x in data.get(key, []) if str(x).strip()}
    return low("own_work"), low("own_work_tags")


def mark_own_work(root: pathlib.Path, title: str) -> str:
    """Record a page as this wiki's own work, by its exact title. Refuses a title the wiki does not have."""
    wanted = title.strip().lower()
    match = None
    for p in sorted((root / "wiki").rglob("*.md")):
        if "crm" in p.relative_to(root / "wiki").parts:
            continue
        t = field(frontmatter(p.read_text(encoding="utf-8"))[0], "title")
        if t and t.lower() == wanted:
            match = t
            break
    if not match:
        raise SystemExit(f"crm: no page is titled {title!r}. Use the title as `leads` shows it.")
    path = root / OWN_WORK
    data = {}
    if path.exists():
        own_work(root)  # stops on broken JSON before anything is overwritten
        data = json.loads(path.read_text(encoding="utf-8"))
    titles = data.get("own_work", [])
    if match.lower() not in {x.lower() for x in titles}:
        data["own_work"] = titles + [match]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return match

def leads(root: pathlib.Path, top: int = 12) -> list[dict]:
    """Organisations the wiki knows that have no card and no link from one, most linked-to first.

    Found by exclusion, as luck_candidates.reach_gaps does: org pages carry domain tags, not an
    org marker. People are left out: a person with no card is a different gap.
    """
    own_titles, own_tags = own_work(root)
    known = set()
    for c in cards(root):
        known.add(c["title"].lower())
        known |= {l.lower() for l in c["links"]}
    pages, bodies = {}, []
    for p in sorted((root / "wiki").rglob("*.md")):
        rel = p.relative_to(root / "wiki")
        if p.name in SKIP_FILES or rel.parts[0] in SKIP_DIRS or "crm" in rel.parts:
            continue
        text = p.read_text(encoding="utf-8")
        fm, body = frontmatter(text)
        bodies.append(body)
        title, tags = field(fm, "title"), tags_of(fm)
        if (field(fm, "type") == "entity" and title and title.lower() not in known | own_titles
                and not tags & (OURS_TAGS | PLACE_TAGS | own_tags) and "person" not in tags):
            pages[title] = {"title": title, "path": p.relative_to(root).as_posix(),
                            "description": field(fm, "description")[:140]}
    corpus = "\n".join(bodies)
    for t, page in pages.items():
        page["mentions"] = len(re.findall(r"\[\[" + re.escape(t) + r"(?:\||\]\])", corpus))
    return sorted(pages.values(), key=lambda x: (-x["mentions"], x["title"]))[:top]


# ---------------------------------------------------------------- command line

def _print_due(r: dict) -> None:
    def show(label: str, rows: list[dict], extra) -> None:
        print(f"\n{label} ({len(rows)})")
        for x in rows or [None]:
            print("  none" if x is None else f"  {x['title']}: {extra(x)}")
    print(f"Follow-ups on {r['today']}, across {r['cards']} cards")
    show("Overdue", r["overdue"], lambda x: f"{x['next_action']} (due {x['due']})")
    show(f"Due in the next {r['within_days']} days", r["due_soon"], lambda x: f"{x['next_action']} (due {x['due']})")
    show("Open, with no next step", r["no_next_step"], lambda x: f"stage {x['stage']}")
    show(f"Open, no contact for over {QUIET_DAYS} days", r["gone_quiet"], lambda x: f"last contact {x['last_contact']}")
    if r["stage_unset"]:
        print(f"\n{r['stage_unset']} card(s) have no stage yet.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--today", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("due"); d.add_argument("--within", type=int, default=7); d.add_argument("--json", action="store_true")
    c = sub.add_parser("counts"); c.add_argument("--json", action="store_true")
    lg = sub.add_parser("log")
    lg.add_argument("card"); lg.add_argument("--kind", required=True); lg.add_argument("--note", required=True)
    lg.add_argument("--date"); lg.add_argument("--next"); lg.add_argument("--due"); lg.add_argument("--why")
    lg.add_argument("--stage"); lg.add_argument("--owner")
    ld = sub.add_parser("leads"); ld.add_argument("--top", type=int, default=12); ld.add_argument("--json", action="store_true")
    nl = sub.add_parser("not-a-lead"); nl.add_argument("title")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root)
    today = as_date(a.today) if a.today else dt.date.today()

    if a.cmd in ("due", "counts"):
        r = due(cards(root), today, getattr(a, "within", 7))
        if a.cmd == "counts":
            print(json.dumps(counts(r)))
        elif a.json:
            print(json.dumps(r, indent=2))
        else:
            _print_due(r)
    elif a.cmd in ("log", "leads", "not-a-lead") and is_commons(root):
        raise SystemExit(COMMONS_REFUSAL)
    elif a.cmd == "log":
        when = as_date(a.date) if a.date else today
        due_on = as_date(a.due) if a.due else None
        if (a.date and not when) or (a.due and not due_on):
            raise SystemExit("crm: dates are YYYY-MM-DD.")
        path = find_card(root, a.card)
        entry = log(path, kind=a.kind, note=a.note, when=when, today=today, nxt=a.next, due_on=due_on,
                    why=a.why, stage=a.stage, owner=a.owner)
        print(f"{path.relative_to(root)}: {entry}")
    elif a.cmd == "not-a-lead":
        title = mark_own_work(root, a.title)
        print(f"{OWN_WORK}: {title} is this wiki's own work, and will not be offered as a lead.")
    else:
        rows = leads(root, a.top)
        if a.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"Organisations the wiki knows with no card yet ({len(rows)} shown, most linked-to first)")
            for x in rows:
                print(f"  {x['title']} ({x['mentions']} links): {x['description']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
