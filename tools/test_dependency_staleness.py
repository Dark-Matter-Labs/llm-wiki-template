#!/usr/bin/env python3
"""
Properties of dependency_staleness.py.

The case this exists for is `a synthesis written against an older register`: the Axioms Register
moved by half while thirty-six pages that argue against it did not, and nothing in the wiki could
say so.

These build real git repositories with controlled commit dates, because the whole substance of
the tool is derived from git history. A test that stubbed the history would test the arithmetic
and not the thing.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dependency_staleness as ds  # noqa: E402
import export  # noqa: E402
import staleness  # noqa: E402

FAILED = []
DAY = 86400
T0 = 1780000000  # a fixed instant well inside git's comfortable range


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(title, *, type="synthesis", body="body\n", visibility="internal", **extra):
    fm = [f"type: {type}", f"title: {title}", "description: d", "tags: [t]",
          "status: draft", f"visibility: {visibility}", "confidence: medium",
          "timestamp: 2026-08-01", "sources: []"]
    fm += [f"{k}: {v}" for k, v in extra.items()]
    return "---\n" + "\n".join(fm) + "\n---\n\n" + body


class Repo:
    """A throwaway git wiki whose commits land at chosen instants."""

    def __init__(self, root: pathlib.Path):
        self.root = root
        (root / "wiki").mkdir(parents=True)
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "T")
        self._git("config", "commit.gpgsign", "false")   # a signing host must not fail the suite

    def _git(self, *a):
        subprocess.run(["git", "-C", str(self.root), *a], check=True,
                       capture_output=True, text=True)

    def write(self, slug: str, text: str):
        f = self.root / "wiki" / f"{slug}.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def commit(self, at: int, msg="c"):
        stamp = f"{int(at)} +0000"
        env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-q", "-m", msg],
                       check=True, capture_output=True, env=env)

    def activate(self):
        """Point every module's globals at this repository and drop cached history."""
        ds.ROOT, ds.WIKI = self.root, self.root / "wiki"
        staleness.ROOT, staleness.WIKI = self.root, self.root / "wiki"
        staleness.CACHE = self.root / ".staleness-cache.json"
        ds.reset_caches()


def link(title):
    return f"It rests on [[{title}]].\n"


def run(**kw):
    return ds.audit(**kw)


