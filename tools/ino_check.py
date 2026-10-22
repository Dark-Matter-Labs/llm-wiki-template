#!/usr/bin/env python3
"""
ino_check.py — does a piece of work know which question it serves, and what would change its mind?

house-rules: ignore-file

Asked for by Michelle at Medulla on 16 October 2026, and by Robyn on 22 October: a prompt, like the
Joker, that asks whether a piece of work has been checked against inquiry-native organising every
time something is made. This is the mechanical half. It reads one artefact (a wiki page, a
markdown draft, or an HTML page) and looks for the six marks of an inquiry-native document:

  1. question   — which question the work serves
  2. hunches    — its hunches or hypotheses, stated so they could be wrong
  3. mind       — what would change our mind, or show it is wrong
  4. who        — who stands behind it, by name, and in which register
  5. reopen     — when it is reopened: a recommit, review or until date
  6. cannot     — what it cannot hold, or could not verify

A script can only find the marks. It cannot judge whether a hunch is specific enough to be wrong.
The reading pass in `.claude/skills/ino-check/SKILL.md` does that. This never edits anything and,
by default, never fails: it is a mirror, not a gate. `--strict` exits 1 when any mark is missing,
for anyone who wants a gate later.

A document that has no hunches, nothing that would change its mind and no reopen date reads as a
plan. That is sometimes right. It should know what it is.

Usage:
  python3 tools/ino_check.py wiki/some-page.md          # one artefact
  python3 tools/ino_check.py draft.html other.md        # several
  python3 tools/ino_check.py --json <files>             # for the app
  python3 tools/ino_check.py --strict <files>           # exit 1 on a missing mark
"""

import argparse
import html as htmlmod
import json
import re
import sys

MARKS = ["question", "hunches", "mind", "who", "reopen", "cannot"]
TITLES = {
    "question": "Which question does this serve?",
    "hunches": "What are its hunches?",
    "mind": "What would change our mind?",
    "who": "Who stands behind it, by name?",
    "reopen": "When is it reopened?",
    "cannot": "What can it not hold?",
}

DATE = r"\b(?:20\d\d-\d\d-\d\d|\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) 20\d\d|(?:January|February|March|April|May|June|July|August|September|October|November|December) 20\d\d)\b"

# Frontmatter keys that satisfy a mark on their own.
FM_KEYS = {
    "question": ("question", "serves", "commits_to", "inquiry"),
    "hunches": ("hunches", "hypotheses"),
    "mind": ("falsified_by", "would_be_wrong_if", "test"),
    "who": ("validated_by", "held_by", "steward", "author"),
    "reopen": ("recommit", "until", "review", "reopen", "next_review"),
    "cannot": ("cannot_hold", "not_verified", "unverified"),
}

# Body text patterns. Each is (pattern, what to call the evidence).
BODY = {
    "question": [
        (r"^#{1,4}\s*(?:the\s+)?(?:question|inquiry|inquiries)\b", "a question heading"),
        (r"^#{1,4}\s*why (?:it|this) matters", "a why-it-matters heading"),
        (r"\b(?:the|this|which|one) question (?:it|this|we|the work) (?:serves|tests|asks|holds|probes)", "names the question it serves"),
        (r"\b(?:serves|tests|probes) (?:the|this|one) (?:question|inquiry)\b", "names the question it serves"),
        (r"\bpart of \[\[[^\]]*(?:pilot|inquiry|question)[^\]]*\]\]", "links the inquiry it belongs to"),
        (r"\bwhat (?:we|this|the work) (?:are|is) trying to find out\b", "says what it is trying to find out"),
    ],
    "hunches": [
        (r"^#{1,4}\s*.*\b(?:hunch|hunches|hypothes[ei]s)\b", "a hunches heading"),
        (r"\b(?:our|the|a|first|strategic|three|two) hunch(?:es)?\b", "names a hunch"),
        (r"\bhypothes[ie]s\b", "names a hypothesis"),
        (r"\bproposed as (?:a )?hunch", "proposed as hunches"),
    ],
    "mind": [
        (r"\bwhat would (?:change (?:our|my|the|your) mind|make (?:it|this|them) wrong|show (?:it|this) (?:is|was) wrong|test (?:it|this|them)|falsify|count as an answer)", "says what would change its mind"),
        (r"\b(?:could|can|may|might) (?:turn out to |still )?be wrong\b", "says it could be wrong"),
        (r"\bspecific enough to be wrong\b", "says it could be wrong"),
        (r"\b(?:supported|complicated|silent)\s*[:.]", "marks hypotheses supported, complicated or silent"),
        (r"\bif (?:none|neither|no) (?:of (?:the|these|them) )?(?:appears?|arrives?|happens?|did|does)\b", "names the outcome that would count against it"),
        (r"\bthe finding is that\b", "names the finding that would count against it"),
        (r"\bsigns? (?:it is|that it is|of it) working\b", "names what would show it is working"),
    ],
    "who": [
        (r"(?:\*\*|^|\|\s*|\(|_)(?:settled for now|our hunch|open)(?:\*\*|_)?\s*[:|)]", "uses the three registers as marks"),
        (r"\bstands? behind\b", "says who stands behind it"),
        (r"\bvalidated by\b", "names who validated it"),
        (r"\b(?:written|drafted|proposed|held) by [A-Z][a-z]+", "names its author"),
        (r"\blast updated on .{4,30} by [A-Z]", "a header line with a name"),
        (r"\b(?:steward|holder|founder)s?\s*[:：]\s*[A-Z][a-z]+", "names a steward or holder"),
    ],
    "reopen": [
        (r"\brecommits?\b.*" + DATE, "a recommit date"),
        (r"\b(?:review(?:ed)?|revisit(?:ed)?|reopen(?:ed)?|recommit(?:ted)?|look again|next review)\b.{0,80}" + DATE, "a review date"),
        (r"\b(?:until|by)\s+" + DATE, "an until date"),
        (r"\b(?:end of|at the) (?:seed|cycle|10x100|month|quarter)\b.{0,60}\b(?:review|recommit)", "a review tied to a cycle"),
        (r"\bversion history\b", "a version history"),
    ],
    "cannot": [
        (r"\bcannot (?:hold|verify|see|read|check)\b", "says what it cannot hold or verify"),
        (r"\bcan(?:')?t (?:hold|verify|see|read|check)\b", "says what it cannot verify"),
        (r"\bnot (?:readable|stated|verified|confirmed|in the room|yet (?:built|written|tested))\b", "says what is not confirmed"),
        (r"\b(?:unsourced|unverified|unconfirmed|not confirmed)\b", "marks what is unconfirmed"),
        (r"\bleft out\b|\bwhat this (?:page|note|document) (?:does not|cannot)\b", "says what was left out"),
        (r"\b(?:somatic|sensory|place-based|embodied|tacit)\b.{0,80}\b(?:know|knowledge|knowing)\b", "names knowledge the text does not hold"),
    ],
}


