#!/usr/bin/env python3
"""
test_check_onboarding.py — prove the doc checker fires, and prove it stays quiet.

Both halves matter equally. A check that misses real drift is useless; a check that cries
about every backticked word gets switched off within a fortnight, which is worse, because
the repo then believes it is covered. Half of the cases below are false-positive guards.

Usage:  python3 tools/test_check_onboarding.py
"""
import os
import subprocess
import sys

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

    # Deliberately NOT under raw/: source documents are gitignored by design, so a
    # reference into raw/ cannot be verified from a checkout and is accepted unchecked.
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

    check("a schedule that really exists is not flagged",
          not run("The newsletter goes out monthly, automatically.", crons=1))
    check("a correct axiom range is not flagged", not run("The register runs A0–A27."))

    # --- the command itself -------------------------------------------------------
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
