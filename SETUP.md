# Setting up a new wiki from this template

Roughly 20 minutes, most of it waiting on GitHub. You need: a GitHub account with access
to your org, and a Claude plan that includes Claude Code.

The person doing this setup needs a browser only — but if you're comfortable in a terminal,
steps 4–6 are faster there.

---

## 1. Create the repo

On the template repo's GitHub page: **Use this template → Create a new repository**.

- **Name it** for its owner, e.g. `alex-llm-wiki`.
- **Make it private.** Do this now, not later — a repo that starts public has a public
  history even after you flip the switch. If in doubt, private.

## 2. Decide who can read it, before adding content

Read **[SHARING-AND-ACCESS.md](SHARING-AND-ACCESS.md)** — specifically the two boundaries.
The one-line version:

> `visibility:` on a page controls what gets **published**. It does **not** control who can
> open the repo. On GitHub, read access is per-repository — anyone who can open this repo
> reads every private page and everything in `raw/`.

If your org's base permission is `Read`, **every member of your org can already read this
wiki**. Fix that (SHARING-AND-ACCESS Part A) *before* the first sensitive ingest, and verify
it with a second account.

## 3. Make it the owner's

Two edits, and the wiki stops being generic:

- **`CLAUDE.md` → "Who you are working with"** — replace the placeholder with the actual
  person: their field, their vocabulary, what they want the wiki to answer, how much
  pushback they want. This section is what makes Claude a useful librarian for *them*
  rather than a generic one.
- **`wiki/overview.md` → "What this wiki is for"** — a sentence or two on the body of
  knowledge being accumulated.

Everything else can be left alone until it needs changing.

## 3b. If this is a COMMONS, not a personal wiki

Skip this if the wiki belongs to one person. A **commons** — a team's or an option's shared
wiki — needs four changes, and **the first one is not optional**: without it the commons
publishes an empty graph and every spoke syncing from it is told the sync succeeded.

**1. The two-cut export.** This template ships the *spoke* export, which publishes only
`wiki.public.json`. A commons defaults every page to `internal`, so its public cut is empty
by construction. Copy both files from an existing commons (`xco-team-wiki` is the reference):

```bash
cp ../xco-team-wiki/tools/export.py            tools/export.py
cp ../xco-team-wiki/.github/workflows/export.yml .github/workflows/export.yml
```

That version writes `wiki.shared.json` too — public + unlisted + **internal**, the cut the
`internal` tier exists for — and adds the `origin` / `contributed` provenance fields the
federation view needs. Both cuts strip `private` completely: body, title and inbound links.

Verify it rather than assuming, because the failure looks like success:

```bash
python3 tools/export.py && ls export/
python3 tools/test_export_shared.py
```

You want `wiki.shared.json` present and non-trivial. A 218-byte `wiki.public.json` on its
own is the bug.

**2. The private-page advisory.** Copy `tools/check_no_private.py` from a commons and add a
step to `.github/workflows/checks.yml`. It **warns** rather than fails — a page
mid-migration is a real case — and surfaces on the pull request so a reviewer decides.

**3. Delete `deploy-pages.yml`.** A commons is not a publishing surface. Work that should
reach the open web goes out through a member's own wiki, after `publish-check`.

**4. Fix the scaffolding's own visibility.** `wiki/axioms.md` and `wiki/overview.md` ship
`private`. In a commons they should be `internal`, or the advisory in step 2 fires on the
template's own files from day one.

Then set `design/federation.json`: `"role": "commons"`, a one-line `subject`, `receives_from`
listing who contributes up into it, and `contributes_to` if it feeds a wider commons in turn.

## 4. Connect Claude

1. The GitHub account the owner uses with Claude needs access to the repo — via the Claude
   GitHub App authorization or a synced token. If the org restricts third-party OAuth apps,
   an org admin may need to approve the Claude GitHub App on this repo.
2. Confirm **Claude Code on the web** is enabled for the account/organization (on Team and
   Enterprise plans this can be an admin toggle).
3. The owner opens **[claude.ai/code](https://claude.ai/code)**, selects the repo, and
   starts typing.

Each session runs in a fresh cloud environment that clones the repo, which is why every
tool here is dependency-free stdlib Python — there is nothing to install.

## 5. Set the secrets you actually need

Repo → *Settings → Secrets and variables → Actions*. **None of these are needed for
day-to-day wiki use** — skip any you don't want yet.

| Name | Kind | Needed for | Cost |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | secret | the Friday reflection job | **API credits, billed outside your Claude plan** |
| `SHARED_REPO_TOKEN` | secret | the colleague mirror | free |
| `SHARED_REPO` | variable | the colleague mirror (`YOUR-ORG/YOUR-WIKI-shared`) | free |
| `DEPLOY_HOOK_URL` | secret | pinging a frontend to rebuild | free |

**If you don't want the weekly job**, delete the `schedule:` block from
`.github/workflows/weekly-reflect.yml` — reflections then run only when asked for. Leaving
the file in place without `ANTHROPIC_API_KEY` set just means the job fails weekly; delete
the schedule rather than letting a red X become normal.

## 6. Prove the gates work

Before trusting the boundaries, watch them fail and pass once:

```bash
python3 tools/export.py --check && python3 tools/test_export.py && python3 tools/test_export_shared.py && python3 tools/test_internal_tier.py
```

All four should pass on a fresh template. These same checks run in CI on every push, and a
failure blocks publishing.

## 7. First ingest

Drop a document into `raw/` (drag-and-drop works in GitHub's web UI) and tell Claude:

> ingest this

Claude reads it, writes a summary page, cascades updates across affected pages, updates the
index and log, and opens a **pull request**. Read the plain-language summary, merge it, and
the wiki has begun.

## 8. Clean up the scaffolding

Once real content exists:

> delete the example files

That removes `wiki/examples/` and `raw/EXAMPLE-sample-source.md`, and tidies the index.

---

## What you just set up

- **`raw/`** — source documents. Immutable; Claude only ever reads them.
- **`wiki/`** — the pages Claude writes and maintains.
- **`.claude/skills/`** — 14 workflows (ingest, query, lint, brief, office-hours,
  publish-check, publish-web, joker, reflect, metacognition, gravity, learn, delta, crm).
- **`tools/`** — stdlib-only helpers: the exporter, the boundary tests, the leak scanner.
- **`.github/workflows/`** — export graph, shared mirror, Pages deploy, Friday reflection.
- **`CLAUDE.md`** — the constitution Claude reads at the start of every session.

## Things that bite people

- **Publishing is a two-step.** Claude changes a page's tier and opens a PR; **the page
  goes live only when you merge it.** Nothing is published behind your back.
- **`unlisted` is on the public internet.** Unlinked and unindexed, but anyone with the URL
  can read it. For colleagues-only, use `internal`.
- **Don't put secrets in `tools/sensitive_terms.txt`.** It's a versioned file; writing a
  sensitive phrase there to block it also publishes it. Read the warning at the top of it.
- **The `export` branch must stay an orphan.** See the last caveat in SHARING-AND-ACCESS.md.
