#!/usr/bin/env python3
"""
test_newsletter.py — prove the gather step counts the right window and names no person.

Written 2026-09-15, when the tool was about to travel to ten more wikis. Its docstring makes
three promises and nothing checked any of them: that it reports per WIKI and never per person,
that it does not touch `private` material, and that it summarises the last COMPLETE month. The
first is a house rule, and a rule enforced only by a comment is a rule with one careless edit
between it and being gone.

Usage:  python3 tools/test_newsletter.py
"""
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newsletter as N  # noqa: E402


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
        if not ok:
            fails.append(name)

    # --- the window ------------------------------------------------------------------
    check("the month reported is the last COMPLETE one",
          N.last_complete_month(dt.date(2026, 9, 15)) == (2026, 8))
    check("...including across a year boundary",
          N.last_complete_month(dt.date(2026, 1, 3)) == (2025, 12))
    check("...and on the first of a month, which is the case the cron guards against",
          N.last_complete_month(dt.date(2026, 3, 1)) == (2026, 2))
    check("a window ends on the month's real last day, February included",
          N.month_window(2026, 2) == (dt.date(2026, 2, 1), dt.date(2026, 2, 28)))
    check("...and in a leap year", N.month_window(2024, 2)[1] == dt.date(2024, 2, 29))

    # --- the house rule --------------------------------------------------------------
    # "knowledge, not surveillance ... binds hardest in the team wiki and every shared
    # instance". A per-person count inside a shared instance is activity tracking of named
    # colleagues, so the unit is the repository the page came from.
    nodes = [
        {"timestamp": "2026-08-04", "origin": "malik-llm-wiki", "contributed_by": "Malik"},
        {"timestamp": "2026-08-19", "origin": "malik-llm-wiki", "contributed_by": "Malik"},
        {"timestamp": "2026-08-07", "origin": "fang-llm-wiki", "contributed_by": "Fang"},
        {"timestamp": "2026-07-31", "origin": "malik-llm-wiki", "contributed_by": "Malik"},
        {"timestamp": "2026-09-01", "origin": "malik-llm-wiki", "contributed_by": "Malik"},
    ]
    got = N.arrivals(nodes, dt.date(2026, 8, 1), dt.date(2026, 8, 31))
    check("arrivals are counted per wiki", got == {"malik-llm-wiki": 2, "fang-llm-wiki": 1},
          str(got))
    check("...and never per person",
          not any("Malik" in str(k) or "Fang" in str(k) for k in got), str(got))
    check("a page dated outside the window is not counted", sum(got.values()) == 3, str(got))
    check("a page with no origin is attributed to this wiki, not to nobody",
          N.arrivals([{"timestamp": "2026-08-02"}], dt.date(2026, 8, 1), dt.date(2026, 8, 31))
          == {"(written here)": 1})

    # The guard that matters: `contributed_by` names a human and must not be read at all.
    src = pathlib.Path(__file__).resolve().parent.joinpath("newsletter.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith(("#", "*", '"')))
    check("the tool never reads `contributed_by` outside its own refusal note",
          'get("contributed_by"' not in code and "['contributed_by']" not in code)

    # --- the boundary ----------------------------------------------------------------
    # It may read a commons' SHARED cut, which is already filtered, and never the full graph
    # sitting beside it. The first version of this test put both files in one directory and
    # passed under a mutation that read either, because the two collided on the same key and
    # the shared one happened to win on sort order. Green for the wrong reason, which is the
    # thing this whole repository keeps finding. They are separated now.
    def cuts_for(files):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for rel, payload in files.items():
                f = root / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(payload), encoding="utf-8")
            old = N.COMMONS
            N.COMMONS = root
            try:
                return N.commons_cuts()
            finally:
                N.COMMONS = old

    shared = [{"timestamp": "2026-08-05", "origin": "robyn-llm-wiki"}]
    unfiltered = [{"timestamp": "2026-08-06", "origin": "robyn-llm-wiki",
                   "title": "A PRIVATE PAGE", "visibility": "private"}]

    got = cuts_for({"xco-team-wiki/export/wiki.shared.json": shared})
    check("a commons' shared cut is read", list(got) == ["xco-team-wiki"], str(list(got)))

    # The one that matters: a commons with only an unfiltered graph yields NOTHING.
    got = cuts_for({"power-project-wiki/export/wiki.json": unfiltered})
    check("an unfiltered graph is not read, even when it is the only file there",
          got == {} and "A PRIVATE PAGE" not in json.dumps(got), str(got))

    got = cuts_for({"xco-team-wiki/export/wiki.shared.json": shared,
                    "power-project-wiki/export/wiki.json": unfiltered})
    check("...and it is still not read when a legitimate cut sits next to it",
          list(got) == ["xco-team-wiki"] and "A PRIVATE PAGE" not in json.dumps(got), str(got))

    # --- the refusals ----------------------------------------------------------------
    check("the tool has no delivery path",
          not any(w in src for w in ("smtplib", "sendgrid", "mailto:", "requests.post")))
    check("...and calls no model, so the free half stays free",
          "anthropic" not in src.lower())

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