def main():
    print("dependency_staleness — has the ground moved under a derivative page?\n")

    # THE CASE THIS EXISTS FOR.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.write("challenge", page("Challenge", body=link("Register")))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, stats = run()
        check("a synthesis whose dependency was rewritten after it is reported", len(rows) == 1,
              f"got {len(rows)}")
        if rows:
            # 0.75, not 1.0: the body is the six rewritten lines plus the two blank lines
            # that follow the frontmatter, and those are unchanged. Blank lines sit in the
            # denominator, which dilutes churn slightly and uniformly. Asserted exactly so a
            # change to how the body is sliced shows up here rather than drifting quietly.
            check("...naming the page, the dependency, the churn and the gap",
                  rows[0]["page"] == "challenge" and rows[0]["dependency"] == "register"
                  and rows[0]["churn"] == 0.75 and rows[0]["gap_days"] == 40,
                  str({k: rows[0][k] for k in ("page", "dependency", "churn", "gap_days")}))

    # Direction matters: a dependency that settled BEFORE the page was written is ground the
    # page has already seen. Reporting it would flag every page in the corpus.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 10 * DAY)
        r.write("challenge", page("Challenge", body=link("Register")))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, _ = run()
        check("a dependency that moved BEFORE the page was written is not reported", not rows,
              f"got {rows}")

    # The threshold is the whole reason this is readable. A dependency gaining one line in
    # twelve is not drift.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        base = "".join(f"line {i}\n" for i in range(12))
        r.write("register", page("Register", type="concept", body=base))
        r.write("challenge", page("Challenge", body=link("Register")))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body=base + "one more\n"))
        r.commit(T0 + 30 * DAY)
        r.activate()
        rows, stats = run()
        check("a small change is set aside by the churn threshold", not rows, f"got {rows}")
        check("...but it is still counted as moved, so the report can say so",
              stats["moved"] == 1, str(stats))
        loose, _ = run(min_churn=0.0)
        check("...and --churn 0 surfaces it", len(loose) == 1, f"got {len(loose)}")

    # Inherited from staleness.py, and the reason that tool exists: a schema backfill rewrites
    # frontmatter across the corpus. If that counted, every page would be stale on every migration.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.write("challenge", page("Challenge", body=link("Register")))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n",
                                 validation="machine", derivation="source"))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, stats = run()
        check("a frontmatter-only change to the dependency is not drift",
              not rows and stats["moved"] == 0, f"rows={rows} stats={stats}")

    # The pool restriction. A `summary` rests on a source in raw/, not on its neighbours.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.write("digest", page("Digest", type="summary", body=link("Register")))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, _ = run()
        check("a summary page is outside the derivative pool", not rows, f"got {rows}")
        wide, _ = run(pool_all=True)
        check("...and --all reaches it", len(wide) == 1, f"got {len(wide)}")

    # Same-session edits are one person updating a page and its neighbour together.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.write("challenge", page("Challenge", body=link("Register")))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 3600)
        r.activate()
        rows, stats = run()
        check("an edit an hour later is set aside as one working session",
              not rows and stats["same_session"] == 1, f"rows={rows} stats={stats}")
        close, _ = run(min_gap=0)
        check("...and --min-gap 0 includes it", len(close) == 1, f"got {len(close)}")

    # Reliance: the same churn weighs more on a page that leans harder.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        for i in range(4):
            r.write(f"other{i}", page(f"Other {i}", type="concept"))
        r.write("narrow", page("Narrow", body=link("Register")))
        r.write("broad", page("Broad", body=link("Register")
                              + "".join(f"[[Other {i}]]\n" for i in range(4))))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, _ = run()
        by = {x["page"]: x for x in rows}
        check("both pages are reported", set(by) == {"narrow", "broad"}, str(sorted(by)))
        if len(by) == 2:
            check("...and the page leaning harder on it ranks above the page that name-checks it",
                  by["narrow"]["weight"] > by["broad"]["weight"]
                  and rows[0]["page"] == "narrow",
                  f"narrow={by['narrow']['weight']} broad={by['broad']['weight']}")

    # The validation anchor: the sharper question, which this corpus cannot yet answer.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.write("endorsed", page("Endorsed", body=link("Register"), validation="peer",
                                 validated_by="[Indy Johar]", validated_at="2026-06-01"))
        r.write("machine", page("Machine", body=link("Register")))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, stats = run(anchor="validation")
        check("--anchor validation sees only the human-endorsed page",
              [x["page"] for x in rows] == ["endorsed"] and stats["pages"] == 1,
              f"rows={[x['page'] for x in rows]} stats={stats}")

    # The tier is the gate, not the date. A page downgraded to `machine` that still carries a
    # stale `validated_at` is not endorsed by anyone, and must not be read as if it were.
    # Mutation testing found this: deleting the tier check failed no test, because every other
    # machine page in the suite simply had no date to fall back on.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.write("downgraded", page("Downgraded", body=link("Register"), validation="machine",
                                   validated_at="2026-06-01"))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, stats = run(anchor="validation")
        check("a machine page carrying a leftover validated_at is not an endorsement",
              not rows and stats["pages"] == 0, f"rows={rows} stats={stats}")

    # A dependency that did not exist at the anchor cannot be compared. Scoring that as a
    # total rewrite would invent a finding out of an absence.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("challenge", page("Challenge", body="nothing yet\n"))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="a\nb\nc\n"))
        r.commit(T0 + 20 * DAY)
        # the page gains the link, then the register is rewritten — but the page's own body
        # last moved at T0+20*DAY, before which the register did not exist at all
        r.write("challenge", page("Challenge", body=link("Register")))
        r.commit(T0 + 20 * DAY)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\n"))
        r.commit(T0 + 60 * DAY)
        r.activate()
        rows, stats = run()
        check("a dependency present at the anchor is compared, not guessed",
              stats["unmeasurable"] == 0 and len(rows) == 1,
              f"rows={len(rows)} stats={stats}")

    # An anchor older than the repository has no commit behind it. Real: this wiki's pages date
    # from March 2025 and its git repo from 2026-07-03, so 2 rows hit this today. Scoring it as a
    # total rewrite would manufacture the loudest finding in the report out of an absence.
    with tempfile.TemporaryDirectory() as t:
        r = Repo(pathlib.Path(t))
        r.write("register", page("Register", type="concept", body="a\nb\nc\nd\ne\nf\n"))
        r.write("ancient", page("Ancient", body=link("Register"), validation="peer",
                                validated_by="[Indy Johar]", validated_at="1999-01-01"))
        r.commit(T0)
        r.write("register", page("Register", type="concept", body="Z\nY\nX\nW\nV\nU\n"))
        r.commit(T0 + 40 * DAY)
        r.activate()
        rows, stats = run(anchor="validation")
        check("an anchor predating the repository is counted, never scored",
              not rows and stats["unmeasurable"] == 1, f"rows={rows} stats={stats}")

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
