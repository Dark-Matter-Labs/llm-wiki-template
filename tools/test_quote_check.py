#!/usr/bin/env python3
"""
test_quote_check.py — a quote beside a citation is found in that source, and the checker says
plainly when it cannot look.

The quiet cases matter as much as the loud ones. A quote that differs from its source only in
curly quotes, a ligature or a line-break hyphen is the same quote, and calling it a misquote
would bury the real ones. Special characters are written as escapes on purpose.

  python3 tools/test_quote_check.py

house-rules: ignore-file (it matches a source's British spelling of civilization on purpose)
"""

import io
import os
import pathlib
import random
import sys
import subprocess
import tempfile
import zipfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quote_check  # noqa: E402

FAILED = []
FM = "---\ntype: summary\ntitle: {title}\nvisibility: private\n---\n\n"


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  \u2014 {detail}" if not cond and detail else ""))
    if not cond:
        FAILED.append(label)


def write(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return p


def snapshot(root):
    base = pathlib.Path(root)
    return {str(p): p.read_bytes() for d in ("wiki", "raw") for p in sorted((base / d).rglob("*")) if p.is_file()}


def page(root, slug, body, title="T"):
    return write(root, f"wiki/{slug}.md", FM.format(title=title) + body)


def docx_runs(paragraphs):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        xml = "".join("<w:p>" + "".join(f"<w:r><w:t>{r}</w:t></w:r>" for r in runs) + "</w:p>"
                      for runs in paragraphs)
        z.writestr("word/document.xml", f"<w:document><w:body>{xml}</w:body></w:document>")
    return buf.getvalue()


def docx(paragraphs):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        xml = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in paragraphs)
        z.writestr("word/document.xml", f'<w:document><w:body>{xml}</w:body></w:document>')
    return buf.getvalue()


def by_quote(results, start):
    return next(r for r in results if r.quote.startswith(start))


def test_normalising():
    n = quote_check.words
    check("curly and straight quotes, case and punctuation do not matter",
          n("The \u201cwide\u201d Field, it said.") == n('the "wide" field it said'))
    check("a ligature is the letters it stands for", n("\ufb01nance \ufb02ow") == n("finance flow"))
    check("a soft hyphen is invisible to the match", n("consti\u00adtutive") == n("constitutive"))
    check("a word hyphenated across a line break in a PDF is one word",
          n("is consti-\ntutive here") == n("is constitutive here"))
    check("markdown emphasis is not part of the words", n("*not* a _forecast_") == n("not a forecast"))
    check("British and American spellings are the same word",
          n("substrate stabilisation, prioritising behaviours") == n("substrate stabilization, prioritizing behaviors"))
    check("and their longer forms", n("behavioural, favourable, analysed") == n("behavioral, favorable, analyzed"))
    check("short words are left alone: four is not for, rise is not rize", n("four rise") != n("for rize"))
    check("a spoken uh or um is not a word of the quote", n("which are not uh again targetable") == n("which are not again targetable"))
    check("a dash between words is a gap, not a letter", n("open\u2014and closed") == n("open and closed"))


