---
round: R321
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R321 plan - exact fixed pole-target examination

**Opened**: 2026-08-03
**Driver**: answer Q-0076 by running the exact R320 pole template through the
unchanged governed model-only bank without target, gain, or outcome-driven
search.
**Parent**: CLM-0790; CLM-0805; CLM-0810; Q-0076.

## TL;DR

Recompute the single R320 controller and corrected-observer template on the
same four augmented model pairs, preserve the sealed R319 scales, information,
plants, governor, development cases, and still-untouched examination, and
stop at the first failed prospective gate. Both arms must pass nominal poles,
finite gains and traces, and zero governed violations before the 80-case bank
is constructed. No ANDES, EVAL, physical control, distributed runtime, reward,
agent, or training path is authorized.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0076 [opened R320] Can the exact R320 fixed pole-targeted observer feedback pass nominal poles, finite estimation, unchanged governed development, the untouched bipolar/mismatch examination, the absolute practical floor, and the matched retained-versus-deleted comparison without any target or gain search?

## Recently Closed (last 3)

- Q-0075 closed-positive @ R320, by CLM-0810 — Which controller and observer eigenmodes caused R319's nominal pole rejection, are they controllable and observable under the exact delayed augmentation, and can one non-tuned pole-targeted repair be prospectively identified without loading the hidden examination?
- Q-0074 closed-negative @ R319, by CLM-0805 — Can one full-order observer-based discrete-time quadratic regulator, synthesized directly on the one-sample-delay augmented realizations, pass offline pole, estimation, constraint, mismatch, and matched-comparison gates without reusing the rejected DC inverse or scalar grid?
- Q-0073 closed-positive @ R318, by CLM-0800 — Which frozen scalar candidates were rejected by the nominal augmented- pole gate versus the governed development traces, and can one analytically preconditioned timing or controller-form repair be defined without widening the outcome-seen grid?

## Methodology

### Exact synthesis and parent authority

- Verify the R316 dynamic-model authority, the R319 sealed scales and hidden-
  examination state, and the R320 `POLE-TARGET-ELIGIBLE` analysis with all
  sidecars before preparing the R321 seal.
- For both operating points and both retained-versus-cross-deleted synthesis
  arms, rebuild the unchanged 14-state delayed realization. Use exactly the
  R320 14 controller targets from `0.90` through `0.98`, the four zero plus ten
  observer targets from `0.80` through `0.94`, `YT`, relative tolerance
  `1e-6`, at most 100 iterations, and one call for each gain. No target,
  method, tolerance, retry, gain scaling, covariance, or candidate search.
- Preserve the sealed R319 output scales exactly at both points and the four
  action scales of `0.36`; do not recompute them from cases. Require finite
  gains, achieved target error at most `1e-8`, controller radius at most
  `0.98`, and corrected-observer radius at most `0.94`. Record placement
  convergence warnings and returned iteration diagnostics descriptively; the
  achieved finite pole contract is the hard gate.

### Conditional model-only execution

- Execute each arm on the same full retained R316 plant with the unchanged
  delayed four-coordinate measurement, known point schedule, zero initial
  estimate and first command, four-coordinate-to-node mapping, and default
  power, ramp, SOC, timing, efficiency, energy, and system-base limits.
- Run the unchanged 32 nominal development cases: two points, two shapes, four
  coordinates, and two signs. Require both arms to have finite gains,
  estimates, innovations, outputs, actions, SOC, energy ratios, and zero
  constraint violations in addition to the nominal pole gates.
- Construct no examination case unless both arms pass every development gate.
  If admitted, run the unchanged 16 bipolar base cases under the five frozen
  mismatch transforms, producing 80 cases per arm. Require finite traces and
  zero violations for both arms.
- The retained arm passes only when every examination energy ratio to zero
  control is at most `0.98`, and its mean and worst ratios each improve on the
  cross-deleted arm by at least `0.02`. Deterministically replay the complete
  calculation before writing the create-only result.

### Comparison-identifiability contract

- **Scientific object**: one exact fixed pole-targeted full-order delayed
  observer-feedback construction per arm, not a controller family.
- **Information**: both arms receive the same delivered four-coordinate
  delayed measurement and known operating-point label; no global runtime
  statistic, neighbour message, or privileged state is added.
- **Action and execution**: both use the same four coordinate actions, node
  mapping, feasible set, actuator limits, timing, governor, and full retained
  executed plant. Execution remains centralized model-only arithmetic; it is
  not distributed-agent evidence.
- **Budget**: both use the same targets, method, tolerances, one placement call,
  model order, zero tuning candidates, cases, mismatch transforms, and metrics.
- **Single factor and estimand**: only the synthesis realization retains versus
  deletes named common/differential transfer blocks. The estimand is their
  finite-bank normalized output-energy value in this one construction.
- **Decision**: `ALLOW` for that bounded contrast if both arms execute the
  examination. Stay out of controller-family, general decoupling, physical
  robustness, voltage/current safety, distributed execution, communication,
  agent, learning, topology-generalization, hardware, and deployment claims.

### EVAL rule

- EVAL is `NOT-APPLICABLE-MODEL-ONLY`: R321 produces no physical trace. If a
  later separately registered physical round is authorized, run EVAL only
  after sealed trace completion as a diagnostic; a poor diagnostic may open a
  prospectively repaired rule, but may not retune, invalidate, or strengthen
  the sealed formal result after inspection.

## Gate

- `INVALID-POLE-TARGET-EXAMINATION`: any parent/hash, exact-target, source,
  matrix, sealed-scale, case-count, conditional-access, comparison, replay,
  artifact, no-physical, or no-EVAL guard fails.
- `POLE-TARGET-NO-GO`: the result is valid but either synthesis, nominal pole,
  finite development, governed-development, finite examination, governed-
  examination, every-case absolute improvement, or matched mean/worst gate
  fails. Close Q-0076 and stop this exact design without tuning.
- `POLE-TARGET-PASS`: every gate passes. Close Q-0076 and authorize only one
  separately registered physical deterministic-controller question; do not
  implement distributed agents or train a neural controller.

Every outcome is model-only and finite-bank. The conference title wording
stays exactly unchanged, while its coordination and learning terms remain
prospective.

## 资产保护契约

- Preserve every R306--R320 source, plan, seal, result, feed, claim, question,
  and verdict byte-for-byte; especially do not edit the sealed R319 controller
  module or the R320 diagnostic.
- New assets are limited to this plan and seal, one reusable fixed-pole
  synthesis module, one pure R321 classifier, one stable adapter, focused
  public-seam tests, create-only machine results with sidecars, manifest, feed,
  claim, verdict, question closure, and selected-line navigation refresh.
- Do not import ANDES, access another manuscript line for writing, change the
  conference title, define a reward, implement a distributed runtime, or start
  training.

## Cross-references

- Dynamic-model authority: CLM-0790.
- Rejected predecessor: CLM-0805.
- Exact mathematical eligibility: CLM-0810.
- Active question: Q-0076.
