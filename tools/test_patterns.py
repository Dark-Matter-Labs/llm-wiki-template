#!/usr/bin/env python3
"""
test_patterns.py — prove the pattern finder cannot leak, cannot invent, and cannot drift.

Every case below is a way `patterns.py` could be wrong while its output still read as
perfectly sensible. Two of them are regressions: both were live defects found on
2026-09-15 while building it, and both produced confident, plausible, wrong output.

Usage:  python3 tools/test_patterns.py
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patterns as P  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def page(slug, title, links, **fields):
    n = {
        "slug": slug, "title": title, "type": "summary", "visibility": "internal",
        "tags": ["t"], "sources": [f"raw/{slug}.md"],
        "outbound_links": list(links), "inbound_links": [],
    }
    n.update(fields)
    return n


def clique(prefix, n, **fields):
    """n pages all linking to each other — a cluster nothing can miss."""
    slugs = [f"{prefix}{i}" for i in range(n)]
    return [page(s, f"{prefix} page {i}", [o for o in slugs if o != s], **fields)
            for i, s in enumerate(slugs)]


#: The synthetic wiki's name. Fixed, not the temp directory's: `origin` is compared
#: against ROOT.name, and a random name means the "our own material returning" filter can
#: never match and `wikis` differs every run — the harness would fake both failures.
LOCAL = "home-wiki"


def run(nodes, commons=None, **kw):
    """Point the module at a synthetic corpus and gather."""
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d) / LOCAL
        (root / "export").mkdir(parents=True)
        (root / "export" / "wiki.json").write_text(json.dumps({"nodes": nodes}))
        for name, got in (commons or {}).items():
            cut = root / ".commons" / name / "export"
            cut.mkdir(parents=True)
            (cut / "wiki.shared.json").write_text(json.dumps({"nodes": got}))
        old = (P.ROOT, P.EXPORT, P.COMMONS)
        P.ROOT, P.EXPORT, P.COMMONS = root, root / "export/wiki.json", root / ".commons"
        try:
            return P.gather(**kw)
        finally:
            P.ROOT, P.EXPORT, P.COMMONS = old


def titles(m):
    return {t for r in m["candidates"] for t in r["members"]}


def main():
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if not ok else ""))
        if not ok:
            fails.append(name)

    # 1. A private page sitting in the middle of an obvious cluster must not come out.
    #    The corpus carries 181 private pages including the whole CRM; a pattern report
    #    is something people paste into a channel.
    nodes = clique("open", 5) + [page("secret", "The Secret Deal",
                                      ["open0", "open1", "open2"], visibility="private")]
    for s in ("open0", "open1", "open2"):
        next(n for n in nodes if n["slug"] == s)["outbound_links"].append("secret")
    m = run(nodes)
    check("private page never reaches the output", "The Secret Deal" not in titles(m))

    # 2. ...and the CRM is refused even when the owner asks for private material, because
    #    a CRM cluster is a cluster of PEOPLE. The first prototype's densest find was two
    #    contact pages for the same person.
    nodes = clique("open", 5) + clique("contact", 5, tags=["crm"], visibility="private")
    m = run(nodes, include_private=True)
    check("CRM refused even under --include-private",
          not any(t.startswith("contact") for t in titles(m)))
    check("--include-private is stamped on the output", m["corpus"]["included_private"])

    # 3. REGRESSION. Material this wiki contributed upward comes back down in the commons
    #    cut. Left in, every page clustered with its own mirror and the cluster reported
    #    "spans 2 wikis" — a cross-wiki meta-pattern manufactured from a single wiki.
    ours = clique("shared", 5)
    echo = [dict(n, origin=LOCAL) for n in ours]
    m = run(ours, commons={"team-wiki": echo}, federation=True)
    dupes = [r for r in m["candidates"] if len(r["members"]) != len(set(r["members"]))]
    check("our own pages returning from the commons are not read back", not dupes)
    check("and cannot fake a cross-wiki pattern",
          not any(r["travels"] for r in m["candidates"]))

    # ...while a genuinely foreign page still counts as another context. The edge has to
    # come FROM the commons page: local links point at bare slugs, and a commons slug is
    # namespaced, so a local->commons link cannot resolve.
    ours = clique("shared", 5)
    foreign = [page("f0", "Foreign page", [n["slug"] for n in ours],
                    origin="robyn-llm-wiki")]
    m = run(ours, commons={"team-wiki": foreign}, federation=True)
    check("a page from another wiki does count as another context",
          any(r["travels"] for r in m["candidates"]),
          f"candidates: {[(r['pages'], r['wikis']) for r in m['candidates']]}")

    # 4. REGRESSION. The output must not change between runs of the same corpus. It did:
    #    frozenset iteration follows PYTHONHASHSEED, so tied naming pages and tied tags
    #    swapped every run. A reproducibility tool that is not reproducible is worthless,
    #    and `diff` reported the files identical while five md5s disagreed.
    nodes = clique("a", 6) + clique("b", 6) + clique("c", 6)
    once = json.dumps(run(nodes)["candidates"], sort_keys=True)
    check("deterministic within a process",
          all(json.dumps(run(nodes)["candidates"], sort_keys=True) == once
              for _ in range(3)))
    env = dict(os.environ)
    outs = set()
    for seed in ("0", "1", "424242"):
        env["PYTHONHASHSEED"] = seed
        outs.add(subprocess.run(
            [sys.executable, str(HERE / "patterns.py"), "--json"],
            capture_output=True, text=True, env=env, cwd=HERE.parent).stdout)
    check("deterministic across hash seeds, on the real corpus", len(outs) == 1,
          f"{len(outs)} different outputs")

    # 4b. REGRESSION. Resolution interacts with total graph size, so the value tuned on
    #     809 pages shattered a small wiki into singletons and the tool reported "no
    #     patterns" — indistinguishable from there being none. Eight of the eleven wikis
    #     in this federation are small.
    small = clique("p", 5) + clique("q", 5) + clique("r", 5)
    m = run(small)
    check("a small corpus still yields clusters (resolution adapts)",
          len(m["candidates"]) == 3,
          f"got {len(m['candidates'])} at resolution {m['settings']['resolution']}")
    check("and the chosen resolution is reported",
          m["settings"]["resolution_chosen_automatically"])

    # 5. An already-named cluster is not what was asked for, so it must rank below an
    #    unnamed one however tight it is.
    named = clique("named", 6)
    named[0].update(type="synthesis", title="What the named group is about")
    named[0]["inbound_links"] = [n["slug"] for n in named[1:]]
    m = run(named + clique("bare", 6))
    order = [r["naming_coverage"] for r in m["candidates"]]
    check("unnamed clusters rank first", order == sorted(order))

    # 6. The refusals are structural. If someone adds `--check` this tool becomes a gate
    #    that fails you for writing more pages, and gates that punish good work get
    #    switched off — taking the useful part with them.
    helptext = subprocess.run([sys.executable, str(HERE / "patterns.py"), "--help"],
                              capture_output=True, text=True).stdout
    check("no --check flag exists", "--check" not in helptext)

    # 7. A bad --agreement is refused rather than silently clamped.
    rc = subprocess.run([sys.executable, str(HERE / "patterns.py"), "--agreement", "3"],
                        capture_output=True, text=True).returncode
    check("--agreement outside (0,1] exits non-zero", rc != 0)

    print()
    if fails:
        print(f"{len(fails)} check(s) failed: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
