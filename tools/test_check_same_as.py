#!/usr/bin/env python3
"""Does check_same_as refuse what it claims to refuse?

The whole value of this gate is the five edges it turns down, so a version that accepted
everything would look identical in this wiki — which today declares three, all legal. Case 7
mutates the openness comparison away and asserts the refusal cases stop refusing.

    python3 tools/test_check_same_as.py
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent / "check_same_as.py"

PAGE = ("---\ntype: entity\ntitle: {title}\ndescription: d\ntags: [t]\nstatus: draft\n"
        "visibility: {vis}\nconfidence: low\nvalidation: machine\ntimestamp: 2026-09-18\n"
        "sources: []\n{extra}---\n\nBody.\n")


def world(pages, cuts=None, name="indy-llm-wiki"):
    """A throwaway wiki, optionally with commons cuts cached under .commons/."""
    root = pathlib.Path(tempfile.mkdtemp()) / name
    (root / "tools").mkdir(parents=True)
    (root / "wiki").mkdir()
    shutil.copy(TOOL, root / "tools" / "check_same_as.py")
    for slug, (title, vis, extra) in pages.items():
        (root / "wiki" / f"{slug}.md").write_text(
            PAGE.format(title=title, vis=vis, extra=extra), encoding="utf-8")
    for wiki, nodes in (cuts or {}).items():
        d = root / ".commons" / wiki / "export"
        d.mkdir(parents=True)
        (d / "wiki.shared.json").write_text(json.dumps({"nodes": nodes}), encoding="utf-8")
    return root


def run(root, args=("--check",)):
    r = subprocess.run([sys.executable, str(root / "tools" / "check_same_as.py"), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        if detail:
            print(f"        {detail.strip()[:280]}")
        failures.append(name)


cut_internal = {"xco-team-wiki": [{"slug": "a-shared-thing", "visibility": "internal"}]}
cut_private = {"xco-team-wiki": [{"slug": "a-quiet-thing", "visibility": "private"}]}

print("1. no same_as anywhere is the normal case")
code, out = run(world({"plain": ("Plain", "internal", "")}))
check("exits zero", code == 0, out)
check("says none declared", "0 edge(s)" in out, out)

print("2. a private page may name anything — it never exports")
code, out = run(world({"p": ("P", "private", "same_as: [michelle-llm-wiki/whatever]\n")}))
check("exits zero", code == 0, out)
check("counts the edge", "1 edge(s)" in out, out)

print("3. internal -> internal, visible in a cut, is allowed")
code, out = run(world({"p": ("P", "internal", "same_as: [xco-team-wiki/a-shared-thing]\n")},
                      cuts=cut_internal))
check("exits zero", code == 0, out)

print("4. internal -> private is refused")
code, out = run(world({"p": ("P", "internal", "same_as: [xco-team-wiki/a-quiet-thing]\n")},
                      cuts=cut_private))
check("exits non-zero", code != 0, f"code={code}")
check("says why", "may not name a private" in out, out)

print("5. unlisted -> private is refused too")
code, out = run(world({"p": ("P", "unlisted", "same_as: [xco-team-wiki/a-quiet-thing]\n")},
                      cuts=cut_private))
check("exits non-zero", code != 0, f"code={code}")

print("6. a non-private page pointing somewhere unreadable is refused")
code, out = run(world({"p": ("P", "internal", "same_as: [some-other-wiki/a-thing]\n")},
                      cuts=cut_internal))
check("exits non-zero", code != 0, f"code={code}")
check("says it cannot check", "reads no cut" in out, out)

print("   …and the malformed and self-pointing cases")
code, out = run(world({"p": ("P", "internal", "same_as: [not-a-reference]\n")}))
check("a bare word is refused", code != 0 and "wiki-name/slug" in out, out)
code, out = run(world({"p": ("P", "internal", "same_as: [indy-llm-wiki/itself]\n")}))
check("pointing at this wiki is refused", code != 0 and "points at this wiki" in out, out)

print("7. MUTATION: drop the openness comparison, case 4 must stop refusing")
needle = "            if OPENNESS.get(there, 0) < OPENNESS.get(here, 0):"
src = TOOL.read_text()
if needle not in src:
    check("mutation anchor present", False, "the comparison this file tests is not there")
else:
    root = world({"p": ("P", "internal", "same_as: [xco-team-wiki/a-quiet-thing]\n")},
                 cuts=cut_private)
    (root / "tools" / "check_same_as.py").write_text(src.replace(needle, "            if False:"))
    code, out = run(root)
    check("mutant allows an internal page to name a private one", code == 0,
          f"code={code} {out[:200]}")

print()
print(f"FAILED: {', '.join(failures)}" if failures else "all passed")
raise SystemExit(1 if failures else 0)
