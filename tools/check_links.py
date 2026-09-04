#!/usr/bin/env python3
"""
check_links.py — every `[[wiki-link]]` must resolve to a page that exists.

## Why this exists

`CLAUDE.md` warns twice about the two ways a link silently dies, on the assumption that something
is watching. Nothing was. On 2026-08-31 a link written as `[[xCO Capital Formation Architecture]]`
— the page is `The xCO Capital-Formation Architecture` — passed every gate in CI. Inserting a
deliberately nonexistent target and re-running produced *"schema check OK — 778 pages valid."*

The CI step was called **"Schema + link integrity"** and did not check link integrity. It checked
one link failure mode — a link wrapped across a newline — and not the ordinary one.

## In a shared repo, an unresolved link may be a boundary leak

Found on 2026-09-04, clearing the last of the baseline: six rows in `xco-team-wiki` were links to
pages that are `visibility: private` in the wiki they came from. `contribute.py` redacts those, but
that overview page was hand-authored directly in the commons on 2026-08-05 and never went through
the contribute route -- so nothing redacted anything.

This checker was the only thing that noticed, and its finding sat in the baseline for four weeks
labelled as known debt. **Baselining a dead link can baseline a boundary leak.** A wiki-link that
does not resolve locally in a commons is not automatically a typo; before baselining one, check
whether the target is a page somebody deliberately kept private. The prose can stay either way --
it is the graph edge that must not exist.

The reason it stayed invisible is in `export.py`:

    n["outbound_links"] = [s for s in n["outbound_links"] if s in present]

The exporter **drops unresolvable edges** while building the graph. That is right for the export
artifact — a graph should not carry dangling edges — but it means a broken link produces a clean
export, a passing gate, and one fewer edge than the author intended. The page still renders; the
connection is just gone.

## Agreeing with the exporter, rather than guessing

This reuses `export.WIKILINK_RE`, `export._norm_title` and `export.build_nodes` rather than
reimplementing them. That is deliberate: the question worth answering is not "does this look like a
link" but **"would this edge survive the export?"** — and only the exporter's own parsing can
answer it. A checker with its own regex would disagree at the edges and produce exactly the false
positives that teach people to ignore a gate.

It inherits both fixes recorded in `CLAUDE.md` for free: links wrapped across a newline, and
aliased links inside a markdown table where the `|` is escaped as `\\|`.

## Code spans are not links

A wiki-link inside backticks is being *shown*, not made — prose about the link syntax, of which
this corpus has plenty (`[[links]]`, `[[wiki-link]]`, `[[xCO:Page Title]]`). Thirteen of the
twenty-eight unresolved targets in the first scan were that. Fenced blocks and inline code spans
are stripped before scanning, so documentation about wiki-links does not read as broken
wiki-links.

## The baseline

The genuinely broken remainder is recorded in `tools/links-baseline.json`, and **the check fails on
anything new**. Same shape as `check_sources.py`: a debt register, not an exemption. It should only
shrink, and every run prints how much is left so it cannot quietly become permanent.

Fixing the existing ones is editorial — `see [[log]]` could become plain prose or point at a real
page, and that is an author's call, not a script's. So they are reported, never rewritten.

Usage:
  python3 tools/check_links.py             # the reading
  python3 tools/check_links.py --check     # exit 1 on any NEW unresolved link (CI)
  python3 tools/check_links.py --report    # every offender, with its page and context
  python3 tools/check_links.py --update-baseline
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
BASELINE = ROOT / "tools" / "links-baseline.json"

SKIP_DIRS = {"index", "log"}
SKIP_FILES = {"index.md", "log.md"}

FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_code(body: str) -> str:
    """Blank out code, preserving length so offsets stay meaningful for context."""
    body = FENCE.sub(lambda m: " " * len(m.group(0)), body)
    return INLINE_CODE.sub(lambda m: " " * len(m.group(0)), body)


def pages():
    for p in sorted(WIKI.rglob("*.md")):
        if p.name in SKIP_FILES or p.parent.name in SKIP_DIRS:
            continue
        yield p


def audit() -> "tuple[list[dict], int]":
    """Unresolved links, and the total scanned. Resolution is the exporter's own."""
    nodes, _t2s = export.build_nodes(str(WIKI))
    known = {export._norm_title(n["title"]) for n in nodes.values()}

    broken, total = [], 0
    for p in pages():
        text = p.read_text(encoding="utf-8")
        body = text.split("---", 2)[2] if text.startswith("---") else text
        scan = strip_code(body)
        for m in export.WIKILINK_RE.finditer(scan):
            total += 1
            target = export._norm_title(m.group(1))
            if target in known:
                continue
            s = max(0, m.start() - 34)
            broken.append({
                "page": p.relative_to(ROOT).as_posix(),
                "target": target,
                "context": " ".join(body[s:m.end() + 20].split()),
            })
    return broken, total


def load_baseline() -> set:
    if not BASELINE.exists():
        return set()
    d = json.loads(BASELINE.read_text(encoding="utf-8"))
    return {(e["page"], e["target"]) for e in d.get("unresolved", [])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Every wiki-link must resolve.")
    ap.add_argument("--check", action="store_true", help="exit 1 on any NEW unresolved link")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args(argv)

    broken, total = audit()
    baseline = load_baseline()
    new = [b for b in broken if (b["page"], b["target"]) not in baseline]

    print(f"wiki-links — {total} scanned, {len(broken)} unresolved "
          f"({len({b['target'] for b in broken})} distinct target(s))")

    if args.update_baseline:
        BASELINE.write_text(json.dumps({
            "_comment": "Wiki-links whose target page does not exist. A debt register, not an "
                        "exemption: it must only ever shrink. Fixing one is editorial — a dead "
                        "`see [[log]]` might become prose or point at a real page — so they are "
                        "reported here and never rewritten by a script. --check fails on anything "
                        "not listed.",
            "recorded": "2026-08-31",
            "unresolved": [{"page": b["page"], "target": b["target"]} for b in
                           sorted(broken, key=lambda x: (x["page"], x["target"]))],
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pairs = len({(b["page"], b["target"]) for b in broken})
        print(f"\nbaseline written: {len(broken)} unresolved link(s), {pairs} distinct "
              f"page/target pair(s) — the pair is what --check matches on, so a target linked "
              f"twice from one page counts once.")
        return 0

    if args.report and broken:
        per = collections.Counter(b["target"] for b in broken)
        print(f"\nUNRESOLVED, by target:")
        for t, n in per.most_common():
            print(f"  {n:>3}×  [[{t}]]")
        print(f"\nwith context:")
        for b in sorted(broken, key=lambda x: x["page"])[:40]:
            print(f"  {b['page']}\n     …{b['context'][:104]}")

    if args.check:
        if new:
            print(f"\nFAIL — {len(new)} link(s) point at a page that does not exist:")
            for b in new:
                print(f"  {b['page']}  ->  [[{b['target']}]]")
                print(f"     …{b['context'][:96]}")
            print("\nCheck the exact title (they are case- and punctuation-sensitive), or write it "
                  "as prose if no such page is meant to exist.")
            return 1
        print(f"\nlinks OK — no new unresolved link. Baseline debt: {len(baseline)} "
              f"page/target pair(s), {len(broken)} occurrence(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
