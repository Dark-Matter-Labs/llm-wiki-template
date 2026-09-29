#!/usr/bin/env python3
"""
test_check_history.py — pages retire rather than disappear, and past log days only grow.

  python3 tools/test_check_history.py
"""

import datetime
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_history  # noqa: E402

FAILED = []
TODAY = datetime.date(2026, 9, 29)


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def git(d, *a):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=d, check=True,
                   capture_output=True)


def repo():
    d = tempfile.mkdtemp()
    git(d, "init", "-q", "-b", "main")
    os.makedirs(os.path.join(d, "wiki", "log"))
    files = {"wiki/alpha.md": "Alpha.\n", "wiki/beta.md": "Beta.\n",
             "wiki/log/2026-09-20.md": "# Log\n\n## [2026-09-20] ingest | x\n",
             "wiki/log/2026-09-28.md": "# Log\n\n## [2026-09-28] ingest | y\n",
             "wiki/log/2026-09.md": "| day | n |\n"}
    for rel, text in files.items():
        open(os.path.join(d, rel), "w").write(text)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "base")
    git(d, "checkout", "-q", "-b", "work")
    return d


def found(d):
    return check_history.problems("main", TODAY, cwd=d)


def edit(d, rel, text, mode="w"):
    with open(os.path.join(d, rel), mode) as fh:
        fh.write(text)


def commit(d):
    git(d, "add", "-A")
    git(d, "commit", "-qm", "change")


def main():
    print("check_history — no deleted pages, no rewritten past days\n")

    d = repo(); edit(d, "wiki/alpha.md", "Alpha, improved.\n"); edit(d, "wiki/gamma.md", "New.\n"); commit(d)
    check("editing and adding pages passes", found(d) == [], str(found(d)))

    d = repo(); os.remove(os.path.join(d, "wiki/beta.md")); commit(d)
    got = found(d)
    check("deleting a page is refused", len(got) == 1 and "beta.md" in got[0], str(got))

    d = repo(); git(d, "mv", "wiki/beta.md", "wiki/beta-renamed.md"); commit(d)
    check("renaming a page is not a deletion", found(d) == [], str(found(d)))

    d = repo(); edit(d, "wiki/log/2026-09-20.md", "\n## [2026-09-20] repair | late note\n", "a"); commit(d)
    check("adding lines to a past day passes", found(d) == [], str(found(d)))

    d = repo(); edit(d, "wiki/log/2026-09-20.md", "# Log\n\n## [2026-09-20] ingest | x, reworded\n"); commit(d)
    got = found(d)
    check("changing a line of a past day is refused", len(got) == 1 and "2026-09-20" in got[0], str(got))

    d = repo(); os.remove(os.path.join(d, "wiki/log/2026-09-20.md")); commit(d)
    check("deleting a past day is refused", len(found(d)) == 1, str(found(d)))

    d = repo(); edit(d, "wiki/log/2026-09-28.md", "# Log\n\n## [2026-09-28] ingest | y, fixed\n"); commit(d)
    check("yesterday's log may still be corrected", found(d) == [], str(found(d)))

    d = repo(); edit(d, "wiki/log/2026-09.md", "| day | n |\n| 20 | 1 |\n"); commit(d)
    check("the regenerated month index is exempt", found(d) == [], str(found(d)))

    d = repo(); os.remove(os.path.join(d, "wiki/beta.md")); commit(d)
    cwd = os.getcwd()
    try:
        os.chdir(d)
        check("the CLI fails without approval", check_history.main(["--base", "main", "--today", "2026-09-29"]) == 1)
        check("the CLI passes when a person approved",
              check_history.main(["--base", "main", "--today", "2026-09-29", "--approved"]) == 0)
    finally:
        os.chdir(cwd)

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
