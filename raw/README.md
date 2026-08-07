# raw/ — your source documents

Put source files here: PDFs, articles, notes, data, images. This folder is the
**source of truth** and is treated as **read-only** by Claude — it reads from these
files but never edits or deletes them.

- Drag files in through GitHub's web interface, or ask for help the first time.
- Images can go in `raw/assets/`.
- After adding a file, tell Claude: "ingest the new document in raw."

The `EXAMPLE-sample-source.md` file is a demo — delete it once you've added real sources.

Note: by default the `.gitignore` keeps auto-generated `.md` conversions of PDFs out of
version control (so this folder stays your originals). The example file is exempted so
the demo works.
