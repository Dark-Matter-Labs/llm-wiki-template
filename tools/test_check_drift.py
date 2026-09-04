#!/usr/bin/env python3
"""
test_check_drift.py — the properties that make a drift gate worth having.

The gate exists because three defects in three days turned out to be three samples from a
population of thirty-eight: files living in more than one wiki, outside the synced layer, quietly
disagreeing.

As with the link checker, what must NOT be reported matters as much as what must. A drift
detector that cries wolf on files that are supposed to differ gets ignored, and the corpus has
plenty of those -- design/federation.json is per-repo by design.

The last test is the one this repo learned the hard way, twice in a week: a check that cannot run
must SAY it cannot run. A workflow died for six weeks behind a truncated `ls`, and a red PR merged
because a loop waited for CI to finish rather than to pass. Silence is the failure mode to test for.

  python3 tools/test_check_drift.py
"""

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_drift as cd            # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def build(tmp, files_by_repo, shared=(), siblings=("sib-a", "sib-b")):
    """files_by_repo: {repo_name: {relpath: content}}. First repo is 'self'.

    Writes a real manifest, because that is how the tool reads the layer in every repo but
    the source one. Faking it another way would test a path nine wikis never take.
    """
    root = pathlib.Path(tmp)
    for repo, files in files_by_repo.items():
        for rel, content in files.items():
            p = root / repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    cd.ROOT = root / "self"
    cd.BASELINE = root / "self" / "tools" / "drift-baseline.json"
    cd.MANIFEST = root / "self" / "design" / "shared-layer.json"
    cd.MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    cd.MANIFEST.write_text(json.dumps({
        "siblings": list(siblings), "shared": list(shared),
        "generated": "docs/assets/xco-tokens.css"}), encoding="utf-8")
    return root


def paths(drift):
    return sorted(d["path"] for d in drift)


def main():
    print("check_drift — report real divergence, and nothing else\n")
    saved = (cd.ROOT, cd.BASELINE, cd.MANIFEST)
    try:
        with tempfile.TemporaryDirectory() as t:
            build(t, {"self": {"tools/a.py": "x"}, "sib-a": {"tools/a.py": "x"}})
            drift, n, _ = cd.audit()
            check("identical copies are not reported", paths(drift) == [], f"{paths(drift)}")
            check("both repos were actually seen", n == 2, f"{n}")

        with tempfile.TemporaryDirectory() as t:
            build(t, {"self": {"tools/a.py": "x"}, "sib-a": {"tools/a.py": "DIFFERENT"}})
            drift, _, _ = cd.audit()
            check("a file that disagrees with itself is reported", paths(drift) == ["tools/a.py"])

        with tempfile.TemporaryDirectory() as t:
            build(t, {"self": {"tools/only-here.py": "x"}, "sib-a": {"tools/b.py": "y"}})
            drift, _, _ = cd.audit()
            check("a file in only one repo is not reported",
                  paths(drift) == [], "nothing to disagree with")

        with tempfile.TemporaryDirectory() as t:
            build(t, {"self": {"tools/a.py": "x"}, "sib-a": {"tools/a.py": "DIFFERENT"}},
                  shared=["tools/a.py"])
            drift, _, _ = cd.audit()
            check("a file already in SHARED is not reported",
                  paths(drift) == [], "sync_design_system.py owns that one")

        with tempfile.TemporaryDirectory() as t:
            build(t, {"self": {"tools/links-baseline.json": "1"},
                      "sib-a": {"tools/links-baseline.json": "2"}})
            drift, _, _ = cd.audit()
            check("a per-repo generated register is not reported",
                  paths(drift) == [], "differing is its correct state")

        with tempfile.TemporaryDirectory() as t:
            build(t, {"self": {"wiki/page.md": "x"}, "sib-a": {"wiki/page.md": "DIFFERENT"}})
            drift, _, _ = cd.audit()
            check("wiki content is not scanned",
                  paths(drift) == [], "corpora are supposed to differ")

        with tempfile.TemporaryDirectory() as t:
            build(t, {"self": {"tools/a.py": "x", "tools/b.py": "x"},
                      "sib-a": {"tools/a.py": "P", "tools/b.py": "Q"}})
            cd.BASELINE.parent.mkdir(parents=True, exist_ok=True)
            cd.BASELINE.write_text(json.dumps({"drifted": [{"path": "tools/a.py"}]}), encoding="utf-8")
            drift, _, _ = cd.audit()
            base = cd.load_baseline()
            new = [d for d in drift if d["path"] not in base]
            check("the baseline suppresses known drift", "tools/a.py" not in paths(new))
            check("the baseline does not suppress a new one",
                  paths(new) == ["tools/b.py"], f"{paths(new)}")

        with tempfile.TemporaryDirectory() as t:
            # No siblings on disk at all — the CI case.
            build(t, {"self": {"tools/a.py": "x"}}, siblings=("absent-1", "absent-2"))
            _, n, _ = cd.audit()
            check("with no siblings, it reports one repo rather than pretending to compare",
                  n == 1, f"{n}")
            rc = cd.main(["--check"])
            check("and --check exits 0 while SAYING it could not compare",
                  rc == 0, "a gate that cannot run must say so, not pass quietly")
    finally:
        cd.ROOT, cd.BASELINE, cd.MANIFEST = saved

        with tempfile.TemporaryDirectory() as t:
            # The nine-wiki case: manifest present, sync_design_system.py absent entirely.
            build(t, {"self": {"tools/a.py": "x"}, "sib-a": {"tools/a.py": "DIFFERENT"}})
            check("works with no sync_design_system.py present at all",
                  paths(cd.audit()[0]) == ["tools/a.py"],
                  "this is the state of nine of the ten wikis")

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
