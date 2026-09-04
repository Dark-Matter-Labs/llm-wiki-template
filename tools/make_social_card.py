#!/usr/bin/env python3
"""
make_social_card.py — generate the Open Graph link-preview card.

Published pages exist to be SENT AS LINKS. The preview card is the first thing most
people see, and more people see it than open the page. Without an og:image the link
renders as a bare text row.

This writes a single shared, branded card reused by every page. It is deliberately
generic (no per-page text) so it never goes stale and never leaks a page title into a
chat preview — which matters, because an `unlisted` page's title should not be more
public than the page.

Output: docs/assets/social-card.png at 1200x630 (the Open Graph standard).

Usage:
  python3 tools/make_social_card.py
  python3 tools/make_social_card.py --line1 "Your statement" --line2 "second line"
  python3 tools/make_social_card.py --eyebrow "ORG · SECTION" --url "example.github.io"

Requires Pillow. If it isn't installed:
  pip install Pillow --break-system-packages
"""

import json
import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("error: Pillow is required.\n"
             "       pip install Pillow --break-system-packages")

# Design tokens — kept in step with docs/assets/xco.css.
SHADOW = (0x19, 0x26, 0x40)   # --shadow  navy
MIDTONE = (0xF2, 0x7F, 0x3D)  # --midtone orange (on navy it is 5.66:1 — safe)
WHITE = (255, 255, 255)       # --highlight
W, H = 1200, 630              # Open Graph standard
PAD = 89                      # --s5, the page gutter

# Font fallbacks. The site's own faces come from Google Fonts and aren't on disk, so
# the card uses the closest system grotesque. Sharing the geometry matters more than
# sharing the exact face.
FONT_CANDIDATES = [
    ("/System/Library/Fonts/Helvetica.ttc", 0, 1),          # (path, regular idx, bold idx)
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0, 0),
    ("/Library/Fonts/Arial.ttf", 0, 0),
]


def load_fonts():
    for path, reg, bold in FONT_CANDIDATES:
        if os.path.exists(path):
            return path, reg, bold
    return None, 0, 0


def tracked(draw, xy, text, font, fill, track):
    """Draw letter-spaced text. PIL has no tracking, so step glyph by glyph."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track
    return x


def build(args):
    path, reg_i, bold_i = load_fonts()

    def font(size, bold=False):
        if not path:
            return ImageFont.load_default()
        try:
            return ImageFont.truetype(path, size, index=(bold_i if bold else reg_i))
        except Exception:
            return ImageFont.load_default()

    img = Image.new("RGB", (W, H), SHADOW)
    d = ImageDraw.Draw(img)

    # Top rule — mirrors .top-rule::after: an orange segment across ~40% of the width.
    d.rectangle([0, 0, int(W * 0.40), 13], fill=MIDTONE)

    tracked(d, (PAD, 110), args.eyebrow, font(22), WHITE, 3.2)

    head = font(76, bold=True)
    for i, line in enumerate([l for l in (args.line1, args.line2) if l]):
        d.text((PAD, 196 + i * 86), line, font=head, fill=WHITE)

    # Baseline rule + URL, echoing the page footer.
    d.rectangle([PAD, H - 132, W - PAD, H - 130], fill=MIDTONE)
    tracked(d, (PAD, H - 104), args.url.upper(), font(19), WHITE, 2.4)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    img.save(args.out, "PNG", optimize=True)
    print(f"wrote {args.out}  ({W}x{H}, {os.path.getsize(args.out):,} bytes)")
    if not path:
        print("note: no system font found — used PIL's bitmap default, so the card will "
              "look crude. Install a TTF and re-run.")


def _card():
    """This wiki's card wording, from design/social-card.json.

    These used to be hardcoded argparse defaults, which duplicated a config file that already
    existed and already said it was per-repo -- so the generator carried one wiki's tagline into
    every other wiki that took a copy. Reading the config is what lets the generator itself be
    identical across the federation; the wording stays local, which is the whole point of the
    split. (Same move as PRE_SPLIT_MONTHS in the log tools: the per-repo fact goes to per-repo
    config, and the code travels.)
    """
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "design", "social-card.json")
    try:
        with open(path, encoding="utf-8") as fh:
            c = json.load(fh)
    except (OSError, ValueError):
        c = {}
    lines = list(c.get("lines") or ["", ""]) + ["", ""]
    return (c.get("kicker", ""), lines[0], lines[1], c.get("footer", ""))


def main(argv=None):
    eyebrow, line1, line2, url = _card()
    p = argparse.ArgumentParser(description="Generate the Open Graph social card.")
    p.add_argument("--eyebrow", default=eyebrow)
    p.add_argument("--line1", default=line1)
    p.add_argument("--line2", default=line2)
    p.add_argument("--url", default=url)
    p.add_argument("--out", default="docs/assets/social-card.png")
    build(p.parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
