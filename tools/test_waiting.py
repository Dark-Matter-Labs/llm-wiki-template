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
import json
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


def fake(branches, proposed, main_contains=(), diffs=None, tips=None):
    """Stand in for GitHub and git. Returns the patches to apply to the module.

    `proposed` may be a plain iterable of branch names, meaning "proposed and merged at the
    beginning of time", or a mapping of branch -> mergedAt, with None for a proposal that
    never merged. `tips` maps branch -> last commit timestamp; the default is older than any
    merge, so a branch with a merged proposal stays quiet unless a test says otherwise.
    """
    diffs = diffs or {}
    tips = tips or {}
    merged = (proposed if isinstance(proposed, dict)
              else {b: "2000-01-01T00:00:00Z" for b in proposed})

    def gh(args):
        if args[:1] == ["api"]:
            return list(branches)
        if args[:1] == ["pr"] and "--state" in args and "all" in args:
            return [{"headRefName": b, "mergedAt": at} for b, at in merged.items()]
        return []

    def ok(cmd, cwd=None):
        if "--is-ancestor" in cmd:
            return cmd[cmd.index("--is-ancestor") + 1].split("/", 1)[-1] in main_contains
        return True                                      # rev-parse: the ref exists

    def run(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "diff"]:
            ref = next(c for c in cmd if "..." in c).split("...")[-1].split("/", 1)[-1]
            if "--unified=0" in cmd:
                return ""                               # no content: nothing to measure
            files = diffs.get(ref, [])
            if "--diff-filter=A" in cmd:
                return "\n".join(files)
            return "\n".join(files)
        if cmd[:2] == ["git", "log"]:
            if any("%cI" in c for c in cmd):   # membership, not substring, was the bug
                return tips.get(cmd[-1].split("/", 1)[-1], "1999-01-01T00:00:00Z")
            return "2026-07-04"
        return ""
    return gh, ok, run


