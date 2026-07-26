# ICEMS 2026 evidence sufficiency audit

**Audit date**: 2026-07-26

**Paper title under review**: *Decoupling-Oriented Coordination of Paralleled
VSGs With Multi-Agent Reinforcement Learning*

**Scope**: read-only audit of the submitted digest, R274-R278 evidence, and the
parked LaTeX skeleton. This document does not authorize another experiment or
manuscript writing.

## Bottom line

The current evidence is **conditionally sufficient for an honest
decoupling-and-evaluation paper**, but it is **not sufficient for a positive
MARL-superiority paper**.

The title can remain because the implemented controller genuinely contains a
multi-agent learning layer and the central technical object is a
decoupling-oriented, hard-zero-sum coordination constraint. However, the full
paper must say that the learned layer produced a statistically supported
13.96% synchronization-loss improvement while its 7.48% early inter-area IAE
improvement did not clear the registered uncertainty gate. It must not claim
that MARL reliably outperformed the strong classical reference overall.

No additional seed or fresh-bank run is authorized for the exact R278
contract. R278 prospectively required both co-primary endpoints to pass before
three-seed continuation. One failed, so stopping is the scientifically correct
outcome rather than missing execution.

## Submitted digest commitment audit

The submitted one-page digest was visually reviewed from
`C:/Users/27443/Downloads/ICEMS_2026_Digest(2).pdf`.

| Digest statement | Current evidence | Full-paper treatment |
|---|---|---|
| The work is decoupling-oriented coordination of paralleled VSGs with MARL. | Supported in a narrower and more physical form by the R274-R278 common/differential and fast/slow decomposition. | Retain. Define decoupling by control coordinates and actuator timescales, not by HAWE. |
| The reproduced DDIC reaches the published 6-s LS1/LS2 terminal targets closely. | Historical reproduction evidence exists, but this is not the main R274-R278 comparison and does not establish physical restoration quality. | Background or setup check only; never use it as the new method's main performance result. |
| HAWE makes a strong but seed-sensitive controller repeatable at inference time. | Deterministic re-evaluation is not evidence that weighting improved the selected actor, and the historical record does not separate HAWE value from a lucky seed. | Withdraw as a contribution. At most state that the initial ensemble interpretation did not survive stronger evaluation. |
| Explicit coupling, support-allocation, and coordinated-action targets are introduced. | Supported after correction: common restoration, common transient support, and differential inertia redistribution are now explicit and separately testable. | Retain with the corrected equations, metrics, and hard-zero-sum action contract. |

The digest title does not contain “HAWE”, so removing HAWE from the full method
does not require a title change. The method description and conclusion do
change materially; the full paper should acknowledge this as an experimental
refinement rather than silently repeating the digest claim.

## Claim-to-evidence matrix

| Candidate full-paper claim | Authoritative evidence | Status | Maximum defensible wording |
|---|---|---|---|
| Bounded slow active power restores common frequency. | R274 summary and CLM-0580. VSG-mean IAE -58.63%; final-window common error -77.29%; paired intervals and all guards pass. | Supported | The constrained droop-PI storage layer provides material sustained common-frequency authority in the tested model and bank. |
| A simple fast common-inertia pulse improves transient response above the slow layer. | R275 summary and CLM-0585. RoCoF -28.37%, peak -11.08%, synchronization loss -4.29%, early inter-area IAE -9.91%; all registered guards pass. | Supported | A frozen 3-s common-inertia pulse adds independent transient value under the validated slow layer. |
| The fast and slow layers create a special nonlinear synergy. | R276 summary and CLM-0590 classify `ADDITIVE-ONLY`. | Contradicted | The benefits are largely additive; complexity or “synergy” is not a contribution. |
| A disturbance-dependent differential allocation opportunity exists. | R277 oracle summary and CLM-0595. Outcome-seeing oracle: synchronization loss -25.64%, early inter-area IAE -19.66%, all guards pass. | Supported only as attainability evidence | The viewed-bank oracle establishes an attainable margin and motivates a learned allocator; it is not controller performance. |
| The shared hard-zero-sum MARL reliably improves both differential endpoints. | R278 repaired pilot analysis and CLM-0600. Synchronization -13.96%, 95% interval [-20.45%, -4.71%]; early inter-area IAE -7.48%, interval [-14.67%, +0.59%]. | Not supported | The policy improved synchronization with paired statistical support, while early inter-area benefit remained uncertain. |
| MARL is safe and respects the physical decomposition. | R278 action, completion, storage, energy, slow/common, safety, and CVaR90 guards. All 24 trajectories completed; no storage violations; hard-zero-sum audit passes at a float32-derived tolerance. | Supported for seed 49 on the viewed bank | The evaluated seed respected the registered physical and storage contracts on all 24 development cases. |
| MARL generalizes across training seeds and unseen disturbances. | Only seed 49 was run; the evaluation bank had already been viewed in R277. | Missing by stopped design | Make no multi-seed, unseen-bank, robustness, or generalization claim. |
| HAWE improves performance or seed robustness. | Historical selected-seed/ensemble records do not isolate weighting value. | Not supported | HAWE is not a contribution and should not appear in headline results. |
| The work establishes a unified physical GFM-BESS controller. | R274 uses `PV+GENCLS` plus an independent GFL ESD1 authority proxy. | Not supported | Describe the simulated hybrid actuator exactly; do not call it a unified GFM-BESS implementation. |

