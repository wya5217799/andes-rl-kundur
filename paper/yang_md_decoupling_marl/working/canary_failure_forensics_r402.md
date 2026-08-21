# Canary failure forensics — R402 CD-MATD3 design defects

- **Status**: active (analysis input for the successor design decision)
- **Date**: 2026-08-15
- **Input**: sealed R402 canary bank (`results/research_loop/r402_cd_matd3_canary/`,
  decision artifact `formal_analysis.json`, endpoint table
  `endpoint_table.json`), training manifests and checkpoints.
- **Tool**: `probes/canary_failure_forensics.py` (re-runnable, read-only);
  data dump `tmp/r402_forensics.json` (sha256
  `a4c53f2f16106cc28909d6749fc7c1f9fb01de842164cff198f6ac3236b7cedd`).
- **Scope**: post-hoc analysis of sealed data only; no new physics was run and
  no classification was changed.

## Verified findings (ordered by causal weight)

1. **The common-mode constraint was deleted during training.** The Lagrangian
   multiplier fell from its 1.0 start to 0.00-0.14 in all six CD-MATD3 runs
   and stayed near zero, because the frozen per-episode budget (3.0) sits far
   above the actual training-time common cost scale (per-episode C_c between
   0 and 4.8, median about 2).  With a 0.05 dual step the multiplier cannot
   recover.  The actor objective therefore minimized only the differential
   channel for essentially the whole run.  Evidence: checkpoint multiplier
   payloads and the manifests' `lagrange_trace` and
   `episode_common_costs`; final values reproduce the dual arithmetic
   exactly.
2. **The reward contains no action-effort term.** Both cost channels depend
   only on frequency and power disagreement, so bang-bang actions are free.
   Evaluation shows 6.4-19.1% of steps pinned at the 0.25 slew bound (0.4%
   for the deterministic reference) and mean action magnitude 4-6x the
   reference.
3. **Even the unconstrained differential chase failed.** With the constraint
   off, the CD arms' own differential cost totals (2.96-5.98 over the bank)
   remain 3.1-6.3x worse than the deterministic reference (0.95).  A
   per-record regression of differential cost on action magnitude gives
   inconsistent signs (-0.18/+0.17/-0.03), so large swings do not explain it;
   the four-actor joint critic with persistent 0.1 exploration noise most
   plausibly failed to converge within 43200 steps (high seed variance,
   no stored loss curves to confirm directly).
4. **Runtime messages changed the policy but added no value.** Message-versus-
   no-message action correlation is about zero (-0.14/0.04/0.15) and the
   message arm is the worst on both registered endpoints; under a
   training-only joint critic the runtime neighbour channels are redundant
   information plus noise.
5. **The scalar baseline also lost to the deterministic reference.** The
   Yang-style scalar reward (which does carry action-cost terms and keeps
   action magnitude low) still ends 2.9-4.1x worse on both endpoints and
   worse on common cost (50-57 vs 29.6).  This is consistent with the R399
   finding that the selected deterministic law sits near the practical
   frontier of its family on this formulation.

## Causal summary

The canary failure is a design outcome, not a verdict on the learner class:
a mis-calibrated safety budget removed the common-mode constraint, a
missing action-effort term made bang-bang free, and the remaining
unconstrained differential objective was not converged within the frozen
interaction budget; messages then contributed noise without information.

## Recommendations for any successor design

1. Replace the adaptive dual with a frozen common weight (no dead zone by
   construction) or re-calibrate the budget to the measured cost scale.
2. Add an action-magnitude cost to the differential channel.
3. Store full per-episode diagnostics (returns, critic losses, per-channel
   costs) for convergence auditing.
4. Keep the three-arm message attribution structure; the message question
   remains the object of study.
5. A successor canary requires a fresh unseen bank and fresh seeds; the R402
   profiles are disclosed and burned as unseen evidence.

## Disposition

This memo is a decision input, not an evidence claim.  Its findings feed the
successor design decision recorded in the route amendment that follows it.
