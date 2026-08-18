#!/usr/bin/env python3
"""
house_rules.py — the two xCO house rules, enforced rather than remembered.

From Dark-Matter-Labs/xco-style-guide#11, where they became first-class:

  1. Always spell civilization with a z, never an s.
  2. Always write xCO — lowercase x, uppercase CO.

Rule 1 is a deliberate exception to the rest of the house's British spelling:
"optionality", "manoeuvre" and "organising" keep their s, and civilization does not.
That is exactly the sort of rule nobody remembers, which is why it is checked.

What is NOT touched, and why
----------------------------
* `raw/` — source documents are immutable. A source that says "civilisation" said
  that; correcting it would falsify the record.
* Blockquote lines (`>`) — a verbatim quotation belongs to whoever wrote it.
* Any file containing the marker `house-rules: ignore-file`, and this linter's own
  test fixtures.
* Slugs, paths, domains, handles, URLs, CSS custom properties and filenames.
  `xco-style-guide`, `docs/xco.md`, `xco@example.org` and `--xco-tokens` are all
  correct lowercase, and flagging them would train people to ignore the linter.

Casing detection is case-sensitive, so a correct `xCO` never trips, while a
sentence-final `Built with XCO.` still does.

Usage:
  python3 tools/house_rules.py              # report
  python3 tools/house_rules.py --fix        # apply, then report what changed
  python3 tools/house_rules.py --check      # exit 1 on any violation (CI)
"""

import argparse
import os
import re
import sys

# `export/` is generated from wiki/ — fixing it directly would be corrected twice
# and drift the moment anything regenerates. Fix the source; rebuild the export.
SKIP_DIRS = {".git", "raw", "export", "node_modules", "view", "contrib",
             ".commons", "__pycache__"}
EXTS = {".md", ".html", ".txt", ".json", ".css", ".py", ".yml", ".yaml"}

# Rule 1 — the s/z family. Case is preserved when fixing.
CIVIL = re.compile(r"\bcivilis(ation|ations|ational|ed|es|ing|e)\b", re.I)

# Rule 2 — a standalone xCO token. The character classes on both sides are what
# keep slugs, paths, domains, handles and identifiers out: `xco-style-guide`,
# `docs/xco.md`, `xco@example.org`, `--xco-tokens` all have an excluded neighbour.
BAD_CASE = re.compile(
    r"(?<![A-Za-z0-9_./@-])(XCO|Xco|xCo|XCo|xco)(?![A-Za-z0-9_@/-]|\.[A-Za-z0-9])")

URL = re.compile(r"https?://\S+")


def fix_civil(m):
    """Swap the s for a z, preserving the case of the letter replaced.

    The s sits at index 6 of "civilis". An off-by-one here produced "Civilzsation"
    and the edge-case tests caught it before anything shipped.
    """
    word = m.group(0)
    z = "Z" if word[6].isupper() else "z"
    return word[:6] + z + word[7:]


def scan_text(text, fix=False):
    """Return (new_text, [(rule, line_no, excerpt)])."""
    hits, lines = [], text.split("\n")
    for i, line in enumerate(lines, 1):
        # A verbatim quotation is not ours to correct.
        if line.lstrip().startswith(">"):
            continue
        # Blank out URLs for detection so a link never trips a rule.
        probe = URL.sub(lambda m: " " * len(m.group(0)), line)

        for m in CIVIL.finditer(probe):
            hits.append(("civilization-z", i, m.group(0)))
        for m in BAD_CASE.finditer(probe):
            hits.append(("xCO-casing", i, m.group(0)))

        if fix and (CIVIL.search(probe) or BAD_CASE.search(probe)):
            # Rebuild the line, leaving any URL span untouched.
            out, last = [], 0
            for u in URL.finditer(line):
                out.append(_apply(line[last:u.start()]))
                out.append(u.group(0))
                last = u.end()
            out.append(_apply(line[last:]))
            lines[i - 1] = "".join(out)
    return "\n".join(lines), hits


def _apply(chunk):
    chunk = CIVIL.sub(fix_civil, chunk)
    return BAD_CASE.sub("xCO", chunk)


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in EXTS:
                yield os.path.join(dirpath, fn)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check the two xCO house rules.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--fix", action="store_true", help="apply the corrections")
    ap.add_argument("--check", action="store_true", help="exit 1 on any violation")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    by_rule, by_file, changed = {}, {}, 0
    for path in sorted(walk(args.root)):
        # Never rewrite the linter or its fixtures. The first --fix run "corrected"
        # the inputs in test_house_rules.py, turning every case into xCO -> xCO and
        # making the whole suite vacuous. A linter that edits its own test data
        # cannot be trusted to have been tested.
        if os.path.basename(path) in ("house_rules.py", "test_house_rules.py"):
            continue
        try:
            src = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if "house-rules: ignore-file" in src:
            continue
        new, hits = scan_text(src, fix=args.fix)
        if not hits:
            continue
        rel = os.path.relpath(path, args.root)
        by_file[rel] = len(hits)
        for rule, ln, ex in hits:
            by_rule.setdefault(rule, []).append((rel, ln, ex))
        if args.fix and new != src:
            open(path, "w", encoding="utf-8").write(new)
            changed += 1

    total = sum(by_file.values())
    if args.fix:
        print(f"house rules — corrected {total} occurrence(s) across {changed} file(s)\n")
    else:
        print(f"house rules — {total} occurrence(s) in {len(by_file)} file(s)\n")

    for rule, items in sorted(by_rule.items()):
        print(f"  {rule}: {len(items)}")
        if args.verbose:
            for rel, ln, ex in items[:40]:
                print(f"      {rel}:{ln}  {ex}")
            if len(items) > 40:
                print(f"      … and {len(items) - 40} more")
    if by_file and not args.verbose:
        print("\n  worst files:")
        for rel, n in sorted(by_file.items(), key=lambda kv: -kv[1])[:8]:
            print(f"    {n:>5}  {rel}")

    if not total:
        print("  clean — both rules hold.")
    print("\n  Not scanned: raw/ (immutable sources) and blockquoted lines "
          "(someone else's words).")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    raise SystemExit(main())
