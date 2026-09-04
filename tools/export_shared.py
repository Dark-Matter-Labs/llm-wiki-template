#!/usr/bin/env python3
"""
export_shared.py — build the *shared* cut of the wiki as readable markdown.

This is the "colleagues can read it, but only the shareable part" tier. It emits a
directory of markdown pages containing ONLY non-private pages (public + unlisted),
so it can be pushed to a separate, colleague-readable repo. It is the access-boundary
sibling of export.py (which produces the JSON graph for the frontend lens).

Hard invariant — a `private` page leaks NOTHING into the shared output:
  * its page file is absent,
  * its title never appears (not as a filename, not in the index, not in any body),
  * links pointing to it are redacted (reusing export.make_public's exact policy),
  * a `parent:` that names a private page is dropped.
Also excluded entirely: raw/ (never touched here), log.md (references private titles),
and the real index.md (lists every private page). A fresh index is generated from the
shared set only.

Standard library only. Reuses export.py so the redaction policy has one source of truth.

Usage:
  python tools/export_shared.py                 # write ./shared
  python tools/export_shared.py --out DIR       # write DIR
  python tools/export_shared.py --wiki wiki --out shared
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402  (build_nodes, make_public, split_frontmatter, WIKILINK_RE)


def wiki_display_name():
    """Human label for this wiki, e.g. "Indy's LLM Wiki".

    Read from design/federation.json rather than hardcoded, because that one string was
    the only thing making this file repo-specific -- and so the only reason it could not
    join the synced design layer. It had already drifted into two versions across ten
    repos, which is how a fix to one of them fails to reach the other nine.

    federation.json is the right home: it is per-repo and deliberately NOT synced, since
    a wiki's position in the graph does not travel between wikis. Neither does its name.
    """
    import json
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.path.dirname(here), "design", "federation.json")
    try:
        with open(path, encoding="utf-8") as f:
            fed = json.load(f)
    except (OSError, ValueError):
        return "this LLM Wiki"
    return fed.get("display_name") or fed.get("name") or "this LLM Wiki"

# Order sections in the generated index by page type.
TYPE_SECTIONS = [
    ("overview", "Overview & synthesis"),
    ("synthesis", "Overview & synthesis"),
    ("entity", "Entities"),
    ("concept", "Concepts"),
    ("comparison", "Comparisons"),
    ("summary", "Source summaries"),
]


# Frontmatter is REBUILT (not copied) from this whitelist. Rebuilding drops YAML
# comments and any stray fields — a raw copy would leak private titles/links hidden
# in `#` comment lines. Order mirrors the schema in CLAUDE.md.
FM_STRING_FIELDS = ["type", "title", "description", "status", "visibility",
                    "confidence", "timestamp", "layer", "parent", "horizon",
                    # Ledger fields, added 2026-09-02. The whitelist predated the
                    # goal/commitment schema, so a contributed commitment arrived with no
                    # commits_to / state / resources / until -- and the receiving repo's
                    # own schema check REQUIRES commits_to and state on a commitment. The
                    # contribution would therefore have landed red in the commons, which
                    # is why the ledger had never successfully moved off a personal wiki.
                    #
                    # These pass through clean() like every other field, so a commits_to
                    # naming a PRIVATE goal is blanked rather than published. That then
                    # fails the receiving schema check by design: better a loud refusal
                    # than a commitment quietly pointing at a goal nobody can see.
                    "commits_to", "resources", "until", "state"]
FM_LIST_FIELDS = ["tags", "sources"]
FM_OPTIONAL = {"layer", "parent", "horizon",
               "commits_to", "resources", "until", "state"}


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _needs_quote(s):
    return (s == "" or s[0] in "-?:,[]{}#&*!|>'\"%@`" or s[-1] in " \t"
            or ": " in s or " #" in s or any(c in s for c in "\"[]{}|>"))


def _yaml_scalar(s):
    if not _needs_quote(s):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_list(items):
    return "[" + ", ".join(_yaml_scalar(str(x)) for x in items) + "]"


def _emit_frontmatter(fm, clean):
    """Rebuild a clean frontmatter block from whitelisted fields only.
    `clean` maps a raw string value -> private-link-stripped value."""
    lines = ["---"]
    for key in FM_STRING_FIELDS:
        if key not in fm:
            if key in FM_OPTIONAL:
                continue
            val = ""  # keep required fields present even if somehow missing
        else:
            val = fm[key]
        if isinstance(val, list):  # defensive: a scalar field parsed as list
            val = " ".join(str(x) for x in val)
        val = clean(str(val))
        if key in FM_OPTIONAL and val == "":
            continue
        lines.append(f"{key}: {_yaml_scalar(val)}")
    for key in FM_LIST_FIELDS:
        items = fm.get(key, [])
        if not isinstance(items, list):
            items = [items] if items else []
        lines.append(f"{key}: {_yaml_list(items)}")
    lines.append("---")
    return "\n".join(lines)


def build_shared(wiki_dir):
    """Return (shared_files, index_markdown, private_titles).

    shared_files: dict {relpath -> file_text} for every non-private page. Frontmatter
    is rebuilt from a whitelist (comments dropped); string fields and the body are
    private-link-stripped; a `parent:` naming a private page is dropped.
    """
    nodes, title_to_slug = export.build_nodes(wiki_dir)
    # The mirror's boundary is narrower than the web's: `internal` pages DO travel to
    # trusted colleagues (that is the tier's whole purpose), `private` never does.
    public, private_slugs = export.make_public(
        nodes, title_to_slug, hide=export.HIDE_FROM_SHARED)
    private_titles = {nodes[s]["title"] for s in private_slugs
                      if isinstance(nodes[s].get("title"), str)}

    def clean(value):
        # redact any [[private link]] hiding in a frontmatter string (e.g. description),
        # then drop a value that IS exactly a private title (used to null a private parent).
        stripped = export._strip_private_links(value, title_to_slug, private_slugs)
        if export._norm_title(stripped) in private_titles:
            return ""
        return stripped

    shared_files = {}
    for slug in sorted(public):
        src_path = os.path.join(wiki_dir, slug + ".md")
        fm, _body = export.split_frontmatter(_read(src_path))
        if fm is None:
            continue  # defensive; nodes always have frontmatter
        clean_body = public[slug]["body"]  # already private-link-stripped by make_public
        text = _emit_frontmatter(fm, clean) + "\n\n" + clean_body.lstrip("\n")
        shared_files[os.path.join("wiki", slug + ".md")] = text

    index_md = _build_index(public)
    return shared_files, index_md, private_titles


def _build_index(public):
    """Generate a fresh index listing ONLY shared pages, grouped by type."""
    # de-duplicate section titles while preserving order
    section_order = []
    for _t, label in TYPE_SECTIONS:
        if label not in section_order:
            section_order.append(label)
    type_to_label = {t: label for t, label in TYPE_SECTIONS}

    buckets = {label: [] for label in section_order}
    other = []
    for slug in sorted(public):
        n = public[slug]
        label = type_to_label.get(n.get("type"))
        entry = f"- [[{n['title']}]] — {n.get('description') or ''}".rstrip(" —")
        (buckets[label] if label else other).append(entry)

    lines = [
        "# Shared Wiki Index",
        "",
        f"This is the **shared, read-only** cut of {wiki_display_name()} — the pages marked "
        "`public` or `unlisted`. Private pages and raw sources are not present in this "
        "repository at all. Do not edit here; this mirror is regenerated automatically.",
        "",
    ]
    for label in section_order:
        entries = buckets[label]
        if not entries:
            continue
        lines.append(f"## {label} ({len(entries)})")
        lines.extend(entries)
        lines.append("")
    if other:
        lines.append(f"## Other ({len(other)})")
        lines.extend(other)
        lines.append("")
    return "\n".join(lines)


def _readme():
    name = wiki_display_name()
    return f"""# {name} — shared mirror (read-only)

