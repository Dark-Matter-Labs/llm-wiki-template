# LLM Wiki — template

A personal knowledge base that an LLM builds and maintains for you. You bring the sources
and the questions; Claude does the reading, summarising, cross-referencing, and filing.
Over time it becomes a compounding store of knowledge that answers questions your raw
documents never could on their own.

**This is a template repo.** It has the structure, the skills, the tools, the CI gates and
the scheduled jobs — and no content. Click **Use this template** to create a wiki, then
follow **[SETUP.md](SETUP.md)**.

Built on the [LLM-Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
(Karpathy, 2026), with role-based skills inspired by [gstack](https://github.com/garrytan/gstack).

---

## The loop

The whole thing is one loop, and it works from a browser with no terminal:

**say what you want → Claude works → you review and merge a pull request.**

Every change arrives as a PR with a plain-language summary. That's the oversight step:
nothing enters the wiki, and nothing gets published, without a human merge.

### Things you can say

| You want to…                     | Just say something like…                               |
| -------------------------------- | ------------------------------------------------------ |
| Add a document to the wiki       | "Add this report to the wiki" (with the file in `raw/`) |
| Ask what the wiki knows          | "What does the wiki say about outcomes-based financing?" |
| Compare things                   | "Compare how Lisbon and Tallinn approached this"       |
| Get caught up                    | "Catch me up on what's new"                            |
| Health-check the wiki            | "Check the wiki and tell me what's stale or missing"   |
| Think through a new idea         | "I've got a new concept note — push back on it"        |
| Check something before sharing   | "Is this page ready to publish?"                       |
| Have your position challenged    | "Challenge this" / "what's the counterposition?"       |
| See how your thinking moved      | "Run the weekly reflection" / "what deviated this week?" |
| Measure a new document against the wiki | "Run a delta on this"                           |
| Track people and meetings        | "Log that meeting" / "prep me for my meeting with…"    |
| Turn a habit into a skill        | "Make that a skill" (it asks you to confirm first)     |

You never need to know the folder layout or run anything.

---

## Four visibility tiers

Every page carries a `visibility`, and **everything starts `private`**:

| Tier | Reaches |
| --- | --- |
| `private` | nothing — never leaves the repo, not even its title |
| `internal` | the colleague mirror only — **never the open web** |
| `unlisted` | mirror + the public site, unindexed and unlinked |
| `public` | mirror + the public site, linked and indexed |

To publish, say *"make this public"* — Claude runs a publish-check and opens a PR. **The
page goes live only once you merge it.**

Two boundaries are enforced in code and proven by tests on every push: private content
never reaches the mirror, and neither private nor internal content reaches the web. A
failing test blocks publication.

⚠ **`visibility` controls publishing, not access.** GitHub read access is per-repository —
anyone who can open the repo reads everything in it, private pages included. Read
**[SHARING-AND-ACCESS.md](SHARING-AND-ACCESS.md)** before your first sensitive ingest.

---

## Skills

Each skill is a role Claude plays. They live in `.claude/skills/` as plain markdown —
nothing to install.

| Skill            | Role                | What it does |
| ---------------- | ------------------- | ------------ |
| `ingest`         | Librarian           | Reads a new source, writes a summary, and updates every affected page across the wiki. |
| `query`          | Researcher          | Answers a question from the wiki with citations; files good answers back as new pages. |
| `lint`           | Editor              | Health-checks the wiki: contradictions, stale claims, orphans, gaps, duplicates. |
| `brief`          | Chief of staff      | A two-minute catch-up on what's new and what's worth doing next. |
| `office-hours`   | Thinking partner    | Interrogates a new idea before you commit — reframes it, challenges premises. |
| `publish-check`  | Fact-checker        | Verifies a page is sourced and honest (and its tier fits) before it's shared. |
| `publish-web`    | Web publisher       | Turns a page into a styled, shareable web page on the site. |
| `joker`          | Rival thinker       | Steelmans a genuinely different set of assumptions against your position. |
| `reflect`        | Weekly reflector    | Writes the Friday reflection: how the thinking deviated, signals, corrections. |
| `metacognition`  | Coach               | Names how you actually work with the tool and where the loop costs you. |
| `gravity`        | Cartographer        | Where the corpus's centre of mass sits, and which way it's moving. |
| `learn`          | Apprentice          | Turns a recurring pattern into a new skill — after you confirm it. |
| `delta`          | Surveyor            | Measures an incoming document against the wiki's position — agrees, extends, diverges, or contradicts. Informs; never auto-merges. |
| `crm`            | Relationship keeper | Contacts, accounts, and a dated interaction log. **Always private.** |

Add your own: copy an existing `SKILL.md`, change the `name` and `description`, describe
the workflow. Claude picks it up automatically — or say *"make that a skill"* and it drafts
one for you to confirm.

---

## What's in the repo

- **`raw/`** — your source documents. Read-only. The source of truth.
- **`wiki/`** — the pages Claude writes and maintains.
  - `index.md` — the catalogue (Claude's routing file for questions)
  - `overview.md` — the big-picture map
  - `axioms.md` — the register of foundational assumptions, with honest evidence statuses
  - `log.md` — index to the dated record; entries live in `log/YYYY-MM.md`, one per month
- **`.claude/skills/`** — the 14 workflows above.
- **`tools/`** — stdlib-only helpers: exporter, boundary tests, leak scanner, search.
- **`.github/workflows/`** — export graph, shared mirror, Pages deploy, Friday reflection.
- **`docs/`** — the published site (GitHub Pages) and its stylesheets.
- **`CLAUDE.md`** — the constitution that makes Claude a careful librarian rather than a
  generic chatbot. It reads this at the start of every session.

A worked example ships in `wiki/examples/` and `raw/EXAMPLE-sample-source.md` so you can
see what a finished ingest looks like. Say *"delete the example files"* once you have real
content.

---

## Automation

| Workflow | Trigger | Cost |
| --- | --- | --- |
| `export.yml` | push to `main` touching the wiki | free — deterministic, no LLM |
| `export-shared.yml` | same | free |
| `deploy-pages.yml` | push touching `docs/` | free |
| `weekly-reflect.yml` | Fridays 15:00 UTC + on demand | **Claude API credits, billed outside your plan** |

The three export/deploy jobs are plain Python and never call a model. Only the weekly
reflection does. Delete its `schedule:` block to make reflections manual-only.

---

## Credit

Pattern: Andrej Karpathy's LLM-Wiki gist. Skill structure inspired by Garry Tan's gstack.

**Fixing something small yourself?** You don't need Claude for a typo — see **[EDITING.md](EDITING.md)** for the thirty-second browser edit, and for the short list of files that are computed rather than written and shouldn't be hand-edited.
