#!/usr/bin/env python3
"""No source path leaves this wiki in a contribution bundle.

Written 2026-10-29 by Fang. A page had had a person's name removed from its body with care,
and still named him three times in its citations, inside a source filename. Every other
guarantee in contribute.py had held; the leak walked out through a file path, because
nothing was reading filenames as content. (The filename is not quoted: this file travels to
every wiki.) The shared copy adds two cases agreed with Gurden the same day: a date anywhere
in a filename counts, and a source with no date and no label becomes "an undated source".

These tests fix the structural rule rather than the incident: whatever a source is called,
the path does not travel.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contribute  # noqa: E402

LABELS = {"2026-10-20-fortnightly-summary.md": "fortnightly session",
          "power-book-manuscript-2026-09-22.md": "Power Book manuscript"}

failures = []


def check(name, got, want):
    if got != want:
        failures.append(f"{name}\n      got:  {got!r}\n      want: {want!r}")


# A labelled, dated source reads as the session it was.
check("labelled",
      contribute.dated_reference("raw/2026-10-20-fortnightly-summary.md", LABELS),
      "fortnightly session, 20 October 2026")

# An unlabelled one is bare and dated — safe, because it says nothing but when.
check("unlabelled",
      contribute.dated_reference("raw/2026-10-13-portfolio-with-a-name-summary.md", {}),
      "source dated 13 October 2026")

# A date at the end of the filename counts as much as one at the start.
check("labelled, date at the end",
      contribute.dated_reference("raw/power-book-manuscript-2026-09-22.md", LABELS),
      "Power Book manuscript, 22 September 2026")
check("unlabelled, date at the end",
      contribute.dated_reference("raw/workshop-notes-2026-10-28.md", {}),
      "source dated 28 October 2026")

# No date and no label: a vaguer citation, never a refusal, and never the filename.
check("unlabelled, undated", contribute.dated_reference("raw/notes.md", {}), "an undated source")
check("a folder", contribute.dated_reference("raw/banos/drive/", {}), "an undated source")

# A path in backticks can hold spaces; it is replaced whole, so no half-name is left behind.
ticked = contribute.strip_source_paths("See `raw/A Person Name call notes.md` for detail.\n", {})
check("backticked path with spaces", ticked, "See an undated source for detail.\n")
# Saying the folder's name, with no file in it, gives nothing away and is left alone.
check("bare folder name", contribute.strip_source_paths("Never edit `raw/`.\n", {}), "Never edit `raw/`.\n")

# A reference carries a comma, which separates items in a YAML flow sequence. Inside
# frontmatter the replacement is quoted, so one source cannot silently become two.
page = ('---\n'
        'title: T\n'
        'sources: [raw/2026-10-20-fortnightly-summary.md, raw/2026-09-11-legal-summary.md]\n'
        '---\n'
        '\n'
        'A claim (raw/2026-10-20-fortnightly-summary.md).\n')
out = contribute.strip_source_paths(page, LABELS)
check("frontmatter quoted",
      [l for l in out.split("\n") if l.startswith("sources:")][0],
      'sources: ["fortnightly session, 20 October 2026", "source dated 11 September 2026"]')
check("body unquoted",
      [l for l in out.split("\n") if l.startswith("A claim")][0],
      "A claim (fortnightly session, 20 October 2026).")

# The proof, not the intention: nothing that looks like a source path survives.
if "raw/" in out:
    failures.append("a source path survived staging")

# A collision is a collision whatever the capitals. This was exact until 2026-10-29, when
# "Butterfly institution" staged cleanly against a commons holding "Butterfly Institution".
check("title key ignores case",
      contribute.title_key("Butterfly institution"),
      contribute.title_key("Butterfly Institution"))
check("title key ignores punctuation",
      contribute.title_key("Free-associational power"),
      contribute.title_key("Free associational power"))
if contribute.title_key("Ground game") == contribute.title_key("Capital stack"):
    failures.append("title key collapses genuinely different titles")

if failures:
    print("test_contribute_sources FAILED")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("contribute boundary OK — no source path travels, and a collision survives a change of case")
