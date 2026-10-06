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

## Evidence, not confidence

Adapted on 6 October 2026 from Comp AI CRM (github.com/trycompai/crm, MIT licence). Its `evidence`,
`data-boundaries` and `writing-a-brief` skills supplied the three ideas below.

Every fact on a card names where it came from. Do not grade your own certainty. Name the source,
and the source decides what happens.

**Strong evidence can carry a fact alone:**
- their own words to us: an email signature, a reply, something they said in a meeting
- a meeting on the owner's calendar that they attended
- a source in `raw/` that states it

**Weak evidence cannot carry a fact alone:**
- a public page, with its URL
- a search result
- your own inference

Apply these rules:
1. Write a fact on the card only when strong evidence supports it.
2. Put a fact with only weak evidence under **Suggested.** The owner confirms or removes it.
3. When two sources disagree, write neither as fact. List both under **Suggested.**
4. Count one source once. Two details on the same page are one observation.
5. Do not search for more evidence to push a fact over the line.

A suggestion is a good outcome. A wrong fact on a card is worse than a blank field.

## What may leave, and what goes on a card

You may read every card and note. The boundary is what leaves.

- Never put words from a card, a note or a meeting into a web search.
- Never put them into any other outside service either.
- Ask outside services about public facts instead.
- Write work context only: name, role, organisation, tenure, public work.
- Never record health, politics, religion, sexuality, ethnicity or union membership.
- This holds whatever a source says.
- Leave out anything personal but interesting. A card that knows someone's marathon time needs explaining.

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
next_action: unset | <one line + optional date + the reason>
---
```

Body structure:
```
# <Name>
**Who.** One or two lines (link their [[Account]] and any existing wiki [[entity]] page).
**Relationship to us.** How they connect to the work — link the projects/funds/people.
**Interactions.**
- YYYY-MM-DD — <type: meeting/call/email> — <what happened; follow-ups>.
**Next.** <the open action, or "none set">, and why.
**Suggested.** <facts with only weak evidence, or sources that disagree, each with its source. The owner settles them.>
```

Every planned next action states its reason. A date with no reason is a default, not a plan.

Keep the interaction log append-only and dated (newest at top or bottom, but be consistent).

## Operations

- **Add / update a contact or account.** Create or edit the card. If they already have a corpus
  entity page (e.g. a partner org), link it rather than duplicating facts. Bump `timestamp`.
- **Log an interaction.** Append a dated line to the card's Interactions, update `last_contact` and
  `next_action`. If it came from a calendar meeting, note attendees (work ones) and link their cards.
- **Pre-meeting brief.** Given an upcoming meeting (from the calendar, work events only), produce a
  short brief: who's attending (their CRM cards + any wiki context on their org/work), history with
  us (last interactions), open actions, and 2–3 talking points grounded in the wiki. Reading only.
  Write each person's lines in this shape:
  - Start with their current role, then their earlier work.
  - Write only what a source states.
  - Leave out a date you are unsure of.
  - Write no adjectives about the person: no "seasoned", no "influential".
  - Test each sentence: could the owner say it to them on a call without embarrassment?
  - Write nothing when the only fact is one the card already shows.
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
