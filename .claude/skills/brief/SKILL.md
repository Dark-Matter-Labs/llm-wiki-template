---
name: brief
description: Produce a catch-up briefing from the wiki. Use when the owner says "catch me up", "what's new", "weekly summary", "what changed", or wants a digest of recent activity and open threads. Reads the log and recently-changed pages and writes a short, plain-language briefing.
---

# Brief

A standing "chief of staff" digest. Turns the wiki's recent activity into something the owner
can read in two minutes.

In a commons, assume two audiences rather than one. Some members read **only** this repo, so a
brief is often the whole of what they see of a week's work — including anything that came down
from the centre. Write it so it stands on its own for someone who has not been in the sessions.

## Steps

1. **Read the log** — today's day file first (`wiki/log/YYYY-MM-DD.md`), then walk back
   through the month index (`wiki/log/YYYY-MM.md`; format at `wiki/log.md`). Focus on entries
   since the last brief (or the last 1–2 weeks if unclear). The `## [date]` prefixes make this
   easy to bound.

2. **Look at what changed.** Identify the pages touched by recent ingests and the
   questions asked in recent queries. Pull the substance, not the file activity.

3. **Read `wiki/overview.md` and any active `synthesis` pages** to frame what's new
   against the bigger picture.

4. **Write the briefing.** Keep it tight and plain-language:
   - **What came in** — new sources ingested and the one thing each changed.
   - **What we now know that we didn't** — genuine shifts in the synthesis.
   - **Open threads** — contradictions flagged, coverage gaps, `confidence: low` pages
     that newer sources could firm up.
   - **Suggested next moves** — sources worth finding, questions worth asking. (You're
     good at proposing the next question — do it here.)

5. **Optionally file it** as `wiki/briefs/<date>-brief.md` if a record is wanted. Ask. If filed,
   give it `visibility: private` in a personal wiki, or `internal` in a commons so the other
   members can read it. Add it to the index and log it in today's day file.

## Rules
- This is a read-and-synthesise pass. Don't ingest or restructure here.
- Ground every claim in the wiki; separate fact from your suggestions.
- Two minutes to read. Ruthlessly brief.
