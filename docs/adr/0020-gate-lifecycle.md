# ADR-0020: Gate lifecycle — evidence-based demotion for model-capability rules

- **Status:** Accepted
- **Date:** 2026-08-17
- **Deciders:** repository owner and agent governance review
- **Related:** ADR-0007, ADR-0008, ADR-0011, R86, R246, R291, CLM-0430

## Context

Many hard gates in `CLAUDE.md` are tombstones of specific agent failures:
R246 burned ten rounds on an estimated baseline, so `measured > estimated`
became a hard rule; CLM-0430 showed `geo` and `cum_rf` moving in opposite
directions, so dual-metric citation became a hard rule; R291 caught claim
statements forking feed substance, so byte/line budgets became hard rules;
pre-R339 context compression reopened in-flight rounds, so the
`--strict-no-active` lock became a hard rule.

Those gates encode two different things.  Some encode scientific or
reproducibility epistemology — true regardless of how capable the agent is
(a baseline is measured or it is not; `V4` is bit-identical or it is not).
Others encode model-capability assumptions — they exist because a weaker
model mis-estimated, over-wrote, or forgot.  As model capability improves,
rules of the second kind can over-freeze the process; the owner asked for a
self-optimization mechanism instead of immortal rules.

Blanket relaxation is unsafe: every gate is a tombstone of a real, expensive
failure.  Relaxation therefore needs the same discipline the repository
applies to science: evidence first, measured not estimated, automatic
re-tightening on recurrence, and a human checkpoint only on the
consequential, permanent step — never on the mission's critical path.

## Decision

Introduce a per-gate lifecycle with a machine-readable registry
`docs/repo-hygiene/gate-registry.json` and the CLI
`memory/tools/gate_lifecycle.py`.

1. **Classification.** Every load-bearing gate in `CLAUDE.md` is registered
   as `locked` (science / reproducibility / human-facing — never demotable)
   or `soft` (model-capability guard — demotable).
2. **States.** `hard` → `warn` → `advisory` → `retired`.  `retired` is
   recorded only when the prose rule and its detector are both removed in a
   governance edit.
3. **Demotion.** A `soft` gate is demotable only when (a) its detector
   remains in place — demotion lowers ceremony, never the guard — and (b)
   `audit` shows at least `threshold_rounds` rounds since the last recorded
   recurrence or attestation (`clean_since_round`).  Permanent demotion
   requires operator approval, a recorded pre-grant, or a recorded override.
4. **Long-task paths (approval off the critical path).**
   - `provisional` — a one-step demotion (hard→warn) that needs **no
     approval**: the agent may take it mid-mission when the gate is
     audit-eligible and `provisional_allowed` is true, and it **expires
     automatically** after `provisional_ttl_rounds`; expiry lapses the
     authority by computation and the operator may `ratify` it into a
     permanent demotion afterwards.  Resource-safety soft gates
     (`seal-capacity-evidence`, `cold-start-budget`,
     `strict-no-active-lock`) set `provisional_allowed: false` — a
     provisionally relaxed capacity budget is how long tasks burn a machine.
   - `grant` / `revoke` — the operator pre-authorizes permanent demotion
     for one gate, up front, once; subsequent eligible demotions proceed
     without stopping.  The approval is moved from per-event to per-gate.
5. **Re-promotion is automatic.** `flag` records a recurrence of the
   guarded failure mode; a non-`hard` soft gate jumps straight back to
   `hard` and any provisional is cleared.  The safety direction needs no
   approval and no expiry.
6. **Demotion is authority, not enforcement.** A recorded demotion
   authorizes one relaxation edit of the prose rule (and its detector) in
   the same governance change.  Provisional authority is bounded by its
   TTL: if the agent consumes it with a file edit, the edit must be
   ratified or reverted before expiry — an expired provisional plus a
   surviving file edit is an inconsistency to repair in the next
   governance edit, and `list`/`audit` surface it.
7. **No backfill.** Clean clocks start at registry creation (R410).  Old
   failure-free history is not inferred retroactively — the same
   `measured > estimated` discipline, applied to governance itself.
8. **No new per-round ceremony.** The tool is on demand; nothing is added
   to the round open/close sequence.

## Current classification (seed)

Locked: `measured-over-estimated`, `dual-metric`, `topology-eig-gates`,
`v4-bit-identical`, `paper-assets-round-first`, `andes-wsl-only`,
`pi-plain-language`, `single-source-fact-allocation`, `atomic-reservation`,
`no-simulink-chase`.

Soft with `provisional_allowed: true` (style/verbosity guards; first
demotion candidates): `statement-byte-cap`, `verdict-line-cap`,
`caveman-ai-compactness`, `feed-single-write`, `plan-first-nontrivial`.

Soft with `provisional_allowed: false` (resource/safety guards; permanent
path only): `strict-no-active-lock`, `cold-start-budget`,
`seal-capacity-evidence`.

## Consequences

- Positive: rules stop being immortal; relaxation is measured, recorded,
  and reversible; the safety direction is fully automatic; the relaxation
  direction never blocks a long mission (provisional + grant), while the
  permanent, consequential step keeps a lazy, optional human checkpoint;
  the paper path (round open/close) is untouched.
- Negative: one more registry and one more tool to maintain; provisional
  authority is deliberately unavailable for resource-safety gates and for
  gates below the clean threshold — in those cases the human checkpoint is
  the point, not an accident of design.
