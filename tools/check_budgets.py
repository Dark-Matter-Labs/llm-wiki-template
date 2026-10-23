#!/usr/bin/env python3
"""
check_budgets.py — keep the instructions every session loads from quietly growing back.

    python3 tools/check_budgets.py            # report sizes against the budget
    python3 tools/check_budgets.py --check    # fail when a budget is exceeded (CI)
    python3 tools/check_budgets.py --init     # write design/budgets.json from today's sizes, with headroom

Adapted on 23 October 2026 from nvk/llm-wiki, which checks byte ceilings on its instruction files on every
push. This wiki moved most of CLAUDE.md into `.claude/reference/` on 13 October to save tokens on every turn;
nothing stopped it growing back. Two numbers matter:

- **always loaded**: CLAUDE.md, every file in `.claude/rules/`, and every skill's `description:` line, which
  the agent reads at the start of each session whether or not the skill is used;
- **one skill's body**: the largest SKILL.md, read in full whenever that skill runs.

The budgets live in `design/budgets.json`, one per wiki, because each wiki's CLAUDE.md is its own. A budget is
raised on purpose, by editing that file in a proposed change that says why, never by the tool.
"""

import argparse
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUDGETS = "design/budgets.json"
HEADROOM = 1.15
SKILL_FLOOR = 30000
DESC = re.compile(r"\A---\n(.*?)\n---", re.S)


def description_bytes(skill_md: str) -> int:
    """Bytes of a skill's description: line(s), the part every session loads."""
    m = DESC.match(skill_md)
    if not m:
        return 0
    d = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", m.group(1), re.M | re.S)
    return len(d.group(1).strip().encode("utf-8")) if d else 0


def measure(root: pathlib.Path = ROOT) -> dict:
    size = lambda p: len(p.read_bytes()) if p.exists() else 0
    rules = sorted((root / ".claude" / "rules").glob("*.md"))
    skills = sorted((root / ".claude" / "skills").glob("*/SKILL.md"))
    texts = {s: s.read_text(encoding="utf-8", errors="replace") for s in skills}
    biggest = max(skills, key=lambda s: len(texts[s].encode("utf-8")), default=None)
    return {
        "claude_md": size(root / "CLAUDE.md"),
        "rules": sum(size(r) for r in rules),
        "skill_descriptions": sum(description_bytes(t) for t in texts.values()),
        "always_loaded": size(root / "CLAUDE.md") + sum(size(r) for r in rules)
                         + sum(description_bytes(t) for t in texts.values()),
        "largest_skill": len(texts[biggest].encode("utf-8")) if biggest else 0,
        "largest_skill_name": biggest.parent.name if biggest else "",
    }


def ceil_to(n: float, step: int = 1000) -> int:
    return int(math.ceil(n / step) * step)


def initial_budgets(m: dict) -> dict:
    return {"_comment": "Byte budgets for what every session loads (tools/check_budgets.py). Raise one on purpose, "
                        "in a proposed change that says why.",
            "always_loaded": ceil_to(m["always_loaded"] * HEADROOM),
            "skill_body_max": max(SKILL_FLOOR, ceil_to(m["largest_skill"] * 1.10))}


def problems(m: dict, b: dict) -> list:
    out = []
    if m["always_loaded"] > b["always_loaded"]:
        out.append(f"always loaded is {m['always_loaded']:,} bytes, over its budget of {b['always_loaded']:,} "
                   f"(CLAUDE.md {m['claude_md']:,}, rules {m['rules']:,}, skill descriptions {m['skill_descriptions']:,})")
    if m["largest_skill"] > b["skill_body_max"]:
        out.append(f"the {m['largest_skill_name']} skill is {m['largest_skill']:,} bytes, over the {b['skill_body_max']:,} budget for one skill")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--init", action="store_true")
    a = ap.parse_args(argv)
    m, path = measure(), ROOT / BUDGETS
    if a.init:
        if path.exists():
            print(f"{BUDGETS} already exists; edit it on purpose to change a budget.")
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(initial_budgets(m), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {BUDGETS}: {json.loads(path.read_text())}")
        return 0
    if not path.exists():
        print(f"no {BUDGETS} yet; run with --init to record today's sizes with headroom.")
        return 1 if a.check else 0
    b = json.loads(path.read_text(encoding="utf-8"))
    found = problems(m, b)
    print(f"budgets — always loaded {m['always_loaded']:,} of {b['always_loaded']:,} bytes; "
          f"largest skill {m['largest_skill_name']} {m['largest_skill']:,} of {b['skill_body_max']:,}")
    for p in found:
        print(f"  OVER  {p}")
    if found:
        print("  Move detail into .claude/reference/ or a skill's own references, or raise the budget on purpose.")
    return 1 if found and a.check else 0


if __name__ == "__main__":
    sys.exit(main())
