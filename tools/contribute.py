#!/usr/bin/env python3
"""
contribute.py — prepare a page for the shared commons, safely.

The flow up from a personal wiki to `xco-team-wiki`. It is deliberately the same consent
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
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export            # noqa: E402
import export_shared     # noqa: E402

DEFAULT_OUT = "contrib"

# Where this wiki sits in the federation. Declared in design/federation.json rather
# than assumed, because a spoke no longer belongs to exactly one commons: with
# learning-system-wiki alongside xco-team-wiki, a person can contribute to either, and
# a guess about which one is a disclosure decision made by a default.
#
# The file is per-repo and is NOT part of the synced design layer — a wiki's place in
# the graph is its own, the same way its social-card wording is.
FEDERATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "design", "federation.json")


def topology():
    """This wiki's declared role and targets.

    A repo with no declaration keeps the old single-commons behaviour, so nothing that
    predates the second commons breaks.
    """
    if os.path.exists(FEDERATION):
        with open(FEDERATION, encoding="utf-8") as fh:
            return json.load(fh)
    return {"role": "spoke",
            "contributes_to": [os.environ.get("WIKI_COMMONS", "xco-team-wiki")]}


def resolve_commons(requested, topo):
    """Which commons this contribution is for. Refuses to guess.

    Returns (name, error). With more than one target and no --to, that is an error and
    not a default: contributing to the wrong commons publishes to the wrong audience,
    and the fix afterwards is a deletion request rather than a revert.
    """
    targets = topo.get("contributes_to") or []
    if not targets:
        return None, ("this wiki contributes to no commons "
                      "(design/federation.json lists none)")
    if requested:
        if requested not in targets:
            return None, (f"{requested!r} is not a commons this wiki contributes to.\n"
                          f"       Declared: {', '.join(targets)}")
        return requested, None
    if len(targets) == 1:
        return targets[0], None
    return None, ("this wiki contributes to more than one commons, so --to is required:\n"
                  + "\n".join(f"         --to {t}" for t in targets)
                  + "\n\n       Which commons a page goes to is an audience decision; "
                    "picking one for you would make it silently.")


def _origin_repo():
    """This wiki's own name, derived from the git remote rather than hardcoded.

    Every spoke stamps its provenance with its own name. Hardcoding that means one
    hand-edit per repo and one chance to get it wrong — and a mis-stamped `origin` is
    a quiet lie about where a page came from, which is exactly what provenance exists
    to prevent. Deriving it makes a fresh spoke correct with no setup step.
    """
    url = subprocess.run(["git", "remote", "get-url", "origin"],
                         capture_output=True, text=True).stdout.strip()
    if not url:
        return "unknown-origin"
    name = url.rstrip("/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


ORIGIN = _origin_repo()

# Whole areas that never travel, whatever their tier says.
REFUSE_PATH_PREFIXES = ("crm/",)

def commons_cache_paths(name):
    """Where a cached copy of `name`'s graph might be.

    The per-commons layout comes first; the flat legacy path is the fallback, because
    the sync-commons workflow still writes a single .commons/export for whichever
    commons it is pointed at. Consequence, stated rather than hidden: with two commons
    declared and the flat cache in use, the collision check below covers only the one
    the workflow syncs — and check_collisions() says so when it cannot verify.
    """
    return [os.path.join(".commons", name, "export", "wiki.shared.json"),
            os.path.join(".commons", name, "export", "wiki.public.json"),
            os.path.join(".commons", "export", "wiki.shared.json"),
            os.path.join(".commons", "export", "wiki.public.json")]

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


def commons_titles(name):
    """Titles already in `name`, from the cached export. None if no cache."""
    for path in commons_cache_paths(name):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            nodes = d.get("nodes", {})
            nodes = list(nodes.values()) if isinstance(nodes, dict) else nodes
            return {n.get("title") for n in nodes if isinstance(n.get("title"), str)}
    return None


def check_collisions(wiki_dir, slugs, commons):
    """Titles among `slugs` that the commons already holds.

    Contributing a page the commons already has OVERWRITES it — silently losing any
    edit the commons made after it arrived, and dropping provenance the commons added.
    That is the two-canons problem at the moment of contribution, and it is invisible
    in the staged bundle: the file looks fine, it just replaces a different one.

    Nearly every page in a seeded spoke collides, so this cannot be a warning nobody
    reads. It refuses, and --update is the deliberate override.
    """
    theirs = commons_titles(commons)
    if theirs is None:
        return None, []            # no cache; cannot check, say so rather than assume
    hits = []
    for slug, _p, fm, _b in export.discover(wiki_dir):
        if slug in slugs and fm.get("title") in theirs:
            hits.append((slug, fm.get("title")))
    return theirs, hits


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
    ap.add_argument("--to", default=None,
                    help="which commons to contribute to; required when this wiki "
                         "declares more than one")
    ap.add_argument("--update", action="store_true",
                    help="the page already exists in the commons and you mean to replace it")
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
        t = topology()
        print(f"  role: {t.get('role', 'spoke')}   "
              f"contributes to: {', '.join(t.get('contributes_to') or ['(none)'])}")
        return 0

    if not args.slugs:
        ap.error("give at least one slug, or --list")
    if not args.by:
        ap.error("--by is required: provenance is stamped, never invented")

    topo = topology()
    commons, err = resolve_commons(args.to, topo)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    # Refuse a silent overwrite before doing any work.
    theirs, hits = check_collisions(args.wiki, set(args.slugs), commons)
    if theirs is None:
        print(f"note: no cached graph for {commons} (.commons/), so a page that already\n"
              f"      exists there cannot be detected. Run the 'Sync the commons' workflow\n"
              f"      to enable the check, or review the PR diff carefully.", file=sys.stderr)
    elif hits and not args.update:
        print("error: these pages ALREADY EXIST in the commons — contributing would "
              "overwrite them:\n", file=sys.stderr)
        for slug, title in hits:
            print(f"         {slug}\n           -> {title!r}", file=sys.stderr)
        print("\n       The commons may have edited its copy since. Overwriting loses that\n"
              "       silently, which is the two-canons failure this federation exists to\n"
              "       avoid.\n\n"
              "       If the commons copy is stale and yours should replace it, say so\n"
              "       deliberately:  --update  (the reviewer then sees the diff and decides).\n"
              "       If not, reference the commons page instead of re-contributing it.",
              file=sys.stderr)
        return 1
    elif hits:
        print(f"warning: {len(hits)} page(s) already in the commons will be REPLACED. "
              f"Say so in the PR body so the reviewer checks the diff.\n", file=sys.stderr)

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
    print(f"  Nothing has left this repo. Open a PR against {commons} to propose them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
