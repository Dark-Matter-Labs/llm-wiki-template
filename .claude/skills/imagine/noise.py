#!/usr/bin/env python3
"""
noise.py: pick seeds or cards for the imagine skill by chance, in one of two ways.

  dice   Every pick is independent. A roll can land anywhere. (White noise.)
  drift  Picks wander. Seeds sit on a ring with related seeds next to each other,
         and a Perlin-noise walk moves along it, so each pick is near the last
         but the walk turns and sometimes travels. (Smooth, coherent noise.)

Perlin noise is Ken Perlin's 1983 method for natural-looking randomness, made after
working on the film Tron. It is the difference between static and a coastline.

Usage:
  python3 .claude/skills/imagine/noise.py seeds                # three seeds, dice
  python3 .claude/skills/imagine/noise.py seeds --drift 0.15   # three seeds, a gentle wander
  python3 .claude/skills/imagine/noise.py seeds --drift 0.15 --at 4.5   # carry on a walk
  python3 .claude/skills/imagine/noise.py cards --n 1          # draw one card from the deck
  python3 .claude/skills/imagine/noise.py --test
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import secrets
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
KINDS = {"reference", "motif", "form", "provocation", "palette"}
DECK_TITLE = "An oblique deck for Dm"
EXPORT = ROOT / ".commons" / "imagination-wiki" / "export" / "wiki.shared.json"


# ---------- Perlin noise, one dimension ----------

def perlin(seed: int):
    """Return n(x) in roughly [-1, 1]: smooth, continuous, and the same for the same seed."""
    rng = random.Random(seed)
    grads = [rng.uniform(-1, 1) for _ in range(256)]

    def fade(t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def n(x: float) -> float:
        i = math.floor(x)
        f = x - i
        g0, g1 = grads[i % 256], grads[(i + 1) % 256]
        a, b = g0 * f, g1 * (f - 1)
        return 2 * (a + fade(f) * (b - a))

    def octaves(x: float) -> float:
        # a big slow wave plus a smaller quick one: travel, with detail
        return (n(x) + 0.5 * n(x * 2.1 + 17.3)) / 1.5

    return octaves


# ---------- the pools ----------

def frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def tags_of(raw: str) -> set:
    return {t.strip() for t in raw.strip("[]").split(",") if t.strip()}


def load_pages() -> list:
    """[(title, tags, body)] from this wiki if it is the Imagination Wiki, else from its shared copy, else nothing."""
    pages = []
    wiki = ROOT / "wiki"
    for p in sorted(wiki.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm.get("title"):
            pages.append((fm["title"].strip('"'), tags_of(fm.get("tags", "")), text))
    fed = ROOT / "design" / "federation.json"
    try:
        here = json.loads(fed.read_text(encoding="utf-8")).get("name") if fed.exists() else None
    except ValueError:
        here = None
    if here == "imagination-wiki":
        return pages
    if EXPORT.exists():
        nodes = json.loads(EXPORT.read_text(encoding="utf-8"))["nodes"]
        return [(n["title"], set(n.get("tags") or []), n.get("body") or "") for n in nodes]
    return []  # never treat another wiki's own pages as seeds: they were not offered here


def ring(items: list) -> list:
    """Order seeds so related ones sit side by side: start anywhere, always step to the most similar left."""
    if not items:
        return []
    left, out = list(items), [items[0]]
    left.remove(items[0])
    while left:
        cur = out[-1][1]
        nxt = max(left, key=lambda it: (len(cur & it[1]) / (len(cur | it[1]) or 1), it[0]))
        out.append(nxt)
        left.remove(nxt)
    return out


def seeds(pages: list) -> list:
    return ring([(t, tags) for t, tags, _ in pages if KINDS & tags])


def cards(pages: list) -> list:
    """Cards are the list items under '## The cards' on the deck page, in their written order."""
    for title, _, body in pages:
        if title == DECK_TITLE:
            part = body.split("## The cards", 1)[-1].split("\n## ", 1)[0]
            return [(l[2:].strip(), set()) for l in part.splitlines() if l.startswith("- ")]
    return []


# ---------- picking ----------

def pick(pool: list, n: int, drift: float | None, at: float | None, seed: int) -> tuple:
    """Return (indices, next_at). drift=None means dice."""
    rng = random.Random(seed)
    if not pool:
        return [], at
    n = min(n, len(pool))
    if drift is None:
        return rng.sample(range(len(pool)), n), None
    noise = perlin(seed)
    t = rng.uniform(0, 50) if at is None else at
    pos = rng.uniform(0, len(pool)) if at is None else (noise(t * 0.37) + 1) / 2 * len(pool)
    chosen = []
    while len(chosen) < n:
        pos = (pos + drift * len(pool) * noise(t)) % len(pool)
        i = int(pos) % len(pool)
        while i in chosen:  # never the same seed twice in one roll: step to the neighbour
            i = (i + 1) % len(pool)
        chosen.append(i)
        t += 0.61
    return chosen, round(t, 2)


# ---------- self-check ----------

def test() -> None:
    n = perlin(7)
    xs = [i * 0.01 for i in range(4000)]
    vs = [n(x) for x in xs]
    assert all(-1.5 <= v <= 1.5 for v in vs), "noise out of range"
    assert max(abs(a - b) for a, b in zip(vs, vs[1:])) < 0.08, "noise is not smooth"
    assert perlin(7)(3.3) == n(3.3), "same seed must give the same noise"
    assert perlin(8)(3.3) != n(3.3), "different seeds should differ"
    pool = [(str(i), set()) for i in range(12)]
    for d in (None, 0.05, 0.3, 1.0):
        idx, _ = pick(pool, 3, d, None, 42)
        assert len(set(idx)) == 3 and all(0 <= i < 12 for i in idx), f"bad picks for drift {d}"
    # a small drift stays closer than dice, on average, over many walks
    def spread(d):
        tot = 0
        for s in range(300):
            a, b, c = pick(pool, 3, d, None, s)[0]
            tot += min(abs(a - b), 12 - abs(a - b)) + min(abs(b - c), 12 - abs(b - c))
        return tot
    assert spread(0.05) < spread(None), "drift should wander, not jump"
    r = ring([("a", {"x"}), ("b", {"y"}), ("c", {"x"})])
    assert [t for t, _ in r] == ["a", "c", "b"], "ring should seat related seeds together"
    print("noise.py: all checks pass")


def main() -> int:
    ap = argparse.ArgumentParser(description="Pick seeds or cards by chance: dice, or a Perlin drift.")
    ap.add_argument("pool", nargs="?", choices=["seeds", "cards"], default="seeds")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--drift", type=float, help="0.05 wanders gently, 0.5 roams. Leave out for dice.")
    ap.add_argument("--at", type=float, help="carry on a walk: pass the 'next at' from the last run")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    if a.test:
        test()
        return 0
    pages = load_pages()
    pool = seeds(pages) if a.pool == "seeds" else cards(pages)
    if not pool:
        print(f"No {a.pool} found. " + ("Is this wiki connected to the Imagination Wiki?" if a.pool == "seeds"
              else f"The deck page '{DECK_TITLE}' was not found."))
        return 1
    idx, nxt = pick(pool, a.n, a.drift, a.at, secrets.randbits(32))
    for i in idx:
        print(pool[i][0])
    if nxt is not None:
        print(f"(next at {nxt})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
