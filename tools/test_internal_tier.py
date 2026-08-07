#!/usr/bin/env python3
"""
test_internal_tier.py — prove the `internal` tier's two-sided invariant.

`internal` is the colleagues-only tier: it must reach the shared mirror (that is the
whole point of it) and must NEVER reach the open web (the Pages site or the public
JSON graph). Those are two different boundaries, so both directions are tested here.

Run: `python3 tools/test_internal_tier.py` (exit 0 = pass).

Distinctive, non-substring tokens are used so a leak can't hide behind a common word.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export          # noqa: E402
import export_shared   # noqa: E402

INT_SLUG = "zzq-internal-4c7e"
INT_TITLE = "Zzq Internal Working Note 4c7e"
INT_MARKER = "zzq-internal-body-marker-8891"

PRIV_SLUG = "zzq-priv-2b1d"
PRIV_TITLE = "Zzq Confidential Node 2b1d"

INTERNAL_PAGE = f"""---
type: concept
title: {INT_TITLE}
description: colleagues may read this; the open web may not
tags: [internal]
status: draft
visibility: internal
confidence: medium
timestamp: 2026-08-03
sources: []
---

# {INT_TITLE}

Working content {INT_MARKER} that colleagues should see but the public must not.
"""

PRIVATE_PAGE = f"""---
type: concept
title: {PRIV_TITLE}
description: nobody outside the source repo may read this
tags: [secret]
status: draft
visibility: private
confidence: low
timestamp: 2026-08-03
sources: []
---

# {PRIV_TITLE}

Never leaves the repo.
"""

PUBLIC_PAGE = f"""---
type: concept
title: Zzq Public Page 9k2
description: fully public
tags: [open]
status: reviewed
visibility: public
confidence: high
timestamp: 2026-08-03
sources: []
---

# Zzq Public Page 9k2

Links to [[{INT_TITLE}]] and to [[{PRIV_TITLE}]].
"""


def _write(d, name, text):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write(text)


def run():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        wiki = os.path.join(tmp, "wiki")
        os.makedirs(wiki)
        _write(wiki, INT_SLUG + ".md", INTERNAL_PAGE)
        _write(wiki, PRIV_SLUG + ".md", PRIVATE_PAGE)
        _write(wiki, "zzq-public-9k2.md", PUBLIC_PAGE)

        nodes, t2s = export.build_nodes(wiki)

        # ---- 1. the WEB export must hide internal AND private ----
        web, _ = export.make_public(nodes, t2s)          # default = HIDE_FROM_WEB
        web_blob = "\n".join(n["title"] + n["body"] for n in web.values())
        if INT_SLUG in web:
            failures.append("internal page is present as a node in the web export")
        if PRIV_SLUG in web:
            failures.append("private page is present as a node in the web export")
        if INT_TITLE in web_blob:
            failures.append("internal TITLE leaked into the web export")
        if INT_MARKER in web_blob:
            failures.append("internal BODY leaked into the web export")
        if PRIV_TITLE in web_blob:
            failures.append("private title leaked into the web export")
        if "[redacted]" not in web_blob:
            failures.append("links to hidden pages were not redacted in the web export")

        # ---- 2. the SHARED mirror must include internal, exclude private ----
        shared, _ = export.make_public(nodes, t2s, hide=export.HIDE_FROM_SHARED)
        sh_blob = "\n".join(n["title"] + n["body"] for n in shared.values())
        if INT_SLUG not in shared:
            failures.append("internal page is MISSING from the shared mirror "
                            "(the tier would be pointless)")
        if INT_MARKER not in sh_blob:
            failures.append("internal body missing from the shared mirror")
        if PRIV_SLUG in shared:
            failures.append("private page leaked into the shared mirror")
        if PRIV_TITLE in sh_blob:
            failures.append("private title leaked into the shared mirror")

        # ---- 3. end-to-end: the markdown the mirror actually ships ----
        out = os.path.join(tmp, "sharedout")
        export_shared.write_shared(wiki, out)
        files, blob = [], []
        for root, _d, fns in os.walk(out):
            for fn in fns:
                p = os.path.join(root, fn)
                files.append(p)
                with open(p, encoding="utf-8") as fh:
                    blob.append(fh.read())
        blob = "\n".join(blob)
        paths = "\n".join(files)
        if INT_SLUG not in paths:
            failures.append("internal page not written to the shared markdown output")
        if PRIV_SLUG in paths or PRIV_TITLE in blob:
            failures.append("private page reached the shared markdown output")

        # ---- 4. the tier is accepted by schema validation ----
        if export.validate(wiki):
            failures.append(f"schema validation rejected the fixture: {export.validate(wiki)}")

    if failures:
        print("FAIL — internal-tier invariant broken:")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS — internal tier: reaches the colleague mirror, never the open web "
          "(private excluded from both; links redacted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
