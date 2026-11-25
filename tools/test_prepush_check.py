#!/usr/bin/env python3
"""Tests for prepush_check.py: which commands count as a push, and which repository they push."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepush_check as p  # noqa: E402

CASES = [
    ("git push -u origin fix/x", "/w", "/w", "a plain push runs the checks where the chat is"),
    ("rtk git push", "/w", "/w", "the rtk wrapper is still a push"),
    ("cd /a && git add x && git commit -m y && git push", "/w", "/a", "a push after cd runs where it pushes"),
    ("git -C /b push origin main", "/w", "/b", "git -C names the repository"),
    ("git push origin --delete old", "/w", None, "deleting a branch changes no files"),
    ("git push origin :old", "/w", None, "the colon form of delete too"),
    ("git status && gh pr create --title t", "/w", None, "not a push"),
    ("echo 'git push'", "/w", None, "a quoted mention is not a push"),
]

failures = 0
for command, cwd, want, why in CASES:
    got = p.pushed_repo(command, cwd)
    ok = got == want
    failures += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {why}" + ("" if ok else f" (got {got!r}, wanted {want!r})"))
print("all passed." if not failures else f"{failures} failed.")
sys.exit(1 if failures else 0)
