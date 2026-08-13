#!/usr/bin/env python3
"""
test_validation_weighting.py — prove the super-producer protection actually protects.

The failure this guards against, in the owner's words (7 Aug 2026):

    "Somebody puts in loads of data, but it's four generations of previous thinking.
     Suddenly we pull the gravity of the whole model back four generations."

Schema tests prove the `validation` field is *accepted*. This proves it *does something*:
that a large body of unvalidated material is admitted to the corpus without moving its
centre of mass, and that the same material — once people have stood behind it — moves the
centre as it should.

If this test fails, the validation layer is decoration.

Usage:  python3 tools/test_validation_weighting.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", ".claude", "skills", "gravity"))
import compute_gravity as G  # noqa: E402


def page(title, body, validation="machine"):
    return (f"---\ntitle: {title}\nvalidation: {validation}\n---\n\n{body}\n")


# Two vocabularies with no overlap, so any centroid movement is unambiguous.
ESTABLISHED = ("catchment liability water flood risk underwriting capacity "
               "agreement stewardship verification coupled hydrological")
INTRUDER = ("blockchain token ledger cryptocurrency mining wallet consensus "
            "nft staking decentralised exchange volatility")


def corpus(n_base=50, n_intruder=0, intruder_validation="machine"):
    """A base corpus on one topic, optionally flooded with pages on another."""
    pages = {}
    for i in range(n_base):
        pages[f"/base/p{i}.md"] = page(
            f"Base {i}", " ".join([ESTABLISHED] * 6), "collective")
    for i in range(n_intruder):
        pages[f"/intr/q{i}.md"] = page(
            f"Intruder {i}", " ".join([INTRUDER] * 6), intruder_validation)
    return pages


def drift(pages_a, pages_b):
    """1 - cosine between the two centroids: 0 = unmoved, 1 = orthogonal."""
    idf = G.build_space({**pages_a, **pages_b})
    Ga, _, _ = G.centroid(pages_a, idf)
    Gb, _, _ = G.centroid(pages_b, idf)
    return 1 - G.cos(Ga, Gb)


def main():
    failures = []

    def check(name, ok, detail):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}\n        {detail}")
        if not ok:
            failures.append(name)

    base = corpus()

    # 1. The protection itself: an equal-sized flood of UNVALIDATED material must
    #    barely move the centre.
    flood_machine = corpus(n_intruder=50, intruder_validation="machine")
    d_machine = drift(base, flood_machine)
    check("50 unvalidated pages barely move the centroid",
          d_machine < 0.05, f"drift = {d_machine:.4f} (must be < 0.05)")

    # 2. The same material, once the group has stood behind it, SHOULD move the centre.
    #    A layer that suppressed everything equally would be useless.
    flood_collective = corpus(n_intruder=50, intruder_validation="collective")
    d_collective = drift(base, flood_collective)
    check("the same 50 pages at `collective` do move it",
          d_collective > 0.10, f"drift = {d_collective:.4f} (must be > 0.10)")

    # 3. The ordering is what makes it a hierarchy rather than an on/off switch.
    d_self = drift(base, corpus(n_intruder=50, intruder_validation="self"))
    d_peer = drift(base, corpus(n_intruder=50, intruder_validation="peer"))
    ordered = d_machine < d_self < d_peer < d_collective
    check("drift increases monotonically with validation level",
          ordered,
          f"machine {d_machine:.4f} < self {d_self:.4f} "
          f"< peer {d_peer:.4f} < collective {d_collective:.4f}")

    # 4. Ratio: the protection has to be worth having, not a rounding difference.
    ratio = d_collective / d_machine if d_machine else float("inf")
    check("validated material moves the centre several times more than unvalidated",
          ratio > 3, f"collective/machine = {ratio:.1f}x (must be > 3x)")

    # 5. Unvalidated pages are ADMITTED, not excluded — they must still be indexed and
    #    findable. Suppressing their weight is not the same as dropping them.
    idf = G.build_space(flood_machine)
    w, _ = G.inbound_mass(flood_machine)
    intruders_present = sum(1 for f in flood_machine if f.startswith("/intr/"))
    all_weighted = all(w[f] > 0 for f in flood_machine)
    check("unvalidated pages are admitted and carry non-zero weight",
          intruders_present == 50 and all_weighted,
          f"{intruders_present} present, all weights > 0 = {all_weighted}")

    # 6. A page with no `validation` field must not crash and must default to machine.
    legacy = {"/x/legacy.md": "---\ntitle: Legacy\n---\n\n" + ESTABLISHED}
    check("a page with no validation field defaults to machine",
          G.page_validation(legacy["/x/legacy.md"]) == "machine",
          f"got {G.page_validation(legacy['/x/legacy.md'])!r}")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("All validation-weighting checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
