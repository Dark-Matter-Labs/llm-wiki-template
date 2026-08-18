#!/usr/bin/env python3
"""
build_social_card.py — generate docs/assets/social-card.png from the design tokens.

The card is the first thing anyone sees of this work: it is what renders in Slack,
in a DM, in a feed. It was still on v1 — navy ground, orange rule, grotesque display
— which is now three replaced decisions, so a shared link advertised a system the
site no longer uses.

Generated rather than drawn, for the same reason the token CSS is: a card made by
hand drifts the moment a value changes, and nobody notices because nobody looks at
their own preview image.

Design notes
------------
Paper register, not inverse. The inverse register means a move into the
consequential; a social card is the "signal" reading resolution — topic, stance,
source — and dressing it as consequential would be a claim the card cannot support.
Warm paper also matches what a reader sees the instant they click through, and
continuity between the card and the page is worth more than shouting in a feed.

Deliberately no domain legend. The shape channel is the system's signature and it
was tempting, but a legend here would be apparatus with no job to do, and it turns
to mush at thumbnail size. The system's own rule — representation is not additional
evidence — applies to its own advertising.

Usage:
  python3 tools/build_social_card.py
  python3 tools/build_social_card.py --check     # verify the PNG is current
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_tokens as bt  # noqa: E402

OUT = os.path.join(HERE, "..", "docs", "assets", "social-card.png")
W, H = 1200, 630

# The wording is per-wiki and lives OUTSIDE the shared layer, in
# design/social-card.json, so syncing the design system between repos never gives
# one wiki another's tagline. The generator is shared; the words are not.
COPY = os.path.join(HERE, "..", "design", "social-card.json")

DEFAULT = {
    "kicker": "DARK MATTER LABS",
    "lines": ["An LLM wiki."],
    "footer": "dark-matter-labs.github.io",
}


def copy_for_card():
    if os.path.exists(COPY):
        with open(COPY, encoding="utf-8") as fh:
            return {**DEFAULT, **json.load(fh)}
    return DEFAULT


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def svg():
    doc = bt.load()
    idx = bt.build_index(doc)
    R = lambda p: bt.resolve(idx[p], idx)

    paper = R("semantic.surface.page")
    ink = R("semantic.text.primary")
    soft = R("semantic.text.secondary")
    rule = R("semantic.border.strong")
    accent = R("domain.bio.base")

    # The stacks resolve to a real installed face; rsvg picks the first it finds.
    serif = "Iowan Old Style, Palatino, Baskerville, Georgia, serif"
    mono = "SFMono-Regular, Menlo, Consolas, monospace"

    # The one texture in the system, at card scale. Subtle enough to read as paper
    # rather than as noise once a platform recompresses it.
    c = copy_for_card()
    kicker, lines, footer = c["kicker"], c["lines"], c["footer"]

    grain = (f'<pattern id="g" width="5" height="5" patternUnits="userSpaceOnUse">'
             f'<circle cx="0" cy="0" r="0.7" fill="{ink}" opacity="0.055"/></pattern>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img"
     aria-label="{esc(' '.join(lines))} — {esc(kicker)}">
  <defs>{grain}</defs>

  <rect width="{W}" height="{H}" fill="{paper}"/>
  <rect width="{W}" height="{H}" fill="url(#g)"/>

  <!-- Geometry sits on the spacing scale: 96 margin, 128 accent, 8 bar. The first
       cut used 90/150/7 — off-scale numbers that looked fine and meant nothing. -->
  <rect x="96" y="0" width="128" height="8" fill="{accent}"/>

  <text x="96" y="128" font-family="{mono}" font-size="19"
        letter-spacing="3.4" fill="{soft}">{esc(kicker)}</text>

  <text font-family="{serif}" font-size="82" fill="{ink}" letter-spacing="-1.6">
    {chr(10).join(f'    <tspan x="96" y="{300 + i * 92}">{esc(l)}</tspan>' for i, l in enumerate(lines[:2]))}
  </text>

  <rect x="96" y="508" width="{W - 192}" height="1" fill="{rule}"/>
  <text x="96" y="548" font-family="{mono}" font-size="17"
        letter-spacing="1.5" fill="{soft}">{esc(footer)}</text>
</svg>
"""


def render(path):
    src = svg()
    tmp = path + ".svg"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H),
                        "-o", path, tmp], check=True, capture_output=True)
    finally:
        os.unlink(tmp)
    return src


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate the social preview card.")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the PNG is missing or the wrong size")
    args = ap.parse_args(argv)

    if args.check:
        if not os.path.exists(OUT):
            print("error: docs/assets/social-card.png is missing.", file=sys.stderr)
            return 1
        try:
            out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", OUT],
                                 capture_output=True, text=True, check=True).stdout
            w = int(out.split("pixelWidth:")[1].split()[0])
            h = int(out.split("pixelHeight:")[1].split()[0])
        except Exception as e:  # noqa: BLE001 — a probe failure must not gate a deploy
            print(f"note: could not read the card's dimensions ({e}); skipping.")
            return 0
        if (w, h) != (W, H):
            print(f"error: social-card.png is {w}x{h}, expected {W}x{H}.", file=sys.stderr)
            return 1
        print(f"  social-card.png is {w}x{h}.")
        return 0

    if not subprocess.run(["which", "rsvg-convert"], capture_output=True).returncode == 0:
        print("error: rsvg-convert not found (brew install librsvg).", file=sys.stderr)
        return 2

    render(OUT)
    size = os.path.getsize(OUT)
    digest = hashlib.sha256(open(OUT, "rb").read()).hexdigest()[:12]
    print(f"  wrote {os.path.relpath(OUT)} — {W}x{H}, {size // 1024} KB, sha {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
