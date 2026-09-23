# The technical version

This is the companion to `ONBOARDING.md` and `HOW-IT-WORKS.md`. Those two are written for people who
never want to see a terminal, and they leave the machinery out on purpose. Everything they leave out is
here: for technical readers, for admins, and for Claude.

*If you're new and not technical, you don't need this page. Close it.*

This page is the same in every wiki. The rules that bind Claude live in `CLAUDE.md` and
`.claude/skills/`; where this page and those disagree, those win, and this page is the one to fix.

---

## The plain words, translated

The friendly guides use everyday words. Each one stands for something specific.

| The guides say | What it is |
| --- | --- |
| your wiki | a private GitHub repository in the Dark-Matter-Labs organisation |
| a team wiki | a *commons*: a repository with `role: commons` in `design/federation.json` |
| a draft | a branch, plus the pull request opened from it |
| "Shall I merge this?" / saving | merging that pull request into `main` |
| the checks | the GitHub Actions workflows, chiefly `.github/workflows/checks.yml` |
| undo | reverting the merge commit; every merge is its own commit, so each one reverts cleanly |
| your original documents | the files in `raw/`, which are never edited |
| a label | the `visibility` field in a page's frontmatter |
| standing behind a page | the `validation` field, set by a person |
| "what's waiting for me?" | `tools/waiting.py`: unmerged branches and open pull requests |

---

## A page, underneath

Every page in `wiki/` is a markdown file that opens with a block of YAML frontmatter:

```yaml
---
type: concept
title: Human-readable title
description: One sentence describing the page
tags: [tag1, tag2]
status: draft
visibility: private        # private | internal | unlisted | public
confidence: medium
validation: machine        # machine | self | peer | collective
timestamp: 2026-09-23
sources: [raw/some-report.pdf]
---
```

`CLAUDE.md` defines every field. The two that matter to the friendly guides are `visibility` (the
label) and `validation` (who stands behind it). A page with no `visibility` field is treated as
`private` by every exporter.

### Standing behind a page: the three lines

When a person has read a page and agrees with it, they change `validation` and add two lines:

```yaml
validation: self
validated_by: [Your Name]
validated_at: 2026-09-23
```

All three are needed. Every read-out that counts human confirmation counts it **by date**, so a
confirmation without `validated_at` is recorded in the file and missing from every report. `EDITING.md`
walks through doing this in GitHub's web editor.

Claude may set `machine` and may *propose* `self`. It may never set `peer` or `collective`, and the
gates refuse any `validated_by` that names a model.

---

## Adding a file yourself

For a PDF, a Word file or an image that is too large to paste into the chat:

1. Open the wiki on github.com and go into the `raw/` folder.
2. **Add file → Upload files**, and drop the file in.
3. Choose **Create a new branch for this commit and start a pull request**, then **Propose changes**.
4. **Create pull request**, then **Merge pull request**.
5. Tell Claude: *"I've added a file to raw/, please ingest it."*

Some wikis ignore certain file types in `raw/` and un-ignore real sources one by one in `.gitignore`.
If an upload doesn't appear, that's the likely reason; ask Claude to add the exception.

---

## How the labels are enforced

A label controls **publication**, not **access**. On GitHub, read access is per repository, never per
file, so anyone who can open the repository can read every file in it, `private` pages and `raw/`
included. `SHARING-AND-ACCESS.md` covers how access is locked down.

Publication is handled by `tools/export.py`, which defines both boundaries:

```python
HIDE_FROM_WEB    = {"private", "internal"}   # never reaches the Pages site or the public graph
HIDE_FROM_SHARED = {"private"}               # never reaches the colleague mirror either
```

| Label | Pages site | Public JSON graph | Colleague mirror | A commons' shared cut |
| --- | --- | --- | --- | --- |
| `private` | no | no | no | no |
| `internal` | no | no | yes | yes |
| `unlisted` | yes, unlinked and unindexed | yes | yes | yes |
| `public` | yes | yes | yes | yes |

