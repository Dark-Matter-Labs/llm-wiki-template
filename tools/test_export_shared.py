#!/usr/bin/env python3
"""
test_export_shared.py — prove the shared markdown export leaks nothing private.

Runs with stdlib only: `python tools/test_export_shared.py` (exit 0 = pass).

The fixture uses deliberately unique, non-substring tokens for the private page's
slug and title (zzq-priv-*, "Zzq Confidential *") so a leak can't hide behind a
common word.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_shared  # noqa: E402

PRIVATE_SLUG = "zzq-priv-9f3a"
PRIVATE_TITLE = "Zzq Confidential Node 9f3a"
PRIVATE_PARENT_TITLE = "Zzq Confidential Parent 7b2c"

PRIVATE_PAGE = f"""---
type: concept
title: {PRIVATE_TITLE}
description: secret internal thing that must never leave
tags: [secret]
status: draft
visibility: private
confidence: low
timestamp: 2026-07-15
sources: []
---

# {PRIVATE_TITLE}

Highly sensitive body text zzq-body-marker-1234.
"""

PRIVATE_PARENT = f"""---
type: concept
title: {PRIVATE_PARENT_TITLE}
description: private parent
tags: [secret]
status: draft
visibility: private
confidence: low
timestamp: 2026-07-15
sources: []
---

# {PRIVATE_PARENT_TITLE}
"""

# Public page that links to the private one and nests under a private parent.
# The third link is deliberately SPLIT ACROSS A NEWLINE — a line-wrapped private
# link must still be redacted (regression guard for the whitespace-normalization fix).
PUBLIC_LINKER = f"""---
type: concept
title: Public Linker Page
description: a shareable page that references a private one
tags: [open]
status: reviewed
visibility: public
confidence: high
timestamp: 2026-07-15
parent: {PRIVATE_PARENT_TITLE}
# hidden note: grounds on [[{PRIVATE_TITLE}]] and {PRIVATE_PARENT_TITLE}
sources: []
---

# Public Linker Page

This links to [[{PRIVATE_TITLE}]] and also [[{PRIVATE_TITLE}|a friendly alias]].
A wrapped reference to [[Zzq Confidential
Node 9f3a]] must also be redacted.
It also links to [[Public Standalone Page]] which is fine.
"""

PUBLIC_STANDALONE = """---
type: summary
title: Public Standalone Page
description: totally shareable
tags: [open]
status: reviewed
visibility: unlisted
confidence: medium
timestamp: 2026-07-15
sources: [raw/example.md]
---

# Public Standalone Page