## Evidence integrity audit

All discovered SHA-256 sidecars in the audited R274-R278 result directories
were recomputed on 2026-07-26:

| Evidence directory | Sidecars checked | JSON files | Missing targets | Hash mismatches |
|---|---:|---:|---:|---:|
| `results/r274_prospective_active_power_authority` | 7 | 55 | 0 | 0 |
| `results/r275_fast_md_authority` | 27 | 27 | 0 | 0 |
| `results/r276_fast_slow_factorial` | 27 | 27 | 0 | 0 |
| `results/r277_learning_gap_oracle` | 147 | 148 | 0 | 0 |
| `results/r278_icems_residual_pilot_s49` | 26 | 26 | 0 | 0 |
| `memory/rounds/R278` | 2 | 2 | 0 | 0 |

The principal trace directories contain 240 JSON trajectories:
24 in R274, 24 in R275, 24 in R276, 144 in R277, and 24 in the R278 pilot.
R278 training completed 300/300 episodes and 4,500/4,500 real-ANDES
environment steps. Its frozen checkpoint SHA-256 is
`724f9edde39d5b68c913e91283e62c3fee6030af2fc9b8ccfd8770b5c7654ced`.

The immutable R278 summary originally classified the result `INVALID` solely
because a `1e-8` physical-zero-sum check was numerically impossible after
float32 decoding around an inertia value of 500. The separately retained
analysis repair changed only that audit tolerance to four float32 ULP
(`1.220703e-04`); the observed maximum was `4.577637e-05`. It did not change
trajectories, checkpoint, resampling, metrics, gates, or thresholds. The
repaired classification is `PILOT-NO-GO`, recorded by CLM-0600.

## Parked LaTeX skeleton audit

`paper/icems2026/` remains untracked and must not yet be treated as the
manuscript of record. Its current source conflicts with completed evidence in
four places:

1. it still defines `PILOT RESULT PENDING` and `TBD` result macros;
2. it says the full study reports a “complete seed set”, although the frozen
   pilot correctly stopped after seed 49;
3. it frames the third contribution as a sealed strong-baseline evaluation,
   but the R278 bank is a viewed development bank, not a fresh formal bank;
4. its conclusion is still future tense and does not state `PILOT-NO-GO`.

These are known placeholders, not evidence defects. They must be corrected
before the skeleton can be considered a draft, but they are intentionally
left untouched while manuscript writing is paused.

## Manuscript start gate

LaTeX writing may start only after all of the following are accepted:

- keep the existing title, but treat “with MARL” as the constrained method
  being evaluated, not a promise of superiority;
- make physical fast/slow and common/differential decomposition the primary
  contribution;
- report R278 as a partial signal and overall no-go against the registered
  two-endpoint gate;
- make no three-seed, fresh-bank, topology-generalization, unified-GFM-BESS,
  stability-certificate, EMT/HIL, or deployment claim;
- remove HAWE from the method, abstract contribution, headline table, and
  conclusion;
- preserve the original invalid summary and disclose the analysis-only
  float32 tolerance repair in the reproducibility or limitations text.

If the intended paper must instead claim that MARL is consistently superior,
the current evidence is insufficient and the existing R278 contract cannot be
rescued post hoc. That would require a newly authorized scientific objective,
new prospective protocol, and likely a title/method decision; it is not a
routine completion experiment.
