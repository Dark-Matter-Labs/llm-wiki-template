#!/usr/bin/env python3
"""test_validation_sweep.py — the sweep sorts stuck pages rightly, and --apply touches only the `self` group."""
import datetime
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validation_sweep as V  # noqa: E402

TODAY = datetime.date(2026, 11, 19)
OLD = "2026-09-01"


def page(title, extra="", body="Plain words.", ts=OLD, validation="machine"):
    return (f"---\ntype: concept\ntitle: \"{title}\"\ntags: [x]\nstatus: draft\nvisibility: private\n"
            f"confidence: medium\nvalidation: {validation}   # a comment\ntimestamp: {ts}\nsources: []\n{extra}"
            f"---\n\n# {title}\n\n{body}\n")


def wiki(root, role, pages):
    (root / "design").mkdir(parents=True)
    (root / "design" / "federation.json").write_text(json.dumps({"role": role, "owner": "owner-login"}))
    for rel, text in pages.items():
        (root / "wiki" / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / "wiki" / rel).write_text(text)
    return root


def main():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))
        ok &= bool(cond)

    with tempfile.TemporaryDirectory() as t:
        w = wiki(pathlib.Path(t) / "own-wiki", "spoke", {
            "plain.md": page("Plain"),
            "recent.md": page("Recent", ts="2026-11-10"),
            "money.md": page("Money", body="The grant was £40,000 for two years."),
            "budget.md": page("Budget for 2027"),
            "goal.md": page("Goal").replace("type: concept", "type: goal"),
            "public.md": page("Public").replace("visibility: private", "visibility: public"),
            "crm/someone.md": page("Someone"),
            "contested.md": page("Contested", extra="contradicts: \"Plain\"\n"),
            "ruling.md": page("Ruling", extra="decides:\n  - claude/x\n"),
            "digest.md": page("Digest", extra="derivation: derivative\n"),
            "seeded.md": page("Seeded", extra="origin: other-wiki\n"),
            "dormant.md": page("Dormant").replace("status: draft", "status: dormant"),
            "empty-by.md": page("Empty by", extra="validated_by: []   # who ticked; empty for machine\n"),
            "already.md": page("Already", validation="self\nvalidated_by: [owner-login]"),
            "index.md": "# Index\n",
            "log/2026-11-19.md": "# log\n",
        })
        got = {rel: (what, why) for rel, _t, what, why in V.sweep(w, 30, TODAY)}
        check("a plain old page is proposed as self (default)", got.get("plain.md") == ("self", "default"), got)
        check("a recent page is left out", "recent.md" not in got)
        check("a sum in passing does not ask the owner", got.get("money.md") == ("self", "default"), got.get("money.md"))
        check("a budget asks the owner", got.get("budget.md") == ("ask", "a budget"))
        check("a goal asks the owner", got.get("goal.md") == ("ask", "a commitment"))
        check("a public page alone does not ask the owner", got.get("public.md") == ("self", "default"))
        check("a CRM card asks the owner", got.get("crm/someone.md") == ("ask", "a named person"))
        check("a contradiction asks the owner", got.get("contested.md") == ("ask", "contested"))
        check("a decision, written as an indented list, asks the owner", got.get("ruling.md") == ("ask", "a decision"))
        check("a scheduled job's page is left", got.get("digest.md", ("",))[0] == "leave")
        check("a page from another wiki is left", got.get("seeded.md", ("",))[0] == "leave")
        check("a dormant page is left", got.get("dormant.md", ("",))[0] == "leave")
        check("an empty validated_by does not block the default", got.get("empty-by.md") == ("self", "default"))
        check("a page already at self, the index and the log are not listed",
              not {"already.md", "index.md", "log/2026-11-19.md"} & set(got))

        rows = V.sweep(w, 30, TODAY)
        n = V.apply(w, rows, TODAY)
        plain = (w / "wiki" / "plain.md").read_text()
        check("apply sets only the self group", n == 4, n)
        check("the default is written in full", "validation: self\nvalidated_by: [owner-login]\n"
              "validated_at: 2026-11-19\nvalidation_note: default\n" in plain, plain)
        check("the rest of the page is unchanged", plain.endswith("# Plain\n\nPlain words.\n") and "machine" not in plain)
        empty_by = (w / "wiki" / "empty-by.md").read_text()
        check("the old empty validated_by line is replaced, not doubled", empty_by.count("validated_by:") == 1)
        check("an ask page is not touched", "validation: machine" in (w / "wiki" / "budget.md").read_text())
        check("running it again changes nothing", V.sweep(w, 30, TODAY) == [r for r in rows if r[2] != "self"])

        c = wiki(pathlib.Path(t) / "team-commons", "commons", {"plain.md": page("Plain")})
        check("a commons page is left for a person there", [r[2] for r in V.sweep(c, 30, TODAY)] == ["leave"])
        try:
            V.apply(c, V.sweep(c, 30, TODAY), TODAY)
            check("apply refuses a commons", False)
        except SystemExit:
            check("apply refuses a commons", True)
        check("--apply refuses another wiki's folder", V.main([str(c), "--apply"]) == 2)

    print("\nall passed" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
