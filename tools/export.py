#!/usr/bin/env python3
"""
#
# WHY THIS FILE IS NOT IN THE SYNCED DESIGN LAYER
#
# export.py deliberately differs by ROLE, and the differences are coherent rather than
# drift. Checked 2026-09-02: every repo`s export workflow matches its own export.py, so
# nothing here is broken.
#
#   * A commons (xco-team-wiki, learning-system-wiki, power-project-wiki, fang-llm-wiki)
#     also emits wiki.shared.json -- public + unlisted + internal -- because spokes sync
#     FROM it, and carries origin/contributed provenance for the federation view.
#   * A personal spoke and the template emit the public cut only. Nobody syncs from them,
#     so a shared cut would be an unused file.
#
# Do NOT "fix" this by adding the file to SHARED in sync_design_system.py. That would push
# one role`s exporter onto every repo and give five of them a cut nobody reads. The cost of
# the split is that a genuine bug must be propagated by hand -- as the bracket-list comment
# fix in _parse_value was, on 2026-09-02, to nine repos at once.
export.py — turn the wiki into a JSON graph for the frontend "lens".

Standard library only (no dependencies) so it runs in CI and fresh cloud sessions.

Two outputs:
  export/wiki.json         — everything (stays in the repo/branch; never deployed)
  export/wiki.public.json  — public + unlisted only; every `private` page is fully
                             stripped: its node is absent, and every link edge that
                             points to or from it is absent. Private link *markup* is
                             also removed from published bodies. Unlisted pages are
                             included and flagged "visibility": "unlisted".

Modes:
  python tools/export.py           # write both exports
  python tools/export.py --check   # validate frontmatter only; exit nonzero on errors

The public-export invariant (a private page leaks nothing) is covered by
tools/test_export.py and by --check-level schema validation.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0"

REQUIRED_FIELDS = ["type", "title", "description", "tags", "status",
                   "visibility", "confidence", "timestamp", "sources"]
ALLOWED_TYPE = {"entity", "concept", "summary", "comparison", "overview", "synthesis",
                "goal", "commitment"}
ALLOWED_VISIBILITY = {"public", "unlisted", "internal", "private"}

# Two boundaries, deliberately distinct:
#   HIDE_FROM_WEB   — what never reaches the open web (Pages site + public JSON graph).
#   HIDE_FROM_SHARED — what never reaches the colleague mirror either.
# `internal` sits between: shared with trusted colleagues, never published.
HIDE_FROM_WEB = frozenset({"private", "internal"})
HIDE_FROM_SHARED = frozenset({"private"})
ALLOWED_LAYER = {"goal", "portfolio", "mechanism", "sequence"}

# Validation — who has stood behind a page, as distinct from what the page claims
# about its own evidence (that is `confidence`). A well-sourced page nobody has
# confirmed is a different object from a hunch the group has endorsed, and the
# gravity weighting treats them differently.
#   machine    — written or filed by the model; nobody has confirmed it yet
#   self       — the author confirmed it
#   peer       — another member confirmed it
#   collective — reviewed together
ALLOWED_VALIDATION = {"machine", "self", "peer", "collective"}

# Commitment lifecycle. `declined` is FIRST-CLASS and non-penalised: refusing is a valid
# outcome, and a ledger that renders a decline as a failure teaches people not to answer.
# `exited` likewise — leaving a commitment deliberately is not the same as letting it lapse.
ALLOWED_COMMITMENT_STATE = {"proposed", "held", "honoured", "revised",
                            "lapsed", "exited", "declined"}
# States that represent a commitment nobody is carrying any more, but which are NOT
# failures. Only `lapsed` is a failure — the commitment fell over without a decision.
NON_FAILURE_CLOSED = {"honoured", "exited", "declined"}
DEFAULT_VALIDATION = "machine"
ALLOWED_HORIZON = {"near", "mid", "far"}

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")


# --------------------------------------------------------------------------- #
# Frontmatter parsing (minimal, tolerant, stdlib-only)
# --------------------------------------------------------------------------- #

def split_frontmatter(text):
    """Return (frontmatter_dict_or_None, body). Pages without a leading --- block
    (index.md, log.md, README stubs) return (None, text) and are treated as
    non-nodes — skipped, not errors."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    return parse_frontmatter(parts[1]), parts[2].lstrip("\n")


