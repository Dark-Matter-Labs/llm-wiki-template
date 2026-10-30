---
name: visual-guide
description: File a project's visual style guide (logo, colour, type, layout, components, motion, design tokens) as one wiki page in a standard shape, with every exact value cited. Use when someone says "add this style guide", "capture our visual guide", "here's the brand guide for…", "file the Figma style guide", or shares a style guide site, PDF or token file. Also says which guide a wiki follows when it has none of its own.
---

# Visual guide

## Why this exists

On 30 October 2026 two visual style guides arrived on the same day: the Dm style guide site and Anahat's Madrid 2050
guide. Both hold the same kinds of thing: colours with tokens, a contrast table, typefaces, components, motion and a
brief for Claude. They were filed in two different shapes, so a reader could not compare them. Gurden and Anahat
asked for a shared skill so that every option's guide reads the same way. This is the first of the d.INO design
skills. The others (checking an asset against a guide, making an on-brand brief) will read pages in this shape.

## Which guide a wiki follows

Each federation, option and position keeps its own guide. No guide is sent to every wiki.

- **Dm federation:** the Dm guide, filed in the Dm commons as "The Dm brand and style guide site".
- **xCO:** xCO's own identity, filed in the xCO team wiki as "xCO Visual Identity — Dusk Tritone".
- **An option or position with its own guide uses it,** filed in its team wiki. Madrid has "Madrid 2050° style
  guide". Ocean Studio's "House style" is in progress.
- **An xCO option or position without its own guide uses xCO's, for now** (Gurden, 30 October 2026).

A guide is filed in the team wiki of the project it belongs to, never copied into other wikis. When someone asks
which guide applies, answer from this list and the wiki's `design/federation.json`.

## Method

1. **Follow the `ingest` skill for the source.** Save it into `raw/`, run `tools/source_scan.py`, and ask the tier
   once. With no answer, use this wiki's default. A guide its maker marks unlisted or not indexed never goes higher
   than `internal` without the maker's yes.
2. **Read the exact values from their best source.** Prefer, in this order:
   - a token file (JSON, CSS, SCSS) or the guide's own code;
   - the guide's tables;
   - its prose.
   Say which you read. If values are drawn by a script and not visible as text, read the script and say so.
3. **Look for an existing page first.** Run `python3 tools/search.py "<project> style guide" --top 12`. If the
   project already has a guide page, update it in place. Where values changed, flag the change rather than overwrite.
4. **Write one page in the shape below.** It is a `summary` with `derivation: source`. Title it
   "<Project> visual guide". Every colour, size, weight and rule carries a locator: section, heading or file.
5. **Credit the maker as the source names them.** If only the owner says who made it, write "(maker named by
   <owner>)". If nobody does, write "Maker not stated". Never guess.
6. **Cascade.** Link the project's page, the organisation's page and any other guide the project follows. Add one
   index row and a log entry: `## [YYYY-MM-DD] ingest | <Project> visual guide`.
7. **Run the checks and propose.** Run `tools/house_rules.py`, `tools/quote_check.py --check` on the page, and
   `tools/gates.py`. In a personal wiki, ask "Shall I merge this?". In a team wiki, propose and stop.

## The page's shape

Use these sections, in this order. Write "Not in the guide." under any the source does not cover. Never fill a gap.

1. **About this guide.** Whose it is, who made it, the master copy (Figma file, repository or site), the date read,
   whether it is adopted or a draft, and who may change it.
2. **Logo.** The versions, clear space, minimum size, and do's and don'ts.
3. **Colour.** A table: name, token, value, role. Then the guide's contrast pairs as a table: text colour,
   background, smallest size allowed. Copy values exactly. Never round or convert them.
4. **Type.** The typefaces, their licence (free or paid, and whose), the fallback, and the named text styles as a
   table: name, typeface, weight, size, line height.
5. **Layout.** Grid, spacing scale and breakpoints.
6. **Imagery.** Photography, illustration and diagrams.
7. **Components.** Buttons, cards, links, forms, charts: what each looks like and when to use it.
8. **Motion.** What moves, how fast, and what happens when a reader asks for reduced motion.
9. **Voice.** Only what the visual guide itself says. Link the writing guide this project follows rather than
   restating it.
10. **For builders.** Where the token files, fonts, logo files and any brief or prompts for Claude live, and their
    formats.
11. **Open questions.** Inconsistencies inside the guide, a maker or licence not stated, and values that disagree
    with another guide the project follows.

## Hard rules

- **Never invent a value.** A colour, size or rule the guide does not state stays out, or goes under Open questions.
- **Your own checks are yours.** If you test a contrast pair yourself, mark the result as Claude's check, never as
  the guide's rule.
- **Never copy font or logo files into the wiki.** Link them. Fonts carry licences, and a paid typeface is flagged
  under Type and Open questions.
- **One guide, one page.** A second guide for the same project updates the page and flags what differs.
- **Never edit `raw/`.** Never write a verification mark. Nothing merges without a person's yes in this chat.

## Connections

- `ingest`: saving the source, the tier and the cascade. This skill adds the page's shape.
- The project's writing guide, where its wiki has one: `xco-voice` in xCO wikis, the Dm guides in Dm wikis.
  This skill covers how things look, never how things are written.
- `publish-check`: before a guide page or anything made from it leaves Dark Matter Labs.
