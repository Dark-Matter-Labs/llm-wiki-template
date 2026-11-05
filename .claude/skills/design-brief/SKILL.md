---
name: design-brief
description: Make a page, deck, card, dashboard or screen look made by a good studio, not by a model. Use when anyone asks Claude to design or build something people will look at ("make a landing page", "design the cards", "build the dashboard", "make it look good", "it looks too AI"). Reads the guide this wiki follows, writes a bold brief before building, then cuts. Pairs with design-critic.
---

# Design brief

## Why this exists

Asked for by Gurden on 3 November 2026. A model left to itself designs by committee: it picks the safe, likely
choice every time, so everything it makes looks alike. Two sources name the problem:

- Anshu Chimala's "How to turn your AI into a world-class designer" (Lenny's Newsletter, 1 September 2026). Its
  method: explore wide, define a distinct identity, then deliver by cutting. Its free part was read.
- "The vibecoded slop checklist" (credited to @theadnaankhan), which Gurden shared the same day: 14 tells and a bonus.
  `design-critic` holds it as `checklist.md`.

Our own work shows what the opposite looks like. See "What our own work teaches" below.

This is the second of the d.INO design skills. `visual-guide` files a guide. This skill makes things from it.
`design-critic` checks what was made.

## Method

### 1. Find the guide and the subject

1. Find the guide this wiki follows. `visual-guide` says which, by federation and project. Read that guide's page.
2. Where the guide states a colour, a typeface or a rule, it wins over anything in this skill.
3. Name the subject, the reader and the one job the thing must do. Use the wiki's own pages for the subject.
   If the reader or the job is unclear, ask one question.

### 2. Discover: go wide before you go deep

1. Make the model less predictable. Run `python3 -c "import secrets; print(secrets.token_hex(16))"`. Read
   choices from the string: which accent leads, which layout, which reference. Never show the string.
2. Name one concrete reference from the subject's own world, not from software. For example: a field map, a
   transit diagram, a seed packet or a court filing. Say how it shapes the layout or type.
3. Offer three directions in two lines each. Let the person react. Sharpen the one they choose.
4. Keep the directions that lost. A later model may do better with them.

### 3. Define: write the brief, then check it

Write the brief before any code. Keep it short:

- **Palette:** four to six values, taken from the guide. Say what each colour means.
- **Type:** the guide's faces, a scale and their weights.
- **Layout:** one sentence and a rough sketch in text.
- **The one bold thing:** the element a reader remembers. Everything else stays quiet.
- **Real content:** the words, figures and pictures it will carry, from the wiki, with their sources.

Check the brief against `design-critic`'s checklist. If a choice there is a default and not the guide's choice,
change it, and say what you changed.

### 4. Build, then let a critic judge it

1. Build from the brief.
2. Take a screenshot at laptop width and at phone width.
3. Run `design-critic` on the screenshot, in a fresh context that sees only the screenshot, the brief and the
   guide page.
4. Fix the biggest gaps it names. Run the same critic again, with the same prompt.
5. Stop when the score reaches 8, or when two rounds do not raise it. Say which.

### 5. Deliver: cut

1. Remove one thing before you finish: a glow, a gradient, a border, a label, a container or a highlight.
2. Prefer the platform's own controls to custom ones that work worse.
3. Let real pictures and real numbers carry the page. A shape is not a picture.

## What our own work teaches

Read on 3 November 2026 from the Dm Figma file "What We're Building" cards (season 04), the Dm style guide, the
xCO style guide and d.INO Home. These are patterns. Exact values stay in each guide.

- **Colour means something.** On the Dm cards, each card's accent says what kind of build it is: orange for
  "demand for the future", blue for "delivering solutions", purple for both. In d.INO Home, mint is your own wiki,
  blue a team's, pink a colleague's, and ochre a thing that needs you. A colour with no meaning is decoration.
- **One accent at a time.** Each Dm card uses one accent, on its key phrase and its partner line. xCO's guide says
  that a seventh colour is usually an opacity stop.
- **No pure white or pure black.** xCO's paper is chalk and its ink is a blue-black. Dm's dark ground is near-black.
- **No monospace labels.** Since 3 November 2026 d.INO sets labels in Ronzino's own small capitals and xCO in
  Untitled Sans. A monospace is for code.
- **A diagram says what kind of thing it is.** Each Dm card carries a small typology diagram, and xCO draws its
  diagrams by hand as part of its grammar. Neither uses a picture as decoration.
- **Texture comes from the subject.** The cards use contour lines, like a map, rather than a stock gradient.
- **Real people sign the work.** Each card names the people behind it, with a photo and an email address.

## Hard rules

- **The guide wins.** Never override a value the guide states. Never invent one it does not state.
- **Never copy font or logo files into a wiki.** Link them.
- **Generated images need the owner's yes.** Keep any image or video API key in a gitignored file. Never show a
  generated picture of a real person or place as real.
- **Hold the quality floor:** text contrast of 4.5:1, visible keyboard focus, reduced motion respected, and no
  sideways scrolling at phone width.
- **Respect the tiers.** A design for the open web carries only `public` material. Run `publish-check` before
  anything leaves Dark Matter Labs.

## Output

Give the person, in this order:

1. The brief.
2. The thing, with its two screenshots.
3. The critic's last score, and why you stopped.
4. What you cut, in one line.

## Connections

- `visual-guide`: which guide applies, and the shape of a guide page.
- `design-critic`: the checklist and the critic.
- `publish-check` and `publish-web`: before anything goes out.
- `ai-detox` and the wiki's writing guide: the words on the page.
