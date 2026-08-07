#!/usr/bin/env python3
"""Delta instrument — locate where an incoming document contacts the wiki's current position.

Delta is the *position/contact* companion to the gravity instrument (which measures the
corpus's mass and trajectory). Given an incoming document, this script finds:

  - radial r  = cos(doc, mass centroid G)      how aligned it is with the corpus overall
  - novelty n = 1 − nearest-page cosine        how far it sits from anything already held
  - the NEAREST PAGES it touches (top-k by cosine) — the contact surface to read + classify
  - the AXIOMS it bears on (top-k Axioms-Register cards by cosine) — the reference positions
  - its distinctive pull (top offset terms vs the mass) — what it pushes toward

It does NOT classify the contacts (agree / extend / diverge / contradict) or decide anything —
the semantic field sees vocabulary, not meaning. It routes attention; the reader classifies.
For the trajectory read (ahead of / behind the motion), run the gravity skill's `eval` mode.

Stdlib only; deterministic. Reuses .claude/skills/gravity/compute_gravity.py so the term space,
tokeniser and mass model are identical to the gravity instrument.

Usage:
  python3 .claude/skills/delta/compute_delta.py path/to/incoming.md [--top 8] [--axioms 5]
"""
import argparse, os, re, sys

# Reuse the gravity instrument's machinery (same lens, tokeniser, mass model).
_GRAV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gravity")
sys.path.insert(0, os.path.abspath(_GRAV))
import compute_gravity as G  # noqa: E402


def parse_axioms(path="wiki/axioms.md"):
    """Split the Axioms Register into {axiom_id+heading: card_text}."""
    if not os.path.exists(path):
        return {}
    text = open(path, encoding="utf-8", errors="replace").read()
    cards = {}
    # split on '## A<n> — <claim...>' headings
    parts = re.split(r"(?m)^(## A\d+[^\n]*)$", text)
    # parts = [pre, head1, body1, head2, body2, ...]
    for i in range(1, len(parts), 2):
        head = parts[i].lstrip("# ").strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        cards[head] = head + "\n" + body
    return cards


def main():
    ap = argparse.ArgumentParser(description="Measure an incoming document's delta to the wiki.")
    ap.add_argument("file", help="path to the incoming document (raw draft or external doc)")
    ap.add_argument("--top", type=int, default=8, help="nearest pages to surface (default 8)")
    ap.add_argument("--axioms", type=int, default=5, help="axioms to surface (default 5)")
    ap.add_argument("--axioms-file", default="wiki/axioms.md")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2

    current = G.wiki_files_from_dir(".")
    if not current:
        print("error: no wiki/ pages found (run from repo root)", file=sys.stderr)
        return 2
    idf = G.build_space(current)
    G_now, vecs, _disp = G.centroid(current, idf)
    titles = {f: G.page_meta(txt, os.path.basename(f)) for f, txt in current.items()}

    doc_text = open(args.file, encoding="utf-8", errors="replace").read()
    v = G.vectorize(doc_text, idf)
    if not v:
        print("warning: document has no terms in the corpus term space — "
              "delta is undefined (too short, or entirely off-vocabulary).", file=sys.stderr)

    r = G.cos(v, G_now)
    near = sorted(((G.cos(v, pv), f) for f, pv in vecs.items()), reverse=True)[:args.top]
    novelty = 1 - near[0][0] if near else 1.0
    offset = G.sub(v, G_now)

    axcards = parse_axioms(args.axioms_file)
    ax_scored = sorted(((G.cos(v, G.vectorize(txt, idf)), head)
                        for head, txt in axcards.items()), reverse=True)[:args.axioms]

    self_match = near and near[0][0] > 0.98
    print(f"== DELTA: {args.file}")
    print(f"  radial   r = {r:+.3f}   (alignment with the corpus mass; high = squarely on-corpus)")
    print(f"  novelty  n = {novelty:.3f}   (distance to the nearest existing page)")
    if self_match:
        print("  NOTE: nearest page ~1.0 — this file is (almost) already in the wiki; "
              "measure a raw draft or external doc for a true delta.")
    print(f"\n  Nearest pages (the contact surface — READ these, then classify each contact):")
    for c, f in near:
        print(f"    {c:.3f}  {titles.get(f, f)}   [{f}]")
    print(f"\n  Axioms it bears on (READ these cards in wiki/axioms.md; does the doc"
          f" agree / extend / diverge / contradict each?):")
    if ax_scored:
        for c, head in ax_scored:
            print(f"    {c:.3f}  {head}")
    else:
        print("    (no axioms.md found)")
    print(f"\n  Its distinctive pull (top offset terms vs the mass): {G.top_terms(offset, 12)}")
    print("\n  Rσ note: ordinal instrument — it locates contact, it does not classify or decide."
          " Deltas are movement, not verdicts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