A `private` page is dropped entirely: body, title, and every link pointing at it. `tools/test_internal_tier.py`
proves both boundaries hold. The export is published to an orphan `export` branch that holds only the
generated JSON; it must stay an orphan, or it becomes a full copy of the private repository.

---

## Sharing up: from your wiki to a commons

*"Share this with the team"* runs the contribute skill, which drives tools/contribute.py. Both exist
only in a wiki that contributes up to a commons; the top commons has neither.

```
python3 tools/contribute.py --list                       # what is eligible
python3 tools/contribute.py <slug> --by "Your Name"      # stage one page
python3 tools/contribute.py <slug> --by "Your Name" --to <commons>   # when there are several
```

It stages a sanitised copy with provenance (`origin`, who contributed it, when), strips links to
`private` pages, refuses any `private` page outright, and opens a pull request against the commons.
**It never pushes to the commons' `main`.** A different member of the commons reviews and merges it:
the four-eyes rule, and the one place in the system where a second person is always required.

Which commons a wiki may contribute to is `contributes_to` in `design/federation.json`.

---

## Reading down: from a commons to your wiki

Once a week (Monday, 06:00 UTC) the sync-commons workflow clones each commons' shared cut into
`.commons/<name>/`. It authenticates with the repository secret `COMMONS_READ_TOKEN`: a read-only
token that must be allowed to read every commons the wiki reads from. Locally, the same thing is:

```
python3 tools/sync_commons.py
```

Which commons a wiki reads is `reads_from` in `design/federation.json`, falling back to
`contributes_to` when it's absent. A wiki can read without ever contributing, which is how a
repository holding material that must not travel still sees what the group knows.

`.commons/` is gitignored and never merged into `wiki/`. It is reference material: the `delta` and
`gravity` skills measure against it, and tools/contribution_prompt.py uses it to suggest pages worth
sharing. On a fresh checkout it is empty until the sync runs.

---

## Starting a commons

An org admin creates the repository first (from `llm-wiki-template`, private). Then the `onboard`
skill runs the first conversation, and the configuration falls out of it:

```
python3 tools/init_wiki.py --init --name <repo> --role commons \
    --display-name "<Name>" --contributes-to <parent-commons>
python3 tools/init_wiki.py --check
```

After that, an admin adds the new commons to the repositories the read token may open (so the
wikis below it can read it), and sets `COMMONS_READ_TOKEN` on the new repository if it reads from a
commons of its own. A commons files new pages at `internal` by default, not `private`.

---

## The checks on every change

Every pull request runs `.github/workflows/checks.yml`. The gates most worth knowing:

| Gate | What it refuses |
| --- | --- |
| `tools/export.py` `--check` | frontmatter that breaks the schema |
| `tools/check_links.py` `--check` | `[[links]]` to pages that don't exist |
| `tools/house_rules.py` `--check` | civilization spelt with an s, and xCO written any other way |
| `tools/check_prose.py` `--check` | new prose debt beyond the file's recorded baseline |
| `tools/check_onboarding.py` `--check` | these guides naming files, tiers or skills that don't exist |
| `tools/init_wiki.py` `--check` | a configuration that disagrees with `design/federation.json` |
| `tools/cross_check.py` `--check` | a `validated_by` that names a model |

A failing check blocks the merge and never changes anything. Nothing is lost.

---

## Where the rules live

- **`CLAUDE.md`**: this wiki's constitution. Page conventions, tiers, validation, hard rules.
- **`.claude/skills/`**: one folder per operation (`ingest`, `query`, `lint`, `contribute`, and the
  rest), each with the steps Claude follows.
- **`.claude/rules/finishing.md`**: why Claude asks "Shall I merge this?" in the session rather than
  leaving a pull request for later.
- **`SHARING-AND-ACCESS.md`**: repository access, the colleague mirror, emergencies.
- **`EDITING.md`**: what a person can safely change by hand in GitHub's web editor.

The files shared across every wiki (this one included) come from `indy-llm-wiki` and are copied by
tools/sync_design_system.py. Change them there, not in a sibling, or the next sync overwrites the change.
