---
name: dm-style-guide
description: >-
  Apply, audit, and enforce Dark Matter Labs' (Dm) publishing standards across
  its four companion guides — Style & Standards, Attribution, AI Usage, and
  Publishing. Use whenever the user is drafting, editing, reviewing, crediting,
  or preparing to publish anything under the Dark Matter Labs / Dm name (Medium,
  Substack, LinkedIn, grant proposals, client reports, blog posts, websites).
  Triggers: checking a draft against "the style guide" / "house style" /
  "Appendix A"; building a credit block or lineage; licensing (CC BY-SA / BY-NC),
  consent, or how to attribute a contributor, external framework, or visual;
  declaring AI use; classifying material sensitivity before using an AI tool;
  a self-risk assessment or whether peer review is needed; the pre-publication
  checklist; posting protocol; audience/register fit; coined terms;
  positionality; or the "words to use with care" / "AI-tells" list — even if the
  user doesn't name a guide.
---

# Dm publishing standards (four companion guides)

## In these wikis

The four guides govern anything published under the Dark Matter Labs name. Three house rules of
these wikis sit beside them, and win inside a wiki page:

- **Dashes.** The guide asks for a spaced dash in a published piece. In a wiki page, and in
  anything else these wikis write in their own voice, `ai-detox` and `tools/check_prose.py` refuse
  em dashes: use a comma, a colon or a new sentence. Quoted words keep their dashes.
- **Quotation marks.** The guide's curly single quotes are for the published piece. Wiki pages use
  straight double quotes, which the citation checker (`tools/quote_check.py`) reads.
- **House spellings.** Civilization takes a z and xCO keeps its lowercase x, checked by
  `tools/house_rules.py`. Otherwise British English, as the guide says.

Where a wiki also carries a project's own voice skill, that skill governs writing for the project;
this one governs anything that goes out under the Dm name. `ai-detox` still governs sentence
mechanics everywhere.


This skill operationalises Dark Matter Labs' four companion guides (2026,
Governance Gap Committee governance-transition work) so they can be **used**
while working, **audited** against a draft, and their mechanical parts
**enforced** consistently:

- **Style & Standards** — the craft of the output.
- **Attribution** — who is credited, and how (credit block, lineage, licensing,
  consent).
- **AI Usage** — the process *before* the others: safe, honest AI use.
- **Publishing** — risk assessment, peer review, checklist, and posting protocol.

The AI Usage Guide describes itself as the entry point across the others; a full
publishing lifecycle runs **AI pre-flight → draft → audit → attribute →
publish**.

## A necessary honesty about scope

These guides are explicitly "not gatekeeping mechanisms," and 'good style' is
not a single house voice. The skill respects that by splitting each guide into
two registers:

- **Deterministic / checkable** — Appendix A house conventions + word list
  (`scripts/mechanical_check.py`), and the Publishing risk-level mapping
  (`scripts/risk_assessment.py`). These are reliable, rule-based, and repeatable.
- **Judgment-based** — audience, complexity, coining, positionality, channel
  fit; sensitivity classification; whether a contribution is credited fairly;
  whether an argument is really yours. These are **flagged for human decision**,
  not graded. Coverage here depends on model reasoning and is **not guaranteed**
  to catch every issue — present findings as prompts for a human writer/reviewer.

This skill does not replace peer review, consent conversations, or legal advice
on copyright or IP terms.

## Reference files — read the ones the task needs

| File | Covers |
|---|---|
| `references/house-conventions.md` | Appendix A mechanics + "words to use with care" table |
| `references/writing-principles.md` | Style §1 Audience; §2 Complexity (+ complexity check) |
| `references/situating-and-positionality.md` | Style §3 Coined terms & situating; §4 Positionality, Indigenous frameworks, translation |
| `references/channels.md` | Style §5 channel/audience *matching* (what to write for each) |
| `references/attribution.md` | Contributor mapping, credit block, lineage, in-text/visual citation, licensing, consent, websites |
| `references/ai-usage.md` | Sensitivity classes, tool/account rules, using AI well, validation, AI pre-publish checks |
| `references/publishing.md` | Risk tests, peer-review prep, pre-publication checklist, posting protocol |

## Assets and scripts

- `scripts/mechanical_check.py <file> [--json]` — deterministic Appendix A audit.
- `scripts/risk_assessment.py [--irreversibility --exposure --sensitivity …]` —
  deterministic review-level calculator (interactive if run with no args).
- `assets/credit_block_template.md` — fill-in credit block + lineage.
- `assets/pre_publication_checklist.md` — combined Publishing + AI pre-publish list.

---

## Mode: AI PRE-FLIGHT (before material goes into an AI tool)

Trigger: the user is about to feed documents/data to an AI tool, or asks whether
something is safe to upload. Read `ai-usage.md`.

1. **Classify sensitivity**: public / internal / confidential / personal-
   identifiable / sensitive-personal. State the class and the rule (e.g.
   confidential → do not upload without explicit permission; sensitive-personal
   → do not upload). Apply **minimum necessary data** — extract/anonymise rather
   than uploading whole datasets.
2. **Check tool access & account**: prefer the shared org account; confirm what a
   connected tool can access, retention, and training use before connecting.
3. Only then proceed to drafting.

## Mode: DRAFT (apply the guides while writing)

Trigger: writing/rewriting something for publication under Dm.

1. **Audience and channel first** (`writing-principles.md` §1, `channels.md`).
   If unstated, ask the four-question audience test or infer and say so.
