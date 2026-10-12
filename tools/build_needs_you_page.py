#!/usr/bin/env python3
"""
build_needs_you_page.py — the "Needs you" page for one wiki, built from its real items.

Built 12 October 2026 at Gurden's call to test with real data rather than mock-ups. It renders the
list from needs_you.py and the menu from skill_menu.py into one page. The page never acts on its
own: "Yes" opens the proposal on GitHub, where the owner saves it with their own sign-in, and every
piece of thinking work hands Claude the exact words to use. The page carries private items, so it
is only ever published locked: encrypt_page.mjs wraps it before it reaches the wiki's site, and the
publishing workflow refuses to publish it without a password.

    python3 tools/build_needs_you_page.py [--out export/needs-you.html]
    NEEDS_YOU_PASSWORD=… python3 tools/build_needs_you_page.py --lock docs/needs-you/index.html

The heading comes from design/federation.json ("Leon's wiki", "The xCO Team Wiki"), so every wiki's
publishing workflow runs the same two lines. --lock builds, locks with encrypt_page.mjs, and refuses
to leave anything readable behind.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TEMPLATE_FILE = HERE / "templates" / "needs_you_page.html"


def heading(root: pathlib.Path) -> str:
    """What the page calls this wiki: the owner's name for a personal wiki, the wiki's own name otherwise."""
    f = root / "design" / "federation.json"
    fed = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    shown = (fed.get("display_name") or fed.get("name") or root.name).strip()
    m = re.match(r"^(.+?)['’]s\b", shown)
    if fed.get("role", "spoke") == "spoke" and m:
        return f"{m.group(1)}’s wiki"
    return shown[:1].upper() + shown[1:]


def locked_ok(text: str) -> bool:
    """The published file must hold ciphertext and nothing readable."""
    return "const DATA" not in text and "var CT = " in text


def render(name: str, repo: str, items: list, menu: list, paths: dict, built: str, modules: dict | None = None) -> str:
    """The page as HTML. `paths` maps a page title to its file, so anything named can link to it on GitHub."""
    modules = modules or {"map": {"areas": [], "links": [], "pages_total": 0}, "onboarding": [],
                          "moved": {"days": 7, "added": 0, "changed": 0, "newest": []},
                          "travels": {"role": "spoke", "shares_into": [], "reads_from": [], "could_go_up": 0, "top": []}}
    titles = {t for i in items for t in [i["action"].get("page")] + [p["title"] for p in i["action"].get("pages", [])] if t}
    titles |= {t for a in modules["map"]["areas"] for t in a["pages"]} | set(modules["moved"]["newest"])
    links = {t: f"https://github.com/{repo}/blob/main/{paths[t]}" for t in titles if t in paths}
    data = {"items": items, "menu": menu, "links": links, "modules": modules}
    h = TEMPLATE_FILE.read_text(encoding="utf-8")
    h = h.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    h = h.replace("__NAME__", json.dumps(name)).replace("__BUILT__", json.dumps(built))
    return h.replace("__TITLE__", f"Needs you · {name}")


def _paths(root: pathlib.Path) -> dict:
    out = {}
    for p in (root / "wiki").rglob("*.md"):
        m = re.search(r"^title:\s*(.+)$", p.read_text(encoding="utf-8", errors="replace"), re.M)
        if m:
            out[m.group(1).strip().strip("\"'")] = p.relative_to(root).as_posix()
    return out


def _repo(root: pathlib.Path) -> str:
    url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True).stdout.strip()
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else ""


def main(argv=None) -> int:
    import needs_you
    import skill_menu
    ap = argparse.ArgumentParser(description="Build one wiki's Needs-you page from its real items.")
    ap.add_argument("--name", help="the owner's first name; by default the heading comes from design/federation.json")
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--out", default="export/needs-you.html")
    ap.add_argument("--lock", metavar="PUBLISHED", help="also lock the page into this file (needs NEEDS_YOU_PASSWORD)")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root)
    title = f"{a.name}’s wiki" if a.name else heading(root)
    import view_modules
    items = needs_you.gather(root)
    menu = skill_menu.build_menu(skill_menu.skills_held(root), lambda n: skill_menu._first_line(root, n))
    modules = view_modules.gather(root, (needs_you._run_json(root, ["tools/waiting.py", "--json"]) or {}).get("up"))
    built = datetime.datetime.now(datetime.timezone.utc).strftime("%-d %b %Y, %H:%M UTC")
    html = render(title, _repo(root), items, menu, _paths(root), built, modules)
    out = root / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}: {len(items)} item(s), {sum(len(g['skills']) for g in menu)} skill(s)")
    if a.lock:
        pub = root / a.lock
        r = subprocess.run(["node", str(HERE / "encrypt_page.mjs"), str(out), str(pub), title])
        if r.returncode or not pub.exists() or not locked_ok(pub.read_text(encoding="utf-8")):
            pub.unlink(missing_ok=True)
            print("::error::The Needs-you page is not locked. Nothing was published.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