This repository is an **automatically generated, read-only mirror** of the shareable
part of {name}. It contains only pages marked `public` or `unlisted`.

**Not here (by design):** anything marked `private`, the `raw/` source documents, the
activity log, and internal workflow files. Private page titles and links to them are
stripped, not just their bodies.

- **Do not edit these files** — changes are overwritten on the next sync.
- To propose a change, work in the source wiki, not here.
- Read it with your own Claude Code by pointing it at this repo, or browse `wiki/index.md`.
"""


def write_shared(wiki_dir, out_dir):
    shared_files, index_md, _priv = build_shared(wiki_dir)
    # Clean prior wiki/ contents in the out dir so deletions propagate.
    wiki_out = os.path.join(out_dir, "wiki")
    if os.path.isdir(wiki_out):
        for root, _d, files in os.walk(wiki_out):
            for fn in files:
                if fn.endswith(".md"):
                    os.remove(os.path.join(root, fn))
    for rel, text in shared_files.items():
        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
    # The out dir's wiki/ is otherwise created only as a side effect of copying a
    # shareable page. A wiki with none -- a brand-new one -- reached this line with no
    # directory to write into and raised FileNotFoundError, so its mirror never built.
    os.makedirs(os.path.join(out_dir, "wiki"), exist_ok=True)
    with open(os.path.join(out_dir, "wiki", "index.md"), "w", encoding="utf-8") as f:
        f.write(index_md + "\n")
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(_readme())
    return len(shared_files)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the shared (non-private) markdown cut.")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--out", default="shared")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.wiki):
        print(f"error: wiki dir not found: {args.wiki}", file=sys.stderr)
        return 2
    n = write_shared(args.wiki, args.out)
    print(f"shared export: {n} non-private pages -> {args.out}/wiki/ (+ index.md, README.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