def test_finding_quotes(root):
    page(root, "a", 'Intro line.\n\nThe paper says "machines make institutional opening nearly\nfree" '
                    "and moves on (raw/s.md).\n\n"
                    'Too short to check: "nearly free" (raw/s.md).\n\n'
                    'No citation here: "this is quoted but nothing is cited".\n\n'
                    "> Administrative technology is constitutive, not instrumental.\n"
                    "> (raw/s.md)\n\n"
                    'The source (raw/s.md) puts it as "a working architecture, not a finished programme".\n\n'
                    '> **Provenance.** A paper brought in on 20 August, which calls itself "a working\n'
                    '> architecture, not a forecast" in its opening line (raw/s.md).\n')
    write(root, "wiki/log/2026-10-01.md", 'Log: "this quote is in a log file entry" (raw/s.md).\n')
    got = quote_check.quotes(root)
    texts = [q.quote for q in got]
    check("a quote wrapped across a line is one quote",
          "machines make institutional opening nearly free" in texts, str(texts))
    check("a quote under five words is not checked", "nearly free" not in texts)
    check("a quote with no citation in its paragraph is not checked",
          not any("nothing is cited" in t for t in texts))
    check("a blockquote with a citation is checked as a whole",
          "Administrative technology is constitutive, not instrumental." in texts, str(texts))
    check("a quote after its citation is paired with that citation",
          any(t.startswith("a working architecture") for t in texts))
    check("log pages are not checked", not any("log file" in t for t in texts))
    check("a call-out box that opens with a bold label is a note, not a quotation",
          not any(t.startswith("**Provenance") or t.startswith("Provenance") for t in texts), str(texts))
    check("a quote inside a call-out box is still checked",
          "a working architecture, not a forecast" in texts, str(texts))
    q = next(q for q in got if q.quote.startswith("machines"))
    check("a quote knows its page and line", (q.page, q.line) == ("wiki/a.md", 9), f"{q.page}:{q.line}")
    check("a quote knows its cited source", q.sources == ["raw/s.md"], str(q.sources))


def test_citation_groups():
    s = quote_check.sources_in
    check("one source", s("raw/a.md") == ["raw/a.md"])
    check("a locator after the file is dropped", s("raw/a.pdf, \u00a73.2") == ["raw/a.pdf"])
    check("two sources separated by a semicolon", s("raw/a.md; raw/b.pdf") == ["raw/a.md", "raw/b.pdf"])
    check("a filename with brackets survives", s("raw/Report (WIP).pdf p. 4") == ["raw/Report (WIP).pdf"])
    check("a filename broken across a line is joined", s("raw/Large-Scale\nOrganizing.pdf") == ["raw/Large-Scale Organizing.pdf"])


def test_checking(root):
    write(root, "raw/s.md", "Machines make institutional opening nearly free, while closure stays dear.\n"
                            "Administrative technology is constitutive, not instrumental.\n"
                            "This is a working architecture, not a finished programme and not a forecast.\n")
    write(root, "raw/p.html", "<html><style>.x{}</style><body><p>The open and <b>reachable</b> range "
                              "of futures that remain&nbsp;possible.</p><script>var a='x';</script></body></html>")
    write(root, "raw/w.docx", docx(["Payment is released only on verified outcomes, never before."]))
    write(root, "raw/sheet.xlsx", b"not really a spreadsheet")
    page(root, "b",
         '"Machines make institutional opening nearly free" (raw/s.md).\n\n'
         '"Machines make institutional openings almost free" (raw/s.md).\n\n'
         '"Every claim in this wiki has been read by a person" (raw/s.md).\n\n'
         '"The open and reachable range of futures" (raw/p.html).\n\n'
         '"Payment is released only on verified outcomes" (raw/w.docx).\n\n'
         '"a working architecture \u2026 not a forecast" (raw/s.md).\n\n'
         '"the shared telos of a living field" (raw/gone.pdf).\n\n'
         '"what the table in the sheet says here" (raw/sheet.xlsx).\n\n'
         '"Administrative technology is constitutive, not instrumental" (raw/gone.md; raw/s.md).\n')
    got = quote_check.run(root)
    v = {r.quote: r.verdict for r in got}
    check("an exact quote is found", v["Machines make institutional opening nearly free"] == "found", str(v))
    close = by_quote(got, "Machines make institutional openings")
    check("a slightly reworded quote is close, not found", close.verdict == "close", close.verdict)
    check("a close quote shows what the source actually says",
          "institutional opening nearly free" in close.passage, close.passage)
    miss = by_quote(got, "Every claim")
    check("a quote the source does not contain is not found", miss.verdict == "not-found", miss.verdict)
    check("a quote is found in an HTML source, with tags and scripts stripped",
          by_quote(got, "The open and reachable").verdict == "found", str(v))
    check("a quote is found in a Word document", by_quote(got, "Payment is released").verdict == "found", str(v))
    check("each part of a quote with an ellipsis is found", by_quote(got, "a working architecture").verdict == "found", str(v))
    gone = by_quote(got, "the shared telos")
    check("a source not on this machine is not checked, and says so",
          gone.verdict == "unchecked" and "not on this machine" in gone.reason, f"{gone.verdict} {gone.reason}")
    sheet = by_quote(got, "what the table")
    check("a file type this tool cannot read is not checked, and says so",
          sheet.verdict == "unchecked" and "can't read" in sheet.reason, f"{sheet.verdict} {sheet.reason}")
    check("with two sources, a quote found in either is found",
          by_quote(got, "Administrative").verdict == "found")
    write(root, "raw/papers/deep.md", "A paper filed in a folder of its own, cited by name alone.")
    page(root, "bare", '"filed in a folder of its own" (raw/deep.md).\n')
    bare = quote_check.run(root, pages=["wiki/bare.md"])[0]
    check("a source cited by its name alone is found in the folder it sits in",
          bare.verdict == "found" and bare.source == "raw/deep.md", f"{bare.verdict} {bare.reason}")
    write(root, "secret.md", "a file outside the sources folder entirely")
    page(root, "escape", '"a file outside the sources folder entirely" (raw/../secret.md).\n')
    out = quote_check.run(root, pages=["wiki/escape.md"])[0]
    check("a citation that climbs out of raw/ is never read",
          out.verdict == "unchecked" and "not a file in raw/" in out.reason, f"{out.verdict} {out.reason}")


