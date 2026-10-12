#!/usr/bin/env python3
"""
test_view_modules.py — the data behind the full view's modules: the map of big areas, the onboarding
list, what moved, and how work travels.

  python3 tools/test_view_modules.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import view_modules as V  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(slug, links, kind="concept", desc="", path=None):
    return {"slug": slug, "title": slug.replace("-", " ").title(), "type": kind, "description": desc,
            "outbound_links": links, "inbound_links": [], "path": path or f"wiki/{slug}.md"}


def main():
    print("view_modules — the full view's data\n")

    # Two tight groups joined by one link, and a lone pair that is too small to be an area.
    g1 = ["finance", "capital", "funds", "returns", "risk"]
    g2 = ["ocean", "whales", "fisheries", "seas"]
    nodes = [page(s, [t.replace("-", " ").title() for t in g1 if t != s]) for s in g1]
    nodes += [page(s, [t.replace("-", " ").title() for t in g2 if t != s]) for s in g2]
    nodes[0]["outbound_links"].append("Ocean")
    nodes += [page("lonely-a", ["Lonely B"]), page("lonely-b", ["Lonely A"])]
    nodes += [page("overview", ["Finance", "Ocean"], kind="overview"), page("leon", ["Finance"], path="wiki/crm/contacts/leon.md")]
    m = V.areas(nodes)
    sizes = sorted(a["size"] for a in m["areas"])
    check("pages that link to each other become one area each", sizes == [4, 5], str(m["areas"]))
    check("an area is named by its most linked page", {a["label"] for a in m["areas"]} == {"Finance", "Ocean"},
          str([a["label"] for a in m["areas"]]))
    check("the link between two areas is counted", m["links"] and m["links"][0]["weight"] == 1, str(m["links"]))
    check("a pair too small to be an area is left off the map", all(a["size"] >= V.MIN_AREA for a in m["areas"]))
    check("the overview and relationship pages are not on the map",
          not any(t in ("Overview", "Leon") for a in m["areas"] for t in a["pages"]))
    check("each area lists only its few most linked pages", all(len(a["pages"]) <= V.TOP_PAGES for a in m["areas"]))
    check("the same wiki always draws the same map", V.areas(nodes) == m)
    many = [page(f"p{i}-{j}", [f"P{i}-{k}" for k in range(4) if k != j]) for i in range(20) for j in range(4)]
    check("the map never shows more than a calm number of areas", len(V.areas(many)["areas"]) <= V.MAX_AREAS)

    steps = V.onboarding(raw_files=5, summaries=2, ops={"query": 0, "contribute": 1, "joker": 0},
                         stood_behind=0, overview_written=True)
    labels = {s["label"]: s for s in steps}
    check("finished steps are ticked", labels["Add your first sources"]["done"] and labels["Share something with the team"]["done"])
    check("unfinished steps carry the words to say", not labels["Ask your wiki a question"]["done"]
          and labels["Ask your wiki a question"]["say"])
    check("the onboarding list stays short", len(steps) <= 8)

    t = V.travels({"role": "spoke", "contributes_to": ["rz-commons", "bioregional-finance-wiki"], "reads_from": None},
                  {"available": True, "targets": [{"commons": "rz-commons", "eligible": 3, "top": [{"title": "A"}]}]})
    check("how work travels names where it goes and what could go", t["shares_into"] == ["rz-commons", "bioregional-finance-wiki"]
          and t["could_go_up"] == 3, str(t))

    # How the wiki grew: cumulative pages and sources, one point per week (weeks start on Monday).
    g = V.growth([("2026-09-02", "page"), ("2026-09-03", "source"), ("2026-09-15", "page"), ("2026-09-16", "page")],
                 today="2026-09-22")
    check("growth counts up week by week, from the first week to this one",
          [(w["week"], w["pages"], w["sources"]) for w in g] ==
          [("2026-08-31", 1, 1), ("2026-09-07", 1, 1), ("2026-09-14", 3, 1), ("2026-09-21", 3, 1)], str(g))
    check("an empty wiki has no growth line", V.growth([], today="2026-09-22") == [])

    # What kind of work: the log's entries per week, in three plain kinds.
    log = ["## [2026-09-21] ingest | A report", "## [2026-09-21] query  | A question", "## [2026-09-22] rebuild | x",
           "## [2026-09-22] office-hours | an idea", "## [2026-09-01] lint | old", "## [2026-09-22] repair | y (mine)"]
    w = V.work(log, today="2026-09-22", weeks=2)
    check("work is counted per week in three kinds", w["weeks"] == [
        {"week": "2026-09-14", "adding": 0, "thinking": 0, "upkeep": 0},
        {"week": "2026-09-21", "adding": 1, "thinking": 2, "upkeep": 2}], str(w))
    check("work outside the window is left out", sum(sum(v for k, v in x.items() if k != "week") for x in w["weeks"]) == 5)

    # Who stands behind it: validation and confidence, as counts in a fixed order.
    t = V.trust([{"validation": "machine", "confidence": "low"}, {"validation": "self", "confidence": "high"},
                 {"validation": "peer", "confidence": "high"}, {"validation": "collective"}, {}])
    check("pages a person stands behind are counted apart from machine-filed ones",
          t["validation"] == [["Filed by Claude", 2], ["You", 1], ["Others too", 2]], str(t))
    check("confidence is counted low to high, with unknown left out",
          t["confidence"] == [["Low", 1], ["Medium", 0], ["High", 2]], str(t))

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