def split_frontmatter(text):
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            fm = text[4:end]
            body = text[end + 4:]
            keys = {}
            for line in fm.splitlines():
                m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
                if m:
                    keys[m.group(1).lower()] = m.group(2).strip()
            return keys, body
    return {}, text


def html_to_text(text):
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", text, flags=re.I)
    text = re.sub(r"</(p|li|tr|div|section|h[1-6]|blockquote)>", "\n", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return htmlmod.unescape(text)


def _fm_hit(keys, mark):
    for k in FM_KEYS[mark]:
        v = keys.get(k, "")
        if v and v.lower() not in ("", "[]", "none", "null", "not confirmed", "not set", "machine"):
            return f"`{k}:` in the page's details"
    if mark == "question" and keys.get("type", "") == "question":
        return "the page is a question"
    if mark == "who" and keys.get("validation", "") in ("self", "peer", "collective"):
        return f"`validation: {keys['validation']}`"
    return None


def check_text(text, is_html=False):
    keys, body = ({}, html_to_text(text)) if is_html else split_frontmatter(text)
    # Blockquoted lines are someone else's words; do not credit them to the page.
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith(">")]
    flat = "\n".join(lines)
    out = {}
    for mark in MARKS:
        hit = _fm_hit(keys, mark)
        if hit:
            out[mark] = {"found": True, "evidence": hit}
            continue
        found = None
        for pat, label in BODY[mark]:
            flags = re.I | re.M
            m = re.search(pat, flat, flags)
            if m:
                line_no = flat.count("\n", 0, m.start()) + 1
                found = f"{label} (line {line_no})"
                break
        out[mark] = {"found": bool(found), "evidence": found or "nothing found"}
    return out


def verdict(result):
    missing = [m for m in MARKS if not result[m]["found"]]
    plan = all(m in missing for m in ("hunches", "mind", "reopen"))
    if not missing:
        return "reads as an inquiry: all six marks found", missing
    if plan:
        return "reads as a plan: no hunches, nothing that would change its mind, no reopen date", missing
    return f"{len(missing)} of six marks missing: " + ", ".join(missing), missing


def render(path, result):
    v, missing = verdict(result)
    lines = [f"INO check — {path}", f"  {v}", ""]
    lines.append("  | mark | found | evidence |")
    lines.append("  |---|---|---|")
    for m in MARKS:
        r = result[m]
        lines.append(f"  | {TITLES[m]} | {'yes' if r['found'] else 'no'} | {r['evidence']} |")
    lines.append("")
    lines.append("  A script finds the marks. Whether a hunch is specific enough to be wrong is the reading pass's call.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find the six marks of an inquiry-native document.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any mark is missing")
    a = ap.parse_args(argv)
    rc = 0
    results = {}
    for path in a.files:
        try:
            text = open(path, encoding="utf-8").read()
        except OSError as e:
            print(f"ino-check: cannot read {path}: {e}", file=sys.stderr)
            rc = 2
            continue
        res = check_text(text, is_html=path.lower().endswith((".html", ".htm")))
        results[path] = res
        v, missing = verdict(res)
        if a.strict and missing:
            rc = max(rc, 1)
        if not a.json:
            print(render(path, res))
            print()
    if a.json:
        print(json.dumps({p: {"marks": r, "verdict": verdict(r)[0]} for p, r in results.items()}, indent=1, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
