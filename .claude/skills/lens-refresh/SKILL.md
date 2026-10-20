---
name: lens-refresh
description: Rebuild this wiki's lens from its own settings, have the owner lock it again, propose the locked page, and say in plain words what changed. Use when the owner says "refresh the lens", "update the lens", "rebuild the lens", "the lens doesn't show my new page", "put today's changes in the lens" or "relock the lens". Works in any wiki that has a lens. Claude never handles the password.
---

# Refresh the lens

## Why this exists

The lens is a locked reading view of a wiki, at `https://dark-matter-labs.github.io/<wiki>/lens/`.
It is a copy built at one moment. A saved change shows in it only after the next rebuild and lock.

By 20 October 2026, six wikis held 214 lens entries in their logs. Prateek's wiki alone had 23 relock changes.
The same steps kept going wrong in the same places:

- A rebuild from a session holding a different password locked readers out, four times in two days.
- A rebuild from an old draft left recent pages out of the lens.
- A system-wide lens update copied shared files over two days of Prateek's own work.

Generalised from Prateek's `lens-update` and xco-team-wiki's `lens-deployment-workflow`. Gurden verified the
pattern on 20 October 2026.

## Method

1. **Check this wiki has a lens.** It has one when `design/lens/settings.json` exists. If it does not, say so in
   one line and stop. Setting up a lens is separate work.
2. **Check the wiki folder is up to date.** Run `git status`, then `git fetch` and count how far behind main it is.
   - If the folder is on an old draft, the lens will miss recent pages. Build from main instead.
   - If another chat is working in the folder, or there are changes you did not make, use a separate worktree.
   - Never set aside or discard someone else's changes to make room.
3. **Build it:** `python3 tools/build_lens.py --by "Claude for <owner>"`.
   - Use the owner's name as the breadcrumb shows it. A person who builds it themselves uses their own name.
   - If this wiki's lens also reads other wikis, use the same `--also "Name=path/to/wiki"` as last time.
     This wiki's own lens skill or the last `rebuild` log entry says which.
   - Every build runs a privacy check. If it stops, report the problem in plain words and stop. Never work round it.
4. **Find what changed.** Compare the wiki with the last time the lens was saved:
   `git log -1 --format=%H -- docs/lens/index.html`, then list the pages added or changed in `wiki/` since then.
   Add the build's own counts: pages in the lens, and pages held back as private.
5. **Hand the lock to the person who holds the password.** Give them this command to run on their own computer:
   `LENS_PASSWORD='…' node tools/encrypt_lens.mjs export/lens.html docs/lens/index.html`
   - They type the password in place of `…`. You never see it.
   - An owner with no terminal asks the maintainer who holds the lens password to run it.
   - To keep it out of their shell history, they can run `read -rs LENS_PASSWORD && export LENS_PASSWORD` first,
     then the command without the `LENS_PASSWORD='…'` part.
   - The lock refuses a password that does not open the live page. That means a wrong password, not a fault.
     Ask them to try the one in their password manager.
   - Only `--new-password` changes the password. Offer it only when they ask to change it. Then remind them to
     tell everyone who reads the lens.
   - A second lens with its own password is set in `lock.others` in the settings. It has its own variable, for
     example `LAB_LENS_PASSWORD`, and its own output folder. Never lock it with the wiki's own password.
6. **Check the locked page.** After they say it is locked:
   - `docs/lens/index.html` must contain `var SALT =`. That shows it is the locked page.
   - Pick the slug of a known page from `wiki/` and grep `docs/lens/index.html` for it. It must find nothing.
     A hit means page text shows through. Stop and say so.
7. **Propose it.** Make a draft holding `docs/lens/index.html` and nothing else. Push it and open a proposed change.
   Saving that file is what makes the site update. Changes to settings or the builder alone do not.
8. **Say what changed,** in plain words (below). Then ask: "Shall I merge this? That saves it into your wiki."
9. **After it is saved, confirm the live page matches.** Wait a minute or two, then compare
   `curl -s <lens URL> | shasum -a 256` with `shasum -a 256 docs/lens/index.html` on main. Say whether they match.

## Output

Lead with what a reader of the lens will now find. For example:

> The lens now holds 412 pages, 6 more than last time. New: <page title>, <page title>.
> Changed: <page title>. 38 pages stay out as private. The password is unchanged.

- Name new and changed pages by title, in the chat with the owner only.
- In the proposed change's description, give counts only. Never name a private page there.
- Say whether the password changed. Say if any step was skipped, and why.

## Hard rules

- **Claude never asks for, types, stores or repeats a password.** Not in a command, a file, a log, a commit or a reply.
  If someone pastes one into the chat, do not use it or repeat it. Suggest they change it with `--new-password`.
- **`export/lens.html` carries internal pages.** It never goes in `docs/`, a proposed change, an Artifact or anywhere
  public. Only the locked `docs/lens/index.html` leaves the computer.
- **The owner's own edition** (`--personal`, written to `export/lens-personal.html`) is never locked or put on a site.
- **Never change the password without the owner asking.** Never change `lock.salt_prefix`. Every remembered device would
  ask again.
- **`design/lens/lens.html` and `tools/build_lens.py` are shared files.** A change meant for every wiki is made in the
  source wiki and delivered with `tools/deliver_shared.py`. Never copy a shared file between wikis.
- **This wiki's own differences belong in `design/lens/settings.json`:** names, colours, shelves, labels and switches.
  Those never meet a shared update.
- **Never skip or weaken the privacy check.** If it stops the build, the lens stays as it was.

## Connections

- `guides/your-lens.md`: the owner's guide to reading the lens and keeping its password.
- `design/lens/SPEC.md`: what each setting does, and "A third wiki" for setting up a new lens.
- `.claude/rules/shared-changes.md` in the source wiki: shared changes and each wiki's own changes.
- `.claude/rules/finishing.md`: how to ask "Shall I merge this?".
- `publish-check`: for pages going on the open web. The lens is locked, so it needs the privacy check instead.
- `tools/rollout.py` and `tools/deliver_shared.py`: for a lens change that goes to every wiki.
