#!/usr/bin/env python3
"""
test_check_onboarding.py — prove the doc checker fires, and prove it stays quiet.

Both halves matter equally. A check that misses real drift is useless; a check that cries
about every backticked word gets switched off within a fortnight, which is worse, because
the repo then believes it is covered. Half of the cases below are false-positive guards.

Usage:  python3 tools/test_check_onboarding.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_onboarding as K  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TIERS = {"public", "unlisted", "internal", "private"}
SKILLS = {"ingest", "query", "lint", "joker"}


def run(text, tiers=TIERS, skills=SKILLS, crons=1, max_axiom=27):
    return K.check_doc("DOC.md", text, tiers, skills, crons, max_axiom)


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
        if not ok:
            fails.append(name)

    def says(found, needle):
        return any(needle in claim or needle in truth for claim, truth in found)

    # --- it fires -----------------------------------------------------------------
    # The real defect: a doc teaching three tiers when the schema has four. `internal`
    # covers 328 pages here, so the omission is not a detail.
    got = run("Pages are `public`, `unlisted` or `private`.")
    check("an incomplete tier list is caught", says(got, "internal"))

    # raw/ has its own cases below, against a tree whose .gitignore is known: whether a
    # raw/ path is ignored depends on the wiki, and a travelling test may not assume it.
    got = run("Run `tools/NOPE-not-a-tool.py` for that.")
    check("a file that does not exist is caught", says(got, "NOPE-not-a-tool.py"))

    got = run("Briefs live in `nowhere-at-all/`.")
    check("a folder that does not exist is caught", says(got, "nowhere-at-all/"))

    got = run("Run the `sorcery` skill for that.")
    check("a skill that does not exist is caught", says(got, "sorcery"))

    got = run("A reflection is written every Friday, automatically.", crons=0)
    check("a scheduled promise with no schedule left is caught", says(got, "scheduled"))

    got = run("The register runs A0–A19.")
    check("a stale axiom range is caught", says(got, "A27"))

    # --- it stays quiet -----------------------------------------------------------
    # Docs name files the way people say them. Anchoring at the root would flag every one.
    check("a bare filename that exists deeper in the tree is not flagged",
          not run("Read `axioms.md` and `index.md` first."))
    check("a folder named without its parent is not flagged",
          not run("Counterpositions land in `challenges/`."))
    check("a placeholder path is not flagged",
          not run("Tell Claude: I've added `raw/<filename>` — please ingest it."))
    check("a doc that names one tier in passing is not required to name all four",
          not run("Keep it `private` unless you are sure."))
    # A commons legitimately contrasts two tiers in prose without listing the set. Firing
    # there taught nothing, and would have had a correct document edited to satisfy the
    # check — which is how a check earns its way into being switched off. Found when the
    # checker was synced to xco-team-wiki and immediately complained about its own docs.
    check("a doc contrasting two tiers in prose is not treated as an enumeration",
          not run("In your own wiki everything starts `private`; here everything starts "
                  "`internal`, and that is a real boundary."))
    # ...but the original defect, three of four with `internal` missing, must still fire.
    got3 = run("Every page is `public`, `unlisted` or `private`.")
    check("three of four tiers is still caught as an incomplete enumeration",
          says(got3, "internal"))
    # A path the sentence places in another repository is not ours to resolve.
    check("a path explicitly located in another wiki is not flagged",
          not run("See `wiki/boundary-review-external-readers.md` in indy-llm-wiki."))
    check("...but an unqualified path that exists nowhere is still flagged",
          says(run("See `wiki/no-such-boundary-note.md` for the detail."),
               "no-such-boundary-note"))
    check("an emphasised ordinary word is not mistaken for a skill",
          not run("**visibility** decides where a page can go."))
    # REGRESSION. `export/` is gitignored and built by CI, so it exists in a working copy
    # where the export has been run and NOT in a clean checkout. The check passed locally
    # and failed in CI — green for the wrong reason, which is the exact failure it exists
    # to catch, one level up. A documented generated artefact is not a broken reference.
    check("a gitignored, CI-generated file is not flagged",
          not run("The graph is written to `export/wiki.json`."))
    check("a gitignored, CI-generated folder is not flagged",
          not run("Anything in `export/` is computed, never hand-edited."))

    check("a generated file named bare, without its ignored folder, is not flagged",
          not run("The public cut is `wiki.public.json`."))
    # And the guard on that leniency: an invented name must still be caught.
    got = run("See `totally-made-up-output.json`.")
    check("an invented file is still caught despite the generated-file leniency",
          says(got, "totally-made-up-output.json"))

    # An example is a shape, not a promise that a particular file exists. Eight wikis failed
    # on the date their CLAUDE.md happens to use to illustrate the per-day log layout, and
    # this one passed only because its example date exists here — a check holding by luck.
    check("a path introduced as an example is not flagged",
          not run("One file per day (e.g. `wiki/log/1999-01-02.md`), appended to."))
    # And the guard: the same non-existent path, asserted rather than illustrated, still fails.
    check("...but the same path asserted as fact is still caught",
          says(run("Today's entries are in `wiki/log/1999-01-02.md`."), "1999-01-02"))
    check("an example folder is still checked, since only files carry the shape problem",
          says(run("Logs live in (e.g. `no-such-log-folder/`)."), "no-such-log-folder/"))

    # A path a PRESENT SKILL names is a path this repo can produce. `wiki/crm/roster.md` is
    # the case: named by the `crm` skill in eight wikis where nobody has added a contact yet.
    # Built against a temporary tree rather than this repo, because which skills a wiki holds
    # differs — a commons has no `crm` at all — and a travelling test may not assume one.
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / ".claude" / "skills" / "crm").mkdir(parents=True)
        (root / ".claude" / "skills" / "crm" / "SKILL.md").write_text(
            "The catalogue is `wiki/crm/roster.md`.\n", encoding="utf-8")
        old_root = K.ROOT
        K.ROOT, K._WRITTEN, K._TREE, K._IGNORED = root, None, None, {}
        try:
            check("a path a skill in this repo creates is not flagged",
                  not run("`wiki/crm/roster.md` is its catalogue."))
            check("...and the guard holds: a path no skill or tool names is still caught",
                  says(run("The roster is `wiki/crm/nobody-writes-this.md`."),
                       "nobody-writes-this"))
        finally:
            K.ROOT, K._WRITTEN, K._TREE, K._IGNORED = old_root, None, None, {}

    # REGRESSION, 2026-09-22. Four wikis ignore `raw/*.md` and un-ignore their real sources
    # one by one, so `git check-ignore` succeeded for ANY `raw/<name>.md` — and their READMEs
    # named `raw/EXAMPLE-sample-source.md`, deleted months earlier, with the gate green. Newer
    # wikis, which un-ignore that one file, failed correctly on the same sentence. Source
    # documents are curated by a person and built by nothing, so "git ignores it" is no
    # evidence that anything will produce it. Built in a throwaway repo with no tools/, so
    # nothing but the rule under test can make a path resolve.
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / ".gitignore").write_text("raw/*.md\n!raw/README.md\nraw/scratch/\nexport/\n",
                                         encoding="utf-8")
        (root / "raw").mkdir()
        (root / "raw" / "README.md").write_text("What goes here.\n", encoding="utf-8")
        (root / "raw" / "assets").mkdir()
        (root / "raw" / "assets" / ".gitkeep").write_text("", encoding="utf-8")
        # Present on this machine, ignored, so absent from every clean checkout.
        (root / "raw" / "local-only-source.md").write_text("Never committed.\n", encoding="utf-8")
        old_root = K.ROOT
        K.ROOT, K._WRITTEN, K._TREE, K._IGNORED = root, None, None, {}
        try:
            check("an invented raw/ file is caught even though .gitignore ignores raw/*.md",
                  says(run("Drop it next to `raw/foo.md`."), "raw/foo.md"))
            check("...including the deleted example four READMEs still named",
                  says(run("A worked example ships in `raw/EXAMPLE-sample-source.md`."),
                       "EXAMPLE-sample-source"))
            check("an invented raw/ folder is caught even though .gitignore ignores it",
                  says(run("Drafts wait in `raw/scratch/`."), "raw/scratch/"))
            # The narrowing must not reach the case the leniency exists for. There is no
            # tools/ here, so only the ignore rule can vouch for `export/wiki.json`.
            check("a gitignored, CI-generated file is still not flagged when raw/ is narrowed",
                  not run("The graph is written to `export/wiki.json`."))
            check("a raw/ file the wiki commits (un-ignored with !raw/...) still resolves",
                  not run("Start with `raw/README.md`."))
            # On disk here, absent in CI. Passing it locally would be green for the wrong
            # reason, the failure this file has recorded twice already.
            check("an ignored raw/ file present only on this machine is still flagged",
                  says(run("See `raw/local-only-source.md`."), "local-only-source"))
            check("the raw/ folder itself is not flagged",
                  not run("Drop the PDF into `raw/`."))
            # Folders are a place to put sources, not sources: every CLAUDE.md names
            # `raw/assets/`, and the file rule must not be applied to it.
            check("a folder under raw/ that exists is not held to the file rule",
                  not run("Images live in `raw/assets/`."))
        finally:
            K.ROOT, K._WRITTEN, K._TREE, K._IGNORED = old_root, None, None, {}

    check("a schedule that really exists is not flagged",
          not run("The newsletter goes out monthly, automatically.", crons=1))
    check("a correct axiom range is not flagged", not run("The register runs A0–A27."))

    # --- the command itself -------------------------------------------------------
    # CLAUDE.md is the constitution and was checked by nothing until 2026-09-15. Assert it
    # stays in scope: removing it would silently stop checking the file every session reads.
    src = open(os.path.join(HERE, "check_onboarding.py"), encoding="utf-8").read()
    check("CLAUDE.md is one of the documents checked", '"CLAUDE.md"' in src)

    r = subprocess.run([sys.executable, os.path.join(HERE, "check_onboarding.py"), "--check"],
                       capture_output=True, text=True)
    check("--check passes on this repo as it stands", r.returncode == 0,
          r.stdout.strip().splitlines()[0] if r.stdout.strip() else "")
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "check_onboarding.py")],
                        capture_output=True, text=True)
    check("a plain run never fails the build", r2.returncode == 0)

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
