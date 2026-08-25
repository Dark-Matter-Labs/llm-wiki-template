#!/usr/bin/env python3
"""
test_staleness.py — the one property the staleness signal exists for.

`staleness.py` was written because git mtime lied: a schema backfill on 2026-08-12
rewrote the frontmatter of all 766 pages, so every page reported the same 10 days of
age in a wiki that started in March 2025. A signal a migration can reset measures
migrations.

So the property under test is exactly that: **a frontmatter-only commit must not count
as a change, and a body commit must.** Everything else in the tool is plumbing.

  python3 tools/test_staleness.py
"""

import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import staleness  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True).stdout


def commit(repo, path, text, message, when):
    path.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    env = {**os.environ,
           "GIT_AUTHOR_DATE": str(when), "GIT_COMMITTER_DATE": str(when),
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message],
                   env=env, capture_output=True)


def page(fm_extra, body):
    return f"---\ntype: concept\ntitle: T\n{fm_extra}---\n\n{body}\n"


def main():
    print("staleness — frontmatter changes must not count as changes\n")
    now = int(time.time())
    DAY = 86400

    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp)
        subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], capture_output=True)
        wiki = repo / "wiki"
        wiki.mkdir()
        p = wiki / "thing.md"

        # 40 days ago: the real content lands.
        commit(repo, p, page("", "The actual argument."), "write it", now - 40 * DAY)
        # 2 days ago: a schema backfill touches frontmatter across the corpus.
        commit(repo, p, page("validation: machine\n", "The actual argument."),
               "backfill: add validation", now - 2 * DAY)

        old_root, old_wiki, old_cache = staleness.ROOT, staleness.WIKI, staleness.CACHE
        staleness.ROOT, staleness.WIKI = repo, wiki
        staleness.CACHE = repo / ".cache.json"
        try:
            ages = {k: int((time.time() - v) / 86400) for k, v in staleness.compute(force=True).items()}
            got = ages.get("wiki/thing.md")
            check("a frontmatter-only commit does not reset the clock",
                  got is not None and got >= 39, f"reported {got}d, expected ~40d")

            # Now a real edit to the body, yesterday.
            commit(repo, p, page("validation: machine\n", "The argument, revised."),
                   "revise", now - 1 * DAY)
            ages = {k: int((time.time() - v) / 86400) for k, v in staleness.compute(force=True).items()}
            got = ages.get("wiki/thing.md")
            check("a body commit does reset it", got is not None and got <= 2,
                  f"reported {got}d, expected ~1d")

            # Catalogues have no meaningful body age and must be skipped.
            (wiki / "index").mkdir()
            (wiki / "index" / "concepts.md").write_text("# shelf\n", encoding="utf-8")
            (wiki / "index.md").write_text("# router\n", encoding="utf-8")
            commit(repo, wiki / "log.md", "# log\n", "catalogues", now)
            rels = set(staleness.pages())
            check("catalogues and logs are skipped",
                  not any(r.endswith(("index.md", "log.md")) or "/index/" in r for r in rels),
                  f"{sorted(rels)}")
        finally:
            staleness.ROOT, staleness.WIKI, staleness.CACHE = old_root, old_wiki, old_cache

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
