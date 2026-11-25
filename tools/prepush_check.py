#!/usr/bin/env python3
"""prepush_check.py — run a wiki's own checks before Claude pushes it.

A Claude Code PreToolUse hook (wired in .claude/settings.json). Added 25 November 2026: in the 30 days before,
50 of 94 failed runs across the wikis were the wiki checks, mostly work that was edited after the local checks
ran, or never checked here at all. A failure then surfaced on GitHub, after the push, often in a shared wiki.

What it does: when a Bash command pushes with git, it finds the repository being pushed, and if that repository
has tools/gates.py, it runs it. If any gate fails, the push is stopped and the failures are shown, so they are
fixed first. Anything else passes straight through.

A gate that already fails on main is not this push's doing. Then say so to the owner, and push with
CHECKS_ACKNOWLEDGED=1 in front of the command. That is for a failure that is not yours, never to skip a check.
"""
import json
import os
import re
import shlex
import subprocess
import sys

PUSH_RE = re.compile(r"(^|[;&|]\s*|\s)git(\s+-C\s+\S+)?\s+push\b")


def pushed_repo(command, cwd):
    """The directory whose repository the command pushes, or None if it is not a git push."""
    for part in re.split(r"&&|;|\|\|", command):
        if not PUSH_RE.search(part):
            continue
        if "--delete" in part or re.search(r"\spush\s+\S+\s+:\S", part):
            return None  # deleting a remote branch changes no files
        m = re.search(r"git\s+-C\s+(\S+)", part)
        if m:
            return os.path.expanduser(shlex.split(m.group(1))[0])
        # the nearest `cd <dir>` before the push, if any
        before = command[: command.find(part)]
        cds = re.findall(r"(?:^|&&|;)\s*cd\s+(\S+)", before)
        return os.path.expanduser(shlex.split(cds[-1])[0]) if cds else cwd
    return None


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if "CHECKS_ACKNOWLEDGED=1" in command:
        return 0
    repo = pushed_repo(command, event.get("cwd") or os.getcwd())
    if not repo:
        return 0
    try:
        top = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return 0
    if not os.path.exists(os.path.join(top, "tools", "gates.py")):
        return 0
    run = subprocess.run([sys.executable, "tools/gates.py"], cwd=top, capture_output=True, text=True,
                         timeout=600)
    if run.returncode == 0:
        return 0
    tail = "\n".join((run.stdout + run.stderr).strip().splitlines()[-15:])
    print(f"The wiki's own checks fail in {top}, so this push is stopped. Fix what they report, then push.\n"
          f"If the same gate already fails on main and it is not this change's doing, tell the owner and\n"
          f"push with CHECKS_ACKNOWLEDGED=1 in front of the command.\n\n{tail}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
