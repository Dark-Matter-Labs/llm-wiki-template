#!/usr/bin/env python3
"""check_prose.py — the mechanical half of `ai-detox`, as a ratchet.

The `ai-detox` skill is the judgement. This is the part a script can settle: the banned words,
the X-not-Y construction, and the em dash. It exists because a rule nobody checks is a rule that
decays, and this house already learned that twice today, with the house spellings and with the
onboarding docs.

WHY IT IS A RATCHET AND NOT A GATE. Measured on 2026-09-15, across 867 pages, with frontmatter,
code, page titles, URLs and quotations all excluded:

    banned words      636
    X-not-Y            399
    em dashes       20,559
    files affected     426  of 867

A gate would fail on the first run and stay failing. Rewriting 867 pages to satisfy a style rule
written in September is not obviously wanted, and a check that can only be satisfied by work
nobody has agreed to gets switched off. So this records what is there and fails only on a RISE:
a file's count may fall and may never grow, and a new file starts at zero.

That makes the rule bind where it can bind, on prose written from now on, without demanding a
retrospective rewrite of prose written before it existed.

ONE LIMIT WORTH KNOWING. The X-not-Y detector stops at a full stop. "It's not a shortage of
capital. It is a break in continuity." is the same move split over two sentences and is NOT
caught, because a pattern allowed to cross a sentence boundary matches unrelated pairs and a
check that flags ordinary prose gets ignored. Eight of the nine cases in `tools/test_check_prose.py`
are caught; that ninth is the known gap.

WHAT IT DOES NOT CHECK. The shapes that matter most and cannot be regexed: the recap paragraph,
the closing offer, the sentence whose only job is to say the last one mattered, the reflexive
rule of three. `ai-detox` lists them and a person applies them. A green run here is not a claim
that the prose is good.

WHAT IT NEVER READS. `raw/`, which is immutable, and any blockquoted line, which is somebody
else's words. Page titles in `[[...]]` are names of things, not prose: a page called
"Computational Landscape Adaptation Facility" cannot be renamed to satisfy a word list.

    python3 tools/check_prose.py                    # the report
    python3 tools/check_prose.py --check            # exit 1 on any rise (CI)
    python3 tools/check_prose.py --update-baseline  # record deliberately, with a reason
"""
import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCAN = ROOT / "wiki"
BASELINE = ROOT / "tools" / "prose-baseline.json"

#: House list plus the additions from `ai-writing-detox`. "landscape" is here for its abstract
#: use; the carve-out for land is in the skill and cannot be made by a regex, so a page about
#: hillsides carries its count in the baseline and that is the honest outcome.
BANNED_WORDS = (
    "delve realm tapestry testament underscore showcase holistic nuanced multifaceted "
    "transformative game-changer unpack elevate crucial pivotal robust seamless leverage "
    "leveraging landscape utilize comprehensive cutting-edge synergy paradigm empower "
    "innovative sophisticated ecosystem"
).split()

BANNED_PHRASES = [
    "here's the thing", "hope this helps", "at the end of the day", "in today's world",
    "let's dive in", "let's delve", "the reality is", "simply put",
    "it's important to note", "it's worth mentioning", "it goes without saying",
    "as we all know", "without further ado", "in this article, we will",
    "to be fair", "to be honest", "when it comes to", "in terms of",
    "moving forward", "going forward", "at this point in time", "due to the fact that",
]

WORD_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in BANNED_WORDS) + r")\b", re.I)
PHRASE_RE = re.compile("|".join(re.escape(p) for p in BANNED_PHRASES), re.I)

#: "is not just X, it's Y" and its relatives. `ai-writing-detox` calls this the dominant
#: 2025-2026 ChatGPT and Claude signature, which is why it is checked rather than trusted.
XNOTY_RE = re.compile(
    # Two shapes, because "isn't" already carries the negation and a single pattern that
    # demanded a following "not" silently matched neither of the source skill's own examples.
    r"(?:"
    r"\b(?:is|are|was|were|it'?s|that'?s|this\s+is)\s+not\s+"
    r"|\b(?:isn't|aren't|wasn't|weren't)\s+"
    r")"
    r"(?:just\s+|merely\s+|only\s+|about\s+)?"
    r"[^.;\n]{2,60}?[,\u2014-]\s*"
    # Only the explicit continuation. "but" was tried and dropped: "the vote is not final but
    # provisional" is ordinary English, and a check that flags ordinary English gets ignored.
    r"(?:it'?s|it\s+(?:is|was)|they'?re|they\s+(?:are|were)|this\s+(?:is|was)|that'?s)\b",
    re.I)

CATEGORIES = ("words", "phrases", "xnoty", "emdash")