def test_review_findings(root):
    """Found by a second reader on 2026-10-01; each was reproduced before it was fixed."""
    write(root, "raw/s.md", "Machines make institutional opening nearly free, while closure stays dear.\n")
    page(root, "inside", 'See (raw/s.md, "machines make institutional opening nearly free") for this.\n')
    try:
        got = quote_check.run(root, pages=["wiki/inside.md"])
        check("a quote inside its own citation does not crash the run", True)
        check("a quote inside its own citation is paired with that citation",
              [r.verdict for r in got] == ["found"], str([(r.quote, r.verdict) for r in got]))
    except IndexError as e:
        check("a quote inside its own citation does not crash the run", False, repr(e))

    probe = ("import sys; sys.path.insert(0, %r); import quote_check; "
             "quote_check.CITE.search('x (raw/' + 'a' * 40)" % os.path.dirname(os.path.abspath(__file__)))
    try:
        subprocess.run([sys.executable, "-c", probe], timeout=5, check=True)
        hung = False
    except subprocess.TimeoutExpired:
        hung = True
    check("an unclosed citation cannot hang the run", not hung)

    write(root, "raw/runs.docx", docx_runs([["Pay", "ment is released only on verified outcomes."]]))
    page(root, "runs", '"Payment is released only on verified outcomes" (raw/runs.docx).\n')
    r = quote_check.run(root, pages=["wiki/runs.md"])[0]
    check("a word Word split across two runs is still one word", r.verdict == "found", f"{r.verdict} {r.passage}")

    write(root, "raw/empty.md", "")
    page(root, "empty", '"anything at all from an empty file" (raw/empty.md).\n')
    r = quote_check.run(root, pages=["wiki/empty.md"])[0]
    check("a source with no words is not checked, rather than a misquote",
          r.verdict == "unchecked" and "no text" in r.reason, f"{r.verdict} {r.reason}")

    page(root, "brackets", '"[M]achines make institutional opening nearly free" (raw/s.md).\n\n'
                           '"Machines make [the] opening nearly free, while closure stays dear" (raw/s.md).\n')
    rs = quote_check.run(root, pages=["wiki/brackets.md"])
    check("a capital letter changed in brackets is the same quote", rs[0].verdict == "found", rs[0].verdict)
    check("words supplied in brackets stand for the source's own", rs[1].verdict == "found", rs[1].verdict)
    write(root, "raw/brit.md", "A civilisation that cannot institutionalise doubt should not silently migrate "
                               "costs to workers. Look for high-legitimacy systems first.\n")
    page(root, "house", '"A civilization that cannot institutionalise doubt" (raw/brit.md).\n\n'
                        '"should not silently migrate[s] costs to workers" (raw/brit.md).\n\n'
                        '"look[ing] for high-legitimacy systems first" (raw/brit.md).\n\n'
                        '"should not silently [...] to workers" (raw/brit.md).\n')
    rs = quote_check.run(root, pages=["wiki/house.md"])
    check("civilization with a z, the house rule, quotes a source's civilisation",
          rs[0].verdict == "found", rs[0].verdict)
    check("letters added in brackets stand for the source's word", rs[1].verdict == "found", rs[1].verdict)
    check("a word's ending changed in brackets is the same quote", rs[2].verdict == "found", rs[2].verdict)
    check("an ellipsis in brackets is an ellipsis", rs[3].verdict == "found", rs[3].verdict)
    check("a bracket stands for a few words, not a page of them",
          not quote_check._exact("Machines make [x] stays dear", " machines make " + "other words " * 30
                                 + "stays dear "))
    write(root, "raw/label.html", '<p class="hero-state">[ ATLAS / EXPLANATION / CAPITAL REVISION / NON-OPERATIVE ]</p>')
    page(root, "label", '"[ ATLAS / EXPLANATION / CAPITAL REVISION / NON-OPERATIVE ]" (raw/label.html).\n')
    r = quote_check.run(root, pages=["wiki/label.md"])[0]
    check("a quote that is all one bracketed label is read literally", r.verdict == "found", r.verdict)
    write(root, "raw/labels.html", '<td><span class="k">Settlement</span>Parliament authorises the body each year.</td>'
                                   '<p>Its <b>reach</b>able range of futures stays open here.</p>')
    page(root, "labels", '"Parliament authorises the body each year" (raw/labels.html).\n\n'
                         '"Its reachable range of futures stays open" (raw/labels.html).\n')
    rs = quote_check.run(root, pages=["wiki/labels.md"])
    check("a word after a label set in its own tag is still the first word", rs[0].verdict == "found", rs[0].verdict)
    check("a word split by a formatting tag is still one word", rs[1].verdict == "found", rs[1].verdict)
    write(root, "raw/locator.md", "The danger is compensated degradation: continuity purchased by consuming the capacity.\n")
    page(root, "locator", '> "The danger is compensated degradation: continuity purchased by consuming the\n'
                          '> capacity." \u00a705 (raw/locator.md)\n')
    rs = quote_check.run(root, pages=["wiki/locator.md"])
    check("a quoted block followed by its section number is the quote alone",
          [r.verdict for r in rs] == ["found"], str([(r.quote, r.verdict) for r in rs]))
    check("a quote with no words outside brackets and ellipses is never found",
          not quote_check._exact("[...] \u2026", " machines make "))

    page(root, "order", '"nearly free, while closure \u2026 machines make institutional" (raw/s.md).\n')
    r = quote_check.run(root, pages=["wiki/order.md"])[0]
    check("the parts of a quote with an ellipsis must come in the source's order", r.verdict != "found", r.verdict)

    rng = random.Random(1)
    vocab = [f"w{i}" for i in range(150)]                 # every word occurs ~600 times
    filler = " ".join(rng.choice(vocab) for _ in range(90000))
    write(root, "raw/big.md", filler + " w3 w14 w15 w92 w65 w35 w89 w79.\n")
    page(root, "big", '"w3 w14 w15 w92 omega w35 w89 w79" (raw/big.md).\n')
    r = quote_check.run(root, pages=["wiki/big.md"])[0]
    check("a near match at the end of a large source is still found, as close",
          r.verdict == "close" and r.alike >= 0.85 and "w92 w65 w35" in r.passage, f"{r.verdict} {r.alike} {r.passage}")

    outside = write(root, "outside.md", "Text outside the sources folder, reached through a link.")
    link = pathlib.Path(root) / "raw" / "link.md"
    link.symlink_to(outside)
    page(root, "link", '"outside the sources folder, reached through a link" (raw/other/link.md).\n')
    r = quote_check.run(root, pages=["wiki/link.md"])[0]
    check("a link inside raw/ to a file outside it is never read",
          r.verdict == "unchecked", f"{r.verdict} {r.reason}")