2. **Structure to carry the reader** — context → proposition → action; anchor
   abstraction in a concrete referent first.
3. **Beyond binary, propositional** — name what the status quo does well and
   what your proposal cannot yet do.
4. **Situate** (`situating-and-positionality.md` §3) — default to established
   terms; cite and mark departures; cross-reference prior Dm work. Coin only if
   the three tests pass, and justify it in the body.
5. **Positionality deliberately** (§4) — declaring is the default for public
   work but a judgment; flag personal-risk / Indigenous-context cases for
   peer/consent decisions.
6. **Use AI well if drafting with AI** (`ai-usage.md`) — bounded task, controlled
   source base, structured outputs, verify every claim.
7. **British English, plain and short**, applying Appendix A as you go.
8. Finish with the complexity check + `mechanical_check.py`.

## Mode: AUDIT (check an existing draft)

Trigger: "check this against the style guide", "is this ready to publish", "audit
this draft".

**Step A — deterministic checks (the reliable part).**
```bash
python scripts/mechanical_check.py path/to/draft.md      # or .txt / .docx
```
(.docx needs `pip install python-docx --break-system-packages`.) If scripts
cannot run here, do the Appendix A checks by hand and say so.

**Step B — judgment review (flag, don't grade)**, citing locations:
- *Audience & register*; *complexity & accessibility* (run the five-point
  complexity check; watch for "too AI"); *terms & situating* (coinage tests,
  discourse cited, prior Dm work linked); *positionality*; *channel fit* (status
  + intended reader stated near the top?).
- If AI was used: verify citations/figures/claims against primary sources; check
  for flattened complexity; check the argument is actually the author's.

**Step C — report** using the format below.

## Mode: ATTRIBUTE (credit the work)

Trigger: "build a credit block", "how do I credit …", licensing, consent, or
lineage questions. Read `attribution.md`; use `assets/credit_block_template.md`.

1. **Map contributors** across all types — foundational, condition-building,
   adaptation, production (incl. design & code), feedback. Name conceptual and
   departed contributors; flag any **background IP** (needs attribution *and*
   consent).
2. **Draft the credit block first, then seek consent** — share it and invite
   corrections rather than asking the open-ended 'how would you like to be
   credited?'. Respect anyone who does not want crediting.
3. **Lineage section** — prior work (authors + year), project context, ecosystem
   contributors, licence, invitation to add missing contributions.
4. **Citation** — hyperlink originals; contextualise unpublished internal work;
   credit external frameworks; be consistent in academic-style outputs. For
   visuals, follow the adapted/minor/unchanged rule.
5. **Licence** — default CC BY-SA 4.0; CC BY-NC 4.0 to restrict commercial use;
   flag funded-project/partnership IP terms to #help-publishing.
6. **Declare AI use** in the credit block if AI was used in any phase.

## Mode: PUBLISH (risk, review, checklist, posting)

Trigger: "do I need peer review", "is this ready", "how do I post this". Read
`publishing.md`; use `assets/pre_publication_checklist.md`.

1. **Self-risk assessment** — run the calculator:
   ```bash
   python scripts/risk_assessment.py            # interactive
   ```
   or pass `--irreversibility {low,medium,high} --exposure {contained,moderate,high}
   --sensitivity <flags>`. Output: proceed / one peer / structured (1–2 reviewers
   agreed at the start).
2. **If review is needed** — help draft the framing note (what it is / is not /
   what you need / what you're not asking for), a specific deadline, and effort
   estimate. Note the silent-consent rule.
3. **Walk the pre-publication checklist**; do not mark items the user has not
   actually confirmed.
4. **Posting protocol** — Google Doc + internal review first; post intention on
   #help-publishing; channel-appropriate version (`channels.md`); after Medium,
   add to the Dm Provocations publication.

---

## Audit report format

ALWAYS use this structure so reports are comparable across pieces:

```
# Dm publishing audit — <piece title / filename>
Primary reader (stated/inferred): …   Channel: …   AI-assisted: yes/no

## 1. Mechanical conventions (deterministic — mechanical_check.py)
[HIGH/MEDIUM/LOW/INFO] <rule> — <location> — <change>

## 2. Judgment review (flags for human decision — not a verdict)
### Audience & register
### Complexity & accessibility (five-point complexity check)
### Terms & situating
### Positionality & care
### Channel fit
### AI validation (if AI-assisted): citations/figures verified, flattened complexity, argument ownership

## 3. Attribution & publishing readiness
- Credit block / lineage present and consented?  Licence noted?
- Risk level (from risk_assessment.py) and review status
- Outstanding pre-publication checklist items

## 4. Strengths worth keeping
## 5. Summary (plain-language readiness; honest about what was not checkable)
```

## Things to get right (theory of mind for the reviewer)

- The guides' biggest stated craft frustration is **accessibility** — jargon
  with no way in, prose that reads "too AI". Weight it heavily.
- Appendix A's real test is **consistency**, not matching this skill's defaults.
- Do not flatten voice; diversity of writers and bleeding-edge ideas are to be
  **preserved**.
- Coining a term that already has an established name is a credibility risk;
  scrutinise coinages, but Dm's best work includes earned ones.
- **Attribution and consent are relational obligations**, not formalities —
  never invent or impose credit; draft-then-confirm.
- **Personal disclosure, Indigenous-knowledge handling, and confidential-source
  material** carry real human/legal cost — shared decisions requiring review and
  consent, never an automated call.
- AI can fabricate authoritative-looking sources — **verify every citation,
  figure, and claim** against primary sources before anything external ships.
