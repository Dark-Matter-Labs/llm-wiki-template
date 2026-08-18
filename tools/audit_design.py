#!/usr/bin/env python3
"""
audit_design.py — audit published pages against the house design standard.

Checks the mechanical parts of the standard set out in `.impeccable.md` and the
`publish-web` skill. It is deliberately conservative: everything it reports is a fact
about the markup, not a judgement about the design.

**It cannot replace looking at the page.** Monotony, rhythm, hierarchy and the AI-slop
test need eyes on a screenshot. This tool finds the things that are cheap to find, so
that human attention goes to the things that aren't.

Usage:
  python3 tools/audit_design.py                 # summary
  python3 tools/audit_design.py --verbose       # every finding, per page
  python3 tools/audit_design.py --check         # exit 1 if any ERROR-level finding
"""

import argparse
import glob
import os
import re
import sys
from collections import Counter, defaultdict

DOCS = "docs"
LIGHT, DARK = "assets/xco.css", "assets/xco-dusk.css"

# AI-slop tells from impeccable:frontend-design that are detectable in source.
SLOP = [
    # backdrop-filter only. A plain `filter: blur()` is usually depth-of-field on a
    # diagram element, which is legitimate — matching it produced false positives.
    ("glassmorphism", r"backdrop-filter\s*:"),
    ("gradient text", r"background-clip:\s*text|-webkit-background-clip:\s*text"),
    ("neon glow", r"box-shadow:[^;]*0\s+0\s+\d+px[^;]*(#0ff|cyan|magenta)"),
    ("centred body text", r"body\s*\{[^}]*text-align:\s*center"),
    ("rounded card + drop shadow", r"border-radius:\s*\d+px[^;]*;[^}]*box-shadow:\s*0\s+\d+px\s+\d+px"),
]

SEV_ERROR, SEV_WARN, SEV_INFO = "ERROR", "WARN", "INFO"


