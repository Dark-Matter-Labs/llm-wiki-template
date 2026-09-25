---
name: contribute
description: Propose a page from this wiki to the commons it contributes to. Use when the owner says "share this with the team", "contribute this", "send this to the team wiki", "propose this to the commons", or wants something they have written to become shared canon. Stages a sanitised, provenance-stamped bundle and opens a PR against the commons named in `design/federation.json`; never pushes to the commons directly.
---

# Contribute a page to the commons

The flow up from this wiki to the commons above it. It is the same consent loop as
everything else, pointed at a second repo: you assemble a proposal, a **different person**
reviews and merges it.

**The target is not written here.** It is `contributes_to` in `design/federation.json`, which
`tools/contribute.py` reads; `python3 tools/contribute.py --list` prints it. If more than one
commons is declared, the tool **refuses to guess** and requires `--to <commons>`, because
which commons a page goes to is an audience decision. Below, `<commons>` is that name and
`<this-wiki>` is this repo's own `name` in the same file.

**What this skill is for:** moving knowledge that has become genuinely shared — a concept
the team relies on, a summary others should not have to re-read the source for, a position
worth arguing with. Not for pushing everything you write into a shared space; a commons
that mirrors one wiki is not a commons.

## A push is permanent — spend the effort before it, not after

Every guarantee below runs **before** the bundle leaves this repo, and that is not a
convenience. Once a commit reaches the commons it is reachable by SHA in **every clone and
every fork, forever** — after a deleted branch, after a closed PR, after a force-push, after
the file is removed in a later commit. GitHub keeps unreachable objects served; a colleague
who cloned an hour ago has a copy you cannot reach at all.

So there is no "take it back" step in this skill, because there isn't one in git. **Treat a
leak as unrecoverable and spend the effort before the push:** read what was staged, check the
tier with the owner, and let a refusal stand. The few minutes of reading is the entire
mitigation available.

The one real remedy is out of scope for a wiki operation and belongs to the owner: rotate
whatever was exposed, on the assumption it has already been read.

## Before anything: the two things that decide it

