---
round: R320
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R320 plan - nominal pole-cause diagnosis

**Opened**: 2026-08-03
**Driver**: answer Q-0075 by distinguishing structural loss of control or
observation from the frozen R319 pole placement before any redesign.
**Parent**: CLM-0790; CLM-0800; CLM-0805; Q-0075.

## TL;DR

Replay only the sealed R319 nominal matrices and gains. Recompute every
controller and corrected-observer pole, identify the modes above the unchanged
`0.995` ceiling, and test full controllability/observability plus normalized
PBH margins at those modes. If structurally eligible, attempt one fixed,
non-tuned real-pole template solely as a mathematical placement check. Load no
bipolar/mismatch examination, output-energy result, ANDES trace, EVAL profile,
distributed runtime, reward, agent, or training path.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete - re-run render.py only after the round closes. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0075 [opened R319] Which controller and observer eigenmodes caused R319's nominal pole rejection, are they controllable and observable under the exact delayed augmentation, and can one non-tuned pole-targeted repair be prospectively identified without loading the hidden examination?

## Recently Closed (last 3)

- Q-0074 closed-negative @ R319, by CLM-0805 - Can one full-order observer-based discrete-time quadratic regulator, synthesized directly on the one-sample-delay augmented realizations, pass offline pole, estimation, constraint, mismatch, and matched-comparison gates without reusing the rejected DC inverse or scalar grid?
- Q-0073 closed-positive @ R318, by CLM-0800 - Which frozen scalar candidates were rejected by the nominal augmented-pole gate versus the governed development traces, and can one analytically preconditioned timing or controller-form repair be defined without widening the outcome-seen grid?
- Q-0072 closed-negative @ R317, by CLM-0795 - What constrained common/differential feedback law can be synthesized and rejected offline before closed-loop testing without hiding surrogate error in gain tuning?

## Methodology

### Immutable parent and no-performance access

- Verify R319's seal, controller result, formal analysis, provenance, feed,
  claim, and all sidecars. R319 must remain `OBSERVER-LQR-NO-GO`, all validity
  guards must remain true, both arms must retain zero examination cases, and
  no retained-versus-deleted effect may exist.
- Restore the unchanged R316 retained realizations and reconstruct the R319
  cross-deleted models by the sealed Markov deletion, order-10 ERA, and `0.995`
  model-pole rule. Restore R319 feedback and observer gains exactly from the
  sealed result; do not resynthesize an LQR or observer.
- Do not construct or load R319 bipolar cases, mismatch transforms, output-
  energy rankings, hidden examination arrays, physical traces, or EVAL input.

### Pole replay and cause fields

- For each of two points and two arms, recompute controller poles of `A-BK`
  and corrected-observer poles of `(I-LC_m)A`. Stored-versus-recomputed maximum
  radii must agree within `1e-12`; otherwise return diagnostic conflict.
- Record every pole whose magnitude exceeds `0.995`, its complex value,
  magnitude, controller-versus-observer origin, point, and arm. Map it to the
  nearest open-loop augmented pole by absolute complex distance. This mapping
  is descriptive, not a modal-mechanism claim.
- Form controller controllability and observer observability matrices for each
  14-state augmented model. Use relative singular-value rank tolerance
  `1e-10` and require full rank.
- At every failed pole compute normalized PBH margin as smallest divided by
  largest singular value of `[lambda I-A, B]` for control and
  `[[lambda I-A],[C_m]]` for observation. A margin below `1e-10` is a
  structural failure under this registered numerical contract.

### One fixed placement feasibility template

- Only when all four augmented models are full rank and every failed-mode PBH
  margin is at least `1e-10`, attempt one controller pole vector of 14 unique
  real values evenly spaced from `0.90` through `0.98`. The corrected-state
  observer template preserves the augmentation's four structural zero poles
  and places its ten dynamic poles at unique real values evenly spaced from
  `0.80` through `0.94`.
- Use the same vectors for both arms and points, one `YT` placement call per
  controller/observer, relative tolerance `1e-6`, and at most 100 iterations.
  No target, call, tolerance, or interpretation changes after any placement
  result is visible.
- Placement passes only when every returned gain is finite, every achieved
  pole matches the sorted target within absolute `1e-8`, and maximum achieved
  controller/observer radii are at most `0.98`/`0.94`. Do not run this gain on
  a disturbance case in R320.

### Comparison and EVAL boundary

- R320 is a cause and mathematical reachability diagnosis, not an efficacy
  comparison. Arm differences are descriptive and `QUALIFY`; no retained-
  cross value, decoupling value, controller-family value, or physical claim is
  estimated.
- `EVAL-v2` is not applicable because no physical trace exists. Public-
  interface tests, deterministic replay, sidecars, and the formal diagnostic
  classifier own integrity.

## Gate

- `INVALID-POLE-CAUSE-DIAGNOSIS`: any source/hash, parent classification,
  zero-examination, matrix/gain shape, deterministic replay, pole-identity,
  case-access, artifact, or no-EVAL guard fails.
- `DIAGNOSTIC-CONFLICT`: the recomputed R319 maximum radius differs from its
  sealed value by more than `1e-12`, or the recomputed failed-mode set does not
  explain the registered controller/observer gate failures.
- `STRUCTURAL-POLE-NO-GO`: any relevant augmented pair is rank deficient or
  any failed-mode normalized PBH margin is below `1e-10`. Close Q-0075 and stop
  this full-order delayed state-feedback route.
- `TARGET-PLACEMENT-NO-GO`: all failed modes are structurally reachable and
  observable, but the one fixed placement template fails its finite, target-
  accuracy, or achieved-radius checks. Close Q-0075 and stop rather than search
  target poles.
- `POLE-TARGET-ELIGIBLE`: all structural and fixed-template checks pass. Close
  Q-0075 and authorize only one separately sealed model-only examination of
  this exact pole template under the unchanged governor and matched comparator.

Every outcome remains nominal and model-only. R320 authorizes no physical
closed loop, distributed implementation, reward, agent, or training.

## Asset protection contract

- Preserve R306--R319 artifacts, especially all R319 sources, seal, results,
  feed, claim, question, and verdict. Do not edit or repair them.
- New assets are limited to the R320 plan/seal, one pure pole diagnostic, one
  stable runner, focused tests, create-only machine results with sidecars,
  manifest/feed/claim/verdict/question/navigation reconciliation.
- Keep the fixed conference title exactly unchanged. Its coordination,
  distributed-agent, and learning terms remain prospective.

## Cross-references

- Dynamic-model authority: CLM-0790.
- Static pole-localization authority: CLM-0800.
- Observer-LQR no-go authority: CLM-0805.
- Active question: Q-0075.
