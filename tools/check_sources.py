#!/usr/bin/env python3
"""
check_sources.py — a page's `sources:` must point at a file that exists.

## Why this exists

`CLAUDE.md` carries the rule the whole wiki rests on: **never invent sources or citations.** It
was checked by nobody. On 2026-08-27, while assembling a cross-check packet for a page 139 others
depend on, one of its six cited sources turned out not to be in `raw/`. A scan found the pattern:

    85 frontmatter citations, across 31 distinct files, that do not resolve against the
    source library on this machine.

**A correction to the first version of this docstring, which mattered.** It said those files
"have never existed in this repository — zero commits, in any branch, ever." That reading was
wrong. `.gitignore` excludes `raw/**/*.pdf`, `*.png`, `*.html`, `*.docx` and more by design —
*"Source documents stay local, not versioned (size / licensing). The wiki cites them by filename
but the originals are not pushed."* A gitignored file has zero commits whether or not it exists.
550 files sit in `raw/` here; 337 are tracked.

So what this tool can honestly say is narrower and still worth saying: **these citations do not
resolve against the source library on the machine it runs on.** Some will be missing only here —
the curator's copy is the authoritative one. Others will be genuinely unresolvable anywhere, and
those are the ones that matter, because an uncheckable citation is worse than an absent one: it
looks like evidence.

## Why this is NOT a CI gate

It was one, for about ten minutes, and CI failed immediately with a list of 200+ perfectly good
citations. **CI checks out 337 of 550 source files by design, so it can never answer this
question** — every citation to a PDF looks broken there. A gate that cannot distinguish a real
defect from its own missing inputs is worse than no gate.

It belongs where someone with the full source library runs it: the `lint` pass.

## What it checks, and what it deliberately does not

**Frontmatter `sources:` only.** That list is a bracketed, comma-separated field with no
newline-wrapping anywhere in the corpus, so it parses unambiguously.

Inline `(raw/…)` citations are **not** gated, and that is a deliberate limit rather than an
oversight. Filenames in this corpus contain parentheses (`… (WIP).pdf`, `… (4 Jan 2026).pdf`) and
some citations wrap across a newline, so a naive `\\(raw/[^)]+\\)` scan mis-parses a real fraction
of them. A gate that reports its own parser bugs as corpus defects is a gate people learn to
ignore — the specific failure this file exists to end. `--report` shows an inline estimate,
labelled as an estimate.

## The baseline

Failing on the 31 that already do not resolve would block every future change on unrelated
history, so they are recorded in `tools/sources-baseline.json`. **The check fails on anything
NEW.** The baseline is a debt register, not an exemption: it should only ever shrink, and
`--check` prints the outstanding count every run so it cannot quietly become permanent.

## In every wiki, from 2026-10-12

It began in indy-llm-wiki, and the figures above are that wiki's. On 2026-10-12 it joined the shared
layer, so every wiki's lint pass runs it, each against its own `tools/sources-baseline.json`. A
commons will show many absent files: its pages were contributed with citations to the contributing
wiki's `raw/`, which the commons never held. That is expected, and the baseline records it.

Usage:
  python3 tools/check_sources.py             # the reading
  python3 tools/check_sources.py --check     # exit 1 on any NEW unresolvable source (local lint)
  python3 tools/check_sources.py --report    # every offender, plus the inline estimate
  python3 tools/check_sources.py --update-baseline
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
BASELINE = ROOT / "tools" / "sources-baseline.json"

SKIP_DIRS = {"index", "log"}
SKIP_FILES = {"index.md", "log.md"}


def pages():
    for p in sorted(WIKI.rglob("*.md")):
        if p.name in SKIP_FILES or p.parent.name in SKIP_DIRS:
            continue
        yield p


def by_basename() -> "dict[str, list[str]]":
    out = collections.defaultdict(list)
    if RAW.is_dir():
        for f in RAW.rglob("*"):
            if f.is_file():
                out[f.name].append(f.relative_to(ROOT).as_posix())
    return out


ITEM = re.compile(r'"([^"]*)"|\'([^\']*)\'|([^,\s][^,]*)')


def declared_sources(text: str) -> "list[str]":
    """The raw/ paths in the frontmatter's `sources:`, as a one-line list or a block list.

    Fixed 2026-10-12, when this went to every wiki: a block list was skipped entirely, and a
    quoted filename with a comma in it was split in two. Only the frontmatter is read, so a
    `sources:` line in a page's body is not mistaken for one.
    """
    fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not fm:
        return []
    head = fm.group(1)
    inline = re.search(r"^sources:\s*\[(.*?)\]\s*$", head, re.M | re.S)
    if inline:
        items = [next(g for g in m.groups() if g is not None).strip() for m in ITEM.finditer(inline.group(1))]
    else:
        block = re.search(r"^sources:\s*\n((?:[ \t]*-[^\n]*\n?)+)", head, re.M)
        items = [line.strip()[1:].strip().strip('"').strip("'") for line in block.group(1).splitlines()] if block else []
    return [s for s in items if s.startswith("raw/")]


def same_path(path: str) -> str:
    """A path as a reader sees it: any kind of space is a space, and an accented letter has one spelling.

    Added 2026-10-12. A folder in indy-llm-wiki's raw/ has a non-breaking space after a dash, and
    five pages cite it with an ordinary one. The citations were right; the folder name carries an
    invisible quirk, and raw/ is never renamed. Asking pages to copy an invisible character would
    make them worse, so the comparison ignores it instead.
    """
    return re.sub(r"[  -​  　]", " ", unicodedata.normalize("NFC", path))


def raw_paths() -> "set[str]":
    return {same_path(f.relative_to(ROOT).as_posix()) for f in RAW.rglob("*") if f.is_file()} if RAW.is_dir() else set()


def audit() -> dict:
    """Every declared source, classified. `drift` is mechanically fixable; `absent` is not."""
    base = by_basename()
    present = raw_paths()
    ok, drift, absent = 0, [], []
    for p in pages():
        rel = p.relative_to(ROOT).as_posix()
        for s in declared_sources(p.read_text(encoding="utf-8")):
            if (ROOT / s).exists() or same_path(s) in present:
                ok += 1
            elif base.get(s.split("/")[-1]):
                drift.append({"page": rel, "cited": s, "found_at": base[s.split("/")[-1]][0]})
            else:
                absent.append({"page": rel, "cited": s})
    return {"ok": ok, "drift": drift, "absent": absent}


def inline_estimate() -> dict:
    """An ESTIMATE. See the module docstring for why this is not gated."""
    base = by_basename()
    total = miss = 0
    for p in pages():
        t = p.read_text(encoding="utf-8")
        t = t.split("---", 2)[2] if t.startswith("---") else t
        for chunk in re.findall(r"\(raw/(?:[^()]|\([^()]*\))*\)", t):
            for s in re.split(r"[;,]", chunk.strip("()")):
                s = " ".join(s.split())
                if not s.startswith("raw/"):
                    continue
                total += 1
                if not (ROOT / s).exists() and not base.get(s.split("/")[-1]):
                    miss += 1
    return {"total": total, "unresolved": miss}


def load_baseline() -> set:
    if not BASELINE.exists():
        return set()
    return set(json.loads(BASELINE.read_text(encoding="utf-8")).get("absent", []))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Declared sources must exist.")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on a NEW unresolvable source. Run locally, never in CI: "
                         "source files such as PDFs are not stored in the wiki, so CI never has them all.")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args(argv)

    r = audit()
    absent_files = sorted({a["cited"] for a in r["absent"]})
    drift_files = sorted({d["cited"] for d in r["drift"]})
    baseline = load_baseline()
    new = [f for f in absent_files if f not in baseline]

    total = r["ok"] + len(r["drift"]) + len(r["absent"])
    print(f"declared sources — {total} citation(s): {r['ok']} resolve, "
          f"{len(r['drift'])} path-drift, {len(r['absent'])} absent "
          f"({len(absent_files)} distinct file(s))")

    if args.update_baseline:
        BASELINE.write_text(json.dumps(
            {"_comment": "Sources cited in frontmatter that do not resolve against the local "
                         "raw/ library. Some may exist only on the curator's machine — raw/ "
                         "binaries are gitignored by design. A debt register, not an exemption: "
                         "it must only ever shrink. --check fails on anything not listed here.",
             "recorded": __import__("datetime").date.today().isoformat(),
             "absent": absent_files}, indent=2) + "\n", encoding="utf-8")
        print(f"\nbaseline written: {len(absent_files)} distinct file(s)")
        return 0

    if args.report:
        if drift_files:
            print(f"\nPATH DRIFT ({len(r['drift'])} citation(s)) — the file exists, "
                  f"the path is wrong. Mechanically fixable:")
            for d in r["drift"][:20]:
                print(f"  {d['page']}\n     cited {d['cited']}\n     found {d['found_at']}")
        if absent_files:
            print(f"\nABSENT ({len(r['absent'])} citation(s), {len(absent_files)} file(s)) — "
                  f"not in raw/ on this machine:")
            per = collections.Counter(a["cited"] for a in r["absent"])
            for f, n in per.most_common():
                print(f"  {n:>3} page(s)  {f}")
        e = inline_estimate()
        print(f"\ninline (raw/…) citations — ESTIMATE only, not gated: "
              f"{e['unresolved']} of {e['total']} do not resolve.")
        print("  Not gated because filenames here contain parentheses and some citations wrap")
        print("  across a newline, so this scan mis-parses a real fraction of them.")

    if args.check:
        if new:
            print(f"\nFAIL — {len(new)} source(s) cited that do not exist and are not in the "
                  f"baseline:")
            for f in new:
                for a in r["absent"]:
                    if a["cited"] == f:
                        print(f"  {a['page']}  ->  {f}")
                        break
            print("\nEither add the file to raw/, correct the path, or — if the claim has no "
                  "source — say so on the page instead of citing one.")
            return 1
        print(f"\nsources OK — no new unresolvable citation. "
              f"Baseline debt: {len(baseline)} file(s) still missing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
