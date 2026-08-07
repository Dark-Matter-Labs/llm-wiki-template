---
name: publish-web
description: Turn a wiki page (or a synthesis/overview/curated topic) into a styled, standalone, shareable HTML web page under docs/, served by GitHub Pages. Use when the owner says "publish this as a web page", "make a shareable link for…", "put this on the site", "turn this into a webpage", or wants wiki content sent to people as a URL. Applies the xCO design system with full typographic, layout, accessibility and UX craft.
---

# Publish a wiki page to the web

the owner wants to share wiki content as web links. Published pages live in `docs/` and are
served by **GitHub Pages** at `https://YOUR-ORG.github.io/YOUR-WIKI/<name>.html`.
Each page is a self-contained, styled, responsive HTML file that anyone can open.

**Publishing is a higher bar than the wiki**, on two axes:
- **Truth** — these pages leave the building. Run `publish-check` first: verify sourcing,
  flag unsupported claims, confirm the owner wants it public.
- **Craft** — a wiki page is a working note; a published page is a designed artefact. It is
  read by people who owe you no patience. **Design is not decoration here — it is how the
  argument becomes legible.** A well-set page is understood; a badly-set one is closed.

The single most important instruction in this skill: **do not translate markdown into HTML.
Re-compose the argument into a designed page.** A dumped page is a failure even if every
tag is valid.

---

## Step 0 — Editorial pass, before any HTML

Do this in your head (or in notes) *first*. It determines everything downstream.

1. **Find the claim.** What is the one thing this page asserts? It becomes the `h1` — a
   sentence, not a title. "Growth is the widening distribution of the capacity to shape
   shared worlds" is an `h1`. "The Agency Accounts" is a filename.
2. **Write the one-sentence argument.** This becomes `.subtitle` and the meta description
   and the `og:description`. If you can't write it, you don't understand the page yet.
3. **Sequence the movements.** Group the source into 3–7 sections. Each gets a 1–3 word
   mono label. **If you need more than 7, the page is two pages.**
4. **Choose the texture of each section** before writing it — prose, cards, table, stats,
   quote. Plan the alternation now (see *Rhythm*).
5. **Find the three lines worth setting large.** The lead, and one or two pull-quotes.
   These carry a reader who never reads a full paragraph.
6. **Decide what to cut.** Published pages are shorter than wiki pages. Caveats stay;
   throat-clearing goes.

**The scannability test — apply it at the end.** Read *only* the eyebrow, `h1`, subtitle,
section labels, lead, and pull-quotes. Do you get the argument? If not, the page fails for
the majority of real readers, however good the prose is.

---

## Build steps

1. **Confirm intent & sourcing.** Run `publish-check`-style checks. Never publish without
   the owner's explicit go-ahead.
2. **Choose a filename** — short, kebab-case, stable: `docs/<slug>.html`. This IS the
   shareable URL; don't churn it later.
3. **Do the Step 0 editorial pass.**
4. **Write the HTML** from the template below, applying the craft rules.
5. **Do NOT touch `docs/index.html`.** The root stays a minimal `noindex` landing page and
   must never become a directory of published pages — pages are reachable only by the direct
   link the owner shares. Adding a card there silently widens the audience for every page.
6. **Verify** — run the full verification loop below. Not optional; it catches the errors
   that are invisible in source.
7. **Ship.** Commit to a branch, push, open/update a PR. Report the exact URL in plain language.
8. **Log it.** Append `## [YYYY-MM-DD] publish | <page title> → <url>` to the current month's
   log file (`wiki/log/YYYY-MM.md`).

---

## The page template

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <title>… — YOUR ORGANISATION</title>
  <meta name="description" content="…the one-sentence argument…">

  <!-- Link preview. These pages exist to be SENT AS LINKS — in Slack, email, WhatsApp,
       LinkedIn. The preview card IS the first impression, and more people will see it
       than will open the page. Never ship without these. -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="…the h1, or a shortened version of it…">
  <meta property="og:description" content="…the one-sentence argument…">
  <meta property="og:url" content="https://YOUR-ORG.github.io/YOUR-WIKI/<slug>.html">
  <meta property="og:image" content="https://YOUR-ORG.github.io/YOUR-WIKI/assets/social-card.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="https://YOUR-ORG.github.io/YOUR-WIKI/<slug>.html">

  <link rel="stylesheet" href="assets/xco.css">
