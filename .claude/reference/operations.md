<!-- Moved word for word from CLAUDE.md on 2026-10-13 so it is read when needed, not on every turn.
     CLAUDE.md keeps every rule as a short line and points here for the reasons and the detail. -->

# The core operations in full

The table of what to run when, and the notes on the site, the Axioms Register and the CRM.

## The core operations

You have skills in `.claude/skills/`. Read the relevant SKILL.md before running one.
In plain-English terms, here is when each fires:

| The owner says something like…                     | You run   |
| -------------------------------------------------- | --------- |
| "add this", "ingest", "here's a new report"        | `ingest`  |
| "what does the wiki say about…", "find", "compare" | `query`   |
| "check the wiki", "is it healthy", "clean up"      | `lint`    |
| "catch me up", "what's new", "weekly summary"      | `brief`   |
| "I have a new idea / project", "help me think"     | `office-hours` |
| "sharpen this", "test my idea", "make this defensible" (questions only, no answers) | `sharpen` |
| "set up a wiki for X", "onboard a new option", "Santiago needs its own wiki" | `onboard` |
| "is this ready to publish / share externally"      | `publish-check` |
| "publish this as a web page", "make a shareable link", "put this on the site" | `publish-web` |
| "challenge this", "run the joker", "what's the counterposition", "steelman the opposite" | `joker` |
| "run the weekly reflection", "what deviated this week" (by hand — the Friday job was deleted 2026-09-18) | `reflect` |
| "how am I using this", "metacognition", "usage patterns" | `metacognition` |
| "what's the gravity / trajectory of the repo", "where does this sit relative to the repo" | `gravity` |
| "make that a skill", "learn this pattern" (asks you to verify before creating) | `learn` |
| "run a delta", "measure this against the wiki", "where does this sit / move us", "diff this paper against our position" | `delta` |
| "share this with the team", "contribute this", "propose this to the commons" | `contribute` |
| "add a contact", "log that meeting", "met X today", "what follow-ups are due", "who do we know at…", "who haven't we spoken to", "funder pipeline", "prep me for my meeting with…" | `crm` (with `tools/crm.py`) |
| "find leads", "lead generation", "who should we approach about…", "who funds…" | `leads` |
| "cross-check this", "get a second opinion", "what would another model say" | `cross-check` |
| "run the luck generator", "who should I talk to", "who's worth a conversation" | `luck` |
| "what don't we know", "what's unanswered", "what is the wiki waiting on" | `open_questions.py`, then `inquiry` |
| "what patterns are emerging", "meta patterns", "what haven't we named yet" | `patterns` |
| "what's waiting for me", "what needs me", "anything outstanding" | `waiting` |
| "ai detox", "make this sound human", "take the AI out of this" | `ai-detox` |
| "dm style", "in our voice", "make this sound like DM" | `dm-style-guide` |
| "xCO voice", "in xCO's voice", "xCO tone" (and anything written for or as xCO) | `xco-voice` |
| "did anything get lost", "check parity" — **and automatically on every rebuild** of an artifact with a countable record set | `rebuild-parity` |
| "do the call notes", "file my call notes", "here are the notes from the call" | `call-notes` |
| "update the overview", "the overview is out of date" — and when lint names overview drift | `overview-refresh` |
| "update my commitments", "that's done", "what am I on the hook for" | `my-commitments` |
| "from now on…", "always…", "make that a rule", "what rules have I set" | `rulings` |
| "rename this", "it's now called X", "is the name right everywhere" | `rename` |
| "update the live page", "fix the page on the site", "it looks wrong on my phone" | `live-page` |
| "are my sources still current", "has this page changed", "refresh the sources" | `source-refresh` |
| "something leaked", "remove this everywhere", "retract this", "I pasted a password" | `retract` |
| "run the INO check", "is this inquiry-native", "does this know what it's testing" — and before a theory of change, proposal, brief, deck or published page leaves the wiki | `ino-check` |
| "refresh the lens", "the lens doesn't show my new page", "relock the lens" | `lens-refresh` |
| "set up my customisations", "use Rooms in my wiki", and when `waiting.py` names a customisation | `customise` |
| "make a pre-read for…", "a one-pager for…", "brief them before Thursday" | `pre-read` |
| "am I over-reading this", "is this extrapolation" — **and automatically whenever the wiki's analysis sits beside someone else's document** | `source-proportion` |

Published web pages live in `docs/` and are served by GitHub Pages at
`https://dark-matter-labs.github.io/indy-llm-wiki/` (styled with the xCO design system).

**The Axioms Register (`wiki/axioms.md`)** is the living register of the corpus's foundational
assumptions — each with a claim, its logic chain, dependencies, and an honest evidence status
(`evidenced | assumptive | contested`; `assumptive` is legitimate). The `joker` skill reads it to
find the orthodoxy it challenges; the `reflect` skill checks whether the week's work moved an axiom;
keep it in step with [[The Core Assumption Chain]] (the narrative build-out of the same spine).

**The CRM (`wiki/crm/`)** is the relationship layer — contacts and accounts as private entity
pages with a dated interaction log and the `[[link]]` graph as the relationship map; `wiki/crm/roster.md`
is its catalogue. Run the `crm` skill for it. **It is the most sensitive data in the repo and is
ALWAYS `visibility: private`** — never public/unlisted, never published or exported, never in the
shared mirror. Calendar integration is **read-only** (log meetings, pre-meeting briefs) and excludes
personal events; writing to the calendar needs the owner's explicit per-action approval. Never fabricate
relationship state (`unset` when unknown).

If intent is ambiguous, ask **one** short clarifying question, then proceed.