def audit_page(path):
    """Return a list of (severity, code, detail) for one page."""
    name = os.path.basename(path)
    s = open(path, encoding="utf-8", errors="ignore").read()
    out = []

    light, dark = LIGHT in s, DARK in s

    # --- register discipline ------------------------------------------------
    if light and dark:
        out.append((SEV_ERROR, "register-mixed",
                    "links both stylesheets — one register per page"))
    elif not light and not dark:
        out.append((SEV_INFO, "register-none",
                    "uses neither shared stylesheet (bespoke page)"))

    # --- accessibility gates (WCAG 2.2 AA is a shipping gate) ---------------
    if "og:title" not in s:
        out.append((SEV_ERROR, "no-link-preview", "no og:title — shared link renders bare"))
    if "og:image" not in s:
        out.append((SEV_ERROR, "no-og-image", "no og:image"))
    # `outline: none` is only a defect when nothing replaces it. Suppressing the default
    # outline and then styling :focus-visible with a border/background/shadow is a correct,
    # common pattern — flagging it as an error sends people to "fix" working pages and
    # makes them worse. So: error only when no :focus-visible rule supplies an indicator.
    if re.search(r"outline:\s*(none|0)\b", s):
        replacement = re.search(
            r":focus-visible[^{]*\{[^}]*(outline\s*:\s*(?!none|0)|border[-a-z]*\s*:|"
            r"background[-a-z]*\s*:|box-shadow\s*:)", s, re.I)
        if replacement:
            out.append((SEV_INFO, "focus-custom",
                        "suppresses the default outline but styles :focus-visible — verify by eye"))
        else:
            out.append((SEV_ERROR, "focus-suppressed",
                        "outline:none with no :focus-visible replacement — no visible focus"))
    if s.count("<h1") > 1:
        out.append((SEV_WARN, "multiple-h1", f"{s.count('<h1')} h1 elements"))
    if s.count("<main") > 1:
        out.append((SEV_ERROR, "multiple-main", f"{s.count('<main')} main landmarks — invalid"))
    # Resolve the skip link's ACTUAL href rather than assuming it points at #main.
    # A page is free to name its landmark anything; what matters is that the target
    # exists. Hardcoding the id reported a working skip link on a perfectly good page
    # as broken, which would have blocked its deploy.
    m = re.search(r'class="skip-link"[^>]*href="#([^"]+)"', s) or \
        re.search(r'href="#([^"]+)"[^>]*class="skip-link"', s)
    if m:
        target = m.group(1)
        if not re.search(rf'id="{re.escape(target)}"', s):
            out.append((SEV_ERROR, "skip-target-missing",
                        f'skip link points at #{target}, which no element has'))
    elif 'class="skip-link"' in s:
        out.append((SEV_ERROR, "skip-target-missing", "skip link has no href"))
    if re.search(r"<table", s) and "scope=" not in s:
        out.append((SEV_WARN, "table-no-scope", "table without th scope"))
    if 'target="_blank"' in s:
        out.append((SEV_WARN, "new-tab", "opens a new tab — steals the back button"))

    # --- colour discipline ---------------------------------------------------
    # Orange as text on the light register fails AA (2.60:1). Structure use is fine.
    if light:
        for m in re.finditer(r"color:\s*(#F27F3D|var\(--midtone\))(?!\w)", s, re.I):
            frag = s[max(0, m.start() - 90):m.start()]
            if "dark-card" not in frag and "footer" not in frag and "slide-dark" not in frag:
                out.append((SEV_WARN, "orange-text-on-paper",
                            "orange used as text colour on the light register (2.60:1)"))
                break
    if re.search(r"(background|color)\s*:\s*#fff(f{3})?\b", s, re.I):
        out.append((SEV_INFO, "pure-white", "hardcodes pure #FFF rather than the tinted paper"))

    # --- rhythm / monotony ---------------------------------------------------
    grids = re.findall(r'class="aside-grid([^"]*)"', s)
    if len(grids) >= 3 and len(set(g.strip() for g in grids)) == 1:
        out.append((SEV_WARN, "grid-monotony",
                    f"{len(grids)} identical card grids — the 'identical card grids' failure"))
    # long sticky section labels wrap badly in the narrow margin column
    for m in re.finditer(r'class="section-label"[^>]*>(.*?)<', s, re.S):
        words = len(re.sub(r"<[^>]+>", "", m.group(1)).split())
        if words > 4:
            out.append((SEV_WARN, "long-section-label", f"section label is {words} words (max 3)"))
            break

    # --- AI-slop tells -------------------------------------------------------
    for label, pat in SLOP:
        if re.search(pat, s, re.I):
            out.append((SEV_WARN, "slop", label))

    return name, out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit published pages against the design standard.")
    ap.add_argument("--docs", default=DOCS)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--check", action="store_true", help="exit 1 on any ERROR finding")
    args = ap.parse_args(argv)

    pages = sorted(p for p in glob.glob(os.path.join(args.docs, "*.html"))
                   if os.path.basename(p) != "index.html")
    if not os.path.isdir(args.docs):
        print(f"error: no {args.docs!r} directory (cwd is {os.getcwd()}).\n"
              f"       Run from the repo root: python3 tools/audit_design.py", file=sys.stderr)
        return 2
    if not pages:
        print(f"no published pages under {args.docs}/ yet — nothing to audit.")
        return 0

    counts = Counter()
    by_code = defaultdict(list)
    for p in pages:
        name, findings = audit_page(p)
        for sev, code, detail in findings:
            counts[sev] += 1
            by_code[(sev, code)].append((name, detail))

    print(f"design audit — {len(pages)} published pages\n")
    for sev in (SEV_ERROR, SEV_WARN, SEV_INFO):
        rows = sorted(((c, v) for (s_, c), v in by_code.items() if s_ == sev),
                      key=lambda kv: -len(kv[1]))
        if not rows:
            continue
        print(f"{sev} ({counts[sev]})")
        for code, hits in rows:
            print(f"  {len(hits):>4}  {code:<22} {hits[0][1]}")
            if args.verbose:
                for n, _ in hits:
                    print(f"          {n}")
        print()

    if not counts:
        print("  clean — nothing mechanical to fix. Still run the eyes-on checks.")
    print("Note: monotony, hierarchy and the AI-slop test need a screenshot, not a regex.")
    return 1 if (args.check and counts[SEV_ERROR]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
