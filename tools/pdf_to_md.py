#!/usr/bin/env python3
"""
pdf_to_md.py — convert a PDF in raw/ into readable markdown for ingestion.

When the owner adds a PDF, Claude can run this to get clean markdown text to read and
summarise, rather than wrestling with the raw binary. The converted markdown is
written next to the source with a .md extension so the original PDF stays untouched
(raw/ is immutable — this only ADDS a companion file, it never edits the PDF).

Usage (Claude shells out to this):
    python tools/pdf_to_md.py raw/some-report.pdf
    # writes raw/some-report.md

Tries pymupdf4llm first (best markdown structure), falls back to pypdf if unavailable.
If neither is installed, prints the pip install command to run.
"""

import sys
from pathlib import Path


def convert(pdf_path: Path) -> str:
    # Preferred: pymupdf4llm produces well-structured markdown
    try:
        import pymupdf4llm
        return pymupdf4llm.to_markdown(str(pdf_path))
    except ImportError:
        pass

    # Fallback: pypdf plain text extraction
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    except ImportError:
        print(
            "Neither pymupdf4llm nor pypdf is installed. Install one with:\n"
            "  pip install pymupdf4llm --break-system-packages\n"
            "or\n"
            "  pip install pypdf --break-system-packages",
            file=sys.stderr,
        )
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: python tools/pdf_to_md.py raw/<file>.pdf", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print(f"Not a PDF: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    md = convert(pdf_path)
    out = pdf_path.with_suffix(".md")
    out.write_text(md, encoding="utf-8")
    print(f"Wrote {out} ({len(md):,} chars). The original PDF is unchanged.")


if __name__ == "__main__":
    main()
