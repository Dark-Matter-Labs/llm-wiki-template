---
name: dm-style-guide
description: Write in Dark Matter Labs' voice. Use for anything carrying the DM name outward, and always alongside ai-detox for the newsletter or a published page. Fires on "dm style", "in our voice", "dm style guide", "make this sound like DM".
---

# Dark Matter Labs voice

Taken from the living guide in the `dm-style-guide` repository (v1.0.0, 2026), section 06 *Voice
and tone*, whose values are pulled from the live darkmatterlabs.org codebase. This file is the
working extract; the guide is the source, and if the two disagree the guide wins.

## The voice in one line

Systems-minded, inquiry-led, quietly hopeful. A research lab thinking out loud about the next
economies.

We write about radical, planetary ideas in plain, precise language. We lead with questions, never
hype. The register is essayistic and civic.

## In our voice

> "What would it mean to treat a forest as legal infrastructure, something a city is obliged to
> maintain, the way it maintains a road?"

## Not our voice

> "Our game-changing platform unlocks next-gen synergies to revolutionise sustainability!"

## Do

Open with inquiry. "What would it mean to...", "How might we...".

Be precise and grounded. Explain radical ideas in plain words.

Hold a long, intergenerational, planetary horizon.

Stay calm and confident. Hope without hype.

## Don't

Use marketing superlatives, buzzwords or exclamation marks.

Over-claim or sell. We open options. We do not promise outcomes.

Use emoji or hype punctuation in formal assets.

Flatten complexity into slogans.

## The house orthography, which is not optional

Always spell **civilization** with a z, never an s. It is a deliberate exception to the rest of
the house's British spelling: *optionality*, *manoeuvre* and *organising* keep their s.

Always write **xCO**, lowercase x, uppercase CO.

Both are checked by `python3 tools/house_rules.py`, and the check gates every deploy. Neither
touches `raw/` or a verbatim quotation, because those are somebody else's words.

## How this sits with `ai-detox`

They do different jobs and both apply. `ai-detox` removes the tells that make prose read as
machine-written. This file says what the writing should sound like once they are gone.

Where they appear to conflict, `ai-detox` wins on sentence mechanics and this file wins on stance.
The one real overlap is hype: both ban it, which is not a conflict.

Note the tension worth holding rather than resolving. The DM voice opens with inquiry; `ai-detox`
bans rhetorical questions you then answer yourself. Both are right. An opening question that the
piece genuinely goes on to explore is inquiry. One you answer in the next sentence is decoration.
