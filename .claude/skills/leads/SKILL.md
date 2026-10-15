---
name: leads
description: "Lead finding: suggests organisations worth approaching for a goal or need, each with the reason, the source and whether a warm route exists, and creates a private prospect card only on a yes. Fires on \"find leads\", \"lead generation\", \"who should we approach about X\", \"who funds X\", \"build a prospect list for X\", \"who else should be in this pipeline\". Never contacts anyone; drafts a message only when asked, and never sends it."
---

# Leads: who is worth approaching, and why

The CRM records relationships. This skill finds the ones not yet started. It is lead generation
the wiki's way: every suggestion names its reason and its source, weak evidence stays a suggestion,
and a person decides.

## Hard rules

- **Personal wikis only.** If `design/federation.json` says `role: commons`, stop and say that lead
  finding happens in a personal wiki, because contacts never live in a shared one. `tools/crm.py`
  refuses there too.
- **The `crm` skill's rules all apply.** Read its hard rules first. Prospect cards are
  `visibility: private`, always.
- **Never contact anyone.** Drafting a message is fine when the person asks for one; sending it is
  theirs to do, from their own email.
- **Never put card or note text into a web search.** Search for public facts about the organisation
  and the goal instead.
- **Organisations first.** Suggest organisations, and roles within them. Name a person only when a
  public source names them in that role, and put it under Suggested on the card.
- **No scoring of people.** Rank by fit to the goal and by evidence, never by a person's influence.
- **Only the owner's own CRM.** Never look in a colleague's wiki for routes. In a commons, there is
  no CRM to search.

## Method

1. **Start from a need.** A goal, a position, a funding gap or a question. If the person gave none,
   ask one question: "For which goal or need?" Read the wiki's page for it, so every suggestion can
   cite why it fits.
2. **Inside out: what the wiki already knows.**
   - `python3 tools/crm.py leads --json` lists organisations the wiki has pages for but no card,
     most linked-to first. Keep those whose page fits the need.
   - Where it exists, `python3 tools/luck_candidates.py --json` lists goals nobody backs yet, which
     are needs worth a lead.
3. **Outside in: public research, optional.** Search for organisations working on the need: funders,
   operators, public bodies, partners. Use only public sources, keep each URL, and treat what you
   find as weak evidence.
4. **Check for a route.** Look in the owner's own CRM for a card that links the organisation or works
   there. A warm route is worth more than a cold approach; say who holds it.
5. **Shortlist five or fewer.** For each: the organisation, why it fits (with the wiki page or URL),
   warm or cold and through whom, and one suggested first step with a reason. Say plainly when the
   evidence is thin.
6. **On a yes, create the card.** Write `wiki/crm/accounts/<slug>.md` from the crm card template with
   `crm_stage: prospect`, `crm_owner` only if the person names one, and a `crm_source:` line saying
   where the lead came from (`wiki`, `research` or `introduction`). Public facts go under
   **Suggested** with their URLs. Then set the first step with
   `python3 tools/crm.py log <card> --kind note --note "Added as a lead for <need>" --next "<step>" --due <date> --why "<reason>"`.
7. **Bookkeeping.** Update `wiki/crm/roster.md` and append `## [YYYY-MM-DD] crm | leads for <need>: +N prospects`
   to today's log file.

## Output

A short list in chat, then the question "Shall I add any of these as prospects?" Nothing is written
before a yes.
