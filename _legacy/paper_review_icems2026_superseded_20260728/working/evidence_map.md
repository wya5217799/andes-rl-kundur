# ICEMS 2026 evidence map

Cutoff: 2026-07-27

Paper title: *Decoupling-Oriented Coordination of Paralleled VSGs With
Multi-Agent Reinforcement Learning*

## Central claim

The full paper fixes sustained common-frequency restoration and aggregate
transient support before learning. Shared MARL and a size-matched centralized
TD3 actor may change only one bounded, hard-zero-sum differential-inertia
coordinate. On an independent 24-disturbance bank and across three predefined
training seeds, both learned controllers improve the two primary endpoints
relative to \(q=0\), but the centralized actor is consistently stronger.
Therefore, the evidence supports constrained learned differential allocation;
it does not support incremental value from the multi-agent factorization.

## Claim-to-source map

| Manuscript claim | Frozen source | Maximum wording |
|---|---|---|
| Slow active power has sustained restoration authority. | `results/r274_prospective_active_power_authority/active_power_authority_summary.json` | On the tested 24-case development bank, droop--PI reduced full-horizon mean-frequency IAE by 58.63% and final-window common error by 77.29%, with paired 95% intervals wholly below zero and all guards passing. |
| A common inertia pulse adds transient value above the slow layer. | `results/r275_fast_md_authority/fast_md_authority_summary.json` | The fixed 3-s pulse improved all four fast endpoints by 4.29%--28.37%, with paired support and all guards passing. |
| Fast and slow benefits are additive rather than synergistic. | `results/r276_fast_slow_factorial/fast_slow_factorial_summary.json` | None of six endpoints cleared the registered non-additive interaction gate. |
| A differential allocation margin exists. | `results/r277_learning_gap_oracle/learning_gap_oracle_summary.json` | An outcome-seeing development-bank oracle improved synchronization by 25.64% and early inter-area IAE by 19.66%; this is an attainability upper bound, not a deployable controller. |
| The causal comparator is reproducible and was fixed before the independent bank. | `memory/rounds/R279/causal_development_seal.json`; `results/r279_causal_development/causal_development_summary.json` | The comparator is bounded memoryless area-frequency/RoCoF feedback. Nine gain pairs were fixed prospectively; among candidates meeting all checks, the lowest worst-location score selected \((k_f,k_r)=(0,0.25)\), which was then frozen. |
| The evaluation bank is independent of controller outcomes. | `results/r279_fresh_bank/formal_bank.json`; `results/r279_fresh_bank/screen_summary.json` | After all six learned checkpoints were fixed, seed 2026072704 generated 24 new magnitudes. A controller-blind \(q=0\) feasibility screen accepted all cases without redraw or exclusion. |
| Centralized TD3 improves both primary endpoints relative to \(q=0\). | `results/r279_formal_evaluation/formal_summary.json`; corrected action audit in `results/r280_r279_action_audit_correction/correction_summary.json` | Across three predefined seeds, the signed effects were -24.35% [-31.50%, -17.48%] for synchronization loss and -17.04% [-24.60%, -8.96%] for early inter-area IAE; both criteria passed. |
| Shared MARL improves both primary endpoints relative to \(q=0\). | Same R279/R280 sources | Across three predefined seeds, the signed effects were -16.79% [-24.73%, -5.81%] for synchronization loss and -9.54% [-17.19%, -0.60%] for early inter-area IAE; both criteria passed. |
| Multi-agent factorization adds no incremental value on this benchmark. | Same R279/R280 sources | Shared MARL was worse than centralized TD3 by 9.98% [1.04%, 26.13%] in synchronization loss and 9.04% [3.09%, 19.54%] in area IAE; all three paired seeds favored centralized TD3 on both endpoints. |
| The causal comparator did not explain the learned gains. | `results/r279_formal_evaluation/formal_summary.json` | The fixed causal comparator did not clear both materiality gates. This does not establish superiority over classical differential control as a class. |
| The evaluated controllers respected the registered contracts. | R279 formal traces and R280 correction summary | All 192 trajectories completed. Action magnitude, slew, active-window, storage, SOC, saturation, relative no-harm, and CVaR90 checks passed after the representation-aware audit correction. |
| The R280 change was a numerical audit correction only. | `results/r280_r279_action_audit_correction/correction_summary.json`; `memory/rounds/R280/verdict.md` | Five float32 slew checks changed from false to true under the prospectively sealed one-ULP rule. No trajectory, checkpoint, effect estimate, bootstrap sample, or efficacy threshold changed, and no new ANDES trajectory was generated. |
| The weighted ensemble from the digest is not a contribution. | `docs/research/2026-07-26_icems_evidence_sufficiency_audit.md` | A post-digest controlled reconstruction did not isolate HAWE value beyond selection of a favorable actor, so the full paper omits HAWE and states the transition explicitly. |

## Explicit exclusions

- No claim that MARL is necessary, superior to centralized TD3, or the source
  of the measured learning benefit.
- No claim that the tested causal controller represents classical differential
  or mutual-damping control as a class.
- Three predefined seeds exclude a single lucky-seed explanation on this bank;
  they do not characterize the wider training-seed population.
- No topology, EMT/HIL, stability-certificate, communication-failure, or
  deployment generalization.
- No claim that zero-sum input projection proves closed-loop modal or dynamic
  decoupling.
- No claim that the actuator is a unified physical GFM-BESS; it uses
  PV+GENCLS VSG proxies with four independent grid-following ESD1 devices.
- The R277 oracle is never presented as causal policy performance.
- The R280 audit correction is never described as retraining or a changed
  efficacy gate.

## Citation evidence

Bibliographic metadata is checked against publisher pages, DOI records,
PMLR/NeurIPS proceedings, institutional records, or the original paper.
The two 2026 additions cover coordinated MARL virtual-inertia/load-frequency
control and learned inertia--damping adaptation with explicit power-decoupling
control; the manuscript distinguishes their broader joint-control objectives
from its matched architecture-identifiability question.