Nothing sensitive here.
"""


def _write(d, name, text):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write(text)


def run():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        out = os.path.join(tmp, "shared")
        os.makedirs(wiki)
        _write(wiki, PRIVATE_SLUG + ".md", PRIVATE_PAGE)
        _write(wiki, "zzq-priv-parent-7b2c.md", PRIVATE_PARENT)
        _write(wiki, "public-linker.md", PUBLIC_LINKER)
        _write(wiki, "public-standalone.md", PUBLIC_STANDALONE)

        export_shared.write_shared(wiki, out)

        # Collect every output file path + content.
        all_text = []
        all_paths = []
        for root, _d, files in os.walk(out):
            for fn in files:
                p = os.path.join(root, fn)
                all_paths.append(p)
                with open(p, encoding="utf-8") as fh:
                    all_text.append(fh.read())
        blob = "\n".join(all_text)
        paths_blob = "\n".join(all_paths)

        failures = []

        # 1. No file named after the private slug/parent.
        if PRIVATE_SLUG in paths_blob:
            failures.append("private slug appears in an output filename")
        if "zzq-priv-parent" in paths_blob:
            failures.append("private parent slug appears in an output filename")

        # 2. Private titles never appear anywhere (filenames or content).
        if PRIVATE_TITLE in blob:
            failures.append("PRIVATE_TITLE leaked into shared output")
        if PRIVATE_PARENT_TITLE in blob:
            failures.append("PRIVATE_PARENT_TITLE leaked into shared output")

        # 3. Private body marker never appears.
        if "zzq-body-marker-1234" in blob:
            failures.append("private body text leaked")

        # 4. The bare link is redacted; the aliased link degrades to its alias text.
        linker = next((t for p, t in zip(all_paths, all_text)
                       if p.endswith("public-linker.md")), "")
        if "[[" in linker and PRIVATE_TITLE in linker:
            failures.append("private wikilink survived in public linker body")
        if "[redacted]" not in linker:
            failures.append("bare private link was not redacted to [redacted]")
        if "a friendly alias" not in linker:
            failures.append("aliased private link did not degrade to its display text")
        if "parent:" in linker:
            failures.append("private parent frontmatter survived on public page")

        # 5. Public pages ARE present.
        if not any(p.endswith("public-standalone.md") for p in all_paths):
            failures.append("public standalone page missing from shared output")
        if "Public Standalone Page" not in blob:
            failures.append("public content missing")

        # 6. Generated index exists and lists only shared pages.
        idx = next((t for p, t in zip(all_paths, all_text)
                    if p.endswith(os.path.join("wiki", "index.md"))), "")
        if not idx:
            failures.append("generated index.md missing")
        if PRIVATE_TITLE in idx or PRIVATE_PARENT_TITLE in idx:
            failures.append("private title leaked into generated index")

        if failures:
            print("FAIL — shared export leaked or misbehaved:")
            for f in failures:
                print("  -", f)
            return 1
        print("PASS — shared export leaks nothing private "
              "(2 private pages excluded, links redacted, parent dropped, index clean)")
        return 0


def run_empty():
    """A wiki with nothing shareable must still produce a valid, empty mirror.

    This is not a hypothetical. `fang-llm-wiki` was created on 2026-08-26 with only
    scaffolding, and its "Export shared mirror" workflow failed on every run for a week
    with FileNotFoundError: 'shared_out/wiki/index.md' -- because the out dir's wiki/
    was only ever created as a side effect of copying a shareable page, and there were
    none. The colleague mirror for that wiki has never existed.

    The failure mode is the worst shape available: it fires only on a brand-new wiki,
    which is exactly when nobody is watching the Actions tab.
    """
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        out = os.path.join(tmp, "shared")
        os.makedirs(wiki)
        # One page, private: shareable count is zero.
        _write(wiki, PRIVATE_SLUG + ".md", PRIVATE_PAGE)

        failures = []
        try:
            n = export_shared.write_shared(wiki, out)
        except Exception as e:  # noqa: BLE001 - the bug was an uncaught FileNotFoundError
            print(f"FAIL — empty corpus raised {type(e).__name__}: {e}")
            return 1

        if n != 0:
            failures.append(f"expected 0 shared files, got {n}")
        idx = os.path.join(out, "wiki", "index.md")
        if not os.path.isfile(idx):
            failures.append("no wiki/index.md written for an empty corpus")
        else:
            with open(idx, encoding="utf-8") as fh:
                body = fh.read()
            if PRIVATE_TITLE in body:
                failures.append("private title leaked into the empty index")
        if not os.path.isfile(os.path.join(out, "README.md")):
            failures.append("no README.md written for an empty corpus")

        if failures:
            print("FAIL — empty corpus mirror is malformed:")
            for f in failures:
                print("  -", f)
            return 1
        print("PASS — a wiki with nothing shareable still yields a valid empty mirror")
        return 0


COMMITMENT = """---
type: commitment
title: A Contracted Lead For Something
description: A commitment page carrying the full ledger field set.
tags: [ledger]
status: draft
visibility: internal
confidence: high
validation: machine
timestamp: 2026-09-02
commits_to: "A Real Public Goal"
resources: One contracted lead, starting next month.
until: Open-ended.
state: held
sources: []
---

The body.
"""

GOAL = """---
type: goal
title: A Real Public Goal
description: The goal the commitment above commits to.
tags: [ledger]
status: draft
visibility: public
confidence: high
validation: machine
timestamp: 2026-09-02
horizon: mid
sources: []
---

The goal body.
"""


def run_ledger():
    """A contributed commitment must arrive with its ledger fields intact.

    The whitelist predated the goal/commitment schema, so commits_to, resources, until
    and state were silently dropped on the way into a commons — and the RECEIVING repo's
    schema check requires commits_to and state on a commitment. A contribution would
    therefore land red, which is a large part of why the ledger had never moved off a
    personal wiki. Dropping a field is invisible; landing red is not, but only after the
    fact and in someone else's repository.
    """
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        out = os.path.join(tmp, "shared")
        os.makedirs(wiki)
        _write(wiki, "a-real-public-goal.md", GOAL)
        _write(wiki, "a-contracted-lead.md", COMMITMENT)
        export_shared.write_shared(wiki, out)

        with open(os.path.join(out, "wiki", "a-contracted-lead.md"), encoding="utf-8") as fh:
            got = fh.read()

        failures = []
        for field, value in [("commits_to", "A Real Public Goal"), ("state", "held"),
                             ("until", "Open-ended."),
                             ("resources", "One contracted lead, starting next month.")]:
            if f"{field}:" not in got:
                failures.append(f"{field} dropped from the contributed commitment")
            elif value not in got:
                failures.append(f"{field} present but value mangled (wanted {value!r})")
        if "type: commitment" not in got:
            failures.append("type downgraded — the receiving ledger will not see this page")

        # The goal keeps its optional horizon; a page without ledger fields gains none.
        with open(os.path.join(out, "wiki", "a-real-public-goal.md"), encoding="utf-8") as fh:
            goal = fh.read()
        if "horizon: mid" not in goal:
            failures.append("goal lost its horizon")
        if "state:" in goal or "commits_to:" in goal:
            failures.append("ledger fields invented on a page that had none")

        if failures:
            print("FAIL — ledger fields do not survive contribution:")
            for f in failures:
                print("  -", f)
            return 1
        print("PASS — a contributed commitment keeps commits_to, resources, until and state")
        return 0


if __name__ == "__main__":
    # Every scenario runs, even after one fails. An `or` chain short-circuits, so the
    # first failure would hide the others and each CI run would surface one at a time.
    raise SystemExit(max(run(), run_empty(), run_ledger()))
