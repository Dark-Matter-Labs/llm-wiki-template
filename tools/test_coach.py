#!/usr/bin/env python3
"""
test_coach.py — the suggestions the wiki offers, and the discipline around them.

The coach exists to make the system proactive without making it a nag. So the properties tested are
the ones that keep it worth listening to: it speaks only from a real signal, it puts the most useful
thing first, it says nothing it has been told to stop saying, and a healthy wiki gets a tip rather
than an invented problem.

  python3 tools/test_coach.py
"""

import datetime
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coach  # noqa: E402

FAILED = []
TODAY = datetime.date(2026, 9, 28)


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(root, rel, **fm):
    fm.setdefault("type", "concept")
    fm.setdefault("title", pathlib.Path(rel).stem)
    fm.setdefault("visibility", "private")
    fm.setdefault("validation", "machine")
    fm.setdefault("timestamp", "2026-09-20")
    body = fm.pop("body", "Some text.")
    head = "\n".join(f"{k}: {v}" for k, v in fm.items())
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\n{head}\n---\n\n{body}\n", encoding="utf-8")


def log(root, day, kind, title="x"):
    p = root / "wiki" / "log" / f"{day}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(f"\n## [{day}] {kind} | {title}\n")


def fresh(tmp, fed=None):
    root = pathlib.Path(tmp)
    (root / "design").mkdir(parents=True, exist_ok=True)
    (root / "design" / "federation.json").write_text(json.dumps(fed or {"role": "spoke", "contributes_to": []}))
    page(root, "wiki/overview.md", type="overview", title="Overview", timestamp="2026-09-20",
         body="## What this wiki is for\n\nThe land question in Seville.\n")
    return root


def ids(root, **kw):
    return [s["id"] for s in coach.suggestions(root, today=TODAY, **kw)]


def main():
    print("coach — one useful suggestion, from a real signal, never a nag\n")

    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        check("a wiki with no real pages is told to add its first documents first",
              ids(root)[0] == "first-documents", str(ids(root)))

    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        page(root, "wiki/overview.md", type="overview", title="Overview",
             body="## What this wiki is for\n\n_Replace this with a sentence or two._\n")
        for i in range(5):
            page(root, f"wiki/p{i}.md")
        check("an unwritten purpose is noticed", "purpose" in ids(root), str(ids(root)))

    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        for i in range(12):
            page(root, f"wiki/p{i}.md", body="Cites (raw/filed.pdf).")
        (root / "raw").mkdir()
        (root / "raw" / "filed.pdf").write_text("x")
        (root / "raw" / "waiting.pdf").write_text("x")
        (root / "raw" / "README.md").write_text("x")
        got = coach.suggestions(root, today=TODAY)
        unfiled = [s for s in got if s["id"] == "unfiled-sources"]
        check("a source nobody has filed is noticed, and the README is not a source",
              unfiled and unfiled[0]["count"] == 1, str(unfiled))
        check("an unfiled source outranks housekeeping", got[0]["id"] == "unfiled-sources", str([s["id"] for s in got]))

    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        for i in range(12):
            page(root, f"wiki/p{i}.md", timestamp="2026-09-27")
        page(root, "wiki/overview.md", type="overview", title="Overview", timestamp="2026-08-01",
             body="## What this wiki is for\n\nReal purpose.\n")
        log(root, "2026-08-01", "lint")
        log(root, "2026-09-27", "ingest")
        got = ids(root)
        check("an overview far behind the newest page is noticed", "overview" in got, str(got))
        check("a health check nearly two months old is noticed", "lint" in got, str(got))

    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        for i in range(12):
            page(root, f"wiki/p{i}.md", timestamp="2026-09-27")
        log(root, "2026-09-26", "lint")
        log(root, "2026-09-27", "ingest")
        page(root, "wiki/p0.md", validation="self", timestamp="2026-09-27")
        got = ids(root)
        check("a recent health check is not suggested again", "lint" not in got, str(got))
        check("a wiki with a validated page is not asked to validate", "stand-behind" not in got, str(got))
        check("a healthy wiki gets a tip, not an invented problem",
              got and got[0].startswith("tip-"), str(got))

    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        for i in range(12):
            page(root, f"wiki/p{i}.md", timestamp="2026-09-27")
        got = ids(root)
        check("no page with a person's name behind it is noticed", "stand-behind" in got, str(got))
        (root / "design" / "coach.json").write_text(json.dumps({"off": ["stand-behind", "lint", "tips"]}))
        got = ids(root)
        check("a suggestion the owner switched off is never offered", "stand-behind" not in got, str(got))
        check("switching off tips switches off every tip", not any(i.startswith("tip-") for i in got), str(got))

    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        for i in range(12):
            page(root, f"wiki/p{i}.md", timestamp="2026-09-10", validation="self")
        log(root, "2026-09-10", "lint")
        got = ids(root)
        check("a long gap since the last visit suggests catching up", "catch-up" in got, str(got))

    # tips rotate, and a commons is not told to share with the team
    tips_a = [s["id"] for s in coach.tips(pathlib.Path("."), datetime.date(2026, 9, 28), role="spoke")]
    tips_b = [s["id"] for s in coach.tips(pathlib.Path("."), datetime.date(2026, 9, 29), role="spoke")]
    check("tips rotate from day to day", tips_a != tips_b, f"{tips_a} {tips_b}")
    check("there is a tip about artifacts",
          any(t["id"] == "tip-artifacts" for t in coach.TIPS), str([t["id"] for t in coach.TIPS]))
    commons_tips = {t["id"] for t in coach.TIPS if coach._tip_applies(t, "commons")}
    check("a commons is never told to share up to the team", "tip-share" not in commons_tips, str(commons_tips))

    # every suggestion says what to say
    with tempfile.TemporaryDirectory() as t:
        root = fresh(t)
        for s in coach.suggestions(root, today=TODAY, limit=None):
            if not s.get("say"):
                check(f"suggestion {s['id']} tells the person what to say", False)
                break
        else:
            check("every suggestion tells the person what to say", True)

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
