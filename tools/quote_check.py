#!/usr/bin/env python3
"""
quote_check.py — is a quoted passage really in the source it cites?

## Why this exists

`check_sources.py` asks whether a cited file exists. `verification.py` records a person's reading
of a claim. Neither asks the one thing a machine can answer exactly: when a page puts words in
quotation marks beside `(raw/file)`, are those words in that file? A misquote with a real
citation is worse than no citation, because it looks like evidence.

Staged on 2026-09-29, from the awesome-llm-wiki review. The first test then found that of about
335 quotes beside a citation, only 14 could be checked on this machine, because almost every
source is a PDF and PDFs had no text copy. So this reads PDFs through `pdftotext` where it is
installed, and keeps the text in `.cache/source-text/`, which git ignores: nothing new enters the
repository, and `raw/` is never touched. Word and PowerPoint files are read directly; they are
zip archives of XML.

## What it decides, and what it leaves to a person

Mechanical only. One pre-registered study found two model judges agreed almost not at all on
whether a citation was grounded (correlation 0.04), so no model is asked. For each quote:

  * **found** — every word is in the source, in order. Case, punctuation, curly quotes,
    ligatures and line-break hyphens are ignored, because they are the same words.
  * **close** — the source has a passage at least 60% alike. Shown side by side: a light
    paraphrase inside quotation marks, or a misquote. A person decides which.
  * **not-found** — nothing in the source comes near. Read these first.
  * **unchecked** — the source is not on this machine, or is a kind of file this cannot read.
    Said plainly, and never counted as a failure.

A paraphrase cannot be checked this way, and nothing here pretends otherwise. That is what the
weekly `verification.py --sample 3` is for. This tool never writes a `{✓ …}` mark: a found quote
is evidence for a person, not a verification.

## Why it is not a CI gate

CI checks out a fraction of the sources by design (see `check_sources.py`), so most quotes would
read as unchecked there. It runs where the sources are: in `lint`, and at `ingest` on the pages
just written, where `--check` fails if a new quote is not in its source, so the misquote is fixed
before anyone is asked to save it.

  python3 tools/quote_check.py                         # the report for the whole wiki
  python3 tools/quote_check.py --check wiki/a.md ...   # exit 1 if a quote on these pages is not found
  python3 tools/quote_check.py --json                  # every result

Stdlib only; `pdftotext` is optional.

house-rules: ignore-file (it matches a source's British spelling of civilization on purpose)
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from array import array
from collections import Counter
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher

ROOT = pathlib.Path(__file__).resolve().parent.parent
PDFTOTEXT = shutil.which("pdftotext")
CACHE = ".cache/source-text"

MIN_WORDS = 5          # shorter quotes are mostly phrases and titles, and match anywhere
CLOSE = 0.6            # share of the quote's words found in order in one passage
SHOW = 0.4             # below this, a nearest passage is not worth showing
MAX_ANCHORS = 1200
PER_ANCHOR = 200       # places looked at per word pair or rare word, spread across the source

# One character at a time, never `[^()]+` inside `*`: that nesting backtracks exponentially on an
# unclosed bracket, and one typo in a page hung the whole run (found in review, 2026-10-01).
CITE = re.compile(r"\((raw/(?:[^()]|\([^()]*\))*)\)")
SOURCE = re.compile(r"raw/.+?\.(?:pdf|md|markdown|txt|html?|docx|pptx|xlsx|csv|json|svg|png|jpe?g)"
                    r"(?=\s|$|[,;):#])", re.I)
QUOTE = re.compile('"([^"]+)"|\u201c([^\u201d]+)\u201d')
ELLIPSIS = re.compile(r"\s*(?:\u2026|\.\.\.|\[\s*(?:\u2026|\.\.\.)\s*\])\s*")
BRACKETED = re.compile(r"\S*\[[^\]]*\]\S*")   # an editor's change: "[T]he", "migrate[s]", "[the fund]"
GAP_CHARS = 2500       # how far apart the parts of a quote either side of an ellipsis may sit
BRACKET_CHARS = 40     # what a bracketed change may stand for: a word or a short phrase
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
TOKEN = re.compile("[^\\W_]+(?:[-\u2010\u2011'\u2019][^\\W_]+)*")
UNIT_START = re.compile(r"^\s*(?:[-*+]|\d+\.)\s|^\s*\|")
TEXT_TYPES = {".md", ".markdown", ".txt", ".csv", ".json"}
MARKUP_TYPES = {".html", ".htm", ".svg"}
SKIP_DIRS = {"log", "index"}
SKIP_FILES = {"log.md", "index.md"}


@dataclass
class Quote:
    page: str
    line: int
    quote: str
    sources: list = field(default_factory=list)


@dataclass
class Result(Quote):
    verdict: str = "unchecked"
    reason: str = ""
    source: str = ""
    alike: float = 0.0
    passage: str = ""


# ---------------------------------------------------------------- words


def _clean(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).replace("\u00ad", "")
    return re.sub(r"(?<=[^\W_])-[ \t]*\n\s*(?=[^\W_])", "", s)    # consti-\ntutive


def _norm(token: str) -> str:
    # The house rule spells civilization with a z, inside quotations too, so a source's
    # "civilisation" and the page's "civilization" are the same word for this purpose.
    return re.sub("[-\u2010\u2011'\u2019]", "", token.lower()).replace("civilis", "civiliz")


def _tokens(s: str):
    """The cleaned text, each word's start offset in it, and the normalised words."""
    c = _clean(s)
    starts, ws = array("l"), []
    for m in TOKEN.finditer(c):
        starts.append(m.start())
        ws.append(_norm(m.group()))
    return c, starts, ws