def _strip_inline_comment(value):
    # Cut a trailing " # comment" from a scalar value (used e.g. by the
    # visibility field). Only applied to bare scalars, never to bracket lists.
    m = re.search(r"\s+#", value)
    return value[:m.start()] if m else value


def _parse_value(raw):
    raw = raw.strip()
    # A bracket list may carry a trailing comment: `sources: []   # why it is empty`.
    # Without this the value fails the endswith("]") test below, falls through to the
    # scalar branch, and the whole string becomes a one-element list -- so an EMPTY
    # sources list turns into the phantom source "[]", which check_sources.py then
    # hunts for on disk. Cutting only after the LAST "]" keeps a "#" that legitimately
    # sits inside the list, which is why the comment stripper is not used here.
    if raw.startswith("[") and not raw.endswith("]") and "]" in raw:
        after = raw[raw.rfind("]") + 1:]
        if after.lstrip().startswith("#"):
            raw = raw[:raw.rfind("]") + 1]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        # comma-separated; tolerant of the odd path/tag. (Node schema does not
        # depend on perfect source-list splitting.)
        return [_unquote(x.strip()) for x in inner.split(",") if x.strip()]
    return _unquote(_strip_inline_comment(raw).strip())


def _unquote(s):
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    return s


def parse_frontmatter(fm):
    data = {}
    for line in fm.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s?(.*)$", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        data[key] = _parse_value(raw)
    return data


# --------------------------------------------------------------------------- #
# Discovery + node building
# --------------------------------------------------------------------------- #

def discover(wiki_dir):
    """Yield (slug, abspath, frontmatter, body) for every .md page with frontmatter."""
    for root, _dirs, files in os.walk(wiki_dir):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, wiki_dir)
            slug = rel[:-3]  # drop .md; keeps subdir, e.g. "examples/greenline-summary"
            with open(path, encoding="utf-8") as fh:
                fm, body = split_frontmatter(fh.read())
            if fm is None:
                continue  # navigation/stub file, not a content node
            yield slug, path, fm, body


def _norm_title(s):
    """Normalize a link target so it can match a page title.

    Two authoring realities to absorb:
      * a [[link]] wrapped across source lines — collapse internal whitespace, since
        titles live on one frontmatter line;
      * a [[Target\\|alias]] inside a markdown table — escaping the pipe there is
        CORRECT authoring (an unescaped | would split the cell), but it leaves a
        trailing backslash on the target, so strip it.
    Without this the link silently fails to resolve (and, for private pages, to redact).
    """
    return re.sub(r"\s+", " ", s).strip().rstrip("\\").strip()


def extract_links(body):
    """Return list of (target_title, display) from [[Title]] / [[Title|display]]."""
    out = []
    for m in WIKILINK_RE.finditer(body):
        target = _norm_title(m.group(1))
        display = (m.group(2) or "").strip()
        out.append((target, display))
    return out


