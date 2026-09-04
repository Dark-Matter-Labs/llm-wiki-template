#!/usr/bin/env python3
"""
test_sync_commons.py — the local commons fetch, and the states it must not misreport.

The bug this tool fixes was not a crash. `sync-commons.yml` ran green daily for a month while
delivering nothing, because it wrote into an ephemeral runner. So the properties worth testing here
are mostly about **reporting the truth about emptiness** — an absent cache must read as absent, and
a wiki that declares no commons must not read as a failure.

  python3 tools/test_sync_commons.py
"""

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_commons as sc  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def build(tmp, contributes_to=None, cached_cuts=None):
    root = pathlib.Path(tmp)
    (root / "design").mkdir(parents=True, exist_ok=True)
    if contributes_to is not None:
        (root / "design" / "federation.json").write_text(
            json.dumps({"name": "a-wiki", "role": "spoke", "contributes_to": contributes_to}),
            encoding="utf-8")
    for name, n in (cached_cuts or {}).items():
        d = root / ".commons" / name / "export"
        d.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            (d / f"wiki.cut{i}.json").write_text("{}", encoding="utf-8")
    sc.ROOT = root
    sc.FEDERATION = root / "design" / "federation.json"
    sc.CACHE = root / ".commons"
    return root


def main():
    print("sync_commons — tell the truth about an empty cache\n")
    saved = (sc.ROOT, sc.FEDERATION, sc.CACHE)
    try:
        with tempfile.TemporaryDirectory() as t:
            build(t, contributes_to=["xco-team-wiki", "power-project-wiki"])
            check("declared commons are read from federation.json",
                  sc.declared() == ["xco-team-wiki", "power-project-wiki"], f"{sc.declared()}")
            check("an absent cache reads as absent, not as zero",
                  sc.cached("xco-team-wiki") is None,
                  "None and 0 mean different things: never fetched vs fetched and empty")

        with tempfile.TemporaryDirectory() as t:
            build(t, contributes_to=["xco-team-wiki"], cached_cuts={"xco-team-wiki": 2})
            check("a populated cache reports its cut count", sc.cached("xco-team-wiki") == 2)

        with tempfile.TemporaryDirectory() as t:
            build(t, contributes_to=["xco-team-wiki"], cached_cuts={"xco-team-wiki": 0})
            check("a fetched-but-empty cache reads as 0, not absent",
                  sc.cached("xco-team-wiki") == 0)

        with tempfile.TemporaryDirectory() as t:
            # A top commons contributes nowhere. That is correct, not a missing cache.
            build(t, contributes_to=[])
            check("a wiki that declares no commons is not an error", sc.declared() == [])
            check("and it exits 0 rather than reporting a failure", sc.main([]) == 0)

        with tempfile.TemporaryDirectory() as t:
            build(t, contributes_to=None)     # no federation.json at all
            check("a missing federation.json yields no commons rather than a crash",
                  sc.declared() == [])

        for url, want in [
            ("https://github.com/Dark-Matter-Labs/indy-llm-wiki.git", "Dark-Matter-Labs"),
            ("git@github.com:Dark-Matter-Labs/indy-llm-wiki.git", "Dark-Matter-Labs"),
        ]:
            got = url.split("github.com:", 1)[1].split("/", 1)[0] if "github.com:" in url \
                else url.split("github.com/", 1)[1].split("/", 1)[0]
            check(f"owner parses from {'ssh' if ':' in url.split('github.com')[1][:1] else 'https'} remote",
                  got == want, f"{got}")
    finally:
        sc.ROOT, sc.FEDERATION, sc.CACHE = saved

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
