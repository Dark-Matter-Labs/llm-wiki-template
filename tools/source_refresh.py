#!/usr/bin/env python3
"""
source_refresh.py — has a web source changed since it was saved into raw/?

    python3 tools/source_refresh.py --list           # the sources it can check, without fetching anything
    python3 tools/source_refresh.py                  # fetch each one and report: new, unchanged, changed, unreachable
    python3 tools/source_refresh.py --only raw/x.md  # one source
    python3 tools/source_refresh.py --accept raw/x.md   # after a person has filed the new version, take it as the baseline

Adapted on 23 October 2026 from the refresh command in nvk/llm-wiki. A saved source is a snapshot; the page it
came from keeps changing: a Substack post is edited, a published deck gets a new version, a partner's page is
taken down. Nothing here noticed.

How it works. A source in raw/ names its web address in its opening lines (`Source: https://…`, or a `source:`
/ `url:` field). The first check records a fingerprint of the page's text in `design/source-refresh.json`; later
checks compare against it. Sign-in-only services (Google Docs, Notion, Slack, claude.ai, Otter) are listed as not
checkable rather than fetched.

What it never does. It never edits raw/: a changed page is saved as a NEW source file by the `source-refresh`
skill, and only after a person has looked. (nvk/llm-wiki's refresh overwrites the raw file, which breaks its own
rule that raw is immutable; this one does not.) It does not judge what changed; it only says that something did.
Not for CI: it reads the network, and pages change for trivial reasons a person must weigh.
"""

import argparse
import datetime
import hashlib
import html
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = "design/source-refresh.json"
SUFFIXES = (".md", ".txt", ".html", ".htm")
URL = re.compile(r"https?://[^\s)>\"'\]]+")
NAMED = re.compile(r"^\W*(?:source|url|canonical_url|link|original)\s*:\s*<?(https?://[^\s)>\"'\]]+)", re.I | re.M)
SIGN_IN = ("docs.google.com", "drive.google.com", "notion.so", "notion.site", "slack.com", "claude.ai", "otter.ai",
           "figma.com", "miro.com", "linkedin.com")


def source_url(text: str) -> "str | None":
    """The web address a saved source names in its opening lines, preferring a labelled one."""
    head = "\n".join(text.splitlines()[:30])
    m = NAMED.search(head)
    if m:
        return m.group(1).rstrip(".,;")
    m = URL.search(head)
    return m.group(0).rstrip(".,;") if m else None


def checkable(url: str) -> bool:
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    return not any(host == d or host.endswith("." + d) for d in SIGN_IN)


def page_text(raw: bytes) -> str:
    """The readable text of a page, so markup, scripts and whitespace changes do not count as change."""
    t = raw.decode("utf-8", errors="replace")
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (wiki source refresh)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(5_000_000)


def sources(root: pathlib.Path) -> dict:
    """{raw path: url} for every text source in raw/ that names a web address."""
    out = {}
    raw = root / "raw"
    for p in sorted(raw.rglob("*")) if raw.is_dir() else []:
        if p.is_file() and p.suffix.lower() in SUFFIXES:
            u = source_url(p.read_text(encoding="utf-8", errors="replace"))
            if u:
                out[p.relative_to(root).as_posix()] = u
    return out


def check_one(rel: str, url: str, state: dict, getter=fetch, today: str = "") -> str:
    """Fetch one source and update its entry. Returns new | unchanged | changed | unreachable | not-checkable."""
    entry = state.setdefault(rel, {"url": url})
    entry["url"] = url
    if not checkable(url):
        entry["status"] = "not-checkable"
        return "not-checkable"
    try:
        fp = fingerprint(page_text(getter(url)))
    except (urllib.error.URLError, OSError, ValueError) as e:
        entry.update(status="unreachable", checked=today, error=str(e)[:120])
        return "unreachable"
    entry["checked"] = today
    entry.pop("error", None)
    if "baseline" not in entry:
        entry.update(baseline=fp, latest=fp, status="new", since=today)
        return "new"
    entry["latest"] = fp
    entry["status"] = "unchanged" if fp == entry["baseline"] else "changed"
    if entry["status"] == "changed":
        entry.setdefault("changed_on", today)
    else:
        entry.pop("changed_on", None)
    return entry["status"]


def load(root):
    p = root / STATE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save(root, state):
    p = root / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(sorted(state.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None, root: pathlib.Path = ROOT, getter=fetch) -> int:
    ap = argparse.ArgumentParser(description="Has a web source changed since it was saved into raw/?")
    ap.add_argument("--list", action="store_true", help="list checkable sources; fetch nothing")
    ap.add_argument("--only", action="append", default=[], help="check only this raw path (repeatable)")
    ap.add_argument("--accept", action="append", default=[], help="take the latest version of this source as its baseline")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    found, state, today = sources(root), load(root), datetime.date.today().isoformat()
    if a.accept:
        for rel in a.accept:
            e = state.get(rel)
            if not e or "latest" not in e:
                print(f"  {rel}: never checked; nothing to accept")
                continue
            e.update(baseline=e["latest"], status="unchanged", accepted=today)
            e.pop("changed_on", None)
            print(f"  {rel}: its latest version is now the baseline")
        save(root, state)
        return 0
    todo = {r: u for r, u in found.items() if not a.only or r in a.only}
    if a.list:
        for r, u in todo.items():
            print(f"  {'checkable  ' if checkable(u) else 'sign-in    '} {r}  ->  {u}")
        print(f"\n{sum(map(checkable, todo.values()))} of {len(todo)} source(s) can be checked.")
        return 0
    results = {r: check_one(r, u, state, getter, today) for r, u in todo.items()}
    save(root, state)
    if a.json:
        print(json.dumps({r: dict(state[r], result=s) for r, s in results.items()}, indent=1))
        return 0
    order = ["changed", "unreachable", "new", "unchanged", "not-checkable"]
    for status in order:
        rows = [r for r, s in results.items() if s == status]
        if rows and status in ("changed", "unreachable"):
            print(f"{status} ({len(rows)}):")
            for r in rows:
                print(f"  {r}  ->  {state[r]['url']}")
    counts = {s: sum(1 for v in results.values() if v == s) for s in order}
    print("\n" + " · ".join(f"{n} {s}" for s, n in counts.items() if n))
    if counts["changed"]:
        print("A changed source is filed as a NEW raw file, after a person has looked; then --accept it. raw/ is never edited.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
