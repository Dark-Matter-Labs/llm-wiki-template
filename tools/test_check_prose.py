#!/usr/bin/env python3
"""
test_check_prose.py — prove the detector fires, and prove it leaves ordinary prose alone.

The second half is the one that decides whether this survives. A style check that flags normal
English gets switched off inside a fortnight, and the repo then believes its prose is watched.
Most of the cases below are therefore negatives.

Usage:  python3 tools/test_check_prose.py
"""
import json
import os
import pathlib
import subprocess
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_prose as C  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
        if not ok:
            fails.append(name)

    # --- the X-not-Y signature, which the source skill calls the dominant 2025-2026 tell ----
    catches = [
        "This isn't just a news story, it's a wake-up call.",
        "It's not about the technology, it's about the people.",
        "This is not just a rule, it is a paradigm.",
        "This wasn't just a press conference, it was a turning point.",
    ]
    for t in catches:
        check(f"catches: {t[:44]}", len(C.XNOTY_RE.findall(t)) > 0)

    leaves = [
        "The vote is not final but provisional.",
        "It is not raining.",
        "The page is not in the corpus, and nobody noticed.",
        "She is not the author, and the note says so.",
        "The facility is not viable without a named payer.",
    ]
    for t in leaves:
        check(f"leaves alone: {t[:42]}", len(C.XNOTY_RE.findall(t)) == 0)

    # The known gap, asserted so it stays known. If someone widens the pattern across a full
    # stop this test fails and they have to decide deliberately.
    check("the across-a-full-stop form is a KNOWN MISS, not silently handled",
          len(C.XNOTY_RE.findall("It's not a shortage of capital. It is a break in "
                                 "continuity.")) == 0)

    # --- what must never be counted ------------------------------------------------------
    check("a page title is a name, not prose",
          C.count("See [[Computational Landscape Adaptation Facility]] for that.")["words"] == 0)
    check("a fenced code block is not prose",
          C.count("text\n```\nleverage robust\n```\n")["words"] == 0)
    check("inline code is not prose", C.count("run `leverage --robust` now")["words"] == 0)
    check("a URL is not prose", C.count("see https://x.test/robust-landscape here")["words"] == 0)
    check("a quotation is somebody else's words",
          C.count("> This is a robust, comprehensive tapestry.\n")["words"] == 0)
    check("frontmatter is not prose",
          C.count("---\ntags: [robust, landscape]\n---\n\nplain text\n")["words"] == 0)
    # A catalogue row is navigation, and its em dash is a separator rather than a sentence.
    # Added 2026-09-15: filing six commitment pages raised the router's em dash count by six,
    # and the alternatives were baselining a debt nobody incurred or writing catalogue rows in
    # a format the rest of the corpus does not use. The file-level skip caught the shelves
    # under `wiki/index/` and missed `wiki/index.md`, which is the same object one level up.
    check("a catalogue row is not prose",
          C.count("- [[Some Page]] — one line about it\n")["emdash"] == 0)
    check("...and neither is an indented one",
          C.count("  - [[Some Page]] — one line about it\n")["emdash"] == 0)
    # The guard: an ordinary bulleted sentence is still prose, or this is a hole big enough
    # to hide a document in.
    check("an ordinary bullet is still prose",
          C.count("- This is a robust sentence — with an em dash.\n")["emdash"] == 1)
    check("...and its banned words still count",
          C.count("- This is a robust sentence.\n")["words"] == 1)
    check("a link row that is not a page title is still prose",
          C.count("- [a thing](https://x.test) — robust and comprehensive\n")["emdash"] == 1)

    # Added 2026-09-22. The same row written as a markdown link rather than a wiki-link was not
    # matched, so filing a page into an index that uses that form raised the ratchet on the act
    # of filing. It moved three times in one day in learning-system-wiki before this was fixed.
    check("a catalogue row written as a markdown link is not prose",
          C.count("- **[A Title](a-title.md)** — one line about it\n")["emdash"] == 0)
    check("...bold or not",
          C.count("- [A Title](a-title.md) — one line about it\n")["emdash"] == 0)
    check("...and indented",
          C.count("  - **[A Title](a-title.md)** — one line about it\n")["emdash"] == 0)
    # The two guards. The target decides, not the syntax: a row naming a page in this wiki is a
    # name, a row citing something outside it is a sentence. And the separator has to be there,
    # or every bulleted sentence that happens to start with a link escapes the gate.
    check("a row pointing outside the wiki is still prose",
          C.count("- [a thing](https://x.test) — robust and comprehensive\n")["emdash"] == 1)
    check("...including a bold one",
          C.count("- **[a thing](https://x.test)** — robust and comprehensive\n")["emdash"] == 1)
    check("a bulleted sentence that merely begins with a link is still prose",
          C.count("- **[A Title](a-title.md)** is a robust thing — really\n")["emdash"] == 1)
    check("...and its banned words still count",
          C.count("- [A Title](a-title.md) is robust and comprehensive.\n")["words"] == 2)

    # MUTATION. Put the old pattern back and the markdown-link row must be counted again. If it
    # still passes, the three checks above are decorative.
    _saved = C.CATALOGUE_ROW
    try:
        C.CATALOGUE_ROW = re.compile(r"\s*[-*]\s*\[\[")
        check("mutant (wiki-link form only) counts the markdown row again",
              C.count("- **[A Title](a-title.md)** — one line about it\n")["emdash"] == 1)
        check("...while the wiki-link row is unaffected by the mutation",
              C.count("- [[Some Page]] — one line about it\n")["emdash"] == 0)
    finally:
        C.CATALOGUE_ROW = _saved
    check("the real pattern is restored after the mutation",
          C.count("- **[A Title](a-title.md)** — one line about it\n")["emdash"] == 0)

    # A heading is a label, not a sentence. The house log header is `# Log — 2026-09-16`, so
    # under the old counting EVERY new day file failed the ratchet on its own template, one
    # em dash, forever. A gate that fires on the act of starting a page teaches people to
    # baseline. Added 2026-09-16, the first day a new log file tripped it.
    check("a heading's em dash is not counted",
          C.count("# Log — 2026-09-16\n")["emdash"] == 0)
    check("...at any depth", C.count("#### A Section — and its label\n")["emdash"] == 0)
    check("...and an X-not-Y shape in a heading is not counted either",
          C.count("## This isn't just a rule, it's a paradigm\n")["xnoty"] == 0)
    # The guards. Headings are exempt from the SENTENCE rules only.
    check("a banned word in a heading is still counted",
          C.count("## Leveraging Robust Synergy\n")["words"] == 3,
          "bad writing is bad wherever it sits")
    check("an em dash in the body is still counted",
          C.count("# A heading\n\nA sentence — with a dash.\n")["emdash"] == 1)
    check("a hash inside a line is not a heading",
          C.count("The tag #hashtag — in prose.\n")["emdash"] == 1)
    # ...but the same words in the body ARE counted, or the exclusions above would be a hole.
    check("the same words in the body are counted",
          C.count("This is a robust and comprehensive tapestry.")["words"] == 3)
    check("an em dash in the body is counted",
          C.count("a sentence — with a dash")["emdash"] == 1)

    # --- the ratchet ---------------------------------------------------------------------
    base = {"wiki/a.md": {"words": 3, "phrases": 0, "xnoty": 1, "emdash": 10}}
    same = {"wiki/a.md": {"words": 3, "phrases": 0, "xnoty": 1, "emdash": 10}}
    risen, appeared, fallen = C.compare(same, base)
    check("no change is not a failure", not risen and not appeared)

    worse = {"wiki/a.md": {"words": 4, "phrases": 0, "xnoty": 1, "emdash": 10}}
    risen, appeared, _ = C.compare(worse, base)
    check("a rise is caught", len(risen) == 1 and "words" in risen[0][1])

    better = {"wiki/a.md": {"words": 1, "phrases": 0, "xnoty": 0, "emdash": 4}}
    risen, appeared, fallen = C.compare(better, base)
    check("a fall is never a failure", not risen and not appeared and fallen == ["wiki/a.md"])

    fresh = dict(base, **{"wiki/new.md": {"words": 1, "phrases": 0, "xnoty": 0, "emdash": 0}})
    risen, appeared, _ = C.compare(fresh, base)
    check("a new file with findings is caught", [p for p, _ in appeared] == ["wiki/new.md"])

    clean = dict(base)
    risen, appeared, _ = C.compare(clean, base)
    check("a new CLEAN file is not reported at all", not appeared,
          "scan() never records a file with no findings")

    # --- the command ---------------------------------------------------------------------
    r = subprocess.run([sys.executable, str(HERE / "check_prose.py"), "--update-baseline"],
                       capture_output=True, text=True)
    check("--update-baseline without a reason is refused", r.returncode == 2)

    r = subprocess.run([sys.executable, str(HERE / "check_prose.py"), "--check"],
                       capture_output=True, text=True)
    check("--check passes on this repo as it stands", r.returncode == 0,
          (r.stdout or "").strip().splitlines()[-1:] or "")

    r = subprocess.run([sys.executable, str(HERE / "check_prose.py")],
                       capture_output=True, text=True)
    check("a plain run never fails the build", r.returncode == 0)

    # The baseline must be readable and must carry its reason, or it is an exemption list.
    d = json.loads((HERE / "prose-baseline.json").read_text(encoding="utf-8"))
    check("the baseline records why it was set", bool(d.get("reason")))
    check("the baseline carries totals", set(d.get("totals", {})) == set(C.CATEGORIES))

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
