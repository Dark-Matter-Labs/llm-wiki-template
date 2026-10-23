#!/usr/bin/env python3
"""test_source_refresh.py — the source re-check's own cases, with a fake web so nothing is fetched."""

import contextlib
import io
import pathlib
import sys
import tempfile
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import source_refresh as R  # noqa: E402


def main() -> int:
    fails = []
    check = lambda name, ok: fails.append(name) if not ok else print(f"  ok   {name}")
    check("a labelled source address is found", R.source_url("# T\n\n- Source: https://a.example/p/x\n") == "https://a.example/p/x")
    check("a frontmatter url is found", R.source_url("---\nurl: https://b.example/y\n---\n") == "https://b.example/y")
    check("trailing punctuation is dropped", R.source_url("See https://c.example/z.\n") == "https://c.example/z")
    check("a sign-in service is not checkable", not R.checkable("https://docs.google.com/document/d/1"))
    check("markup and spacing do not count as change",
          R.fingerprint(R.page_text(b"<p>Hello  <b>world</b></p><script>x()</script>")) == R.fingerprint(R.page_text(b"<div>Hello world</div>")))
    web = {"https://a.example/p": b"<p>first version</p>"}

    def getter(url):
        if url not in web:
            raise urllib.error.URLError("gone")
        return web[url]

    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        (root / "raw").mkdir()
        (root / "raw" / "a.md").write_text("# A\n- Source: https://a.example/p\n\nsaved text\n")
        (root / "raw" / "g.md").write_text("# G\nSource: https://docs.google.com/document/d/1\n")
        (root / "raw" / "dead.md").write_text("# D\nSource: https://dead.example/q\n")
        before = (root / "raw" / "a.md").read_text()
        run = lambda *a: R.main(list(a), root=root, getter=getter)
        with contextlib.redirect_stdout(io.StringIO()):
            run()
        s = R.load(root)
        check("the first check records a baseline", s["raw/a.md"]["status"] == "new" and "baseline" in s["raw/a.md"])
        check("a sign-in source is listed, not fetched", s["raw/g.md"]["status"] == "not-checkable")
        check("a dead page is unreachable", s["raw/dead.md"]["status"] == "unreachable")
        with contextlib.redirect_stdout(io.StringIO()):
            run()
        check("an unchanged page stays unchanged", R.load(root)["raw/a.md"]["status"] == "unchanged")
        web["https://a.example/p"] = b"<p>second version</p>"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run()
        check("an edited page is reported changed", R.load(root)["raw/a.md"]["status"] == "changed" and "raw/a.md" in out.getvalue())
        check("raw/ is never edited", (root / "raw" / "a.md").read_text() == before)
        with contextlib.redirect_stdout(io.StringIO()):
            run("--accept", "raw/a.md")
            run()
        check("after --accept the new version is the baseline", R.load(root)["raw/a.md"]["status"] == "unchanged")
    for f in fails:
        print(f"  FAIL {f}")
    print(f"{len(fails)} check(s) failed" if fails else "all checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
