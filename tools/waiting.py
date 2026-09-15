#!/usr/bin/env python3
"""waiting.py — everything that needs a person, in a language that is not git's.

Asked for at the Berlin meeting, 14 September 2026: *how do we make this work for people who
do not know git?* The honest answer turned out not to be "explain git better".

WHAT THE MEASUREMENT FOUND. On 2026-09-15, one wiki in this federation had **61 branches**. **Thirty-seven
had never had a pull request opened for them at all**, the oldest from 4 July, and between
them they carried **66 wiki pages that exist there and nowhere else** — written, committed,
pushed, and then invisible.

(The first pass at that measurement said 30 branches, 20 unproposed, 34 pages. It was reading
one page of the GitHub API without `--paginate`, so "30" was a page size rather than a count.
The tool paginates; a report that silently stops at thirty is worse than no report.)

Nothing was broken. No check failed, no PR sat unreviewed — the review queue was empty all
along, which is exactly why nobody looked. The work was in the one place the system never
shows anyone. A person who does not know what a branch is cannot discover a branch, and the
only surface they are taught is the pull request.

So this is not a git tutorial. It is the missing inbox: one list of what is waiting, written
without the words *branch*, *commit*, *rebase* or *remote*, each item carrying the URL that
does the next step. The intended surface is not this terminal — see
`.github/workflows/waiting.yml`, which keeps one GitHub Issue up to date, because an issue is
a web page a person can read without knowing anything at all.

WHAT IT DOES NOT DO. It never opens the proposal for you. Sixty-six pages nobody has looked
at since July are not obviously all wanted, and a tool that swept them into the corpus would
be making a judgement about somebody's unfinished thinking. It gives you the link.

    python3 tools/waiting.py                 # the list
    python3 tools/waiting.py --json          # for the workflow to render
    python3 tools/waiting.py --repo owner/x  # override the repository it asks about
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import pathlib
ROOT_P = pathlib.Path(ROOT)


def _run(cmd, cwd=ROOT, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:                                     # noqa: BLE001
        return ""


def repo_slug(override=None) -> str:
    if override:
        return override
    url = _run(["git", "remote", "get-url", "origin"])
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", url or "")
    return m.group(1) if m else ""


def _ok(cmd, cwd=ROOT) -> bool:
    """Exit status only. `_run` cannot answer this: a command that succeeds with no output
    and one that fails both come back as the empty string."""
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=60).returncode == 0
    except Exception:                                     # noqa: BLE001
        return False


def _gh_json(args):
    out = _run(["gh"] + args)
    try:
        return json.loads(out) if out else None
    except ValueError:
        return None


def decisions():
    """Branches somebody has already decided about, from the wiki itself.

    A page records a decision by listing the branches it covers in a `decides:` block. The
    page's own `validation` then says who stood behind it — and that distinction is the
    whole point of this function rather than a simple ignore-list.

    Written 2026-09-15, because the tool's first real output re-opened a question the corpus
    had already closed on 2026-09-03 and had written a page specifically to stop anyone
    re-deriving. An inbox that keeps re-raising settled matters trains people to stop opening
    it, which is the failure this tool exists to end.
    """
    out = {}
    for f in sorted((ROOT_P / "wiki").rglob("*.md")):
        try:
            head = f.read_text(encoding="utf-8", errors="ignore")[:4000]
        except Exception:                                 # noqa: BLE001
            continue
        if "\ndecides:" not in head:
            continue
        fm = head.split("---")[1] if head.startswith("---") else head
        branches = re.findall(r"^\s*-\s*(\S+)\s*$", fm.split("decides:", 1)[1], re.M)
        title = (re.search(r"^title:\s*\"?(.+?)\"?\s*$", fm, re.M) or [None, f.stem])[1]
        when = (re.search(r"^timestamp:\s*(\S+)", fm, re.M) or [None, "?"])[1]
        val = (re.search(r"^validation:\s*(\w+)", fm, re.M) or [None, "machine"])[1]
        by = (re.search(r"^validated_by:\s*(.+)$", fm, re.M) or [None, ""])[1].strip()
        vis = (re.search(r"^visibility:\s*(\w+)", fm, re.M) or [None, "private"])[1]
        for b in branches:
            out[b] = {"page": title, "when": when, "validation": val, "visibility": vis,
                      "validated_by": by, "by_a_person": val != "machine" and bool(by)}
    return out


class Unavailable(RuntimeError):
    """Raised when a question could not be asked, rather than answered with a guess."""


def open_proposals(slug):
    """Pull requests waiting for a person, with their checks in plain words."""
    rows = _gh_json(["pr", "list", "-R", slug, "--state", "open", "--limit", "50",
                     "--json", "number,title,url,createdAt,statusCheckRollup,isDraft"]) or []
    out = []
    for p in rows:
        checks = [c.get("conclusion") or c.get("state") or "" for c in
                  (p.get("statusCheckRollup") or [])]
        if not checks or all(c == "" for c in checks):
            state = "still being checked"
        elif any(c in ("FAILURE", "CANCELLED", "TIMED_OUT") for c in checks):
            state = "a check says something is wrong"
        elif all(c in ("SUCCESS", "NEUTRAL", "SKIPPED") for c in checks):
            state = "checked and ready"
        else:
            state = "still being checked"
        out.append({"number": p["number"], "title": p["title"], "url": p["url"],
                    "since": (p.get("createdAt") or "")[:10],
                    "state": "a draft, not finished" if p.get("isDraft") else state})
    return out


def never_proposed(slug):
    """Work that exists only on a branch nobody ever opened a proposal for.

    The branch is deliberately not shown as the headline. What a person needs to know is
    *what is in it* — how many pages, written when — and where to click.
    """
    # The branch list comes from GitHub, paginated, not from local refs. Two reasons, and
    # the second is the one that actually bit. `refs/remotes/origin` is a cache of whatever
    # this checkout last saw, so it still lists branches deleted months ago and the answer
    # differs per machine — `--prune` fixes this checkout and not the next one. And the
    # GitHub API pages at 30: the first pass at this measurement reported "30 branches"
    # without `--paginate` and was quietly reporting a page size, against a true 61.
    branches = _gh_json(["api", f"repos/{slug}/branches", "--paginate",
                         "--jq", "[.[].name]"]) or []
    # One query for every proposal ever, rather than one per branch: 50 branches was 50
    # round trips and half a minute.
    # FAILS CLOSED, DELIBERATELY. `_gh_json` returns None when the query could not be made
    # and [] when it genuinely found nothing, and treating those the same is how this tool
    # published a wrong number on its very first real run: the workflow granted `issues:
    # write` and `contents: read` but no `pull-requests` scope, so this query returned
    # nothing, every branch looked unproposed, and 37 pieces of work were reported as 55.
    # A list that silently overstates is worse than no list — it teaches people to discount
    # it, and this whole tool exists because something went unread.
    asked = _gh_json(["pr", "list", "-R", slug, "--state", "all", "--limit", "1000",
                      "--json", "headRefName"])
    if asked is None:
        raise Unavailable("could not ask which work has already been proposed "
                          "(needs `pull-requests: read`)")
    proposed = {p.get("headRefName") for p in asked}
    _run(["git", "fetch", "--quiet", "origin"])
    out = []
    for b in branches:
        if b in ("main", "HEAD", "export"):
            continue
        ref = f"origin/{b}"
        if not _ok(["git", "rev-parse", "--verify", "--quiet", ref]):
            continue
        # Already contained in main: nothing waiting.
        if _ok(["git", "merge-base", "--is-ancestor", ref, "origin/main"]):
            continue
        # Ancestry alone is not enough — a squash merge rewrites history, so a branch that
        # WAS merged still fails the test above. Asking whether a proposal ever existed is
        # what separates "merged and left lying around" from "never surfaced to anyone".
        if b in proposed:
            continue
        added = [f for f in _run(["git", "diff", "--name-only", "--diff-filter=A",
                                  f"origin/main...{ref}"]).splitlines()
                 if f.startswith("wiki/") and f.endswith(".md")]
        changed = _run(["git", "diff", "--name-only", f"origin/main...{ref}"]).splitlines()
        if not changed:
            continue
        out.append({
            "branch": b,
            "when": _run(["git", "log", "-1", "--format=%ad", "--date=short", ref]),
            "new_pages": len(added),
            "files": len(changed),
            "url": f"https://github.com/{slug}/compare/main...{b}?expand=1",
        })
    out.sort(key=lambda r: (r["when"], -r["new_pages"]))
    return out


#: How many pages to put in front of somebody. `verification.py --sample 3` settled this
#: number for the same reason: a list of 400 is a list nobody starts.
STAND_BEHIND_SAMPLE = 3


def nothing_stands_behind(limit=STAND_BEHIND_SAMPLE):
    """The load-bearing pages in this wiki nobody has confirmed, as a short sample.

    Weight is inbound links: a page the rest of the corpus leans on matters more than one
    nothing cites. `dormant` pages are skipped, and so is anything already validated.

    NO AUTHORSHIP IS READ, and none may be. "Which pages did X write" is the question the
    house rule refuses, and it would be the obvious way to build this. The list is per
    repository instead, which is enough: in a personal wiki the owner is the only person who
    could stand behind anything, and in a commons the question belongs to whoever opens it.

    Empty, rather than wrong, when the graph has not been built: a fresh checkout has no
    `export/wiki.json`, and guessing from filenames would put invented weights in front of a
    person who has no way to check them.
    """
    f = ROOT_P / "export" / "wiki.json"
    if not f.exists():
        return {"available": False, "pages": [], "total_unvalidated": 0}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:                                      # noqa: BLE001
        return {"available": False, "pages": [], "total_unvalidated": 0}
    nodes = d["nodes"] if isinstance(d, dict) and "nodes" in d else d
    if isinstance(nodes, dict):
        nodes = list(nodes.values())
    live = [n for n in nodes
            if (n.get("validation") or "machine") == "machine"
            and n.get("status") != "dormant"]
    ranked = sorted(live, key=lambda n: (-len(n.get("inbound_links") or []),
                                         str(n.get("title") or "")))
    return {
        "available": True,
        "total_unvalidated": len(live),
        "total_pages": len(nodes),
        "pages": [{"title": n.get("title"), "slug": n.get("slug"),
                   "leaned_on_by": len(n.get("inbound_links") or []),
                   "visibility": n.get("visibility", "private")}
                  for n in ranked[:limit] if (n.get("inbound_links") or [])],
    }


def gather(slug):
    m = {"repo": slug, "proposals": open_proposals(slug), "never_proposed": [],
         "decided": [], "unavailable": None, "stand_behind": nothing_stands_behind()}
    try:
        found = never_proposed(slug)
    except Unavailable as exc:
        m["unavailable"] = str(exc)
        return m
    decided = decisions()
    for r in found:
        d = decided.get(r["branch"])
        if d:
            m["decided"].append({**r, "decision": d})
        else:
            m["never_proposed"].append(r)
    return m


def render(m) -> str:
    out = [f"What's waiting for you — {m['repo']}", ""]
    props, never = m["proposals"], m["never_proposed"]

    if props:
        out.append(f"  {len(props)} change(s) proposed, waiting for you to say yes")
        for p in props:
            out.append(f"     {p['title'][:66]}")
            out.append(f"       {p['state']} · since {p['since']} · {p['url']}")
        out.append("")

    if never:
        pages = sum(p["new_pages"] for p in never)
        out.append(f"  {len(never)} piece(s) of work that were never proposed — "
                   f"{pages} page(s) exist there and nowhere else")
        out.append("     Written, saved, and never put forward, so nothing has ever asked")
        out.append("     you about them. Open a link to see the change and propose it.")
        for p in never[:12]:
            what = f"{p['new_pages']} new page(s)" if p["new_pages"] else f"{p['files']} file(s)"
            out.append(f"     {p['when']}  {what:<18} {p['url']}")
        if len(never) > 12:
            out.append(f"     … and {len(never) - 12} more")
        out.append("")


    dec = m.get("decided") or []
    if dec:
        by_page = {}
        for d in dec:
            by_page.setdefault((d["decision"]["page"], d["decision"]["when"],
                                d["decision"]["by_a_person"]), []).append(d)
        out.append(f"  {len(dec)} piece(s) already decided about — not listed above")
        for (page, when, person), items in by_page.items():
            pages = sum(i["new_pages"] for i in items)
            out.append(f"     {len(items)} of them, {pages} page(s), by \"{page[:48]}\" ({when})")
            if not person:
                out.append("       NOBODY HAS STOOD BEHIND THAT DECISION — it is recorded at")
                out.append("       machine validation, so it is a proposal that has been")
                out.append("       treated as settled. A person can confirm it or reopen it.")
        out.append("")

    sb = m.get("stand_behind") or {}
    if sb.get("pages"):
        out.append(f"  {sb['total_unvalidated']} page(s) nobody has stood behind, of "
                   f"{sb['total_pages']}")
        out.append("     Confirming one takes three lines and only a person can do it.")
        for r in sb["pages"]:
            out.append(f"     {r['leaned_on_by']:3d} other page(s) lean on: {str(r['title'])[:58]}")
        out.append("")

    if m.get("unavailable"):
        out.append(f"  !! {m['unavailable']}")
        out.append("     So the list of work nobody put forward is NOT shown. It would have")
        out.append("     counted every piece of work, including everything already settled.")
        out.append("")
    elif not props and not never:
        out.append("  Nothing is waiting. Everything written has been proposed and settled.")
        out.append("")

    out.append("  This list never acts for you. Old work is not automatically wanted work,")
    out.append("  and deciding that is the part a person does.")
    return "\n".join(out)


def markdown(m, public_safe: bool = False) -> str:
    """The same list as a GitHub Issue body — the surface a non-coder actually uses.

    `public_safe` withholds the TITLE of any decision page that is not `visibility: public`.
    The body is the same either way; only the name of the page is dropped.

    Added 2026-09-15, the day this shipped to eleven repositories, one of which
    (llm-wiki-template) is public. The decision page in this wiki is `private`, and its title
    was going straight into an issue body with nothing in the path asking what tier it was.
    In a private repository an issue is inside the same boundary as the pages, so the title
    is shown; in a public one it is not, and the workflow decides which by asking GitHub
    rather than by assuming.
    """
    props, never = m["proposals"], m["never_proposed"]
    out = ["*Everything below needs a person. Nothing here happens on its own.*", ""]

    if props:
        out += [f"## {len(props)} change(s) proposed, waiting for you", ""]
        for p in props:
            out.append(f"- **[{p['title']}]({p['url']})** — {p['state']}, since {p['since']}")
        out.append("")

    if never:
        pages = sum(p["new_pages"] for p in never)
        out += [f"## {len(never)} piece(s) of work nobody ever put forward", "",
                f"**{pages} page(s) exist only here.** They were written and saved, and then "
                "nothing ever asked you about them — so nothing has been wrong, and nothing "
                "has been visible either.", "",
                "Open one to see exactly what it would add. The green button on that page "
                "proposes it; you can also just close the tab and nothing happens.", "",
                "| written | what's in it | open it |", "|---|---|---|"]
        for p in never:
            what = (f"{p['new_pages']} new page(s)" if p["new_pages"]
                    else f"{p['files']} changed file(s)")
            out.append(f"| {p['when']} | {what} | [look]({p['url']}) |")
        out.append("")


    dec = m.get("decided") or []
    if dec:
        by_page = {}
        for d in dec:
            by_page.setdefault((d["decision"]["page"], d["decision"]["when"],
                                d["decision"]["by_a_person"],
                                d["decision"].get("visibility", "private")), []).append(d)
        out += ["## Already decided about", "",
                "Listed here rather than above, so this page does not keep asking you the "
                "same closed question every week.", ""]
        for (page, when, person, vis), items in by_page.items():
            pages = sum(i["new_pages"] for i in items)
            named = page if (vis == "public" or not public_safe) else "a page in this wiki"
            out.append(f"- **{len(items)} piece(s)**, {pages} page(s) — decided by "
                       f"*{named}* ({when})")
            if not person:
                out.append("  - **Nobody has stood behind that decision.** It is recorded at "
                           "`validation: machine` — a proposal that has been treated as "
                           "settled. A person can confirm it, or reopen it.")
        out.append("")

    sb = m.get("stand_behind") or {}
    # Same boundary as the decision titles above: in a public repository the sample may name
    # only pages that are themselves public. Without this the feature added on 2026-09-16
    # would have published private page titles into llm-wiki-template's issue, which is the
    # exact hole closed the day before for the decision page.
    rows = [r for r in sb.get("pages", [])
            if not public_safe or r.get("visibility") == "public"]
    if rows:
        out += [f"## {sb['total_unvalidated']} page(s) nobody has stood behind", "",
                "Nothing here is broken. These are pages the rest of the wiki leans on that "
                "**no person has confirmed**, so the system records them as written by a "
                "machine and believed by nobody.", "",
                "Confirming one is three lines at the top of the page, and it is one of the "
                "few things a model may never do for you. Open a page, use the pencil icon, "
                "and add:", "",
                "```yaml", "validation: self", "validated_by: [Your Name]",
                f"validated_at: {dt.date.today().isoformat()}", "```", "",
                "The date is the one people leave out, and without it the confirmation is "
                "invisible to every read-out.", "",
                "| how many pages lean on it | page |", "|---|---|"]
        for r in rows:
            out.append(f"| {r['leaned_on_by']} | {r['title']} |")
        out += ["", "Three, not a list of hundreds, because a list of hundreds is one nobody "
                    "starts.", ""]

    if m.get("unavailable"):
        out += ["## Part of this list could not be worked out", "",
                f"**{m['unavailable']}**", "",
                "The list of work nobody put forward is deliberately not shown rather than "
                "shown wrong: without that answer it would count everything, including work "
                "that was settled months ago.", ""]
    elif not props and not never:
        out += ["## Nothing is waiting", "",
                "Everything written has been put forward and settled.", ""]

    out += ["---",
            "*Kept up to date by `.github/workflows/waiting.yml`. Old work is not "
            "automatically wanted work, so this list never acts for you.*"]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="What needs a person, in plain language.")
    ap.add_argument("--repo", help="owner/name; default is this checkout's origin")
    ap.add_argument("--json", action="store_true", help="emit the list as JSON")
    ap.add_argument("--markdown", action="store_true",
                    help="emit a GitHub Issue body")
    ap.add_argument("--public-safe", action="store_true",
                    help="withhold the title of any decision page that is not public")
    a = ap.parse_args(argv)
    # Validate at the boundary. An empty or malformed --repo previously fell through to the
    # checkout's own origin and reported on a DIFFERENT repository than the one asked for,
    # which is the worst way to be wrong: confidently, about the wrong thing.
    if a.repo is not None and not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", a.repo):
        print(f"--repo must look like owner/name, not {a.repo!r}", file=sys.stderr)
        return 2
    slug = repo_slug(a.repo)
    if not slug:
        print("could not work out which repository this is — pass --repo owner/name",
              file=sys.stderr)
        return 2
    m = gather(slug)
    if a.json:
        print(json.dumps(m, indent=2))
    elif a.markdown:
        print(markdown(m, public_safe=a.public_safe))
    else:
        print(render(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