1. **Tier.** `private` never contributes. If a page should be shared, it must first be
   promoted to `internal` — and that is a **disclosure decision**, so ask the owner (in a
   commons, the page's author) explicitly. Never promote a page in order to contribute it in
   the same breath.
2. **Is it actually shared knowledge, at the level above?** In a personal wiki, a page nobody
   but the author will use stays here. In a commons, everything is already shared with its
   members, so the question is narrower: does the wider group above need it? Ask what makes
   it commons material; if the answer is thin, say so.

## Steps

1. **Identify the page(s).** `python3 tools/contribute.py --list` shows what is eligible.
2. **Check the tier with the owner** if anything is `private`. Do not promote it yourself.
3. **Stage the bundle:**

   ```
   python3 tools/contribute.py <slug> [<slug> ...] --by <person>
   ```

   This writes a sanitised copy to `contrib/` and **nothing else** — no push, no PR. It
   refuses private and CRM pages outright, rebuilds frontmatter from a whitelist, redacts
   links to private pages, stamps provenance, and runs the sensitive-term scan over the
   result. If it refuses, the refusal is the answer; do not work around it.
4. **Read what was staged.** Open the files. The tool guarantees the boundary; it cannot
   judge whether the page reads sensibly out of its original context. Fix wording that only
   made sense next to a private page.
5. **Open a PR against the commons** — never a direct push:

   ```
   cd ../<commons> && git checkout main && git pull && git checkout -b contribute/<slug>
   cp -r ../<this-wiki>/contrib/wiki/. wiki/
   python3 tools/export.py --check && python3 tools/scan_public_leaks.py
   ```

   Then commit and `gh pr create`. State in the PR body **what the page is for**, and that
   it needs someone else to merge it.

   **Always target the commons' `main`, never another PR's branch** — even when the pages
   link to an earlier contribution that has not merged yet. Say so in the body instead
   ("depends on <commons>#<pr>; the diff narrows once that merges"). A PR based on
   another branch can report *merged* without ever reaching `main`: xco-team-wiki#134 did
   exactly that on 2026-09-25, and had to be repaired as #135.
6. **Cascade happens in the commons, not here.** The receiving wiki updates its own index,
   log and cross-references when the PR is reviewed. Do not edit the commons' index from
   this side.
7. **Log it** — append `## [YYYY-MM-DD] contribute | <title> → <commons>#<pr>` to **today's**
   day file (`wiki/log/YYYY-MM-DD.md`, created with the header `# Log — YYYY-MM-DD` if it is the
   day's first entry), then run `python3 tools/sync_log_index.py`.

## What the tool guarantees (so you do not have to check by hand)

| Guarantee | Why it exists |
| --- | --- |
| `private` refused | The tier is the boundary; filtering later is how leaks happen |
| CRM refused by path | Relationship data never enters a shared space, whatever its tier |
| Frontmatter rebuilt from a whitelist | A YAML comment can hide a private page's title |
| Links to private pages redacted | Including in `description` and other frontmatter strings |
| Provenance stamped | `contributed_by`, `origin`, `origin_rev` — recorded, never invented |
| Sensitive-term scan on the bundle | The commons is a wider audience than this repo |

## If the commons already has the page

The tool refuses, and that refusal is usually correct. **Nearly every page in a wiki seeded
from the commons already exists there** — 577 of 595 when this was first measured — so
contributing without checking would overwrite the commons' copy and silently lose whatever
it had done since. A wiki seeded from the template rather than from its commons will collide
less often; that makes each collision *more* worth reading, because the commons reached the
same page by its own route.

When you hit it, there are only two honest answers:

- **The commons copy is fine.** Reference it; do not re-contribute. If your version differs
  because you *disagree*, say so on your page with `contradicts:` — that is a position, and
  positions are kept, not overwritten.
- **The commons copy is genuinely stale and yours should replace it.** Then say so
  deliberately with `--update`, and **write in the PR body what changed and why**, because
  the reviewer is now approving a replacement rather than an addition.

`--update` is not the way past an inconvenient error. It is a claim that you have looked at
the commons copy and it should go.

*(If there is no cached commons graph the tool says it cannot check, rather than implying
all-clear. Run the sync workflow to enable the check.)*

## Validation is re-based on the way across

`peer` and `collective` mean **this** group stood behind a page. Carried over unchanged,
the commons would inherit a consensus it was never party to. So the tool re-bases:

```
machine    -> machine     nobody has stood behind it anywhere
self       -> self        the author still stands behind it; that travels
peer       -> self        re-earn it in the commons
collective -> self        re-earn it in the commons
```

**Do not override this.** If a page was peer-reviewed here, say so in the PR body — that is
useful context for the reviewer, and it is not the same as asserting the commons agreed.

## Hard rules

- **Never push to the commons directly.** Every contribution is a PR someone else merges.
- **Never merge your own contribution** — the four-eyes rule is the commons' constitution.
- **Never promote a page's tier to make it contributable.** That is the owner's call, taken
  separately and for its own reasons.
- **Never contribute CRM data, capital or deal specifics, or transcripts** — refused by the
  tool, and it should never be asked for.
- **Never edit the commons' `index.md` or log from this side.**
- **Every contribution PR targets the commons' `main`**, never another PR's branch — a
  stacked PR can show as merged while its pages never arrive.
- If the tool refuses, **report the refusal plainly**. It is a boundary working, not an
  obstacle to route around.
- **Never treat a push as reversible.** Deleting a branch, closing a PR or force-pushing
  removes nothing — the object stays reachable by SHA in every clone and fork. There is no
  undo to fall back on, which is why the whole check happens before.

## Connections
- `tools/contribute.py` — the staging tool; `tools/test_contribute.py` proves the guarantees.
- `design/federation.json` — this repo's declared place in the graph: what it contributes to,
  and what it reads.
- The federation architecture page — what the commons is for, and the three kinds of conflict.
- The `publish-check` skill — the equivalent bar for the *outward* boundary.

