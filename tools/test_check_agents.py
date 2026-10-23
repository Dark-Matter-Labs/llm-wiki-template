#!/usr/bin/env python3
"""test_check_agents.py — the any-tool check's own cases, on a throwaway wiki it builds and removes."""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_agents as C  # noqa: E402


def skill(root: pathlib.Path, folder: str, text: str) -> None:
    d = root / ".claude" / "skills" / folder
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(text, encoding="utf-8")


def main() -> int:
    fails = []
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        skill(root, "good-one", "---\nname: good-one\ndescription: Does a thing.\n---\n")
        p = C.problems(root)
        if not ("AGENTS.md is missing" in p and any(".agents/skills" in x for x in p)):
            fails.append("a bare wiki reports the missing AGENTS.md and link")
        (root / "AGENTS.md").write_text("x", encoding="utf-8")
        (root / ".agents").mkdir()
        (root / ".agents" / "skills").symlink_to("../.claude/skills")
        if C.problems(root):
            fails.append(f"a good wiki passes: {C.problems(root)}")
        (root / ".claude" / "skills" / ".archive").mkdir()
        if C.problems(root):
            fails.append(f"a hidden folder is ignored: {C.problems(root)}")
        skill(root, "Bad_Name", "---\nname: Bad_Name\ndescription: x\n---\n")
        skill(root, "wrong", "---\nname: other\ndescription: x\n---\n")
        skill(root, "no-desc", "---\nname: no-desc\n---\n")
        p = C.problems(root)
        for want in ("Bad_Name: name must", "wrong: name is other", "no-desc: no description"):
            if not any(x.startswith(want) for x in p):
                fails.append(f"reports {want!r}: got {p}")
    for f in fails:
        print(f"  FAIL  {f}")
    print(f"{len(fails)} check(s) failed" if fails else "all checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
