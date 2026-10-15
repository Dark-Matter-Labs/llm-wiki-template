#!/usr/bin/env python3
"""test_crm.py — what tools/crm.py must never get wrong.

  1. `counts` carries numbers only: it feeds a page that is published (locked), so a name in it
     would be a CRM leak.
  2. A follow-up is overdue, due soon, or missing by its date and stage, and a closed or dormant
     relationship is never nagged about.
  3. Logging appends a dated line, replaces the "none logged yet" placeholder, and moves
     last_contact forward only: an older meeting logged late must not make a card look stale.
  4. Logging refuses what would invent state: a future-dated interaction, a due date with no step,
     an unknown stage, and any card that is not private.
  5. Leads leave out organisations already carded or linked from a card, people, places and us.

  python3 tools/test_crm.py
"""
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crm  # noqa: E402

TODAY = dt.date(2026, 10, 15)


def card(root, kind, slug, title, **f):
    fields = {"crm_stage": "active", "crm_owner": "unset", "last_contact": "unset", "next_action": "unset",
              "visibility": "private"} | f
    fm = "\n".join(f"{k}: {v}" for k, v in fields.items())
    p = root / "wiki" / "crm" / kind / f"{slug}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\ntype: entity\ntitle: {title}\n{fm}\ntimestamp: 2026-07-17\n---\n\n# {title}\n\n"
                 "**Who.** Someone.\n\n**Interactions.**\n- _None logged yet._\n\n**Next.** none set.\n",
                 encoding="utf-8")
    return p


def page(root, name, title, tags, typ="entity"):
    p = root / "wiki" / f"{name}.md"
    p.write_text(f"---\ntype: {typ}\ntitle: {title}\ntags: [{', '.join(tags)}]\ndescription: d\n---\nbody\n",
                 encoding="utf-8")


def check(name, ok):
    print(("  PASS  " if ok else "  FAIL  ") + name)
    return ok


def main():
    results = []
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        card(root, "contacts", "ana", "Ana Example", next_action='"send the paper"', next_action_due="2026-10-10")
        card(root, "contacts", "ben", "Ben Example", next_action='"call back by 2026-10-18"')
        card(root, "contacts", "cy", "Cy Example")                                    # open, no next step
        card(root, "accounts", "old", "Old Org", crm_stage="closed", next_action_due="2026-01-01",
             next_action='"x"')
        card(root, "contacts", "quiet", "Quiet Example", last_contact="2026-05-01", next_action='"y"')
        r = crm.due(crm.cards(root), TODAY, 7)
        results.append(check("an overdue step is overdue", [x["title"] for x in r["overdue"]] == ["Ana Example"]))
        results.append(check("a date inside next_action still counts", [x["title"] for x in r["due_soon"]] == ["Ben Example"]))
        results.append(check("an open card with no step is listed", [x["title"] for x in r["no_next_step"]] == ["Cy Example"]))
        results.append(check("a closed relationship is never nagged", all(x["title"] != "Old Org" for x in r["overdue"])))
        results.append(check("gone quiet after 90 days", [x["title"] for x in r["gone_quiet"]] == ["Quiet Example"]))
        n = json.dumps(crm.counts(r))
        results.append(check("counts carry no names", "Example" not in n and "Org" not in n))

        p = card(root, "contacts", "dee", "Dee Example", last_contact="2026-10-01")
        crm.log(p, kind="meeting", note="Talked\nabout the fund.", when=dt.date(2026, 9, 1), today=TODAY,
                nxt="Send the brief", due_on=dt.date(2026, 10, 20), why="they asked", stage="prospect")
        text = p.read_text()
        results.append(check("the dated line is appended, on one line", "- 2026-09-01 · meeting · Talked about the fund." in text))
        results.append(check("the placeholder is gone", "None logged yet" not in text))
        results.append(check("last_contact never moves back", "last_contact: 2026-10-01" in text))
        results.append(check("next step, date and reason are recorded",
                             'next_action: "Send the brief (why: they asked)"' in text and "next_action_due: 2026-10-20" in text))
        results.append(check("the stage is set only when given", "crm_stage: prospect" in text))
        crm.log(p, kind="call", note="Second call.", when=TODAY, today=TODAY)
        text = p.read_text()
        results.append(check("a second entry follows the first", text.index("2026-09-01 ·") < text.index("2026-10-15 · call")))
        results.append(check("last_contact moves forward", "last_contact: 2026-10-15" in text))

        def refuses(**kw):
            args = {"kind": "meeting", "note": "n", "when": TODAY, "today": TODAY} | kw
            try:
                crm.log(p, **args)
            except SystemExit:
                return True
            return False
        results.append(check("refuses a future-dated interaction", refuses(when=TODAY + dt.timedelta(days=1))))
        results.append(check("refuses a due date with no step", refuses(due_on=TODAY)))
        results.append(check("refuses an unknown stage", refuses(stage="hot")))
        results.append(check("refuses an empty note", refuses(note="  ")))
        pub = card(root, "contacts", "pub", "Pub Example", visibility="internal")
        try:
            crm.log(pub, kind="note", note="n", when=TODAY, today=TODAY)
            refused = False
        except SystemExit:
            refused = True
        results.append(check("refuses a card that is not private", refused))

        page(root, "known-org", "Known Org", ["funding"])
        page(root, "linked-org", "Linked Org", ["funding"])
        page(root, "new-org", "New Org", ["water"])
        page(root, "a-person", "A Person", ["person"])
        page(root, "a-place", "A Place", ["place"])
        page(root, "us", "Us", ["dark-matter-labs"])
        page(root, "idea", "An Idea", ["water"], typ="concept")
        (root / "wiki" / "mentions.md").write_text("---\ntitle: M\n---\n[[New Org]] and [[New Org]]\n")
        card(root, "accounts", "known-org", "Known Org")
        p2 = card(root, "contacts", "eve", "Eve Example")
        p2.write_text(p2.read_text() + "\nWorks with [[Linked Org]].\n")
        found = [x["title"] for x in crm.leads(root)]
        results.append(check("leads are uncarded, unlinked organisations only", found == ["New Org"]))
        results.append(check("leads count how often the wiki links them", crm.leads(root)[0]["mentions"] == 2))
        (root / "design").mkdir(exist_ok=True)
        (root / "design" / "federation.json").write_text('{"role": "commons"}')
        def refused_in_commons(args):
            try:
                crm.main(["--root", str(root)] + args)
            except SystemExit as e:
                return "shared wiki" in str(e)
            return False
        results.append(check("a shared wiki logs nothing", refused_in_commons(["log", "dee", "--kind", "note", "--note", "n"])))
        results.append(check("a shared wiki finds no leads", refused_in_commons(["leads"])))
    print("\nall passed" if all(results) else "\nFAILED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
