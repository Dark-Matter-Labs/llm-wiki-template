#!/usr/bin/env python3
"""Does check_frontmatter actually fire?

The gate is trivial enough to look obviously correct, which is how the last three
unfireable checks in this federation got written. Case 6 mutates the failure exit away
and asserts case 2 stops failing, so a gate that quietly stops working fails this file
rather than passing it.

    python3 tools/test_check_frontmatter.py
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent / "check_frontmatter.py"

CLEAN = '---\ntype: concept\ntitle: "A Title: With a Colon"\n---\n\nBody.\n'
BROKEN = "---\ntype: concept\ntitle: A Title: With a Colon\n---\n\nBody.\n"
NO_FM = "# Just a heading\n\nNo frontmatter here.\n"
LIST_FM = "---\n- one\n- two\n---\n\nBody.\n"


def run(pages: dict[str, str], args=(), script: pathlib.Path = TOOL):
    """Lay out a throwaway wiki and run the gate against it."""
    root = pathlib.Path(tempfile.mkdtemp())
    (root / "tools").mkdir()
    (root / "wiki").mkdir()
    shutil.copy(script, root / "tools" / "check_frontmatter.py")
    for name, text in pages.items():
        (root / "wiki" / name).write_text(text)
    r = subprocess.run(
        [sys.executable, str(root / "tools" / "check_frontmatter.py"), *args],
        capture_output=True, text=True,
    )
    return r.returncode, r.stdout + r.stderr


failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        if detail:
            print(f"        {detail.strip()[:300]}")
        failures.append(name)


print("1. a clean corpus passes")
code, out = run({"a.md": CLEAN, "b.md": CLEAN}, ("--check",))
check("exits zero", code == 0, out)
check("says how many parsed", "2 page(s) parse" in out, out)

print("2. an unquoted colon fails under --check")
code, out = run({"a.md": CLEAN, "bad.md": BROKEN}, ("--check",))
check("exits non-zero", code != 0, f"code={code}")
check("names the file", "bad.md" in out, out)
check("names the line", "line 3" in out, out)
check("counts only the bad one", "1 of 2" in out, out)

print("3. without --check it reports but does not fail")
code, out = run({"bad.md": BROKEN})
check("exits zero", code == 0, out)
check("still reports", "bad.md" in out, out)

print("4. a page with no frontmatter is not this gate's business")
code, out = run({"plain.md": NO_FM}, ("--check",))
check("exits zero", code == 0, out)

print("5. frontmatter that is a list, not a mapping, is caught")
code, out = run({"list.md": LIST_FM}, ("--check",))
check("exits non-zero", code != 0, f"code={code}")
check("says what it found", "not a mapping" in out, out)

print("6. MUTATION: drop the failing exit, case 2 must stop failing")
needle = "    return 1 if check else 0"
src = TOOL.read_text()
if needle not in src:
    check("mutation anchor present", False, "the exit this file claims to test is not there")
else:
    mutant_dir = pathlib.Path(tempfile.mkdtemp())
    mutant = mutant_dir / "check_frontmatter.py"
    mutant.write_text(src.replace(needle, "    return 0"))
    code, out = run({"a.md": CLEAN, "bad.md": BROKEN}, ("--check",), script=mutant)
    check("mutant passes a corpus it should refuse", code == 0, f"code={code} out={out[:200]}")

print()
print(f"FAILED: {', '.join(failures)}" if failures else "all passed")
raise SystemExit(1 if failures else 0)
