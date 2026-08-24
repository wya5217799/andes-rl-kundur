# Learning re-verification + all-fresh source factorial launch decision (2026-08-25)

## Status

OWNER-APPROVED (2026-08-25, in conversation). The owner selected "launch both
phases" after (a) a measured-time correction — the R477 first training wave
(16 cells) measured 10,803 s wall, so 234 fresh training cells = 15 waves ≈
45 h plus evaluation ≈ 47-48 h total, NOT the initially misstated 14-16 h —
and (b) a cost/risk review of renting a cloud server, which the owner declined
after the review (rental ≈ USD 40-60/day for 64 vCPU/128 GB; environment
re-validation and capacity re-measurement would consume roughly the one day
saved, while re-introducing environment risk on the axis the R478 correction
just closed).

## Decisions

1. Launch the corrected-plan Phase 3 (minimal learning ladder) and Phase 4
   (all-fresh source factorial) as ONE successor round (R482), on the local
   host, 16 concurrent workers.
2. Frozen statistical design unchanged: n_star=26 fresh seeds 501-526, eight
   factorial arms, four profiles, 43,200 interaction steps per cell, log(1.10)
   materiality boundary, exact one-sided Wilcoxon signed-rank at the boundary,
   Holm over four hypotheses, FWER 0.05.
3. Training budget unchanged (43,200 steps/cell). Cutting it would break
   comparability with every historical contract and invalidate the frozen
   power plan; owner accepted the unchanged budget after discussion.
4. Experiment-termination clause: after R482 closes, the corrected plan's
   experiment program is exhausted — Phase 1/2 closed (R478/R481), Phase 3/4 =
   this round, Phase 3D / the energy-port residual learner formally excluded
   because the energy-port claim is terminal (CLM-1490). Remaining work =
   manuscript lane only. Any new experiment requires a fresh owner decision
   and a new round.
5. Owner review gate: after the code is written, NO execution (no WSL/ANDES
   invocation, no rehearsal, no training) before the owner reviews the code
   and plan. Notify the owner at each launch moment.
6. External audit `gpt_pro_md_base_conversion_impact_answer_20260825`
   reviewed and registered: consistent with the route; adds an offline
   recomputation list and a forbidden-statement list for the manuscript lane;
   no design change to R482.

## Binding conditions

- All six statistical-audit pre-registration fixes close before the seal.
- Dual code/design review with one adversarial reviewer before the seal.
- Seal commit before execution; no in-round patching or retry.

## Cross-references

- paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md
- paper/yang_md_decoupling_marl/working/prospective_direct_md_successor_decision_20260825.md
- paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json
- memory/rounds/R481/plan.md (deterministic gate that opened this round)
