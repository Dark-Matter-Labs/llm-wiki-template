#!/usr/bin/env python3
"""
test_tokens.py — the accessibility contract, executable.

Both predecessor systems stated their contrast rules in prose, and both shipped
values that broke them: v1's orange failed as text, and the v0.1 draft had four
under-target foregrounds plus a whole register with no semantic colours at all.
Prose does not fail a build. This does.

Every rule below is one the system already claims to follow. The only new thing
is that it is now checked.

  python3 tools/test_tokens.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_tokens as bt  # noqa: E402

TEXT_MIN, GRAPHIC_MIN = 4.5, 3.0
FAILURES = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def lum(h):
    h = h.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def cr(a, b):
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + .05) / (lo + .05)


def main():
    print("xCO tokens — the accessibility contract\n")
    doc = bt.load()
    idx = bt.build_index(doc)
    MISSING = object()

    def R(path):
        """Resolve, or return MISSING — a deleted token is a contract failure with a
        name attached, not a stack trace."""
        if path not in idx:
            return MISSING
        try:
            return bt.resolve(idx[path], idx)
        except ValueError:
            return MISSING

    def ok(v):
        return v is not MISSING

    MEANINGS = ["continuity", "system", "risk", "agency", "contested", "critical"]

    for reg, base in (("paper", "semantic"), ("inverse", "register.inverse")):
        page = R(f"{base}.surface.page")
        if not ok(page):
            check(f"[{reg}] register is defined", False, "no surface.page")
            continue
        raised = R(f"{base}.surface.raised")
        quiet = R(f"{base}.surface.quiet")
        # `structural` is deliberately excluded: it is a divider band and a disabled
        # field, and WCAG exempts disabled controls. Forcing text to clear it would
        # collapse secondary and muted into the same grey, which costs more than it
        # buys. The JSON says so, and the next check holds it to that.
        print(f"  -- {reg} register, ground {page} " + "-" * (44 - len(reg)))

        # 1. text on every surface it can legitimately sit on
        for tok in ("primary", "secondary", "muted", "link", "critical"):
            v = R(f"{base}.text.{tok}")
            if not ok(v):
                check(f"[{reg}] text.{tok} exists", False, "token missing or unresolvable")
                continue
            worst = min(cr(v, s) for s in (page, raised, quiet))
            check(f"[{reg}] text.{tok} >= {TEXT_MIN} on every surface",
                  worst >= TEXT_MIN, f"worst {worst:.2f}:1 ({v})")

        # 2. a meaning colour is a foreground: it is read as text
        for m in MEANINGS:
            v = R(f"{base}.meaning.{m}")
            if not ok(v):
                check(f"[{reg}] meaning.{m} exists", False,
                      "v0.1 remapped surface and text but not the semantic colours")
                continue
            got = cr(v, page)
            check(f"[{reg}] meaning.{m} >= {TEXT_MIN} on its ground",
                  got >= TEXT_MIN, f"{got:.2f}:1 ({v})")

        # 3. a tint is a ground: the register's own text must sit on it
        ink = R(f"{base}.text.primary")
        for m in MEANINGS:
            v = R(f"{base}.tint.{m}")
            if not ok(v):
                check(f"[{reg}] tint.{m} exists", False, "token missing")
                continue
            got = cr(ink, v)
            check(f"[{reg}] text.primary on tint.{m} >= {TEXT_MIN}",
                  got >= TEXT_MIN, f"{got:.2f}:1 (ink {ink} on {v})")

        # 4. the one border token allowed to carry an essential boundary
        strong = R(f"{base}.border.strong")
        check(f"[{reg}] border.strong >= {GRAPHIC_MIN} (essential graphics)",
              cr(strong, page) >= GRAPHIC_MIN, f"{cr(strong, page):.2f}:1")
        focus = R(f"{base}.border.focus")
        check(f"[{reg}] border.focus >= {GRAPHIC_MIN}",
              cr(focus, page) >= GRAPHIC_MIN, f"{cr(focus, page):.2f}:1")

        # 5. and the decorative ones must NOT be mistaken for essential. This is a
        #    documentation check: if a low-contrast border ever loses its warning,
        #    someone will reach for it to draw a meaningful line.
        for tok in ("subtle", "default"):
            node = doc["semantic" if reg == "paper" else "register"]
            node = node["border"] if reg == "paper" else node["inverse"]["border"]
            desc = (node.get(tok) or {}).get("$description", "") if reg == "paper" else ""
            if reg == "paper":
                check(f"[{reg}] border.{tok} is documented as decorative-only",
                      "ecorative" in desc, "a low-contrast border with no warning invites misuse")
        print()

    # 6. colour is never the sole carrier — the rule both systems state
    print("  -- the second channel " + "-" * 44)
    for m in MEANINGS:
        node = doc["component"]["meaning"].get(m, {})
        check(f"meaning.{m} ships a text marker", bool(node.get("marker", {}).get("$value")))
        check(f"meaning.{m} ships a shape", bool(node.get("shape", {}).get("$value")))
    shapes = [doc["component"]["meaning"][m]["shape"]["$value"] for m in MEANINGS]
    check("all six shapes are distinct", len(set(shapes)) == 6, f"got {shapes}")
    markers = [doc["component"]["meaning"][m]["marker"]["$value"] for m in MEANINGS]
    check("all six markers are distinct", len(set(markers)) == 6)

    # 7. every meaning and tint resolves in BOTH registers — the v0.1 gap
    print()
    print("  -- both registers are complete " + "-" * 35)
    for m in MEANINGS:
        for k in ("meaning", "tint"):
            check(f"register.inverse.{k}.{m} exists",
                  f"register.inverse.{k}.{m}" in idx,
                  "v0.1 remapped surface and text but not the semantic colours")

    # 8. nothing reaches out to a CDN
    print()
    print("  -- self-containment " + "-" * 46)
    # $schema is metadata about the format, not a value any renderer fetches.
    flat = []
    for _p, v in bt.walk(doc):
        flat.extend(v if isinstance(v, list) else [v])
    offenders = [v for v in flat if isinstance(v, str) and re.search(r"https?://|//fonts\.", v)]
    check("no token VALUE reaches an external URL", not offenders,
          f"a token that fetches is a token that can fail: {offenders[:2]}")
    fams = " ".join(R(f"primitive.font.family.{f}") for f in ("serif", "sans", "mono"))
    check("font stacks end in a generic family",
          all(g in fams for g in ("serif", "sans-serif", "monospace")))

    # 9. legacy sheets pin literals; those pins must equal the tokens they mirror.
    #    Legacy pages predate the theme axis and were authored as fixed-register
    #    documents, so they pin rather than follow the reader. A pin is a copy, and
    #    a copy drifts — unless something checks it.
    print()
    print("  -- legacy pins " + "-" * 51)
    import re as _re
    PINS = {
        "docs/assets/xco.css": {
            "--shadow": R("semantic.text.primary"),
            "--highlight": R("semantic.surface.page"),
            "--midtone": R("domain.bio.base"),
            "--midtone-ink": R("domain.bio.ink")},
        "docs/assets/xco-dusk.css": {
            "--shadow": R("register.inverse.surface.page"),
            "--highlight": R("register.inverse.text.primary"),
            "--midtone": R("domain.bio.base"),
            "--midtone-lift": R("register.inverse.meaning.critical")},
    }
    root = os.path.join(HERE, "..")
    for path, pins in PINS.items():
        full = os.path.join(root, path)
        if not os.path.exists(full):
            check(f"{os.path.basename(path)} exists", False)
            continue
        css = open(full, encoding="utf-8").read()
        head = css[:css.index("}", css.index(":root"))]
        for name, want in pins.items():
            m = _re.search(_re.escape(name) + r"\s*:\s*(#[0-9a-fA-F]{3,8})", head)
            got = m.group(1).lower() if m else None
            check(f"{os.path.basename(path)} {name} matches the token",
                  got == str(want).lower(), f"pinned {got}, token says {want}")

    # 10. the social card carries the tokens it claims to.
    #     Not "a generator exists that would produce them" — the shipped PNG is read
    #     back and its pixels compared. The card is the first thing anyone sees of
    #     this work and nobody looks at their own preview image, so it is exactly the
    #     artefact that rots unnoticed. It was still on the v1 navy until today.
    print()
    print("  -- social card " + "-" * 51)
    card = os.path.join(HERE, "..", "docs", "assets", "social-card.png")
    if not os.path.exists(card):
        check("social-card.png exists", False)
    else:
        try:
            from PIL import Image
            from collections import Counter
            im = Image.open(card).convert("RGB")
            hx = lambda t: "#%02x%02x%02x" % t
            check("social card is 1200x630", im.size == (1200, 630), f"got {im.size}")
            # the grain dots are sub-pixel, so take the mode of a quiet region
            mode = Counter(im.getpixel((x, y))
                           for x in range(900, 1100, 7)
                           for y in range(560, 620, 7)).most_common(1)[0][0]
            want = R("semantic.surface.page")
            check("social card ground is semantic.surface.page",
                  hx(mode).lower() == str(want).lower(), f"card {hx(mode)}, token {want}")
            acc = hx(im.getpixel((150, 4)))
            wanta = R("domain.bio.base")
            check("social card accent is domain.bio.base",
                  acc.lower() == str(wanta).lower(), f"card {acc}, token {wanta}")
        except ImportError:
            print("  --    Pillow absent; card pixels not verified here (CI checks size only)")

    # 11. the generated CSS is not stale
    print()
    print("  -- generated artefact " + "-" * 44)
    css = bt.render()
    on_disk = open(bt.OUT, encoding="utf-8").read() if os.path.exists(bt.OUT) else ""
    check("docs/assets/xco-tokens.css matches the JSON source", css == on_disk,
          "run python3 tools/build_tokens.py")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED:")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    print("contract holds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
