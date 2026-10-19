#!/usr/bin/env python3
"""test_add_analytics.py — the counter goes on public pages of a wiki that opted in, never on a locked page, never
twice, never on a page with its own security rules, and never without --write."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import add_analytics as a  # noqa: E402


def main():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok &= bool(cond)

    page = "<html><body><p>essay</p></body></html>"
    new, why = a.with_counter(page)
    check("a public page gets the counter before </body>", why == "added" and new.index(a.MARK) < new.index("</body>"))
    check("never twice", a.with_counter(new) == (None, "already"))
    check("a locked page is left out", a.with_counter('<script>var SALT = "q8+/AA==", IV = "x"</script>')[1] == "locked")
    check("a page with its own security rules is left alone",
          a.with_counter('<meta http-equiv="Content-Security-Policy" content="x"><body></body>')[1] == "own security rules")
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "docs")); os.makedirs(os.path.join(d, "design"))
        open(os.path.join(d, "docs", "p.html"), "w").write(page)
        os.chdir(d)
        try:
            a.main(["docs"]) ; check("nothing happens without opting in", a.MARK not in open("docs/p.html").read())
            json.dump({"simpleanalytics": True}, open("design/analytics.json", "w"))
            a.main(["docs"]); check("without --write it only reports", a.MARK not in open("docs/p.html").read())
            a.main(["--write", "docs"]); check("with --write and opted in, the page is counted", a.MARK in open("docs/p.html").read())
        finally:
            os.chdir(here)
    print("\nall passed" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
