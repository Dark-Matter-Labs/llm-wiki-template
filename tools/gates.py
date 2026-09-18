#!/usr/bin/env python3
"""gates.py — run the gates this repository's own `checks.yml` runs.

WHY THIS EXISTS. The monthly newsletter workflow opens a pull request with the default
`GITHUB_TOKEN`, and GitHub deliberately does not fire `pull_request` or `push` workflows for
a PR opened by `github-actions[bot]`. The protection against recursive runs is also, here, a
hole: `.github/workflows/checks.yml` never ran on a newsletter branch in any of the eleven
repositories. Confirmed 2026-09-18 on Dark-Matter-Labs/malik-llm-wiki#68, where
`gh pr checks 68` reported no checks at all and the issue carried a `[[Page|alias]]` link
wrapped across a newline, which drops the edge from the link graph without any visible error.
`tools/export.py --check` catches that. Nothing ran it.

So the job that writes the issue runs the gates itself, before the pull request is opened.

WHY IT READS `checks.yml` INSTEAD OF LISTING GATES. The newsletter workflow is a SHARED file:
one copy, eleven repositories. `checks.yml` is not, and the eleven do not agree — measured
2026-09-18, indy-llm-wiki runs 27 gate steps, power-project-wiki 17, and the other nine 16. A
list of gate names written into the shared workflow would therefore be one list applied to
eleven different gate sets, wrong in every repository at once and drifting further with each
gate anybody adds. This repo has already paid for that shape: `checks.yml` used to name each
test suite by hand, and three suites turned out never to have run in CI at all.

So the list is derived. Whatever a repository's own `checks.yml` runs, this runs, which makes
the result a prediction of the verdict that repository's pull request would have reached.

WHAT IT PICKS UP. Every step whose `run:` is a single line invoking `python3 tools/...` or
`bash tools/...`. That is every gate in all eleven files today.

WHAT IT DOES NOT. Multi-line `run: |` blocks, which are shell rather than a gate, and in
practice the discovery loop over `tools/test_*.py`. Those suites test the tools, not the page
a newsletter just wrote, and executing an arbitrary shell block extracted from YAML buys
little and risks more. Single-line `python3 tools/test_*.py` steps are picked up, because the
rule is about the shape of the step and a rule with an exception in it is a rule with a hole.

An extraction that finds nothing is a broken parser, not a clean repository, so zero gates is
a failure and says so.

    python3 tools/gates.py            # run them, report, exit 1 on any failure
    python3 tools/gates.py --list     # print the commands, run nothing
    python3 tools/gates.py --check    # same as the default; for symmetry with every other gate
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKS = ROOT / ".github" / "workflows" / "checks.yml"

#: A single-line `run:` invoking a tool in this repo. Anything else is left alone.
GATE_RE = re.compile(r"^\s+run:\s+((?:python3|bash)\s+tools/\S+.*?)\s*$")


def gate_commands(text: str) -> list[str]:
    """The gate commands in a checks.yml, in the order the file runs them.

    Deliberately textual. PyYAML is not in the standard library and this house ships no
    third-party dependency, so the choice is a regex over lines or a YAML parser written
    here, and a hand-rolled parser would be the larger thing to be wrong about.
    """
    found: list[str] = []
    for line in text.splitlines():
        m = GATE_RE.match(line)
        if m:
            found.append(m.group(1))
    return found


def read_gates(path: pathlib.Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"error: no {path.relative_to(ROOT)} to read gates from")
    cmds = gate_commands(path.read_text(encoding="utf-8"))
    if not cmds:
        raise SystemExit(
            f"error: found no gates in {path.relative_to(ROOT)}. That is a broken parser, "
            "not a clean repository - a wiki with no checks does not exist in this federation."
        )
    return cmds


def run_gate(cmd: str) -> tuple[bool, str]:
    argv = shlex.split(cmd)
    if argv[0] not in ("python3", "bash"):
        return False, f"refusing to run {cmd!r}: not a tool invocation"
    if argv[0] == "python3":
        argv[0] = sys.executable
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print the commands, run nothing")
    ap.add_argument("--check", action="store_true", help="run them (the default)")
    args = ap.parse_args()

    cmds = read_gates(CHECKS)

    if args.list:
        for c in cmds:
            print(c)
        return 0

    print(f"{len(cmds)} gates, from {CHECKS.relative_to(ROOT)}")
    failed: list[str] = []
    for c in cmds:
        ok, out = run_gate(c)
        if ok:
            print(f"  ok    {c}")
        else:
            print(f"  FAIL  {c}")
            for line in out.strip().splitlines()[-12:]:
                print(f"          {line}")
            failed.append(c)

    if failed:
        print(f"\n{len(failed)} of {len(cmds)} gates failed:")
        for c in failed:
            print(f"  - {c}")
        return 1
    print(f"\nall {len(cmds)} gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
