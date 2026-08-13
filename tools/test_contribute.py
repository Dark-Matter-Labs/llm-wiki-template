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
        check("provenance is stamped",
              "contributed_by: tester" in text and "origin: YOUR-WIKI" in text
              and "origin_rev: abc1234" in text)

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

        # --- nothing escapes on its own --------------------------------------
        check("build_bundle writes nothing to disk by itself",
              not os.path.exists(os.path.join(tmp, "contrib")),
              "staging is the caller's explicit step")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("All contribute checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
