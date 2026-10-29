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
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export            # noqa: E402
import export_shared     # noqa: E402

DEFAULT_OUT = "contrib"

# ---------------------------------------------------------------------------
# Source paths never travel.
#
# Added 2026-10-29 by Fang, after a page that had had a person's name carefully removed
# from its body still named him three times in its citations, inside a source filename.
# Every other guarantee in this file had held. The leak walked out through a file path,
# which nothing was reading, because in most wikis a source path is a document and not an
# event. (The filename itself is deliberately not quoted here: this file travels to every
# wiki.)
#
# In a transcript-based wiki a filename IS a record: who met, when, and what about. And it
# is worse than the same fact in prose, because a reader skims a path without registering
# that they have just been told who was in a private room.
#
# So the rule is structural rather than detective. The tool does not try to recognise a
# name — it cannot, and a list of names to watch for would be a second codebook. Instead
# **no `raw/` path survives staging at all**, whatever it contains. Each becomes a dated
# reference, which is the provenance that can actually be checked from the commons anyway:
# the source file is not there to open.
#
# A label may be declared per source in design/source-labels.json, mapping a basename to a
# short descriptor that is safe to say out loud ("fortnightly session"). With no label the
# reference is bare and dated. Both forms are honest; the labelled one is kinder to read.
#
# Two additions for the shared copy, agreed with Gurden on 2026-10-29 (fang-llm-wiki#154 is
# the original). Measured that day, refusing every source without a leading date would have
# blocked sharing for half or more of the shareable pages in most wikis, because many
# filenames carry their date at the end and `raw/` is never renamed. So:
#   * a date anywhere in the filename counts, the first one found;
#   * a source with no date and no label becomes "an undated source", rather than refusing
#     the page. Nothing leaks either way; the citation is only vaguer.
# And one tightening: a path written inside backticks may contain spaces (`raw/A Name.md`),
# which the plain pattern would cut short and leave half a filename behind. Backticked paths
# are replaced whole, first.
SOURCE_LABELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "design", "source-labels.json")

RAW_PATH_RE = re.compile(r"raw/[^\s,\]\)\"'`]+")
TICKED_RAW_RE = re.compile(r"`raw/[^`\n]+`")
DATE_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
YAML_SEQ_RE = re.compile(r"^\s*[A-Za-z_][\w-]*:\s*\[")
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def source_labels():
    try:
        with open(SOURCE_LABELS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str) and not k.startswith("_")}


def dated_reference(path, labels):
    """`raw/2026-10-20-fortnightly-summary.md` -> `fortnightly session, 20 October 2026`."""
    base = os.path.basename(path.rstrip("/"))
    label = labels.get(base) or labels.get(path)
    m = DATE_RE.search(base)
    when = None
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31:
        when = f"{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]} {m.group(1)}"
    if label:
        return f"{label}, {when}" if when else label
    return f"source dated {when}" if when else "an undated source"


def strip_source_paths(text, labels):
    """Replace every raw/ path with a dated reference, and prove none survived.

    A dated reference contains a comma, which is an item separator inside a YAML flow
    sequence — so a reference substituted into `sources: [...]` unquoted would silently
    split one source into two. Lines that carry YAML list items get quoted replacements;
    prose gets bare ones. A path inside backticks is replaced whole, spaces and all.
    """
    in_frontmatter = text.startswith("---\n")
    lines, out_lines = text.split("\n"), []
    seen_close = False
    for line in lines:
        if in_frontmatter and not seen_close and out_lines and line.strip() == "---":
            seen_close = True
        quote = bool(in_frontmatter and not seen_close and (
            YAML_SEQ_RE.match(line) or line.lstrip().startswith("- ")))

        def ref(path):
            r = dated_reference(path, labels)
            return f'"{r}"' if quote else r

        line = TICKED_RAW_RE.sub(lambda m: ref(m.group(0)[1:-1]), line)
        out_lines.append(RAW_PATH_RE.sub(lambda m: ref(m.group(0)), line))
    out = "\n".join(out_lines)
    leftover = re.search(r"raw/[A-Za-z0-9]", out)
    if leftover:
        raise ValueError(f"a source path survived staging near "
                         f"{out[leftover.start():leftover.start() + 40]!r}. Nothing staged.")
    return out


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
    # A commons this wiki READS but may not push to. Naming it is not an oversight to be
    # helpfully worked around; it is the whole point of the declaration, so say which it is.
    readonly = [c for c in (topo.get("reads_from") or []) if c not in targets]
    if not targets:
        hint = (f"\n       It reads {', '.join(readonly)} but may not contribute to "
                f"{'it' if len(readonly) == 1 else 'them'}.") if readonly else ""
        return None, ("this wiki contributes to no commons "
                      "(design/federation.json lists none)" + hint)
    if requested:
        if requested in readonly:
            return None, (f"{requested!r} is a commons this wiki READS and may not write to.\n"
                          f"       design/federation.json lists it under `reads_from`, not "
                          f"`contributes_to`.\n"
                          f"       That is a deliberate one-way link. If it should become "
                          f"two-way, a person changes the declaration.")
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
    # An allowlist since 2026-09-29: `Private`, `confidential` or a typo is not a tier.
    if vis not in CONTRIBUTABLE:
        return False, f"tier {vis!r} is not one of {sorted(CONTRIBUTABLE)} — fix the label first"
    return True, f"{vis} — eligible"


