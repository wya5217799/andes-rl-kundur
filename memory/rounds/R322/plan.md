---
round: R322
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R322 plan - development-only authority diagnosis and one analytic repair

**Opened**: 2026-08-03
**Driver**: answer Q-0077 by separating placed-gain, estimation-error, and
governor-projection effects on the registered development bank before any new
holdout or physical work.
**Parent**: CLM-0790; CLM-0810; CLM-0815; Q-0077.

## TL;DR

Recompute the exact R321 designs from its outcome-free seal, use only the
unchanged 32 nominal development cases, and decompose each raw command into
true-state and estimation-error parts before the node governor. Compare the
original observer feedback with an exact-state governed counterfactual under
prospective dominance signatures. Then derive at most one common scalar from
the registered power and ramp ceilings, apply it once to both arms' feedback
gains, and reject or admit that actuator-normalized candidate on development
only. Never load an R321 examination case or outcome field.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0077 [opened R321] Which development-only mechanism dominates R321's near-continuous governor intervention and output-energy amplification - placed feedback gain, corrected-observer transients, governor projection, or their interaction - and can one analytic repair be fixed before any fresh holdout?

## Recently Closed (last 3)

- Q-0076 closed-negative @ R321, by CLM-0815 — Can the exact R320 fixed pole-targeted observer feedback pass nominal poles, finite estimation, unchanged governed development, the untouched bipolar/mismatch examination, the absolute practical floor, and the matched retained-versus-deleted comparison without any target or gain search?
- Q-0075 closed-positive @ R320, by CLM-0810 — Which controller and observer eigenmodes caused R319's nominal pole rejection, are they controllable and observable under the exact delayed augmentation, and can one non-tuned pole-targeted repair be prospectively identified without loading the hidden examination?
- Q-0074 closed-negative @ R319, by CLM-0805 — Can one full-order observer-based discrete-time quadratic regulator, synthesized directly on the one-sample-delay augmented realizations, pass offline pole, estimation, constraint, mismatch, and matched-comparison gates without reusing the rejected DC inverse or scalar grid?

## Methodology

### Parent and no-examination boundary

- Verify the R321 formal-analysis file and sidecar by its already registered
  whole-file hash only; do not parse its case, arm, comparison, or metric
  fields. Load only the R321 prospective seal, R316 dynamic model, and sources
  needed to reconstruct the exact four designs.
- Preserve the R321 pole targets, placement method/tolerances/one-call budget,
  sealed output/action scales, retained versus cross-deleted synthesis models,
  full retained executed plants, delayed measurement, known point, node
  mapping, governor, initial conditions, and all limits.
- Define only the R319/R321 32-case nominal development bank. The adapter has no
  bipolar case builder, mismatch-transform builder, ANDES, EVAL, physical,
  distributed, reward, agent, or training command.

### Development-only causal decomposition

- Replay the original observer feedback and independently reconstruct the true
  delayed augmented state from each full retained plant and applied action.
  At every step verify `raw observer command = exact-state command +
  estimation-error command` within absolute `1e-10` in coordinate and node
  bases.
- Record raw power and raw ramp ratios to the unchanged ceilings, projection
  residual, intervention count, exact-state versus estimation-error command
  energies, and normalized output energy. Reconstruct the applied action and
  plant output within `1e-10`; any mismatch is invalid.
- Run one privileged exact-state governed counterfactual on the same plant,
  disturbance, limits, and timing. It is diagnostic only and cannot become a
  deployment or information-pattern baseline.
- Pre-register `OBSERVER-TRANSIENT-DOMINANT` only when exact-state governed
  feedback passes the `0.98` every-case floor and reduces mean output energy by
  at least 50 percent versus observer feedback. Pre-register
  `GAIN-AUTHORITY-DOMINANT` only when exact-state governed feedback still fails
  every case, exact-state raw power or ramp exceeds twice its ceiling in every
  case, and the median estimation-error command norm is at most half the raw
  observer command norm. Otherwise return `MIXED-MECHANISM`.

### One analytic actuator-normalized repair

- Across both arms and all original observer-feedback development traces,
  compute one common scalar as the minimum of one, inverse worst raw-node-power
  ratio, and inverse worst raw-node-ramp ratio. This formula, ceilings, and
  pooling are fixed before execution; no scalar grid, retry, clipping change,
  or arm-specific scalar is allowed.
- Multiply only both arms' feedback gains by that scalar; preserve observer
  gains and every other contract field. Run one development replay.
- The candidate is eligible for a separately sealed fresh holdout only when
  both arms retain finite nominal controller/observer poles at radius at most
  `0.995`, all traces are finite with zero checked violations, the retained arm
  meets the `0.98` every-case absolute floor, and retained mean and worst ratios
  improve on cross-deleted by at least `0.02`. No fresh holdout is run in R322.

### Comparison and EVAL boundary

- The mechanism decomposition is descriptive and development-only. The common
  repair scalar keeps information, action, plant, limits, timing, cases, model
  order, and tuning budget matched; only retained-versus-deleted synthesis
  blocks differ. Any comparative statement is limited to this reused
  development bank and cannot be a paper efficacy result.
- EVAL is `NOT-APPLICABLE-MODEL-ONLY` because no physical trace exists. A later
  physical round, if ever authorized, runs EVAL after sealing as diagnostic
  only and cannot use it for retrospective tuning.

## Gate

- `INVALID-DEVELOPMENT-DIAGNOSIS`: any source/hash, exact-design, no-
  examination, matrix, decomposition identity, replay, case, scale, comparison,
  artifact, no-EVAL, or no-physical guard fails.
- `MECHANISM-NOT-IDENTIFIED`: the result is valid but neither dominance
  signature holds. Close Q-0077 without selecting a repair.
- `ACTUATOR-NORMALIZED-REPAIR-NO-GO`: one dominance signature holds, but the
  single common analytic scalar fails any nominal, finite, governed, absolute,
  or matched development gate. Close Q-0077 and stop this repair.
- `ACTUATOR-NORMALIZED-REPAIR-ELIGIBLE`: one dominance signature holds and the
  single common scalar passes every development gate. Close Q-0077 and
  authorize only one separately sealed fresh model-only holdout.

Every outcome remains development-only. It authorizes no physical control,
distributed implementation, reward, agent, training, robustness, safety,
topology-generalization, or title-result claim.

## 资产保护契约

- Preserve every R306--R321 source, plan, seal, result, feed, claim, question,
  and verdict byte-for-byte. Do not edit sealed controller or runner modules.
- New assets are limited to this plan/seal, one reusable decomposition module,
  one pure classifier, one stable development-only adapter, focused public-seam
  tests, create-only machine results with sidecars, manifest/feed/claim/verdict,
  question transition, and selected-line navigation refresh.
- Keep the conference title exactly unchanged. Do not load the used 80-case
  examination into calculation, run ANDES, define a reward, implement a
  distributed runtime, or train a neural controller.

## Cross-references

- Dynamic-model authority: CLM-0790.
- Exact nominal template authority: CLM-0810.
- Exact-template no-go: CLM-0815.
- Active question: Q-0077.
