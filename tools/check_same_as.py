#!/usr/bin/env python3
"""`same_as:` — the same subject, held in more than one wiki.

Measured 2026-09-18: 172 entity and concept titles exist in more than one wiki, and 165 of
them already carry `origin`, because they are copies contributed up to a commons. Seven do
not. They are pages different people wrote independently about the same thing, with nothing
joining them — `Dark Matter Labs` in three wikis, `xCO` in three, `Muga Valley` in two.

`same_as` is that missing edge, and nothing else. It does not merge, supersede, or rank. It
records that two pages are about one subject, which is a judgement a person makes.

    same_as: [michelle-llm-wiki/muga-valley]

THE ONE RULE, AND WHY IT IS NOT SYMMETRIC.

Identity is symmetric in the world. Recording it is not, because naming a page names its
existence. A `private` page's title never leaves its repo — not in an export, not in a link
pointing at it — so a more visible page that claims kinship with one would publish the fact
that it exists.

So a page may only point at a target at least as open as itself:

    private  ->  anything          a private page never exports, so it can leak nothing
    internal ->  internal, public  and the target must be visible in a commons cut read here
    unlisted ->  unlisted, public  unlisted is reachable on the web by direct link
    public   ->  public

Of the 22 possible edges among those seven subjects, 17 are legal and 5 are refused. Every
refusal is an internal or unlisted page reaching for a private one.

A non-private page must also be able to SEE its target: the slug has to resolve in a commons
cut this wiki reads. Asserting that a page exists in a repository you have no access to is
not a claim this wiki can stand behind, and `.commons/` is the only cross-wiki evidence any
of these repos has.

    python3 tools/check_same_as.py            # what is declared, and whether it holds
    python3 tools/check_same_as.py --check    # exit 1 on any violation
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
COMMONS = ROOT / ".commons"

OPENNESS = {"private": 0, "internal": 1, "unlisted": 2, "public": 3}
ENTRY = re.compile(r"^[A-Za-z0-9][\w.-]*/[\w./-]+$")


def frontmatter(raw: str) -> str | None:
    if not raw.startswith("---"):
        return None
    end = raw.find("\n---", 3)
    return raw[4:end] if end > 0 else None


def field(block: str, key: str) -> str | None:
    m = re.search(rf"^{key}:\s*(.+?)\s*$", block, re.M)
    return m.group(1).strip().strip('"\'') if m else None


def entries(block: str) -> list[str]:
    """`same_as: [a/b, c/d]` or a one-per-line list. Absent is the normal case."""
    m = re.search(r"^same_as:\s*(.*)$", block, re.M)
    if not m:
        return []
    inline = m.group(1).strip()
    if inline.startswith("["):
        return [x.strip().strip('"\'') for x in inline[1:-1].split(",") if x.strip()]
    out = []
    for line in block[m.end():].split("\n"):
        if not line.startswith(("  -", "- ")):
            break
        out.append(line.split("-", 1)[1].strip().strip('"\''))
    return out


def readable() -> dict[str, dict[str, str]]:
    """{wiki: {slug: visibility}} from every commons cut cached here."""
    out: dict[str, dict[str, str]] = {}
    if not COMMONS.exists():
        return out
    for cut in sorted(COMMONS.rglob("wiki.shared.json")):
        try:
            nodes = json.loads(cut.read_text(encoding="utf-8")).get("nodes") or []
        except Exception:                                  # noqa: BLE001
            continue
        name = cut.relative_to(COMMONS).parts[0]
        for n in nodes:
            slug = n.get("slug") or n.get("id")
            if not slug:
                continue
            # A page in a commons cut may have been contributed from elsewhere; it is
            # readable here either way, which is the only question this asks.
            out.setdefault(n.get("origin") or name, {})[slug] = n.get("visibility") or "internal"
            out.setdefault(name, {})[slug] = n.get("visibility") or "internal"
    return out


def audit():
    seen = readable()
    problems, edges = [], 0
    for p in sorted(WIKI.rglob("*.md")):
        block = frontmatter(p.read_text(encoding="utf-8", errors="ignore"))
        if block is None:
            continue
        targets = entries(block)
        if not targets:
            continue
        here = field(block, "visibility") or "private"
        rel = p.relative_to(ROOT)
        for t in targets:
            edges += 1
            if not ENTRY.match(t):
                problems.append((rel, t, "not in the form wiki-name/slug"))
                continue
            wiki, slug = t.split("/", 1)
            if wiki == ROOT.name:
                problems.append((rel, t, "points at this wiki; same_as is for other wikis"))
                continue
            if OPENNESS.get(here, 0) == 0:
                continue                                   # private carrier: nothing can leak
            known = seen.get(wiki, {})
            if not known:
                problems.append((rel, t, f"this wiki reads no cut of {wiki}, so the claim "
                                         f"cannot be checked from here"))
                continue
            if slug not in known:
                problems.append((rel, t, f"no page {slug} in the cut of {wiki} read here"))
                continue
            there = known[slug]
            if OPENNESS.get(there, 0) < OPENNESS.get(here, 0):
                problems.append((rel, t, f"a {here} page may not name a {there} one"))
    return problems, edges


def main(argv) -> int:
    problems, edges = audit()
    if not problems:
        print(f"same_as OK — {edges} edge(s) declared, every one within the boundary.")
        return 0
    print(f"same_as — {len(problems)} of {edges} edge(s) refused\n")
    for rel, target, why in problems:
        print(f"  {rel}")
        print(f"     same_as: {target}")
        print(f"     {why}")
    print("\n  Identity is symmetric; recording it is not. A page may only name a target at\n"
          "  least as open as itself, because naming a page publishes that it exists.")
    return 1 if "--check" in argv else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