</head>
<body>
  <!-- First tab stop. Lets a keyboard user jump the masthead. -->
  <a class="skip-link" href="#main">Skip to content</a>

  <div class="top-rule"></div>
  <div class="page-shell">

    <header class="hero hero-single">
      <div class="hero-copy">
        <p class="eyebrow">YOUR ORGANISATION · SECTION · <Type></p>
        <h1>…the claim, as a sentence…</h1>
        <p class="subtitle">…the one-sentence argument…</p>
      </div>
    </header>

    <section class="document-meta" aria-label="Document details">
      <div><span class="label">Type</span><span class="value">…</span></div>
      <div><span class="label">Status</span><span class="value">…</span></div>
      <div><span class="label">Updated</span><span class="value">…</span></div>
    </section>

    <main id="main">
      <section class="section">
        <h2 class="section-label">…1–3 word kicker…</h2>
        <div class="section-content">
          <p class="lead">…the strongest line…</p>
          <p>…</p>
        </div>
      </section>
      <!-- repeat .section per movement -->
    </main>

    <footer class="footer">…provenance + honesty line + link back…</footer>
  </div>
</body>
</html>
```

**On the section label as `h2`:** the mono kicker is the page's real heading structure —
mark it up as one so screen readers and search get a sensible outline. If a section needs a
visible headline *as well*, put an `h2` inside `.section-content` and demote the label to a
`div` — never emit two `h2`s for one section, and never skip a level.

---

## Craft: typography

The system is three typefaces doing three jobs. **Choose by role, never by looks.**

| Face | Role | Never use for |
| --- | --- | --- |
| **Crimson Pro** (serif) | the argument — running prose | headings, labels, UI |
| **Inter** (sans) | statements — `h1`/`h2`/`h3`, `.lead`, `.quote-block`, data | long prose |
| **DM Mono** | structure — eyebrows, labels, captions, section kickers | anything you must *read*, not scan |

**Measure is the discipline that matters most.** Body text is 21px Crimson Pro capped at
`--measure` (760px ≈ 70–75 characters). That cap is already on `p`, `ul`, `ol` — **do not
override it.** Long lines are the single most common way a beautiful page becomes unreadable:
the eye loses its place on the return sweep.

- **Prose obeys `--measure` (760px).** Always.
- **Display elements may run wider (1060px)** — `.lead`, `.quote-block`, `.aside-grid`.
  They're absorbed in a glance, not read line by line, so the return-sweep problem doesn't apply.
- **Tables and figures may run widest (1240px)**, because scanning a matrix is a different act.

**Hierarchy is carried by scale contrast, not by many sizes.** The system jumps hard —
`h1` up to 108px against 21px body. That ratio is why it reads instantly. **Do not invent
intermediate sizes**; every step you add flattens the hierarchy. Use the ladder you have:
`h1` → `.lead` → `h2` → `h3` → body → `.small`/`.caption`.

**Other rules:**
- **One `h1` per page.** No skipped levels (`h2` → `h4` is a bug).
- **Never centre body text.** The system is left-aligned and ragged-right throughout; centring
  destroys the return sweep and the grid.
- **Bold is for load-bearing terms**, roughly one per paragraph at most. Bold everywhere is
  bold nowhere.
- **No italic for emphasis in prose** — Crimson Pro's italic is for titles and voice.
- **Never set prose in all-caps.** Caps are for mono labels under ~5 words only.

---

## Craft: space

**Negative space is a structural element, not leftover margin.** The spacing scale is
Fibonacci — `--s1: 13px`, `--s2: 21px`, `--s3: 34px`, `--s4: 55px`, `--s5: 89px` — and each
step encodes one level of relationship:

| Step | Means | Use between |
| --- | --- | --- |
| `--s1` 13px | *bound together* | a label and the thing it labels; a figure and its caption |
| `--s2` 21px | *same thought* | paragraphs; cards in a grid |
| `--s3` 34px | *new block* | a heading and its body; a block and the next |
| `--s4` 55px | *new movement* | before/after a quote, table, or figure |
| `--s5` 89px | *new section* | between `.section`s (the CSS already does this) |

**Two consequences you must respect:**

1. **Never use a value off the scale.** No `margin: 40px`. If you reach for a number, you've
   stopped designing and started nudging. The scale is what makes 106 pages feel like one system.
2. **Proximity is meaning.** A caption 34px from its figure has visually detached from it. If
   two things are related, they must be *closer together* than either is to anything else.
   Most "this page feels muddled" problems are proximity errors, not colour or type problems.

**Generosity at the top.** The hero is `78vh` on purpose: the page opens with a held breath.
Resist the urge to fill it. Space above a claim is what makes it read as a claim.

---

## Craft: grid & alignment

- The page is a **golden-ratio grid** — `--phi-major: 61.8fr` / `--phi-minor: 38.2fr`.
  `.section` puts the mono label in the minor column and content in the major.
- **The sticky section label is a wayfinding device.** It stays visible while the reader
  scrolls the section, answering "where am I?". Keep labels **1–3 words** — a long label
  wraps into a paragraph in the margin and stops working.
- **Use `.section-wide`** when content genuinely needs full width (a large matrix, a wide
  figure). The label then sits above rather than beside. Don't use it just to get more room.
- **Everything aligns to the same left edge.** The `--page-pad` gutter and the 13px navy
  `.page-shell` border establish it. Never introduce an ad-hoc indent.
- **Optical alignment beats mathematical alignment** for large type: if a huge `h1` looks
  inset because it starts with a round letter, that's normal — don't "fix" it with a
  negative margin.

---

## Craft: colour & contrast

Three colours. **Navy is everything; orange is punctuation; white is air.**

- `--shadow` `#192640` — text and structure. 15.08:1 on white. The workhorse.
- `--midtone` `#F27F3D` — **structure only on paper**: rules, borders, underlines, the
  left edge of a `.quote-block`, the `::before` tick on a section label.
  **It is 2.67:1 on white — it FAILS WCAG AA for text.** Never set body or label text in it
  on a white background.
