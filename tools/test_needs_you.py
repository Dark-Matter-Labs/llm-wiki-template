#!/usr/bin/env python3
"""
test_needs_you.py — the "Needs you" list says what needs a person, in their words, with one action each.

Written 2026-10-12, first for Leon: "see what needs his attention and say yes to it". The list is the
data behind a view in the app; these tests pin the choices that view depends on — what is offered a
yes, what is not, the order, and that nothing in it needs a technical background to read.

  python3 tools/test_needs_you.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import needs_you as N  # noqa: E402

FAILED = []
JARGON = ("raw/", "branch", "pull request", " pr ", "merge", "commit", "repo", "frontmatter", "baseline", "ci ")


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def proposal(n, state, title="Overview brought up to date", summary="Adds the October work."):
    return {"number": n, "title": title, "url": f"https://x/pull/{n}", "since": "2026-10-10", "state": state,
            "summary": summary}


def main():
    print("needs_you — what needs a person, and the one thing to do about it\n")

    waiting = {"proposals": [proposal(1, "checked and ready"), proposal(2, "a check says something is wrong"),
                             proposal(3, "a draft, not finished"), proposal(4, "still being checked")],
               "never_proposed": [{"pages": 2, "lines": 40}],
               "stand_behind": {"available": True, "total_unvalidated": 30,
                                "pages": [{"title": "Muga Valley", "leaned_on_by": 12, "visibility": "internal"}]}}
    items = N.build_items(
        waiting=waiting,
        coach=[{"id": "unfiled-sources", "priority": 80, "text": "3 document(s) you added haven't been filed.",
                "say": "Ingest the documents that haven't been filed yet.", "why": "Files in raw/ no page cites."}],
        contradictions=[("Relationalized Finance", "SI-SF Codex 25")],
        overview={"behind": 21, "since": "2026-09-24"},
        quotes_not_in_source=4,
        descriptions={"Relationalized Finance": "Bollier and Hulst on finance as relationship.",
                      "SI-SF Codex 25": "System investing and system finance."},
    )
    kinds = [i["kind"] for i in items]

    check("a checked, ready change is offered a yes", items[0]["kind"] == "proposal" and items[0]["action"]["type"] == "yes",
          str(items[0]))
    check("its yes says what it does in plain words", "save" in items[0]["action"]["label"].lower(), items[0]["action"]["label"])
    check("its explanation is the change's own summary", items[0]["why"] == "Adds the October work.")
    failing = [i for i in items if i["kind"] == "proposal" and i["ref"] == 2]
    check("a change a check objects to is shown, but never offered a yes",
          failing and failing[0]["action"]["type"] != "yes", str(failing))
    check("a draft is not shown at all", not any(i["kind"] == "proposal" and i["ref"] == 3 for i in items))
    check("a change still being checked waits, without a yes",
          [i["action"]["type"] for i in items if i["kind"] == "proposal" and i["ref"] == 4] == ["wait"])

    c = next(i for i in items if i["kind"] == "contradiction")
    check("a contradiction shows both pages with what each says, and asks which wins",
          c["action"]["type"] == "decide" and "Bollier" in c["action"]["pages"][0]["says"]
          and "System investing" in c["action"]["pages"][1]["says"], str(c))
    check("an overview 21 pages behind is listed", "overview" in kinds)
    check("an overview a few pages behind is not",
          "overview" not in [i["kind"] for i in N.build_items({}, [], [], {"behind": 3, "since": "x"}, 0, {})])
    check("quotes not found in their source are one item, counted", sum(k == "quotes" for k in kinds) == 1
          and "4 quotes are" in next(i for i in items if i["kind"] == "quotes")["title"])
    co = next(i for i in items if i["kind"] == "suggestion")
    check("a coach suggestion carries the words to say to Claude", co["action"]["say"].startswith("Ingest"))
    sb = next(i for i in items if i["kind"] == "stand_behind")
    check("the most leaned-on unconfirmed page is offered to stand behind", "Muga Valley" in sb["title"]
          and sb["action"]["type"] == "confirm")
    check("work never put forward is listed", "never_proposed" in kinds)

    # Found on the first real run (georgia-llm-wiki): the coach's "work waiting to be saved" sat
    # beside the very proposals it counts. A suggestion that repeats an item already listed goes.
    dup = N.build_items({"proposals": [proposal(9, "checked and ready")]},
                        [{"id": "waiting", "text": "3 piece(s) of work are waiting", "say": "x", "why": "y"},
                         {"id": "overview", "text": "Your overview is 17 days behind", "say": "x", "why": "y"}],
                        [], {"behind": 8, "since": "x"}, 0, {})
    check("a suggestion that repeats a listed item is dropped",
          [i["kind"] for i in dup] == ["proposal", "overview"], str([i["kind"] for i in dup]))
    alone = N.build_items({}, [{"id": "overview", "text": "Your overview is 17 days behind", "say": "x", "why": "y"}],
                          [], {"behind": 2, "since": "x"}, 0, {})
    check("but kept when nothing else says it", [i["kind"] for i in alone] == ["suggestion"])

    # Concerns, added 2026-10-12 at Gurden's ask ("open items, concerns, things to do"): the wiki's
    # own open questions, lines that wait on a named person, and checks that are failing.
    oq = {"totals": {"items": 37, "pages": 8, "waits": 2},
          "pages": [{"title": "Bioregional Financing Facility", "sections": [{"heading": "Open questions",
                     "items": ["**Bridge or buffer?** The book says both", "**Who governs, and how?** Arc 1 gives"]}],
                     "waits": [{"who": "Gurden", "line": "**Linking to the rest** *(Gurden to confirm the addresses)*"}]}]}
    con = N.build_items({}, [], [], {}, 0, {}, open_questions=oq, checks_failing=True)
    kinds_c = [i["kind"] for i in con]
    check("failing checks come first among concerns", kinds_c[0] == "broken", str(kinds_c))
    q = next(i for i in con if i["kind"] == "questions")
    check("open questions are one item, counted, quoting the first ones in plain words",
          "37" in q["title"] and "Bridge or buffer?" in q["why"] and "**" not in q["why"], q["why"])
    check("an open question is quoted by its headline, not a long sentence",
          q["why"] == "Among them: Bridge or buffer? Who governs, and how?", q["why"])
    check("counts read as a person writes them", "(s)" not in " ".join(i["title"] for i in items + con))
    w = next(i for i in con if i["kind"] == "waits")
    check("a line waiting on a named person says who", "Gurden" in w["why"], w["why"])
    check("every item says which group it belongs to",
          all(i.get("group") in ("yes", "concern", "todo") for i in items + con))
    check("thinking work hands off to Claude with the words ready",
          all(i["action"]["type"] in ("yes", "look", "wait", "decide", "confirm") or i["action"].get("say")
              for i in items + con))

    order = [i["kind"] for i in items]
    check("ready changes come first, then decisions, then checks, then the rest",
          order.index("proposal") < order.index("contradiction") < order.index("quotes") < order.index("suggestion"),
          str(order))

    text = " ".join(f" {i['title']} {i['why']} {i['action']['label']} ".lower() for i in items)
    hits = [j for j in JARGON if j in text]
    check("nothing in the list needs a technical background to read", not hits, str(hits))
    check("no item names who wrote anything", not any("author" in i or "by" in i for i in items))
    check("every item has exactly one action", all(isinstance(i.get("action"), dict) for i in items))

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
