#!/usr/bin/env python3
"""
retract.py — remove a leaked value (a secret, a private title, a name) from every copy in this wiki.

    python3 tools/retract.py              # asks for the value without showing it, then lists where it is
    python3 tools/retract.py --apply      # the same, then replaces every copy with [RETRACTED] and re-scans
    printf '%s' "$VALUE" | python3 tools/retract.py --stdin [--apply]

Adapted on 23 October 2026 from the retract command in nvk/llm-wiki. A person runs it, in their own terminal:
the value is typed into a hidden prompt, so it never appears in a chat, a command line, a log or this tool's
output. Claude never handles it.

It looks for the value as written and in the forms a leak usually takes: URL-encoded, JSON-escaped, base64
(standard and URL-safe) and hex. It reads every text file in the wiki, including the local `raw/` and
`export/` copies that git ignores. `raw/` is otherwise never edited; a leak is the one exception, and the
person running this makes that call.

It does not reach:
- **git history.** Earlier commits keep the old text. Rotate a leaked secret; ask an admin about rewriting
  history for anything else.
- **the locked lens.** It is encrypted, so the value cannot be searched there. Rebuild and lock it again.
- **binary files** such as PDFs and images. They are listed for a person to replace by hand.
- **other wikis and commons**, which need their own run.

A past day's log changed here fails the history guard until a person adds the `approved-removal` label.
The run ends `verified` (nothing left) or `incomplete` (with where), never silently.
"""

import argparse
import base64
import getpass
import json
import pathlib
import subprocess
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = "[RETRACTED]"
SKIP_DIRS = {".git", "node_modules", ".commons", "__pycache__", ".staleness-cache"}
EXTRA_DIRS = ("raw", "export", "docs", "wiki", "design")
MAX_BYTES = 20_000_000
MIN_LEN = 4


def variants(value: str) -> list:
    """The value as written and in the encodings a leak usually takes, longest first so none is half-replaced."""
    b = value.encode("utf-8")
    forms = {value, urllib.parse.quote(value, safe=""), urllib.parse.quote_plus(value),
             json.dumps(value)[1:-1],
             base64.b64encode(b).decode().rstrip("="), base64.urlsafe_b64encode(b).decode().rstrip("="),
             b.hex(), b.hex().upper()}
    return sorted((f for f in forms if len(f) >= MIN_LEN), key=len, reverse=True)


def files(root: pathlib.Path) -> list:
    """Every file git tracks, plus the local copies under raw/, export/, docs/, wiki/ and design/ it ignores."""
    out = set()
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True)
    out.update(root / p for p in r.stdout.split("\0") if p)
    for d in EXTRA_DIRS:
        if (root / d).is_dir():
            out.update(p for p in (root / d).rglob("*") if p.is_file())
    return sorted(p for p in out if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS))


def scan(root: pathlib.Path, forms: list) -> tuple:
    """({text file: count}, [binary files that hold it]), never the value itself."""
    hits, binary = {}, []
    raw = [f.encode("utf-8") for f in forms]
    for p in files(root):
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
            data = p.read_bytes()
        except OSError:
            continue
        n = sum(data.count(f) for f in raw)
        if not n:
            continue
        if b"\0" in data[:4096]:
            binary.append(p)
        else:
            hits[p] = n
    return hits, binary


def apply(hits: dict, forms: list) -> None:
    for p in hits:
        text = p.read_text(encoding="utf-8", errors="surrogateescape")
        for f in forms:
            text = text.replace(f, MARK)
        p.write_text(text, encoding="utf-8", errors="surrogateescape")


def report(root, hits, binary, header):
    print(header)
    for p, n in sorted(hits.items()):
        print(f"  {n:>4}  {p.relative_to(root)}")
    for p in binary:
        print(f"  ----  {p.relative_to(root)}  (binary: replace or remove this file by hand)")


def main(argv=None, root: pathlib.Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description="Remove a leaked value from every copy in this wiki.")
    ap.add_argument("--stdin", action="store_true", help="read the value from standard input, not a hidden prompt")
    ap.add_argument("--apply", action="store_true", help="replace every copy with [RETRACTED]; without it, only report")
    a = ap.parse_args(argv)
    value = (sys.stdin.read() if a.stdin else getpass.getpass("Value to retract (typing is hidden): ")).strip("\n")
    if len(value) < MIN_LEN:
        print(f"refused: a value shorter than {MIN_LEN} characters would match too much.")
        return 2
    forms = variants(value)
    hits, binary = scan(root, forms)
    if not hits and not binary:
        print("verified: the value is not in any file here. (Git history and the locked lens are not searched.)")
        return 0
    report(root, hits, binary, f"found in {len(hits) + len(binary)} file(s), {sum(hits.values())} copies in text:")
    if not a.apply:
        print("\nNothing changed. Run again with --apply to replace every copy with " + MARK + ".")
        return 0
    apply(hits, forms)
    left, left_bin = scan(root, forms)
    if left or left_bin:
        report(root, left, left_bin, "\nincomplete: the value is still in:")
        return 1
    print(f"\nverified: {sum(hits.values())} copies replaced in {len(hits)} file(s); a re-scan finds none.")
    print("Still to do: rotate it if it was a secret; rebuild and lock the lens; run this in any wiki or commons that "
          "received a copy. Git history keeps the old text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
