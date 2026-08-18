#!/usr/bin/env python3
"""
test_house_rules.py — the linter's own edge cases.

house-rules: ignore-file

A style linter earns its place by not crying wolf. Three real bugs were caught here
before anything shipped:

  * the sentence-final `Built with XCO.` was silently excluded by the same lookahead
    that protects `docs/xco.md`;
  * the s-to-z fix had an off-by-one that produced "Civilzsation";
  * and the first --fix run rewrote the inputs in THIS file, turning every case into
    a tautology. Hence the marker above, and the skip in the linter.

  python3 tools/test_house_rules.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from house_rules import scan_text  # noqa: E402

W = "XCO"          # the WRONG casing, built from code points so that
w = "civilis"   # no --fix run can ever rewrite it

CASES = [
    # --- rule 2: casing that must be corrected ------------------------------
    (f"Built with {W}.",              True,  "Built with xCO."),
    ("ending sentence with " + W.lower(), True, "ending sentence with xCO"),
    (f"({W}) in brackets",            True,  "(xCO) in brackets"),
    (f"{W}, then more",               True,  "xCO, then more"),
    ("Xco and xCo are wrong",         True,  "xCO and xCO are wrong"),
    ("The xCO system is fine.",       False, "The xCO system is fine."),
    # --- rule 2: slugs, paths, domains, identifiers must NOT trip -----------
    ("See xco-style-guide for details.", False, "See xco-style-guide for details."),
    ("Open docs/xco.md now.",         False, "Open docs/xco.md now."),
    ("Mail xco@example.org today.",   False, "Mail xco@example.org today."),
    ("Uses --xco-tokens variable.",   False, "Uses --xco-tokens variable."),
    ("the file xco2.css is fine",     False, "the file xco2.css is fine"),
    ("xco.tokens.json stays",         False, "xco.tokens.json stays"),
    (f"Visit https://x.io/{W}/page here.", False, f"Visit https://x.io/{W}/page here."),
    # --- rule 1: civilization with a z --------------------------------------
    (f"{w.capitalize()}ation is at stake.", True, "Civilization is at stake."),
    (f"{w}ational risk",              True,  "civilizational risk"),
    (f"{w.upper()}ATION SHOUTED",     True,  "CIVILIZATION SHOUTED"),
    # --- rule 1: the rest of British spelling is untouched ------------------
    ("organising and manoeuvre stay", False, "organising and manoeuvre stay"),
    # --- someone else's words are not ours to correct -----------------------
    (f"> A quote about {w}ation.",    False, f"> A quote about {w}ation."),
]


def main():
    print("house rules — linter edge cases\n")
    failed = 0
    for text, should_flag, want in CASES:
        _, hits = scan_text(text)
        fixed, _ = scan_text(text, fix=True)
        flag_ok, fix_ok = bool(hits) == should_flag, fixed == want
        if flag_ok and fix_ok:
            print(f"  ok    {text!r}")
            continue
        failed += 1
        print(f"  FAIL  {text!r}")
        if not flag_ok:
            print(f"          flagged={bool(hits)}, expected {should_flag}")
        if not fix_ok:
            print(f"          got  {fixed!r}\n          want {want!r}")

    print()
    if failed:
        print(f"{failed}/{len(CASES)} FAILED")
        return 1
    print(f"all {len(CASES)} edge cases pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
