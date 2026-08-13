#!/usr/bin/env python3
"""
contribute.py — prepare a page for the shared commons, safely.

The flow up from a personal wiki to `YOUR-COMMONS`. It is deliberately the same consent
loop as everything else: this script only ever writes a **staging bundle** to disk. It
does not push, does not open a PR, and cannot reach the commons on its own.

What it guarantees, so the skill does not have to be careful:

  * **`private` never contributes.** Refused outright — not filtered later, refused here.
  * **CRM never contributes.** Path-level refusal, independent of the tier.
  * **Frontmatter is rebuilt from a whitelist**, never copied. A YAML comment can hide a
    private page's title, and copying would carry it across.
  * **Links to private pages are redacted** in body and frontmatter alike.
  * **Provenance is stamped, never invented**: who contributed it, which wiki it came
    from, and the exact source revision.
  * **Validation is re-based** (see below).
  * **The sensitive-term scan runs on the bundle** before anything leaves.

Why validation is re-based
--------------------------
`peer` and `collective` mean *this group* stood behind a page. Carried into a different
group unchanged, they would assert agreement that never happened — the commons would
inherit a consensus it was never party to. So:

    machine    -> machine     (nobody has stood behind it anywhere)
    self       -> self        (the author still stands behind it; that travels)
    peer       -> self        (re-earn it here)
    collective -> self        (re-earn it here)

The author's own confirmation is portable. Other people's is not.

Usage:
  python3 tools/contribute.py <slug> [<slug> ...]      # stage into contrib/
  python3 tools/contribute.py <slug> --by gurden       # set contributed_by
  python3 tools/contribute.py --list                   # what is eligible
  python3 tools/contribute.py <slug> --out /tmp/bundle
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export            # noqa: E402
import export_shared     # noqa: E402

DEFAULT_OUT = "contrib"
ORIGIN = "YOUR-WIKI"

# Whole areas that never travel, whatever their tier says.
REFUSE_PATH_PREFIXES = ("crm/",)

# Validation levels are group-relative above `self`; see the module docstring.
VALIDATION_REBASE = {"machine": "machine", "self": "self",
                     "peer": "self", "collective": "self"}


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def eligible(slug, fm):
    """(ok, reason) — may this page be contributed at all?"""
    if any(slug.startswith(p) for p in REFUSE_PATH_PREFIXES):
        return False, "CRM / relationship data never enters the commons"
    vis = fm.get("visibility", "private")
    if vis == "private":
        return False, ("marked `private` — promote it to `internal` deliberately first, "
                       "which is a disclosure decision and belongs to a person")
    return True, f"{vis} — eligible"


def build_bundle(wiki_dir, slugs, contributed_by, rev):
    """Return {relpath: text} for the staged contribution, or raise ValueError."""
    nodes, title_to_slug = export.build_nodes(wiki_dir)
    public, private_slugs = export.make_public(
        nodes, title_to_slug, hide=export.HIDE_FROM_SHARED)
    private_titles = {nodes[s]["title"] for s in private_slugs
                      if isinstance(nodes[s].get("title"), str)}

    def clean(value):
        stripped = export._strip_private_links(value, title_to_slug, private_slugs)
        if export._norm_title(stripped) in private_titles:
            return ""
        return stripped

    out = {}
    for slug in slugs:
        path = os.path.join(wiki_dir, slug + ".md")
        if not os.path.exists(path):
            raise ValueError(f"no such page: {slug}")
        fm, _body = export.split_frontmatter(export_shared._read(path))
        if fm is None:
            raise ValueError(f"{slug}: no frontmatter")

        ok, why = eligible(slug, fm)
        if not ok:
            raise ValueError(f"{slug}: refused — {why}")
        if slug not in public:
            raise ValueError(f"{slug}: excluded by the boundary filter (private)")

        # Rebuild frontmatter from the whitelist — never copy the raw block.
        text = export_shared._emit_frontmatter(fm, clean)

        # Stamp provenance and re-based validation. These lines are appended inside the
        # block, before the closing delimiter, so the whitelist stays authoritative.
        rebased = VALIDATION_REBASE.get(fm.get("validation", "machine"), "machine")
        prov = [f"validation: {rebased}",
                f"contributed_by: {contributed_by}",
                f"origin: {ORIGIN}",
                f"origin_rev: {rev}"]
        lines = text.split("\n")
        assert lines[-1] == "---"
        text = "\n".join(lines[:-1] + prov + ["---"])

        body = public[slug]["body"].lstrip("\n")
        out[os.path.join("wiki", slug + ".md")] = text + "\n\n" + body
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage pages for contribution to the commons.")
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--by", default=None, help="who is contributing (required to stage)")
    ap.add_argument("--list", action="store_true", help="show what is eligible")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.wiki):
        print(f"error: no {args.wiki!r} directory (cwd is {os.getcwd()}).\n"
              f"       Run from the repo root.", file=sys.stderr)
        return 2

    if args.list:
        n_ok = n_no = 0
        for slug, _p, fm, _b in export.discover(args.wiki):
            ok, why = eligible(slug, fm)
            n_ok, n_no = (n_ok + 1, n_no) if ok else (n_ok, n_no + 1)
            if ok:
                print(f"  {slug}  ({why})")
        print(f"\n  eligible: {n_ok}   refused: {n_no}")
        return 0

    if not args.slugs:
        ap.error("give at least one slug, or --list")
    if not args.by:
        ap.error("--by is required: provenance is stamped, never invented")

    rev = git("rev-parse", "--short", "HEAD") or "unknown"
    if git("status", "--porcelain", "--", args.wiki):
        print("warning: wiki/ has uncommitted changes — origin_rev will not describe "
              "exactly what you are contributing. Commit first.", file=sys.stderr)

    try:
        bundle = build_bundle(args.wiki, args.slugs, args.by, rev)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    for rel, text in bundle.items():
        dest = os.path.join(args.out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"  staged {dest}")

    # The same tripwire that guards the web guards this boundary too.
    leak = subprocess.run([sys.executable, "tools/scan_public_leaks.py", "--paths", args.out],
                          capture_output=True, text=True)
    if leak.returncode != 0:
        print("\nERROR: the staged bundle tripped the sensitive-term scan. "
              "Nothing should leave this repo until that is understood.\n", file=sys.stderr)
        print(leak.stdout or leak.stderr, file=sys.stderr)
        return 1

    print(f"\n  {len(bundle)} page(s) staged in {args.out}/ at rev {rev}, contributed_by {args.by}.")
    print("  Nothing has left this repo. Open a PR against the commons to propose them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
