#!/usr/bin/env python3
"""
sync_log_index.py — regenerate each month's log index from its day files.

The log split from one file per month to one file per day on 2026-08-13 (a month file
is a single append point, and two sessions working the same day collided on it every
time). `check_log_shape.py` guards the split itself: no entries in a month file, every
entry dated to the day file it sits in, every day file listed in its month's index.

What it does not guard is content drift. The month index is a hand-written summary
of each day — an entry count and an "operations" breakdown — and both are worked out by
reading the day file, not derived from it. That summary went stale twice: "the month
index had lost today" was diagnosed and repaired on 2026-08-13
(wiki/log/2026-08-14.md), and the exact same defect recurred on 2026-08-18
(wiki/log/2026-08-18.md, second `repair | The month index lost today again (mine)`).
Two entries that both say "remember to do the second step" are not a memory problem,
they are a missing tool — the row is a **projection of the day file**, and nothing
should ever hand-type a projection.

This script recomputes every month's index table directly from its day files: for each
`wiki/log/YYYY-MM-DD.md`, it counts entries by their `## [date] type | …` prefix and
renders `type` (or `type×N` when N > 1), highest count first, ties broken by the order
the type first appears in the day file — the convention already used by every
hand-written row before this tool existed. Regenerating is idempotent: run it again on
an unchanged day file and the index is byte-identical, so it is safe to run after every
edit rather than only when something looks wrong.

Months exempt from the per-day convention (`PRE_SPLIT_MONTHS`, kept in sync with
`check_log_shape.py`) are left alone — they are single files by design and were never
retrofitted.

Usage:
  python3 tools/sync_log_index.py           # regenerate, report what changed
  python3 tools/sync_log_index.py --check   # exit 1 if any index is out of date; write nothing (CI)
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

LOG = pathlib.Path(__file__).resolve().parent.parent / "wiki" / "log"

# Kept in sync with tools/check_log_shape.py — months written before the per-day
# split; single files by design, never retrofitted.
PRE_SPLIT_MONTHS: "set[str]" = set()   # migrated whole; no month here predates the split

DAY = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
# `+` is in the class because compound operations are an established convention in the
# log — `query+build`, `delta+rebuild` on 2026-08-02. Without it those two entries did
# not match, the day counted 28 instead of 30, and `--check` would then have enforced
# the undercount as canonical. A projection tool that cannot see part of its own source
# is worse than the stale hand-typed row it replaces, because it is authoritative.
ENTRY = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]\s*([A-Za-z+-]+)\s*\|", re.M)
# Every `## [` heading must parse. One that does not is a format nobody anticipated,
# and silently dropping it is exactly the failure above.
HEADING = re.compile(r"^## \[.*$", re.M)

MONTH_NAMES = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}


def entry_counts(day_path: pathlib.Path) -> "list[tuple[str, int]]":
    """Operation counts for one day file, in first-appearance order."""
    counts: "dict[str, int]" = {}
    order: "list[str]" = []
    text = day_path.read_text(encoding="utf-8")

    matched = ENTRY.findall(text)
    headings = HEADING.findall(text)
    if len(matched) != len(headings):
        unparsed = [h for h in headings if not ENTRY.match(h)]
        raise ValueError(
            f"{day_path.name}: {len(unparsed)} entry heading(s) do not parse as "
            f"`## [YYYY-MM-DD] type | title`, so the count would be wrong:\n    "
            + "\n    ".join(h[:100] for h in unparsed))

    for _date, kind in matched:
        if kind not in counts:
            order.append(kind)
        counts[kind] = counts.get(kind, 0) + 1
    return [(k, counts[k]) for k in order]


def format_ops(counts: "list[tuple[str, int]]") -> str:
    # Highest count first; ties keep first-appearance order (a stable sort achieves
    # this for free, since `counts` already arrives in that order).
    ordered = sorted(counts, key=lambda kv: -kv[1])
    return ", ".join(f"{k}×{n}" if n > 1 else k for k, n in ordered)


def build_month_index(month: str, days: "list[str]") -> str:
    year, mon = month.split("-")
    lines = [
        f"# Wiki Log — {MONTH_NAMES[mon]} {year}",
        "",
        "Index of the month's daily log files. Entries live in **one file per day** so that two",
        "sessions working on the same day never collide on the same file. Newest day at the bottom.",
        "",
        "| Day | Entries | Operations |",
        "|---|---|---|",
    ]
    for day in sorted(days):
        counts = entry_counts(LOG / f"{day}.md")
        total = sum(n for _k, n in counts)
        lines.append(f"| [{day}]({day}.md) | {total} | {format_ops(counts)} |")
    lines.append("")
    lines.append("Format and the full month list live in [`wiki/log.md`](../log.md).")
    lines.append("")
    return "\n".join(lines)


def find_day_files() -> "dict[str, list[str]]":
    by_month: "dict[str, list[str]]" = {}
    for path in sorted(LOG.glob("*.md")):
        m = DAY.match(path.name)
        if m:
            day = m.group(1)
            by_month.setdefault(day[:7], []).append(day)
    return by_month


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                     help="exit 1 if any index would change; write nothing (CI)")
    args = ap.parse_args(argv)

    by_month = find_day_files()
    changed = []

    for month, days in sorted(by_month.items()):
        if month in PRE_SPLIT_MONTHS:
            continue
        index_path = LOG / f"{month}.md"

        # This script REPLACES the month file wholesale, which is only safe when that
        # file is purely an index. A wiki that has not migrated to the per-day split
        # still keeps its entries there, and one stray day file is enough to make this
        # loop think the month is split. Simulated against a sibling wiki before this
        # guard existed: 9 entries and 132 lines became an index listing one day.
        # A month file holding entries is therefore refused, not overwritten.
        if index_path.exists():
            existing = index_path.read_text(encoding="utf-8")
            if ENTRY.search(existing) or HEADING.search(existing):
                print(f"error: wiki/log/{month}.md still contains log entries, so it is "
                      f"not an index yet.\n"
                      f"       Overwriting it would delete them. This wiki has not "
                      f"migrated to the one-file-per-day split;\n"
                      f"       split {month}'s entries into wiki/log/{month}-DD.md "
                      f"files first, then run this.", file=sys.stderr)
                return 1

        try:
            new_content = build_month_index(month, days)
        except ValueError as e:
            # A gate people cannot act on is a gate they learn to ignore, so this
            # reports the offending heading rather than a traceback.
            print(f"error: {e}", file=sys.stderr)
            return 1
        old_content = (index_path.read_text(encoding="utf-8")
                       if index_path.exists() else None)
        if old_content != new_content:
            changed.append(month)
            if not args.check:
                index_path.write_text(new_content, encoding="utf-8")

    if args.check:
        if changed:
            print("log index OUT OF DATE:", file=sys.stderr)
            for m in changed:
                print(f"  - wiki/log/{m}.md does not match its day files "
                      f"(run: python3 tools/sync_log_index.py)", file=sys.stderr)
            return 1
        print(f"log index OK — {len(by_month) - len(PRE_SPLIT_MONTHS & by_month.keys())} "
              f"month(s) match their day files")
        return 0

    if changed:
        print(f"regenerated {len(changed)} month index file(s): {', '.join(changed)}")
    else:
        print("log index already up to date — nothing regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
