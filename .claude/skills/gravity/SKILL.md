---
name: gravity
description: Measure the repo's centre of mass and trajectory, and read inputs against both. Use when the owner asks "what's the gravity", "what's the trajectory", "where does this sit relative to the repo", "run the gravity check", or weekly from the reflect skill. Deterministic instrument (stdlib Python) — routes attention, never certifies.
---

# Gravity — the wiki's mass and trajectory, measured

The computational companion to the repository-gravity model (see the notes below for the model and
its constraints). One script, four modes, no dependencies beyond python3 + git.

## The model in one paragraph

Every wiki page body is a TF-IDF vector in the corpus's own term space (IDF lens from the
current corpus, so all snapshots are comparable). Each page is weighted by structural mass
(1 + ln(1 + inbound wiki-links)). **Gravity** G(t) = the mass-weighted centroid. **Trajectory**
V = G(t₂) − G(t₁), reconstructed from git snapshots; its rising/falling terms are the
human-readable direction of motion. An **input** d reads against both: radial r = cos(v_d, G)
(alignment with the mass), tangential τ = cos(v_d − G, V) (ahead of / behind / orthogonal to
the motion), novelty n = 1 − nearest-page cosine.

## Running it

From the repo root:

```
python3 .claude/skills/gravity/compute_gravity.py weekly
python3 .claude/skills/gravity/compute_gravity.py snapshot [--at 2026-07-10]
python3 .claude/skills/gravity/compute_gravity.py series --dates 2026-07-06,2026-07-10,2026-07-16
python3 .claude/skills/gravity/compute_gravity.py eval path/to/incoming-doc.md [--window 7]
```

- **weekly** — the standing report: current snapshot, 7-day centroid displacement, dispersion
  change (spreading vs tightening), rising/falling terms, and the pages most ahead of / behind
  the motion. The `reflect` skill runs this and folds the output into its §5.
- **series** — the trajectory over arbitrary dates: per-leg displacement |V|, direction
  persistence (cos between successive legs — is the motion holding a direction or jumping
  ingest to ingest?), rising/falling terms per leg.
- **eval** — read one or more incoming documents against G and V before/after ingesting.
  Note: a file already in `wiki/` self-matches (novelty ≈ 0); true inputs should be raw
  drafts or external documents.

## Interpreting the numbers (ordinal, always)

- **r high, τ ≈ 0 or negative** — the input confirms the mass and sits behind the motion:
  filing / prior-mass anchor. Fine in moderation; if *everything* reads this way, the Rσ
  reinforcement alarm fires.
- **τ strongly positive** — the input rides or extends an active turn (reinforcement or
  acceleration — check whether the turn's per-leg |V| is growing). Acceleration with no
  drag entries in the window is the runaway flag.
- **τ strongly negative with r high** — drag: the held position resisting the motion. These
  are precious; log them, don't smooth them.
- **r low, |τ| low, n high** — deflection: a new direction. Provenance decides whether it's
  exploration or scatter.
- Direction persistence rising across legs = the trajectory is holding a heading; persistently
  near-zero = motion is ingest-noise, not a trajectory.

## Hard constraints

- The readings are **ordinal tripwires, never scores or targets**. Never optimise any of them.
- The instrument **opens questions; it never certifies** "we are learning" / "we have
  drifted" — that verdict is the owner's.
- Numbers accompany, never replace, the classified delta ledger (radial × tangential ×
  provenance) described above — the semantic field sees vocabulary,
  not meaning; a paraphrase drifts less than it should and a synonym drifts more.
- Always pair a surprising reading with the git/log evidence before surfacing it.
