# Your lens

The lens is a reading view of a wiki: a map, shelves, an outline and the pages themselves. It is a web page, locked
with a password, at `https://dark-matter-labs.github.io/<wiki>/lens/`.

## Reading it

- Some lenses open on **Outline**, a calm contents page. **Detail** shows the map, the shelves and the other views.
- Open a page, and links in it open beside it, so the trail stays in view.
- Search finds pages by title, tag and words.
- Some lenses also have a **Front page** tab: the pages getting the most attention across the wikis.

## Sharing a link to one page

1. Open the page in the lens.
2. Copy the address from your browser. It ends with the page, for example `#w0.capital-terms-plain-map`.
3. Send it. The reader needs the lens password.

In lenses that have Focus view, press **Focus** before you copy. The address then ends in `!focus`, and the page
opens on its own, without the map and panels.

## Why the lens does not show today's change

The lens is a copy, built and locked at one moment. A change saved in the wiki shows in the lens only after the next
rebuild and lock. Ask Claude to rebuild it, then lock it yourself with the password.

## The password

- Keep each lens's password in one place, such as your password manager.
- Use that same password every time you lock. If you give Claude or another machine a different one, the lock now
  stops and says so. It does not quietly change the password.
- To change it on purpose, ask Claude for the `--new-password` step, then tell the people who read the lens.
- Never paste a password into a chat or a page.

## What the lens never shows

Private pages, their titles and links to them are never in a shared lens. Each build checks this and stops if one
gets through.
