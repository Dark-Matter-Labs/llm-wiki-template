#!/usr/bin/env python3
"""
add_analytics.py — add the SimpleAnalytics counter to a wiki's public pages, at the moment the site is published.

Asked for by Gurden on 19 October 2026: see how the pages we share publicly get clicks and attention. Dark Matter
Labs already pays for SimpleAnalytics, which sets no cookies and collects no personal data, and the site address
(dark-matter-labs.github.io) is already registered there. Each wiki's path tells its pages apart.

The rules:
- A wiki opts in with design/analytics.json ({"simpleanalytics": true}). Without it, this does nothing.
- Locked pages are never counted: the lenses, the front page, Needs-you. They are for colleagues, and counting
  colleagues' reading drifts towards watching people.
- A page with its own Content-Security-Policy that does not allow the counter is left alone and reported.
- The pages in the wiki are never changed. The publishing step runs this with --write on its own copy, just before
  upload. Run without --write, it only reports what would be counted.

  python3 tools/add_analytics.py docs            # report only
  python3 tools/add_analytics.py --write docs    # the publishing step
"""

import json
import os
import re
import sys

# No integrity hash on the script: SimpleAnalytics serves one "latest" file that changes as they update it, so a
# pinned hash would silently stop the counting. The page loses nothing if the script fails to load.
COUNTER = ('<script async src="https://scripts.simpleanalyticscdn.com/latest.js"></script>\n'
           '<noscript><img src="https://queue.simpleanalyticscdn.com/noscript.gif" alt="" '
           'referrerpolicy="no-referrer-when-downgrade"></noscript>\n')
MARK = "simpleanalyticscdn.com"
LOCKED = re.compile(r'var SALT = "[A-Za-z0-9+/=]+"[,;] (?:var )?IV = "')
CSP = re.compile(r"""http-equiv=["']Content-Security-Policy""", re.I)
BODY_END = re.compile(r"</body\s*>", re.I)


def opted_in(root="."):
    try:
        with open(os.path.join(root, "design", "analytics.json"), encoding="utf-8") as f:
            return json.load(f).get("simpleanalytics") is True
    except (OSError, ValueError):
        return False


def with_counter(html):
    """(new html or None, why). None means leave the page as it is."""
    if MARK in html:
        return None, "already"
    if LOCKED.search(html):
        return None, "locked"
    if CSP.search(html):
        return None, "own security rules"
    ends = list(BODY_END.finditer(html))
    if ends:
        at = ends[-1].start()
        return html[:at] + COUNTER + html[at:], "added"
    return html + COUNTER, "added"


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    write = "--write" in args
    docs = next((a for a in args if not a.startswith("--")), "docs")
    if not opted_in():
        print("analytics: this wiki has not opted in (design/analytics.json), so no page is counted.")
        return 0
    seen = {}
    for dirpath, _dirs, files in os.walk(docs):
        for fn in files:
            if not fn.lower().endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                html = open(path, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            new, why = with_counter(html)
            seen.setdefault(why, []).append(os.path.relpath(path, docs))
            if new is not None and write:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
    verb = "counted" if write else "would be counted"
    print(f"analytics: {len(seen.get('added', []))} public page(s) {verb}; "
          f"{len(seen.get('locked', []))} locked page(s) left out")
    for p in seen.get("own security rules", []):
        print(f"  left alone, its own security rules would block the counter: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