def words(s: str) -> list:
    return _tokens(s)[2]


# ---------------------------------------------------------------- quotes on pages


def sources_in(group: str) -> list:
    group = " ".join(group.split())                    # a citation wrapped across a line
    found = [m.group() for m in SOURCE.finditer(group)]
    return found or [group.split(";")[0].split(", ")[0].strip()]


def _body(text: str):
    """The body after the frontmatter, and the line number it starts on."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            nl = text.find("\n", end + 4)
            cut = len(text) if nl == -1 else nl + 1
            return text[cut:], text.count("\n", 0, cut) + 1
    return text, 1


def _units(body: str, first: int):
    """Paragraphs, list items and table rows, as (start line, text). Headings stand alone."""
    unit, start = [], first
    for n, line in enumerate(body.split("\n"), first):
        if not line.strip() or line.lstrip().startswith("#") or (unit and UNIT_START.match(line)):
            if unit:
                yield start, "\n".join(unit)
            unit = [] if not line.strip() or line.lstrip().startswith("#") else [line]
            start = n
            continue
        if not unit:
            start = n
        unit.append(line)
    if unit:
        yield start, "\n".join(unit)


def _unlink(s: str) -> str:
    return WIKILINK.sub(lambda m: m.group(2) or m.group(1), s)


def _blockquote(start: int, text: str, cites: list):
    inner = "\n".join(re.sub(r"^\s*>\s?", "", ln) for ln in text.split("\n"))
    inner = CITE.sub("", inner)
    inner = "\n".join(ln for ln in inner.split("\n") if not re.match(r"^\s*[\u2014\u2013-]\s", ln))
    inner = " ".join(inner.split()).strip("\"\u201c\u201d ")
    if len(words(inner)) >= MIN_WORDS:
        yield start, _unlink(inner), sources_in(cites[0].group(1))


def _cite_for(m, cites):
    """The citation a quote belongs to: the one around it, else the next, else the last before."""
    for group in ([c for c in cites if c.start() <= m.start() and m.end() <= c.end()],
                  [c for c in cites if c.start() >= m.end()]):
        if group:
            return group[0]
    before = [c for c in cites if c.end() <= m.start()]
    return before[-1] if before else None


def _inline(start: int, text: str, cites: list):
    for m in QUOTE.finditer(text):
        q = " ".join((m.group(1) or m.group(2)).split())
        if "raw/" in q or "](" in q or "http" in q or len(words(q)) < MIN_WORDS:
            continue
        cite = _cite_for(m, cites)
        if cite is None:
            continue
        yield start + text.count("\n", 0, m.start()), _unlink(q), sources_in(cite.group(1))


def _quotation(text: str) -> bool:
    """A blockquote is a quotation unless it opens with a bold label: `> **Provenance.** ...` is
    the wiki's own call-out box, and 3 in 4 of the first run's misquotes were boxes like it."""
    s = text.lstrip()
    return s.startswith(">") and not re.match(r">\s*(?:\*\*|__|\[!)", s)


def _page_quotes(root: pathlib.Path, path: pathlib.Path):
    body, first = _body(path.read_text(encoding="utf-8", errors="replace"))
    rel = str(path.relative_to(root))
    for start, text in _units(body, first):
        cites = list(CITE.finditer(text))
        if not cites:
            continue
        if _quotation(text):
            found = _blockquote(start, text, cites)
        else:
            plain = re.sub(r"(?m)^\s*>\s?", "", text)       # a call-out box's line markers
            found = _inline(start, plain, list(CITE.finditer(plain)))
        for line, q, srcs in found:
            yield Quote(page=rel, line=line, quote=q, sources=srcs)


def _pages(root: pathlib.Path, pages=None):
    if pages:
        return [root / p for p in pages]
    out = []
    for p in sorted((root / "wiki").rglob("*.md")):
        rel = p.relative_to(root / "wiki")
        if rel.parts[0] not in SKIP_DIRS and rel.name not in SKIP_FILES:
            out.append(p)
    return out


def quotes(root, pages=None) -> list:
    root = pathlib.Path(root).resolve()
    return [q for p in _pages(root, pages) if p.is_file() for q in _page_quotes(root, p)]


# ---------------------------------------------------------------- reading sources


INLINE_TAGS = re.compile(r"</?(?:a|b|i|em|strong|span|mark|u|small|abbr|code)\b[^>]*>", re.I)


def _strip_markup(s: str) -> str:
    """HTML to text. Inline tags join, block tags separate: "<b>reach</b>able" is one word."""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>|<!--.*?-->", " ", s)
    s = INLINE_TAGS.sub("", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def _office_text(xml: str, para: str) -> str:
    """Word and PowerPoint XML to text. They split one word across runs ("Pay" + "ment"), so
    every tag but a paragraph, tab or line break joins rather than separates."""
    xml = xml.replace(para, "\n")
    xml = re.sub(r"<(?:w:tab|w:br|a:br)\b[^>]*>", " ", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def _zip_xml(path: pathlib.Path, members: str, para: str) -> str:
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if re.fullmatch(members, n))
        return "\n".join(_office_text(z.read(n).decode("utf-8", "replace"), para) for n in names)


def _cache(root: pathlib.Path) -> pathlib.Path:
    """The folder for PDF text. It ignores itself, so no wiki can commit it by accident."""
    folder = root / CACHE
    folder.mkdir(parents=True, exist_ok=True)
    marker = root / ".cache" / ".gitignore"
    if not marker.exists():
        marker.write_text("*\n", encoding="utf-8")
    return folder


def _pdf(root: pathlib.Path, path: pathlib.Path):
    if not PDFTOTEXT:
        return None, "can't read PDFs here (pdftotext is not installed)"
    st = path.stat()
    key = hashlib.sha256(f"{path.relative_to(root)}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:20]
    cached = _cache(root) / f"{key}.txt"
    if cached.is_file():
        text = cached.read_text(encoding="utf-8")
    else:
        try:
            run = subprocess.run([PDFTOTEXT, "-q", "-enc", "UTF-8", str(path), "-"],
                                 capture_output=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            return None, f"can't read this PDF ({type(e).__name__})"
        if run.returncode != 0:
            return None, "pdftotext could not read this PDF"
        text = run.stdout.decode("utf-8", "replace")
        part = cached.with_suffix(".part")                # never trust half a copy
        part.write_text(text, encoding="utf-8")
        os.replace(part, cached)
    if len(text.split(None, 20)) < 20:
        return None, "the PDF has no text layer (probably a scan)"
    return text, ""


def by_name(root: pathlib.Path) -> dict:
    """Every file under raw/ by its name alone, as check_sources.py resolves a bare citation."""
    index = {}
    for f in sorted((root / "raw").resolve().rglob("*")):
        if f.is_file():
            index.setdefault(f.name, f.resolve())        # a link is judged by where it points
    return index


def source_text(root: pathlib.Path, rel: str, names: dict | None = None):
    """(text, "") or (None, why not). `names` is by_name(root), passed in to build it once a run."""
    raw = (root / "raw").resolve()
    path = (root / rel).resolve()
    if raw not in path.parents:
        return None, "not a file in raw/"
    if not path.is_file():
        path = (names if names is not None else by_name(root)).get(path.name)
        if path is None:
            return None, "not on this machine"
        if raw not in path.parents:
            return None, "not a file in raw/"
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            return _pdf(root, path)
        if ext in TEXT_TYPES:
            return path.read_text(encoding="utf-8", errors="replace"), ""
        if ext in MARKUP_TYPES:
            return _strip_markup(path.read_text(encoding="utf-8", errors="replace")), ""
        if ext == ".docx":
            return _zip_xml(path, r"word/(?:document|footnotes|endnotes|comments)\.xml", "</w:p>"), ""
        if ext == ".pptx":
            # Slides and their speaker notes: a deck's caveats usually live in the notes.
            return _zip_xml(path, r"ppt/(?:slides/slide|notesSlides/notesSlide)\d+\.xml", "</a:p>"), ""
    except (zipfile.BadZipFile, KeyError, OSError) as e:
        return None, f"can't read this file ({type(e).__name__})"
    return None, f"can't read {ext or 'this kind of'} files here"


# ---------------------------------------------------------------- matching


def _parts(q: str) -> list:
    """The quote's runs of words as (words, how far after the previous run it may start).
    An ellipsis may stand for a passage; a bracketed change, for a word or a short phrase."""
    out, pending = [], 0
    for i, chunk in enumerate(ELLIPSIS.split(q)):
        if i:
            pending += GAP_CHARS
        for j, piece in enumerate(BRACKETED.split(chunk)):
            if j:
                pending += BRACKET_CHARS
            ws = " ".join(words(piece))
            if ws:
                out.append((ws, pending))
                pending = 0
    return out


def _exact(q: str, joined: str) -> bool:
    """Every part of the quote in the source, in order, each within its allowed gap of the last."""
    parts = _parts(q)
    if not parts:
        return False
    first, at, tries = f" {parts[0][0]} ", joined.find(f" {parts[0][0]} "), 0
    while at != -1 and tries < 2000:
        end, ok = at + len(first) - 1, True
        for part, gap in parts[1:]:
            nxt = joined.find(f" {part} ", end)
            if nxt == -1 or nxt - end > gap:
                ok = False
                break
            end = nxt + len(part) + 1
        if ok:
            return True
        at, tries = joined.find(first, at + 1), tries + 1
    return False


def _spread(xs: list, n: int) -> list:
    """At most n of xs, taken evenly from start to end, so the end of a long source is seen."""
    return xs if len(xs) <= n else xs[::-(-len(xs) // n)]


def _passage(clean: str, starts, i0: int, i1: int) -> str:
    i0, i1 = max(0, i0 - 2), min(len(starts) - 1, i1 + 2)
    end = TOKEN.match(clean, starts[i1])
    text = " ".join(clean[starts[i0]:end.end() if end else starts[i1]].split())
    return text if len(text) <= 320 else text[:317] + "..."


class _Source:
    """One source's words, with what a near-match search needs built only when first asked."""

    def __init__(self, text: str):
        self.clean, self.starts, self.ws = _tokens(text)
        self.joined = f" {' '.join(self.ws)} "
        self._offsets = self._counts = None

    def word_at(self, char: int) -> int:
        if self._offsets is None:
            self._offsets, pos = array("l"), 1
            for w in self.ws:
                self._offsets.append(pos)
                pos += len(w) + 1
        return bisect.bisect_left(self._offsets, char)

    def count(self, w: str) -> int:
        if self._counts is None:
            self._counts = Counter(self.ws)
        return self._counts[w]

    def find_all(self, needle: str, limit: int) -> list:
        out, at = [], self.joined.find(needle)
        while at != -1 and len(out) < limit * 20:
            out.append(at)
            at = self.joined.find(needle, at + 1)
        return _spread(out, limit)


