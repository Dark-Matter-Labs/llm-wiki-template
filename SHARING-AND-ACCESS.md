# Sharing & access — who can read what

This wiki has **two different kinds of "private," and they are easy to confuse.** Getting
this right is what keeps sensitive material safe while still letting colleagues benefit
from the shareable parts.

**Read this before you put anything sensitive in the wiki.** The mistake it prevents is
one people make once, and it is not recoverable.

## The two boundaries

**1. The publication boundary — what leaves the repo for the open web.**
Every page carries a `visibility` field (`public` / `unlisted` / `internal` / `private`,
default `private`). This controls what gets *published*: the GitHub Pages site, the JSON
graph a frontend reads, and the colleague mirror. This boundary is handled automatically
and is well tested.

**2. The access boundary — who can open the repository at all.**
This is **not** controlled by the `visibility` field. On GitHub, read access is granted
**per repository, not per file.** Anyone who can open the repo can read *every* file in
it — including every page marked `private` and everything in `raw/` — regardless of the
`visibility` field. **The `visibility` field is a publishing instruction, not a lock.**

> A colleague pointing their own Claude Code at this repo will read whatever their GitHub
> access allows — the `visibility` labels do not stop them. That is a GitHub permissions
> question, not a Claude question.

Because access is per-repo, "some pages private, some shared with colleagues" **requires
separating by repository**. That is what this setup does:

| Tier | Where it lives | Who can read it |
| --- | --- | --- |
| `private` | the **source repo** (this one) | the owner (+ a maintainer) only |
| `internal` | the **shared mirror repo** | trusted colleagues (read-only) |
| `unlisted` | mirror **+** the Pages site, unindexed and unlinked | anyone with the direct link |
| `public` | mirror + the **Pages site**, linked and indexed | the open internet |

The owner keeps working in one place (this repo). The shareable cut flows outward
automatically.

**The two boundaries in code.** `tools/export.py` defines them explicitly, and the tests
in `tools/test_internal_tier.py` prove both directions hold:

```python
HIDE_FROM_WEB    = {"private", "internal"}   # never reaches the Pages site / public graph
HIDE_FROM_SHARED = {"private"}               # never reaches the colleague mirror either
```

---

## Part A — lock down the source repo (org owner action)

If your org's base permission lets every member read every repo, colleagues can read this
wiki today, private pages included. **These are GitHub access-control changes; only an org
owner can make them — they cannot be scripted from inside the repo.**

1. **Check the org's base permission.** GitHub → your org → *Settings → Member privileges
   → Base permissions.* If this is `Read` (or higher), **every member can read every repo**.
   To restrict a single repo it must be set to **`No permission`**, with access then granted
   per repo/team. (This is an org-wide change — confirm it's acceptable, or use the fallback.)
2. **Grant access to just the owner + a maintainer.** This repo → *Settings → Collaborators
   and teams* → remove broad team access; add them directly, or a small private team
   containing only them, with `Write`/`Admin` as appropriate.
3. **Verify** with a colleague account (or ask one): they should now get a 404 on the repo.
   *Do not skip this.* An unverified permission change is a belief, not a control.

**Fallback if the org base permission can't be lowered** (too disruptive org-wide): transfer
this repo to the owner's personal GitHub account as a private repo (*Settings → General →
Danger Zone → Transfer*). Only people they explicitly invite can then see it. Trade-off: it
leaves the org's ownership/backup — keep a periodic backup if you go this way.

Note: browser/iPad Claude Code keeps working unchanged either way — it uses the owner's own
GitHub access, which they retain.

---

## Part B — set up the shared mirror repo (for colleagues)

This gives colleagues a repo they *can* read that contains only the shareable pages — never
`private` pages, never `raw/`.

1. **Create the target repo**, e.g. `YOUR-ORG/YOUR-WIKI-shared` (private is fine — grant
   colleagues read on *this* one). Start it empty.
2. **Create a write token** scoped to that repo only: preferably a **fine-grained personal
   access token** with *Contents: Read and write* on the mirror repo only, or a machine
   account. Do not reuse a broad token.
3. **Add the token + target to THIS (source) repo** → *Settings → Secrets and variables →
   Actions*:
   - Secret **`SHARED_REPO_TOKEN`** = the token from step 2.
   - Variable **`SHARED_REPO`** = `YOUR-ORG/YOUR-WIKI-shared`.
4. **Grant colleagues read** on the shared repo.
5. **Trigger it**: *Actions → Export shared mirror → Run workflow* (or merge any wiki change).

