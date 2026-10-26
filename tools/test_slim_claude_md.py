#!/usr/bin/env python3
"""test_slim_claude_md.py — the template's text is swapped, an owner's edit never is, layout survives, twice is once."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slim_claude_md as s  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok &= bool(cond)

    compact = {"Working style": "## Working style\n\nShort.", "Page types": "## Page types\n\nTypes, briefly."}
    old_style = "## Working style\n\nA long paragraph about style."
    # Pretend the long text above is the template's, for this test only.
    s.TEMPLATE["Working style"] = s.digest(old_style)
    doc = ("# CLAUDE.md\n\nIntro.\n\n---\n\n" + old_style + "\n\n---\n\n## Page types\n\nOur own edited types.\n\n"
           "## Who you are working with\n\nRobyn.\n\n```\n## [2026-10-26] ingest | not a heading\n```\n")
    after, rows = s.slim(doc, compact)
    what = {h: w for h, w, *_ in rows}
    check("the template's text is replaced", what["Working style"] == "replaced" and "Short." in after
          and "A long paragraph" not in after)
    check("an owner's edit is kept, word for word", what["Page types"].startswith("kept") and "Our own edited types." in after)
    check("a section it does not manage is untouched", "## Who you are working with\n\nRobyn." in after)
    check("the divider after a replaced section survives", "Short.\n\n---\n\n## Page types" in after)
    check("a heading inside a code block is not a section",
          "## [2026-10-26] ingest | not a heading" in after and len(s.sections(doc)) == 3)
    check("running it twice changes nothing", s.slim(after, compact)[0] == after)
    check("a compact section already in place is reported as such", dict((h, w) for h, w, *_ in s.slim(after, compact)[1])
          ["Working style"] == "already compact")
    check("no change at all leaves the text identical", s.slim("# Only a title\n", compact)[0] == "# Only a title\n")

    shipped = os.path.join(ROOT, s.COMPACT)
    if os.path.exists(shipped):
        got = s.compact_sections(open(shipped, encoding="utf-8").read())
        check("the shared compact file holds every section it swaps in", set(s.SWAP.values()) <= set(got))
        check("every compact section names no single wiki's site",
              not any("github.io/" in v and "<this wiki" not in v for v in got.values()))
    print("\nall passed" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
