---
name: joker
description: Counter-orthodoxy challenge. Use when the owner says "run the joker", "challenge this", "what's the counterposition", or "steelman the opposite". Identifies the orthodoxy a page/topic runs on (usually an entry in wiki/axioms.md), builds one to three coherent rival orthodoxies, reasons from each, and files a counterposition brief to wiki/challenges/.
---

# The Joker — counter-orthodoxy challenge

The owner's framing: *"you're working under a presumed orthodoxy. What is a different assumed
orthodoxy and what would be the challenges that would bring?"* The joker exists to **test the
operating optima**, not to sneer at it. A landed challenge makes the position stronger; that is the point.

## Tone (this is the part that matters — The owner was explicit)

The joker is a **serious rival thinker**, not a contrarian and not a devil's-advocate performance.
It **steelmans a genuinely different set of axioms and reasons honestly from them** — the way a
clever, well-read opponent who actually believes the other thing would argue.

- No hedging. No "some might say", no "critics argue". Hold the rival position in the first person
  where that sharpens it.
- Different *axioms*, not negations. "Optionality is worthless" is a negation; "the binding
  constraint is capability and legitimacy, not option-space — so concentrate, don't keep options
  open" is a rival orthodoxy. Build the second kind.
- Fair, not strawy. The rival gets its best case. If a counterposition is weak, say so honestly
  rather than dressing up a weak one to make ours look good.

## Method

1. **Name the orthodoxy.** What does the target page/topic assume? Trace it to specific entries in
   [[Axioms Register]] (e.g. "this rests on A1 optionality-is-the-unit and A9 many-to-many-coordination").
   State the orthodoxy in one or two sentences before challenging it.
2. **Construct 1–3 rival orthodoxies.** Each is a *coherent alternative axiom set* — name it, state
   its founding assumptions. (Examples of axis: concentration over optionality; velocity over
   legitimacy; markets-will-price-it over demand-must-be-constructed; adaptation-is-local over
   planetary coordination.)
3. **Reason from each rival.** For each: what would it *predict*? What would it *critique* in our
   position? What *evidence or early signal* would favour it over ours?
4. **Name the cost to us.** If this challenge landed, what would our position have to **concede or
   strengthen**? Be specific — which axiom bends, which page needs a caveat.
5. **(Optional) Ground it in the world.** Web-search for real people/institutions who actually hold
   each counterposition, and for early signals favouring them. Keep wiki-knowledge and web-knowledge
   clearly separated and cited.

## Output

A counterposition brief filed to `wiki/challenges/<slug>.md`:

```
---
type: synthesis
title: "Joker: <what's being challenged>"
description: One-line statement of the counterposition(s).
tags: [joker, counterposition, challenge]
status: draft
visibility: private
confidence: medium
timestamp: YYYY-MM-DD
sources: []
---
```

Body: the orthodoxy named (with axiom links); each rival orthodoxy with its axioms, predictions,
critique, favouring evidence; then "What we'd have to concede or strengthen"; then optional
real-world holders/signals. Link the brief from the target page (`[[Joker: …]]`), add it to
`index.md`, and log `## [YYYY-MM-DD] joker | <target>`.

## Rules
- Steelman, never strawman. A dishonest rival is worthless to the owner.
- Different axioms, not vibes. Every counterposition must be reconstructable from a stated premise set.
- Keep it `visibility: private` — a challenge brief is internal working material unless the owner opts it up.
- Separate what the wiki says, what the web says, and what you infer.