def _anchors(qw: list, src: _Source) -> list:
    """Where a near match could start: every adjacent word pair of the quote found in the source,
    and the quote's rarest words, each spread across the whole source rather than its first pages."""
    out = set()
    for j in range(len(qw) - 1):
        for at in src.find_all(f" {qw[j]} {qw[j + 1]} ", PER_ANCHOR):
            out.add((src.word_at(at + 1), j))
    rare = sorted({w for w in qw if src.count(w)}, key=src.count)[:3]
    for w in rare:
        for at in src.find_all(f" {w} ", PER_ANCHOR):
            out.add((src.word_at(at + 1), qw.index(w)))
    return _spread(sorted(out), MAX_ANCHORS)


def _nearest(qw: list, src: _Source):
    """The passage most alike the quote: (share of the quote's words found in order, passage)."""
    best, span = 0.0, None
    for p, i in _anchors(qw, src):
        lo = max(0, p - i - 2)
        window = src.ws[lo:lo + len(qw) + 4]
        blocks = [b for b in SequenceMatcher(None, qw, window, autojunk=False).get_matching_blocks() if b.size]
        score = sum(b.size for b in blocks) / len(qw)
        if blocks and score > best:
            best, span = score, (lo + blocks[0].b, lo + blocks[-1].b + blocks[-1].size - 1)
    return best, (_passage(src.clean, src.starts, *span) if span else "")


