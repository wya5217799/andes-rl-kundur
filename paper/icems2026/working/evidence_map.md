# ICEMS 2026 evidence map

Cutoff: 2026-07-26

Paper title: *Decoupling-Oriented Coordination of Paralleled VSGs With
Multi-Agent Reinforcement Learning*

## Central claim

The paper evaluates a physically decoupled controller in which sustained
common-frequency restoration and aggregate transient support are frozen
classical layers, while MARL is restricted to a bounded hard-zero-sum
differential-inertia coordinate. The evidence supports the decomposition and
a synchronization improvement for one evaluated seed, but not overall MARL
superiority, multi-seed robustness, or unseen-bank generalization.

## Claim-to-source map

| Manuscript claim | Frozen source | Maximum wording |
|---|---|---|
| Slow active power has sustained restoration authority. | `results/r274_prospective_active_power_authority/active_power_authority_summary.json` | On the tested 24-case bank, droop--PI reduced full-horizon mean-frequency IAE by 58.63% and final-window common error by 77.29%, with paired 95% intervals wholly below zero and all guards passing. |
| A common inertia pulse adds transient value above the slow layer. | `results/r275_fast_md_authority/fast_md_authority_summary.json` | The frozen 3-s pulse improved all four registered fast endpoints by 4.29%--28.37%, with paired support and all guards passing. |
| Fast and slow benefits are additive rather than synergistic. | `results/r276_fast_slow_factorial/fast_slow_factorial_summary.json` | None of six endpoints cleared the registered non-additive interaction gate. |
| A differential allocation margin exists. | `results/r277_learning_gap_oracle/learning_gap_oracle_summary.json` | An outcome-seeing viewed-bank oracle improved synchronization by 25.64% and early inter-area IAE by 19.66%; this is an attainability upper bound, not a deployable controller. |
| The seed-49 shared policy improves synchronization. | `memory/rounds/R278/analysis_repair.json` | Synchronization loss improved by 13.96%, paired 95% CI [-20.45%, -4.71%]. |
| The same policy does not clear the inter-area co-primary gate. | `memory/rounds/R278/analysis_repair.json` | Early inter-area IAE improved by 7.48% in the point estimate, but the paired 95% CI [-14.67%, +0.59%] crossed zero; the prospective classification is `PILOT-NO-GO`. |
| The evaluated policy respects the registered contracts. | `results/r278_icems_residual_pilot_s49/icems_residual_pilot_summary.json`; R278 traces | All 24 trajectories completed. Action, storage, slow/common, fast-safety, and CVaR90 guards passed. Maximum commanded/actual storage power was below 0.314 pu and SOC remained within [0.486074, 0.511454]. |
| The original R278 invalid flag was a numerical audit defect only. | `memory/rounds/R278/analysis_repair.json` | The physical zero-sum tolerance was changed from 1e-8 to four float32 ULP (1.220703e-4); maximum observed error was 4.577637e-5. No trajectory, checkpoint, bootstrap sample, metric, or efficacy threshold changed. |
| The weighted ensemble from the digest is not a contribution. | `docs/research/2026-07-26_icems_evidence_sufficiency_audit.md` | A post-digest controlled audit did not isolate HAWE value beyond the selected seed, so it is omitted from the full method and headline claims. |

## Explicit exclusions

- No claim of reliable improvement on both MARL co-primary endpoints.
- No multi-seed, unseen-bank, topology, EMT/HIL, or deployment generalization.
- No stability certificate.
- No claim that the actuator is a unified physical GFM-BESS; the model uses
  PV+GENCLS VSG proxies with four independent GFL ESD1 storage devices.
- The R277 oracle is never presented as policy performance.
- The R278 analysis-only tolerance repair is disclosed and never described as
  retraining or a changed efficacy gate.

## Citation evidence

Primary bibliographic metadata was checked against publisher pages, DOI
records, PMLR/NeurIPS proceedings, institutional records, or the original
paper. Citations are used only for the claims stated in the manuscript:
VSG foundations, parallel-VSG restoration and damping, adaptive/MARL VSG
control, safe/risk-aware RL, TD3/CTDE, statistical evaluation, ANDES, and the
Kundur test system.
