#!/usr/bin/env python3
"""
check_agents.py — keep the wiki usable from any coding agent, not only Claude Code.

    python3 tools/check_agents.py --check

Asked for by Gurden on 20 October 2026: the wiki's rules and skills should work in Codex, opencode or any other
tool. AGENTS.md is the shared front door. Skills follow the open Agent Skills format: a folder holding SKILL.md,
whose frontmatter has a `name` equal to the folder's name and a `description`. Codex finds them through
`.agents/skills`, a link to `.claude/skills`; opencode reads `.claude/skills` directly. A skill whose name breaks
the format still works in Claude Code, but other tools skip it without saying so. This check says so.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
LINK = ROOT / ".agents" / "skills"
NAME_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
FRONT_RE = re.compile(r"\A---\n(.*?)\n---", re.S)


def skill_problems(folder: pathlib.Path) -> list[str]:
    """What stops one skill folder loading in other tools. Empty means it loads."""
    f = folder / "SKILL.md"
    if not f.exists():
        return [f"{folder.name}: no SKILL.md"]
    m = FRONT_RE.match(f.read_text(encoding="utf-8"))
    if not m:
        return [f"{folder.name}: SKILL.md has no frontmatter"]
    fm = m.group(1)
    name = re.search(r"^name:\s*(.+?)\s*$", fm, re.M)
    out = []
    got = name.group(1).strip("\"'") if name else ""
    if got != folder.name:
        out.append(f"{folder.name}: name is {got or 'missing'!s}, must equal the folder name")
    elif len(got) > 64 or not NAME_RE.fullmatch(got):
        out.append(f"{folder.name}: name must be lowercase letters and digits joined by single hyphens, 64 at most")
    if not re.search(r"^description:\s*\S", fm, re.M):
        out.append(f"{folder.name}: no description")
    return out


def problems(root: pathlib.Path = ROOT) -> list[str]:
    skills, link = root / ".claude" / "skills", root / ".agents" / "skills"
    out = [] if (root / "AGENTS.md").exists() else ["AGENTS.md is missing"]
    if not link.exists() or link.resolve() != skills.resolve():
        out.append(".agents/skills must link to .claude/skills (ln -s ../.claude/skills .agents/skills)")
    for d in sorted(p for p in skills.iterdir() if p.is_dir() and not p.name.startswith(".")) if skills.exists() else []:
        out += skill_problems(d)
    return out


def main() -> int:
    found = problems()
    if not found:
        n = sum(1 for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith(".")) if SKILLS.exists() else 0
        print(f"agents OK — AGENTS.md present, {n} skill(s) load in any tool")
        return 0
    print("agents — other tools would miss part of this wiki:")
    for p in found:
        print(f"  {p}")
    return 1 if "--check" in sys.argv else 0


if __name__ == "__main__":
    sys.exit(main())
