#!/usr/bin/env python3
"""
test_commons_report.py — the report names the commons this wiki READS.

Found on 2026-09-24 in bioregional-finance-wiki, the first commons that reads another without
contributing to it. The weekly sync fetched rz-commons successfully, then its report step said
"This wiki contributes to no commons" and showed nothing, because the report asked which commons
the wiki contributes to rather than which it reads. The fetch and the report disagreed about
the same wiki. The rule for "which commons does this wiki read" lives in
`sync_commons.declared()`; these tests hold the report to it.

  python3 tools/test_commons_report.py
"""

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commons_report as cr  # noqa: E402
import sync_commons as sc  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def build(tmp, fed, cached=None):
    """A throwaway wiki: its federation.json, and optionally a cached shared cut per commons."""
    root = pathlib.Path(tmp)
    (root / "design").mkdir(parents=True, exist_ok=True)
    (root / "design" / "federation.json").write_text(json.dumps(fed), encoding="utf-8")
    for name, types in (cached or {}).items():
        d = root / ".commons" / name / "export"
        d.mkdir(parents=True, exist_ok=True)
        nodes = [{"title": f"{name} page {i}", "type": t} for i, t in enumerate(types)]
        (d / "wiki.shared.json").write_text(json.dumps({"nodes": nodes}), encoding="utf-8")
    sc.ROOT = root
    sc.FEDERATION = root / "design" / "federation.json"
    sc.CACHE = root / ".commons"
    return root


def run_report(root):
    out = io.StringIO()
    cwd = os.getcwd()
    try:
        os.chdir(root)
        with contextlib.redirect_stdout(out):
            code = cr.main([])
    finally:
        os.chdir(cwd)
    return code, out.getvalue()


def main():
    print("commons_report — report what this wiki reads\n")
    saved = (sc.ROOT, sc.FEDERATION, sc.CACHE)
    try:
        with tempfile.TemporaryDirectory() as t:
            build(t, {"name": "reader", "role": "commons", "contributes_to": [], "reads_from": ["rz-commons"]},
                  cached={"rz-commons": ["concept", "concept", "entity"]})
            check("a read-only wiki's commons come from reads_from",
                  cr.declared_commons() == ["rz-commons"], f"{cr.declared_commons()}")
            code, text = run_report(t)
            check("the report shows what it read", "3 pages readable" in text, text.strip()[:120])
            check("the report does not claim there is nothing to read",
                  "no commons" not in text, text.strip()[:120])
            check("it exits cleanly", code == 0)

        with tempfile.TemporaryDirectory() as t:
            build(t, {"name": "spoke", "role": "spoke", "contributes_to": ["xco-team-wiki"]},
                  cached={"xco-team-wiki": ["summary"]})
            check("a wiki with only contributes_to still reads those commons",
                  cr.declared_commons() == ["xco-team-wiki"], f"{cr.declared_commons()}")

        with tempfile.TemporaryDirectory() as t:
            build(t, {"name": "top", "role": "commons", "contributes_to": []})
            code, text = run_report(t)
            check("a wiki that reads nothing says so in terms of reading",
                  "reads no commons" in text, text.strip()[:120])
            check("and exits cleanly", code == 0)

        with tempfile.TemporaryDirectory() as t:
            build(t, {"name": "reader", "role": "commons", "contributes_to": ["xco-team-wiki"],
                      "reads_from": ["rz-commons"]}, cached={"rz-commons": ["concept"]})
            check("reads_from wins over contributes_to when both are set",
                  cr.declared_commons() == ["rz-commons"], f"{cr.declared_commons()}")
    finally:
        sc.ROOT, sc.FEDERATION, sc.CACHE = saved

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
