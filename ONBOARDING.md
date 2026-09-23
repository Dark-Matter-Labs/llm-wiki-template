# Start here

This is **your** wiki. You will not need a terminal, you will not need to learn git, and you
will not need anyone to walk you through it.

That last part is the test. **If this page can't get you to a first real contribution on its
own, the system has failed, not you** — so please note anywhere you get stuck. That is the
most useful thing you can send back.

About an hour, most of it reading.

---

## What this is, in one paragraph

A **living wiki**: a few hundred interlinked markdown pages. You bring sources and questions;
**Claude does the reading, summarising, cross-referencing and filing.** It is not a chatbot
answering over a folder — it is a maintained artifact that gets richer every time anyone adds
to it. The pattern is Andrej Karpathy's *LLM-Wiki*.

**The loop:** say what you want in plain English → Claude does the work and proposes a change
→ you read the summary and approve it. Nothing enters the record without a person saying yes.

---

## Before you start

You need two things, and no more:

1. **A GitHub account** with access to this repository. If you can read this file on
   github.com, you have it.
2. **Claude Code**, at **[claude.ai/code](https://claude.ai/code)** — open it in a browser,
   pick this repository, and type. There is nothing to install.

Three words you will meet, and then never have to think about again:

- **Repository** (or "repo") — the folder this wiki lives in.
- **Pull request** (or "PR") — a proposed change, shown as a before-and-after, that does
  nothing until someone clicks Merge. This is the undo button; it is why you cannot break
  anything.
- **Merge** — accepting the proposal. This is the only irreversible-feeling button, and it
  isn't: every merge can be reverted on its own. **You won't usually press it yourself.** When
  Claude finishes a piece of work in your own wiki, it tells you what changed and asks *"Shall I
  merge this?"* Say yes and it merges. Say no, or say nothing, and the work waits safely.

---

## Your first ten minutes

Open [claude.ai/code](https://claude.ai/code), pick this repository, and type one of these:

> *"Catch me up."*
> *"What does this wiki say about \<something you care about\>?"*
> *"What's in here?"*

Read the answer. Notice that every factual claim names the source it came from, and that
anything Claude worked out itself is labelled as its own reasoning rather than dressed up as
a fact. That distinction is the point of the whole thing.

You have now used it. Everything below is detail.

---

## Adding your first document

Pick something of yours that isn't in here yet — a paper, a concept note, a deck, meeting
notes. Then choose whichever of these suits the document:

**Paste it.** For anything you can copy: paste it into the chat and say *"please add this to
the wiki."* Simplest, and works for most things.

**Upload it.** For a PDF or a Word file, put it in the `raw/` folder through the browser:

1. Open the `raw/` folder on github.com.
2. **Add file → Upload files** (top right).
3. Drag the file in.
4. Under *Commit changes*, choose **"Create a new branch for this commit and start a pull
   request"**, then **Propose changes** → **Create pull request** → **Merge**.
5. Tell Claude: *"I've added `raw/<filename>` — please ingest it."*

**Point at it.** If it's a public web page, just give Claude the link.

Claude will read it, tell you the takeaways in plain language, **ask you which visibility
tier applies** (see below — say `private` if you are unsure), write a summary page, and update
every existing page your document touches. A single source normally touches five to fifteen
pages; that bookkeeping is the part that would rot if a person had to do it.

Then it opens a pull request and tells you, in plain words, what it learned. Read that, check
the new page reads correctly, and when Claude asks *"Shall I merge this?"*, say yes. You don't
need to find anything on github.com. (In a shared commons it stops at the pull request instead,
because there a second person reviews it.)

Now ask: *"What does the wiki now say about \<a topic your document covered\>?"* and watch your
contribution come back in the answer. That is the compounding effect, live.

---

## What's yours, and what's shared

Everything here is yours until you deliberately share it. Every page carries a **visibility**
tier, and there are four:

| tier | where it can go |
| --- | --- |
| **`private`** | Never leaves this repository. Not exported, not published, not shared — not the body, not the title, not links pointing to it. **This is the default.** |
| **`internal`** | Shared with trusted colleagues through the team wiki. Never on the open web. This is the ordinary tier for working knowledge. |
| **`unlisted`** | On the website, but not indexed and not linked from anywhere. Reachable only by direct link. |
| **`public`** | Publishable to the open web. |

A page only reaches the team wiki if you ask Claude to **contribute** it, and even then it
arrives there as a pull request someone else reviews. Nothing travels by accident.

**One honest caveat.** This repository sits in the Dark Matter Labs organisation, so org
owners can technically read it — GitHub grants access per repository, not per page. `private`
here means *not shared, not published, not exported*. It does not mean hidden from DM.
Anything that needs that should not live here.

---

## Asking for what you want

Claude plays roles — short job descriptions kept in `.claude/skills/`. You never name them;
you just say what you want and the right one fires.

| You say something like… | What happens |
| --- | --- |
| "Add this report" | reads the source, writes a summary, updates every affected page |
| "What does the wiki say about…?" | answers with citations, and files a good answer back |
| "Catch me up" | a short digest of what's new |
| "Check the wiki / what's stale?" | health check: contradictions, orphans, broken links |
| "Help me think about this idea" | interrogates a new idea before you commit to it |
| "Challenge this" | builds the strongest *rival* position to our own |
| "Where does this document sit relative to us?" | measures agreement, extension, divergence, contradiction |
| "What patterns are emerging?" | groups the wiki keeps forming that nobody has named |
| "Share this with the team" | stages a sanitised contribution to the team wiki |
| "What's waiting for me?" | lists work that was written and never merged, so nothing is forgotten |
| "Is this ready to publish?" | checks sourcing and visibility before anything ships |

There are more than these. Ask *"what can you do?"* and Claude will tell you.

---

## Fixing small things yourself

You do not need Claude to fix a typo. **`EDITING.md`** is the thirty-second guide: click the
pencil icon on any page, make the change, propose it, merge it.

The line between "do it yourself" and "ask Claude" is **blast radius, not effort**. A typo is
one file. Renaming a page is every page that links to it.

---

## What you cannot break

- **Nothing merges without automatic checks passing.** Spelling, broken links, missing
  fields, hand-typed numbers that should be computed — all refused before they land.
- **Every change is its own pull request**, so any one of them can be reverted alone.
- **Nothing is ever deleted to tidy up.** Pages that retire are marked `dormant` and stay
  readable at the same address.
- **Source documents in `raw/` are never edited.** A report that said something is the record
  of what it said.

If a check goes red, `EDITING.md` has a table of the common ones. Or close the pull request
and ask Claude. Nothing is lost either way.

---

## Two things only a person can do

**Standing behind a page.** `validation` records *who has confirmed a page* — `machine`
(nobody yet, the honest default), `self` (you did), `peer`, `collective`. Claude may set
`machine` and propose `self`; it can **never** award `peer` or `collective`, because a model
granting those would make the ladder meaningless.

It takes three lines, and the third is the one people forget:

```yaml
validation: self
validated_by: [Your Name]
validated_at: 2026-09-16
```

Without the date the confirmation is invisible. Every read-out counts validation **by its
date**, so a page confirmed without one is standing behind nothing as far as the system can
tell. Ask Claude "what should I stand behind?" and it will name a few candidates; it will
never do this part for you.

**Settling a disagreement.** When two pages genuinely conflict, Claude declares it and stops.
Which one wins is a judgement, and judgements belong to people.

---

## When you get stuck

Say *"I don't understand"* to Claude at any point — it will explain in plain language and
adjust. It knows the rules of this wiki; they are written down in `CLAUDE.md` and it reads
them at the start of every session.

And tell us where this page failed you. Where did you have to guess? What did you want to ask
a human? What did Claude do that surprised you, well or badly? Those notes go straight back
into this file and into the rules — the system is meant to learn from its own onboarding.

Welcome aboard.