- `--midtone-ink` `#C7510D` — **text on paper.** Same hue and saturation, darkened to
  4.55:1 so it passes AA. Use this whenever orange must be *read* on white.
- On navy panels (`.footer`, `.dark-card`, `.slide-dark`, `.hn-*`) `--midtone` is 5.66:1 and
  is correct for text — keep using it there.

**The 5% rule.** If more than about a twentieth of the page is orange, it has stopped being
an accent and become a second body colour — at which point it emphasises nothing. Count the
orange before you ship: top rule, section ticks, one quote bar, maybe one card edge.

**Never introduce a new colour.** No greys for "secondary" text — use `.small`, or navy at a
smaller size. No semantic red/green. If something needs to recede, make it smaller or shorter,
not lighter. (Grey text is the most common accessibility failure in editorial design.)

---

## Craft: choosing the right component

The most common failure is prose that should have been a table, or a table that should have
been prose. Choose by the *shape of the information*:

| The content is… | Use | Not |
| --- | --- | --- |
| A single strong assertion opening a section | `.lead` | a bold paragraph |
| A quotable line, or a sourced quotation | `.quote-block` | `<blockquote>` unstyled |
| 2–6 **parallel** items of similar weight | `.aside-grid` + `.card` | a bulleted list |
| One item needing emphasis among cards | `.accent-card` / `.dark-card` | colour on text |
| A matrix — items × attributes | `.table-wrap` + `table` | prose describing the matrix |
| 2–4 headline numbers | `.stat-grid` + `.stat` | numbers buried in a sentence |
| A sequence or causal chain | `.chain` | an ordered list |
| Term → definition pairs | `.def-list` | a table with two columns |
| An equation or formal relation | `.formula` | an image of an equation |
| A caveat or aside | `.small` after the block | a footnote |

**Rules of use:**
- **Cards must be parallel and similar in length.** A grid where one card is 3× another looks
  broken. Rewrite to balance, or use prose.
- **A list of 2 is not a grid** — write it as a sentence.
- **Tables need a real header row** with `<th scope="col">`, and a `.caption` above or below
  saying what the table shows.
- **Never nest** a grid inside a card, or a table inside a card.

---

## Craft: rhythm & flow

This is what makes a long page readable rather than merely correct.

- **Alternate texture.** Never more than **three consecutive prose paragraphs** without a
  change — a quote, a card grid, a table, a stat row, a subhead. The eye needs a landing.
- **Never stack two heavy display elements.** A `.lead` immediately followed by a
  `.quote-block` reads as shouting; put prose between them.
- **Open each section with its strongest sentence**, not with context-setting. Context can
  follow the claim; it can't precede it and survive.
- **Vary section length.** Five sections of identical length feels mechanical. A short,
  sharp section after two long ones creates emphasis for free.
- **End deliberately.** The last section should land the argument, not trail into caveats.
  Caveats belong in the footer honesty line or inline where they arise.
- **The footer carries provenance and honesty**: what this was synthesised from, the
  "interpretation, not a primary source" line, and a link back. Carry over the wiki's flagged
  tensions rather than smoothing them.

---

## UX & accessibility — non-negotiable

These are requirements, not aspirations. **A page that fails these does not ship.**

