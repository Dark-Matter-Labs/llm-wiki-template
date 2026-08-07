---
name: publish-check
description: Check whether a wiki page or synthesis is ready to be shared or published externally. Use when the owner says "is this ready to publish", "can I share this", "check this before it goes out", or is about to lift wiki content into a report, post, or proposal. Verifies sourcing, flags unsupported claims, and checks for the kinds of issues that matter when work leaves the building.
---

# Publish check

The wiki is a working store; publishing to the outside world is a higher bar. Run this
before any wiki content becomes a report, post, proposal, or client-facing document.

## Checks

1. **Every claim is sourced or clearly marked.** Walk the page. Each factual claim
   should trace to a `raw/` source. Anything that is your synthesis or inference must
   be labelled as such — it may still be publishable, but the owner needs to know which is which.

2. **No fabricated or guessed citations.** Verify each cited source actually exists in
   `raw/` and actually says what the page claims. Flag any that don't.

3. **Confidence is honest.** A `confidence: low` page shouldn't be presented as settled
   fact. Flag anywhere the page's tone outruns its evidence.

4. **Contradictions resolved or acknowledged.** If the wiki flagged a contradiction on
   this topic, it can't silently disappear in the published version. Surface it.

5. **Attribution and lineage.** If the content draws on external frameworks, other
   people's ideas, or contributors, check they're credited. (If the owner has a house style
   guide for attribution/licensing, apply it here.)

6. **Plain-language pass.** Flag jargon that a general reader wouldn't follow, and any
   claim that would land differently out of context.

7. **Visibility tier is consistent with the content.** Check the page's `visibility`
   against what it actually says:
   - If it's marked `public` but reads as sensitive — names unconsenting people, exposes
     internal strategy/positions, scores places/actors, discloses partner or deal specifics,
     or would embarrass someone if indexed — **flag it and recommend `unlisted` or `private`**.
     Do not let it ship public on your own judgement; surface it to the owner.
   - If it's `private`/`unlisted` and the owner is asking to publish it, treat this whole check
     as the gate for moving it to `public`. Publishing = changing `visibility` to `public`
     and merging; nothing leaves the repo until that field changes.
   - If it's `internal`, it may go to colleagues via the mirror but **must not** be
     published to the web; treat a request to publish it as a tier change needing the owner's call.
   - Remember the boundary rule: a `private` page's title and inbound links are stripped
     from exports too, so "just this once" public exposure of a private page is never casual.

8. **Run the public-leak tripwire.** Before signing off anything that will become public
   or unlisted, run `python3 tools/scan_public_leaks.py`. It fails if any never-public term
   (`tools/sensitive_terms.txt`) appears on a public surface (all of `docs/` and every
   `public`/`unlisted` page). If it fires, stop and fix — do not ship. If the page discloses
   something newly sensitive, add the term to `sensitive_terms.txt` as part of the fix.
   (Remember: this is a backstop; the real protection is the access boundary — see
   `SHARING-AND-ACCESS.md`.)

## Output

A short readiness report:
```
# Publish check — <page title> — YYYY-MM-DD
Ready to share: yes / not yet

Must fix before publishing:
- …
Worth considering:
- …
```

Then, if the owner approves fixes, apply the sourcing/labelling corrections and note it in
the current month's log file (`wiki/log/YYYY-MM.md`; see `wiki/log.md`).

## Rules
- Err toward caution. Better to flag a borderline claim than let an unsupported one ship.
- Never "fix" a sourcing gap by inventing a source. Flag it and let the owner supply one.
- Don't use words like "guarantees", "ensures", "prevents", or "eliminates" about the
  content's effects unless a source explicitly supports that framing.
