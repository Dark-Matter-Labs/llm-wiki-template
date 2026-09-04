#!/usr/bin/env python3
"""
test_wiki_context.py — the properties that keep a generated block honest.

The block exists because hand-copied guidance went stale in nine repos at once. So the properties
that matter are: it must say something DIFFERENT in a spoke and in a top commons (a commons has no
up-flow, and telling it to contribute would be telling it to do something impossible); it must
adapt to a corpus with enormous sources; it must never touch a line outside its own markers; and
--check must actually fail when the block drifts, because a generated block nobody checks is just a
hand-written one with extra steps.

  python3 tools/test_wiki_context.py
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_context as wc      # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def repo(tmp, fed, pages=3, sources=(), claude="# CLAUDE.md\n\nOpening prose.\n\n## Rules\n\nBe good.\n"):
    root = pathlib.Path(tmp)
    (root / "design").mkdir(parents=True, exist_ok=True)
    (root / "design" / "federation.json").write_text(json.dumps(fed), encoding="utf-8")
    (root / "wiki").mkdir(exist_ok=True)
    for i in range(pages):
        (root / "wiki" / f"p{i}.md").write_text("x", encoding="utf-8")
    (root / "raw").mkdir(exist_ok=True)
    for i, size in enumerate(sources):
        (root / "raw" / f"s{i}.md").write_text("x" * size, encoding="utf-8")
    (root / "CLAUDE.md").write_text(claude, encoding="utf-8")
    # Every wiki is a git repo, and the block counts what git TRACKS -- so a fixture that is not
    # a repo would test a state that cannot occur and would hide the CI-reproducibility property.
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    wc.ROOT = root
    return root


def main():
    print("wiki_context — generated, adapted, and checked\n")

    with tempfile.TemporaryDirectory() as t:
        repo(t, {"name": "michelle-llm-wiki", "role": "spoke",
                 "contributes_to": ["learning-system-wiki"]})
        b = wc.render()
        check("a spoke is told which commons it is connected to",
              "learning-system-wiki" in b and "connected to" in b)
        check("and told the connection runs both ways",
              "**Up:**" in b and "**Down:**" in b)
        check("and told what to do when the down-flow cache is empty",
              "sync_commons.py" in b, "a fresh checkout has none, which reads as broken")
        check("and told that what comes down is not merged", "not merged" in b.lower())

    with tempfile.TemporaryDirectory() as t:
        repo(t, {"name": "xco-team-wiki", "role": "commons", "contributes_to": []})
        b = wc.render()
        check("a TOP COMMONS is told nothing sits above it, not told to contribute",
              "Nothing sits above" in b and "**Up:**" not in b,
              "telling a top commons to contribute is telling it to do the impossible")
        check("and told that is correct rather than broken", "correct rather than broken" in b)

    with tempfile.TemporaryDirectory() as t:
        repo(t, {"name": "w", "role": "spoke", "contributes_to": ["c"]},
             sources=(50_000, 60_000, 1_000))
        b = wc.render()
        check("a corpus with huge sources gets the large-source discipline",
              "2 of those sources are over 40KB" in b and "do not read a large source" in b)
        check("and an ingest is told to take them in passes", "in passes" in b)

    with tempfile.TemporaryDirectory() as t:
        repo(t, {"name": "w", "role": "spoke", "contributes_to": ["c"]}, sources=(1_000, 2_000))
        b = wc.render()
        check("a corpus of small sources is told to read them whole",
              "read them whole" in b and "do not read a large source" not in b)

    with tempfile.TemporaryDirectory() as t:
        repo(t, {"name": "w", "role": "spoke", "contributes_to": ["c"]})
        b = wc.render()   # every wiki, whatever its shape, carries the retrieval discipline
        check("every wiki gets the same retrieval order",
              "search.py" in b and "Never load pages in order to decide which pages to load" in b)
        check("and is told to build the graph export when it is missing",
              "tools/export.py" in b, "it is gitignored, so a fresh checkout has no graph hop")

    with tempfile.TemporaryDirectory() as t:
        root = repo(t, {"name": "w", "role": "spoke", "contributes_to": ["c"]})
        before = (root / "CLAUDE.md").read_text()
        check("--check fails when the block is absent", wc.main(["--check"]) == 1)
        check("and --check changes nothing", (root / "CLAUDE.md").read_text() == before)

        wc.main([])
        text = (root / "CLAUDE.md").read_text()
        check("the block is inserted before the first section, not at the end",
              text.index(wc.START) < text.index("## Rules"))
        check("hand-written prose outside the markers survives",
              "Opening prose." in text and "Be good." in text)
        check("--check passes once generated", wc.main(["--check"]) == 0)

        # Drift: someone edits the generated block by hand.
        (root / "CLAUDE.md").write_text(text.replace("search.py", "grep"), encoding="utf-8")
        check("--check fails when the block has been hand-edited", wc.main(["--check"]) == 1)

        # Drift: the federation changes underneath it.
        wc.main([])
        (root / "design" / "federation.json").write_text(
            json.dumps({"name": "w", "role": "spoke", "contributes_to": ["c", "xco-team-wiki"]}),
            encoding="utf-8")
        check("--check fails when federation.json changes and the block does not",
              wc.main(["--check"]) == 1, "this is the drift the tool exists to catch")
        wc.main([])
        check("regenerating picks up the new commons",
              "xco-team-wiki" in (root / "CLAUDE.md").read_text())

    with tempfile.TemporaryDirectory() as t:
        # THE CI PROPERTY: a runner sees only what git tracks. If the block counted the working
        # directory, every wiki whose .gitignore excludes binary sources would generate a block
        # locally that can never match in CI -- which is exactly how this shipped red the first time.
        root = repo(t, {"name": "w", "role": "spoke", "contributes_to": ["c"]}, sources=(1_000,))
        (root / ".gitignore").write_text("raw/*.pdf\n", encoding="utf-8")
        (root / "raw" / "huge.pdf").write_bytes(b"x" * 90_000)     # ignored: must not be counted
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        b = wc.render()
        check("gitignored sources are invisible to the block, so CI and local agree",
              "1 source file(s)" in b and "over 40KB" not in b,
              "a 90KB ignored PDF must not appear")

    with tempfile.TemporaryDirectory() as t:
        root = repo(t, {"name": "w", "role": "spoke", "contributes_to": ["c"]})
        wc.main([]); once = (root / "CLAUDE.md").read_text()
        wc.main([]); twice = (root / "CLAUDE.md").read_text()
        check("running it twice changes nothing the second time", once == twice)

    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t); wc.ROOT = root
        (root / "design").mkdir()
        check("a repo with no CLAUDE.md is left alone rather than given one", wc.main([]) == 0)

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
