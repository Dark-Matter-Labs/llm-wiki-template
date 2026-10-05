# Publishing Guide

Covers self-risk assessment, peer review, the pre-publication checklist, and the
channel posting protocol. Peer review is not gatekeeping — it helps you tell
when independent judgement is enough and when another pair of eyes is warranted.

## Contents
- [Step 1 — Self-risk assessment](#step-1)
- [Step 2 — Preparing for peer review](#step-2)
- [Step 3 — Pre-publication checklist](#step-3)
- [Step 4 — Protocols to post](#step-4)

---

## Step 1 — Self-risk assessment {#step-1}
Three tests decide how much involvement from others you need before publishing.
`scripts/risk_assessment.py` computes the required review level from these
answers deterministically.

**Irreversibility** — if this is wrong/misleading/harmful, how easy to correct
after publication?
- Internal Notion doc: easy to edit → **low**
- Medium article: can be updated but already circulated → **medium**
- Submitted grant proposal or published policy paper: cannot be recalled → **high**

**Scope and exposure** — who sees it, how far does it travel?
- Report to a single funder, no public circulation → **contained**
- Blog post on a Dm social channel → **moderate**
- Major public launch (often with partners), keynote, media-facing → **high**

**Sensitivity** — does the content:
- Make claims that could be politically sensitive or misrepresent Dm's position?
- Draw on a colleague's/partner's work in ways they have not yet seen?
- Touch on lived experience, sensitive data, community voices, or Indigenous
  Cultural and Intellectual Property?
- Reveal information disclosed under explicit or implicit confidentiality (NDA,
  Chatham House, private conversation)?
- Represent a new or contested stance wildly different from what Dm has
  published before?

### Deciding the review level
| Situation | What to do |
|---|---|
| Low irreversibility + contained exposure + no sensitivity flags | Proceed. Use the Step 2 pre-publication checklist. |
| Medium irreversibility OR moderate exposure | Ask at least one informed peer to review. One is enough. |
| High irreversibility, high exposure, OR any sensitivity flag | Structured peer review: identify 1–2 reviewers (one domain expert, one with Dm brand/positioning knowledge) **at the start of the work, not the end**. |

---

## Step 2 — Preparing for peer review {#step-2}
A poorly framed request produces vague feedback. Prepare a short **framing
note**:
- **What this is**: format, intended audience, where it will be published.
- **What it is not**: scope boundaries ('this is not a policy position — it is a
  practitioner reflection').
- **What you need**: be specific (factual accuracy? tone? alignment with Dm's
  public positions? correct crediting?).
- **What you are not asking for**: if you do not need a structural rewrite, say
  so — reviewers default to thoroughness unless told otherwise.

**Set clear expectations**: a specific deadline (not 'when you get a chance');
an indication of effort ('fifteen minutes, not two hours'); any constraints
(imminent window, a partner who already approved their section). For high-
irreversibility/exposure work, agree reviewers at the start.

**The 'silent consent' rule**: set a clear deadline; if you have not heard back
by it, you have the authority to publish. Document the request and deadline.
Reviewing is a mutual responsibility — if you consent to review, respond within
the agreed timeline.

---

## Step 3 — Pre-publication checklist {#step-3}
Confirm each before publishing (see `assets/pre_publication_checklist.md`):
- [ ] Identified all contributors across text, design, visuals, code, and
      condition-building (best effort + documented decisions where at scale)
- [ ] Shared the proposed credit block with contributors; invited corrections
- [ ] Confirmed no confidential partner or client work is being disclosed
- [ ] Have consent for any colleague's background IP used
- [ ] External sources and frameworks credited and, where possible, linked
- [ ] Self-risk assessment complete; peer review done if it was required
- [ ] A Lineage and intellectual responsibility section is included
- [ ] The correct licence is noted
- [ ] Publication date set; named contributors notified; posted on
      #help-publishing

---

## Step 4 — Protocols to post {#step-4}
**Channels.** Primary: LinkedIn, Substack, Medium. Secondary: Instagram (visual-
first, video), YouTube (video), BlueSky (repost only when tagged). X/Twitter
deprecated.

**Steps**:
1. Draft as a Google Doc; complete internal team review first.
2. Share intention to post (with desired date) in #help-publishing, flagging if
   you need: copy review/feedback (light AI/LLM editing and spell/grammar checks
   are fine — but do not over-use AI for text generation); posting support;
   login/admin access (reach out to @tech); or nothing (just visibility).
3. After posting on Medium, add it to the Dm Provocations publication (top-right
   menu → Add to Publication → Provocations → Approve and Add).
4. Follow the crediting/attribution system (see `attribution.md`).
5. After posting, follow up with feedback and comments.

**Platform specifics**:
- **LinkedIn**: long-form text, 3,000-character limit. Prefer a PDF with the
  detail attached (images if no PDF). Tag partners/relevant people in the post
  or first comment.
- **Medium & Substack**: blog format.
- **Instagram**: visual-first; posts for major updates, stories for minor ones
  and sharing links.
- **X/Twitter & BlueSky**: 280 characters per post; can thread; images help.

(For editorial channel/audience *matching* — what to write for each — see
`channels.md`.)
