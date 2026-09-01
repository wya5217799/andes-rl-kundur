# Project intake review — R485 finite-record mechanism mathematics

> Routing note (2026-09-01): this review applies to the dated first return.
> A second, distinct return was subsequently replayed and compared
> adversarially. Use `../COMPARATIVE_ADVERSARIAL_REVIEW.md` as the current
> writing decision; retain this file to document the first verifier's
> cross-runtime comparison defect.

## Verdict

**`QUALIFIED PASS`**. The mathematical core is useful and sufficiently
self-contained for bounded paper language. The return package is preserved
byte-for-byte, but its claim that the supplied verifier passes unchanged is
not accepted on this repository runtime.

The accepted result is narrower than a causal mechanism claim:

1. under the registered common zero reset, the exact componentwise
   amplitude/slew recursion is total-variation diminishing, with the supplied
   terminal-residual strengthening;
2. the 24-policy fixed-previous diagnostic is a frozen-observation actor-path
   intervention, not an additive or closed-loop causal share;
3. the 24x4 constant-anchor result is aggregate RMS norm retention, not proof
   of a temporally static or dominant RMS source.

Nothing here changes R485 `VALID-MIXED`, the 121/208 endpoint count, the 0/208
complete-contract count, or R486's post-hoc status.

## Integrity and execution audit

- The returned folder contains the five requested files. All four payload
  entries in `SHA256SUMS` match.
- Static inspection found no network or subprocess path. The default verifier
  is read-only; writing occurs only with explicit `--write-result`.
- The verifier rebuilt the complete result from the original 31-entry input
  archive, including the checkpoint and four full trace files.
- Projector replay and stored action-delta replay have maximum absolute error
  zero. Actor replay on this runtime has maximum absolute error
  `7.5996e-7`, below the declared `1e-6` actor tolerance.
- A separate finite-grid check found no counterexample to the TV-diminishing
  inequality in 9,375 scalar sequences and reproduced the supplied RMS
  non-contraction counterexample. This supplements, but does not replace, the
  self-contained induction proof in `SOLUTION.md`.

## Verifier qualification

Running the returned verifier in comparison mode does **not** print `PASS`.
It reports eight numerical mismatches, all confined to
`identifiable_decomposition.rows[*].tv.constant_anchor`:

- maximum absolute difference: `8.5615e-5`;
- maximum relative difference: `9.1316e-6`;
- declared result-comparison tolerance: `2e-6`;
- structural/non-numeric mismatches: zero;
- changed thresholds, counts, dispositions, or manuscript numbers: zero.

The rebuilt result is preserved as `math_result.repo_rebuilt.json`. This is a
cross-runtime floating-point reproducibility defect in the returned comparison
gate, not evidence against the TV theorem or the finite-grid counts. Do not
describe the unmodified external verifier as repo-side `PASS`.

## Paper-safe result

The projector statement may be used as a compact lemma or displayed
inequality, bounded to the exact normalized componentwise recursion and common
reset. The mechanism wording should be:

> On the frozen observation paths, replacing the time-varying
> previous-executed-action actor input by its within-record mean reduced raw TV
> in all 48 tested channel-policy cases, with ratios no greater than 0.205.

For RMS, use:

> Constant-anchor raw RMS was at least 0.90 times actual raw RMS in 141 of 192
> tested channel-profile cases (M: 54/96; D: 87/96). This is aggregate norm
> retention, not temporal-static source dominance or pathwise closeness.

Do not use “previous-action feedback amplifies TV” without the frozen-path
intervention qualifier. Do not call a quasi-static setpoint the dominant RMS
source. Do not report the differences as nonnegative or causal mechanism
shares.

## Unresolved objects

The return correctly leaves four items unresolved:

- full-grid Jacobian/radius/secant distributions require the other 23 actor
  checkpoints and their actor-input paths;
- a symmetric two-factor Shapley allocation requires the missing
  `pi(mean observation, recorded previous action)` cell;
- backend-invariant replay of the recursive fixed-previous intervention
  requires its stepwise raw/projected arrays or a bitwise-locked runtime;
- full-grid temporal mean/variance and alignment claims require per-record
  action sums, sums of squares, and inner products or complete paths.

None is required for the current five-page paper. They must not be invented or
turned into a new experiment gate.

## Absorption boundary

- Accepted into the paper-writing evidence card: the projector inequality,
  finite-grid counts, and corrected mechanism wording.
- Retained as advisory/supporting material: representative Jacobians, local
  active-set radii, endpoint secants, and ordered decomposition contrasts.
- Not promoted: unique root cause, training causality, modified-controller
  plant behavior, endpoint preservation, stability, safety, convergence, or
  topology generalisation.

The proposed `manuscript_patch.tex` is acceptable only with this intake review
attached. Future writing should use its one displayed equation and bounded
counts in Discussion or a compact analysis paragraph, not as a new headline or
fourth main contribution.
