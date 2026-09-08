#!/usr/bin/env python3
"""
Properties of check_skill_links.py.

The one that matters is `the notion-sync case`: a shared skill linking a private page is
exactly what shipped to ten repos on 2026-09-08 before anyone read the file.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_skill_links as csl  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def repo(tmp, *, skills: dict, pages: dict, shared: list[str]):
    """skills: {name: body} · pages: {title: visibility} · shared: relpaths the syncer copies."""
    root = pathlib.Path(tmp)
    (root / "design").mkdir(parents=True, exist_ok=True)
    (root / "design" / "shared-layer.json").write_text(
        json.dumps({"source": "t", "siblings": [], "shared": shared}), encoding="utf-8")
    (root / "wiki").mkdir(exist_ok=True)
    for i, (title, vis) in enumerate(pages.items()):
        (root / "wiki" / f"p{i}.md").write_text(
            f"---\ntype: concept\ntitle: {title}\nvisibility: {vis}\n---\n\nbody\n", encoding="utf-8")
    for name, body in skills.items():
        d = root / ".claude" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(body, encoding="utf-8")
    csl.ROOT, csl.SKILLS = root, root / ".claude" / "skills"
    csl.WIKI, csl.MANIFEST = root / "wiki", root / "design" / "shared-layer.json"
    return root


SH = ".claude/skills/{}/SKILL.md"


def main():
    print("check_skill_links — shared skills may not link pages\n")

    # THE CASE THIS EXISTS FOR.
    with tempfile.TemporaryDirectory() as t:
        repo(t, skills={"notion": "See [[The Option Book]] for the figures.\n"},
             pages={"The Option Book": "private"}, shared=[SH.format("notion")])
        check("a shared skill linking a PRIVATE page fails", csl.main(["--check"]) == 1)
        check("...and the report names the page and its tier",
              csl.audit() == [(SH.format("notion"), "The Option Book", "private")])

    with tempfile.TemporaryDirectory() as t:
        repo(t, skills={"delta": "Open [[Axioms Register]] and read it.\n"},
             pages={"Axioms Register": "internal"}, shared=[SH.format("delta")])
        check("an internal page is refused too — the sibling may not have it at all",
              csl.main(["--check"]) == 1)

    # Placeholders. Fourteen of eighteen real links were these; flagging them would kill the gate.
    with tempfile.TemporaryDirectory() as t:
        repo(t, skills={"ingest": "Cross-link with [[Page Title]] style. Use [[link]] and [[entity]].\n"},
             pages={"Something Real": "public"}, shared=[SH.format("ingest")])
        check("syntax placeholders that resolve to nothing are allowed",
              csl.main(["--check"]) == 0)

    # A local skill is not the shared layer's business. The shared list must be NON-EMPTY here:
    # with shared=[] the tool used to exit early as "no manifest" and this passed for the wrong
    # reason — it could not fail, which mutation testing proved by deleting the filter it guards.
    with tempfile.TemporaryDirectory() as t:
        repo(t, skills={"crm": "See [[Indy Johar]].\n", "delta": "no links here\n"},
             pages={"Indy Johar": "private"}, shared=[SH.format("delta")])
        check("a LOCAL skill may link anything, private included",
              csl.main(["--check"]) == 0)

    with tempfile.TemporaryDirectory() as t:
        root = repo(t, skills={"x": "no links\n"}, pages={}, shared=[])
        (root / "design" / "shared-layer.json").write_text("{ not json", encoding="utf-8")
        check("an unreadable manifest FAILS rather than passing quietly",
              csl.main(["--check"]) == 1)

    # Aliased links are still links.
    with tempfile.TemporaryDirectory() as t:
        repo(t, skills={"q": "See [[The Option Book|the book]].\n"},
             pages={"The Option Book": "private"}, shared=[SH.format("q")])
        check("an aliased link is caught, not slipped past", csl.main(["--check"]) == 1)

    # Degrade, do not crash — but do not pass either. A gate that cannot tell which skills
    # travel has not checked anything, and reporting success for that is the whole failure
    # mode this file exists to prevent.
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        (root / ".claude" / "skills").mkdir(parents=True)
        csl.ROOT, csl.SKILLS = root, root / ".claude" / "skills"
        csl.WIKI, csl.MANIFEST = root / "wiki", root / "design" / "nope.json"
        check("a missing manifest fails cleanly rather than passing or crashing",
              csl.main(["--check"]) == 1)

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
