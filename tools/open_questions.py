#!/usr/bin/env python3
"""open_questions.py — what the corpus has not settled, gathered in one place.

The wiki records its answers carefully and scatters its questions. Measured 2026-09-15 across
816 pages: **28 pages carry an `Open questions` section** and **25 pages carry an explicit wait**
of the form "Indy to confirm", 41 times in total. None of it was aggregated anywhere, so a person
could not see what the corpus was waiting to be told without reading it.

That is the gap behind point 9 of the Berlin list, *more inquiry-native workflow*. The `inquiry`
skill was written on 9 September and, measured six days later, **had never been run**: September's
log holds 48 rebuilds, 30 repairs, 7 ingests, 6 lints and 3 queries, and no inquiry at all. The
system is being built far faster than it is being asked.

More documentation was not going to change that. A list of the questions already sitting in the
corpus might, because it gives an inquiry somewhere to start that is not a blank page.

WHAT IT GATHERS. Only things a person wrote down deliberately:

  * `## Open questions` sections, and their variants, with the items underneath.
  * Explicit waits, "<name> to confirm", which are a standing convention here.
  * Open contradictions, from `contradictions.py`, which are questions by another name.

WHAT IT DOES NOT DO. It does not infer a question from prose. "Nobody has" appears in 28 pages and
means something different in most of them, and a tool that guessed would fill this list with
things nobody asked. It has no `--check` and never will: having open questions is the normal state
of a corpus that is thinking, and a gate on it would reward closing them badly.

It also does not rank them. A question's importance is not a property a script can read.

VISIBILITY. Each item carries the tier of the page it came from, and `--shareable` drops anything
`private` outright. The default includes private material, because the owner reading their own
wiki should see all of it; the flag exists for the moment somebody pastes this into a channel.

    python3 tools/open_questions.py               # everything, for the owner
    python3 tools/open_questions.py --shareable   # private material dropped
    python3 tools/open_questions.py --json
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"

HEADING = re.compile(r"^(#{2,4})\s*open\s+question", re.I)
ANY_HEADING = re.compile(r"^#{1,6}\s")
#: "Indy to confirm", "_(Gurden to confirm)_". A standing convention, not a guess.
WAIT = re.compile(r"\b([A-Z][a-z]+)\s+to\s+confirm\b")


def _fm(text: str) -> dict:
    out = {}
    if text.startswith("---"):
        for line in text.split("---", 2)[1].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.split("#")[0].strip().strip('"')
    return out


def from_page(path: pathlib.Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm = _fm(text)
    page = {"path": str(path.relative_to(ROOT)),
            "title": fm.get("title") or path.stem,
            "visibility": fm.get("visibility", "private"),
            "timestamp": fm.get("timestamp", ""),
            "sections": [], "waits": []}

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if HEADING.match(lines[i]):
            head = lines[i].lstrip("# ").strip()
            items, i = [], i + 1
            while i < len(lines) and not ANY_HEADING.match(lines[i]):
                s = lines[i].strip()
                # Only the item's first line: these are often wrapped paragraphs, and the
                # whole point is a list a person can scan.
                if re.match(r"^([-*]|\d+\.)\s+", s):
                    items.append(re.sub(r"^([-*]|\d+\.)\s+", "", s))
                i += 1
            page["sections"].append({"heading": head, "items": items})
            continue
        m = WAIT.search(lines[i])
        if m:
            page["waits"].append({"who": m.group(1), "line": lines[i].strip()[:160]})
        i += 1
    return page if (page["sections"] or page["waits"]) else None


def contradictions():
    """Open contradictions are questions with two pages attached."""
    try:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "contradictions.py")],
                           capture_output=True, text=True, timeout=120, cwd=ROOT)
        out = (r.stdout or "").strip()
        if "coherent" in out.lower():
            return []
        return [l.strip() for l in out.splitlines() if re.match(r"^\s*[0-9]+\.", l)]
    except Exception:                                      # noqa: BLE001
        return []


def gather(shareable=False):
    pages = []
    for p in sorted(WIKI.rglob("*.md")):
        if p.name in ("index.md", "log.md") or "/log/" in p.as_posix() or "/index/" in p.as_posix():
            continue
        got = from_page(p)
        if not got:
            continue
        if shareable and got["visibility"] == "private":
            continue
        pages.append(got)
    return {
        "pages": pages,
        "shareable": shareable,
        "totals": {
            "pages": len(pages),
            "sections": sum(len(x["sections"]) for x in pages),
            "items": sum(len(s["items"]) for x in pages for s in x["sections"]),
            "waits": sum(len(x["waits"]) for x in pages),
        },
        "contradictions": contradictions(),
    }


def render(m) -> str:
    t, out = m["totals"], []
    out.append("open questions — what the corpus has not settled")
    out.append(f"  {t['items']} question(s) in {t['sections']} section(s) across {t['pages']} "
               f"page(s) · {t['waits']} explicit wait(s)")
    if m["shareable"]:
        out.append("  private material excluded")
    out.append("")

    # Grouped per page, not per occurrence: the Axioms Register carries eleven waits and
    # listing each one eleven times buries the other fourteen pages behind it.
    waiting = [p for p in m["pages"] if p["waits"]]
    if waiting:
        out.append(f"  WAITING ON A PERSON — {len(waiting)} page(s)")
        for p in sorted(waiting, key=lambda x: (-len(x["waits"]), x["title"])):
            who = sorted({w["who"] for w in p["waits"]})
            mark = " [private]" if p["visibility"] == "private" else ""
            n = f" ×{len(p['waits'])}" if len(p["waits"]) > 1 else ""
            out.append(f"     {', '.join(who)}: {p['title'][:56]}{n}{mark}")
        out.append("")

    asked = [p for p in m["pages"] if any(s["items"] for s in p["sections"])]
    out.append(f"  ASKED AND NOT ANSWERED — {len(asked)} page(s)")
    for p in sorted(asked, key=lambda x: -sum(len(s["items"]) for s in x["sections"]))[:12]:
        mark = " [private]" if p["visibility"] == "private" else ""
        n = sum(len(s["items"]) for s in p["sections"])
        out.append(f"     {p['title'][:56]}{mark}  ({n})")
        for s in p["sections"]:
            for it in s["items"][:2]:
                out.append(f"        {re.sub(r'[*_`]', '', it)[:86]}")
    if len(asked) > 12:
        out.append(f"     … and {len(asked) - 12} more page(s)")
    out.append("")

    if m["contradictions"]:
        out.append(f"  DECLARED CONTRADICTIONS — {len(m['contradictions'])}")
        for c in m["contradictions"][:6]:
            out.append(f"     {c[:88]}")
        out.append("")

    out.append("  This is where an inquiry starts. `inquiry` takes one of these, searches every")
    out.append("  commons this wiki can read, and comes back with hypotheses and their sources.")
    out.append("  Nothing here is a fault. A corpus with no open questions has stopped thinking.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="What the corpus has not settled.")
    ap.add_argument("--shareable", action="store_true", help="drop anything private")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    m = gather(a.shareable)
    print(json.dumps(m, indent=2) if a.json else render(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
