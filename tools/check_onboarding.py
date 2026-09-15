#!/usr/bin/env python3
"""check_onboarding.py — hold the human-facing docs to the same standard as the code.

The wiki's automatic checks cover the corpus and the tooling and stop at the doorstep. The
documents that a new person actually reads first — ONBOARDING.md, EDITING.md, START-HERE.md,
README.md — were checked by nobody, and on 2026-09-15 they had drifted exactly as far as you
would expect:

    ONBOARDING.md named three visibility tiers      the schema has four, and the missing one
                                                    (`internal`) covers 328 of this wiki's pages
    ONBOARDING.md said axioms run A0-A19            the register reaches A27
    ONBOARDING.md promised a weekly reflection      its schedule was retired the same morning
      "every Friday, automatically"
    ONBOARDING.md listed 8 skills                   25 exist

None of that is sloppiness. A document describing a system that keeps changing is wrong by
default; the only question is whether anything notices. Every claim below is one a script can
settle, so a script settles it.

WHAT IT DOES NOT CHECK. Whether the docs are any good, whether the tone is right, whether the
order helps — none of that is mechanisable, and pretending otherwise would give a false all-
clear on the part that actually matters. This checks the facts and says so.

It also cannot check a reference into a gitignored tree. `raw/` holds source documents that
deliberately never leave the machine that ingested them, and `export/` is built by CI, so
neither is present in a clean checkout: a path under either is accepted unverified. Treating
their absence as an error would fail every correct doc in the federation; treating it as
proof of existence would be a lie. It is accepted, and recorded here as the blind spot.

    python3 tools/check_onboarding.py            # report
    python3 tools/check_onboarding.py --check    # exit non-zero on any drift (CI)
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The documents a person reads before they read anything else.
#: CLAUDE.md is here since 2026-09-15. It is the constitution, it is read at the start of every
#: session, and it was checked by nothing. The first run against it found `wiki/index/dormant.md`,
#: a shelf the file had described since dormancy was designed and which did not exist.
DOCS = ("ONBOARDING.md", "EDITING.md", "START-HERE.md", "README.md", "SHARING-AND-ACCESS.md",
        "CLAUDE.md")

#: Backticked things that look like paths but are illustrative, not references.
PLACEHOLDER = re.compile(r"[<>…]|\bYYYY\b|\bfilename\b|\bsomething\b")

#: "runs every Friday", "automatically each week", "weekly reflection every Friday"
SCHEDULE = re.compile(
    r"(every (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month|day)"
    r"|each (?:week|month|day)|weekly|monthly|nightly|daily)", re.I)
#: ...but only when the sentence also claims it happens on its own.
AUTOMATIC = re.compile(r"automatic|on its own|by itself|runs? (?:on|itself)|scheduled", re.I)


_TREE = None
_IGNORED = {}


def _generated(path: str) -> bool:
    """True when git is told to ignore this path — i.e. it is built, not committed.

    `export/` is the case that matters: the docs describe it correctly ("built by CI, not
    committed to main"), and it exists in any working copy where the export has been run.
    So this check passed on my machine and failed in CI on a clean checkout — green for the
    wrong reason, which is the failure it was written to catch, one level up. A documented
    generated artefact is not a broken reference.
    """
    if path in _IGNORED:
        return _IGNORED[path]
    hit = False
    try:
        import subprocess
        # Both spellings. A pattern written `export/` matches directories only, and git
        # decides directory-ness from the filesystem — so `check-ignore export` matched on
        # my machine, where the export had been built, and did not match in CI, where the
        # directory does not exist. That is the same green-for-the-wrong-reason bug a
        # second time, in the fix for the first one.
        for probe in (path, path.rstrip("/") + "/"):
            r = subprocess.run(["git", "check-ignore", "-q", probe],
                               cwd=ROOT, capture_output=True, timeout=10)
            if r.returncode == 0:
                hit = True
                break
    except Exception:                                    # noqa: BLE001 — no git, no opinion
        hit = False
    if not hit:
        # A bare basename — docs say `wiki.public.json`, not `export/wiki.public.json`.
        # Accept it only when this repo's own tooling actually writes that name. The
        # tempting shortcut is "it would be ignored inside an ignored directory", but
        # `export/` ignores everything under it, so that rule accepts any invented name
        # at all and the check quietly stops checking. Tried, caught by its own tests,
        # replaced with this.
        hit = _written_by_tooling(pathlib.PurePosixPath(path.rstrip("/")).name)
    _IGNORED[path] = hit
    return hit


_NAMES = None
_WRITTEN = None


def _written_by_tooling(name: str) -> bool:
    """True when some tool or workflow in this repo names this file as something it makes.

    Narrow on purpose: it proves the artefact is real without requiring it to be present
    in a checkout, and it cannot be satisfied by a name nobody produces.
    """
    global _WRITTEN
    if not name:
        return False
    if _WRITTEN is None:
        _WRITTEN = ""
        for d in (ROOT / "tools", ROOT / ".github" / "workflows"):
            if not d.is_dir():
                continue
            for f in d.rglob("*"):
                # Skip tests and this file: both quote names that do NOT exist, on purpose,
                # and reading them back would let a fake name vouch for itself.
                if f.name.startswith("test_") or f.name == "check_onboarding.py":
                    continue
                if f.suffix in {".py", ".yml", ".mjs", ".sh"}:
                    try:
                        _WRITTEN += f.read_text(encoding="utf-8", errors="ignore")
                    except Exception:                    # noqa: BLE001
                        pass
    return name in _WRITTEN


def _ignored_names() -> "set[str]":
    """Basenames appearing in .gitignore, for resolving a generated file named bare."""
    global _NAMES
    if _NAMES is None:
        _NAMES = set()
        f = ROOT / ".gitignore"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name = pathlib.PurePosixPath(line.lstrip("!").rstrip("/")).name
                if name and "*" not in name:
                    _NAMES.add(name)
    return _NAMES


def _resolves(path: str, want_dir: bool = False) -> bool:
    """True if `path` names something in this repo, matched as a path suffix.

    Docs say `axioms.md` and `challenges/`, not `wiki/axioms.md` and `wiki/challenges/`,
    and rightly so. Anchoring only at the root would report every one of those as missing.
    """
    global _TREE
    if (ROOT / path).exists() or _generated(path):
        return True
    if _TREE is None:
        _TREE = [q.relative_to(ROOT).as_posix()
                 for q in ROOT.rglob("*")
                 if ".git/" not in q.as_posix() and "node_modules" not in q.as_posix()]
    tail = "/" + path.strip("/")
    for q in _TREE:
        if q.endswith(tail) or q == path.strip("/"):
            if not want_dir or (ROOT / q).is_dir():
                return True
    return False


def _tiers() -> "set[str]":
    """The visibility tiers the schema actually defines."""
    m = re.search(r"^visibility:\s*([a-z |]+)", (ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
                  re.M)
    if not m:
        return set()
    return {t.strip() for t in m.group(1).split("|") if t.strip()}


def _skills() -> "set[str]":
    d = ROOT / ".claude" / "skills"
    return {p.name for p in d.iterdir() if (p / "SKILL.md").exists()} if d.is_dir() else set()


def _crons() -> int:
    wf = ROOT / ".github" / "workflows"
    if not wf.is_dir():
        return 0
    return sum(1 for f in wf.glob("*.yml")
               if re.search(r"^\s*schedule:", f.read_text(encoding="utf-8"), re.M))


def _max_axiom() -> "int | None":
    f = ROOT / "wiki" / "axioms.md"
    if not f.exists():
        return None
    ids = [int(m) for m in re.findall(r"\bA(\d+)\b", f.read_text(encoding="utf-8"))]
    return max(ids) if ids else None


#: "`wiki/boundary-review-external-readers.md` in indy-llm-wiki" — a deliberate pointer at
#: another repository in the federation, not a broken local reference.
ELSEWHERE = re.compile(r"\bin\s+[a-z0-9-]+-wiki\b", re.I)


def _elsewhere(path: str, text: str) -> bool:
    """True when the sentence naming this path says it lives in another wiki."""
    for line in text.splitlines():
        if f"`{path}`" in line and ELSEWHERE.search(line):
            return True
    return False


def check_doc(name: str, text: str, tiers, skills, crons, max_axiom):
    """Every problem found in one document, as (claim, what is actually true)."""
    out = []

    # 1. A document that ENUMERATES the tiers must enumerate all of them — the original
    #    defect was ONBOARDING.md naming three of four and omitting `internal`, which covers
    #    328 pages. The threshold is three, not two, because a commons legitimately discusses
    #    `internal` against `private` in prose without listing the set: firing there taught
    #    nothing and would have had a correct document edited to satisfy the check, which is
    #    how a check earns its way into being switched off.
    named = {t for t in tiers if re.search(rf"`{t}`", text)}
    if len(named) >= len(tiers) - 1 and named != tiers:
        missing = ", ".join(sorted(tiers - named))
        out.append((f"lists visibility tiers but omits: {missing}",
                    f"the schema defines {len(tiers)}: {', '.join(sorted(tiers))}"))

    # 2. Backticked paths must exist. This is what catches a renamed tool or a moved page
    #    long after the person who moved it has forgotten the doc mentioned it. Docs name
    #    things the way people say them — `axioms.md`, `challenges/` — so a name is resolved
    #    anywhere in the tree, not only from the root. Otherwise the check drowns its real
    #    findings in noise and gets switched off, which is the usual way a check dies.
    for path in sorted(set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|py|css|json|yml))`", text))):
        if PLACEHOLDER.search(path) or _elsewhere(path, text):
            continue
        if not _resolves(path):
            out.append((f"mentions `{path}`", "no file of that name anywhere in the repo"))
    for folder in sorted(set(re.findall(r"`([A-Za-z0-9_./-]+/)`", text))):
        if PLACEHOLDER.search(folder) or _resolves(folder.rstrip("/"), want_dir=True):
            continue
        out.append((f"mentions `{folder}`", "no folder of that name anywhere in the repo"))

    # 3. A named skill must exist. Only where the sentence says "skill", so that an
    #    emphasised ordinary word is not mistaken for one.
    named_skills = set(re.findall(r"`([a-z][a-z-]+)`\s+skill", text))
    named_skills |= set(re.findall(r"skill\s+`([a-z][a-z-]+)`", text))
    for skill in sorted(named_skills - skills):
        out.append((f"names the `{skill}` skill", "no such skill in .claude/skills/"))

    # 4. A promise that something happens automatically on a schedule, in a repo with no
    #    scheduled workflow left, is the defect that shipped this morning.
    for line in text.splitlines():
        if SCHEDULE.search(line) and AUTOMATIC.search(line) and crons == 0:
            out.append((f"promises something scheduled: {line.strip()[:70]}",
                        "no workflow in this repo has a schedule"))
            break

    # 5. An axiom range must match the register.
    m = re.search(r"\bA0\s*[-–—]\s*A(\d+)\b", text)
    if m and max_axiom is not None and int(m.group(1)) != max_axiom:
        out.append((f"says axioms run A0-A{m.group(1)}",
                    f"the register reaches A{max_axiom}"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check the human-facing docs against the repo.")
    ap.add_argument("--check", action="store_true", help="exit non-zero on any drift")
    a = ap.parse_args(argv)

    tiers, skills, crons, max_axiom = _tiers(), _skills(), _crons(), _max_axiom()
    problems, looked = {}, []
    for name in DOCS:
        f = ROOT / name
        if not f.exists():
            continue
        looked.append(name)
        found = check_doc(name, f.read_text(encoding="utf-8"), tiers, skills, crons, max_axiom)
        if found:
            problems[name] = found

    total = sum(len(v) for v in problems.values())
    if not problems:
        print(f"onboarding docs OK — {len(looked)} document(s) checked against "
              f"{len(tiers)} tier(s), {len(skills)} skill(s), {crons} scheduled workflow(s)")
        return 0

    print(f"onboarding docs — {total} claim(s) that the repo does not support\n")
    for name, found in problems.items():
        print(f"  {name}")
        for claim, truth in found:
            print(f"     {claim}")
            print(f"       -> {truth}")
        print()
    print("  These are facts, not style. The docs are the first thing a new person reads,")
    print("  and a wrong one teaches a wrong model of the system on day one.")
    return 1 if a.check else 0


if __name__ == "__main__":
    sys.exit(main())
