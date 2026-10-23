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
  python3 tools/staleness.py --freshness     # pages whose freshness has fallen below 50

Freshness (23 October 2026, adapted from nvk/llm-wiki): a fixed age means different things for different
pages. A commitment untouched for a month may be stale; a source summary untouched for a year is fine.
A page may say how fast it goes stale with `volatility: hot | warm | cold`, whose half-lives are 30, 90 and
365 days. Without the field, its type decides (HOT_TYPES, COLD_TYPES, otherwise warm). Freshness is
100 at a body change and halves every half-life. It is a reading list, never a gate and never a fix.
"""

from __future__ import annotations

import argparse
import re
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


HALF_LIFE = {"hot": 30, "warm": 90, "cold": 365}
HOT_TYPES = ("commitment", "question")
COLD_TYPES = ("summary",)


def volatility(text: str) -> str:
    """The page's own `volatility:` if it states one, else a default from its type."""
    head = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
    m = re.search(r"^volatility:\s*(hot|warm|cold)\b", head, re.M)
    if m:
        return m.group(1)
    t = re.search(r"^type:\s*([\w-]+)", head, re.M)
    t = t.group(1) if t else ""
    return "hot" if t in HOT_TYPES else "cold" if t in COLD_TYPES else "warm"


def freshness(days: int, vol: str) -> int:
    """100 at a body change, halving every half-life of the page's volatility."""
    return round(100 * 0.5 ** (max(days, 0) / HALF_LIFE[vol]))


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
    ap.add_argument("--freshness", nargs="?", const=50, type=int, metavar="BELOW",
                    help="list pages whose freshness is below this (default 50), by volatility")
    args = ap.parse_args(argv)

    now = time.time()
    ages = {rel: int((now - ts) / 86400) for rel, ts in compute(args.force).items()}
    keep = {k: v for k, v in ages.items() if v >= args.older_than}

    if args.freshness is not None:
        rows = []
        for rel, days in keep.items():
            vol = volatility((ROOT / rel).read_text(encoding="utf-8", errors="replace"))
            score = freshness(days, vol)
            if score < args.freshness:
                rows.append((score, rel, vol, days))
        rows.sort()
        if args.json:
            print(json.dumps([{"page": r, "freshness": f, "volatility": v, "days": d} for f, r, v, d in rows], indent=2))
            return 0
        print(f"freshness below {args.freshness} — {len(rows)} page(s), least fresh first\n")
        for f, r, v, d in rows[:40]:
            print(f"  {f:>3}  {v:<4} {d:>4}d  {r}")
        if len(rows) > 40:
            print(f"  … and {len(rows) - 40} more")
        print("\n  A reading list, not a fault list. A person decides whether a page needs work.")
        return 0

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
