---
name: live-page
description: Revise a page that is already published. Apply the wiki's versioning rule, add a history line, check it at phone and laptop width in light and dark, and keep any mirror in step. Fires on "update the live page", "change the published page", "fix the page on the site", "make a new version of", "it looks wrong on my phone", "bump the version", "the site still shows the old one".
---

# Revise a live page

## Why this exists

A published page is read by people outside the wiki, so every change to it needs the same steps. A
scan of 28 wikis on 20 October 2026 found 409 log entries with version numbers in 9 wikis (Prateek
189, Ocean Studio 179). It found 83 fixes for phone or width problems. Prateek ruled on 12 October 2026 to
check before publishing. Robyn adopted Prateek's versioning
rule by hand. Generalised from Ocean Studio's `wiki-page-versioning` skill and Prateek's rules for
designed pages. Gurden verified the pattern on 20 October 2026.

`publish-web` makes a new page. This skill changes one that is already out.

## Method

1. **Find the page and its source.** The live page is under `docs/`. Find the wiki page it was built
   from. Read both before changing either.
2. **Check the tier.** The source page must be `public` or `unlisted`. If it is `internal` or
   `private`, stop and ask the owner. Private content never goes into `docs/`.
3. **Read the wiki's versioning rule.** Search `CLAUDE.md`, `.claude/rules/` and `.claude/reference/`
   for "version", and follow what you find. Where the wiki has no rule, use this default:
   - one decimal step per substantive change, v1.2 to v1.3
   - the suffix counts as a whole number, so v1.10 follows v1.9
   - a new whole number only when the owner says so
   - a typo or a broken link is not substantive, so only the date changes
4. **Make the change.** Edit the wiki page first, then the published page, so the two agree.
5. **Change the version everywhere it appears.** Check the `<title>`, `og:title` and `twitter:title`,
   the heading or breadcrumb, the footer, and any download named with the version. One stale number
   leaves the page half-versioned. Update the "last updated" date, with the time where the page shows one.
6. **Add one history line.** Put it in the page's version history, newest first. Say what changed in
   plain words, for example "v1.3, 20 October 2026: adds the funding timeline."
7. **Keep earlier versions only where the rule says so.** Some wikis keep one archived copy, some keep
   none. Never remove an archived copy the rule asks for. Git keeps every other copy.
8. **Scan for leaks.** Run `python3 tools/scan_public_leaks.py` where it exists. Run the
   `publish-check` skill on what changed, and `python3 tools/house_rules.py`.
9. **Check it at three widths, in light and dark.** Open the page with the browser preview tools at
   about 390px, 1000px and 1300px wide. At each width, check that:
   - the page does not scroll sideways
   - text, tables and figures are readable, with nothing cut off or overlapping
   - nothing hidden at one width is left loose at another
   - colours and images read well in both light and dark
   With no browser tools, say the check was not done. Never report a width you did not see.
10. **Keep the mirror in step.** A copy of this page may live in another wiki, such as a team wiki or
    a commons. Do not edit it. Propose the same change there, through `contribute` or that wiki's own
    route, with the owner's yes.
11. **Log it.** Append `## [YYYY-MM-DD] rebuild | <page>, v<old> to v<new>` to today's log, with one
    line on what changed. Run `python3 tools/sync_log_index.py`.

## Output

One draft change and a short summary, for example:
> The funding page is now v1.3. It adds the funding timeline. Checked at phone, tablet and laptop
> width, in light and dark. The team wiki copy has a matching proposed change.

Then ask: "Shall I merge this? That saves it into your wiki." Add one line: the site changes a few
minutes after GitHub publishes it, and it can lag.

## Hard rules

- Never publish a page whose tier does not allow it. Private content never enters `docs/`.
- Every substantive change gets a version step and a history line.
- A page carries one version number everywhere it names itself.
- Check every width before publishing. Say plainly which widths you did not check.
- Never decide a new whole-number version. The owner does.
- Never edit a mirror in another person's wiki. Propose the change there.
- Propose, never merge. Merge only on a yes in this session.

## Connections

- `publish-web` builds a new published page. This skill revises one.
- `publish-check` and `tools/scan_public_leaks.py` guard the tier before anything ships.
- `rebuild-parity` applies when a revision rebuilds the page. Count what went in and what came out.
- `contribute` carries a change to a mirror in a commons.
- `rename` applies when the page's title or address changes.
