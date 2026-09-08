#!/usr/bin/env python3
"""
check_skill_links.py — a skill in the shared layer may not link a page.

## The failure this closes

`check_links.py` scans `wiki/` and nothing else, so `.claude/skills/` is ungated. On 2026-09-08
the `notion-sync` skill was added to the shared layer carrying three wiki-links, two of them to
pages that are `private` in the wiki that authored it. Syncing it would have shipped those links
to ten repositories, where they would have resolved to nothing — and carried a private page's
title into every sibling, which is exactly what `contribute.py` redacts when a page travels.

It was caught by reading the file before pushing it. That is not a control.

## The rule, and why it is shaped this way

**A skill in the shared layer may not carry a wiki-link that resolves to a page here.**

The shared layer is copied verbatim into eleven repositories whose page sets differ — the Axioms
Register is not in `xco-team-wiki` at all, and no sibling has another's private pages. So a
*resolving* link is the dangerous one: it looks correct to its author, and breaks or leaks
everywhere else. Describe the page instead, the way a shared file has to.

The inverse is deliberately allowed. `[[link]]`, `[[Account]]`, `[[Page or Axiom]]` and
`[[wiki-links]]` resolve to nothing because they are **syntax examples** — a skill documenting
the link format, not referencing a page. Gating those would flag fourteen strings that mean
nothing and teach everyone to ignore the gate. Measured before the rule was chosen: of eighteen
wiki-links across nine skills, fourteen were placeholders.

Local skills are not gated. A skill that never leaves this repo may link whatever resolves in it,
private pages included — that is what `crm` and `luck` correctly do.

Usage:
  python3 tools/check_skill_links.py            # report
  python3 tools/check_skill_links.py --check    # exit 1 if a shared skill links a page
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
WIKI = ROOT / "wiki"
MANIFEST = ROOT / "design" / "shared-layer.json"

LINK = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")


def shared_paths() -> "set[str] | None":
    """What the syncer will copy, or None when the manifest cannot be read.

    Read from the manifest, not from the syncer — same reasoning as check_drift.py: the manifest
    is data and travels; the syncer does not, because a spoke running it would push its own files
    onto its siblings.

    None and the empty set are DIFFERENT and were not, which made the gate unable to fire. An
    unreadable manifest returned an empty set, `if not shared` sent main() down the "nothing to
    check" path, and the check passed — so a malformed manifest disabled the gate silently. Found
    by mutation testing: deleting the shared-only filter did not fail a single test, because the
    test that should have caught it was exiting early for this reason instead.
    """
    try:
        return set(json.loads(MANIFEST.read_text(encoding="utf-8"))["shared"])
    except (OSError, ValueError, KeyError):
        return None


def page_titles() -> dict[str, str]:
    """title -> visibility, for every page in this wiki."""
    out: dict[str, str] = {}
    if not WIKI.is_dir():
        return out
    for p in WIKI.rglob("*.md"):
        text = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.M)
        if not m:
            continue
        v = re.search(r"^visibility:\s*(\w+)", text, re.M)
        out[m.group(1)] = v.group(1) if v else "unset"
    return out


def audit() -> list[tuple[str, str, str]]:
    """(skill path, linked title, target visibility) for every offending link."""
    shared, titles, out = shared_paths(), page_titles(), []
    for p in sorted(SKILLS.rglob("SKILL.md")):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in shared:
            continue
        for title in LINK.findall(p.read_text(encoding="utf-8", errors="replace")):
            if title in titles:
                out.append((rel, title, titles[title]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Shared skills may not link pages.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    shared = shared_paths()
    if shared is None:
        print("no readable shared-layer manifest — cannot tell which skills travel.",
              file=sys.stderr)
        return 1 if args.check else 0

    n_shared = sum(1 for p in SKILLS.rglob("SKILL.md")
                   if p.relative_to(ROOT).as_posix() in shared)
    problems = audit()

    if not problems:
        print(f"skill links OK — {n_shared} shared skill(s) carry no page references.")
        return 0

    print(f"{len(problems)} page reference(s) in shared skill(s):\n", file=sys.stderr)
    for rel, title, vis in problems:
        sting = "  ← PRIVATE: its title would travel too" if vis == "private" else ""
        print(f"  {rel}\n      [[{title}]]  ({vis}){sting}", file=sys.stderr)
    print(
        "\nA shared skill is copied verbatim into every wiki, and their page sets differ — so a\n"
        "link that resolves here resolves nowhere else, or carries a title that should not leave.\n"
        "Describe the page instead of linking it. Placeholders like [[Page Title]] are fine:\n"
        "they resolve to nothing and are documenting the syntax.",
        file=sys.stderr,
    )
    return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
