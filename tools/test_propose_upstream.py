#!/usr/bin/env python3
"""
test_propose_upstream.py — the properties that make an up-flow trustworthy.

Two failure modes matter more than the happy path.

The first is **proposing noise**. Without a merge base, "differs from the source" cannot be told
apart from "the source moved on", and every sibling would appear to have opinions it does not
have. A tool that reports thirty-seven proposals on a freshly synced repo gets ignored within a
day, and then the real one is invisible too.

The second is **sending without asking**. `contribute.py` stages and stops for the same reason
this does: nine repositories is too many for one process to write to unattended. The test asserts
the absence of a push, which is the kind of property that only stays true if something checks it.

  python3 tools/test_propose_upstream.py
"""

import hashlib
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import propose_upstream as pu       # noqa: E402

FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def build(tmp, files, shared, synced_as=None, source="src-wiki", name="sib-wiki"):
    """A sibling wiki on disk.

    files:     {relpath: current content}
    shared:    the shared layer as the manifest records it
    synced_as: {relpath: content the last sync wrote}. None means no state file at all.
    """
    root = pathlib.Path(tmp) / name
    (root / "design").mkdir(parents=True)
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    (root / "design" / "shared-layer.json").write_text(
        json.dumps({"source": source, "shared": list(shared)}), encoding="utf-8")
    if synced_as is not None:
        written = {r: hashlib.sha256(c.encode()).hexdigest() for r, c in synced_as.items()}
        (root / "design" / ".sync-state.json").write_text(
            json.dumps({"written": written}), encoding="utf-8")
    pu.ROOT = root
    return root


def main():
    print("propose_upstream — carry a local improvement back, and nothing else\n")

    with tempfile.TemporaryDirectory() as t:
        build(t, {"tools/a.py": "improved"}, ["tools/a.py"], synced_as={"tools/a.py": "original"})
        check("a changed shared file is proposable", pu.changed() == ["tools/a.py"])

    with tempfile.TemporaryDirectory() as t:
        build(t, {"tools/a.py": "original"}, ["tools/a.py"], synced_as={"tools/a.py": "original"})
        check("an untouched shared file is not", pu.changed() == [])

    with tempfile.TemporaryDirectory() as t:
        build(t, {"tools/a.py": "x", "tools/local.py": "changed"}, ["tools/a.py"],
              synced_as={"tools/a.py": "x", "tools/local.py": "original"})
        check("a local file outside the shared layer is nobody else's business",
              pu.changed() == [],
              "it differs and has a base entry — only shared-layer membership excludes it")

    with tempfile.TemporaryDirectory() as t:
        # The noise case: no merge base, so every difference looks like a local opinion.
        build(t, {"tools/a.py": "whatever"}, ["tools/a.py"], synced_as=None)
        check("with no merge base, nothing is proposed rather than everything",
              pu.changed() == [] and pu.main([]) == 0,
              "it must explain, not guess")

    with tempfile.TemporaryDirectory() as t:
        # A file in the shared list the sync has never written here (added upstream since).
        build(t, {"tools/a.py": "x"}, ["tools/a.py", "tools/new.py"], synced_as={"tools/a.py": "x"})
        check("a shared file this repo never received is not a local change",
              pu.changed() == [], "it is behind, not ahead")

    with tempfile.TemporaryDirectory() as t:
        build(t, {"tools/a.py": "improved"}, ["tools/a.py"],
              synced_as={"tools/a.py": "original"}, source="sib-wiki", name="sib-wiki")
        out = pathlib.Path(t) / "self-bundle"
        check("run inside the source wiki, it declines instead of proposing to itself",
              pu.main(["--stage", "--by", "A Person", "--out", str(out)]) == 0
              and not out.exists(),
              "the source has no upstream; staging one would be a bundle addressed to nobody")

    with tempfile.TemporaryDirectory() as t:
        root = build(t, {"tools/a.py": "improved"}, ["tools/a.py"],
                     synced_as={"tools/a.py": "original"})
        out = pathlib.Path(t) / "bundle"
        check("staging without --by is refused", pu.main(["--stage", "--out", str(out)]) == 1,
              "provenance is stamped, never invented")
        check("nothing is written when it is refused", not out.exists())

        rc = pu.main(["--stage", "--by", "A Person", "--out", str(out)])
        body = (out / "PROPOSAL.md").read_text()
        check("staging writes the bundle", rc == 0 and (out / "files" / "tools" / "a.py").is_file())
        check("the bundle carries the file's actual content",
              (out / "files" / "tools" / "a.py").read_text() == "improved")
        check("the bundle names who proposed it and where from",
              "A Person" in body and "sib-wiki" in body and "src-wiki" in body)
        check("the bundle says the source was not reachable rather than faking a diff",
              "no diff" in body or "```diff" in body)
        check("staging does not touch the working tree it is proposing from",
              (root / "tools" / "a.py").read_text() == "improved")

        # Re-staging must not accumulate stale files from a previous run.
        (root / "tools" / "a.py").write_text("improved again", encoding="utf-8")
        pu.main(["--stage", "--by", "A Person", "--out", str(out)])
        check("re-staging replaces the bundle rather than layering on it",
              (out / "files" / "tools" / "a.py").read_text() == "improved again")

    # Read the code, not the prose: an earlier version of this test matched the module's own
    # docstring saying it does not push, and would have passed a module that did.
    import ast
    tree = ast.parse(pathlib.Path(pu.__file__).read_text())
    argv = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            if "subprocess" in fn or fn in ("_sh", "os.system", "os.popen"):
                argv += [a.value for a in node.args if isinstance(a, ast.Constant)
                         and isinstance(a.value, str)]
    check("it cannot push, and does not open a PR",
          not any(w in argv for w in ("push", "gh")) and "gh" not in argv,
          f"the consent loop is the point; it runs {argv}")
    check("every command it can run is read-only",
          set(argv) <= {"git", "rev-parse", "--short", "HEAD", "status", "--porcelain"},
          f"runs {sorted(set(argv))}")

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
