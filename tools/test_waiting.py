#!/usr/bin/env python3
"""
test_waiting.py — prove the inbox counts the right things and speaks the right language.

Two failure modes, and the quiet one is worse. If it MISSES work, the work stays invisible
and nothing says so — which is the exact condition it was built to end. If it reports merged
work as waiting, the list fills with noise and stops being read, which ends the same way.

The tests run offline: the GitHub calls are replaced, so nothing here depends on the network
or on what happens to be in somebody's checkout.

Usage:  python3 tools/test_waiting.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import waiting as W  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

#: Words a person who does not know git should never have to meet in this output.
JARGON = ("branch", "commit", "rebase", "remote", "upstream", "HEAD", "checkout",
          "merge conflict", "refspec")


def fake(branches, proposed, main_contains=(), diffs=None):
    """Stand in for GitHub and git. Returns the patches to apply to the module."""
    diffs = diffs or {}

    def gh(args):
        if args[:1] == ["api"]:
            return list(branches)
        if args[:1] == ["pr"] and "--state" in args and "all" in args:
            return [{"headRefName": b} for b in proposed]
        return []

    def ok(cmd, cwd=None):
        if "--is-ancestor" in cmd:
            return cmd[cmd.index("--is-ancestor") + 1].split("/", 1)[-1] in main_contains
        return True                                      # rev-parse: the ref exists

    def run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "diff"]:
            ref = cmd[-1].split("...")[-1].split("/", 1)[-1]
            files = diffs.get(ref, [])
            if "--diff-filter=A" in cmd:
                return "\n".join(files)
            return "\n".join(files)
        if cmd[:2] == ["git", "log"]:
            return "2026-07-04"
        return ""
    return gh, ok, run


def with_fake(branches, proposed, main_contains=(), diffs=None):
    gh, ok, run = fake(branches, proposed, main_contains, diffs)
    old = (W._gh_json, W._ok, W._run)
    W._gh_json, W._ok, W._run = gh, ok, run
    try:
        return W.never_proposed("owner/repo")
    finally:
        W._gh_json, W._ok, W._run = old


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
        if not ok:
            fails.append(name)

    pages = {"lonely": ["wiki/a.md", "wiki/b.md"]}

    # 1. The whole point: work with no proposal must show up.
    got = with_fake(["main", "lonely"], proposed=[], diffs=pages)
    check("work that was never proposed is reported", len(got) == 1 and got[0]["new_pages"] == 2,
          str(got))

    # 2. ...and work that HAS a proposal must not. A list that repeats what is already in
    #    the review queue is a second queue, which is worse than none.
    got = with_fake(["main", "lonely"], proposed=["lonely"], diffs=pages)
    check("work with a proposal is not repeated here", got == [])

    # 3. REGRESSION. A squash merge rewrites history, so a merged branch is NOT an ancestor
    #    of main and ancestry alone would report it as waiting forever. The proposal check
    #    is what separates the two, and removing it must break this.
    got = with_fake(["main", "lonely"], proposed=["lonely"], main_contains=(), diffs=pages)
    check("a squash-merged branch is not reported as waiting", got == [])

    # 4. Work already contained in main is finished, proposal or not.
    got = with_fake(["main", "lonely"], proposed=[], main_contains=("lonely",), diffs=pages)
    check("work already in main is not reported", got == [])

    # 5. An empty branch is not work.
    got = with_fake(["main", "empty"], proposed=[], diffs={"empty": []})
    check("a branch with no changes is not reported", got == [])

    # 6. The export branch is machinery, not somebody's thinking.
    got = with_fake(["main", "export"], proposed=[], diffs={"export": ["export/wiki.json"]})
    check("the export branch is not reported as waiting", got == [])

    # 7. REGRESSION. The GitHub API pages at 30. The first measurement said "30 branches"
    #    and was reporting a page size against a true 61 — a report that silently stops at
    #    thirty is worse than no report, because it looks complete.
    many = ["main"] + [f"b{i}" for i in range(45)]
    got = with_fake(many, proposed=[], diffs={f"b{i}": ["wiki/x.md"] for i in range(45)})
    check("more than one API page of branches is counted", len(got) == 45, f"got {len(got)}")
    src = open(os.path.join(HERE, "waiting.py"), encoding="utf-8").read()
    check("and the branch listing actually asks for every page", '"--paginate"' in src)

    # 7b. REGRESSION, and the one that actually shipped. A query that COULD NOT BE MADE is
    #     not a query that found nothing. The first real run granted no `pull-requests`
    #     scope, the proposal query came back empty, every branch looked unproposed, and the
    #     issue said 55 pieces against a true 37. It must refuse, not guess.
    def gh_no_pr(args):
        if args[:1] == ["api"]:
            return ["main", "lonely"]
        return None                                      # the query could not be made
    old = (W._gh_json, W._ok, W._run)
    _, ok, run = fake(["main", "lonely"], [], (), pages)
    W._gh_json, W._ok, W._run = gh_no_pr, ok, run
    try:
        raised = False
        try:
            W.never_proposed("owner/repo")
        except W.Unavailable:
            raised = True
        check("a proposal query that cannot be made raises, never returns an empty set",
              raised)
        m = W.gather("owner/repo")
        check("...and gather reports the gap instead of a number",
              m["unavailable"] and m["never_proposed"] == [])
        check("...and the issue body says so rather than showing a wrong list",
              "could not be worked out" in W.markdown(m))
    finally:
        W._gh_json, W._ok, W._run = old

    # 7c. Decisions. The tool's first real output re-opened a question the corpus had closed
    #     on 2026-09-03 — on a page written specifically to stop anyone re-deriving it. An
    #     inbox that keeps re-raising settled matters trains people to stop opening it.
    gh, ok, run = fake(["main", "old", "fresh"], proposed=[], diffs={"old": ["wiki/a.md"],
                                                                    "fresh": ["wiki/b.md"]})
    old = (W._gh_json, W._ok, W._run, W.decisions)
    W._gh_json, W._ok, W._run = gh, ok, run
    W.decisions = lambda: {"old": {"page": "The ruling", "when": "2026-09-03",
                                   "validation": "machine", "validated_by": "",
                                   "by_a_person": False}}
    try:
        m = W.gather("owner/repo")
        check("work with a recorded decision leaves the waiting list",
              [r["branch"] for r in m["never_proposed"]] == ["fresh"],
              str([r["branch"] for r in m["never_proposed"]]))
        check("...and is reported separately as decided", len(m["decided"]) == 1)
        check("a decision nobody stood behind is flagged as such, in both renderers",
              "NOBODY HAS STOOD BEHIND" in W.render(m)
              and "Nobody has stood behind" in W.markdown(m))
        # ...and a decision a PERSON made is not nagged about.
        W.decisions = lambda: {"old": {"page": "The ruling", "when": "2026-09-03",
                                       "validation": "collective",
                                       "validated_by": "[indy, gurden]", "by_a_person": True}}
        m2 = W.gather("owner/repo")
        check("a decision a person stood behind carries no warning",
              "NOBODY HAS STOOD BEHIND" not in W.render(m2))
        check("...but is still shown, so the decision itself stays visible",
              len(m2["decided"]) == 1 and "Already decided" in W.markdown(m2))
    finally:
        W._gh_json, W._ok, W._run, W.decisions = old

    # 7d. The real parser, not a stub. The stubs above hand `by_a_person` straight to the
    #     renderer, so forcing it True passed every one of them — the single most important
    #     distinction in this tool was untested. This exercises decisions() itself.
    with tempfile.TemporaryDirectory() as d:
        w = pathlib.Path(d) / "wiki"
        w.mkdir()
        (w / "machine.md").write_text(
            "---\ntitle: A ruling nobody signed\nvalidation: machine\n"
            "timestamp: 2026-09-03\ndecides:\n  - claude/aaa\n---\nbody\n", encoding="utf-8")
        (w / "person.md").write_text(
            "---\ntitle: A ruling somebody signed\nvalidation: collective\n"
            "validated_by: [indy, gurden]\ntimestamp: 2026-09-04\n"
            "decides:\n  - claude/bbb\n---\nbody\n", encoding="utf-8")
        old_root = W.ROOT_P
        W.ROOT_P = pathlib.Path(d)
        try:
            got = W.decisions()
        finally:
            W.ROOT_P = old_root
    check("decisions() finds every page carrying a `decides:` block", set(got) == {"claude/aaa", "claude/bbb"},
          str(sorted(got)))
    check("a machine-validated ruling is not counted as a person's",
          got.get("claude/aaa", {}).get("by_a_person") is False)
    check("a ruling with validation and a name IS counted as a person's",
          got.get("claude/bbb", {}).get("by_a_person") is True)
    check("...and the deciding page is named, so the ruling can be read",
          got.get("claude/bbb", {}).get("page") == "A ruling somebody signed")

    # 8. The language. This exists for someone who does not know what a branch is; leaking
    #    the vocabulary back into the output would defeat the entire exercise.
    text = W.render({"repo": "owner/repo", "proposals": [
        {"number": 1, "title": "Add the Madrid note", "url": "u", "since": "2026-09-01",
         "state": "checked and ready"}],
        "never_proposed": [{"branch": "b", "when": "2026-07-04", "new_pages": 2,
                            "files": 3, "url": "u2"}]})
    leaked = [w for w in JARGON if w.lower() in text.lower()]
    check("the report uses no git vocabulary", not leaked, f"leaked: {leaked}")
    check("...and still says what to do", "propose" in text.lower())

    # 9. A quiet repo reads as quiet, not as broken.
    text = W.render({"repo": "owner/repo", "proposals": [], "never_proposed": []})
    check("nothing waiting is stated plainly", "Nothing is waiting" in text)

    # 10. It must never act on its own.
    check("no merge or push command exists in the tool",
          not any(w in src for w in ("pr merge", "git push", "--squash")))

    r = subprocess.run([sys.executable, os.path.join(HERE, "waiting.py"), "--repo", ""],
                       capture_output=True, text=True)
    check("an unusable repo argument exits non-zero", r.returncode != 0)

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
