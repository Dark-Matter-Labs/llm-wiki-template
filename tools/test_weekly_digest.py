#!/usr/bin/env python3
"""
test_weekly_digest.py — the Thursday digest's own edge cases.

Three things must hold, and each is a way the digest could do harm rather than merely fail:

  * in a commons, nothing on a `private` page is named: not its title, its commitments, or a
    sentence on an open page that links to it;
  * a section with nothing in it is left out, so a quiet week does not read as a busy one;
  * a commitment is listed only when its date falls inside the next seven days, read the way
    the phone's reminders read it.

  python3 tools/test_weekly_digest.py
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weekly_digest as wd  # noqa: E402

FAILURES = []
THU = dt.date(2026, 11, 5)


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"          got  {got!r}\n          want {want!r}")
        FAILURES.append(label)


def node(slug, title, visibility, body=""):
    return {"slug": slug, "title": title, "visibility": visibility, "body": body,
            "inbound_links": []}


TABLE = """| Band | Category | Commitment | Due | Next step |
|---|---|---|---|---|
| This week | d.INO | **Send the notes** | 2026-11-06 | |
| This week | d.INO | **Too late** | 2026-11-12 | |
| This week | d.INO | **Short date** | 9 Nov | |
| This week | d.INO | ~~**Done already**~~ | 2026-11-07 | |
| Soon | d.INO | **No date** | Session mid-Nov | |
| Soon | d.INO | **Yesterday** | 2026-11-04 | |
"""

NODES = {
    "open-page": node("open-page", "Open Page", "internal"),
    "secret": node("secret", "Secret Deal", "private"),
    "crm/a-person": node("crm/a-person", "A Person", "private"),
    "team-commitments": node("team-commitments", "Team open commitments", "internal", TABLE),
    "my-commitments": node("my-commitments", "Gurden's open commitments", "private", TABLE),
}


def visible(commons):
    return {n["title"].lower() for n in NODES.values() if wd.shown(n, commons)}


def main():
    print("weekly digest — edge cases\n")

    # --- privacy in a commons -------------------------------------------------
    check("a commons shows an internal page", wd.shown(NODES["open-page"], True), True)
    check("a commons never shows a private page", wd.shown(NODES["secret"], True), False)
    check("a personal wiki shows its own private page", wd.shown(NODES["secret"], False), True)
    check("CRM is never listed, even in a personal wiki", wd.shown(NODES["crm/a-person"], False), False)
    check("a sentence linking to a private page is dropped in a commons",
          wd.clean("Ask about [[Secret Deal]] first", visible(True)), None)
    check("the same sentence keeps its words in a personal wiki",
          wd.clean("Ask about [[Secret Deal]] first", visible(False)), "Ask about Secret Deal first")
    check("citations and inner quotes are taken out",
          wd.clean('He said "yes" (raw/x.md, 00:01).', set()), "He said 'yes'.")

    in_commons = {r["page"] for r in wd.commitments_due(NODES, True, THU, visible(True))}
    check("a private commitments page is not read in a commons", in_commons, {"Team open commitments"})

    # --- the seven-day window -------------------------------------------------
    due = [r["commitment"] for r in wd.commitments_due(
        {"t": NODES["team-commitments"]}, True, THU, visible(True))]
    check("only dates in the next seven days, struck rows and undated rows left out",
          due, ["Send the notes", "Short date"])
    check("a day and month take the nearest year", wd.due_date("9 Nov", THU), dt.date(2026, 11, 9))
    check("a full date is read", wd.due_date("~2026-11-06 · prio", THU), dt.date(2026, 11, 6))
    check("a date in words with a year is read", wd.due_date("12 January 2027", THU), dt.date(2027, 1, 12))
    check("no date, no row", wd.due_date("Once Kate has mentioned you", THU), None)

    # --- empty sections are left out --------------------------------------------
    m = {"week_ending": "2026-11-05", "since": "2026-10-30", "visibility": "internal",
         "added": [{"title": "Open Page", "type": "concept", "description": "What it is."}],
         "changed": [], "hunches": [], "commitments_due": [], "questions": [],
         "proposals": [], "worth_sharing": []}
    page = wd.render(m)
    check("a filled section is written", "## New pages (1)" in page, True)
    check("an empty section is not", any(h in page for h in (
        "## Pages that changed", "## Hunches", "## Commitments", "## Questions",
        "## Waiting", "## Moved this week")), False)
    check("a commons digest is internal and says it names no private page",
          ("visibility: internal" in page, "It names no private page." in page), (True, True))
    check("no [[links]] are written", "[[" in page, False)

    # --- worth sharing: never guessed --------------------------------------------
    real = wd.contribute.commons_titles
    try:
        wd.contribute.commons_titles = lambda name: None
        got = wd.worth_sharing([NODES["open-page"]], {"contributes_to": ["team"]})
        check("no copy of the commons is said, not guessed", got,
              [{"commons": "team", "held_unknown": True, "pages": []}])
        wd.contribute.commons_titles = lambda name: {"Already There": "x"}
        got = wd.worth_sharing([NODES["open-page"], NODES["secret"]], {"contributes_to": ["team"]})
        check("a private page is never offered up", got[0]["pages"], ["Open Page"])
    finally:
        wd.contribute.commons_titles = real

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failed")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