def build_nodes(wiki_dir):
    raw = list(discover(wiki_dir))
    # title -> slug (first wins; titles are unique in practice)
    title_to_slug = {}
    for slug, _path, fm, _body in raw:
        title = fm.get("title")
        if isinstance(title, str) and title and title not in title_to_slug:
            title_to_slug[title] = slug

    nodes = {}
    for slug, _path, fm, body in raw:
        outbound = []
        for target, _disp in extract_links(body):
            tslug = title_to_slug.get(target)
            if tslug and tslug != slug and tslug not in outbound:
                outbound.append(tslug)
        node = {
            "id": slug,
            "slug": slug,
            "title": fm.get("title", slug),
            "type": fm.get("type"),
            "layer": fm.get("layer"),          # optional -> None if absent
            "parent": fm.get("parent"),        # optional
            "horizon": fm.get("horizon"),      # optional
            "tags": fm.get("tags", []),
            "confidence": fm.get("confidence"),
            "validation": fm.get("validation", DEFAULT_VALIDATION),
            "validated_by": fm.get("validated_by", []),
            "validated_at": fm.get("validated_at"),
            "contradicts": fm.get("contradicts"),
            "commits_to": fm.get("commits_to"),
            "resources": fm.get("resources"),
            "until": fm.get("until"),
            "state": fm.get("state"),
            "superseded_by": fm.get("superseded_by"),
            "devalued_by": fm.get("devalued_by"),
            "visibility": fm.get("visibility", "private"),
            "timestamp": fm.get("timestamp"),
            "description": fm.get("description"),
            "sources": fm.get("sources", []),
            "body": body.rstrip() + "\n",
            "outbound_links": outbound,
            "inbound_links": [],  # filled below
        }
        nodes[slug] = node

    _recompute_inbound(nodes)
    return nodes, title_to_slug


def _recompute_inbound(nodes):
    for n in nodes.values():
        n["inbound_links"] = []
    present = set(nodes)
    for n in nodes.values():
        n["outbound_links"] = [s for s in n["outbound_links"] if s in present]
    for slug, n in nodes.items():
        for tgt in n["outbound_links"]:
            nodes[tgt]["inbound_links"].append(slug)
    for n in nodes.values():
        n["inbound_links"] = sorted(set(n["inbound_links"]))


# --------------------------------------------------------------------------- #
# Public export (private fully stripped)
# --------------------------------------------------------------------------- #

def make_public(nodes, title_to_slug, hide=HIDE_FROM_WEB):
    """Return a new node dict with every hidden page absent, all edges to/from
    hidden pages removed, and hidden link markup stripped from bodies.

    `hide` is the set of visibility tiers to strip. Two callers, two boundaries:
      * the web export hides {private, internal} — the default;
      * the colleague mirror hides {private} only, so `internal` pages travel to
        trusted colleagues but never to the open web.
    """
    hidden_slugs = {s for s, n in nodes.items() if n["visibility"] in hide}

    public = {}
    for slug, n in nodes.items():
        if n["visibility"] in hide:
            continue
        m = json.loads(json.dumps(n))  # deep copy
        m["body"] = _strip_private_links(m["body"], title_to_slug, hidden_slugs)
        public[slug] = m

    # recompute edges over the visible set only (drops any edge touching a hidden node)
    _recompute_inbound(public)
    return public, hidden_slugs


def _strip_private_links(body, title_to_slug, private_slugs):
    """Replace [[Private Title|display]] -> display, [[Private Title]] -> [redacted],
    so neither the private title nor a navigable link to it survives in a public body."""
    def repl(m):
        target = _norm_title(m.group(1))  # robust to line-wrapped private links
        display = (m.group(2) or "").strip()
        tslug = title_to_slug.get(target)
        if tslug in private_slugs:
            return display if display else "[redacted]"
        return m.group(0)
    return WIKILINK_RE.sub(repl, body)


# --------------------------------------------------------------------------- #
# Meta + validation
# --------------------------------------------------------------------------- #

def build_meta(nodes, kind):
    by_type, by_vis = {}, {}
    for n in nodes.values():
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        by_vis[n["visibility"]] = by_vis.get(n["visibility"], 0) + 1
    ts = os.environ.get("EXPORT_TIMESTAMP") or datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,                 # "full" | "public"
        "exported_at": ts,
        "node_count": len(nodes),
        "counts_by_type": by_type,
        "counts_by_visibility": by_vis,
    }


# A wiki-link split across a source line (often with a stray blockquote ">" on the
# continuation) doesn't resolve — the target no longer matches any page title. This
# has recurred on every batch of freshly-authored pages, so it's a hard check now.
SPLIT_LINK_RE = re.compile(r"\[\[[^\]]*\n[^\]]*\]\]")