def test_pdf_without_reader(root):
    write(root, "raw/doc.pdf", b"%PDF-1.4 not a real pdf")
    page(root, "c", '"this sentence would be in the pdf" (raw/doc.pdf).\n')
    saved = quote_check.PDFTOTEXT
    quote_check.PDFTOTEXT = None
    try:
        r = quote_check.run(root, pages=["wiki/c.md"])[0]
    finally:
        quote_check.PDFTOTEXT = saved
    check("without a PDF reader, a PDF is not checked, and the reason names the missing reader",
          r.verdict == "unchecked" and "PDF" in r.reason, f"{r.verdict} {r.reason}")


def test_pdf_with_reader(root):
    fake = write(root, "bin/pdftotext", "#!/bin/sh\necho 'The open and reachable range of futures that remain "
                 "without crossing irreversible thresholds is what the paper calls optionality, and it says so "
                 "plainly on its first page.'\n")
    fake.chmod(0o755)
    write(root, "raw/real.pdf", b"%PDF-1.4 stand-in")
    page(root, "d", '"remain without crossing irreversible thresholds" (raw/real.pdf).\n')
    saved = quote_check.PDFTOTEXT
    quote_check.PDFTOTEXT = str(fake)
    try:
        first = quote_check.run(root, pages=["wiki/d.md"])[0]
        fake.unlink()
        again = quote_check.run(root, pages=["wiki/d.md"])[0]
    finally:
        quote_check.PDFTOTEXT = saved
    cache = pathlib.Path(root) / quote_check.CACHE
    check("a quote is found in a PDF's text", first.verdict == "found", f"{first.verdict} {first.reason}")
    check("the PDF's text is kept, so the next run needs no reader", again.verdict == "found", again.reason)
    check("the text copies hide themselves from git in any wiki",
          (pathlib.Path(root) / ".cache" / ".gitignore").read_text().strip() == "*")
    check("the text copy is the only thing written", sorted(x.suffix for x in cache.iterdir()) == [".txt"])
    broken = write(root, "bin/broken", "#!/bin/sh\necho 'half a page of text that stops' ; exit 1\n")
    broken.chmod(0o755)
    write(root, "raw/bad.pdf", b"%PDF-1.4 another stand-in")
    page(root, "e", '"half a page of text that stops" (raw/bad.pdf).\n')
    quote_check.PDFTOTEXT = str(broken)
    try:
        r = quote_check.run(root, pages=["wiki/e.md"])[0]
    finally:
        quote_check.PDFTOTEXT = saved
    check("when the PDF reader fails, nothing is kept and the quote is not checked",
          r.verdict == "unchecked" and len(list(cache.iterdir())) == 1, f"{r.verdict} {r.reason}")


