#!/usr/bin/env python3
"""
test_contribute.py — prove the flow up to the commons cannot leak, and cannot lie.

Two classes of failure this guards:

  * **Leaking** — a private page, a CRM page, a private page's *title* hidden in a YAML
    comment, or a link to one, crossing into a wider group.
  * **Lying** — provenance that was invented rather than stamped, or a validation level
    carried across a group boundary so the commons inherits a consensus it was never
    party to.

Usage:  python3 tools/test_contribute.py
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contribute as C  # noqa: E402


PAGE = """---
type: concept
title: {title}
description: {desc}
tags: [t]
status: draft
visibility: {vis}
confidence: medium
validation: {val}
timestamp: 2026-08-12
sources: []
{extra}---

{body}
"""


def write(root, slug, title, vis="internal", val="machine",
          desc="A description.", body="Body text.", extra=""):
    path = os.path.join(root, slug + ".md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PAGE.format(title=title, desc=desc, vis=vis, val=val,
                             extra=extra, body=body))


def check_topology(check):
    """The second commons.

    A spoke may now contribute to more than one, and the tool must refuse to pick.
    Contributing to the wrong commons publishes to the wrong audience, and the remedy
    afterwards is a deletion request, not a revert.
    """
    import os as _os
    import contribute as c

    one = {"role": "spoke", "contributes_to": ["xco-team-wiki"]}
    two = {"role": "spoke", "contributes_to": ["xco-team-wiki", "learning-system-wiki"]}
    none_ = {"role": "commons", "contributes_to": []}

    name, err = c.resolve_commons(None, one)
    check("one declared target resolves without --to",
          name == "xco-team-wiki" and not err, f"got {name!r} / {err!r}")

    name, err = c.resolve_commons(None, two)
    check("two targets REFUSE to be guessed",
          name is None and bool(err) and "--to" in (err or ""), f"got {name!r}")

    name, err = c.resolve_commons("learning-system-wiki", two)
    check("an explicit --to resolves",
          name == "learning-system-wiki" and not err, f"got {name!r} / {err!r}")

    name, err = c.resolve_commons("some-other-wiki", two)
    check("a target that is not declared is refused",
          name is None and bool(err), f"got {name!r}")

    name, err = c.resolve_commons(None, none_)
    check("a commons that contributes nowhere is refused",
          name is None and bool(err), "a top-level commons has nothing above it")

    # The cache lookup must still find the legacy flat path, or every existing spoke
    # silently loses its collision check the day it declares a topology.
    paths = c.commons_cache_paths("xco-team-wiki")
    check("per-commons cache path is preferred",
          paths[0].endswith(_os.path.join("xco-team-wiki", "export", "wiki.shared.json")),
          paths[0])
    check("legacy flat cache path is still a fallback",
          _os.path.join(".commons", "export", "wiki.shared.json") in paths, str(paths))


def main():
    failures = []

    def check(name, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    tmp = tempfile.mkdtemp()
    wiki = os.path.join(tmp, "wiki")
    os.makedirs(wiki)
    try:
        write(wiki, "secret", "The Secret Position", vis="private")
        write(wiki, "shareable", "A Shareable Concept", vis="internal",
              body="Refers to [[The Secret Position]] and to [[Another Shared]].")
        write(wiki, "another-shared", "Another Shared", vis="internal")
        write(wiki, "crm/contact-x", "Contact X", vis="private")
        write(wiki, "peer-page", "A Peer Validated Page", vis="internal", val="peer")
        write(wiki, "coll-page", "A Collectively Validated Page", vis="internal", val="collective")
        write(wiki, "self-page", "A Self Validated Page", vis="internal", val="self")
        # a private title hidden in a YAML comment — the reason frontmatter is rebuilt
        write(wiki, "sneaky", "Sneaky", vis="internal",
              extra="# see also: The Secret Position\n")

        def build(slugs):
            return C.build_bundle(wiki, slugs, "tester", "abc1234")

        # --- refusals -------------------------------------------------------
        try:
            build(["secret"]); ok = False; why = "no error raised"
        except ValueError as e:
            ok, why = "private" in str(e), str(e)
        check("a private page is refused", ok, why)

        try:
            build(["crm/contact-x"]); ok = False; why = "no error raised"
        except ValueError as e:
            ok, why = "CRM" in str(e), str(e)
        check("a CRM page is refused", ok, why)

        # --- the happy path --------------------------------------------------
        b = build(["shareable"])
        text = b["wiki/shareable.md"]
        check("an internal page is staged", "wiki/shareable.md" in b)

        # --- leaking ---------------------------------------------------------
        check("the private page's title never appears",
              "The Secret Position" not in text,
              text.split("\n\n")[1][:90] if "\n\n" in text else "")
        check("the link to the private page is redacted",
              "[[The Secret Position]]" not in text)
        check("the link to a shared page survives",
              "[[Another Shared]]" in text)

        sneaky = build(["sneaky"])["wiki/sneaky.md"]
        check("a private title hidden in a YAML comment is dropped",
              "The Secret Position" not in sneaky,
              "frontmatter is rebuilt from a whitelist, never copied")

        # --- lying -----------------------------------------------------------
        # Assert against the DERIVED origin, not a literal: origin now comes from the
        # git remote, so a hardcoded name only passes in the one repo it was written in.
        check("provenance is stamped",
              "contributed_by: tester" in text and f"origin: {C.ORIGIN}" in text
              and "origin_rev: abc1234" in text,
              f"origin resolved to {C.ORIGIN!r}")

        def val_of(slug, page_slug=None):
            t = build([slug])["wiki/" + (page_slug or slug) + ".md"]
            for line in t.split("\n"):
                if line.startswith("validation:"):
                    return line.split(":", 1)[1].strip()
            return None

        check("peer is re-based to self (the commons must re-earn it)",
              val_of("peer-page") == "self", f"got {val_of('peer-page')}")
        check("collective is re-based to self",
              val_of("coll-page") == "self", f"got {val_of('coll-page')}")
        check("self travels unchanged (the author still stands behind it)",
              val_of("self-page") == "self", f"got {val_of('self-page')}")
        check("machine stays machine",
              val_of("another-shared") == "machine", f"got {val_of('another-shared')}")

        # --- collision with the commons ---------------------------------------
        # 577 of 595 contributable pages already existed in the commons when this was
        # found by rehearsing the loop. A silent overwrite would lose whatever the
        # commons had done to its copy — the two-canons failure, at the moment of
        # contribution, invisible in the staged bundle.
        import json as _json
        cache_dir = os.path.join(tmp, ".commons", "export")
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "wiki.shared.json"), "w", encoding="utf-8") as fh:
            _json.dump({"nodes": [{"title": "A Shareable Concept"}]}, fh)
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp)
            _t, hits = C.check_collisions("wiki", {"shareable"}, "xco-team-wiki")
            check("a page already in the commons is detected as a collision",
                  len(hits) == 1 and hits[0][0] == "shareable", f"hits={hits}")
            _t2, hits2 = C.check_collisions("wiki", {"another-shared"}, "xco-team-wiki")
            check("a page the commons does not have is not a collision",
                  hits2 == [], f"hits={hits2}")
        finally:
            os.chdir(old_cwd)

        # with no cache, it must say it cannot check rather than imply all-clear
        old_cwd = os.getcwd()
        try:
            os.chdir(tempfile.mkdtemp())
            os.makedirs("wiki", exist_ok=True)
            t3, hits3 = C.check_collisions("wiki", set(), "xco-team-wiki")
            check("with no commons cache it reports unknown, not clear",
                  t3 is None, f"titles={t3}")
        finally:
            os.chdir(old_cwd)

        # --- nothing escapes on its own --------------------------------------
        check("build_bundle writes nothing to disk by itself",
              not os.path.exists(os.path.join(tmp, "contrib")),
              "staging is the caller's explicit step")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    check_topology(check)

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("All contribute checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
