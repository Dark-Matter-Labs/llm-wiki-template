---
name: ai-detox
description: Strip the machine tells out of writing. Use on anything a person will read, and always before the newsletter or any published page. Fires on "ai detox", "make this sound human", "take the AI out of this", "detox this draft".
---

# AI detox

Two sources, and where they disagree the house rules win.

**The house rules** were given by Gurden on 15 September 2026 and are reproduced below verbatim.

**`ai-writing-detox`** by Joe Amditis, from
`jamditis/claude-skills-journalism`, `journalism-core/skills/ai-writing-detox`, supplied by
Gurden the same day. Written for newsrooms. Most of it transfers; the parts that do are folded
in below and marked. Its own summary of the problem is worth keeping whole:

> Good writing is invisible. If readers notice the writing style, it's distracting from the
> content. AI patterns are noticeable, they break trust.

That is the reason this skill exists here. A wiki whose whole claim is that a person stands
behind its pages cannot afford prose that announces otherwise.

## The house rules

Write in plain prose. Short sentences, under 20 words most of the time. Vary the length.

No summary or recap at the end. No closing offer ("let me know if..."). No opener ("Great
question").

No bullet lists unless asked. No bold words in prose. No headers in anything under 500 words.

No em dashes. No arrows. No rhetorical questions you then answer yourself.

No "it's not X, it's Y" contrasts. Just say Y.

No rule of three ("fast, simple, effective") where two or four would be honest.

No hedging stacks ("it's worth noting", "while this may vary", "generally speaking"). Say the
limit once, plainly, and move on.

Do not tell the reader why something matters. Tell them the thing. If a sentence only says the
previous sentence was important, cut it.

Prefer a number to a range. Prefer a named source to "experts say".

Answer a simple question in one or two sentences.

## Banned words

**House:** delve, crucial, pivotal, robust, seamless, leverage, landscape, tapestry, testament,
underscore, showcase, holistic, nuanced, multifaceted, transformative, game-changer, navigate (in
the abstract sense), unpack, elevate.

**Added from `ai-writing-detox`:** realm, utilize, comprehensive, cutting-edge, synergy, paradigm,
empower, innovative, sophisticated, leveraging, ecosystem, rich (as a modifier), and *over* for a
quantity where *more than* is meant.

## Banned phrases

**House:** "here's the thing", "hope this helps", "at the end of the day", "in today's world",
"let's dive in", "the reality is", "simply put".

**Added from `ai-writing-detox`:** "it's important to note that", "it's worth mentioning that",
"it goes without saying", "as we all know", "without further ado", "in this article, we will",
"to be fair", "to be honest", "when it comes to", "in terms of", "moving forward", "going
forward", "at this point in time", "due to the fact that", "in order to", "and that's a good
thing", "and that's okay", "and I'm here for it".

## Banned shapes

The words are mechanical and the shapes are the real tell. `ai-writing-detox` names the
X-not-Y construction as **the dominant 2025–2026 ChatGPT and Claude rhetorical signature**,
which is why the house rule bans it outright.

Do not open a sentence with "So,", "Well,", "Now," (when not about time), "Look,", "Listen,",
"Basically," or "Essentially,".

Do not close one with "...right?", "...you know?" or "...if you will".

Do not stack near-synonyms ("comprehensive, sophisticated and robust"). Pick one, or none.

Do not stack hedges ("may potentially be able to possibly").

Do not stack nouns ("production-ready deployment system infrastructure").

Do not hide the actor in the passive ("it was determined that" — by whom?).

Do not define in a circle ("the system enables users to use the functionality").

## The substitution table

From `ai-writing-detox`, and it is the fastest pass to run:

| wrote | write |
|---|---|
| utilize | use |
| facilitate | help |
| implement | build, add, create |
| leverage | use |
| functionality | feature |
| methodology | method |
| in order to | to |
| due to the fact that | because |
| at this point in time | now |
| a large number of | many |
| in the event that | if |
| prior to | before |
| subsequent to | after |
| in close proximity to | near |
| has the ability to | can |

## Headings in sentence case

"Getting started with your project", not "Getting Started With Your Project". From
`ai-writing-detox`, and it agrees with how this wiki's index shelves are already written.

## Where the two sources disagree

**Em dashes.** `ai-writing-detox` says they are "fine in moderation" and only reflexive use is a
tell. The house rule bans them. **The house rule wins**, here and in every other disagreement.

**"Landscape".** `ai-writing-detox` bans it outright as corporate speak, and the house rule lists
it too. Both mean the abstract usage. The word survives where it means land: this corpus holds a
wildfire facility whose subject is actual hillsides, and calling them something else to satisfy a
word list would be worse writing, not better.

## Where the rules bend

**Reference documents keep their structure.** A skill file, a README, a table of measurements, an
index shelf. Headers and lists belong there. The rules govern sentences a person reads through,
not documents a person looks things up in.

**Quotations are left alone.** A source that used an em dash used one. Correcting somebody else's
words falsifies the record, the same reason `raw/` is immutable.

## Two tests, from `ai-writing-detox`

**The verbal tic test.** Read it aloud. A TED talk introduction, a LinkedIn post, a press release
or corporate communications all mean rewrite. How you would explain it to a colleague means keep.

**The deletion test.** Can the word go without losing meaning? Then it goes. Does the sentence add
information, or only sound impressive?

## The automated half

`python3 tools/check_prose.py` settles what a script can settle: the banned words, the banned
phrases, the X-not-Y construction and the em dash. It runs in CI as a **ratchet**, because 850
files already carry findings and 20,559 of them are em dashes. A file's count may fall and may
never rise, and a new file starts at zero. Recovered or imported work is recorded deliberately
with `--update-baseline --reason '...'`.

It never reads a quotation, a page title, code, frontmatter or a URL. It cannot see the shapes in
the section above, which are the half that matters.

## What this skill cannot do

It removes noise. It does not supply substance. A draft that passes every rule here and says
nothing has not passed.