CONTRIBUTABLE = frozenset({"internal", "unlisted", "public"})

# Stamped into frontmatter as a bare scalar, so it must not be able to carry a newline, a
# colon or a comment into the block (review, 2026-09-29). A name, and nothing else.
# fullmatch, because `$` also matches before a trailing newline; and a hyphen only between
# letters, because `---` is the frontmatter delimiter (both found by review the same day).
BY_RE = re.compile(r"[A-Za-z][A-Za-z.' ]*(?:-[A-Za-z.' ]+)*")


def valid_by(name):
    return bool(name) and len(name) <= 80 and bool(BY_RE.fullmatch(name))


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


def title_key(title):
    """A title reduced to what two wikis would have to agree on to mean the same page.

    Case and punctuation are dropped: a commons holding "Butterfly Institution" and a
    spoke holding "Butterfly institution" are two names for one page, and treating them
    as different is how a commons ends up with both. False matches fail safe — the tool
    refuses and `--update` is the deliberate override.
    """
    if not isinstance(title, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def check_collisions(wiki_dir, slugs, commons):
    """Titles among `slugs` that the commons already holds.

    Contributing a page the commons already has OVERWRITES it — silently losing any
    edit the commons made after it arrived, and dropping provenance the commons added.
    That is the two-canons problem at the moment of contribution, and it is invisible
    in the staged bundle: the file looks fine, it just replaces a different one.

    Nearly every page in a seeded spoke collides, so this cannot be a warning nobody
    reads. It refuses, and --update is the deliberate override.

    The comparison is case- and punctuation-insensitive. It was exact until 2026-10-29,
    when "Butterfly institution" and "Mission equity" staged cleanly against a commons
    already holding "Butterfly Institution" and "Mission Equity" — a one-character
    difference, and the check that exists to stop two canons would have made two. A
    collision detector that only finds identical strings finds the easy half.
    """
    theirs = commons_titles(commons)
    if theirs is None:
        return None, []            # no cache; cannot check, say so rather than assume
    by_norm = {title_key(x): x for x in theirs if isinstance(x, str)}
    hits = []
    for slug, _p, fm, _b in export.discover(wiki_dir):
        if slug not in slugs:
            continue
        title = fm.get("title")
        match = by_norm.get(title_key(title))
        if match:
            hits.append((slug, match))
    return theirs, hits


def build_bundle(wiki_dir, slugs, contributed_by, rev):
    """Return {relpath: text} for the staged contribution, or raise ValueError."""
    labels = source_labels()
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
        backers = fm.get("validated_by") or []
        backers = backers if isinstance(backers, list) else [backers]
        # Validation travels with the names behind it, or not at all. `self` without
        # `validated_by` fails the commons' own schema check, so a stood-behind page used to
        # land red (review, 2026-09-29); one with nobody named was never really stood behind.
        if rebased != "machine" and not backers:
            rebased = "machine"
        prov = [f"validation: {rebased}"]
        if rebased != "machine":
            prov.append(f"validated_by: {export_shared._yaml_list([clean(str(b)) for b in backers])}")
            if fm.get("validated_at"):
                prov.append(f"validated_at: {export_shared._yaml_scalar(clean(str(fm['validated_at'])))}")
        prov += [f"contributed_by: {contributed_by}",
                f"origin: {ORIGIN}",
                f"origin_rev: {rev}"]
        lines = text.split("\n")
        if lines[-1] != "---":   # an assert vanishes under python -O, and a malformed bundle would be staged
            raise ValueError(f"{slug}: frontmatter did not end where expected; nothing staged")
        text = "\n".join(lines[:-1] + prov + ["---"])

        body = public[slug]["body"].lstrip("\n")
        staged = text + "\n\n" + body
        try:
            staged = strip_source_paths(staged, labels)
        except ValueError as exc:
            raise ValueError(f"{slug}: {exc}")
        out[os.path.join("wiki", slug + ".md")] = staged
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
    if not valid_by(args.by):
        ap.error("--by must be a plain name (letters, spaces, . ' -), up to 80 characters")

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
