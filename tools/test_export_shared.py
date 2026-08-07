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


if __name__ == "__main__":
    raise SystemExit(run())
