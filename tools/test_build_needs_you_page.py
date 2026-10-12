#!/usr/bin/env python3
"""
test_build_needs_you_page.py — the Needs-you page, built from real items, locked before it is published.

The page goes on a wiki's public site, so two things are tested hardest: nothing readable leaves
without the password, and the page itself only ever points at GitHub and Claude.

  python3 tools/test_build_needs_you_page.py
"""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_needs_you_page as B  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
FAILED = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


ITEMS = [
    {"kind": "proposal", "group": "yes", "ref": 7, "title": "Overview brought up to date", "why": "Adds the October work.",
     "action": {"type": "yes", "label": "Save it into your wiki", "target": "https://github.com/Org/w/pull/7"}},
    {"kind": "contradiction", "group": "yes", "ref": "A", "title": "Two pages disagree", "why": "Only a person decides.",
     "action": {"type": "decide", "label": "Choose which one wins",
                "pages": [{"title": "Page A", "says": "a"}, {"title": "Page B", "says": "b"}]}},
    {"kind": "stand_behind", "group": "yes", "ref": "Page A", "title": "Stand behind “Page A”?", "why": "8 pages lean on it.",
     "action": {"type": "confirm", "label": "Read it and confirm it", "page": "Page A"}},
    {"kind": "questions", "group": "concern", "ref": "q", "title": "3 open questions", "why": "Among them: Why?",
     "action": {"type": "ask", "label": "Pick one", "say": "What don't we know?"}},
]
MENU = [{"group": "Ask and think", "skills": [{"skill": "joker", "label": "Challenge a position", "what": "x",
                                               "say": "Challenge this: {x}", "ask": "Which position?"}]}]
PATHS = {"Page A": "wiki/page-a.md", "Page B": "wiki/page-b.md"}


def main():
    print("build_needs_you_page — the page, and the lock on it\n")
    html = B.render("Leon’s wiki", "Org/w", ITEMS, MENU, PATHS, "12 Oct 2026, 14:05")
    data = json.loads(re.search(r"const DATA = (.*?);\n", html, re.S).group(1))
    check("the items and menu are in the page", len(data["items"]) == 4 and data["menu"][0]["group"] == "Ask and think")
    check("a page named in an item links to its file on GitHub",
          data["links"]["Page A"] == "https://github.com/Org/w/blob/main/wiki/page-a.md", str(data["links"]))
    hosts = set(re.findall(r"https://([a-z0-9.-]+)/", html))
    check("the page only points at GitHub, Claude and the fonts", hosts <= {"github.com", "claude.ai", "fonts.googleapis.com"},
          str(hosts))
    check("a yes opens the proposal on GitHub, where the person saves it", "https://github.com/Org/w/pull/7" in html)
    check("no item runs anything itself: there is no fetch or form post", "fetch(" not in html and "method=" not in html.lower())
    check("it says when it was built", "12 Oct 2026, 14:05" in html)
    mods = {"map": {"areas": [{"id": 0, "label": "Page A", "size": 5, "about": "", "pages": ["Page A", "Page B"]}], "links": [], "pages_total": 9},
            "onboarding": [{"label": "Ask your wiki a question", "done": False, "say": "What does the wiki say about …?"}],
            "moved": {"days": 7, "added": 1, "changed": 2, "newest": ["Page B"]},
            "travels": {"role": "spoke", "shares_into": ["xco-team-wiki"], "reads_from": [], "could_go_up": 0, "top": []}}
    full = json.loads(re.search(r"const DATA = (.*?);\n", B.render("Leon", "Org/w", ITEMS, MENU, PATHS, "x", mods), re.S).group(1))
    check("the full view carries the map, onboarding, what moved and travels", set(full["modules"]) == {"map", "onboarding", "moved", "travels"})
    check("pages on the map link to GitHub", full["links"].get("Page B") == "https://github.com/Org/w/blob/main/wiki/page-b.md")
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d); (root / "design").mkdir()
        fed = root / "design" / "federation.json"
        fed.write_text('{"display_name": "Leon\'s LLM Wiki", "role": "spoke"}')
        check("a personal wiki is headed with its owner's name", B.heading(root) == "Leon’s wiki", B.heading(root))
        fed.write_text('{"display_name": "the xCO Team Wiki", "role": "commons"}')
        check("a shared wiki is headed with its own name", B.heading(root) == "The xCO Team Wiki", B.heading(root))
        fed.write_text('{"display_name": "the People & Hosts Wiki", "role": "spoke"}')
        check("a wiki with no owner's name keeps its own", B.heading(root) == "The People & Hosts Wiki", B.heading(root))
    check("only ciphertext counts as locked", B.locked_ok('var CT = "x"') and not B.locked_ok(html)
          and not B.locked_ok('var CT = "x" const DATA'))
    check("the layout setting holds no wiki content", "localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout))" in html)

    node = shutil.which("node")
    if not node:
        check("node is available to test the lock", False, "node not found")
    else:
        with tempfile.TemporaryDirectory() as d:
            src, out = pathlib.Path(d) / "in.html", pathlib.Path(d) / "out.html"
            src.write_text(html, encoding="utf-8")
            env = {**os.environ, "NEEDS_YOU_PASSWORD": "correct horse battery staple", "NEEDS_YOU_SALT_LABEL": "test"}
            r = subprocess.run([node, str(HERE / "encrypt_page.mjs"), str(src), str(out), "Leon"], env=env,
                               capture_output=True, text=True)
            check("the lock runs", r.returncode == 0, r.stderr[-300:])
            locked = out.read_text(encoding="utf-8") if out.exists() else ""
            check("nothing readable leaves the lock", "Overview brought up to date" not in locked and "Page A" not in locked)
            check("the locked page is never indexed", 'name="robots" content="noindex, nofollow, noarchive"' in locked)
            check("the locked page offers no 'remember me'", "localStorage" not in locked and "Remember" not in locked)
            dec = subprocess.run([node, "-e", DECRYPT, str(out)], env=env, capture_output=True, text=True)
            check("the right password opens it", "Overview brought up to date" in dec.stdout, dec.stderr[-300:])
            bad = subprocess.run([node, "-e", DECRYPT, str(out)], env={**env, "NEEDS_YOU_PASSWORD": "wrong one entirely"},
                                 capture_output=True, text=True)
            check("a wrong password does not", bad.returncode != 0)
            r2 = subprocess.run([node, str(HERE / "encrypt_page.mjs"), str(src), str(out), "Leon"],
                                env={**env, "NEEDS_YOU_PASSWORD": "short"}, capture_output=True, text=True)
            check("a password under 12 characters is refused", r2.returncode != 0)

    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


DECRYPT = r"""
const fs = require("fs"); const { webcrypto: c } = require("crypto");
const h = fs.readFileSync(process.argv[1], "utf8");
const g = n => h.match(new RegExp("var " + n + ' = "([^"]+)"'))[1];
const b = s => Uint8Array.from(Buffer.from(s, "base64"));
(async () => {
  const base = await c.subtle.importKey("raw", new TextEncoder().encode(process.env.NEEDS_YOU_PASSWORD), "PBKDF2", false, ["deriveKey"]);
  const rounds = +h.match(/var ROUNDS = (\d+)/)[1];
  const key = await c.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt: b(g("SALT")), iterations: rounds }, base,
                                       { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  const p = await c.subtle.decrypt({ name: "AES-GCM", iv: b(g("IV")) }, key, b(g("CT")));
  process.stdout.write(new TextDecoder().decode(p));
})().catch(() => process.exit(1));
"""


if __name__ == "__main__":
    raise SystemExit(main())
