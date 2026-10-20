#!/usr/bin/env python3
"""
test_skill_menu.py — every skill a wiki holds is on the menu, in plain words, with words to say.

  python3 tools/test_skill_menu.py
"""

import os
import re
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_menu as M  # noqa: E402

FAILED = []
JARGON = ("branch", "merge", "commit", "repo", "frontmatter", "skill.md", "raw/")


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def main():
    print("skill_menu — what the wiki can do, and the words to say\n")
    held = M.skills_held(pathlib.Path(__file__).resolve().parent.parent)
    menu = M.build_menu(held)
    listed = [s["skill"] for g in menu for s in g["skills"]]
    check("every skill this wiki holds appears exactly once", sorted(listed) == sorted(held),
          str(sorted(set(held) ^ set(listed))))
    check("groups come in the fixed order", [g["group"] for g in menu] == [g for g in M.GROUPS if g in {x["group"] for x in menu}])
    ask = next(g for g in M.build_menu(list(M.MENU)) if g["group"] == "Ask and think")["skills"]
    check("within a group, the most useful come first", ask[0]["skill"] == "query", ask[0]["skill"])
    check("an unknown skill still appears, behind the scenes",
          any(s["skill"] == "brand-new" for g in M.build_menu(["brand-new"]) for s in g["skills"]))
    every = [s for g in menu for s in g["skills"]] + [s for g in M.build_menu(list(M.MENU)) for s in g["skills"]]
    check("every entry carries words to say", all(s["say"].strip() for s in every))
    check("words needing one thing first say what to ask for", all(("{x}" in s["say"]) == bool(s["ask"]) for s in every),
          str([s["skill"] for s in every if ("{x}" in s["say"]) != bool(s["ask"])]))
    text = " ".join(f" {s['label']} {s['what']} {s['ask'] or ''} ".lower() for s in every)
    hits = [j for j in JARGON if re.search(r"(?<![a-z])" + re.escape(j) + r"(?![a-z])", text)]
    check("nothing on the menu needs a technical background to read", not hits, str(hits))
    # A plugin can leave a skill note in .claude/skills/ without saving it. Make one, and check the menu ignores it.
    # (It used to name "overview-refresh", a note on one machine, which became a real skill on 20 October 2026.)
    root = pathlib.Path(__file__).resolve().parent.parent
    note = root / ".claude" / "skills" / "zz-note-a-plugin-left" / "SKILL.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("---\nname: zz-note-a-plugin-left\ndescription: test\n---\n")
    try:
        check("the menu only lists skills saved in the wiki, not notes a plugin left",
              "zz-note-a-plugin-left" not in M.skills_held(root))
    finally:
        note.unlink()
        note.parent.rmdir()

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
