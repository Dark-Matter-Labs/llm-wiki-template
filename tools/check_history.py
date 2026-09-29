#!/usr/bin/env python3
"""
check_history.py — a pull request may not delete a wiki page or rewrite a past day's log,
unless a person has said so.

Two rules this wiki states and nothing enforced: "never delete wiki pages unilaterally" and
"never rewrite past days — corrections are appended as new entries". Adopted 29 September 2026
from the awesome-llm-wiki review (the append-only guard in Verified Memory Vault). A model
tidying up is exactly how either would be broken, and a rule that is only written down is a
preference.

What it refuses, comparing the branch with its base:
  * a deleted page under wiki/ (a rename is not a deletion and passes);
  * a past day's log file (wiki/log/YYYY-MM-DD.md, older than yesterday) that loses or changes
    any line, or is deleted. Adding lines passes. Month index files are regenerated and exempt.

A person approves a real removal, such as a private title that leaked into an old log entry, by
adding the label `approved-removal` to the pull request; the workflow then passes --approved.
A model never adds that label itself.

  python3 tools/check_history.py --base origin/main
  python3 tools/check_history.py --base origin/main --approved
"""

import argparse
import datetime
import re
import subprocess
import sys

DAY_LOG = re.compile(r"^wiki/log/(\d{4}-\d{2}-\d{2})\.md$")


def _git(*args, cwd=None):
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout


def problems(base, today, cwd=None):
    """Plain-language reasons the branch breaks one of the two rules, empty when it does not."""
    out = []
    status = _git("diff", "--name-status", "-M", f"{base}...HEAD", "--", "wiki", cwd=cwd)
    cutoff = today - datetime.timedelta(days=1)
    for line in status.splitlines():
        parts = line.split("\t")
        code, path = parts[0], parts[-1]
        day = DAY_LOG.match(parts[1] if code.startswith("R") else path)
        if day:
            try:
                past = datetime.date.fromisoformat(day.group(1)) < cutoff
            except ValueError:
                past = False
            if not past:
                continue
            if code == "D" or code.startswith("R"):
                out.append(f"{parts[1]}: a past day's log was deleted or moved")
                continue
            num = _git("diff", "--numstat", f"{base}...HEAD", "--", path, cwd=cwd).split()
            if num and num[1] not in ("0", "-"):
                out.append(f"{path}: {num[1]} line(s) of a past day's log changed or removed; "
                           "append a correction to today's log instead")
        elif code == "D" and path.endswith(".md"):
            out.append(f"{path}: a wiki page was deleted; pages retire (status: dormant), they are not removed")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Refuse deleted pages and rewritten past log days.")
    ap.add_argument("--base", required=True, help="the commit or branch the change is compared with")
    ap.add_argument("--approved", action="store_true", help="a person approved the removal (PR label)")
    ap.add_argument("--today", help="YYYY-MM-DD; default today in UTC")
    args = ap.parse_args(argv)
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.datetime.now(datetime.timezone.utc).date()
    try:
        found = problems(args.base, today)
    except RuntimeError as e:
        print(f"history guard could not compare with {args.base}: {e}")
        return 2
    if not found:
        print("history guard: no page deleted, no past log day rewritten.")
        return 0
    print("history guard:")
    for f in found:
        print(f"  {f}")
    if args.approved:
        print("\nApproved by a person (label approved-removal), so this passes.")
        return 0
    print("\nIf a person has decided this removal, they add the label `approved-removal` to the pull request.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
