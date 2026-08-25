#!/usr/bin/env python3
"""
staleness.py — when did each page last change in a way that meant something?

Why this exists, and why the obvious answer is wrong
-----------------------------------------------------
The obvious staleness signal is git mtime. On 2026-08-23 that signal read the same
for every page in the corpus: **10 days**, in a wiki that started in March 2025. The
cause was a schema backfill on 12 August that added `validation:` to all 766 pages —
a corpus-wide frontmatter rewrite that reset every clock at once.

So git mtime here measures *the last schema migration*, not the last real change. Any
lifecycle rule built on it would flag nothing today and everything uniformly the next
time a field is added. `timestamp:` in frontmatter is no better: for the 257 Substack
summaries it records the essay's publication date, not the page's.

This computes the honest signal instead: **the last commit in which a page's BODY
changed**, ignoring commits that only touched frontmatter. A schema backfill moves
frontmatter; real work moves the body.

Measured on the corpus the day it was written: median 37 days, range 2–50. That
discriminates, which is the whole requirement.

Cost
----
It walks each page's history and hashes the body at each revision, so it is O(commits
touching the page). Results are cached in `.staleness-cache.json` (gitignored), keyed
by the page's current blob hash and the repo HEAD, so repeat runs are near-free and a
changed page recomputes only itself.

Usage:
  python3 tools/staleness.py                 # table, oldest first
  python3 tools/staleness.py --json          # machine-readable
  python3 tools/staleness.py --older-than 28 # only pages untouched that long
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
CACHE = ROOT / ".staleness-cache.json"

# Catalogues and logs are navigation, not content — they have no meaningful body age.
SKIP_DIRS = {"log", "index"}
SKIP_FILES = {"index.md", "log.md"}


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True).stdout


def body_of(text: str) -> str:
    """Everything after the frontmatter block. A frontmatter-only edit leaves this equal."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    return text


def pages() -> "list[str]":
    out = []
    for p in sorted(WIKI.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        if p.name in SKIP_FILES or p.parent.name in SKIP_DIRS:
            continue
        out.append(rel)
    return out


def last_body_change(rel: str) -> "int | None":
    """Unix time of the newest commit whose body differs from the commit after it."""
    log = git("log", "--format=%H %at", "--", rel).strip()
    if not log:
        return None
    revs = [l.split() for l in log.split("\n") if l.strip()]
    prev_digest = None
    newest_ts = int(revs[0][1])
    for h, ts in revs:                       # newest first
        blob = git("show", f"{h}:{rel}")
        digest = hashlib.sha1(body_of(blob).encode("utf-8", "replace")).hexdigest()
        if prev_digest is None:
            prev_digest = digest
            newest_ts = int(ts)
            continue
        if digest != prev_digest:
            return newest_ts                 # body changed on its way to the newer commit
        newest_ts = int(ts)
    return newest_ts                          # unchanged all the way back: its creation


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def compute(force: bool = False) -> "dict[str, int]":
    cache = {} if force else load_cache()
    result, dirty = {}, False
    for rel in pages():
        blob = git("hash-object", rel).strip()
        hit = cache.get(rel)
        if hit and hit.get("blob") == blob:
            result[rel] = hit["ts"]
            continue
        ts = last_body_change(rel)
        if ts is None:
            continue
        result[rel] = ts
        cache[rel] = {"blob": blob, "ts": ts}
        dirty = True
    if dirty:
        CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Days since each page's body last changed.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--older-than", type=int, default=0, metavar="DAYS")
    ap.add_argument("--force", action="store_true", help="ignore the cache")
    args = ap.parse_args(argv)

    now = time.time()
    ages = {rel: int((now - ts) / 86400) for rel, ts in compute(args.force).items()}
    keep = {k: v for k, v in ages.items() if v >= args.older_than}

    if args.json:
        print(json.dumps(keep, indent=2, sort_keys=True))
        return 0

    ordered = sorted(keep.items(), key=lambda kv: -kv[1])
    print(f"body staleness — {len(keep)} page(s)"
          + (f" untouched for {args.older_than}+ days" if args.older_than else "") + "\n")
    for rel, days in ordered[:40]:
        print(f"  {days:>5}d  {rel}")
    if len(ordered) > 40:
        print(f"  … and {len(ordered) - 40} more")
    if ordered:
        vals = sorted(keep.values())
        print(f"\n  median {vals[len(vals) // 2]}d · oldest {vals[-1]}d · newest {vals[0]}d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
