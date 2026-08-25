#!/usr/bin/env python3
"""
test_measure_scale.py — the two properties the scale meter got wrong, pinned.

Both were found on 2026-08-25 by running the meter rather than by reasoning about it,
two days after the index was tiered:

  1. **It fired a false 16.3% routing gap.** It read `wiki/index.md` alone, so the 356
     rows that had just moved onto the shelves under `wiki/index/` were invisible and
     125 pages looked unlisted. This is the same blindness `sync_index_counts.py` had,
     in a second tool nobody thought to check when the first was fixed.

  2. **Its router tripwire could not fire on the failure it existed to catch.** It read
     `> 1500 lines`. The index at its worst was 523 lines and ~55,000 tokens. The rows had
     grown, not multiplied. A meter that reports "523, fine" while every operation pays
     55k is not a broken meter — it is an active source of false assurance.

  python3 tools/test_measure_scale.py
"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_scale  # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def page(d, name, title):
    (d / name).write_text(
        f"---\ntype: concept\ntitle: {title}\ndescription: d\ntags: [t]\n"
        f"status: draft\nvisibility: internal\nconfidence: low\nvalidation: machine\n"
        f"timestamp: 2026-08-25\nsources: []\n---\n\nBody about {title}.\n",
        encoding="utf-8")


def build(tmp, router, shelf=None):
    wiki = pathlib.Path(tmp) / "wiki"
    (wiki / "index").mkdir(parents=True)
    page(wiki, "alpha.md", "Alpha")
    page(wiki, "beta.md", "Beta")
    (wiki / "index.md").write_text(router, encoding="utf-8")
    if shelf is not None:
        (wiki / "index" / "concepts.md").write_text(shelf, encoding="utf-8")
    return str(wiki)


def main():
    print("measure_scale — coverage reads the shelves; cost is counted in tokens\n")

    # search.read_pages() reads the real corpus; the probe set is irrelevant here.
    measure_scale.search.read_pages = lambda: []
    measure_scale.search.score = lambda _p, _q: []

    with tempfile.TemporaryDirectory() as tmp:
        # A page catalogued ONLY on a shelf is listed. The router links neither page.
        w = build(tmp, "# Index\n\nSee [[Alpha]].\n", "# Concepts\n\n- [[Beta]] — b\n")
        m = measure_scale.measure(w)
        check("a page listed only on a shelf is not a routing gap",
              m["routing_gaps"] == 0, f"reported {m['routing_gaps']}: {m['_missing_sample']}")
        check("shelves are counted", m["shelves"] == 1, f"reported {m['shelves']}")

    with tempfile.TemporaryDirectory() as tmp:
        # Same wiki, no shelf: Beta really is unreachable and must be reported.
        w = build(tmp, "# Index\n\nSee [[Alpha]].\n")
        m = measure_scale.measure(w)
        check("a genuinely unlisted page is still a routing gap",
              m["routing_gaps"] == 1, f"reported {m['routing_gaps']}")

    with tempfile.TemporaryDirectory() as tmp:
        # The template wikis catalogue with ordinary markdown paths, not wiki-links.
        # Reading only [[...]] reported 100% of their pages unlisted — a false alarm
        # about a file format, dressed as a finding about routing.
        w = build(tmp, "# Index\n\n- [Alpha](alpha.md)\n- [Beta](sub/beta.md)\n")
        # Beta lives in a subdirectory and shares its basename with a decoy at the root:
        # resolution must go by path, or the decoy gets the credit and Beta stays a gap.
        wp = pathlib.Path(w)
        (wp / "sub").mkdir()
        (wp / "beta.md").rename(wp / "sub" / "beta.md")
        page(wp, "beta.md", "Beta Decoy")
        m = measure_scale.measure(w)
        check("a markdown-path catalogue counts as listed, resolved by path",
              m["routing_gaps"] == 1 and m["_missing_sample"] == ["Beta Decoy"],
              f"reported {m['routing_gaps']}: {m['_missing_sample']}")

    with tempfile.TemporaryDirectory() as tmp:
        # The shape that slipped through: few lines, enormous rows.
        fat = "# Index\n\n" + "".join(f"- [[P{i}]] — {'x' * 900}\n" for i in range(80))
        w = build(tmp, fat, "# Concepts\n\n- [[Alpha]] — a\n- [[Beta]] — b\n")
        m = measure_scale.measure(w)
        fired = measure_scale.verdict(m)
        check("a fat router fires the cost tripwire despite few lines",
              any("routing costs" in f for f in fired),
              f"{m['index_lines']} lines, {m['router_tokens']} tokens, fired={fired}")
        check("the old line tripwire would NOT have caught it",
              m["index_lines"] < 1500, f"{m['index_lines']} lines")

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
