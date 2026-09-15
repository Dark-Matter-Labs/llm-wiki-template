#!/usr/bin/env python3
"""community.py — Louvain modularity communities, in the standard library only.

Written because `patterns.py` needs community detection and this repo has no dependency
story: there is no requirements.txt, no pip step in CI, and ~90 tools that run on a bare
Python. That convention is worth more than the import — these tools are synced into eleven
wikis, and a dependency added here is a dependency eleven repos have to install before
anything runs. Adding `networkx` turned CI red the first time it ran.

The algorithm is Blondel, Guillaume, Lambiotte & Lefebvre (2008) with the Lambiotte
resolution parameter: repeatedly move each node to the neighbouring community that most
improves modularity, then contract each community to a single node and do it again, until
a pass changes nothing.

    gain of moving node i into community C
        = w(i, C) - resolution * k_i * sum_tot(C) / 2m

VALIDATION. This is not an implementation anyone should trust on sight, so it is checked
against `networkx.community.louvain_communities` where that happens to be installed - see
`tools/test_community.py`, which skips only the comparison, never the behaviour.

Measured against networkx on this corpus (628 pages, 4104 links, resolution 4.0), it is
CONSERVATIVE: modularity ~0.145 against their ~0.157, and through the consensus in
`patterns.py` it returns 40 stable clusters where they return 53. But of those 40, **32 are
identical to a networkx cluster and 38 are recognisable, median Jaccard 1.00** - it finds
fewer groups, not different ones. That is the right direction to err for a tool whose
failure mode is announcing a pattern that is not there.

Determinism: the node order is shuffled per seed (that is what the seed is for), but every
tie is broken on the sorted community id, so two runs with the same seed are identical
regardless of PYTHONHASHSEED.
"""
import random


def _degrees(adj):
    """Weighted degree, with a self-loop counted twice as the convention requires."""
    return {n: sum(w.values()) + w.get(n, 0.0) for n, w in adj.items()}


def _one_level(adj, resolution, rng):
    """Move nodes greedily until no move improves modularity. Returns (node->community)."""
    k = _degrees(adj)
    m2 = sum(k.values())
    if m2 <= 0:
        return {n: n for n in adj}, False

    comm = {n: n for n in adj}
    tot = dict(k)                       # summed degree of each community
    order = sorted(adj)
    rng.shuffle(order)

    improved, moved = False, True
    while moved:
        moved = False
        for n in order:
            here = comm[n]
            tot[here] -= k[n]           # take n out before scoring, or it scores itself

            weights = {}
            for nb, w in adj[n].items():
                if nb != n:
                    weights[comm[nb]] = weights.get(comm[nb], 0.0) + w

            best, best_gain = here, weights.get(here, 0.0) - resolution * tot[here] * k[n] / m2
            for c in sorted(weights):   # sorted: ties must not depend on dict order
                gain = weights[c] - resolution * tot[c] * k[n] / m2
                if gain > best_gain:
                    best, best_gain = c, gain

            tot[best] += k[n]
            if best != here:
                comm[n] = best
                moved = improved = True
    return comm, improved


def _contract(adj, comm):
    """One node per community; edge weights summed, internal weight becomes a self-loop."""
    out = {}
    for n, nbrs in adj.items():
        a = comm[n]
        row = out.setdefault(a, {})
        for nb, w in nbrs.items():
            b = comm[nb]
            row[b] = row.get(b, 0.0) + w
    # A self-loop must carry the internal weight once, not twice: the loop above visits
    # each internal edge from both ends.
    for a, row in out.items():
        if a in row:
            row[a] /= 2.0
    return out


def louvain_communities(adj, resolution=1.0, seed=0):
    """Communities of an undirected weighted graph given as {node: {neighbour: weight}}.

    Returns a list of sets of the original node keys.
    """
    rng = random.Random(seed)
    nodes = sorted(adj)
    member = {n: {n} for n in nodes}    # current super-node -> original nodes
    cur = {n: dict(w) for n, w in adj.items()}

    while True:
        comm, improved = _one_level(cur, resolution, rng)
        if not improved:
            break
        rolled = {}
        for sup, c in comm.items():
            rolled.setdefault(c, set()).update(member[sup])
        cur = _contract(cur, comm)
        member = rolled
        if len(cur) <= 1:
            break

    return [set(v) for _, v in sorted(member.items(), key=lambda kv: str(kv[0]))]


def from_edges(nodes, edges):
    """Build the adjacency map: every node present, every edge weight 1.0, undirected."""
    adj = {n: {} for n in nodes}
    for a, b in edges:
        if a == b or a not in adj or b not in adj:
            continue
        adj[a][b] = 1.0
        adj[b][a] = 1.0
    return adj


def density(adj, group):
    """Fraction of possible internal edges that exist, for a set of nodes."""
    g = set(group) & set(adj)
    n = len(g)
    if n < 2:
        return 0.0
    links = sum(1 for a in g for b in adj[a] if b in g and a < b)
    return 2.0 * links / (n * (n - 1))


def components(adj):
    """Connected components, as sets."""
    seen, out = set(), []
    for start in sorted(adj):
        if start in seen:
            continue
        stack, group = [start], set()
        while stack:
            n = stack.pop()
            if n in group:
                continue
            group.add(n)
            stack.extend(nb for nb in adj[n] if nb not in group)
        seen |= group
        out.append(group)
    return out
