---
name: design-brief
description: "Design a page, deck, card or screen so it looks made by a good studio, and score it from a screenshot. \"design this\", \"it looks too AI\", \"review this design\", \"is this on brand\"."
---

# Design brief

## Why this exists

Asked for by Gurden on 3 November 2026. A model left to itself designs by committee: it picks the safe, likely
choice every time, so everything it makes looks alike. Two sources name the problem:

- Anshu Chimala's "How to turn your AI into a world-class designer" (Lenny's Newsletter, 1 September 2026). Its
  method: explore wide, define a distinct identity, then deliver by cutting. Its free part was read.
- "The vibecoded slop checklist" (credited to @theadnaankhan), which Gurden shared the same day: 14 tells and a bonus.
  This skill holds it as `checklist.md`, beside this file.

Our own work shows what the opposite looks like. See "What our own work teaches" below.

This is the second of the d.INO design skills. `visual-guide` files a guide. This skill makes things from it, and
its last step, the critic, checks what was made.

**To review a design someone else made** ("review this design", "is this on brand"), go straight to
"The critic" below. Use the brief if there is one, and the guide page.

## Method

### 1. Find the guide and the subject

1. Find the guide this wiki follows. `visual-guide` says which, by federation and project. Read that guide's page.
2. Where the guide states a colour, a typeface or a rule, it wins over anything in this skill.
3. Name the subject, the reader and the one job the thing must do. Use the wiki's own pages for the subject.
   If the reader or the job is unclear, ask one question.
4. Take how it should feel to the reader from the person, in their words. `imagine` hands this on.

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
- **How it should feel:** to the reader, in the person's words.
- **The break, if the person chose one:** the rule of the guide it breaks, and their reason.

Check the brief against `checklist.md`. If a choice there is a default and not the guide's choice,
change it, and say what you changed.

### 4. Build, then let a critic judge it

1. Build from the brief.
2. Take a screenshot at laptop width and at phone width.
3. Run the critic (below) on the screenshot, in a fresh context that sees only the screenshot, the brief and the
   guide page.
4. Fix the biggest gaps it names. Run the same critic again, with the same prompt.
5. Stop when the score reaches 8, or when two rounds do not raise it. Say which.
6. Show the person the result. Ask whether it feels as the brief says, and whether anything in it delights them.
   The critic cannot judge this from a screenshot. Fix what the person names.

### 5. Deliver: cut

1. Remove one thing before you finish: a glow, a gradient, a border, a label, a container or a highlight.
2. Prefer the platform's own controls to custom ones that work worse.
3. Let real pictures and real numbers carry the page. A shape is not a picture.

## The critic

A model that built a page is a poor judge of it: it knows the code and the history, and it likes what it just
wrote. So the critic works in a fresh context that sees only a screenshot.

1. **Get the inputs.** A screenshot at laptop width, and one at phone width if the design is a page. Add the brief,
   if there is one, and the guide page this wiki follows (see `visual-guide`).
2. **Use a fresh context.** Start a subagent where the tools allow it. Give it only the screenshots, the brief and
   the guide page. Never give it the code or the conversation.
3. **Give it the critic prompt below, word for word.** Use the same prompt every round. Never tell it a target score.
4. **Check the tells.** Go through `checklist.md`. A tell is a default, not a choice. If the guide declares the
   choice, it is not a tell. Say which guide line declares it.
5. **Report** in the shape below.

The critic prompt:

> You are the design director of a studio known for work that is never mistaken for anyone else's. You see only
> these screenshots, the brief and the house guide. First say in one sentence what the design is trying to be.
> Then imagine how your studio would have made it for this subject and this reader. Name the three biggest gaps
> between this design and that version, each with a specific fix. Name every pattern that looks generated by a
> model, using the attached checklist. Check every colour, typeface and rule against the house guide, and name each
> place it departs. Where the brief names a break on purpose, judge whether it earns its place. Say what one thing
> to remove. Finally, score it out of 10, where 10 means a demanding studio
> would ship it as it stands. Be specific and blunt. Do not praise.

The report gives, in this order:

1. **Score:** a number out of 10, and one sentence on why.
2. **Biggest gaps:** three at most, each with its fix.
3. **Tells found:** each with its checklist number and where it is.
4. **Off the guide:** each departure, with the guide's line it breaks. Mark a break the brief names as chosen, and
   say whether it earns its place.
5. **Cut:** the one thing to remove.

Rules for the critic:

- **Judge only what you can see.** A screenshot does not show behaviour. Say what you could not check.
- **How it feels is the person's call.** The score judges craft. Step 4 asks the person how it feels.
- **Never score people.** The critic judges the design, never its maker.
- **The guide wins over the checklist.** Our guides make some choices the checklist calls tells, such as the
  lavender accent in the Dm guide. A choice the guide declares is not a fault.
- **A score is not a verification.** It goes in the reply, never in a page's `validation` or `machine_checks`.

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

- **The guide wins.** Never override a value the guide states. Never invent one it does not state. The one
  exception is a break the person names in the brief, with its reason. Never break a rule of the guide yourself.
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
4. What the person said about how it feels, and what you changed for it.
5. What you cut, in one line.

## Connections

- `visual-guide`: which guide applies, and the shape of a guide page.
- `checklist.md`: the tells the brief and the critic check against.
- `publish-check` and `publish-web`: before anything goes out.
- `ai-detox` and the wiki's writing guide: the words on the page.
