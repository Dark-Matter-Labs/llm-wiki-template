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

    # --- the signals -----------------------------------------------------------------
    # Added 2026-09-15, when the issue was rewritten to be about what the corpus is thinking
    # rather than how many pages it gained. Counts are the least surprising thing about a
    # month; these five are the interesting part, so they are the part that must be right.

    # The correction rate. The log's rebuild/repair split exists so it is visible without a
    # metacognition pass, and a window filter that leaks a neighbouring month would make the
    # most self-critical number in the system quietly wrong.
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "wiki" / "log").mkdir(parents=True)
        (root / "wiki" / "log" / "2026-08-04.md").write_text(
            "## [2026-08-04] rebuild | Advanced the thing\n"
            "## [2026-08-04] repair  | Put a thing back (mine)\n"
            "## [2026-08-04] ingest  | A source\n", encoding="utf-8")
        (root / "wiki" / "log" / "2026-08-20.md").write_text(
            "## [2026-08-20] repair  | Somebody else's defect\n"
            "Some prose that mentions ## [2026-08-20] rebuild | not a heading\n",
            encoding="utf-8")
        (root / "wiki" / "log" / "2026-09-01.md").write_text(
            "## [2026-09-01] rebuild | The next month, which must not be counted\n",
            encoding="utf-8")
        # A PRE-SPLIT month file: July 2026 and earlier are one file per month, and the log
        # is appended to by hand, so a mis-dated entry inside one is a real hazard. This is
        # the only shape where the per-entry date filter does any work — the first version of
        # this test asserted the filter and proved nothing, because the filename filter had
        # already excluded the file it used.
        (root / "wiki" / "log" / "2026-07.md").write_text(
            "## [2026-07-09] rebuild | Inside July\n"
            "## [2026-08-02] rebuild | Mis-dated into August, inside July's file\n",
            encoding="utf-8")
        old_root = N.ROOT
        N.ROOT = root
        try:
            c = N.corrections(dt.date(2026, 8, 1), dt.date(2026, 8, 31))
            july = N.corrections(dt.date(2026, 7, 1), dt.date(2026, 7, 31))
        finally:
            N.ROOT = old_root
    check("advances and repairs are counted separately",
          (c["entries"]["rebuild"], c["entries"]["repair"]) == (1, 2), str(c["entries"]))
    check("the next month's file is not counted", c["entries"]["rebuild"] == 1, str(c["entries"]))
    check("a pre-split month file is read", july["entries"]["rebuild"] == 1,
          str(july["entries"]))
    check("...and an entry mis-dated outside the window inside it is not counted",
          july["entries"]["rebuild"] == 1 and c["entries"]["rebuild"] == 1,
          f"july={july['entries']} august={c['entries']}")
    check("a repair of the model's own error is counted as such",
          c["repairs_of_my_own_error"] == 1, str(c))
    check("the repair share is the honest fraction", c["repair_share"] == round(2 / 3, 3),
          str(c["repair_share"]))
    check("a log line quoted inside prose is not read as an entry",
          c["entries"]["rebuild"] == 1, str(c["entries"]))

    # Goals. `declined` and `exited` are NON-PENALISED: refusing, or leaving deliberately, is
    # a valid outcome and must never be rendered as failure. Only `lapsed` counts against a
    # goal. A newsletter that reported "2 commitments failed" here would be lying about two
    # people who made a decision.
    nodes = [
        {"type": "goal", "title": "G1", "horizon": "near", "validation": "machine"},
        {"type": "goal", "title": "G2", "horizon": "far", "validation": "peer"},
        {"type": "commitment", "title": "C1", "commits_to": "G1", "state": "held",
         "timestamp": "2026-08-10"},
        {"type": "commitment", "title": "C2", "commits_to": "G1", "state": "declined",
         "timestamp": "2026-08-12"},
        {"type": "commitment", "title": "C3", "commits_to": "G1", "state": "exited",
         "timestamp": "2026-07-02"},
        {"type": "concept", "title": "not a goal", "timestamp": "2026-08-01"},
    ]
    g = N.goal_vectors({"a-commons": nodes}, dt.date(2026, 8, 1), dt.date(2026, 8, 31))["a-commons"]
    check("goals and commitments are counted from the cut",
          (g["goals"], g["commitments"]) == (2, 3), str(g))
    check("a goal nothing is committed against is named as such",
          g["goals_with_nothing_committed"] == 1, str(g))
    check("every commitment state is reported, declined and exited included",
          g["commitment_states"] == {"held": 1, "declined": 1, "exited": 1},
          str(g["commitment_states"]))
    shown = "\n".join(N._render_signals({
        "patterns": None, "trajectory": None, "corrections": None, "unsettled": None,
        "goals": N.goal_vectors({"a-commons": nodes}, dt.date(2026, 8, 1),
                                dt.date(2026, 8, 31))})).lower()
    check("...and the read-out never calls declined or exited a failure",
          not any(w in shown for w in ("failure", "failed", "missed", "behind schedule")),
          "refusing, or leaving deliberately, is a valid outcome; only lapsed counts against "
          "a goal, and rendering the other two as failure would misreport a decision")
    check("a goal a person stood behind is distinguished from one nobody has",
          g["stood_behind_by_a_person"] == 1, str(g))
    check("only this month's movements are listed",
          [m["page"] for m in g["moved_this_month"]] == ["C1", "C2"],
          str(g["moved_this_month"]))
    check("a wiki with no goals is left out rather than reported as zero",
          N.goal_vectors({"empty": [{"type": "concept"}]}, dt.date(2026, 8, 1),
                         dt.date(2026, 8, 31)) == {})

    # Every signal is optional. A wiki without the tool gets a stated blank, never a guess.
    with tempfile.TemporaryDirectory() as tmp:
        old_root = N.ROOT
        N.ROOT = pathlib.Path(tmp)
        try:
            check("a missing tool returns nothing rather than failing the gather",
                  N.patterns_now() is None and N.unsettled() is None and
                  N.trajectory(dt.date(2026, 8, 1), dt.date(2026, 8, 31)) is None)
        finally:
            N.ROOT = old_root
    check("...and the read-out says the tool is absent rather than printing a zero",
          "not in this wiki" in "\n".join(N._render_signals(
              {"patterns": None, "trajectory": None, "goals": {}, "corrections": None,
               "unsettled": None})))

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