If these aren't set, the workflow still runs the build + leak-test on every push but simply
skips publishing — so nothing breaks before the mirror exists.

**Promoting pages to `internal` in bulk.** `tools/classify_internal.py` proposes which
`private` pages look like ordinary working knowledge. It is a **dry run by default** and
deny-wins (any sensitivity signal keeps a page private). Read every line of the proposal
before `--apply`; visibility is a disclosure decision and belongs to the owner, not a script.

---

## What the automation guarantees

`.github/workflows/export-shared.yml` runs on every push to `main` that touches the wiki:

1. `tools/export.py --check` — frontmatter schema gate.
2. `tools/test_export_shared.py` + `tools/test_internal_tier.py` — the **leak invariants**.
   If a private page's title, body, or a link to it could reach the shared cut, these fail
   and **nothing is published.**
3. `tools/export_shared.py` — builds the shared markdown, then pushes it to the mirror repo.

The shared cut is built so a `private` page leaks nothing:
- its file is absent; its title never appears (filename, index, or body);
- links to it are redacted (`[[Private Title]]` → `[redacted]`), robustly — even links
  wrapped across lines or hidden in a frontmatter comment;
- a `parent:` naming a private page is dropped;
- frontmatter is **rebuilt** from a field whitelist (comments and stray fields discarded);
- `raw/`, `log.md`, and the full `index.md` are never included — a fresh index listing only
  shared pages is generated.

Run the same checks locally any time:

```bash
python3 tools/test_export.py && python3 tools/test_export_shared.py && python3 tools/test_internal_tier.py
```

---

## The publication tripwire (backstop for the open web)

The `docs/` site is public by design, and some of it may be hand-built (interactive pages),
so it sits *outside* the page-level `visibility` system. To stop sensitive material reaching
it by accident:

- **`tools/sensitive_terms.txt`** lists never-public terms.
- **`tools/scan_public_leaks.py`** matches them against every public surface (all of `docs/`
  **and** every `public`/`unlisted` wiki page): `python3 tools/scan_public_leaks.py`.
- It runs in CI as a **hard gate**: a hit **blocks the Pages deploy** and **blocks the
  mirror publish**.
- The `publish-check` skill runs it before anything is shared.

**Two honest limits.** It only catches terms you listed — so it proves nothing about terms
you didn't think of. And **the list is itself versioned**: in any repo that is or becomes
public, the tripwire file publishes the very vocabulary it protects. Read the warning at the
top of `tools/sensitive_terms.txt` before adding entries. The real guarantee is Part A.

## Important caveats (please read)

- **The public web caches.** Anything that was live on the Pages site may already be in
  Google's cache, the Wayback Machine, or someone's saved session. Removing it from the repo
  stops *future* access but **cannot un-publish the past.** Treat anything that was public as
  "may already be out," and if it matters, request removal from search caches.
- **Git history remembers.** Even after a scrub, content stays in past commits — and in every
  existing clone. A history rewrite does **not** help if the sensitive text also lives,
  correctly, in *current* private files: rewriting either leaves those intact (achieving
  nothing) or redacts them too (destroying working material). The honest order of operations
  is **(1) lock down access → (2) delete and let the `export` branch regenerate → (3) treat
  anything formerly public as cached.** A rewrite is worth it only if the repo will *stay*
  shared *and* you specifically want old versions of now-public files purged — and it is an
  org owner's job, since it force-pushes rewritten history and breaks every clone and open PR.
- **Fastest emergency stop:** an org owner can take the Pages site offline immediately (repo
  *Settings → Pages*, or disable the deploy) while cleanup happens. Do this first if you find
  something sensitive live; investigate second.
- **The `export` branch must stay an orphan.** `export.yml` publishes **only**
  `wiki.public.json` (private already stripped) to an orphan branch containing nothing else.
  If you ever change it to `git checkout -B export`, the branch becomes a **full second copy
  of the private repo** — every private page and all of `raw/` — readable by anyone with repo
  access. This template ships with the safe version; keep it that way.

## Rules of thumb for the owner

- **Default is private.** A page is only ever shared if you mark it up a tier.
- **`internal` is the useful middle.** Ordinary working knowledge a colleague needs, never
  on the open web. Most of a mature wiki belongs here.
- **`unlisted` is still on the open web** — just unlinked and unindexed. Anyone with the URL
  can read it, and URLs get forwarded. If it must not be on the public internet, use
  `internal`.
- **`raw/` is the crown jewels** (unpublished drafts, proposals, transcripts) and never
  leaves the source repo.
- **CRM data is always `private`.** No exceptions, no promotions.
