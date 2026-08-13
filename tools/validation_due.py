#!/usr/bin/env python3
"""
validation_due.py — decide whether a validation pass is due, without calling a model.

The cadence problem, from the 7 Aug session: a weekly pass is too slow ("a week is too
long — the input data is so large, I just don't remember it"), and a daily pass burns
credits on days when nothing happened. So the trigger is the **quantum of new material**,
not the calendar.

This script is the cheap half of that. It counts words added to `wiki/` since the last
recorded pass and exits:

    0  — due   (enough new material; the caller should run the paid validation step)
    1  — not due
    2  — error

Because deciding costs nothing, the scheduled job can run daily and still only spend
money on days that produced something. That is the whole design: cost tracks use.

State lives in `wiki/.validation-state` (a commit sha + date), so it is versioned,
diffable, and survives a fresh clone — no external store.

Usage:
  python3 tools/validation_due.py                 # decide, print reasoning
  python3 tools/validation_due.py --floor 800     # override the floor
  python3 tools/validation_due.py --record        # mark a pass as done (writes state)
  python3 tools/validation_due.py --quiet         # exit code only
"""

import argparse
import os
import subprocess
import sys

STATE = os.path.join("wiki", ".validation-state")

# Below the floor, asking is noise — nothing meaningful has been written.
DEFAULT_FLOOR = 500
# Above the ceiling, a single prompt would cover so many pages it gets rubber-stamped,
# which is worse than not asking. The caller should split the batch.
DEFAULT_CEILING = 5000


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def read_state():
    if not os.path.exists(STATE):
        return None
    for line in open(STATE, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            return line.split()[0]
    return None


def words_added_since(sha):
    """Words ADDED to wiki/*.md since sha. Additions only: a deletion is not new
    material to validate, and counting both would fire on a pure cleanup."""
    rng = f"{sha}..HEAD" if sha else "HEAD"
    diff = git("diff", "--unified=0", rng, "--", "wiki/") or ""
    n = 0
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            # skip frontmatter churn — the backfill of a field is not new thinking
            body = line[1:].strip()
            if body and not body.split(":")[0].isidentifier() or " " in body:
                n += len(body.split())
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Is a validation pass due?")
    ap.add_argument("--floor", type=int, default=DEFAULT_FLOOR)
    ap.add_argument("--ceiling", type=int, default=DEFAULT_CEILING)
    ap.add_argument("--record", action="store_true", help="mark a pass as completed")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.isdir("wiki"):
        print(f"error: no wiki/ directory (cwd is {os.getcwd()}).\n"
              f"       Run from the repo root.", file=sys.stderr)
        return 2
    if git("rev-parse", "--git-dir") is None:
        print("error: not a git repository — the trigger needs history to measure against.",
              file=sys.stderr)
        return 2

    head = git("rev-parse", "HEAD")
    if args.record:
        date = git("show", "-s", "--format=%cs", "HEAD") or ""
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w", encoding="utf-8") as fh:
            fh.write("# Last completed validation pass. Managed by tools/validation_due.py.\n")
            fh.write(f"{head} {date}\n")
        if not args.quiet:
            print(f"recorded validation pass at {head[:8]} ({date})")
        return 0

    last = read_state()
    added = words_added_since(last)
    due = added >= args.floor

    if not args.quiet:
        where = f"since {last[:8]}" if last else "since the start of history (no state yet)"
        print(f"  new material {where}: ~{added} words")
        print(f"  floor {args.floor} / ceiling {args.ceiling}")
        if not due:
            print("  -> NOT DUE. Nothing meaningful has been written; asking would be noise.")
        elif added > args.ceiling:
            print("  -> DUE, and OVER CEILING. Split the batch: a prompt covering this much "
                  "gets rubber-stamped, which is worse than not asking.")
        else:
            print("  -> DUE.")
    return 0 if due else 1


if __name__ == "__main__":
    raise SystemExit(main())
