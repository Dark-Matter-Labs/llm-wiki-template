---
name: customise
description: Set up the customisations this wiki asked for in INO Home, one at a time, with this wiki's own content. Use when the owner says "set up my customisations", "set up what I asked for in INO Home", "use Rooms in my wiki", "add hunches to my wiki", or when tools/waiting.py names a customisation not set up yet. Reads design/customisations.json. Never copies another wiki's content.
---

# Set up a customisation

## Why this exists

INO Home has a Customise page at `https://ino-home.vercel.app/#/customise`. It lists what people have added to
their own wikis: Robyn's rooms, Prateek's glossary, the xCO team's hunches, and more. Each one has a button,
"Use this in my wiki".

That button only records the request. It opens a proposed change that adds an entry to
`design/customisations.json` in the person's wiki. Nothing set the customisation up. This skill does.

Built 26 October 2026, at Gurden's request, so the gallery's main button leads somewhere.

## What travels, and what does not

The idea travels. The content does not. A wiki that asks for Rooms gets rooms of its own, agreed with its owner.
It never gets Robyn's rooms.

## Method

1. **Read the requests.** Open `design/customisations.json`. List the entries whose `state` is `wanted`.
   - If the file is missing or nothing is wanted, say so in one line and stop.
   - Each entry carries `id`, `name`, `started_in`, `setup`, `asked_by` and `asked_at`.
2. **Pick one.** If there are several, name them and ask which to set up first. Set up one per proposed change.
3. **Learn the shape from this wiki's own files.** The lens is shared, so every wiki holds every switch.
   - Read `design/lens/SPEC.md` first.
   - If SPEC.md does not cover it, read how `design/lens/lens.html` and `tools/build_lens.py` use the setting.
   - Never open the other wiki's settings, pages or data files to copy them.
4. **Ask the owner what only they know.** Use the table below. Ask one question at a time.
   - Where a sensible default exists, take it and say which default in one line.
5. **Build it from this wiki's own pages.** Work in a draft, never on main.
   - Anchor every item to a page in this wiki: a hunch, a glossary term, a figure, a key document.
   - An item drawn from a `private` page stays out of any file that colleagues can read.
   - Lens switches and names go in `design/lens/settings.json`. That file is this wiki's own.
6. **Mark it done.** In `design/customisations.json`, change the entry's `state` to `done`.
   Add `done_at` (the date) and `done_by` ("Claude for <owner>"). Keep the entry. Never delete it.
7. **Check before sending.** Follow `.claude/rules/pushing.md`: regenerate, run `python3 tools/gates.py`, push once.
8. **Log it.** Append `## [YYYY-MM-DD] rebuild | customisation: <name>` to today's log file.
   Then run `python3 tools/sync_log_index.py`.
9. **Propose it.** Say what a reader will now find, in plain words. Then ask: "Shall I merge this? That saves it into
   your wiki."
10. **Offer one next step.** If the change touched the lens, offer `lens-refresh`. The lens shows it only after a
    rebuild and lock. INO Home shows most customisations as soon as the change is saved.

## What each one needs from the owner

| Customisation | Ask the owner | Then |
|---|---|---|
| Hunches | Which pages hold the open routes? | Write `design/lens/hunches.json`, each hunch anchored to its page. |
| Key terms | Nothing. Offer the ten most-linked concepts as a start. | Write `wiki/glossary.md`, one `### Term` each, ending `See [[page]]`. |
| Checked against sources | Which pages do people rely on most? | Run the `cross-check` skill on those pages. |
| Figures on source summaries | Which sources carry their argument in a diagram? | Capture the figures into `design/lens/figures/`, listed in `figures.json`. |
| Published pages elsewhere | Which pages are on other sites? | List them in `design/lens/external-pages.json`. Never a password or a private link. |
| Links colleagues shared | Which channels? | Stop if this chat cannot read them. Say what access is needed. |
| Your own colour and words | The colour, and the words for who stood behind a page. | Set the accents and `validation_names` in the lens settings. |
| Goals by layer | Nothing. Read the goal pages. | Give each goal a `goal_layer` and a `horizon`. Ask where one is unclear. |
| xCO's portfolio | Which of xCO's entries does this wiki hold a page on? | Point each entry in `design/lens/portfolio.json` at this wiki's page. |
| Rooms | The rooms: a name, a line on each, the words that place a page there. | Add them to the lens settings and switch `rooms` on. |
| Focus switch | Which rooms make up each area of work? | Needs Rooms first. Then switch `focus_bar` on. |
| Your commitments, triaged | Which page holds the open commitments? | Point the lens's commitments box at that page. |
| Dashboard front door | The key documents, and the parts of the work. | List them in the lens settings. |
| Library | Who wrote each source, by tag? | Map the source tags to authors in the lens settings. |
| Your own shelves | Which tags, kinds or titles go on each shelf? | Write the shelf rules in the lens settings. |

For a customisation not in this table, follow the entry's own `setup` line.

## Declined, or not possible

- The owner may decide against it. Set `state` to `declined`, with the date. A declined request is not a failure.
- If this wiki cannot hold it yet, set `state` to `waiting`. Add `why` in one plain sentence.
  For example: "Needs Rooms first." Or: "This chat cannot read the team's channels."

## Hard rules

- **Never copy another wiki's content.** Not its rooms, terms, hunches, figures or settings values.
  `started_in` names where the idea started. It is not a source.
- **Never read another wiki's `design/lens/settings.json`.** It holds pages kept from colleagues, and links that work
  like passwords.
- **One customisation per proposed change.** Each one can then be saved or undone on its own.
- **Never mark a request done that was not set up.** A half-done one stays `wanted`, with a `why`.
- **Shared files stay shared.** Never edit `design/lens/lens.html` or `tools/build_lens.py` for one wiki. A change
  every wiki needs is made in the source wiki and delivered with `tools/deliver_shared.py`.
- **Never handle a lens password.** Locking the lens is `lens-refresh`, and the owner types the password.

## Connections

- INO Home's Customise page, which writes `design/customisations.json`.
- `tools/waiting.py`, which names requests not set up yet.
- `design/lens/SPEC.md`: what each lens setting does.
- `lens-refresh`, `cross-check`, `.claude/rules/pushing.md`, `.claude/rules/finishing.md`.
