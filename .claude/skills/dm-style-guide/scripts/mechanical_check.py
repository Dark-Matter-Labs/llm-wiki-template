#!/usr/bin/env python3
"""
mechanical_check.py — deterministic audit of a draft against Dm Appendix A
(house conventions) and the "words to use with care" list.

WHAT IT IS: reliable, rule-based text matching. It flags the mechanical,
checkable conventions — Dm/DML consistency, mixed British/American spelling,
straight quotes, closed-up em dashes, number style, and flagged words.

WHAT IT IS NOT: it does not judge whether a flagged word is "doing work or
padding", and it does not assess audience, complexity, coining, positionality,
or channel fit — those are judgment calls for a human reviewer (see the
reference files). Treat every word-list hit as "check this", not "remove this".

Usage:
    python mechanical_check.py path/to/draft.md
    python mechanical_check.py path/to/draft.txt --json
    python mechanical_check.py path/to/draft.docx        # needs python-docx

Exit code is 0 always (this is an advisory report, not a gate).
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Reading input
# ---------------------------------------------------------------------------
def read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md", ".markdown", ".html"):
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        try:
            import docx  # python-docx
        except ImportError:
            sys.exit(
                "Reading .docx needs python-docx. Install with:\n"
                "  pip install python-docx --break-system-packages\n"
                "Or convert the draft to .txt/.md first."
            )
        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)
    sys.exit(f"Unsupported file type: {suffix}. Use .txt, .md, or .docx.")


# ---------------------------------------------------------------------------
# Rule data
# ---------------------------------------------------------------------------
# British -> American pairs. We flag the AMERICAN form as the thing to check,
# since house preference is British. Consistency is the real test, so the
# report also reports which varieties appear.
BRITISH_AMERICAN = {
    # american_form : british_form
    "organize": "organise", "organized": "organised", "organizing": "organising",
    "organization": "organisation", "recognize": "recognise",
    "recognized": "recognised", "realize": "realise", "realized": "realised",
    "analyze": "analyse", "analyzed": "analysed", "behavior": "behaviour",
    "behaviors": "behaviours", "color": "colour", "colors": "colours",
    "favor": "favour", "labor": "labour", "neighbor": "neighbour",
    "center": "centre", "centers": "centres", "fiber": "fibre",
    "theater": "theatre", "meter": "metre", "program": "programme",
    "catalog": "catalogue", "dialog": "dialogue", "defense": "defence",
    "license": "licence", "practice_v": "practise",  # noun/verb — advisory only
    "traveling": "travelling", "traveled": "travelled", "modeling": "modelling",
    "labeled": "labelled", "labeling": "labelling", "fulfill": "fulfil",
    "enroll": "enrol", "skillful": "skilful",
}

# Words/phrases to use with care, with the guide's suggested alternative.
FLAGGED_WORDS = {
    r"\bdisrupt(ive|ion|ing|ed|s)?\b": "say what is being changed and how (reshape, reconfigure, challenge, replace)",
    r"\bleverage(d|s|ing)?\b": "use, draw on",
    r"\butilis(e|ed|es|ing)\b": "use",
    r"\butiliz(e|ed|es|ing)\b": "use",
    r"\bunpack(ed|ing|s)?\b": "examine, look closely at",
    r"\bdeep[\s-]dive(s|d)?\b": "examine, look closely at",
    r"\bdouble[\s-]click\b": "examine, look closely at",
    r"\btransformative\b": "describe the actual change concretely",
    r"\bparadigm shift\b": "describe the actual change concretely",
    r"\bgame[\s-]chang(ing|er)\b": "describe the actual change concretely",
    r"\bholistic\b": "say what is connected to what",
    r"\bsynergy\b": "say what is connected to what",
    r"\bempower(ed|ing|s|ment)?\b": "name the actor and the action",
    r"\bin order to\b": "to",
    r"\bthe fact that\b": "that",
    r"\bit should be noted that\b": "(just say it)",
    r"\bvery\b": "cut, or be specific",
    r"\breally\b": "cut, or be specific",
    r"\bquite\b": "cut, or be specific",
    r"\barguably\b": "cut, or be specific",
    # AI-tells
    r"\bdelve(d|s|ing)?\b": "rewrite in your own specific words (AI-tell)",
    r"\btapestry\b": "rewrite in your own specific words (AI-tell)",
    r"\btestament to\b": "rewrite in your own specific words (AI-tell)",
    r"\bnavigat(e|ing) the complexit(y|ies)\b": "rewrite in your own specific words (AI-tell)",
}

# 'enable' is flagged only as a soft note (it has many legitimate uses).
SOFT_FLAGS = {
    r"\benabl(e|ed|es|ing)\b": "vague — name the actor and the action if it hides who does what",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def line_hits(text, pattern, flags=re.IGNORECASE):
    """Return list of (line_no, line_text, matched_text) for a regex."""
    out = []
    rx = re.compile(pattern, flags)
    for i, line in enumerate(text.splitlines(), 1):
        for m in rx.finditer(line):
            out.append((i, line.strip(), m.group(0)))
    return out


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
def check_org_naming(text):
    findings = []
    variants = {}
    for label, pat in {
        "Dm": r"\bDm\b",
        "DML": r"\bDML\b",
        "DM": r"\bDM\b",
        "dm (lowercase)": r"\bdm\b",
    }.items():
        hits = line_hits(text, pat, flags=0)  # case-sensitive
        if hits:
            variants[label] = hits
    used = [k for k in variants if k != "DM" or True]
    # Report if more than one of the org abbreviations appears.
    distinct = [k for k in variants if k in ("Dm", "DML", "DM", "dm (lowercase)")]
    if len(distinct) > 1:
        detail = ", ".join(f"{k} ({len(v)}x)" for k, v in variants.items())
        findings.append({
            "rule": "Org naming consistency",
            "severity": "high",
            "message": f"Multiple abbreviations for the organisation appear: {detail}. "
                       f"Pick one ('Dm' is house default) and hold it; 'DML' only where "
                       f"disambiguation is genuinely needed.",
            "locations": [{"line": ln, "text": tx, "match": mt}
                          for k in variants for (ln, tx, mt) in variants[k][:5]],
        })
    # Full name on first mention
    if re.search(r"\bDm\b", text) and not re.search(r"Dark Matter Labs", text):
        findings.append({
            "rule": "Full name on first mention",
            "severity": "medium",
            "message": "'Dm' is used but 'Dark Matter Labs' never appears. Spell out "
                       "'Dark Matter Labs' on first mention, then 'Dm' thereafter.",
            "locations": [],
        })
    for bad in ("Dark Matter Laboratories", "DarkMatter Labs"):
        hits = line_hits(text, re.escape(bad), flags=0)
        if hits:
            findings.append({
                "rule": "Org name spelling",
                "severity": "high",
                "message": f"'{bad}' appears — house form is 'Dark Matter Labs'.",
                "locations": [{"line": ln, "text": tx, "match": mt} for ln, tx, mt in hits],
            })
    return findings


def check_spelling_variety(text):
    findings = []
    american_present = {}
    for am, br in BRITISH_AMERICAN.items():
        token = am.split("_")[0]  # strip the _v marker
        hits = line_hits(text, rf"\b{re.escape(token)}\b")
        if hits:
            american_present[token] = (br, hits)
    if american_present:
        locs = []
        for token, (br, hits) in american_present.items():
            for ln, tx, mt in hits[:3]:
                locs.append({"line": ln, "text": tx, "match": mt,
                             "suggest": br})
        findings.append({
            "rule": "Spelling variety (British vs American)",
            "severity": "medium",
            "message": "American spelling forms detected. House preference is British "
                       "English; the firm rule is consistency — do not mix varieties "
                       "within a piece. Confirm whether the piece is meant to be "
                       "British throughout.",
            "locations": locs,
        })
    return findings


def check_quotes(text):
    findings = []
    straight_double = line_hits(text, r'"', flags=0)
    straight_single = line_hits(text, r"(?<=\w)'(?=\w)|(?<=\s)'|'(?=\s)", flags=0)
    if straight_double:
        findings.append({
            "rule": "Straight quotation marks",
            "severity": "low",
            "message": f"Straight double quotes (\") found ({len(straight_double)}x). "
                       f"Use smart (curly) quotes throughout; single '…' as first level.",
            "locations": [{"line": ln, "text": tx, "match": '"'} for ln, tx, _ in straight_double[:6]],
        })
    return findings


def check_dashes(text):
    findings = []
    # closed-up em dash between word characters: word—word
    closed_em = line_hits(text, r"\w\u2014\w", flags=0)
    if closed_em:
        findings.append({
            "rule": "Closed-up em dash",
            "severity": "low",
            "message": f"Closed-up em dash (word—word) found ({len(closed_em)}x). "
                       f"Use a spaced dash — like this — for parenthetical breaks, "
                       f"consistently.",
            "locations": [{"line": ln, "text": tx, "match": mt} for ln, tx, mt in closed_em[:6]],
        })
    return findings


def check_numbers(text):
    findings = []
    # numerals 1-10 standalone (not with units/%, not in dates/versions)
    small_numerals = []
    rx = re.compile(r"(?<![\w.$%°-])([1-9]|10)(?![\w.%°])")
    for i, line in enumerate(text.splitlines(), 1):
        for m in rx.finditer(line):
            # crude filter: skip if followed by unit-ish context handled above
            small_numerals.append((i, line.strip(), m.group(0)))
    if small_numerals:
        findings.append({
            "rule": "Numbers: spell out one to ten",
            "severity": "low",
            "message": f"Standalone numerals 1–10 found ({len(small_numerals)}x). "
                       f"Spell out one to ten; numerals for 11+. Always numerals with "
                       f"units and percentages (3°C, 40%). Advisory — check each in context.",
            "locations": [{"line": ln, "text": tx, "match": mt} for ln, tx, mt in small_numerals[:8]],
        })
    return findings


def check_flagged_words(text):
    findings = []
    for pattern, suggestion in FLAGGED_WORDS.items():
        hits = line_hits(text, pattern)
        if hits:
            findings.append({
                "rule": "Word to use with care",
                "severity": "info",
                "message": f"'{hits[0][2]}' (and similar) — {suggestion}. "
                           f"Not banned; check it is doing specific work, not padding.",
                "locations": [{"line": ln, "text": tx, "match": mt} for ln, tx, mt in hits[:6]],
            })
    for pattern, suggestion in SOFT_FLAGS.items():
        hits = line_hits(text, pattern)
        if hits:
            findings.append({
                "rule": "Word to use with care (soft)",
                "severity": "info",
                "message": f"'{hits[0][2]}' — {suggestion}.",
                "locations": [{"line": ln, "text": tx, "match": mt} for ln, tx, mt in hits[:4]],
            })
    return findings


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_all(text):
    findings = []
    findings += check_org_naming(text)
    findings += check_spelling_variety(text)
    findings += check_quotes(text)
    findings += check_dashes(text)
    findings += check_numbers(text)
    findings += check_flagged_words(text)
    return findings


SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def print_report(findings, path):
    print(f"\n=== Dm mechanical check — {path.name} ===")
    print("Deterministic Appendix A checks. Advisory, not a gate.\n")
    if not findings:
        print("No mechanical issues flagged. (Judgment sections still need human review.)")
        return
    findings.sort(key=lambda f: SEV_ORDER.get(f["severity"], 9))
    for f in findings:
        print(f"[{f['severity'].upper()}] {f['rule']}")
        print(f"  {f['message']}")
        for loc in f["locations"]:
            sug = f"  -> {loc['suggest']}" if loc.get("suggest") else ""
            print(f"    line {loc['line']}: …{loc['match']}…{sug}")
        print()
    print("Reminder: this covers only the mechanical conventions. Audience, "
          "complexity, coined terms, positionality, and channel fit are judgment "
          "calls — review them against the reference files.")


def main():
    ap = argparse.ArgumentParser(description="Dm Appendix A mechanical checker")
    ap.add_argument("file", help="path to draft (.txt, .md, or .docx)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()
    path = Path(args.file)
    if not path.exists():
        sys.exit(f"File not found: {path}")
    text = read_text(path)
    findings = run_all(text)
    if args.json:
        print(json.dumps({"file": str(path), "findings": findings}, indent=2))
    else:
        print_report(findings, path)


if __name__ == "__main__":
    main()
