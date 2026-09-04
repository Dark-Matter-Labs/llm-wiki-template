#!/usr/bin/env python3
"""
propose_upstream.py — send a local improvement to a shared file back to the source.

## Why this exists

The shared layer has only ever flowed one way. `sync_design_system.py` copies from the source
repo to the siblings, and until today it overwrote whatever it found. So a spoke could improve a
shared tool or skill and have no way to say so — and every sync was a chance to lose it.

That was not hypothetical. On 2026-09-04 a drift scan found **seven of ten generic tools had a
LARGER version somewhere other than the source**, and two of them were clearly better:

  * `michelle-llm-wiki`'s `reflect` skill, two lines longer than the source's.
  * `learning-system-wiki`'s `classify_internal.py`, deliberately de-projectised, with a comment
    explaining why.

A federation in which only one node may teach is not a federation, and a learning system that can
only broadcast does not learn. This is the missing direction.

## What it does, and refuses to do

It **stages a proposal**. It does not push, does not open a PR, and cannot reach the source repo —
the same consent loop as `contribute.py`, for the same reason: the receiving side has to see the
diff and decide, and a tool that can write to nine repositories should not be able to do it alone.

Provenance is stamped, never invented: which wiki, which revision, who. And only files in the
shared layer are eligible — a local tool that was never shared is nobody else's business.

Usage:
  python3 tools/propose_upstream.py                # what could be proposed
  python3 tools/propose_upstream.py --stage --by "Name"
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Derived from ROOT at call time, not at import: the tests set ROOT to a temp wiki, and a
# constant frozen at import would quietly keep pointing at the real one.
def _manifest() -> pathlib.Path:
    return ROOT / "design" / "shared-layer.json"


def _state() -> pathlib.Path:
    return ROOT / "design" / ".sync-state.json"


def _sh(*a):
    return subprocess.run(a, capture_output=True, text=True, cwd=ROOT).stdout.strip()


def _layer() -> "list[str]":
    m = _manifest()
    if not m.exists():
        return []
    try:
        return list(json.loads(m.read_text(encoding="utf-8")).get("shared", []))
    except ValueError:
        return []


def _base() -> "dict[str, str]":
    st = _state()
    if not st.exists():
        return {}
    try:
        return json.loads(st.read_text(encoding="utf-8")).get("written", {})
    except ValueError:
        return {}


def _digest(p: pathlib.Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def changed() -> "list[str]":
    """Shared files this wiki has changed since the last sync wrote them.

    The merge base is what makes this answerable. Without it, 'differs from the source' cannot be
    told apart from 'the source moved on', and every sibling would look like it had opinions.
    """
    base = _base()
    out = []
    for rel in _layer():
        p = ROOT / rel
        if not p.is_file() or rel not in base:
            continue
        if _digest(p) != base[rel]:
            out.append(rel)
    return sorted(out)


def source_name() -> str:
    m = _manifest()
    if m.exists():
        try:
            return json.loads(m.read_text(encoding="utf-8")).get("source") or "the source wiki"
        except ValueError:
            pass
    return "the source wiki"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Propose a local improvement to a shared file.")
    ap.add_argument("--stage", action="store_true", help="write the proposal bundle")
    ap.add_argument("--by", help="who is proposing (required to stage)")
    ap.add_argument("--out", default="upstream_proposal")
    args = ap.parse_args(argv)

    if ROOT.name == source_name():
        print(f"this IS the source wiki ({source_name()}) — changes here flow outward on the next\n"
              "  sync. There is no upstream to propose to. Run this from a sibling instead.")
        return 0

    if not _state().exists():
        print("no merge base recorded — run the sync once from the source wiki first.\n"
              "  Without it, a local change cannot be told apart from the source having moved on,\n"
              "  and proposing the difference would be proposing noise.")
        return 0

    files = changed()
    here = ROOT.name
    if not files:
        print(f"nothing to propose — {here} has not changed any file in the shared layer\n"
              f"  since the last sync from {source_name()}.")
        return 0

    print(f"{len(files)} shared file(s) changed in {here}, not yet upstream:\n")
    for rel in files:
        print(f"  {rel}")
    if not args.stage:
        print(f"\n  Stage them with:  --stage --by \"Your Name\"\n"
              f"  Nothing is sent. A bundle is written for a human to open against {source_name()}.")
        return 0

    if not args.by:
        print("\n--by is required to stage: provenance is stamped, never invented.")
        return 1

    rev = _sh("git", "rev-parse", "--short", "HEAD") or "unknown"
    dirty = bool(_sh("git", "status", "--porcelain"))
    out = pathlib.Path(args.out)
    if out.exists():
        import shutil
        shutil.rmtree(out)
    (out / "files").mkdir(parents=True)

    notes = [f"# Upstream proposal from `{here}`", "",
             f"- **Proposed by:** {args.by}", f"- **From:** `{here}` at `{rev}`"
             + ("  ⚠ working tree was dirty, so the revision does not describe this exactly" if dirty else ""),
             f"- **To:** `{source_name()}`", "",
             "Staged by `tools/propose_upstream.py`. Nothing was sent — open this against the "
             "source repo so the diff can be read and decided on.", "", "---", ""]

    for rel in files:
        dest = out / "files" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / rel).read_bytes())
        notes += [f"## `{rel}`", "", "```diff"]
        # diff against the last synced state is not reconstructable from a digest, so show the
        # change against the source copy if it is reachable, and say so plainly when it is not.
        src = ROOT.parent / source_name() / rel
        if src.is_file():
            d = list(difflib.unified_diff(
                src.read_text(errors="replace").splitlines(),
                (ROOT / rel).read_text(errors="replace").splitlines(),
                f"{source_name()}/{rel}", f"{here}/{rel}", lineterm="", n=3))
            notes += d[:400] or ["(identical to the source copy on disk)"]
        else:
            notes.append(f"({source_name()} is not checked out beside this repo, so no diff "
                         f"could be rendered. The full file is in files/{rel}.)")
        notes += ["```", ""]

    (out / "PROPOSAL.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print(f"\n  staged {len(files)} file(s) in {out}/")
    print(f"  {out}/PROPOSAL.md carries the provenance and the diffs.")
    print(f"  Nothing has left this repo. Open it against {source_name()} to propose the change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
