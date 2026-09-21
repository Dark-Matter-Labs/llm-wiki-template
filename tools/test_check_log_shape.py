#!/usr/bin/env python3
"""
test_check_log_shape.py — the log's shape checks, and the one that was missing.

The heading check was added on 2026-09-21 after it failed to exist. Two branches both
appended to `wiki/log/2026-09-21.md`; git's union merge kept every entry, correctly dated
and in order, and dropped the file's heading. Nothing caught it. The entries were all
there, the month index regenerated cleanly, and all sixteen gates passed. The file had
simply stopped being a document, and the only reason anybody noticed was that a person
opened it.

Running the new check over the corpus then found a second one: `wiki/log/2026-08-18.md`
had been headless since August.

The check is deliberately loose about the wording. Three headings are in use across the
federation and all three are correct: `# Log — DATE`, `# Log, DATE` and
`# Wiki Log — DATE`. A gate that picked one and failed the other two would be enforcing
a punctuation preference across a corpus that never agreed on one, and gates that fail
correct work get switched off. What is checked is that there is a heading and that it
carries the file's own date.

  python3 tools/test_check_log_shape.py
"""

import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE / "check_log_shape.py"
FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def run(root):
    """Run the COPY of the tool that lives inside the temporary corpus.

    Not the real one. `check_log_shape.py` resolves the log directory from its own
    `__file__`, so running the repo's copy with `cwd` set to a fixture reads the
    repository and ignores the fixture entirely. Four of these cases passed that way
    before this was noticed, which is the failure this whole file is about: a test that
    cannot fail.
    """
    tool = pathlib.Path(root) / "tools" / "check_log_shape.py"
    p = subprocess.run([sys.executable, str(tool)], cwd=root, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def corpus(tmp, day_files, month_index=None):
    """A minimal wiki/log/ with the day files given, plus a matching month index."""
    root = pathlib.Path(tmp)
    log = root / "wiki" / "log"
    log.mkdir(parents=True)
    # the tool resolves LOG from its own location, so it needs a tools/ dir beside wiki/
    (root / "tools").mkdir(exist_ok=True)
    (root / "tools" / "check_log_shape.py").write_text(TOOL.read_text(encoding="utf-8"),
                                                       encoding="utf-8")
    for name, body in day_files.items():
        (log / name).write_text(body, encoding="utf-8")
    days = sorted(n[:-3] for n in day_files if len(n) == 13)
    if month_index is None and days:
        month = days[0][:7]
        rows = "".join(f"- [{d}]({d}.md)\n" for d in days)
        (log / f"{month}.md").write_text(f"# Log, {month}\n\n{rows}", encoding="utf-8")
    return root


def main():
    print("check_log_shape — the shape, and the heading that was not checked\n")

    GOOD = "# Log — 2026-09-21\n\n## [2026-09-21] lint | a clean day\n\nSomething happened.\n"

    with tempfile.TemporaryDirectory() as t:
        root = corpus(t, {"2026-09-21.md": GOOD})
        rc, out = run(root)
        check("a well-formed day file passes", rc == 0, out.strip()[-160:])

    # THE ONE THAT WAS MISSING. This is the exact shape a union merge produces: every
    # entry present, correctly dated, in order — and no heading.
    with tempfile.TemporaryDirectory() as t:
        root = corpus(t, {"2026-09-21.md": "## [2026-09-21] lint | a clean day\n\nSomething happened.\n"})
        rc, out = run(root)
        check("a day file with no heading is caught", rc == 1 and "level-1 heading" in out,
              out.strip()[-200:])

    # ...and it must not be caught by the entry checks, which is why it survived before.
    with tempfile.TemporaryDirectory() as t:
        root = corpus(t, {"2026-09-21.md": "## [2026-09-21] lint | a clean day\n"})
        rc, out = run(root)
        check("...and the finding names the heading, not the entries",
              "no entries" not in out and "belongs in the day file" not in out, out.strip()[-160:])

    # All three wordings in use across the federation are accepted.
    for heading in ("# Log — 2026-09-21", "# Log, 2026-09-21", "# Wiki Log — 2026-09-21"):
        with tempfile.TemporaryDirectory() as t:
            root = corpus(t, {"2026-09-21.md": f"{heading}\n\n## [2026-09-21] lint | ok\n"})
            rc, out = run(root)
            check(f"the heading {heading!r} is accepted", rc == 0, out.strip()[-140:])

    # A heading carrying the wrong date is the other way this rots.
    with tempfile.TemporaryDirectory() as t:
        root = corpus(t, {"2026-09-21.md": "# Log — 2026-09-20\n\n## [2026-09-21] lint | ok\n"})
        rc, out = run(root)
        check("a heading carrying another day's date is caught", rc == 1 and "level-1 heading" in out,
              out.strip()[-180:])

    # Leading blank lines are formatting, not an absent heading.
    with tempfile.TemporaryDirectory() as t:
        root = corpus(t, {"2026-09-21.md": "\n\n# Log — 2026-09-21\n\n## [2026-09-21] lint | ok\n"})
        rc, out = run(root)
        check("blank lines before the heading are not a finding", rc == 0, out.strip()[-140:])

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
