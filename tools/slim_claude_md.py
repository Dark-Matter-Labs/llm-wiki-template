#!/usr/bin/env python3
"""
slim_claude_md.py — swap the template's long CLAUDE.md sections for the compact ones, where nobody has changed them.

Every session reads CLAUDE.md before it does anything. On 26 October 2026 the median wiki loaded about 54 KB of
instructions at the start of each session; the source wiki, slimmed on 13 October, loaded about 45 KB. The slim moved
detail into `.claude/reference/`, but those files never travelled, so the other wikis kept the long sections and their
shared rules pointed at a reference file they did not have. Asked for by Gurden on 26 October 2026, after Prateek and
he named token cost on that day's stand-up.

- The compact sections live in `design/claude-md-compact.md`, a shared file taken from the source wiki's CLAUDE.md.
- A section is replaced only when its text is still exactly the template's (TEMPLATE below). A section an owner
  changed is left as it is and reported, never merged or overwritten.
- Running it twice changes nothing.

  python3 tools/slim_claude_md.py              # replace what can be replaced, and report
  python3 tools/slim_claude_md.py --dry-run    # report only
  python3 tools/slim_claude_md.py --write-compact   # source wiki only: refresh design/claude-md-compact.md
"""
import argparse
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPACT = "design/claude-md-compact.md"

# The template's section -> the compact section that replaces it.
SWAP = {
    "The three layers (never blur them)": "The three layers (never blur them)",
    "Wiki page conventions": "Wiki page conventions",
    "Page types": "Page types",
    "The two navigation files": "The index and the log",
    "The core operations": "The core operations",
    "Hard rules": "Hard rules",
    "Working style": "Working style",
}
# sha256 of each section as llm-wiki-template wrote it (26 October 2026), normalised by norm(). Matched in 19 to 25 of
# the 27 wikis; every other version was a single wiki's own edit.
TEMPLATE = {
    "The three layers (never blur them)": "19f9d309adf3eadf1ee17656958c7f13e98170e50a4c68185020eaf50961cdf9",
    "Wiki page conventions": "b2a9fdc97a79cd770c3ff8a235aa1b2691797a08a7c72744ef451b55d07915d1",
    "Page types": "78a28d40e8af93c2a2ddc2f9960c2c1ae1edce5a638d32dc6c60f45219a7885f",
    "The two navigation files": "b958f02c4de19793e6380cd10be4200aa15fdfee14ea1e894ac69bd57f15a6f9",
    "The core operations": "0b4f604c43e7093ad25bb5fa910138674cfc1009a8ab7d5072188c2e260ac5ef",
    "Hard rules": "16ef30c7b7b2c133b13c56233b7aa94915cba210d04706cfac76d9c775d04b27",
    "Working style": "c92e6a91670f3bcf2c3674f7c187a27ac6628c347e013a40a377dc4f2ef3bb57",
}


def sections(text):
    """[(heading, start line, end line)] for each '## ' section outside code fences; it ends before the next heading."""
    lines, out, fence = text.split("\n"), [], False
    for i, ln in enumerate(lines):
        if ln.startswith("```"):
            fence = not fence
        if not fence and (ln.startswith("## ") or ln.startswith("# ")):
            if out and out[-1][2] is None:
                out[-1][2] = i
            if ln.startswith("## "):
                out.append([ln[3:].strip(), i, None])
    if out and out[-1][2] is None:
        out[-1][2] = len(lines)
    return [tuple(s) for s in out]


def split_tail(block):
    """(body, tail): the trailing blank lines and '---' dividers belong to the layout, not the section."""
    lines = block.split("\n")
    k = len(lines)
    while k and lines[k - 1].strip() in ("", "---"):
        k -= 1
    return "\n".join(l.rstrip() for l in lines[:k]), "\n".join(lines[k:])


def digest(body):
    return hashlib.sha256(body.encode()).hexdigest()


def compact_sections(text):
    lines = text.split("\n")
    return {h: split_tail("\n".join(lines[a:b]))[0] for h, a, b in sections(text)}


def slim(text, compact):
    """(new text, report rows (section, what happened, bytes before, bytes after))."""
    lines, rows, out, last = text.split("\n"), [], [], 0
    for h, a, b in sections(text):
        if h not in SWAP:
            continue
        body, tail = split_tail("\n".join(lines[a:b]))
        new = compact.get(SWAP[h])
        if new is None:
            rows.append((h, "kept: no compact version", len(body.encode()), len(body.encode())))
            continue
        if body == new:
            rows.append((h, "already compact", len(body.encode()), len(body.encode())))
            continue
        if digest(body) != TEMPLATE[h]:
            rows.append((h, "kept: changed in this wiki", len(body.encode()), len(body.encode())))
            continue
        out += lines[last:a] + (new + ("\n" + tail if tail else "")).split("\n")
        last = b
        rows.append((h, "replaced", len(body.encode()), len(new.encode())))
    return "\n".join(out + lines[last:]), rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Swap the template's long CLAUDE.md sections for the compact ones.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write-compact", action="store_true", help="source wiki: refresh design/claude-md-compact.md")
    a = ap.parse_args(argv)
    claude = ROOT / "CLAUDE.md"
    if a.write_compact:
        got = compact_sections(claude.read_text(encoding="utf-8"))
        want = sorted(set(SWAP.values()))
        missing = [h for h in want if h not in got]
        if missing:
            print("CLAUDE.md lacks: " + ", ".join(missing))
            return 1
        (ROOT / COMPACT).write_text(
            "<!-- The compact CLAUDE.md sections every wiki shares, from the source wiki. tools/slim_claude_md.py "
            "puts them in place of the template's long ones. Edit them in the source wiki's CLAUDE.md, then run "
            "--write-compact there. -->\n\n" + "\n\n".join(f"{got[h]}" for h in want) + "\n", encoding="utf-8")
        print(f"wrote {COMPACT}: {len(want)} sections")
        return 0
    compact = compact_sections((ROOT / COMPACT).read_text(encoding="utf-8"))
    before = claude.read_text(encoding="utf-8")
    after, rows = slim(before, compact)
    for h, what, b0, b1 in rows:
        print(f"  {what:28} {h}  ({b0} -> {b1} bytes)")
    saved = len(before.encode()) - len(after.encode())
    print(f"CLAUDE.md: {len(before.encode())} -> {len(after.encode())} bytes, about {saved // 4} tokens less per session"
          + (" (dry run)" if a.dry_run else ""))
    if not a.dry_run and after != before:
        claude.write_text(after, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
