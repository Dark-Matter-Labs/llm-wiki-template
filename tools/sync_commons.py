#!/usr/bin/env python3
"""
sync_commons.py — fetch the commons this wiki reads, to where the tools actually run.

## Why this exists

`.github/workflows/sync-commons.yml` has been running daily, green, in every wiki since August.
It clones each declared commons' `export` branch into `.commons/<name>/export`, prints a report,
and ends — **inside an ephemeral runner**. Nothing is committed, uploaded or cached, so the
directory it creates ceases to exist the moment the job finishes.

Five tools read that path. On any machine, all of them see nothing:

    commons_report.py       "No commons cache for xco-team-wiki, power-project-wiki"
    contribution_prompt.py  "overlap UNKNOWN — no cached export, so the check could not run"
    contribute.py           "no cached graph … a page that already exists there cannot be detected"

The last one is the expensive failure. `contribute.py`'s collision check is what stops the same
page being contributed to a commons twice, and it has been switched off in practice for the whole
life of the federation. **13 of 602 pages in `xco-team-wiki` arrived through the up-flow**; 576 were
bulk-seeded in one go on 2026-08-05. A mechanism whose safety check cannot run does not get used.

So the down-flow was not broken. It was **running perfectly somewhere nobody could read.** This is
the same class as the six weeks of green ticks on a disabled workflow, and the `grep` that printed
nothing when a check failed: an operation that reports success while delivering nothing.

## What this does differently

Exactly what the workflow does, on the machine where the instruments run. It reads the same
declaration (`design/federation.json` → `contributes_to`), clones the same boundary-filtered
`export` branch — never the working tree, so a `private` page in a commons cannot reach a spoke
even by accident — and writes to the same path the tools already expect.

Auth is `gh`, not a token, because this is a local command run by a person who is already signed in.

Usage:
  python3 tools/sync_commons.py            # fetch every declared commons
  python3 tools/sync_commons.py --check    # report what is cached, fetch nothing
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEDERATION = ROOT / "design" / "federation.json"
CACHE = ROOT / ".commons"


def _run(*args) -> "tuple[int, str]":
    p = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    return p.returncode, (p.stdout + p.stderr).strip()


def owner() -> "str | None":
    rc, url = _run("git", "remote", "get-url", "origin")
    if rc != 0:
        return None
    for sep in ("github.com:", "github.com/"):
        if sep in url:
            return url.split(sep, 1)[1].split("/", 1)[0]
    return None


def declared() -> "list[str]":
    """The commons this wiki reads. Same declaration contribute.py writes UP to."""
    if not FEDERATION.exists():
        return []
    try:
        return list(json.loads(FEDERATION.read_text(encoding="utf-8")).get("contributes_to", []))
    except ValueError:
        return []


def cached(name: str) -> "int | None":
    """How many export files are cached for this commons, or None if absent."""
    d = CACHE / name / "export"
    if not d.is_dir():
        return None
    return len(list(d.glob("*.json")))


def fetch(name: str, org: str) -> "tuple[bool, str]":
    dest = CACHE / name / "export"
    if dest.exists():
        shutil.rmtree(dest)          # a stale cut is worse than none: it reads as current
    dest.parent.mkdir(parents=True, exist_ok=True)
    rc, out = _run("gh", "repo", "clone", f"{org}/{name}", str(dest),
                   "--", "--depth", "1", "--branch", "export", "-q")
    if rc != 0:
        if dest.exists():
            shutil.rmtree(dest)
        first = out.splitlines()[0] if out else "clone failed"
        return False, first
    shutil.rmtree(dest / ".git", ignore_errors=True)   # a cache, not a checkout
    n = len(list(dest.glob("*.json")))
    return True, f"{n} cut(s)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fetch the commons this wiki reads, locally.")
    ap.add_argument("--check", action="store_true", help="report what is cached; fetch nothing")
    args = ap.parse_args(argv)

    names = declared()
    if not names:
        print("commons — this wiki declares none in design/federation.json.\n"
              "  Nothing to fetch. A commons at the top of the graph has nothing above it, and "
              "that is a correct state, not a missing cache.")
        return 0

    if args.check:
        print(f"commons cache — {len(names)} declared")
        for n in names:
            c = cached(n)
            print(f"  {n:24} {'absent' if c is None else f'{c} cut(s) cached'}")
        missing = [n for n in names if cached(n) is None]
        if missing:
            print(f"\n  {len(missing)} not cached. The instruments that read them — contribute.py's\n"
                  "  collision check, contribution_prompt.py, commons_report.py — cannot run until\n"
                  "  they are. Run this command with no arguments.")
        return 0

    org = owner()
    if not org:
        print("could not read the GitHub owner from `git remote get-url origin`.")
        return 1

    print(f"fetching {len(names)} commons as {org}\n")
    failed = 0
    for n in names:
        ok, detail = fetch(n, org)
        print(f"  {'OK  ' if ok else 'FAIL'} {n:24} {detail}")
        failed += 0 if ok else 1

    print(f"\n  cached into {CACHE.relative_to(ROOT)}/ — the path contribute.py, "
          f"contribution_prompt.py and commons_report.py already read.")
    if failed:
        print(f"  {failed} failed. `gh auth status` is the first thing to check.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
