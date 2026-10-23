#!/usr/bin/env python3
"""test_check_budgets.py — the budget check's own cases, on a throwaway wiki it builds and removes."""

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_budgets as B  # noqa: E402


def main() -> int:
    fails = []
    check = lambda name, ok: fails.append(name) if not ok else print(f"  ok   {name}")
    check("a description's bytes are counted", B.description_bytes("---\nname: x\ndescription: Does a thing.\n---\nBody") == len("Does a thing."))
    check("a multi-line description stops at the next field",
          B.description_bytes("---\nname: x\ndescription: one\n  two\nother: y\n---\n") == len("one\n  two"))
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        (root / ".claude" / "rules").mkdir(parents=True)
        (root / ".claude" / "skills" / "big").mkdir(parents=True)
        (root / "CLAUDE.md").write_text("x" * 1000)
        (root / ".claude" / "rules" / "r.md").write_text("y" * 500)
        (root / ".claude" / "skills" / "big" / "SKILL.md").write_text("---\nname: big\ndescription: abc\n---\n" + "z" * 2000)
        m = B.measure(root)
        check("always loaded is CLAUDE.md, rules and descriptions", m["always_loaded"] == 1503)
        b = B.initial_budgets(m)
        check("the first budget leaves headroom", b["always_loaded"] >= m["always_loaded"] * 1.15)
        check("today's sizes pass their own budget", B.problems(m, b) == [])
        m2 = dict(m, always_loaded=b["always_loaded"] + 1)
        check("growing past the budget is reported", any("always loaded" in p for p in B.problems(m2, b)))
        m3 = dict(m, largest_skill=b["skill_body_max"] + 1)
        check("an oversized skill is reported by name", any("big skill" in p for p in B.problems(m3, b)))
    for f in fails:
        print(f"  FAIL {f}")
    print(f"{len(fails)} check(s) failed" if fails else "all checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