**Structure**
- `<html lang="en">`, a unique `<title>`, a `<meta name="description">`.
- `<a class="skip-link" href="#main">` as the **first element in `<body>`**.
- Exactly one `<main id="main">`. One `h1`. No skipped heading levels.
- `aria-label` on `.document-meta` (it's a region with no heading).

**Links**
- Link text must make sense read alone. "Read the cascade atlas" — never "here", "this", "read more".
- Only link a `[[wiki link]]` if the target is **also published** in `docs/`. Otherwise render
  it as `<span class="term">name</span>` — styled, honest, not a dead end.
- Any link leaving the site is fine unmarked; don't open new tabs (`target="_blank"` steals
  the reader's back button).

**Interaction**
- Focus rings come from the stylesheet's `:focus-visible` — **never** write `outline: none`.
- Interactive targets ≥ 24×24px (WCAG 2.2 AA). `.card-link` already clears this; small inline
  links in a dense footer may not — give them padding.
- Respect `prefers-reduced-motion` — handled in the stylesheet; don't add animation that bypasses it.

**Content**
- Every table: `<th scope="col">` (and `scope="row"` where rows are labelled) + a caption.
- Every figure: a `.caption` that says what it shows, not "Figure 1".
- Never convey meaning by colour alone — orange plus position/label, never orange alone.
- No text baked into images (it can't be read, searched, translated, or zoomed).

**Delivery**
- Self-contained: no external assets beyond `assets/xco.css` (which pulls Google Fonts).
- No horizontal scroll at any width. Wide tables scroll **inside** `.table-wrap`, not the page.
- Print: the stylesheet has a `@media print` block — check a long page still breaks sanely.

---

## Verification loop (run this every time)

Source review does not catch layout, contrast, or overflow errors. **Look at the page.**

1. **Serve it.** Start the `docs-preview` server (`.claude/launch.json`, port 8099) and open
   `http://localhost:8099/<slug>.html`.
   *If you just edited `assets/xco.css`, cache-bust before trusting what you see* — the
   stylesheet is cached and you will otherwise verify the old design.
2. **Three viewports.** Screenshot at **desktop (1280)**, **tablet (768)**, **mobile (375)**.
   Check at each: no horizontal overflow, cards reflow sensibly, the hero doesn't push all
   content below the fold on mobile, tables scroll inside their wrapper.
3. **Keyboard.** Tab from the top. The skip link must appear first; every link must show a
   visible focus ring; focus order must follow reading order.
4. **Console.** `read_console_messages` — no errors, no 404s on assets.
5. **Contrast.** Any orange text on white must be `--midtone-ink`, not `--midtone`.
6. **The squint test.** Blur your eyes (or shrink the screenshot). You should still see a
   clear hierarchy — one dominant headline, distinct section blocks, a visible rhythm of
   texture. If it reads as a uniform grey slab, the page is under-designed.
7. **The scannability test** from Step 0.

A quick programmatic check for overflow and structure:

```js
({ overflowX: document.body.scrollWidth > document.documentElement.clientWidth,
   h1s: document.querySelectorAll('h1').length,
   main: !!document.querySelector('main#main'),
   skip: !!document.querySelector('.skip-link'),
   emptyLinks: [...document.querySelectorAll('a')].filter(a=>!a.textContent.trim()).length })
```

---

## Anti-patterns

- **Markdown dumped into `<div>`s.** The commonest failure. Re-compose, don't convert.
- **A wall of even-length paragraphs.** No texture, no entry point, no one reads it.
- **Decorative orange.** Colour used to look designed rather than to mean something.
- **Card grids of non-parallel content**, or one card with 4× the text of its neighbour.
- **Long section labels** that wrap in the sticky margin column.
- **Invented spacing values** — the moment you type `margin: 40px`, stop.
- **Grey secondary text** for de-emphasis. Fails contrast, adds a colour, solves nothing.
- **A `.lead` in every section.** If everything leads, nothing does — one or two per page.
- **Publishing without the link-preview block**, so the URL renders as a bare card.

---

## Rules

- Never publish without confirming the owner wants it public.
- Never invent facts or citations; publishing raises the sourcing bar, it doesn't lower it.
- Keep filenames (URLs) stable once shared.
- One shared stylesheet — **extend it, never fork it**, and never inline per-page CSS. If a
  genuinely new component is needed, add it to `assets/xco.css` using the existing tokens,
  and check the change against a sample of existing pages before shipping (the stylesheet is
  shared by every published page — a token change is a change to all of them).
- `docs/index.html` stays minimal and `noindex`. Never catalogue published pages there.

## Enabling / checking GitHub Pages
Pages is served from `main` / `/docs`. Check: `gh api repos/YOUR-ORG/YOUR-WIKI/pages`.
Enable: `gh api -X POST repos/YOUR-ORG/YOUR-WIKI/pages -f 'source[branch]=main' -f 'source[path]=/docs'`.
