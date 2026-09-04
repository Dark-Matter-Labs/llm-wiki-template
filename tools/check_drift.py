#!/usr/bin/env python3
"""
check_drift.py — a file that lives in more than one wiki should not disagree with itself.

## Why this exists

Three defects in three days, each the same shape:

  * 2026-09-02  `export_shared.py` sat outside the synced layer, held there by ONE hardcoded
                proper noun. fang-llm-wiki's colleague mirror had been failing since the repo
                was created and nobody could see it.
  * 2026-09-03  The `_parse_value` bracket-list fix existed in one repo of ten.
  * 2026-09-04  `.claude/skills/` had never been synced at all, so two method skills that
                describe themselves as firing automatically on any repo were present on one.

They looked like three incidents. A scan showed **thirty-three** files present in two or more
wikis, outside `SHARED`, with contents that disagree — `reflect/SKILL.md` in seven versions across
ten repos, `lint` in six. Three samples from a population, not three events.

`sync_design_system.py` answers "is what SHOULD travel in step?" Nothing answered "is anything
travelling that nobody declared?" This does.

## Why some disagreement is correct

`design/federation.json` has ten versions across ten repos because it is *supposed* to: a wiki's
position in the graph does not travel. So the output is a **debt register**, `drift-baseline.json`,
in the same shape as `links-baseline.json` — it may only shrink, and `--check` fails on anything
new. Recording a file as expected-to-differ is a claim someone makes on purpose, not a silence.

## Why this is NOT in CI

It compares sibling checkouts, and CI checks out one repo. Wiring it into a workflow would produce
a step that passes because it found nothing to compare — a gate that cannot fail, which this repo
has now been bitten by twice (a `ls | head` that killed a workflow, a `grep` for a success string
that hid a failure). It runs locally, next to `sync_design_system.py`, which is also local-only and
for the same reason.

Usage:
  python3 tools/check_drift.py                  # the reading
  python3 tools/check_drift.py --check          # exit 1 on drift not in the baseline
  python3 tools/check_drift.py --report         # every offender, with the version count
  python3 tools/check_drift.py --update-baseline
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "design" / "shared-layer.json"


def _layer():
    """(siblings, shared) — from the manifest, which travels; never from the syncer, which does not.

    First version of this file imported sync_design_system directly. That module lives only in the
    source repo by design — a spoke running it would try to push its own files onto its siblings —
    so the import made this tool crash on nine of the ten wikis it had just been synced to. Shipped
    a gate that could not run, which is the very defect it exists to catch.
    """
    import json
    if MANIFEST.exists():
        d = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return list(d.get("siblings", [])), set(d.get("shared", [])) | {d.get("generated")}
    try:                                    # source repo, manifest not yet written
        sys.path.insert(0, str(ROOT / "tools"))
        import sync_design_system as sync
        return list(sync.SIBLINGS), set(sync.SHARED) | {sync.GENERATED}
    except ImportError:
        return [], set()
BASELINE = ROOT / "tools" / "drift-baseline.json"

# Where shared machinery actually lives. Deliberately not the whole tree: wiki/ content is
# SUPPOSED to differ, and comparing it would bury the signal under the corpus.
SCAN_DIRS = ("tools", ".claude/skills", "design", ".github/workflows")
SCAN_SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml"}
SKIP_PARTS = {"worktrees", "__pycache__", "node_modules"}
# Generated or per-repo registers: their contents are a function of the repo, so "differs"
# is the correct state and flagging it would train people to ignore the output.
SKIP_NAMES = {"links-baseline.json", "sources-baseline.json", "drift-baseline.json",
              ".staleness-cache.json"}


def _repos() -> "list[pathlib.Path]":
    here = ROOT
    out = [here]
    for name in _layer()[0]:
        p = here.parent / name
        if p.is_dir():
            out.append(p)
    return out


def _files(repo: pathlib.Path) -> "dict[str, str]":
    found = {}
    for sub in SCAN_DIRS:
        base = repo / sub
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if not f.is_file() or f.suffix not in SCAN_SUFFIXES:
                continue
            if f.name in SKIP_NAMES or SKIP_PARTS & set(f.parts):
                continue
            found[f.relative_to(repo).as_posix()] = hashlib.md5(f.read_bytes()).hexdigest()
    return found


def audit() -> "tuple[list[dict], int, int]":
    repos = _repos()
    shared = _layer()[1]
    seen: "dict[str, dict[str, str]]" = collections.defaultdict(dict)
    for r in repos:
        for rel, digest in _files(r).items():
            seen[rel][r.name] = digest

    drift = []
    multi = 0
    for rel, per_repo in seen.items():
        if len(per_repo) < 2:
            continue
        multi += 1
        if rel in shared:
            continue                      # sync_design_system.py owns this one
        versions = len(set(per_repo.values()))
        if versions > 1:
            drift.append({"path": rel, "repos": len(per_repo), "versions": versions})
    drift.sort(key=lambda d: (-d["versions"], d["path"]))
    return drift, len(repos), multi


def load_baseline() -> set:
    return set(load_reasons())


def load_reasons() -> "dict[str, str]":
    """path -> why it is still drifting.

    A register of thirty-six paths with no reasons is a list, and a list gets skimmed. The
    triage on 2026-09-04 found only three of them were cosmetic; the rest need someone to pick
    a variant or merge two, and at least twice the SPOKE's version was the better one. That is
    not something a count can carry, so each entry carries a sentence and regeneration
    preserves it.
    """
    if not BASELINE.exists():
        return {}
    d = json.loads(BASELINE.read_text(encoding="utf-8"))
    return {e["path"]: e.get("reason", "") for e in d.get("drifted", [])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="A file in two wikis should not disagree with itself.")
    ap.add_argument("--check", action="store_true", help="exit 1 on drift not in the baseline")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args(argv)

    drift, n_repos, multi = audit()

    if n_repos < 2:
        print("drift check — only this repo is checked out, so nothing can be compared.\n"
              "  This tool needs the sibling wikis beside it, the same as sync_design_system.py.\n"
              "  Reporting that plainly rather than exiting 0 as though it had checked.")
        return 0

    baseline = load_baseline()
    new = [d for d in drift if d["path"] not in baseline]
    print(f"drift — {n_repos} wikis, {multi} file(s) shared between two or more, "
          f"{len(drift)} disagreeing")

    if args.update_baseline:
        reasons = load_reasons()          # never lose a sentence someone wrote
        BASELINE.write_text(json.dumps({
            "_comment": "Files present in two or more wikis, outside SHARED, whose contents "
                        "disagree. A debt register, not an exemption: it must only ever shrink. "
                        "Some entries are CORRECT and permanent -- design/federation.json is "
                        "per-repo by design -- but recording that is a claim someone makes on "
                        "purpose. --check fails on anything not listed.",
            "recorded": "2026-09-04",
            "drifted": [{"path": d["path"], "repos": d["repos"], "versions": d["versions"],
                         "reason": reasons.get(d["path"], "")}
                        for d in sorted(drift, key=lambda x: x["path"])],
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nbaseline written: {len(drift)} path(s).")
        return 0

    if args.report and drift:
        print("\nDISAGREEING, worst first:")
        for d in drift:
            mark = "  " if d["path"] in baseline else " *"
            print(f"{mark} {d['versions']:>2} versions across {d['repos']:>2} repos   {d['path']}")
        print("\n  * = not in the baseline")

    if args.check:
        if new:
            print(f"\nFAIL — {len(new)} file(s) disagree and are not in the baseline:")
            for d in new:
                print(f"  {d['versions']} versions across {d['repos']} repos   {d['path']}")
            print("\nEither add it to SHARED in sync_design_system.py so it travels, or record it "
                  "in the baseline as deliberately per-repo. Silence is the one option that is "
                  "not available.")
            return 1
        print(f"\ndrift OK — no new disagreement. Baseline debt: {len(baseline)} path(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