def test_main(root):
    page(root, "good", '"Machines make institutional opening nearly free" (raw/s.md).\n')
    page(root, "bad", '"Every claim in this wiki has been read by a person" (raw/s.md).\n')
    before = snapshot(root)
    out = io.StringIO()
    with redirect_stdout(out):
        ok = quote_check.main(["--root", root, "--check", "wiki/good.md"])
        bad = quote_check.main(["--root", root, "--check", "wiki/bad.md"])
        report = quote_check.main(["--root", root])
    check("--check passes when every quote on the named pages is found", ok == 0)
    check("--check fails when a quote on a named page is not in its source", bad == 1)
    check("the whole-wiki report never fails", report == 0)
    text = out.getvalue()
    check("the report names the misquote with its page and line", "wiki/bad.md:7" in text, text[-600:])
    check("a run changes nothing in the wiki or its sources", before == snapshot(root))


def main():
    print("quote_check \u2014 is a quoted passage really in the source it cites?\n")
    test_normalising()
    test_citation_groups()
    with tempfile.TemporaryDirectory() as d:
        test_finding_quotes(d)
    with tempfile.TemporaryDirectory() as d:
        test_review_findings(d)
    with tempfile.TemporaryDirectory() as d:
        test_checking(d)
        test_pdf_without_reader(d)
        test_pdf_with_reader(d)
        test_main(d)
    print()
    if FAILED:
        print(f"{len(FAILED)} FAILED")
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
