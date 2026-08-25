#!/usr/bin/env python3
"""
cross_check.py — the record, and the guard, for having a second model check a page.

## Why a second model is worth something, and what it is not worth

Asking a different frontier model to read a page and say whether it agrees is a real
signal: two models trained differently, prompted separately, disagreeing about what a
source supports is evidence that the page is shakier than it looks. That is worth
recording, and this file gives it somewhere to live.

It is **not** validation. The `validation` ladder in CLAUDE.md records *who has stood
behind a page* — machine / self / peer / collective — and it is load-bearing: pages that
nobody has confirmed are admitted and indexed but do not move the corpus's centre of
gravity. That protection only means anything if the rungs above `machine` require a
person. A second model is not a second person. It has no stake in being wrong, cannot be
asked what it meant six months later, and — most importantly — agreement between two
models is not independent in the way agreement between two people is: they are trained on
overlapping corpora and fail in correlated ways.

So the rule this file enforces is blunt:

    A machine check may move `confidence`. It may never move `validation`.

`confidence` is a claim about how well-supported a page is — exactly the thing a second
reader can speak to. `validation` is a claim about human endorsement, and no amount of
machine agreement produces one.

## The record

A checked page carries:

    machine_checks:
      - model: gpt-5.2
        date: 2026-08-25
        verdict: agrees | disputes | unsure
        note: one line on what it said

`disputes` is a **declaration, not a resolution** — the same shape as `contradicts:`. It
stands, visible, until a person decides. A model may add the entry and may lower
`confidence`; it may not delete a dispute it disagrees with.

## What is checked here

1. Every `machine_checks` entry is well-formed (model, date, verdict from the vocabulary).
2. `validated_by` never names a model. This is the guard that matters: the moment a second
   model is in the loop, the cheap shortcut is `validation: peer` with `validated_by:
   [gpt-5]`, and that single line would quietly convert the whole gravity protection into
   decoration.
3. A page with a `disputes` entry does not claim `confidence: high`.

Usage:
  python3 tools/cross_check.py            # report the state of machine checking
  python3 tools/cross_check.py --check    # exit 1 on any violation (CI)
  python3 tools/cross_check.py --due      # pages where a second read would be worth most
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
EXPORT = ROOT / "export" / "wiki.json"

SKIP_DIRS = {"index", "log"}
SKIP_FILES = {"index.md", "log.md"}

VERDICTS = {"agrees", "disputes", "unsure"}

# Anything that looks like a model rather than a person. Substring match, lowercased —
# deliberately broad, because a false positive here costs one rename and a false negative
# costs the meaning of the whole validation ladder.
MODEL_MARKERS = (
    "gpt", "claude", "gemini", "llama", "mistral", "grok", "deepseek", "qwen",
    "opus", "sonnet", "haiku", "o1", "o3", "o4", "model", "llm", "ai",
)


def pages():
    for p in sorted(WIKI.rglob("*.md")):
        if p.name in SKIP_FILES or p.parent.name in SKIP_DIRS:
            continue
        yield p


def frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def parse_checks(fm: str) -> "list[dict]":
    """The machine_checks block, parsed without a YAML dependency.

    The wiki has no yaml module guaranteed available in CI, and every other tool here
    parses frontmatter with regexes for the same reason. The shape is fixed and small.
    """
    m = re.search(r"^machine_checks:\s*$", fm, re.M)
    if not m:
        return []
    out, cur = [], None
    for line in fm[m.end():].split("\n"):
        if line and not line.startswith((" ", "\t", "-")):
            break                                   # next top-level key
        item = re.match(r"\s*-\s*(\w+):\s*(.*)$", line)
        if item:
            if cur:
                out.append(cur)
            cur = {item.group(1): item.group(2).strip().strip('"')}
            continue
        kv = re.match(r"\s+(\w+):\s*(.*)$", line)
        if kv and cur is not None:
            cur[kv.group(1)] = kv.group(2).strip().strip('"')
    if cur:
        out.append(cur)
    return out


def field(fm: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+?)\s*$", fm, re.M)
    return m.group(1).strip().strip('"') if m else ""


def looks_like_a_model(name: str) -> bool:
    n = name.lower()
    return any(re.search(rf"(?:^|[^a-z]){re.escape(mk)}(?:[^a-z]|$)", n) for mk in MODEL_MARKERS)


def audit() -> "tuple[list[str], dict]":
    problems, stats = [], {"checked": 0, "checks": 0, "disputed": 0, "pages": 0}
    for p in pages():
        rel = p.relative_to(ROOT).as_posix()
        fm = frontmatter(p.read_text(encoding="utf-8"))
        if not fm:
            continue
        stats["pages"] += 1

        # 2. The guard that matters.
        vb = field(fm, "validated_by")
        for name in [n.strip(" []'\"") for n in vb.split(",") if n.strip(" []'\"")]:
            if looks_like_a_model(name):
                problems.append(
                    f"{rel}: validated_by names {name!r}, which looks like a model. "
                    f"A machine check records itself in machine_checks and may move "
                    f"confidence; validation requires a person.")

        checks = parse_checks(fm)
        if not checks:
            continue
        stats["checked"] += 1
        stats["checks"] += len(checks)

        for i, c in enumerate(checks, 1):
            # 1. Well-formed.
            for req in ("model", "date", "verdict"):
                if not c.get(req):
                    problems.append(f"{rel}: machine_checks[{i}] has no {req}")
            v = c.get("verdict", "")
            if v and v not in VERDICTS:
                problems.append(
                    f"{rel}: machine_checks[{i}] verdict {v!r} is not one of "
                    f"{sorted(VERDICTS)}")
            d = c.get("date", "")
            if d and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
                problems.append(f"{rel}: machine_checks[{i}] date {d!r} is not YYYY-MM-DD")

        if any(c.get("verdict") == "disputes" for c in checks):
            stats["disputed"] += 1
            # 3. A live dispute and a high-confidence claim cannot both stand.
            if field(fm, "confidence") == "high":
                problems.append(
                    f"{rel}: claims confidence: high while a machine check disputes it. "
                    f"Lower the confidence or resolve the dispute.")
    return problems, stats


def due(limit: int = 15) -> "list[tuple[int, str, str]]":
    """Pages where a second read would buy the most: load-bearing but weakly supported.

    Load-bearing is measured by inbound links, because a page many others depend on is
    where a wrong claim propagates. Weakly supported is `confidence` below high with no
    check on record. Nothing here is a judgement about the page — it is a queue.
    """
    if not EXPORT.exists():
        return []
    raw = json.loads(EXPORT.read_text(encoding="utf-8")).get("nodes", [])
    nodes = {n.get("slug"): n for n in raw} if isinstance(raw, list) else raw
    out = []
    for p in pages():
        fm = frontmatter(p.read_text(encoding="utf-8"))
        if not fm or parse_checks(fm):
            continue
        if field(fm, "confidence") not in ("low", "medium"):
            continue
        slug = p.relative_to(WIKI).as_posix()[:-3]
        n = nodes.get(slug) or {}
        inbound = len(n.get("inbound_links", []))
        if inbound:
            out.append((inbound, field(fm, "confidence"), field(fm, "title") or slug))
    return sorted(out, reverse=True)[:limit]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Record and guard machine cross-checks.")
    ap.add_argument("--check", action="store_true", help="exit 1 on any violation (CI)")
    ap.add_argument("--due", action="store_true", help="pages where a second read is worth most")
    args = ap.parse_args(argv)

    problems, stats = audit()

    print(f"machine checks — {stats['checks']} check(s) recorded on {stats['checked']} "
          f"of {stats['pages']} page(s); {stats['disputed']} page(s) disputed")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for pr in problems:
            print(f"  - {pr}")
    elif args.check:
        print("\ncross-check OK — no model is standing in for a person.")

    if args.due:
        rows = due()
        if rows:
            print("\nmost worth a second read (load-bearing, weakly supported, unchecked):")
            for inbound, conf, title in rows:
                print(f"  {inbound:>3} inbound  {conf:<6}  {title}")
        else:
            print("\nnothing queued — every load-bearing weak page has a check, "
                  "or export/wiki.json has not been built.")

    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())
