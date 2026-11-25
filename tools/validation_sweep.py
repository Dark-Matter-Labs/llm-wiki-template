#!/usr/bin/env python3
"""
validation_sweep.py — clear the pages that have sat at `validation: machine` for too long.

Asked for by Gurden on 19 November 2026: "no one is validating anything". That day, across the 43 local wikis,
4,668 of 4,737 pages were at `machine`, none at `peer` or `collective`, and 2,696 had sat there over 30 days.
The rule it applies is in `.claude/reference/page-fields.md`, under Validation.

For each page at `machine` whose `timestamp` is older than --days, it proposes one of:

  self   own wiki, written at the owner's request, nothing critical. `--apply` sets `validation: self`
         with `validation_note: default`.
  ask    own wiki, but critical: a budget, a commitment, a named person, contested, a decision.
         The owner says yes or no. Nothing is changed.
  leave  a commons page, a scheduled job's output, a page from another wiki, or a dormant page.

  python3 tools/validation_sweep.py                       # dry run: this wiki, page by page
  python3 tools/validation_sweep.py --days 60
  python3 tools/validation_sweep.py --totals ../a-wiki ../b-commons   # counts only, any number of wikis
  python3 tools/validation_sweep.py --apply               # this wiki only, the `self` group only

Use --totals for any wiki that is not your own, so no page title is printed.
"""
import argparse
import collections
import datetime
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import export  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
PERSON_TAGS = {"person", "people", "contact"}
EMPTY = {"", "[]", '""', "''", "null", "~", "none"}


def has(raw, key):
    """True when the page's details give `key` a value, inline or as an indented list below it."""
    m = re.search(rf"^{key}:[ \t]*(.*)$", raw, re.M)
    if not m:
        return False
    value = re.split(r"\s+#", m.group(1))[0].strip()
    if value:
        return value.lower() not in EMPTY
    return bool(re.search(rf"^{key}:[^\n]*\n[ \t]+-", raw, re.M))


def critical(fm, raw, body, rel):
    """The first reason this page needs the owner's own yes, or None."""
    tags = {str(t).lower() for t in (fm.get("tags") if isinstance(fm.get("tags"), list) else [])}
    # A sum in passing or a public page is not critical by itself (Gurden, 20 November 2026): see page-fields.md.
    if "budget" in tags or "budget" in str(fm.get("title", "")).lower():
        return "a budget"
    if fm.get("type") in ("commitment", "goal") or has(raw, "commits_to"):
        return "a commitment"
    if fm.get("type") == "person" or tags & PERSON_TAGS or rel.startswith("crm/") or has(raw, "crm_category"):
        return "a named person"
    if (any(has(raw, k) for k in ("contradicts", "superseded_by", "devalued_by"))
            or fm.get("status") == "contested" or re.search(r"verdict:\s*disputes", raw)):
        return "contested"
    if has(raw, "decides"):
        return "a decision"
    if has(raw, "validated_by"):
        return "already names someone"
    return None


def federation(wiki):
    try:
        return json.loads((wiki / "design" / "federation.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def age_days(fm, today):
    """Days since `timestamp`, or None when it is missing or unreadable (counted as old)."""
    try:
        return (today - datetime.date.fromisoformat(str(fm.get("timestamp") or "")[:10])).days
    except ValueError:
        return None


def sweep(wiki, days=30, today=None):
    """[(rel path, title, proposal, reason)] for every page at machine older than `days`."""
    today = today or datetime.date.today()
    fed = federation(wiki)
    commons = fed.get("role") == "commons"
    rows = []
    for path in sorted((wiki / "wiki").rglob("*.md")):
        rel = path.relative_to(wiki / "wiki").as_posix()
        if rel in ("index.md", "log.md") or rel.startswith(("index/", "log/")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body = export.split_frontmatter(text)
        if not fm or not re.search(r"^validation:[ \t]*machine\b", text.split("---", 2)[1], re.M):
            continue
        age = age_days(fm, today)
        if age is not None and age <= days:
            continue
        raw = text.split("---", 2)[1]
        title = str(fm.get("title") or rel)
        if commons:
            rows.append((rel, title, "leave", "a commons: a person there decides"))
        elif fm.get("status") == "dormant":
            rows.append((rel, title, "leave", "dormant"))
        elif fm.get("derivation") == "derivative":
            rows.append((rel, title, "leave", "written by a scheduled job"))
        elif has(raw, "origin"):
            rows.append((rel, title, "leave", "came from another wiki"))
        else:
            why = critical(fm, raw, body, rel)
            rows.append((rel, title, "ask", why) if why else (rel, title, "self", "default"))
    return rows


def set_default_self(text, owner, today):
    """The page with `validation: machine` replaced by a default self, signed with the owner's login."""
    head, sep, rest = text.partition("\n---")
    lines = [ln for ln in head.split("\n")
             if not re.match(r"(validated_by|validated_at|validation_note):", ln)]
    out = []
    for ln in lines:
        if re.match(r"validation:[ \t]*machine\b", ln):
            out += ["validation: self", f"validated_by: [{owner}]", f"validated_at: {today.isoformat()}",
                    "validation_note: default"]
        else:
            out.append(ln)
    return "\n".join(out) + sep + rest


def apply(wiki, rows, today):
    owner = federation(wiki).get("owner")
    if federation(wiki).get("role") != "spoke" or not owner:
        raise SystemExit(f"{wiki.name}: --apply needs a personal wiki with an owner in design/federation.json")
    n = 0
    for rel, _title, what, _why in rows:
        if what != "self":
            continue
        p = wiki / "wiki" / rel
        p.write_text(set_default_self(p.read_text(encoding="utf-8"), owner, today), encoding="utf-8")
        n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Propose what to do with pages stuck at validation: machine.")
    ap.add_argument("wikis", nargs="*", type=pathlib.Path, help="wiki folders (default: this one)")
    ap.add_argument("--days", type=int, default=30, help="older than this many days (default 30)")
    ap.add_argument("--totals", action="store_true", help="counts only, no page titles")
    ap.add_argument("--apply", action="store_true", help="this wiki only: set the `self` group")
    a = ap.parse_args(argv)
    wikis = [w.resolve() for w in a.wikis] or [ROOT]
    if a.apply and wikis != [ROOT]:
        print("--apply only edits this wiki. Run it from inside the wiki you mean.")
        return 2
    today = datetime.date.today()
    grand = collections.Counter()
    for wiki in wikis:
        if not (wiki / "wiki").is_dir():
            print(f"{wiki.name}: no wiki/ folder, skipped")
            continue
        rows = sweep(wiki, a.days, today)
        count = collections.Counter(what for _r, _t, what, _w in rows)
        asks = collections.Counter(why for _r, _t, what, why in rows if what == "ask")
        grand.update(count)
        print(f"{wiki.name} ({federation(wiki).get('role', 'unknown role')}): {len(rows)} pages at machine "
              f"for over {a.days} days. self {count['self']}, ask {count['ask']}, leave {count['leave']}"
              + (f"  (ask: {', '.join(f'{k} {v}' for k, v in asks.most_common())})" if asks else ""))
        if not a.totals:
            for rel, title, what, why in rows:
                print(f"  {what:5}  {title}  [{why}]  wiki/{rel}")
        if a.apply:
            print(f"  set {apply(wiki, rows, today)} pages to self (default). Nothing else changed.")
    if len(wikis) > 1:
        print(f"ALL {len(wikis)} wikis: {sum(grand.values())} pages. self {grand['self']}, ask {grand['ask']}, "
              f"leave {grand['leave']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