def with_fake(branches, proposed, main_contains=(), diffs=None, tips=None):
    gh, ok, run = fake(branches, proposed, main_contains, diffs, tips)
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
    check("a page with no visibility is read as private, per the schema default",
          got.get("claude/aaa", {}).get("visibility") == "private")

    # 7e. THE BOUNDARY. This shipped to eleven repositories, one of them public, and the
    #     decision page in the wiki that wrote it is `private`. Its title was going into an
    #     issue body with nothing in the path asking what tier the page was.
    old = W.decisions
    W.decisions = lambda: {"old": {"page": "A private ruling", "when": "2026-09-03",
                                   "validation": "self", "validated_by": "[gurden]",
                                   "visibility": "private", "by_a_person": True}}
    gh, ok, run = fake(["main", "old"], proposed=[], diffs={"old": ["wiki/a.md"]})
    keep = (W._gh_json, W._ok, W._run)
    W._gh_json, W._ok, W._run = gh, ok, run
    try:
        m = W.gather("owner/repo")
        check("a private page's title is withheld under --public-safe",
              "A private ruling" not in W.markdown(m, public_safe=True))
        check("...but the decision is still reported, so nothing is hidden, only unnamed",
              "Already decided" in W.markdown(m, public_safe=True))
        check("...and the title IS shown without the flag, inside the repo boundary",
              "A private ruling" in W.markdown(m))
        W.decisions = lambda: {"old": {"page": "A public ruling", "when": "2026-09-03",
                                       "validation": "self", "validated_by": "[gurden]",
                                       "visibility": "public", "by_a_person": True}}
        m = W.gather("owner/repo")
        check("a public page is named even under --public-safe",
              "A public ruling" in W.markdown(m, public_safe=True))
        # The guard that matters most: an unmarked page must not read as publishable.
        W.decisions = lambda: {"old": {"page": "An unmarked ruling", "when": "2026-09-03",
                                       "validation": "self", "validated_by": "[gurden]",
                                       "by_a_person": True}}
        m = W.gather("owner/repo")
        check("a decision with no visibility recorded is withheld, not published",
              "An unmarked ruling" not in W.markdown(m, public_safe=True))
    finally:
        W._gh_json, W._ok, W._run = keep
        W.decisions = old

    # --- the validation ask -------------------------------------------------------------
    # Added 2026-09-16. 823 of 824 pages in this wiki had nobody behind them, and the docs told
    # people to write `validated_by` without `validated_at`, which produced confirmations every
    # read-out counted as zero. Docs alone did not move it; this puts the ask on the surface a
    # non-git person already has.
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "export").mkdir()
        nodes = [
            {"slug": "heavy", "title": "Leaned On", "validation": "machine",
             "inbound_links": ["a", "b", "c"], "visibility": "internal"},
            {"slug": "light", "title": "Barely Cited", "validation": "machine",
             "inbound_links": ["a"], "visibility": "internal"},
            {"slug": "orphan", "title": "Nothing Cites This", "validation": "machine",
             "inbound_links": [], "visibility": "internal"},
            {"slug": "done", "title": "Already Confirmed", "validation": "self",
             "inbound_links": ["a", "b", "c", "d"], "visibility": "internal"},
            {"slug": "gone", "title": "Retired", "validation": "machine", "status": "dormant",
             "inbound_links": ["a", "b", "c", "d", "e"], "visibility": "internal"},
        ]
        (root / "export" / "wiki.json").write_text(json.dumps({"nodes": nodes}))
        old_root = W.ROOT_P
        W.ROOT_P = root
        try:
            sb = W.nothing_stands_behind(limit=3)
        finally:
            W.ROOT_P = old_root
    titles = [r["title"] for r in sb["pages"]]
    check("the most leaned-on unconfirmed page is named first", titles[:1] == ["Leaned On"],
          str(titles))
    check("a page a person already stood behind is not asked about again",
          "Already Confirmed" not in titles)
    check("a retired page is not asked about", "Retired" not in titles)
    check("a page nothing cites is not put in front of anybody",
          "Nothing Cites This" not in titles, "weight is the whole point of a sample of three")
    check("the total counts every unconfirmed live page, not just the sample",
          sb["total_unvalidated"] == 3, str(sb))

    # NO AUTHORSHIP. "Which pages did X write" is the question the house rule refuses, and it
    # is the obvious way to build this feature.
    src_w = pathlib.Path(__file__).resolve().parent.joinpath("waiting.py").read_text()
    region = src_w[src_w.index("def nothing_stands_behind"):src_w.index("def gather")]
    check("the ask reads no authorship field",
          not any(k in region for k in ("contributed_by", "author", "validated_by\"")),
          "knowledge, not surveillance")

    # Without a built graph it must say nothing rather than guess.
    with tempfile.TemporaryDirectory() as tmp:
        old_root = W.ROOT_P
        W.ROOT_P = pathlib.Path(tmp)
        try:
            sb = W.nothing_stands_behind()
        finally:
            W.ROOT_P = old_root
    check("with no graph built it offers nothing rather than guessing",
          sb["available"] is False and sb["pages"] == [])

    # And the date, which is the whole reason this exists.
    m = {"repo": "owner/repo", "proposals": [], "never_proposed": [], "decided": [],
         "unavailable": None,
         "stand_behind": {"available": True, "total_unvalidated": 9, "total_pages": 10,
                          "pages": [{"title": "Leaned On", "slug": "heavy",
                                     "leaned_on_by": 3, "visibility": "internal"}]}}
    md = W.markdown(m)
    check("the issue shows all three lines, including validated_at",
          "validation: self" in md and "validated_by:" in md and "validated_at:" in md,
          "a confirmation without a date is invisible to every read-out")
    check("...and says only a person may do it", "may never do it for you" in md.lower()
          or "never do for you" in md.lower())
    # The boundary again. A public repository may name only public pages here, exactly as it
    # may name only a public decision page. Missed on the first pass of this feature.
    m["stand_behind"]["pages"] = [
        {"title": "A Private Page", "slug": "p", "leaned_on_by": 9, "visibility": "private"},
        {"title": "A Public Page", "slug": "q", "leaned_on_by": 2, "visibility": "public"}]
    safe = W.markdown(m, public_safe=True)
    check("a private page's title is not put in a public repository's issue",
          "A Private Page" not in safe)
    check("...but a public one still is", "A Public Page" in safe)
    check("...and the title IS shown inside a private repository",
          "A Private Page" in W.markdown(m))

    # --- held files, computed from this repository alone -----------------------------------
    # A held file is exempt from every later shared-layer correction and looks identical to a
    # current one. On 2026-09-15 a fix reached ten wikis and not the eleventh for that reason.
    # The sync can only see this with every repo on one disk; a CI runner has one. So it is
    # computed here from the travelling manifest plus the recorded base, with no source and
    # no network.
    def held_world(tmp, files, base, source="some-source", name="a-wiki"):
        root = pathlib.Path(tmp) / name
        (root / "design").mkdir(parents=True)
        for rel, body in files.items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
        (root / "design" / "shared-layer.json").write_text(
            json.dumps({"source": source, "shared": sorted(files)}), encoding="utf-8")
        (root / "design" / ".sync-state.json").write_text(
            json.dumps({"written": base}), encoding="utf-8")
        return root

    def dig(s):
        import hashlib
        return hashlib.sha256(s.encode()).hexdigest()

    with tempfile.TemporaryDirectory() as tmp:
        root = held_world(tmp, {"a.md": "accepted\n", "b.md": "adapted\n",
                                "c.md": "never written\n"},
                          {"a.md": dig("accepted\n"), "b.md": dig("as sent\n")})
        old_root = W.ROOT_P
        W.ROOT_P = root
        try:
            h = W.held_here()
        finally:
            W.ROOT_P = old_root
    paths = {r["path"]: r["why"] for r in h["files"]}
    check("a file matching what was last accepted is not held", "a.md" not in paths, str(paths))
    check("a file changed locally is reported as held",
          "changed here" in paths.get("b.md", ""), str(paths))
    check("a file that was never accepted is reported too, which is the quieter case",
          "never accepted" in paths.get("c.md", ""), str(paths))

    # The SOURCE emits the layer and accepts nothing, so nothing there is held. The first
    # version reported all 94 shared files as held in the source wiki, which is the loudest
    # possible way for a staleness report to be useless.
    with tempfile.TemporaryDirectory() as tmp:
        root = held_world(tmp, {"a.md": "x\n"}, {}, source="a-wiki", name="a-wiki")
        old_root = W.ROOT_P
        W.ROOT_P = root
        try:
            h = W.held_here()
        finally:
            W.ROOT_P = old_root
    check("the source wiki reports nothing held, because the question does not apply",
          h["files"] == [] and h["is_source"] is True, str(h))

    # No manifest at all: say nothing rather than guess.
    with tempfile.TemporaryDirectory() as tmp:
        old_root = W.ROOT_P
        W.ROOT_P = pathlib.Path(tmp)
        try:
            h = W.held_here()
        finally:
            W.ROOT_P = old_root
    check("with no shared manifest it reports nothing rather than guessing",
          h["available"] is False and h["files"] == [])

    md = W.markdown({"repo": "o/r", "proposals": [], "never_proposed": [], "decided": [],
                     "unavailable": None, "stand_behind": {},
                     "held": {"available": True, "is_source": False, "shared_total": 9,
                              "files": [{"path": "ONBOARDING.md",
                                         "why": "never accepted from the shared layer"}]}})
    check("the issue names the held file and says what it means",
          "ONBOARDING.md" in md and "will not receive shared corrections" in md)

    # The workflow must actually pass the flag, or the tool's care is decoration.
    wf = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows" / "waiting.yml"
    y = wf.read_text(encoding="utf-8")
    check("the workflow asks GitHub whether the repository is private", "isPrivate" in y)
    check("...and passes --public-safe when it is not", "--public-safe" in y)

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


    # ---- contributed_but_gone: the path home, after a rename -------------------------
    #
    # Found 2026-09-18. Contribution keeps the source's slug, so the commons copy and its
    # origin are joined by path and nothing else. Two pages here were renamed by a lint
    # pass and the join broke in silence; the commons copies were still correct, and only
    # the pointer home was wrong. Four such cases existed in 638 contributed pages.

    def gone_world(tmp, here, commons_nodes, name="a-wiki", commons="the-commons"):
        root = pathlib.Path(tmp) / name
        (root / "wiki").mkdir(parents=True)
        for slug in here:
            f = root / "wiki" / (slug + ".md")
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("---\ntitle: x\n---\n", encoding="utf-8")
        cut = root / ".commons" / commons / "export"
        cut.mkdir(parents=True)
        (cut / "wiki.shared.json").write_text(
            json.dumps({"nodes": commons_nodes}), encoding="utf-8")
        return root

    def gone_of(root):
        src = (pathlib.Path(__file__).resolve().parent / "waiting.py").read_text()
        region = src[src.index("def contributed_but_gone"):src.index("def nothing_stands_behind")]
        ns = {"ROOT_P": root, "json": json, "pathlib": pathlib}
        exec(compile(region, "waiting.py", "exec"), ns)
        return ns["contributed_but_gone"]()

    with tempfile.TemporaryDirectory() as tmp:
        root = gone_world(tmp, ["kept", "deltas/nested"], [
            {"origin": "a-wiki", "slug": "kept", "title": "Kept"},
            {"origin": "a-wiki", "slug": "renamed-away", "title": "Renamed Away"},
            {"origin": "a-wiki", "slug": "deltas/nested", "title": "Nested"},
            {"origin": "another-wiki", "slug": "not-mine", "title": "Someone Else's"},
            {"slug": "written-in-the-commons", "title": "No Origin"},
        ])
        g = gone_of(root)
        rows = g["rows"]
        check("the renamed page is reported", [r["slug"] for r in rows] == ["renamed-away"],
              str(rows))
        check("a page still present is not reported", all(r["slug"] != "kept" for r in rows))
        check("a nested slug still present is not reported",
              all(r["slug"] != "deltas/nested" for r in rows))
        check("another wiki's page is not reported",
              all(r["slug"] != "not-mine" for r in rows))
        check("a page written in the commons is not reported",
              all(r["slug"] != "written-in-the-commons" for r in rows))

    with tempfile.TemporaryDirectory() as tmp:
        root = gone_world(tmp, [], [])
        # gone_world always writes a cut, so remove it to get the real absent case.
        for f in (root / ".commons").rglob("wiki.shared.json"):
            f.unlink()
        g = gone_of(root)
        check("no commons cut means unavailable, not empty", g["available"] is False, str(g))

    # A section that renders nothing when it could not look is the failure this whole
    # session kept finding. Caught on 2026-09-18: waiting.yml never fetched the commons
    # cut, so this check ran every week and could not once have fired.
    blank = {"repo": "x", "proposals": [], "never_proposed": [], "decided": [],
             "gone": {"available": False, "rows": []}}
    check("an unavailable check says so in the issue",
          "looked at nothing" in W.markdown(blank), W.markdown(blank)[:200])
    check("...and in the terminal",
          "could not be checked" in W.render(blank), W.render(blank)[:200])
    check("the weekly workflow fetches the cut it needs",
          "COMMONS_READ_TOKEN" in (pathlib.Path(__file__).resolve().parent.parent
                                   / ".github/workflows/waiting.yml").read_text(),
          "waiting.yml does not fetch the commons, so the check cannot fire")

    # The boundary: a wiki's own page names are not public. Same hole that was closed in
    # the validation ask on 2026-09-16.
    with tempfile.TemporaryDirectory() as tmp:
        root = gone_world(tmp, [], [{"origin": "a-wiki", "slug": "a-private-thing",
                                     "title": "Secret", "visibility": "internal"}])
        m = {"repo": "x", "proposals": [], "never_proposed": [], "decided": [],
             "gone": gone_of(root)}
        pub = W.markdown(m, public_safe=True)
        unpub = W.markdown(m, public_safe=False)
        check("a non-public path is withheld under --public-safe",
              "a-private-thing" not in pub, pub[:200])
        check("and shown without it", "a-private-thing" in unpub, unpub[:200])

    # MUTATION: stop comparing against what is here, and the rename stops being reported.
    src_g = (pathlib.Path(__file__).resolve().parent / "waiting.py").read_text()
    needle = "            if slug and slug not in mine:"
    if needle not in src_g:
        check("mutation anchor present", False, "the comparison this tests is not there")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            root = gone_world(tmp, ["kept"], [
                {"origin": "a-wiki", "slug": "renamed-away", "title": "Renamed Away"}])
            region = src_g[src_g.index("def contributed_but_gone"):src_g.index("def nothing_stands_behind")]
            region = region.replace(needle, "            if False:")
            ns = {"ROOT_P": root, "json": json, "pathlib": pathlib}
            exec(compile(region, "mutant", "exec"), ns)
            check("mutant reports nothing where the real one reports a rename",
                  ns["contributed_but_gone"]()["rows"] == [])


    # ---- could_go_up: the asking the up-flow never had ------------------------------
    #
    # contribution_prompt has computed this since 19 August and nothing ran it on a
    # cadence. The renderings are tested rather than the tool it wraps, which has its own
    # tests: what can go wrong here is a section that says nothing when it could not look,
    # or one that names a page the reader is not entitled to see.

    up_rows = {"available": True, "targets": [
        {"commons": "a-commons", "eligible": 2, "pages_here": 10, "overlap_unknown": False,
         "top": [{"slug": "public-one", "title": "P", "visibility": "public", "inbound": 9},
                 {"slug": "internal-one", "title": "I", "visibility": "internal", "inbound": 4}]}]}
    base = {"repo": "x", "proposals": [], "never_proposed": [], "decided": []}

    md = W.markdown({**base, "up": up_rows}, public_safe=False)
    check("the count carries its denominator", "2 of 10 page(s)" in md, md[:200])
    check("an internal slug is named without --public-safe", "internal-one" in md, md[:300])

    md_safe = W.markdown({**base, "up": up_rows}, public_safe=True)
    check("a public slug is still named under --public-safe", "public-one" in md_safe,
          md_safe[:300])
    check("an internal slug is withheld under --public-safe", "internal-one" not in md_safe,
          md_safe[:300])

    big = {"available": True, "targets": [
        {"commons": "a-commons", "eligible": 638, "pages_here": 824, "overlap_unknown": False,
         "top": []}]}
    md_big = W.markdown({**base, "up": big})
    check("a large share reads as a relationship, not a backlog",
          "Nearly everything here" in md_big, md_big[:300])

    unknown = {"available": True, "targets": [
        {"commons": "a-commons", "eligible": 5, "pages_here": 10, "overlap_unknown": True,
         "top": []}]}
    md_unk = W.markdown({**base, "up": unknown})
    check("an unchecked overlap says the count is of eligible, not of new",
          "could not be checked" in md_unk and "not of\nwhat is new" in md_unk.replace("  ", " ")
          or "not of what is new" in md_unk, md_unk[:300])

    md_off = W.markdown({**base, "up": {"available": False, "why": "the tools would not load"}})
    check("a section that could not look says so",
          "looked at\nnothing" in md_off or "looked at nothing" in md_off, md_off[:300])

    # A top commons contributes nowhere and is not behind on anything.
    md_none = W.markdown({**base, "up": {"available": True, "targets": []}})
    check("a wiki that contributes nowhere gets no section",
          "could go to" not in md_none, md_none[:200])

    # MUTATION: stop filtering by visibility, and the internal slug must leak into the
    # public cut. Without this the four cases above pass on a filter that does nothing.
    src_u = (pathlib.Path(__file__).resolve().parent / "waiting.py").read_text()
    needle = 'if (c["visibility"] == "public" or not public_safe)'
    if needle not in src_u:
        check("mutation anchor present", False, "the visibility filter has moved")
    else:
        import types
        mutant = types.ModuleType("waiting_mutant")
        mutant.__file__ = str(pathlib.Path(__file__).resolve().parent / "waiting.py")
        exec(compile(src_u.replace(needle, "if True"), "waiting_mutant", "exec"),
             mutant.__dict__)
        leaked = mutant.markdown({**base, "up": up_rows}, public_safe=True)
        check("mutant leaks the internal slug into the public cut",
              "internal-one" in leaked, leaked[:300])


    # ---- a deliberate adaptation is not the same finding as a forgotten edit ----------
    #
    # The commons ONBOARDING.md is written for a contributor joining a shared corpus rather
    # than an owner starting a personal one. It is SUPPOSED to differ, and the report called
    # it "never accepted from the shared layer" — crying wolf about a file somebody maintains
    # by hand, in a list whose whole value is that it is short.

    def adapted_world(tmp, files, base, adapted, source="some-source", name="a-wiki"):
        root = pathlib.Path(tmp) / name
        (root / "design").mkdir(parents=True)
        for rel, body in files.items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
        (root / "design" / "shared-layer.json").write_text(
            json.dumps({"source": source, "shared": sorted(files)}), encoding="utf-8")
        (root / "design" / ".sync-state.json").write_text(
            json.dumps({"written": base, "adapted": adapted}), encoding="utf-8")
        return root

    with tempfile.TemporaryDirectory() as tmp:
        root = adapted_world(
            tmp,
            {"ONBOARDING.md": "adapted\n", "stray.md": "edited and forgotten\n"},
            base={},                       # neither has a base
            adapted={"ONBOARDING.md": {"reviewed_at": "2026-09-18", "why": "written for a commons"}})
        old_root = W.ROOT_P
        W.ROOT_P = root
        try:
            h = W.held_here()
        finally:
            W.ROOT_P = old_root
        rows = {r["path"]: r for r in h["files"]}
        check("the declared one is marked deliberate", rows["ONBOARDING.md"].get("deliberate") is True,
              str(rows.get("ONBOARDING.md")))
        check("...and carries the recorded reason",
              "written for a commons" in rows["ONBOARDING.md"]["why"], str(rows["ONBOARDING.md"]))
        check("the undeclared one is not marked deliberate",
              not rows["stray.md"].get("deliberate"), str(rows["stray.md"]))
        check("...and still says nobody accepted it",
              "never accepted" in rows["stray.md"]["why"], str(rows["stray.md"]))

        m = {"repo": "x", "proposals": [], "never_proposed": [], "decided": [], "held": h}
        md = W.markdown(m)
        check("the issue marks the deliberate row", "**on purpose**" in md, md[:300])
        check("...and counts the ones that are not",
              "1 not declared deliberate" in W.render(m), W.render(m)[:300])

    # MUTATION: ignore the declaration, and the deliberate row becomes a warning again.
    src_h = (pathlib.Path(__file__).resolve().parent / "waiting.py").read_text()
    needle = "        if rel in adapted:"
    if needle not in src_h:
        check("mutation anchor present", False, "the declaration branch has moved")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            root = adapted_world(tmp, {"ONBOARDING.md": "adapted\n"}, base={},
                                 adapted={"ONBOARDING.md": {"reviewed_at": "x", "why": "y"}})
            region = src_h[src_h.index("def held_here"):src_h.index("def gather(")]
            region = region.replace(needle, "        if False:")
            ns = {"ROOT_P": root, "json": json, "pathlib": pathlib, "hashlib": __import__("hashlib")}
            exec(compile(region, "mutant", "exec"), ns)
            rows = ns["held_here"]()["files"]
            check("mutant reports the adaptation as an accident",
                  rows and not rows[0].get("deliberate"), str(rows))

    # ---- work pushed to a branch after its proposal merged --------------------------
    #
    # Measured in indy-llm-wiki on 2026-09-22: twelve branches carried commits added after
    # their pull request merged, and every one was invisible here, because the old code
    # skipped any branch whose name had ever appeared on a proposal. The inbox built to
    # surface stranded work was reporting "Nothing is waiting" over a real backlog.
    rows = with_fake(["kept-working"],
                     {"kept-working": "2026-08-01T00:00:00Z"},
                     diffs={"kept-working": ["wiki/a.md"]},
                     tips={"kept-working": "2026-09-01T00:00:00Z"})
    check("work added after a merge is waiting again",
          [r["branch"] for r in rows] == ["kept-working"], str(rows))

    rows = with_fake(["landed"],
                     {"landed": "2026-09-01T00:00:00Z"},
                     diffs={"landed": ["wiki/a.md"]},
                     tips={"landed": "2026-08-01T00:00:00Z"})
    check("a branch with nothing added since it merged stays quiet",
          rows == [], str(rows))

    # A proposal opened and closed without merging is a decision a person took. Raising it
    # again would be the tool arguing with them.
    rows = with_fake(["turned-down"], {"turned-down": None},
                     diffs={"turned-down": ["wiki/a.md"]},
                     tips={"turned-down": "2026-09-01T00:00:00Z"})
    check("a proposal closed without merging is not raised again",
          rows == [], str(rows))

    # MUTATION. Put the old rule back, skipping on the mere existence of a proposal, and the
    # first case must stop being reported. If it still passes, the check is decorative.
    src = pathlib.Path(W.__file__).read_text(encoding="utf-8")
    guard = src[src.index('        merged_at = proposed.get(b'):
                src.index('# nothing added since it landed') + len('# nothing added since it landed')]
    gh, ok, run = fake(["kept-working"], {"kept-working": "2026-08-01T00:00:00Z"},
                       diffs={"kept-working": ["wiki/a.md"]},
                       tips={"kept-working": "2026-09-01T00:00:00Z"})
    mutant = src.replace(guard, "        if b in proposed:\n            continue")
    check("the mutation actually changed the source", mutant != src, "guard text not found")
    ns = {"__name__": "mutant", "__file__": W.__file__}
    exec(compile(mutant, "mutant-waiting", "exec"), ns)
    ns["_gh_json"], ns["_ok"], ns["_run"] = gh, ok, run
    check("mutant (skip on any past proposal) misses the stranded work",
          ns["never_proposed"]("owner/repo") == [], "mutant still reported it")

    # ---- how much of it is not in the wiki, not just how many pages are new ----------
    #
    # Found 2026-09-23. The inbox listed seven unproposed branches with "0 page(s) exist
    # there and nowhere else", and that nearly justified discarding them. One carried a
    # 180-line rewrite of a page main already has, 289 of its 293 added lines on no page in
    # main, because the count only ever looked at pages that were NEW. A rewrite is not new.
    #
    # These run against a real repository in a temporary directory, not a fake, because the
    # thing under test is the reading of git's own output.
    def real_git(repo):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

        def g(*a):
            subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True, env=env)

        def put(rel, body):
            f = pathlib.Path(repo) / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")

        def run(cmd, cwd=None, timeout=60):
            r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=timeout)
            return r.stdout.strip() if r.returncode == 0 else ""

        def ok(cmd, cwd=None):
            return subprocess.run(cmd, cwd=repo, capture_output=True).returncode == 0
        return g, put, run, ok

    LANDED = ["The same paragraph, which reached the wiki under another name.",
              "And its second line, which also reached the wiki another way."]
    REWRITE = ["A rewritten opening that says what the position is actually for.",
               "A second paragraph the page on main has never carried at all.",
               "A third, so the count is not an accident of one line matching."]

    def build(tmp):
        repo = pathlib.Path(tmp) / "repo"
        repo.mkdir()
        g, put, run, ok = real_git(repo)
        g("init", "-q", "-b", "main")
        put("wiki/a-private-slug.md", "---\ntitle: T\n---\nThe original opening line of this page.\n")
        put("wiki/log.md", "# Log\n")
        g("add", "-A"); g("commit", "-q", "-m", "base")
        # A rewrite of a page main already has: no new page, and real work.
        g("checkout", "-q", "-b", "rewrite")
        put("wiki/a-private-slug.md", "---\ntitle: T\n---\n" + "\n".join(REWRITE) + "\nshort\n")
        put("wiki/log.md", "# Log\n## [2026-07-11] ingest | A log line long enough to count\n")
        put("wiki/log/2026-07-11.md", "## [2026-07-11] ingest | Another log line long enough\n")
        g("add", "-A"); g("commit", "-q", "-m", "rewrite")
        # A variant whose words reached main another way, under a different file.
        g("checkout", "-q", "main"); g("checkout", "-q", "-b", "variant")
        put("wiki/variant.md", "\n".join(LANDED) + "\n")
        g("add", "-A"); g("commit", "-q", "-m", "variant")
        g("checkout", "-q", "main")
        put("wiki/landed.md", "\n".join(LANDED) + "\n")
        # A line that reached main only as a log entry is written about, not in the wiki.
        put("wiki/log/2026-07-12.md", REWRITE[0] + "\n")
        g("add", "-A"); g("commit", "-q", "-m", "landed another way")
        for b in ("main", "rewrite", "variant"):
            g("update-ref", f"refs/remotes/origin/{b}", b)
        return repo, run, ok

    def gh_for(branches):
        def gh(args):
            if args[:1] == ["api"]:
                return list(branches)
            if args[:1] == ["pr"]:
                return []
            return None
        return gh

    def measure(ns, repo, run, ok):
        keep = {k: ns[k] for k in ("_gh_json", "_ok", "_run", "ROOT")}
        ns.update(_gh_json=gh_for(["main", "rewrite", "variant"]), _ok=ok, _run=run,
                  ROOT=str(repo))
        try:
            return {r["branch"]: r for r in ns["never_proposed"]("owner/repo")}
        finally:
            ns.update(keep)

    with tempfile.TemporaryDirectory() as tmp:
        repo, run, ok = build(tmp)
        rows = measure(W.__dict__, repo, run, ok)
        rw, va = rows.get("rewrite", {}), rows.get("variant", {})
        check("a rewrite of an existing page counts no new pages", rw.get("new_pages") == 0, str(rw))
        check("...but its unlanded lines are counted", rw.get("unlanded_lines") == 3, str(rw))
        check("...in the one file that carries them", rw.get("unlanded_files") == 1, str(rw))
        check("log lines and short lines are not counted as added work",
              rw.get("added_lines") == 3, str(rw))
        check("lines that reached main in another file are not counted as missing",
              va.get("new_pages") == 1 and va.get("added_lines") == 2
              and va.get("unlanded_lines") == 0, str(va))

        # The headline. "0 pages exist nowhere else" beside 3 lines nowhere else must not read
        # as "nothing would be lost".
        m = {"repo": "o/r", "proposals": [], "never_proposed": [rw], "decided": []}
        md, tx = W.markdown(m, public_safe=True), W.render(m)
        check("the issue says how many lines are not in the wiki",
              "3 line(s)" in md and "1 file(s)" in md, md[:600])
        check("...on the piece's own row, not only in the total",
              any(ln.startswith("| ") and "3 line(s) not in the wiki, 1 file(s)" in ln
                  for ln in md.splitlines()), md[:600])
        check("...and so does the terminal", "3 line(s)" in tx, tx[:600])
        check("no new pages is explained, not left to read as nothing lost",
              "counting new pages alone" in md and "counting new pages alone" in tx, md[:600])
        check("the new figures name no file, so no private path reaches a public issue",
              "a-private-slug" not in md and "a-private-slug" not in tx)
        leaked = [w for w in JARGON if w.lower() in tx.lower()]
        check("...and still use no git vocabulary", not leaked, f"leaked: {leaked}")

        m = {"repo": "o/r", "proposals": [], "never_proposed": [{**va, "new_pages": 0}],
             "decided": []}
        check("work that is all in the wiki already says so, and that nothing would be lost",
              "loses nothing" in W.markdown(m) and "loses nothing" in W.render(m),
              W.markdown(m)[:600])

        # A new page made only of short lines has no line long enough to count, and still exists
        # nowhere else. "Loses nothing" over it is the original failure from the other side.
        stub = {**va, "new_pages": 1, "unlanded_lines": 0, "unlanded_files": 0}
        m = {"repo": "o/r", "proposals": [], "never_proposed": [stub], "decided": []}
        md, tx = W.markdown(m), W.render(m)
        check("a new page is never summed up as nothing to lose",
              "loses nothing" not in md and "loses nothing" not in tx, md[:600])
        check("...and is counted in the headline", "1 page(s) exist there and nowhere else" in md
              and "1 page(s) exist there and nowhere else" in tx, md[:600])

        # A partial clone answers "<id> missing" for a blob it lacks, with a clean exit. Read as
        # an empty blob, every line in it would look absent: the understatement, silently.
        keep = W._cat_blobs
        W._cat_blobs = lambda shas, cwd=None: b"some text line long enough to count\n" + \
            b"0" * 40 + b" missing\n"
        try:
            got = W.landed({"some text line long enough to count"})
        finally:
            W._cat_blobs = keep
        check("a blob main does not have locally gives no figure, not a partial one",
              got is None, str(got))

        # Set aside is not deleted, so a decided piece still says what it holds.
        m = {"repo": "o/r", "proposals": [], "never_proposed": [],
             "decided": [{**rw, "decision": {"page": "A ruling", "when": "2026-09-23",
                                             "by_a_person": True, "visibility": "private"}}]}
        check("a decided piece still reports the lines it holds",
              "3 line(s)" in W.markdown(m, public_safe=True) and "3 line(s)" in W.render(m),
              W.markdown(m)[:600])

        # FAILS HONESTLY. If main cannot be read, every added line would look missing; say it
        # could not be measured instead of printing the overstatement.
        keep = W._cat_blobs
        W._cat_blobs = lambda shas, cwd=None: None
        try:
            rows_off = measure(W.__dict__, repo, run, ok)
        finally:
            W._cat_blobs = keep
        check("an unreadable main gives no figure rather than a wrong one",
              rows_off.get("rewrite", {}).get("unlanded_lines") is None, str(rows_off))
        m = {"repo": "o/r", "proposals": [], "never_proposed": list(rows_off.values()),
             "decided": []}
        check("...and says it could not be measured",
              "could not be measured" in W.markdown(m) and "could not be measured" in W.render(m),
              W.markdown(m)[:600])

        # MUTATIONS. Each must change a number above, or the check it answers is decorative.
        src_m = pathlib.Path(W.__file__).read_text(encoding="utf-8")
        for name, needle, repl, branch, key, want_not in [
            ("stop subtracting what main already has", "if t not in found", "if True",
             "variant", "unlanded_lines", 0),
            ("stop excluding the log", "+ LOG_EXCLUDES", "", "rewrite", "added_lines", 3),
            ("stop ignoring short lines", "MIN_LINE = 20", "MIN_LINE = 0", "rewrite",
             "added_lines", 3),
        ]:
            if needle not in src_m:
                check(f"mutation anchor present: {needle}", False, "the code this tests has moved")
                continue
            ns = {"__name__": "mutant", "__file__": W.__file__}
            exec(compile(src_m.replace(needle, repl), "mutant-waiting", "exec"), ns)
            got = measure(ns, repo, run, ok).get(branch, {}).get(key)
            check(f"mutant ({name}) changes the count", got != want_not, f"still {got}")

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
