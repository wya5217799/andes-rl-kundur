---
round: R262
state: completed
opened: '2026-07-24'
closed: '2026-07-24'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R262 plan — R201 + droop action-blend dual-metric feasibility scan

**Status**: ACTIVE
**Opened**: 2026-07-24
**Driver**: The project goal requires one controller to improve both the
paper `cum_rf` metric and the project 11-axis `geo` metric, but R252 found
that legacy R201 and droop k=10 occupy opposite ends of the Pareto frontier.
R256-R259 identify the missing inductive bias as proportional disturbance
coupling. Test the smallest architecture-free hybrid before any retraining.
**Parent**: R201, R252/CLM-0445, R256/CLM-0470,
R257/CLM-0475, R258/CLM-0480, R259/CLM-0485, R261/CLM-0505

## TL;DR

Evaluate a pre-registered convex action blend
`a = (1-alpha) * a_R201 + alpha * a_droop(k=10)` on the canonical LS1+LS2
path for `alpha in {0, .1, .25, .5, .75, .9, 1}`. This is a zero-training
probe of whether droop's reactive bias can move the empirical dual-metric
frontier before investing in corrected recurrent retraining or imitation
warm-start infrastructure.

## Snapshot at plan-time (oracle as of 2026-07-24)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify
  1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried
  (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0008 closed-negative @ R252, by CLM-0415 — Verify paper-metric ranking
  persists at 500-ep paper convergence horizon
- Q-0021 closed-positive @ R252, by CLM-0231 — V4 env TGOV1 governors u=1.0
  in ANDES JSON but R08 Finding 3 says "completely ineffective" — which is
  true post-R37 refactor?
- Q-0005 closed-partial @ R186, by CLM-0350 — Why does TD3+LSTM seed 50
  collapse while seeds 49/51 converge?

## Methodology

1. Add a reusable hybrid action-function library and `scripts/eval_hybrid.py`;
   do not embed the controller in a round-specific one-off script.
2. Unit-test recurrent reset, endpoint identity, clipping, and agent-count
   validation on Windows without ANDES.
3. Load measured R201 checkpoint
   `results/r201_w1_hreg_tau005_s54/agent_{0..3}_best.pt`.
4. For each pre-registered alpha, run real ANDES V4 at seed 42 for 150
   control steps on LS1 and LS2. Generate fresh no-control siblings and
   write all traces under `results/r262_hybrid_blend/`; never reuse a
   truncated trace.
5. Score each alpha with the canonical `score_trace_files` path, recording
   both higher-is-better `geo` and less-negative-is-better `cum_rf`.
6. Compare against the measured endpoint records:
   R201 `geo=0.4152, cum_rf≈-0.0692`; droop k=10
   `geo=0.1792, cum_rf=-0.0367117`.
7. Treat R201 as a legacy-trained component: R261 proved its recurrent
   Bellman target was misaligned. A positive hybrid result is evidence for
   controller composition, not evidence that corrected TD3-LSTM has been
   trained successfully.

## Gate

Pre-registered outcome classes:

| Outcome | Criterion on one interior alpha | Decision |
|---|---|---|
| **DUAL GOAL MET** | `geo > 0.4152` and `cum_rf > -0.0367117` | The blend strictly beats both measured endpoints on both headline metrics; replicate across seeds and then retrain corrected recurrent agents. |
| **FOLLOW-UP CANDIDATE** | `geo >= 0.35` and `cum_rf >= -0.055` | Meaningful balanced point: retain at least 84% of R201 geo while closing at least 44% of the R201-to-droop paper-metric gap; replicate before any SOTA claim. |
| **PARETO ONLY** | Interior points trade one metric for the other but miss the balanced gate | Direct action blending does not achieve the research goal; use it only as a Pareto control baseline. |
| **INVALID** | Any failed/incomplete trace, endpoint mismatch beyond numerical tolerance, or scoring-basis ambiguity | Stop interpretation and repair the evaluation path. |

The strict research objective is not declared achieved from a single seed
alone. Even `DUAL GOAL MET` advances the status to a replication candidate;
it does not close the robustness requirement.

## Asset protection contract

- Do not modify V4 dynamics, paper anchors, R201 checkpoints, or R85 traces.
- All legacy headline fields remain explicitly on
  `metric_frequency_basis=legacy_control_hz`; retain R261 physical-frequency
  fields in every new trace.
- Add only reusable evaluation code, tests, and namespaced R262 outputs.
- No new algorithm-performance claim without both `geo` and `cum_rf`.

## Cross-references

- R252 / CLM-0445 — measured RL-vs-droop dual-metric Pareto frontier.
- R256 / CLM-0470 — RL saturated/over-actuated while droop was sub-saturated.
- R257 / CLM-0475 — smoothness inversion.
- R258 / CLM-0480 — direct sync-only reward collapses without `phi_abs`.
- R259 / CLM-0485 — droop tracks disturbance; R201 is decoupled.
- R261 / CLM-0505 — historical recurrent checkpoints use legacy target
  alignment and need corrected retraining for intended-algorithm claims.
