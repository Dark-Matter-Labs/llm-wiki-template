---
name: publish-web
description: Turn a wiki page (or a synthesis/overview/curated topic) into a styled, standalone, shareable HTML web page under docs/, served by GitHub Pages. Use when the owner says "publish this as a web page", "make a shareable link for…", "put this on the site", "turn this into a webpage", or wants wiki content sent to people as a URL. Applies the shared design system in docs/assets/.
---

# Publish a wiki page to the web

The owner wants to share wiki content as web links. Published pages live in `docs/` and are
served by **GitHub Pages** at `https://YOUR-ORG.github.io/YOUR-WIKI/<name>.html`.
Each page is a self-contained, styled, responsive HTML file that anyone can open.

**Publishing is a higher bar than the wiki.** These pages leave the building. Before
publishing anything substantive, run the `publish-check` skill first (or fold its checks in):
verify sourcing, flag unsupported claims, and confirm the owner actually wants it public.

## How it works (architecture)

- `docs/` is the GitHub Pages root (served from the `main` branch, `/docs` folder).
- `docs/assets/xco.css` is the **shared stylesheet** — the xCO design system. Every page links it
  with `<link rel="stylesheet" href="assets/xco.css">`. Do not fork per-page CSS; extend the
  shared sheet if a genuinely new component is needed.
- `docs/index.html` is a **deliberately minimal, `noindex` landing page** — basic info only. It is
  **NOT a directory**: it must never list, link to, or catalogue the published pages. The owner's policy is
  that pages are reachable **only by the direct link they share**, not by browsing from the root. Do not
  add cards or links to it when you publish; leave it minimal.
- `docs/.nojekyll` tells Pages to serve files as-is (no Jekyll).
- **Branding is set once, in this skill.** The template ships with a neutral placeholder.
  Replace `YOUR ORGANISATION` and the eyebrow line below with the real organisation and
  section names the first time you publish, then leave them alone so every page matches.

## Steps

1. **Pick the source & confirm intent.** Identify the wiki page(s) to publish. Confirm with the owner
   that it should be public. Run `publish-check`-style checks on the content.
2. **Choose a filename** — short, kebab-case, stable: `docs/<slug>.html`. This IS the shareable
   URL, so don't churn it later.
3. **Write the HTML** following the template and rules below. Translate the markdown into the
   section structure — don't just dump the raw markdown.
4. **Do NOT touch `docs/index.html`.** The root index stays a minimal, page-less landing (see the
   design-system note below). A newly published page is shared by its direct link — never catalogued.
5. **Preview it.** Start the `docs-preview` server (see `.claude/launch.json`) and screenshot to
   confirm it renders on-brand and is responsive; check for broken internal links.
6. **Ship.** Commit to a branch, push, open/update a PR. Once merged (and Pages enabled) the link
   is live. Report the exact URL to the owner in plain language.
7. **Log it.** Append `## [YYYY-MM-DD] publish | <page title> → <url>` to the current month's log file (`wiki/log/YYYY-MM.md`; see `wiki/log.md`).

## HTML template (structure)

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>… — YOUR ORGANISATION</title>
  <meta name="description" content="…one sentence…">
  <link rel="stylesheet" href="assets/xco.css">
</head>
<body>
  <div class="top-rule"></div>
  <div class="page-shell">
    <header class="hero hero-single">
      <div class="hero-copy">
        <p class="eyebrow">YOUR ORGANISATION · <Section> · <Type></p>
        <h1>…a real sentence, not the filename…</h1>
        <p class="subtitle">…the page description…</p>
      </div>
    </header>
    <section class="document-meta">
      <div><span class="label">Type</span><span class="value">…</span></div>
      <div><span class="label">Confidence</span><span class="value">…</span></div>
      <div><span class="label">Updated</span><span class="value">…</span></div>
    </section>
    <main>
      <section class="section">
        <div class="section-label">…short mono kicker…</div>
        <div class="section-content">…content…</div>
      </section>
      <!-- repeat .section per major heading -->
    </main>
    <footer class="footer">…provenance + nav…</footer>
  </div>
</body>
</html>
```

## Design system — the class vocabulary (all defined in `assets/xco.css`)

- **Palette:** `--shadow #192640` (navy, text/structure), `--midtone #F27F3D` (orange, accent only),
  `--highlight #FFFFFF` (paper). Never introduce new colours.
- **Type:** body Crimson Pro serif; headings Inter; labels/eyebrows/captions DM Mono. Fonts load
  from Google Fonts inside the CSS.
- **Spacing** is Fibonacci: 13 / 21 / 34 / 55 / 89 px (`--s1`…`--s5`). Layout uses a golden-ratio grid.
- **Building blocks:** `.hero` / `.hero-single`, `.eyebrow`, `.subtitle`, `.document-meta`,
  `.section` + `.section-label` (sticky mono kicker) + `.section-content`, `.lead`, `.quote-block`,
  `.aside-grid` + `.card` (`.accent-card`, `.dark-card`), `.card-link` (clickable card),
  `.table-wrap` + `table`, `.caption`, `.footer`, `.small`.

## Content rules

- **Rewrite, don't dump.** Turn each top-level heading into a `.section`; lead with a `.lead` or
  `.quote-block` where there's a strong line; use `.aside-grid`/`.card` for lists of parallel items;
  use `.table-wrap`/`table` for matrices.
- **Wiki `[[links]]`:** only make a real `<a>` link if the target is *also published* in `docs/`.
  Otherwise render the concept as `<span class="term">name</span>` (styled, not a dead link).
- **Citations:** keep claims grounded, but web pages are for a general reader — don't paste raw
  `(raw/filename.pdf)` cites. Instead note provenance once in the footer (e.g. "synthesised from N
  internal source documents") and keep the honest "interpretation, not a primary source" line.
- **Provenance & honesty:** carry over the wiki's flagged tensions/caveats rather than smoothing
  them. The footer should link back to `index.html`.
- **Self-contained & responsive:** no external assets except the shared `assets/xco.css` (which
  itself only pulls Google Fonts). Must read well on mobile (the CSS handles the breakpoints).

## Enabling / checking GitHub Pages
Pages is served from `main` / `/docs`. To (re)check:
`gh api repos/YOUR-ORG/YOUR-WIKI/pages`. To enable:
`gh api -X POST repos/YOUR-ORG/YOUR-WIKI/pages -f 'source[branch]=main' -f 'source[path]=/docs'`.

## Rules
- Never publish without confirming the owner wants it public.
- Never invent facts or citations; publishing does not lower the sourcing bar — it raises it.
- Keep filenames (URLs) stable once shared.
- One shared stylesheet — extend it, don't fork it.
