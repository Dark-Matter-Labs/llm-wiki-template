#!/usr/bin/env python3
"""test_retract.py — the retraction tool's own cases, on a throwaway wiki it builds and removes.
The value under test must never appear in the tool's output."""

import base64
import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import retract as R  # noqa: E402

VALUE = "Project Kestrel/42 & co"


def run(root, *args):
    out, old = io.StringIO(), sys.stdin
    sys.stdin = io.StringIO(VALUE)
    try:
        with contextlib.redirect_stdout(out):
            code = R.main(["--stdin", *args], root=root)
    finally:
        sys.stdin = old
    return code, out.getvalue()


def main() -> int:
    fails = []
    check = lambda name, ok: fails.append(name) if not ok else print(f"  ok   {name}")
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "wiki").mkdir(); (root / "raw").mkdir(); (root / "docs").mkdir()
        (root / "wiki" / "a.md").write_text(f"Plain: {VALUE}. Again: {VALUE}.\n")
        (root / "docs" / "b.html").write_text(f"<a href='x?q={urllib.parse.quote(VALUE, safe='')}'>link</a>\n")
        (root / "raw" / "c.json").write_text('{"t": "' + VALUE.replace("/", "\\/") + '", "b64": "'
                                             + base64.b64encode(VALUE.encode()).decode() + '"}\n')
        (root / "raw" / "d.pdf").write_bytes(b"%PDF\0\0" + VALUE.encode())
        (root / "wiki" / "clean.md").write_text("Nothing here.\n")
        code, out = run(root)
        check("a dry run finds the plain, URL-encoded and base64 copies",
              "wiki/a.md" in out and "docs/b.html" in out and "raw/c.json" in out)
        check("a dry run changes nothing", VALUE in (root / "wiki" / "a.md").read_text())
        check("a binary file is listed for a person", "raw/d.pdf" in out and "binary" in out)
        check("the value never appears in the output", VALUE not in out)
        code, out = run(root, "--apply")
        a = (root / "wiki" / "a.md").read_text()
        check("--apply replaces every text copy", VALUE not in a and a.count(R.MARK) == 2)
        check("the URL-encoded copy is replaced", urllib.parse.quote(VALUE, safe="") not in (root / "docs" / "b.html").read_text())
        check("the base64 copy is replaced", base64.b64encode(VALUE.encode()).decode().rstrip("=") not in (root / "raw" / "c.json").read_text())
        check("a binary copy left behind makes the run incomplete, not verified", code == 1 and "incomplete" in out)
        check("an untouched file stays untouched", (root / "wiki" / "clean.md").read_text() == "Nothing here.\n")
        (root / "raw" / "d.pdf").unlink()
        code, out = run(root)
        check("once nothing is left, the run says verified", code == 0 and out.startswith("verified"))
        old = sys.stdin; sys.stdin = io.StringIO("ab")
        try:
            with contextlib.redirect_stdout(io.StringIO()) as o:
                code = R.main(["--stdin"], root=root)
        finally:
            sys.stdin = old
        check("a value too short to be safe is refused", code == 2 and "refused" in o.getvalue())
    for f in fails:
        print(f"  FAIL {f}")
    print(f"{len(fails)} check(s) failed" if fails else "all checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
