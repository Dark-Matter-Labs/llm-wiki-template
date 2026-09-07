---
name: onboard
description: Run the first working session with a new option, team or person's wiki. Use when someone says "set up a wiki for X", "onboard a new option", "Santiago needs its own wiki", "get Copenhagen started", or a new repo has been created from the template and nobody has used it yet. This is an INQUIRY, not a setup wizard — the system asks what the work is trying to do, and the configuration falls out of the answers. Also fires when a wiki is found still carrying the template's worked demo.
---

# Onboard a new option

`SETUP.md` covers the machinery — create the repo, set the secrets, prove the gates run — and
`tools/init_wiki.py --init` now generates the configuration. Neither of them is the thing that
makes a wiki start working.

The thing that makes it start working is the first session, and on the INO interface call the
shape of it was named: *"we're not building an app, we are building a system"* — one that opens
by **asking what you are trying to do**, rather than presenting a fixed structure. A setup wizard
would defeat the operating logic of a system that is inquiry-native by name.

So: ask, in this order, and let the configuration fall out of the answers.

## The evidence that this is the real gap

Standing the repo up feels like finishing. It is not, and the corpus says so plainly — measured
7 September 2026:

| | |
| --- | --- |
| Wikis still holding the template's **fictional** Greenline demo (Lisbon, Tallinn, Cork) | **5 of 9** |
| …including the top commons, alongside 622 real pages | `xco-team-wiki` |
| Wikis whose entire content **is** that demo, byte for byte | `learning-system-wiki`, `prateek-llm-wiki` |
| Pages in `fang-llm-wiki` | **2** |

`learning-system-wiki` is a commons that spokes contribute *to*. Two of the five are wikis in
active daily use — so this is not only an unstarted-wiki problem. **Nobody ever does SETUP step 8**,
and until today nothing said so. `init_wiki.py --check` now raises it as an advisory.

## The five questions

Ask them one at a time, in a real conversation. Each answer decides the next.

**1 · What is this option trying to do — and how would you know, in six months, whether it
worked?** The second half is the forcing question and the first half is rarely enough without it.
Push until the answer is specific enough to be wrong. This becomes `wiki/overview.md`'s *"What
this wiki is for"*, and if a destination emerges, the first `goal` page.

**2 · Whose material is this, and who may open the repository?** Two different questions, and the
second is the one that gets skipped. `visibility:` governs what is **published**; it does not
govern who can read the repo. On GitHub, read access is per-repository, so if the org's base
permission is `Read`, **every member can already read every private page and everything in
`raw/`**. Settle this *before* the first sensitive ingest — SHARING-AND-ACCESS.md, Part A — and
verify it with a second account rather than assuming. Then set the default tier: **if the answer
is unclear, it is `private`.**

**3 · Where does this sit in the federation?** A spoke, or a commons others contribute to? Which
commons does it read from and contribute up to? Now, and only now, generate the configuration:

```
python3 tools/init_wiki.py --init --name <repo> --role spoke \
    --display-name "<what the colleague mirror should call it>" \
    --contributes-to xco-team-wiki
```

**4 · What are the first three sources?** Not thirty. Three real documents this option already
depends on, ingested properly with the cascade. A wiki with no mass cannot answer anything, and
every skill in the set is useless against eight pages — which is why the two wikis that stopped
here have never been used. Run `ingest` on each, and ask the tier **once** for the batch.

**5 · What should the model push back on?** How much challenge is wanted, what jargon is native
here, what a useless answer looks like. This becomes CLAUDE.md's *"Who you are working with"*, and
it is the difference between a librarian for **this** person and a generic one.

## Then, before you call it done

- **Clear the demo.** Delete `wiki/examples/` and any `raw/EXAMPLE-*`. It is fictional, and while
  it sits there it is indexed, searchable, inside the tier boundary and returned by `search.py`
  alongside real material. `init_wiki.py --check` will keep saying so.
- **Write `wiki/overview.md`** from answer 1 — in their words, not the template's.
- **Run the gates once, and read the output**: `init_wiki.py --check`, `export.py --check`,
  `check_links.py --check`. Proving they run is part of onboarding; a gate nobody has ever seen
  fail is a gate nobody trusts.
- **Log it**: `## [YYYY-MM-DD] onboard | <wiki name> — first session`, naming what was decided
  about access and tier, because that decision is the one people later wish had been written down.

## Hard rules

- **Never present this as a form or a checklist.** If the answers arrive as a filled-in template,
  the session did not happen. The questions are the product.
- **Never guess the tier.** Unclear means `private`. Promoting later is one edit; unpublishing is
  not — a push is permanent, and the `contribute` skill says why.
- **Never skip question 2** because it is awkward. It is the only one where getting it wrong is
  irreversible, and it must be settled before anything sensitive is ingested, not after.
- **Never leave the demo in place** and call the wiki set up. Five of nine wikis are the evidence.
- **Do not create a goal or a commitment to make the ledger look populated.** The ledger lives in
  the commons; a spoke inventing entries is how you get two ledgers. If a real destination came
  out of question 1, it belongs where the commons holds them.

## Connections
- `SETUP.md` — the machinery; this skill is what happens after it, or instead of most of it.
- `SHARING-AND-ACCESS.md` — question 2, in full, including how to verify with a second account.
- `tools/init_wiki.py` — generates the configuration and keeps checking it afterwards.
- The `ingest` skill — question 4 is three of these.
- The `office-hours` skill — if question 1 turns into a real argument, that is the better tool.
