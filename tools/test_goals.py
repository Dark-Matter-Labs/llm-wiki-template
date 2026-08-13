#!/usr/bin/env python3
"""
test_goals.py — prove the goal view computes honestly and cannot write.

Three things could go wrong here, and each would be quiet:

  * **It lies about progress.** A number nobody typed still has to be right, and it has
    to be the same number tomorrow for an unchanged corpus.
  * **It penalises refusal.** `declined` and `exited` are valid outcomes. If the view
    renders them as failures, people stop declining honestly and the ledger's data rots.
  * **It writes.** The wiki is the source of truth; a view that edits it is a second
    source of truth, and the consent loop is gone.

Usage:  python3 tools/test_goals.py
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goals  # noqa: E402


GOAL = """---
type: goal
title: {title}
description: A goal.
tags: [g]
status: draft
visibility: {vis}
confidence: medium
validation: machine
timestamp: {ts}
horizon: {horizon}
sources: []
---

{body}
"""

COMMIT = """---
type: commitment
title: {title}
description: A commitment.
tags: [c]
status: draft
visibility: {vis}
confidence: medium
validation: machine
timestamp: {ts}
commits_to: "{goal}"
resources: "{res}"
until: 2027-01-01
state: {state}
sources: []
---

Committed to [[{goal}]].
"""


def main():
    failures = []

    def check(name, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    tmp = tempfile.mkdtemp()
    wiki = os.path.join(tmp, "wiki")
    os.makedirs(wiki)

    def w(slug, text):
        with open(os.path.join(wiki, slug + ".md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    try:
        w("g-live", GOAL.format(title="Live Goal", vis="internal", ts="2026-08-01",
                                horizon="near", body="A goal."))
        w("g-unbacked", GOAL.format(title="Unbacked Goal", vis="internal", ts="2026-08-01",
                                    horizon="mid", body="Nothing committed."))
        w("g-declined", GOAL.format(title="Declined Goal", vis="internal", ts="2026-08-01",
                                    horizon="far", body="All declined."))
        w("g-lapsed", GOAL.format(title="Lapsed Goal", vis="internal", ts="2026-08-01",
                                  horizon="near", body="Something lapsed."))

        w("c-held", COMMIT.format(title="Held C", vis="internal", ts="2026-08-01",
                                  goal="Live Goal", res="2 people", state="held"))
        w("c-declined", COMMIT.format(title="Declined C", vis="internal", ts="2026-08-01",
                                      goal="Declined Goal", res="none", state="declined"))
        w("c-exited", COMMIT.format(title="Exited C", vis="internal", ts="2026-08-01",
                                    goal="Declined Goal", res="none", state="exited"))
        w("c-lapsed", COMMIT.format(title="Lapsed C", vis="internal", ts="2026-08-01",
                                    goal="Lapsed Goal", res="1 person", state="lapsed"))
        w("c-orphan", COMMIT.format(title="Orphan C", vis="internal", ts="2026-08-01",
                                    goal="A Goal That Does Not Exist", res="x", state="held"))
        w("c-private", COMMIT.format(title="Private C", vis="private", ts="2026-08-01",
                                     goal="Live Goal", res="secret", state="held"))

        v = goals.build(wiki, use_git=False)
        by = {g["title"]: g for g in v["goals"]}

        check("goals and commitments are discovered",
              v["counts"]["goals"] == 4 and v["counts"]["commitments"] == 6,
              f"{v['counts']}")

        # --- refusal is not failure -----------------------------------------
        d = by["Declined Goal"]
        check("a goal whose commitments were declined/exited is `closed`, not failed",
              d["health"] == "closed" and d["counts"]["lapsed"] == 0,
              f"health={d['health']} why={d['why']}")
        check("declined and exited count as closed-without-failure",
              d["counts"]["closed_ok"] == 2, f"closed_ok={d['counts']['closed_ok']}")

        text = goals.render(v)
        check("the rendered view marks non-penalised states explicitly",
              "non-penalised" in text,
              "a reader must not mistake a decline for a failure")

        # --- lapsed IS the failure state -------------------------------------
        l = by["Lapsed Goal"]
        check("only `lapsed` raises attention",
              l["health"] == "attention" and "lapsed" in l["why"],
              f"health={l['health']}")

        # --- unbacked vs live -------------------------------------------------
        check("a goal with no commitments reads as unbacked",
              by["Unbacked Goal"]["health"] == "unbacked")
        check("a goal with an open commitment reads as live",
              by["Live Goal"]["health"] == "live",
              f"health={by['Live Goal']['health']}")

        # --- orphan commitment -------------------------------------------------
        check("a commitment naming a non-existent goal is flagged",
              v["counts"]["orphan_commitments"] == 1
              and v["orphan_commitments"][0]["title"] == "Orphan C")

        # --- determinism --------------------------------------------------------
        v2 = goals.build(wiki, use_git=False)
        check("the computation is deterministic for an unchanged corpus",
              goals.render(v) == goals.render(v2))

        # --- it must not write ---------------------------------------------------
        before = {}
        for root, _d, fs in os.walk(wiki):
            for fn in fs:
                p = os.path.join(root, fn)
                before[p] = os.path.getmtime(p), open(p, encoding="utf-8").read()
        goals.build(wiki, use_git=False)
        goals.render(goals.build(wiki, use_git=False))
        after = {}
        for root, _d, fs in os.walk(wiki):
            for fn in fs:
                p = os.path.join(root, fn)
                after[p] = os.path.getmtime(p), open(p, encoding="utf-8").read()
        check("building the view writes nothing to wiki/",
              before == after and len(before) == 10,
              f"{len(before)} files, all unchanged")

        # --- the private commitment is visible HERE but must not leak -----------
        # (the boundary tests own the export cut; this asserts the view carries the tier
        # so a renderer can respect it rather than having to re-derive it)
        priv = [c for st in by["Live Goal"]["commitments"].values() for c in st
                if c["title"] == "Private C"]
        check("a private commitment carries its tier into the view",
              priv and priv[0]["visibility"] == "private",
              "so any renderer can exclude it without guessing")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("All goal-view checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
