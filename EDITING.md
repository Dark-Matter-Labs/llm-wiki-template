# Editing the wiki yourself

You don't need Claude to fix a typo. This is how to make small corrections directly from
your browser — no terminal, no chat, about thirty seconds each.

The safety net is the same one Claude works under: nothing you do here can break the wiki
silently. Every change goes through a pull request, and a set of automatic checks runs
before you merge. If something is wrong, the checks say so and nothing lands.

---

## When to edit yourself, and when to ask Claude

**Edit it yourself** — typos, a wrong date, a broken sentence, a tag, tightening a
description, changing `status: draft` to `reviewed`, correcting a fact you know is wrong.

**Ask Claude** — anything that touches more than one page. Adding a source, creating a
page, renaming a page, moving something between sections, changing a page's `visibility`.
A single source normally touches 5–15 pages, and the bookkeeping that keeps the wiki
navigable is the part that quietly rots when it's skipped.

The line is not effort, it's **blast radius**. A typo is one file. A rename is every page
that links to it.

---

## The thirty-second edit

1. Open the page on GitHub — either from a link Claude gave you, or by browsing to it.
2. Click the **pencil icon** (top right of the file).
3. Make your change.
4. Click **Commit changes…**.
5. Choose **"Create a new branch for this commit and start a pull request"** — this is
   already the default. Leave the branch name as it is.
6. Click **Propose changes**, then **Create pull request**.
7. Wait about twenty seconds for the checks to go green, then **Merge pull request**.

That's it. Step 5 is the only one worth remembering: it's what gives you the checks and
the undo.

### Changing several files at once

Press **`.`** (a full stop) on any page of the repository. A full editor opens in your
browser at `github.dev`. Edit as many files as you like, then use the source-control panel
on the left to commit to a new branch and open a pull request.

---

## If a check goes red

Click **Details** next to the failing check. The message says what's wrong and usually
exactly how to fix it. The ones you're most likely to meet:

| Check | What it means | Fix |
|---|---|---|
| **House rules** | The house spells civilization with a **z** and writes **xCO** — lowercase x, uppercase CO. The check names the file and line. | Correct the spelling or the casing |
| **Schema + link integrity** | A `[[Wiki Link]]` points at a page that doesn't exist, or frontmatter is missing a field | Fix the link, or add the field |
| **Index counts match the corpus** | A number in `wiki/index.md` was typed | See below — don't hand-edit these |
| **Log index matches the day files** | `wiki/log/2026-08.md` was edited directly | See below |

You can also just close the pull request and ask Claude. Nothing is lost.

### Things not to hand-edit

Some files are **computed from the wiki**, not written. Editing them is the one way to
make a mess that looks fine and isn't, so the checks refuse it:

- the counts in `wiki/index.md` (`## Concepts (156)`, the header total)
- the month indexes at `wiki/log/2026-08.md`
- anything in `export/`
- `docs/assets/xco-tokens.css`

If one of these is wrong, the *source* is wrong. Tell Claude what looks off and it will
regenerate them — nothing derived is ever typed by hand.

And **never edit anything in `raw/`.** Those are the source documents, and they are
immutable on purpose: a report that said something is the record of what it said. If a
source is wrong, that fact belongs on the wiki page about it, not in the source.

---

## Two things worth knowing about the frontmatter

The block at the top of every page between `---` lines is the frontmatter. Two fields there
are load-bearing:

**`visibility`** decides where a page can go — `public`, `unlisted`, `internal`, `private`.
Changing it changes what leaves the repository. It's safe to move a page *down* (towards
private) yourself; moving one *up* is worth doing with Claude, which will run the
publish check first.

**`validation`** records *who has stood behind the page* — `machine` (nobody yet), `self`
(you did), `peer`, `collective`. It is not a measure of how good the page is; that's
`confidence`. Setting your own pages to `self` when you've read and agreed with them is
useful and correct — add `validated_by: [your name]` alongside it. This is one of the few
things only a person can do: Claude may propose `self` but can never award `peer` or
`collective`, because a model granting them would make the whole ladder meaningless.

---

## What you can't break

- Nothing merges without the checks passing.
- Every change is a separate pull request, so any one of them can be reverted on its own.
- Nothing is ever deleted to tidy up. Pages that retire are marked `dormant` and stay
  readable at the same address.
