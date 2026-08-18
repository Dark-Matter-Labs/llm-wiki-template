#!/usr/bin/env python3
"""
check_ingest_conformance.py — judge a page the way a second model must be judged.

Build Spec v2's P1.5. The goal is to prove the wiki's workflows run on a non-Anthropic
model, so the corpus is not hostage to one provider.

**Why this exists rather than a diff.** Two models will never write the same summary, so
text equality is the wrong assertion — it would fail on a perfectly good page. What can be
asserted is whether the output obeys the corpus's own rules: valid frontmatter, resolving
links, real citations, and an actual cascade into the pages it touches. A model that
produces a well-formed, well-cited, properly-cascaded page is usable, whatever its prose
sounds like.

This is deliberately model-agnostic: point it at any page produced by any model.

    python3 tools/check_ingest_conformance.py wiki/some-new-summary.md
    python3 tools/check_ingest_conformance.py wiki/a.md --baseline wiki/b.md
    python3 tools/check_ingest_conformance.py wiki/a.md --json

Exit 0 if the page conforms, 1 if not, 2 on a usage error.
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402

# A summary that cites nothing is the classic failure mode of a weaker model: fluent,
# plausible, ungrounded. Citation density is the cheapest signal that it read the source.
MIN_CITATIONS = 2
# An ingest that touches nothing has not cascaded — it has filed a page and stopped.
MIN_CASCADE = 1


def check(page_path, wiki_dir="wiki", since=None):
    """Return (results, ok). Each result is (name, passed, detail)."""
    out = []
    if not os.path.exists(page_path):
        return [("page exists", False, f"no such file: {page_path}")], False

    text = open(page_path, encoding="utf-8").read()
    fm, body = export.split_frontmatter(text)
    slug = os.path.relpath(page_path, wiki_dir)[:-3]

    # 1. schema — the same gate every page passes
    errs = [m for s, m in export.validate(wiki_dir) if s == slug]
    out.append(("frontmatter valid", not errs, "; ".join(errs) or "clean"))

    if fm is None:
        return out, False

    # 2. links resolve. A plausible-looking [[link]] to a page that does not exist is the
    #    single most common way a generated page degrades the graph.
    # Links are written as TITLES and nodes are keyed by SLUG, so resolve through
    # title_to_slug — comparing the two directly reports every good link as dangling.
    nodes, title_to_slug = export.build_nodes(wiki_dir)
    norm = {export._norm_title(t): sl for t, sl in title_to_slug.items()}
    targets = [t for t, _d in export.extract_links(body)]
    dangling = [t for t in targets if export._norm_title(t) not in norm]
    out.append(("every [[link]] resolves",
                not dangling,
                f"{len(targets)} links, {len(dangling)} dangling"
                + (f": {dangling[:3]}" if dangling else "")))

    # 3. citations exist AND point at real files. Inventing a source is worse than
    #    omitting one, so both are checked.
    cites = re.findall(r"\(raw/([^)]+?)\)", body)
    missing = [c for c in set(cites) if not os.path.exists(os.path.join("raw", c))]
    out.append(("cites its sources", len(cites) >= MIN_CITATIONS,
                f"{len(cites)} inline citations (need {MIN_CITATIONS})"))
    out.append(("every citation is a real file", not missing,
                f"{len(missing)} invented" + (f": {missing[:3]}" if missing else "")))

    # 4. sources: frontmatter agrees with the body
    declared = fm.get("sources") or []
    declared = [declared] if isinstance(declared, str) else declared
    undeclared = {f"raw/{c}" for c in cites} - set(declared)
    out.append(("body cites only declared sources", not undeclared,
                f"{len(undeclared)} undeclared" + (f": {sorted(undeclared)[:2]}" if undeclared else "")))

    # 5. the cascade — did anything else change? An ingest that files one page and updates
    #    nothing has not done the job the skill describes.
    if since:
        changed = subprocess.run(["git", "diff", "--name-only", since, "--", wiki_dir],
                                 capture_output=True, text=True).stdout.split()
        others = [c for c in changed if not c.endswith(os.path.basename(page_path))]
        out.append((f"cascaded into other pages (since {since})",
                    len(others) >= MIN_CASCADE,
                    f"{len(others)} other pages touched (need {MIN_CASCADE})"))

    # 6. honest defaults — a model must not award itself validation it cannot grant
    v = fm.get("validation", "machine")
    out.append(("validation is machine or self", v in {"machine", "self"},
                f"validation: {v!r}"
                + ("  <- only a person can award peer/collective" if v not in {"machine", "self"} else "")))

    return out, all(p for _n, p, _d in out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a generated page against the corpus's rules.")
    ap.add_argument("page")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--since", help="git ref to measure the cascade against (e.g. HEAD~1)")
    ap.add_argument("--baseline", help="a page from the other model, checked the same way")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.wiki):
        print(f"error: no {args.wiki!r} directory (cwd is {os.getcwd()}).", file=sys.stderr)
        return 2

    results, ok = check(args.page, args.wiki, args.since)
    payload = {"page": args.page, "conforms": ok,
               "checks": [{"name": n, "pass": p, "detail": d} for n, p, d in results]}

    if args.baseline:
        b_results, b_ok = check(args.baseline, args.wiki, args.since)
        payload["baseline"] = {"page": args.baseline, "conforms": b_ok,
                               "checks": [{"name": n, "pass": p, "detail": d} for n, p, d in b_results]}

    if args.json:
        print(json.dumps(payload, indent=1))
        return 0 if ok else 1

    print(f"conformance — {args.page}\n")
    for n, p, d in results:
        print(f"  {'PASS' if p else 'FAIL'}  {n}\n        {d}")
    if args.baseline:
        print(f"\nbaseline — {args.baseline}\n")
        for n, p, d in payload["baseline"]["checks"]:
            print(f"  {'PASS' if p else 'FAIL'}  {n}\n        {d}")
        print(f"\n  Both conform: {ok and payload['baseline']['conforms']}")
        print("  Conformance is not quality. Run `delta` between the two pages for that —\n"
              "  and remember the honest outcome may be 'usable for ingest, not synthesis'.")
    print()
    print("  CONFORMS." if ok else "  DOES NOT CONFORM.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
