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

## Method

1. **Hear the idea in the person's own form.** A sketch, a few sentences, or speech. Ask at most one question: who is
   it for, and what must it do? If the answer is already there, go on. If they do not know what they want yet, that
   is a good place to start: say so, and go on.
2. **Draw seeds from the Imagination Wiki.** A seed is a page tagged `reference`, `motif`, `form`, `provocation` or
   `palette` that someone offered. Find them where this wiki can see them:
   - **In the Imagination Wiki itself:** its own pages. Run `python3 tools/search.py "<the subject>" --top 12` to see
     what is near the subject.
   - **In any other wiki:** the read-only copy in `.commons/imagination-wiki/export/wiki.shared.json`, if this wiki
     reads it (run `python3 tools/sync_commons.py` if the folder is empty). List its seeds with:
     `python3 -c "import json;[print(n['title'],'|',n['tags']) for n in json.load(open('.commons/imagination-wiki/export/wiki.shared.json'))['nodes'] if set(n.get('tags') or [])&{'reference','motif','form','provocation','palette'}]"`
   - **If this wiki does not read the Imagination Wiki,** say so in one line: Gurden can connect it. Then go on with
     the person's own seeds (below).

   Pick three seeds **by chance, not by rank**, with `python3 .claude/skills/imagine/noise.py seeds`. It reads the
   seeds wherever this wiki can see them. A model asked to choose picks its favourites. Read the three. Name each one,
   and who brought it.
   - **Dice** (the default) can land anywhere. Use it to break the obvious.
   - **Drift** (`--drift 0.1` gently, `0.5` far) walks among related seeds with Perlin noise. Use it once a direction
     feels alive. To keep walking on the next roll, pass back the `next at` value with `--at`.
   **One seed may come from another commons this wiki reads** (`.commons/<name>/export/wiki.shared.json`). Pick it by
   chance too, name its wiki, and say it is shared knowledge, not an offered seed.
   **If there are fewer than three seeds,** say so plainly. Ask the person for one or two of their own: a reference, an
   image, a form they love. Use those, and offer to send each one to the Imagination Wiki, credited to them.
3. **Change the form before the style.** Offer five or more directions, two lines each. At least two must change the
   medium itself. Useful turns:
   - What if it were something you hold, walk through, hear, or play?
   - What would it be for a child, for a river, for someone in 2050?
   - What is the opposite of the obvious version?
   - Which seed would change it most if taken literally?
4. **Let the person play.** They react, combine, or throw directions away. Make rough sketches fast: a few lines of
   text, a layout in characters (an ASCII sketch), or a simple drawing. Rough on purpose, so nobody mistakes it for
   finished.
   **When play is stuck, draw a card:** `python3 .claude/skills/imagine/noise.py cards --n 1`. The cards are Dm's own
   oblique deck, one per seed, after Eno and Schmidt's Oblique Strategies. Apply the card even if it seems not to fit,
   then look at what changed. Never copy cards from the original deck: their words are Eno and Schmidt's.
5. **Settle on one.** Write it in three lines: the form, the one bold thing, and the seed it came from.
6. **Hand it on.** To `design-brief` to make it well, or to a designer with a short note. Say which, and why.
7. **Offer to remember it.** Ask: "Shall I save what we tried and what you kept?" On a yes, write a page tagged `use`:
   what was asked, the directions, what was kept and why. Leave the person's name off unless they ask for credit.
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

## Connections

- `design-brief`: what to do with the chosen direction. `imagine` comes before it.
- `design-critic`: judges a finished design, not a play sketch.
- The Dm Desk, Anahat's interface: it runs this same method and reads the Imagination Wiki.
