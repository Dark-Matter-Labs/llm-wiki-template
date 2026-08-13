#!/usr/bin/env python3
"""
test_contradictions.py — prove closure is actually enforced.

The register is only worth having if it distinguishes "resolved" from "nobody has
looked at it yet", and if a resolution that points nowhere is caught rather than
counted as settled. Each case below is a way the state could be wrong while still
looking fine from the outside.

Usage:  python3 tools/test_contradictions.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contradictions as C  # noqa: E402


def page(title, **fields):
    fm = [f"title: {title}"]
    for k, v in fields.items():
        if v is not None:
            fm.append(f'{k}: "{v}"')
    return {"slug": title.lower().replace(" ", "-"), "contradicts": fields.get("contradicts"),
            "superseded_by": fields.get("superseded_by"),
            "devalued_by": fields.get("devalued_by")}


def corpus(*pages):
    return {p_title: page(p_title, **fields) for p_title, fields in pages}


def main():
    failures = []

    def check(name, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    # 1. A declared contradiction with no resolution is OPEN, not silently fine.
    c = corpus(("A", {"contradicts": "B"}), ("B", {}))
    op, cl, pr = C.analyse(c)
    check("an unresolved contradiction is reported open",
          len(op) == 1 and not cl and not pr, f"open={op} closed={cl} problems={pr}")

    # 2. Superseded closes it — the losing side carries the pointer.
    c = corpus(("A", {"contradicts": "B", "superseded_by": "B"}), ("B", {}))
    op, cl, pr = C.analyse(c)
    check("superseded_by closes the contradiction",
          not op and len(cl) == 1 and not pr, f"closed={cl}")

    # 3. Devalued closes it too, from the other direction.
    c = corpus(("A", {"contradicts": "B"}), ("B", {"devalued_by": "A"}))
    op, cl, pr = C.analyse(c)
    check("devalued_by on the other side also closes it",
          not op and len(cl) == 1 and not pr, f"closed={cl}")

    # 4. Both sides losing is incoherent — somebody resolved it twice, in opposite
    #    directions, and the corpus now asserts each replaced the other.
    c = corpus(("A", {"contradicts": "B", "superseded_by": "B"}), ("B", {"devalued_by": "A"}))
    op, cl, pr = C.analyse(c)
    check("both sides recording a loss is caught as incoherent",
          len(pr) >= 1, f"problems={pr}")

    # 5. A resolution pointing at a page that does not exist LOOKS settled and isn't.
    #    This is the failure the register exists to prevent.
    c = corpus(("A", {"contradicts": "B", "superseded_by": "Ghost"}), ("B", {}))
    op, cl, pr = C.analyse(c)
    check("a resolution pointing at a missing page is caught",
          any("does not exist" in m for _, m in pr), f"problems={pr}")

    # 6. Contradicting a page that does not exist.
    c = corpus(("A", {"contradicts": "Nowhere"}),)
    op, cl, pr = C.analyse(c)
    check("contradicting a missing page is caught",
          any("does not exist" in m for _, m in pr), f"problems={pr}")

    # 7. Self-reference, both ways.
    c = corpus(("A", {"contradicts": "A"}),)
    op, cl, pr = C.analyse(c)
    self_contra = any("itself" in m for _, m in pr)
    c = corpus(("A", {"superseded_by": "A"}),)
    op2, cl2, pr2 = C.analyse(c)
    check("self-reference is caught in both fields",
          self_contra and any("itself" in m for _, m in pr2),
          f"contradicts-self={pr} superseded-self={pr2}")

    # 8. A corpus with no contradictions at all is coherent, not empty-and-suspicious.
    c = corpus(("A", {}), ("B", {}))
    op, cl, pr = C.analyse(c)
    check("a corpus with no contradictions is coherent",
          not op and not cl and not pr)

    # 9. Nothing is deleted by resolution: the losing page is still present and readable.
    c = corpus(("A", {"contradicts": "B", "superseded_by": "B"}), ("B", {}))
    op, cl, pr = C.analyse(c)
    check("the losing page survives resolution (plurality preserved)",
          "A" in c and "B" in c, "both pages still in the corpus")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("All contradiction-closure checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
