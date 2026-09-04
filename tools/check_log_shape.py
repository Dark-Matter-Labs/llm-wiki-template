#!/usr/bin/env python3
"""Guard the log's shape: entries live in day files, month files are indexes only.

The log moved from one file per month to one file per day on 2026-08-13, because a
month file is a single append point and two sessions working the same day collided on
it every time — resolved by hand five times before the split.

Within hours of the split a parallel session, still mid-flight on the old convention,
appended a full entry to `wiki/log/2026-08.md` — which is now an index, not an entry
file. Nothing errored; the entry was simply in a file nothing reads for entries. So the
convention gets a check, on the same principle as the design-standard gate: a
convention nobody enforces is a preference.

Checks:
  1. No `## [YYYY-MM-DD]` entry appears in a month index file (`wiki/log/YYYY-MM.md`).
     Pre-split months are exempt by an explicit allowlist, not by guesswork.
  2. Every entry in a day file carries that day's date — an entry dated 08-11 sitting in
     2026-08-12.md is how chronology quietly rots, which is what the split found in the
     old monthly file (five out-of-order points).
  3. Every day file is listed in its month index, and every listed day file exists.

Exit 0 clean, 1 with findings. No untrusted input; reads only files in this repo.
"""

from __future__ import annotations

import os
import json
import pathlib
import re
import sys

LOG = pathlib.Path(__file__).resolve().parent.parent / "wiki" / "log"

# Months written before the per-day split; single files by design, never retrofitted.
def _pre_split_months():
    """Months that predate the per-day log split, read from this wiki's own federation.json.

    This used to be a constant in the source, which meant the value -- a fact about ONE wiki's
    history -- was baked into a file that wants to travel. indy-llm-wiki has July 2026 as a single
    month file; every wiki created after the split has none, and their copies of this tool differed
    only in that set. Moving the fact to per-repo config lets the code be identical everywhere.
    """
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "design", "federation.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return set(json.load(fh).get("pre_split_months", []))
    except (OSError, ValueError):
        return set()


PRE_SPLIT_MONTHS = _pre_split_months()

MONTH = re.compile(r"^\d{4}-\d{2}\.md$")
DAY = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
ENTRY = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]", re.M)
# A whole entry, for the duplicate check below.
BLOCK = re.compile(r"(?m)^(?=## \[\d{4}-\d{2}-\d{2}\])")


def main() -> int:
    findings: list[str] = []
    day_files: dict[str, list[str]] = {}

    for path in sorted(LOG.glob("*.md")):
        text = path.read_text()
        dates = ENTRY.findall(text)

        if MONTH.match(path.name):
            month = path.stem
            if month in PRE_SPLIT_MONTHS:
                continue
            if dates:
                findings.append(
                    f"{path.relative_to(LOG.parent.parent)}: {len(dates)} entry/entries in a month "
                    f"index — move them to wiki/log/{dates[0]}.md (append to today's file, not the "
                    f"month file)"
                )
        elif m := DAY.match(path.name):
            day = m.group(1)
            day_files.setdefault(day[:7], []).append(day)
            wrong = sorted({d for d in dates if d != day})
            if wrong:
                findings.append(
                    f"{path.relative_to(LOG.parent.parent)}: entries dated {', '.join(wrong)} in the "
                    f"{day} file — each entry belongs in the day file matching its own date"
                )
            if not dates:
                findings.append(f"{path.relative_to(LOG.parent.parent)}: day file with no entries")

            # Day files are union-merged (see .gitattributes), so a bad merge lands
            # without conflict markers and without anyone reading it. Duplication is
            # how that goes wrong, and it has gone wrong once already: a faulty reset
            # on 2026-08-20 put four of Robyn's entries in twice, and every gate then
            # in place passed. This is the compensating control for the review point
            # union removes.
            blocks = [b.rstrip() for b in BLOCK.split(text) if b.startswith("## [")]
            seen: dict[str, int] = {}
            for b in blocks:
                seen[b] = seen.get(b, 0) + 1
            for b, n in seen.items():
                if n > 1:
                    findings.append(
                        f"{path.relative_to(LOG.parent.parent)}: entry appears {n} times — "
                        f"{b.splitlines()[0][:70]}"
                    )

    # cross-check the month indexes against the day files on disk
    for month, days in sorted(day_files.items()):
        index = LOG / f"{month}.md"
        if not index.exists():
            findings.append(f"wiki/log/{month}.md: month index missing for {len(days)} day file(s)")
            continue
        listed = set(re.findall(r"\((\d{4}-\d{2}-\d{2})\.md\)", index.read_text()))
        for missing in sorted(set(days) - listed):
            findings.append(f"wiki/log/{month}.md: {missing}.md exists but is not listed in the index")
        for phantom in sorted(listed - set(days)):
            findings.append(f"wiki/log/{month}.md: lists {phantom}.md, which does not exist")

    if findings:
        print("log shape check FAILED:", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        return 1

    total = sum(len(v) for v in day_files.values())
    print(f"log shape OK — {total} day file(s) across {len(day_files)} month(s), "
          f"{len(PRE_SPLIT_MONTHS)} pre-split month file(s) exempt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
