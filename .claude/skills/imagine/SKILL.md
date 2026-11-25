---
name: imagine
description: "Play with what a thing could be before designing it, from the Imagination Wiki's seeds. \"help me imagine\", \"make it less obvious\", or before design-brief."
---

# Imagine

## Why this exists

Asked for by Anahat and Gurden, 5 November 2026. A model left alone makes the likely thing: the report stays a
report, and "make it better" changes the font and the colour. Anahat named the problem a crisis of imagination. This
skill is the step before design: it asks what the thing could be at all, using what Dm's people have offered to the
Imagination Wiki, and then lets a person play.

Shared with every wiki on 6 November 2026, after Anahat and Gurden agreed that imagination is for everyone, not only
designers: a strategy, an event or a piece of writing can start here too. Imagination is images, and also sensations
and possibilities: things that have not happened yet.

It is an imagination partner, not a replacement for a person's imagination or a designer's hand. It should feel like
a fun partner someone brings an exciting idea to. Every result can be used as it is, or taken to a designer to finish.

Changed on 18 November 2026, after Gurden shared Briana (Mazzio) May's HUMAN.md (human-md.ai, 28 April 2026). Our
reading of it: a person who only reacts to what a model offers is not yet making the thing. In the first two uses
recorded in the Imagination Wiki, Claude proposed and the person judged. So the person now has four moves of their
own: a seed they bring, a change they make by hand, a rule they may break on purpose, and a word on how it should
feel.

Changed on 25 November 2026, at Gurden's request after an audit. The main job is better visual work by Claude. The
Imagination Wiki now holds Dm's own visual forms, each with how it is drawn and what breaks it. So visual work starts
from those forms, and Claude draws real rough pictures, not only words. Oblique cards were one seed that had taken
over the method. They are now optional.

## Method

1. **Hear the idea in the person's own form.** A sketch, a few sentences, or speech. Ask at most one question: who is
   it for, and what must it do? If the answer is already there, go on. If they do not know what they want yet, that
   is a good place to start: say so, and go on.
2. **Draw seeds from the Imagination Wiki.** A seed is a page tagged `reference`, `motif`, `form`, `provocation` or
   `palette` that someone offered. Find them where this wiki can see them:
   - **In the Imagination Wiki itself:** its own pages. Run `python3 tools/search.py "<the subject>" --top 12` to see
     what is near the subject.
   - **In any other wiki:** the read-only copy in `.commons/imagination-wiki/export/wiki.shared.json`. Every Dm wiki
     can use it. If the copy is missing, `noise.py` fetches it with the person's own GitHub sign-in.
   - **If the fetch fails,** the person cannot read the Imagination Wiki yet. Say so in one line: Gurden or Anahat can
     give them read access. Then go on with the person's own seeds (below).

   Pick two seeds **by chance, not by rank**, with `python3 .claude/skills/imagine/noise.py seeds --n 2`. It reads
   the seeds wherever this wiki can see them. A model asked to choose picks its favourites. Read the two. Name each
   one, and who brought it.
   **If the thing is visual** (a picture, diagram, deck, page or poster), pick from Dm's visual seeds:
   `noise.py seeds --n 2 --kind form,palette`. A form page says what the form answers, the structure it needs, how
   it is drawn, and what it must never do. Read all of it. If it names an example picture, search Google Drive for
   that file name and look at it before you draw.
   - **Dice** (the default) can land anywhere. Use it to break the obvious.
   - **Drift** (`--drift 0.1` gently, `0.5` far) walks among related seeds with Perlin noise. Use it once a direction
     feels alive. To keep walking on the next roll, pass back the `next at` value with `--at`.
   **One seed may come from another commons this wiki reads** (`.commons/<name>/export/wiki.shared.json`). Pick it by
   chance too, name its wiki, and say it is shared knowledge, not an offered seed.
   **Then ask the person for one seed of their own, every time.** Ask for something from an odd place, not the
   first search result. It can be an object, a photo, a phrase or a memory. Their seed counts as much as the two
   by chance. If they have none, draw a third seed by chance and say so. Offer to send their seed to the
   Imagination Wiki, credited to them.
   **If there are fewer than two seeds,** say so plainly. Ask the person for more of their own.
3. **Change the form before the style.** Offer five or more directions, two lines each. At least two must change the
   medium itself. Useful turns:
   - What if it were something you hold, walk through, hear, or play?
   - What would it be for a child, for a river, for someone in 2050?
   - What is the opposite of the obvious version?
   - Which seed would change it most if taken literally?
4. **Let the person play.** They react, combine, or throw directions away. Make rough sketches fast: a few lines of
   text, a layout in characters (an ASCII sketch), or a simple drawing. Rough on purpose, so nobody mistakes it for
   finished.
   **For visual work, draw, do not describe.** Make the directions the person likes as rough SVG or HTML sketches.
   Follow the seed form's drawing rules and its "never" line. Look at each render before you show it, and redraw what
   does not read. Rough means few details, not a broken drawing.
   **Cards are optional.** Draw one only if the person asks, or two rounds of play have not moved:
   `python3 .claude/skills/imagine/noise.py cards --n 1`. The cards are Dm's own oblique deck, after Eno and Schmidt's
   Oblique Strategies. Never copy cards from the original deck: their words are Eno and Schmidt's.
   **Before you settle, ask the person to change one thing by hand.** They can cross something out, redraw it,
   rename it or write a line. Use their change as they made it. Do not tidy it.
5. **Settle on one.** Write it in four lines: the form, the one bold thing, the seed it came from, and how it should
   feel. For the last line, ask the person who receives the thing and how it should feel to them. Use their words.
   Then ask whether they want to break one rule of the guide on purpose. If they do, add the rule and their reason
   as a fifth line. A break without a reason is a miss, not a choice. Only the person chooses a break.
6. **Hand it on.** To `design-brief` to make it well, or to a designer with a short note. Say which, and why.
   Give the brief or the note every line from step 5.
7. **Offer to remember it.** Ask: "Shall I save what we tried and what you kept?" On a yes, write a page tagged `use`:
   what was asked, the directions, what was kept and why. Record the person's own moves too: their seed, their change
   by hand, any rule they broke and why, and what they threw away and why. Leave the person's name off unless they
   ask for credit.
   - **In the Imagination Wiki,** the page goes there.
   - **In any other wiki,** it goes in this wiki, `private` by default. Then ask once whether they would like to offer
     it, or a seed it found, to the Imagination Wiki. Anahat and Gurden curate what goes in. Never send it yourself.

## Hard rules

- **Offered, never collected.** Use only what people chose to give. Never read Slack, private channels, messages,
  emoji reactions, prompts or anyone's listening, viewing or screen habits to harvest their expression.
- **Credit the person who brought a seed,** by name, as the page records it.
- **Generated pictures of real people or places are never shown as real.** Say what is generated.
- **Keep the person's work theirs.** Never save a use without a yes. Private material never enters the Imagination Wiki.
- **Rough is fine.** Do not polish during play. Polish is the next skill's job.
- **The person makes, not only judges.** Never skip their seed, their change by hand or their word on feeling to save
  time. If they decline one, continue, and record that they declined.

## Connections

- `design-brief`: what to do with the chosen direction. `imagine` comes before it.
- `design-brief`'s critic: judges a finished design, not a play sketch. Use it on the visual the person settles on.
- The Dm Desk, Anahat's interface: it draws from the same forms in the Imagination Wiki. Its link is on the
  Imagination Wiki's Dm Desk page.
