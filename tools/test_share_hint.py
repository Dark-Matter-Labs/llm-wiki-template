#!/usr/bin/env python3
"""
test_share_hint.py: the share hint's own cases.

What must hold, because each is a way the nudge could do harm rather than merely miss:

  * a contact card is never pointed at a shared wiki;
  * a private page is never offered for sharing, only pointed at ("open first");
  * a page the shared wiki already holds is not suggested again;
  * a shared wiki with no cached copy here is said to be unknown, never guessed;
  * a link counts more than a tag, and a generic tag counts for nothing.

  python3 tools/test_share_hint.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import share_hint as sh  # noqa: E402

FAILURES = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"          got  {got!r}\n          want {want!r}")
        FAILURES.append(label)


M2M = {"titles": {"deep codes", "the many-to-many contract", "beyond the rules"}, "tags": {"m2m", "many-to-many"}}
LAB = {"titles": {"participatory consciousness"}, "tags": {"plus-hm"}}
PROFILES = {"m2m-shared-wiki": M2M, "lab-wiki": LAB, "uncached-wiki": None}
TARGETS = ["m2m-shared-wiki", "lab-wiki"]


def page(title, vis="internal", links=(), tags=()):
    return {"title": title, "visibility": vis, "outbound_links": list(links), "tags": list(tags)}


print("share_hint")
h = sh.hint("contracts-note", page("Contracts note", links=["Deep Codes"], tags=["m2m"]), TARGETS, PROFILES)
check("an open page with a link and a tag is offered to that wiki", (h["kind"], h["commons"]), ("share", "m2m-shared-wiki"))

h = sh.hint("draft", page("Draft", vis="private", links=["Deep Codes", "Beyond the Rules"]), TARGETS, PROFILES)
check("a private page is only pointed at, never offered", (h["kind"], h["commons"]), ("open first", "m2m-shared-wiki"))

h = sh.hint("crm/contacts/someone", page("Someone", links=["Deep Codes"] * 3, tags=["m2m"]), TARGETS, PROFILES)
check("a contact card is never pointed anywhere", h["kind"], "none")

h = sh.hint("deep-codes", page("Deep Codes", links=["The Many-to-Many Contract"]), TARGETS, PROFILES)
check("a page the shared wiki already holds is not suggested", (h["kind"], "already" in h["why"]), ("none", True))

h = sh.hint("thin", page("Thin", tags=["m2m", "many-to-many"]), TARGETS, PROFILES)
check("matching tags alone are never enough", h["kind"], "none")

h = sh.hint("one-link", page("One link", links=["Deep Codes"]), TARGETS, PROFILES)
check("one link with no shared tag is not enough", h["kind"], "none")

h = sh.hint("generic", page("Generic", links=["Deep Codes"], tags=["summary", "xco", "draft"]), TARGETS,
            {"m2m-shared-wiki": {"titles": {"deep codes"}, "tags": {"summary", "xco", "draft"}}})
check("generic tags never count, even if the shared wiki uses them", h["kind"], "none")

h = sh.hint("both", page("Both", links=["Participatory Consciousness", "Deep Codes", "Beyond the Rules"]), TARGETS, PROFILES)
check("the wiki the page leans on most wins", h["commons"], "m2m-shared-wiki")

h = sh.hint("orphan", page("Orphan", links=["Deep Codes"]), ["uncached-wiki"], PROFILES)
check("an uncached shared wiki is said to be unknown, not guessed", (h["kind"], "no shared copy cached" in h["why"]), ("none", True))

pts, why, nlinks = sh.score(page("X", links=["Deep Codes"], tags=["m2m"]), M2M)
check("a link is worth more than a tag", pts, sh.LINK_POINTS + sh.TAG_POINTS)

if FAILURES:
    print(f"\n{len(FAILURES)} failed")
    sys.exit(1)
print("\nall passed")