def validate(wiki_dir):
    """Return list of (slug, message) schema errors."""
    errors = []
    for slug, _path, fm, body in discover(wiki_dir):
        for f in REQUIRED_FIELDS:
            if f not in fm:
                errors.append((slug, f"missing required field: {f}"))
        t = fm.get("type")
        if t is not None and t not in ALLOWED_TYPE:
            errors.append((slug, f"invalid type: {t!r}"))
        v = fm.get("visibility")
        if v is not None and v not in ALLOWED_VISIBILITY:
            errors.append((slug, f"invalid visibility: {v!r}"))
        if "layer" in fm and fm["layer"] not in ALLOWED_LAYER:
            errors.append((slug, f"invalid layer: {fm['layer']!r}"))
        if "horizon" in fm and fm["horizon"] not in ALLOWED_HORIZON:
            errors.append((slug, f"invalid horizon: {fm['horizon']!r}"))
        if fm.get("type") == "commitment":
            st = fm.get("state")
            if st is None:
                errors.append((slug, "a commitment must declare a `state`"))
            elif st not in ALLOWED_COMMITMENT_STATE:
                errors.append((slug, f"invalid commitment state: {st!r}"))
            if not fm.get("commits_to"):
                errors.append((slug, "a commitment must name the goal it `commits_to`"))
        if "state" in fm and fm.get("type") != "commitment":
            errors.append((slug, "`state` is only meaningful on a commitment"))
        if "validation" in fm and fm["validation"] not in ALLOWED_VALIDATION:
            errors.append((slug, f"invalid validation: {fm['validation']!r}"))
        # A page validated above `machine` must say who did it: an unattributed
        # tick is indistinguishable from the model marking its own homework.
        if fm.get("validation") in {"self", "peer", "collective"} and not fm.get("validated_by"):
            errors.append((slug, f"validation {fm['validation']!r} requires validated_by"))
        for m in SPLIT_LINK_RE.findall(body):
            errors.append((slug, "newline-split wiki-link (won't resolve): "
                           + re.sub(r"\s+", " ", m).strip()))
    return errors


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def run_export(wiki_dir, out_dir):
    nodes, title_to_slug = build_nodes(wiki_dir)
    public, _private = make_public(nodes, title_to_slug)

    os.makedirs(out_dir, exist_ok=True)
    full = {"meta": build_meta(nodes, "full"),
            "nodes": [nodes[s] for s in sorted(nodes)]}
    pub = {"meta": build_meta(public, "public"),
           "nodes": [public[s] for s in sorted(public)]}
    with open(os.path.join(out_dir, "wiki.json"), "w", encoding="utf-8") as f:
        json.dump(full, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "wiki.public.json"), "w", encoding="utf-8") as f:
        json.dump(pub, f, indent=2, ensure_ascii=False)
    return full, pub


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export the wiki to a JSON graph.")
    ap.add_argument("--wiki", default="wiki", help="wiki directory (default: wiki)")
    ap.add_argument("--out", default="export", help="output directory (default: export)")
    ap.add_argument("--check", action="store_true",
                    help="validate frontmatter and exit nonzero on schema errors")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.wiki):
        print(f"error: wiki dir not found: {args.wiki}", file=sys.stderr)
        return 2

    if args.check:
        errors = validate(args.wiki)
        if errors:
            print(f"SCHEMA CHECK FAILED — {len(errors)} error(s):", file=sys.stderr)
            for slug, msg in errors:
                print(f"  {slug}: {msg}", file=sys.stderr)
            return 1
        n = sum(1 for _ in discover(args.wiki))
        print(f"schema check OK — {n} pages valid")
        return 0

    full, pub = run_export(args.wiki, args.out)
    fm, pm = full["meta"], pub["meta"]
    print(f"exported {fm['node_count']} nodes -> {args.out}/wiki.json")
    print(f"public export: {pm['node_count']} nodes "
          f"({fm['node_count'] - pm['node_count']} private stripped) "
          f"-> {args.out}/wiki.public.json")
    print(f"visibility: {fm['counts_by_visibility']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
