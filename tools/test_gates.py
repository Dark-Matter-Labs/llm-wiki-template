#!/usr/bin/env python3
"""Does gates.py run the gates the repository actually declares?

The whole value of this tool is that the newsletter job stops trusting a hand-written list.
So the cases that matter are the ones where a hand-written list would look identical and be
wrong: a gate added to checks.yml must be picked up without anybody editing this tool, a gate
removed must stop running, and an extraction that finds nothing must fail loudly rather than
report a clean sweep of zero gates.

Case 6 is the mutation. It deletes the step that would have caught the 2026-09-18 incident
and asserts the derived list no longer contains it, which is the only proof that the list is
read from the file rather than remembered.

    python3 tools/test_gates.py
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent / "gates.py"

CHECKS = """\
name: Wiki checks
on:
  pull_request:
  workflow_dispatch:
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Schema
        # A comment between the name and the run line, as every real file has.
        run: python3 tools/passing_one.py --check

      - name: A shell gate
        run: bash tools/passing_two.sh

      - name: Something that is not a tool
        run: echo hello

      - name: Tool tests
        run: |
          python3 tools/never_runs.py
          echo "a multi-line block is shell, not a gate"
"""

PASS_PY = "#!/usr/bin/env python3\nprint('fine')\n"
PASS_SH = "#!/bin/bash\necho fine\n"
FAIL_PY = "#!/usr/bin/env python3\nimport sys\nprint('the link is split across a newline')\nsys.exit(1)\n"
NEVER = "#!/usr/bin/env python3\nimport sys\nsys.exit(1)\n"


def world(checks: str = CHECKS, failing: bool = False) -> pathlib.Path:
    """A throwaway repository: tools/gates.py, a checks.yml, and the tools it names."""
    root = pathlib.Path(tempfile.mkdtemp()) / "a-wiki"
    (root / "tools").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    shutil.copy(TOOL, root / "tools" / "gates.py")
    (root / ".github" / "workflows" / "checks.yml").write_text(checks, encoding="utf-8")
    (root / "tools" / "passing_one.py").write_text(FAIL_PY if failing else PASS_PY, encoding="utf-8")
    (root / "tools" / "passing_two.sh").write_text(PASS_SH, encoding="utf-8")
    (root / "tools" / "never_runs.py").write_text(NEVER, encoding="utf-8")
    return root


def run(root: pathlib.Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(root / "tools" / "gates.py"), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        if detail:
            print(f"        {detail.strip()[:400]}")
        failures.append(name)


print("gates.py")

# 1. Every single-line tool step is found, python3 and bash alike.
root = world()
rc, out = run(root, "--list")
listed = out.strip().splitlines()
check("1. finds both single-line gates",
      listed == ["python3 tools/passing_one.py --check", "bash tools/passing_two.sh"], out)

# 2. A run: line that is not a tool invocation is left alone.
check("2. ignores a non-tool run: step", "echo hello" not in out, out)

# 3. The body of a multi-line block is not mistaken for a gate.
check("3. ignores the contents of a run: | block", "never_runs" not in out, out)

# 4. A clean repository exits 0 and says how many gates it ran.
rc, out = run(root)
check("4. all gates passing exits 0", rc == 0 and "all 2 gates pass" in out, out)

# 5. One failing gate fails the run and names it. This is the whole point: on 2026-09-18 the
#    newsletter job reported success while the issue it had written did not pass.
rc, out = run(world(failing=True))
check("5. a failing gate exits 1 and is named",
      rc == 1 and "FAIL  python3 tools/passing_one.py --check" in out
      and "the link is split across a newline" in out, out)

# 6. THE MUTATION. Remove the gate from checks.yml and it stops being run. A tool with the
#    list baked in would pass cases 1 to 5 unchanged and fail only here.
mutated = CHECKS.replace("        run: python3 tools/passing_one.py --check\n", "")
rc, out = run(world(checks=mutated), "--list")
check("6. a gate deleted from checks.yml stops running",
      rc == 0 and "passing_one" not in out and "passing_two" in out, out)

# 7. A gate added to checks.yml is picked up with no edit to this tool.
added = CHECKS.replace(
    "      - name: A shell gate\n",
    "      - name: A gate added later\n        run: python3 tools/passing_three.py --check\n\n"
    "      - name: A shell gate\n")
root = world(checks=added)
(root / "tools" / "passing_three.py").write_text(PASS_PY, encoding="utf-8")
rc, out = run(root)
check("7. a gate added to checks.yml is picked up", rc == 0 and "all 3 gates pass" in out, out)

# 8. Zero gates is a broken parser, not a clean repository. Same lesson as the discovery glob
#    in checks.yml: a check that can pass vacuously is not a check.
rc, out = run(world(checks="name: Wiki checks\njobs:\n  checks:\n    steps: []\n"))
check("8. finding no gates fails loudly", rc != 0 and "broken parser" in out, out)

# 9. A missing checks.yml is a failure, not an empty pass.
root = world()
(root / ".github" / "workflows" / "checks.yml").unlink()
rc, out = run(root)
check("9. a missing checks.yml fails", rc != 0 and "no .github/workflows/checks.yml" in out, out)

print()
if failures:
    print(f"{len(failures)} failure(s): {', '.join(failures)}")
    sys.exit(1)
print("all cases pass")