def _check_source(qs: list, text: str) -> dict:
    """{index in qs: (verdict, alike, passage)} for one readable source."""
    src = _Source(text)
    out = {}
    for k, q in enumerate(qs):
        if _exact(q.quote, src.joined):
            out[k] = ("found", 1.0, "")
            continue
        qw = " ".join(w for w, _ in _parts(q.quote)).split()
        score, passage = _nearest(qw, src) if qw else (0.0, "")
        verdict = "close" if score >= CLOSE else "not-found"
        out[k] = (verdict, round(score, 2), passage if score >= SHOW else "")
    return out


RANK = {"found": 3, "close": 2, "not-found": 1}


def _combine(q: Quote, outcomes: list) -> Result:
    """Best verdict across the quote's sources; unreadable ones only explain an unchecked quote."""
    readable = [o for o in outcomes if o[1] in RANK]
    if not readable:
        reasons = "; ".join(f"{src}: {why}" for src, _, why, *_ in outcomes)
        return Result(**asdict(q), verdict="unchecked", reason=reasons)
    src, verdict, _, alike, passage = max(readable, key=lambda o: (RANK[o[1]], o[3]))
    return Result(**asdict(q), verdict=verdict, source=src, alike=alike, passage=passage)


def run(root=None, pages=None) -> list:
    root = pathlib.Path(root or ROOT).resolve()     # macOS reaches /var as /private/var too
    qs = quotes(root, pages)
    by_source = {}
    for k, q in enumerate(qs):
        for s in q.sources:
            by_source.setdefault(s, []).append(k)
    outcomes = {k: [] for k in range(len(qs))}
    names = by_name(root)
    for src, ks in by_source.items():
        text, why = source_text(root, src, names)
        if text is not None and not TOKEN.search(text):
            text, why = None, "the file has no text"
        if text is None:
            for k in ks:
                outcomes[k].append((src, "unchecked", why, 0.0, ""))
            continue
        for j, (verdict, alike, passage) in _check_source([qs[k] for k in ks], text).items():
            outcomes[ks[j]].append((src, verdict, "", alike, passage))
    return [_combine(q, outcomes[k]) for k, q in enumerate(qs)]