def prose(text: str) -> str:
    """Only what a person reads through. Everything else is not prose and must not count."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)       # frontmatter
    text = re.sub(r"```.*?```", " ", text, flags=re.S)             # fenced code
    text = re.sub(r"`[^`\n]*`", " ", text)                         # inline code
    text = re.sub(r"\[\[[^\]]*\]\]", " ", text)                    # page titles are names
    text = re.sub(r"\[([^\]]*)\]\([^)\s]*\)", r"\1", text)         # link text, never the target
    text = re.sub(r"https?://\S+", " ", text)
    # A quotation is somebody else's words. Same reason `raw/` is never corrected.
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">"))


def count(text: str) -> dict:
    t = prose(text)
    return {"words": len(WORD_RE.findall(t)),
            "phrases": len(PHRASE_RE.findall(t)),
            "xnoty": len(XNOTY_RE.findall(t)),
            "emdash": t.count("—")}


def scan(root=SCAN) -> dict:
    out = {}
    for p in sorted(root.rglob("*.md")):
        c = count(p.read_text(encoding="utf-8", errors="ignore"))
        if any(c.values()):
            out[str(p.relative_to(ROOT))] = c
    return out


def load_baseline() -> dict:
    if not BASELINE.exists():
        return {}
    d = json.loads(BASELINE.read_text(encoding="utf-8"))
    return d.get("files", {})


def compare(now: dict, base: dict):
    """(risen, appeared, fallen). A fall is good news and is reported, never failed on."""
    risen, appeared, fallen = [], [], []
    for path, c in sorted(now.items()):
        was = base.get(path)
        if was is None:
            appeared.append((path, c))
            continue
        up = {k: (c[k], was.get(k, 0)) for k in CATEGORIES if c[k] > was.get(k, 0)}
        if up:
            risen.append((path, up))
        elif any(c[k] < was.get(k, 0) for k in CATEGORIES):
            fallen.append(path)
    return risen, appeared, fallen


def write_baseline(now: dict, reason: str):
    BASELINE.write_text(json.dumps({
        # Filenames, not prose. Four existing page slugs spell civilisation with an s, and
        # `house_rules.py` reads this file and flags them. Slugs and paths are exempt from the
        # house spelling by design; the marker is the escape that rule documents.
        "_comment": "house-rules: ignore-file (this file lists page PATHS, and four existing "
                    "slugs spell civilisation with an s; slugs are exempt from the house "
                    "spelling by design). Mechanical ai-detox findings per file. A debt register, not an exemption: "
                    "it must only ever shrink. A file may fall and may never rise, and a new "
                    "file starts at zero. Recording a new file with a count above zero is a "
                    "deliberate act and needs a reason — recovering old work is the usual one. "
                    "See tools/check_prose.py for why this is a ratchet and not a gate.",
        "recorded": "2026-09-15",
        "reason": reason,
        "totals": {k: sum(c[k] for c in now.values()) for k in CATEGORIES},
        "files": now,
    }, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description="The mechanical half of ai-detox, as a ratchet.")
    ap.add_argument("--check", action="store_true", help="exit 1 on any rise or new offender")
    ap.add_argument("--update-baseline", action="store_true",
                    help="record the current state; a deliberate act, so give --reason")
    ap.add_argument("--reason", default="", help="why the baseline is being moved")
    a = ap.parse_args(argv)

    now = scan()
    totals = {k: sum(c[k] for c in now.values()) for k in CATEGORIES}

    if a.update_baseline:
        if not a.reason:
            print("--update-baseline needs --reason. A silently moved ratchet is not a ratchet.",
                  file=sys.stderr)
            return 2
        write_baseline(now, a.reason)
        print(f"baseline recorded — {len(now)} file(s), {sum(totals.values())} finding(s)")
        return 0

    base = load_baseline()
    if not base:
        print(f"prose — {len(now)} file(s) carry findings: "
              + " · ".join(f"{k} {totals[k]}" for k in CATEGORIES))
        print("\n  No baseline yet. Run --update-baseline --reason '...' to record this as the")
        print("  starting debt; after that a file may fall and may never rise.")
        return 0

    risen, appeared, fallen = compare(now, base)
    print(f"prose — {len(now)} file(s) carry findings: "
          + " · ".join(f"{k} {totals[k]}" for k in CATEGORIES))
    if fallen:
        print(f"  {len(fallen)} file(s) improved since the baseline.")

    if not risen and not appeared:
        print("\n  prose OK — nothing rose.")
        return 0

    print()
    for path, up in risen:
        print(f"  ROSE  {path}")
        for k, (now_n, was_n) in up.items():
            print(f"          {k}: {was_n} -> {now_n}")
    for path, c in appeared:
        print(f"  NEW   {path}  "
              + " ".join(f"{k} {c[k]}" for k in CATEGORIES if c[k]))
    print()
    print("  New prose is meant to be clean. If this is recovered or imported work, record it")
    print("  with `--update-baseline --reason '...'` so the debt is visible and attributed.")
    return 1 if a.check else 0


if __name__ == "__main__":
    sys.exit(main())
