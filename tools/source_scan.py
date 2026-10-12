#!/usr/bin/env python3
"""
source_scan.py \u2014 before a model reads a source, look for what a person reading it cannot see.

Adopted 29 September 2026 from the awesome-llm-wiki review (the sanitiser in secure-llm-wiki).
The model workflows were hardened the same day against text a stranger may have written; this is
the other half. A source can carry instructions aimed at the model rather than the reader: in
zero-width or bidirectional characters, in Unicode tag characters, in a base64 run, or in HTML
that never renders. The ingest cascade then spreads whatever the model believed across a dozen
pages, and a contribution carries it into a commons.

It reports and never changes anything, because `raw/` is immutable: a source that says something
said it. What it asks for is a person's look before the ingest goes ahead.

Deliberately narrow. The instruction patterns are the ones that only make sense addressed to a
model ("ignore previous instructions"), not words that merely mention one, because this corpus
writes about AI all the time and a scan that flags every page gets ignored.

  python3 tools/source_scan.py raw/new-report.html          # report, exit 0
  python3 tools/source_scan.py --check raw/a.md raw/b.pdf   # exit 1 if anything is found
  python3 tools/source_scan.py --all                        # every file in raw/
  python3 tools/source_scan.py --secrets --check            # credentials in raw/, wiki/, docs/ (CI)

Credentials and personal links (added 2026-10-12) are the one kind of finding that is fixed rather
than reported: a key in raw/ is not part of the source's argument, and saving it is the leak.

Stdlib only. Reads text files; a PDF or other binary is skipped and says so.
"""

import argparse
import base64
import binascii
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".txt", ".html", ".htm", ".csv", ".json", ".xml", ".yml", ".yaml", ".js", ".svg"}

INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064\ufeff\u00ad]")
INVISIBLE_RUN = re.compile("(?:[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064\u00ad]\\S{0,3}){8,}")
BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
TAGS = re.compile("[\U000e0000-\U000e007f]")
INSTRUCTION = re.compile(
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+|your\s+)?"
    r"(?:previous|prior|above|earlier|preceding)\s+(?:instructions?|prompts?|rules|directions)"
    r"|\bdo\s+not\s+(?:tell|inform|alert|mention\s+(?:this|it)\s+to)\s+the\s+user"
    r"|\bnew\s+instructions\s*:"
    r"|<\|im_(?:start|end)\|>|\[/?INST\]|<\|(?:system|assistant|user)\|>",
    re.I)
BASE64 = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{400,}={0,2}")
DATA_URI = re.compile(r"data:[\w/+.-]+;base64,$")
HIDDEN = re.compile(
    r"<(\w+)[^>]*style\s*=\s*[\"'][^\"']*(?:display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0)"
    r"[^\"']*[\"'][^>]*>(.*?)</\1>", re.I | re.S)

# Credentials: added 2026-10-12, after a blog post saved from a Substack email reached
# prateek-llm-wiki carrying the reader's own unsubscribe and tracking tokens. GitGuardian reported
# it after the push. The shapes are the ones with a fixed prefix or structure, so ordinary prose
# about keys and tokens never matches.
CREDENTIAL = re.compile(
    r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"     # JWT: header.payload.signature
    r"|\bAKIA[0-9A-Z]{16}\b"                                             # AWS
    r"|\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"                           # Anthropic, OpenAI
    r"|\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}"
    r"|\bAIza[0-9A-Za-z_-]{35}"                                          # Google
    r"|\bxox[abprs]-[A-Za-z0-9-]{10,}"                                   # Slack
    r"|\b[spr]k_live_[A-Za-z0-9]{16,}"                                   # Stripe
    r"|-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"
    r"|[?&](?:token|access_token|auth|api_key|apikey|key|sig|signature|secret|password)"
    r"=[A-Za-z0-9._~%-]{16,}")
# Links an email service writes for one reader. They identify the reader, and some act for them
# (unsubscribe, sign-in). Save the public link to the piece instead.
PERSONAL_LINK = re.compile(
    r"https?://(?:[\w-]+\.)?substack\.com/redirect/"
    r"|https?://[\w.-]*list-manage\.com/track/"
    r"|https?://[\w.-]*\.ct\.sendgrid\.net/"
    r"|https?://email\.[\w.-]+/c/")
SECRET_KINDS = {"credential", "personal-link"}


def _visible(ch):
    return f"<U+{ord(ch):04X} {unicodedata.name(ch, 'UNNAMED')}>"


def _snippet(text, start, end, width=40):
    s = text[max(0, start - width):min(len(text), end + width)].replace("\n", " ")
    s = INVISIBLE.sub(lambda m: _visible(m.group()), s)
    s = BIDI.sub(lambda m: _visible(m.group()), s)
    s = TAGS.sub(lambda m: _visible(m.group()), s)
    return s.strip()