# ---------------------------------------------------------------- report


def _short(s: str, n: int = 200) -> str:
    return s if len(s) <= n else s[:n - 3] + "..."


def _listing(title: str, rows: list, limit: int):
    if not rows:
        return
    print(f"\n{title} ({len(rows)}{', first ' + str(limit) if len(rows) > limit else ''}):")
    for r in rows[:limit]:
        print(f"\n  {r.page}:{r.line}")
        print(f"    quote:   \"{_short(r.quote)}\"")
        print(f"    cites:   {r.source or ', '.join(r.sources)}")
        if r.passage:
            print(f"    source:  \"{r.passage}\"   ({round(r.alike * 100)}% alike)")


def report(results: list, limit: int):
    n = Counter(r.verdict for r in results)
    pages = len({r.page for r in results})
    print(f"Quote check: {len(results)} quoted passages sit beside a citation, on {pages} pages.\n")
    print(f"  found word for word in the source   {n['found']:>5}")
    print(f"  worded differently from the source  {n['close']:>5}")
    print(f"  not in the cited source             {n['not-found']:>5}")
    print(f"  could not check on this machine     {n['unchecked']:>5}")
    why = Counter(r.reason.split("; ")[0].rsplit(": ", 1)[-1] for r in results if r.verdict == "unchecked")
    for reason, count in why.most_common():
        print(f"      {count:>5}  {reason}")
    checked = len(results) - n["unchecked"]
    if checked:
        print(f"\n  Of the {checked} this machine could check, {round(100 * n['found'] / checked)}% are word for word.")
    _listing("Not in the cited source, read these first", [r for r in results if r.verdict == "not-found"], limit)
    close = sorted((r for r in results if r.verdict == "close"), key=lambda r: r.alike)
    _listing("Worded differently, a paraphrase or a misquote", close, limit)
    print("\nNothing here is a verification. A person reads the passage and decides; see verification.py.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Is each quoted passage in the source it cites?")
    ap.add_argument("pages", nargs="*", help="pages to check (default: the whole wiki)")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--check", action="store_true", help="exit 1 if a quote is not in its cited source")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=20, help="rows to list in each section")
    args = ap.parse_args(argv)
    results = run(args.root, args.pages or None)
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=1, ensure_ascii=False))
    else:
        report(results, args.limit)
    return 1 if args.check and any(r.verdict == "not-found" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
