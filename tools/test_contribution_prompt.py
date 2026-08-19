#!/usr/bin/env python3
"""
test_contribution_prompt.py — the weekly contribution prompt's own edge cases.

The prompt names pages a person might contribute. Three things must hold, and each
is a way the feature could do real harm rather than merely fail:

  * a `private` page is never named — not its slug, not its title;
  * a page the commons already holds is never suggested (that is an overwrite);
  * a wiki that contributes nowhere is prompted about nothing at all.

  python3 tools/test_contribution_prompt.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contribution_prompt as cp  # noqa: E402

FAILURES = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"          got  {got!r}\n          want {want!r}")
        FAILURES.append(label)


PAGES = {
    "alpha":       {"title": "Alpha", "visibility": "internal", "inbound": 5},
    "beta":        {"title": "Beta",  "visibility": "internal", "inbound": 9},
    "gamma":       {"title": "Gamma", "visibility": "unlisted", "inbound": 1},
    "secret":      {"title": "Secret Deal", "visibility": "private", "inbound": 30},
    "crm/contact": {"title": "A Person", "visibility": "private", "inbound": 0},
}


def main():
    print("contribution prompt — edge cases\n")

    # --- privacy: the whole point of reusing contribute.eligible() -----------
    named = {c["slug"] for c in cp.candidates(PAGES, already={})}
    check("a private page is never named", "secret" in named, False)
    check("CRM is never named", "crm/contact" in named, False)
    check("eligible pages are named", named, {"alpha", "beta", "gamma"})

    # --- collisions: suggesting one of these would mean an overwrite ---------
    got = {c["slug"] for c in cp.candidates(PAGES, already={"Beta"})}
    check("a title the commons holds is dropped", got, {"alpha", "gamma"})

    # --- ranking: most load-bearing first ------------------------------------
    order = [c["slug"] for c in cp.candidates(PAGES, already={})]
    check("ranked by inbound links, descending", order, ["beta", "alpha", "gamma"])

    # --- unknown collision state must not be silently treated as "no clash" --
    unknown = cp.candidates(PAGES, already=None)
    check("no cache -> still lists", {c["slug"] for c in unknown},
          {"alpha", "beta", "gamma"})
    check("no cache -> flagged unverified", all(c["collision_unknown"] for c in unknown), True)
    check("with cache -> not flagged", 
          any(c["collision_unknown"] for c in cp.candidates(PAGES, already={"Beta"})), False)

    # --- a wiki that contributes nowhere is prompted about nothing -----------
    check("commons with no targets -> no prompt",
          cp.targets({"role": "commons", "contributes_to": []}), [])
    check("spoke -> its declared target",
          cp.targets({"role": "spoke", "contributes_to": ["xco-team-wiki"]}),
          ["xco-team-wiki"])
    check("two targets -> both prompted separately",
          cp.targets({"role": "spoke",
                      "contributes_to": ["xco-team-wiki", "learning-system-wiki"]}),
          ["xco-team-wiki", "learning-system-wiki"])

    # --- the seam the mocked cases cannot reach --------------------------------
    # Everything above passes a page dict straight in. The first real run failed on
    # export.build_nodes() returning a tuple, which no mocked case could have caught.
    wiki = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wiki")
    if os.path.isdir(wiki):
        real = cp.read_wiki(wiki)
        check("read_wiki returns a dict of pages", isinstance(real, dict) and len(real) > 0, True)
        sample = next(iter(real.values()))
        check("each page carries the fields candidates() needs",
              sorted(sample.keys()), ["inbound", "title", "visibility"])
        check("no private page survives into candidates() on the real wiki",
              any(real[c["slug"]]["visibility"] == "private"
                  for c in cp.candidates(real, already=set())), False)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        return 1
    print("all edge cases pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
