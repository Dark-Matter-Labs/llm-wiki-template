#!/usr/bin/env python3
"""
test_community.py — prove the hand-written Louvain actually finds communities.

`tools/community.py` exists so this repo keeps its stdlib-only convention, which means
nothing else in CI would notice if it quietly degraded into returning one community per
node, or one community for everything. Both failures look calm from the outside: the first
makes `patterns.py` report no patterns, the second makes it report one enormous one.

The comparison against networkx runs only where networkx happens to be installed. That is
the OPTIONAL half — everything above it tests behaviour directly, so CI without networkx is
still testing the thing, not skipping it.

Usage:  python3 tools/test_community.py
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import community as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def clique(prefix, n):
    return [(f"{prefix}{i}", f"{prefix}{j}") for i in range(n) for j in range(i + 1, n)]


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
        if not ok:
            fails.append(name)

    # 1. Three disjoint cliques are the easiest community structure there is. Anything
    #    that cannot find this is broken, not merely imprecise.
    edges = clique("a", 6) + clique("b", 6) + clique("c", 6)
    nodes = sorted({n for e in edges for n in e})
    adj = C.from_edges(nodes, edges)
    got = C.louvain_communities(adj, resolution=1.0, seed=1)
    check("three disjoint cliques give three communities", len(got) == 3,
          f"got {len(got)}: {[len(g) for g in got]}")
    check("and each holds exactly one clique",
          all(len({n[0] for n in g}) == 1 for g in got))

    # 2. Two cliques joined by a single edge is the classic case: the bridge must not
    #    merge them.
    edges = clique("x", 5) + clique("y", 5) + [("x0", "y0")]
    nodes = sorted({n for e in edges for n in e})
    adj = C.from_edges(nodes, edges)
    got = C.louvain_communities(adj, resolution=1.0, seed=1)
    check("a single bridge does not merge two cliques", len(got) == 2,
          f"got {len(got)}")

    # 3. Neither collapse is allowed: all-in-one, or one-each. Both are the shapes a
    #    silently broken implementation settles into.
    check("does not collapse to a single community", len(got) != 1)
    check("does not shatter to one node each", len(got) != len(nodes))

    # 4. Determinism. The seed is the only thing that may change the answer — not the
    #    process's hash seed, which is what broke `patterns.py` before it shipped.
    a = [sorted(g) for g in C.louvain_communities(adj, resolution=1.0, seed=7)]
    b = [sorted(g) for g in C.louvain_communities(adj, resolution=1.0, seed=7)]
    check("same seed, same partition, in-process", a == b)
    script = ("import sys; sys.path.insert(0, %r); import community as C;"
              "e=[('x%%d'%%i,'x%%d'%%j) for i in range(5) for j in range(i+1,5)]"
              "+[('y%%d'%%i,'y%%d'%%j) for i in range(5) for j in range(i+1,5)]+[('x0','y0')];"
              "n=sorted({v for p in e for v in p});"
              "print(sorted(sorted(g) for g in C.louvain_communities("
              "C.from_edges(n,e), resolution=1.0, seed=7)))" % HERE)
    env = dict(os.environ)
    outs = set()
    for seed in ("0", "1", "999"):
        env["PYTHONHASHSEED"] = seed
        outs.add(subprocess.run([sys.executable, "-c", script],
                                capture_output=True, text=True, env=env).stdout)
    check("same seed, same partition, across PYTHONHASHSEED", len(outs) == 1)

    # 5. Degenerate inputs must not raise. An empty wiki and a wiki with no links are
    #    both real states — every new spoke starts in one of them.
    try:
        C.louvain_communities(C.from_edges([], []), seed=1)
        C.louvain_communities(C.from_edges(["lonely", "also"], []), seed=1)
        ok = True
    except Exception as exc:                          # noqa: BLE001
        ok, = (False,)
        print(f"        {exc}")
    check("an empty or link-free graph does not raise", ok)

    # 6. Helpers used by patterns.py for its reported numbers.
    adj = C.from_edges(["p", "q", "r"], [("p", "q"), ("q", "r"), ("p", "r")])
    check("density of a triangle is 1.0", abs(C.density(adj, ["p", "q", "r"]) - 1.0) < 1e-9)
    adj2 = C.from_edges(["p", "q", "r"], [("p", "q")])
    check("density of one edge among three is 1/3",
          abs(C.density(adj2, ["p", "q", "r"]) - 1 / 3) < 1e-9)
    check("components splits a disconnected graph", len(C.components(adj2)) == 2)

    # 7. OPTIONAL — agreement with the reference implementation, where it is installed.
    try:
        import networkx as nx
    except ImportError:
        print("  --    networkx not installed; comparison skipped (behaviour above still "
              "tested)")
    else:
        edges = clique("a", 8) + clique("b", 8) + clique("c", 8) + [("a0", "b0"), ("b1", "c1")]
        nodes = sorted({n for e in edges for n in e})
        adj = C.from_edges(nodes, edges)
        G = nx.Graph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)
        mine = C.louvain_communities(adj, resolution=1.0, seed=3)
        theirs = nx.community.louvain_communities(G, resolution=1.0, seed=3)
        qm = nx.community.modularity(G, [g for g in mine if g])
        qt = nx.community.modularity(G, [g for g in theirs if g])
        check("modularity within 15% of networkx on a known graph", qm >= qt * 0.85,
              f"mine {qm:.4f} vs networkx {qt:.4f}")
        check("same number of communities on a clear structure", len(mine) == len(theirs),
              f"mine {len(mine)} vs networkx {len(theirs)}")

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