def _line(text, pos):
    return text.count("\n", 0, pos) + 1


def _decodes_to_text(run):
    try:
        raw = base64.b64decode(run + "=" * (-len(run) % 4), validate=False)
    except (binascii.Error, ValueError):
        return False
    if len(raw) < 200:
        return False
    printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in raw)
    return printable / len(raw) > 0.95


def _without_invisibles(text):
    """The text with invisible characters dropped, and each kept character's original index."""
    keep = [i for i, ch in enumerate(text) if not INVISIBLE.match(ch)]
    return "".join(text[i] for i in keep), keep


def _hidden_spans(text):
    return [(m.start(2), m.end(2)) for m in HIDDEN.finditer(text)]


def scan_text(text, name=""):
    """Findings in `text`: a list of {kind, line, snippet} (plus `hidden` for HTML that never renders)."""
    out = []

    def add(kind, start, end, **extra):
        out.append({"kind": kind, "line": _line(text, start), "snippet": _snippet(text, start, end), **extra})

    # One zero-width space is ordinary in scraped web copy (after an emoji, in a blank cell) and
    # hides nothing. A run of them can encode text a person never sees, so a run is the finding.
    for m in INVISIBLE_RUN.finditer(text):
        add("invisible", m.start(), m.end())
    for m in BIDI.finditer(text):
        add("bidi", m.start(), m.end())
    for m in TAGS.finditer(text):
        add("tag-characters", m.start(), m.end())

    hidden = _hidden_spans(text) if pathlib.Path(name).suffix.lower() in (".html", ".htm", ".svg") else []
    # Matched with invisible characters removed, so "ig<ZWSP>nore previous instructions" is caught.
    plain, where = _without_invisibles(text)
    for m in INSTRUCTION.finditer(plain):
        start, end = where[m.start()], where[m.end() - 1] + 1
        inside = any(a <= start < b for a, b in hidden)
        add("instruction", start, end, **({"hidden": True} if inside else {}))

    for m in BASE64.finditer(text):
        if DATA_URI.search(text[max(0, m.start() - 60):m.start()]):
            continue  # an embedded image or font
        if _decodes_to_text(m.group()):
            add("encoded-text", m.start(), m.start() + 20)

    # The snippet for these never carries the value: a report that prints the key leaks it again.
    for m in CREDENTIAL.finditer(text):
        out.append({"kind": "credential", "line": _line(text, m.start()),
                    "snippet": m.group()[:6] + "… (" + str(len(m.group())) + " characters, not shown)"})
    for m in PERSONAL_LINK.finditer(text):
        out.append({"kind": "personal-link", "line": _line(text, m.start()),
                    "snippet": m.group() + "…"})
    return out


def scan_file(path):
    p = pathlib.Path(path)
    if p.suffix.lower() not in TEXT_SUFFIXES or not p.is_file():
        return None
    return scan_text(p.read_text(encoding="utf-8", errors="replace"), p.name)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hidden text and model-directed instructions in sources.")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true", help="every file under raw/")
    ap.add_argument("--check", action="store_true", help="exit 1 if anything is found")
    ap.add_argument("--secrets", action="store_true",
                    help="credentials and personal links only, in raw/, wiki/ and docs/ (the CI gate)")
    ap.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root)
    if args.secrets:
        paths = [str(p) for d in ("raw", "wiki", "docs") for p in sorted((root / d).rglob("*")) if p.is_file()]
    elif args.all:
        paths = [str(p) for p in sorted((root / "raw").rglob("*")) if p.is_file()]
    else:
        paths = args.paths
    if not paths and not args.secrets:
        ap.error("name a file, or --all")
    found = skipped = 0
    for path in paths:
        got = scan_file(path)
        if got is None:
            skipped += 1
            continue
        if args.secrets:
            got = [f for f in got if f["kind"] in SECRET_KINDS]
        for f in got:
            found += 1
            where = " (in HTML that never renders)" if f.get("hidden") else ""
            print(f"{path}:{f['line']}  {f['kind']}{where}  {f['snippet']}")
    print(f"\nsource scan: {found} finding(s) in {len(paths) - skipped} text file(s)"
          + (f", {skipped} not text and not scanned" if skipped else "") + ".")
    if found and args.secrets:
        print("A credential or a reader's personal link is in the wiki. Remove it before this is merged:\n"
              "save the public link to the piece instead of the email's link, and if a real key was\n"
              "committed, revoke it. It stays in the history, so the key is the thing to fix.")
    elif found:
        print("Read each one before ingesting. The source is left as it is; say what it contains.\n"
              "A credential or personal link is the exception: do not save it into raw/ at all.")
    return 1 if (args.check and found) else 0


if __name__ == "__main__":
    raise SystemExit(main())
