---
name: crm
description: Maintain and query the wiki-native CRM — contacts (partners, funders, talent, network) and the organisations/accounts they belong to, as private entity pages with a dated interaction log and a relationship graph. Use when the owner says "add a contact", "log that meeting", "who do we know at X", "who haven't we spoken to", "show the funder pipeline", "prep me for my meeting with…", or wants relationship/network management. Read-only calendar integration (log meetings, pre-meeting briefs) is available and filters out personal events. The CRM is ALWAYS private and never published.
---

# CRM — relationships as a private layer of the wiki

The CRM reuses the wiki's own machinery — entity pages, the `[[link]]` graph, dated logs — pointed
at **people and organisations**. Contacts and accounts are private entity pages under `wiki/crm/`;
relationships are wiki-links; interactions are a dated log on each card; the `query`/`brief` patterns
answer pipeline and network questions.

## Hard rules (read first — this is the most sensitive data in the repo)

- **Everything in `wiki/crm/` is `visibility: private`, always.** Never `public`/`unlisted`, never
  published to `docs/`, never in the shared mirror. Private pages are already stripped from every
  export and the leak scanner only touches public surfaces, so private is the protection — keep it.
- **Real people's data.** Keep notes factual and professional (they may be subject-access-requestable
  under GDPR). No speculation about individuals, no sensitive personal characteristics. If a note
  wouldn't be fine for the person to read, don't write it.
- **Never fabricate relationship state.** If you don't know a stage, owner, or last-contact date,
  set it to `unset` — do not invent it. Mark anything inferred as inferred.
- **Calendar is read-only by default.** Reading events to log meetings / build briefs is fine.
  Creating, editing, or sending calendar invites is a permission-required action — propose it and
  wait for the owner's explicit yes each time; never auto-write.
- **Personal calendar events stay out.** the owner's calendar mixes work and personal/family events.
  Only ever record work/relationship-relevant events; never copy personal event content into the wiki.

## Card conventions

**Contact** (a person) → `wiki/crm/contacts/<slug>.md`, **Account** (an org) → `wiki/crm/accounts/<slug>.md`.
Both are `type: entity`, `visibility: private`, with CRM fields in frontmatter:

```yaml
---
type: entity
title: <Full name / Org name>
description: <one line — who they are and why they matter to us>
tags: [crm, contact | account, <category>]
status: draft
visibility: private
confidence: <high|medium|low>
timestamp: <YYYY-MM-DD>          # last time this card was updated
sources: []                     # cite raw/ if the card is backed by a source; else []
crm_category: partner | funder | talent | network | other
crm_org: "<their organisation>"  # contacts only; link the [[Account]] in the body
crm_stage: unset | prospect | active | dormant | committed | closed
crm_owner: unset | <who at DM owns this relationship>
last_contact: unset | <YYYY-MM-DD>
next_action: unset | <one line + optional date>
---
```

Body structure:
```
# <Name>
**Who.** One or two lines (link their [[Account]] and any existing wiki [[entity]] page).
**Relationship to us.** How they connect to the work — link the projects/funds/people.
**Interactions.**
- YYYY-MM-DD — <type: meeting/call/email> — <what happened; follow-ups>.
**Next.** <the open action, or "none set">.
```

Keep the interaction log append-only and dated (newest at top or bottom, but be consistent).

## Operations

- **Add / update a contact or account.** Create or edit the card. If they already have a corpus
  entity page (e.g. a partner org), link it rather than duplicating facts. Bump `timestamp`.
- **Log an interaction.** Append a dated line to the card's Interactions, update `last_contact` and
  `next_action`. If it came from a calendar meeting, note attendees (work ones) and link their cards.
- **Pre-meeting brief.** Given an upcoming meeting (from the calendar, work events only), produce a
  short brief: who's attending (their CRM cards + any wiki context on their org/work), history with
  us (last interactions), open actions, and 2–3 talking points grounded in the wiki. Reading only.
- **Pipeline / network queries.** Answer from the cards: "funder pipeline by stage", "who's dormant
  (no contact in N months)", "who do we know at org X", "everyone the owner co-authored with".
  Read `wiki/crm/roster.md` first (the catalogue), then drill into cards.
- **Calendar sync (read-only).** Use the Google Calendar tools (`list_events` / `search_events` on
  the relevant calendar) to find work meetings, **filter out personal/family events**, and propose
  interaction log entries + new contact cards for external attendees — The owner approves each.

## Bookkeeping
- Update `wiki/crm/roster.md` (the private catalogue) when you add a contact/account.
- Append to the current month's log file (`wiki/log/YYYY-MM.md`; see `wiki/log.md`): `## [YYYY-MM-DD] crm | <what changed>` (e.g. "logged 2 meetings, +1 contact").
- The main `wiki/index.md` links the CRM once (via the roster); do not list every contact there —
  the roster is the CRM's own index, and it stays private.

## Never
- Never publish, export, or share any CRM page. Never write to the calendar without explicit per-action approval. Never fabricate relationship data. Never record personal (non-work) calendar content.
