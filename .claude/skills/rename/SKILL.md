---
name: rename
description: Record a name change once and carry it through the wiki. Pages, links, tags, published copies and shared copies all follow, and drafts are checked against the list of names. Fires on "rename this", "it's now called X", "change the name to", "we don't call it that any more", "the title has changed", "use the new name", "is the name right everywhere".
---

# Rename

## Why this exists

Names change often, and a half-done rename is worse than none. A scan of 28 wikis on 20 October 2026
found 30 rename entries in 6 wikis (Ocean Studio 12, Prateek 8, Robyn 5). It also found 29 correction
entries, many of them a name caught late. Robyn's wiki logged "+HM's working title changes again".
Indy's wiki and the xCO team wiki renamed ten option and position pages to the live register on the
same day. Generalised from Robyn's `name-check` skill, which keeps one list of names and checks drafts
against it. Gurden verified the pattern on 20 October 2026.

A page is linked by its title, as `[[Page Title]]`. Change a title and every link to it breaks, unless
each link changes too.

## Method

1. **Confirm the new name with the owner.** A person decides names. Ask one question: "From now on it
   is called <new>, not <old>. Is that right?" Assume the old name is out of date, not wrong, and say
   so in one line. With no answer, stop.
2. **Check whose page it is.** If it lives in another person's wiki or a commons, do not rename it
   there. Propose the change to its owner, and stop at that.
3. **Record the name once.** Where the wiki keeps a register of names (for example `design/names.json`
   with `tools/name_check.py`), add the entry first: old name, new name, date, reason. With no
   register, the note on the page (step 5) is the record.
4. **Move the file if the slug changes.** Use `git mv`, never delete and recreate. The history guard
   (`tools/check_history.py`, where it exists) then sees a rename, not a deleted page.
5. **Change the page.** Update `title`, and `description` and `tags` where they carry the old name. Add
   one line near the top: "Renamed on <date> from <old name>." The old name stays searchable.
6. **Carry it through the links.** Find every `[[old title]]`, including the `[[old title|label]]`
   form, and change it. Run `python3 tools/check_links.py --check`. It must report no new broken link.
7. **Carry it through the text.** Search the wiki for the old name in prose. Change uses that mean the
   thing itself. Keep uses that record history, quote a source, or mean something else.
8. **Leave the log's past alone.** Past days are never rewritten. Today's file may have its links
   updated. Append `## [YYYY-MM-DD] rebuild | Renamed <old> to <new>` to today's file, then run
   `python3 tools/sync_log_index.py`.
9. **Update the index.** Change the page's one-line row in `wiki/index.md` and in any shelf under
   `wiki/index/`.
10. **Check the published copies.** Look under `docs/` for a page built from this one. Change the name
    in its title, headings and links. A slug change moves its address too, and old links stop working.
11. **Check the shared copies.** Search each commons copy (`.commons/<name>/`) for a page whose
    `origin` points here. Do not edit it. Propose the same rename there through `contribute`, with the
    owner's yes.
12. **Name what else breaks.** A lens deep link (`#w0.<slug>`) changes with the slug. So does any
    address someone has saved or shared. List these in the summary.
13. **Check the drafts.** Run the name check where the wiki has one, and `python3 tools/house_rules.py`,
    over everything touched.

## When it is not a rename

- **Two pages are one subject.** That is `same_as:`, and a person's call. Propose it. Do not merge the
  pages.
- **The thing changed, not only its name.** Write a new page and link the two. Add `contradicts:` if
  they disagree.
- **The name is still under discussion.** Leave the pages alone. Note it as a working title and ask
  again before anything goes out.

## Output

One draft change and a plain summary, for example:
> Renamed "<old>" to "<new>". One page moved, 14 links and 3 mentions updated, 2 kept as history. The
> published page's address changes. A matching change is proposed to the team wiki.

Then ask: "Shall I merge this? That saves it into your wiki."

## Hard rules

- A person decides every name. Never rename on a guess or a pattern in the text.
- Never rename in another person's wiki without their yes. Propose there instead.
- Keep one register of names where the wiki has one. Never keep a second list in memory notes.
- Never edit `raw/`, a quotation, or a past day's log.
- Never delete the old page. A slug change is a `git mv`.
- A private page's old and new names never appear in a proposal description, a commons or `docs/`.
- Propose, never merge. Merge only on a yes in this session.

## Connections

- `name-check` (Robyn's wiki) holds the register this skill writes to, where a wiki has one.
- `contribute` carries a proposed rename to a commons.
- `live-page` applies when the published copy needs a new version, not only a new name.
- `lint` finds stale uses of an old name later.
- `.claude/reference/page-fields.md` covers `same_as:` and `contradicts:`.
