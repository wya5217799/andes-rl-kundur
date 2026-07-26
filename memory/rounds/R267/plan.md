---
round: R267
state: completed
opened: '2026-07-25'
closed: '2026-07-25'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R267 plan — Q-0029 one-period alpha-slew sealed test

**Status**: ACTIVE
**Opened**: 2026-07-25
**Driver**: R265 的 raw gate 有小 physical mean gain，但 action-TV guard
爆掉；R266 已证抖动由 alpha switching 主导。
**Parent**: Q-0029, R265/CLM-0525, R266/CLM-0530
**Reserved claim**: CLM-0535

## TL;DR

只测一个 alpha-only 对称 slew。rate 不从 R265 追 guard：
用本项目独立 Kundur modal analysis 的 inter-area mode 0.579 Hz，
冻结 full alpha travel 至少一模态周期，得到
`delta_alpha_max = 0.25 * 0.2 * 0.579 = 0.02895/step`。
新 20-scenario no-anchor bank 上只跑 static、raw、slew。一次失败就关
hand-designed gate family，转 training/deployment 一致 residual。

## Snapshot at plan-time (oracle as of 2026-07-25)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — this is the plan-time oracle snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01)
- Q-0026 [opened R260] archive-index lazy extraction signal
- Q-0029 [opened R265] temporal regularisation of state selector

## Recently Closed (last 3)

- Q-0028 closed-negative @ R265, by CLM-0525
- Q-0027 closed-partial @ R264, by CLM-0520
- Q-0008 closed-negative @ R252, by CLM-0415

## Methodology

### Frozen mechanism

Raw selector:

`rho = std(x) / (abs(mean(x)) + std(x) + 1e-8)`

`alpha_raw = 0.25 * clip(rho / 0.05, 0, 1)`

Executed selector:

- step 0: `alpha_exec = alpha_raw`;
- step t>0:
  `alpha_exec = clip(alpha_raw,
  alpha_exec_prev - 0.02895,
  alpha_exec_prev + 0.02895)`.

Final action stays:

`u = learned + alpha_exec * (droop - learned)`.

No final-action filter. No asymmetric rate. No deadband/hysteresis. No second
parameter. `ratio_full_scale=0.05`, `alpha_cap=0.25`, droop `k=10`, R201
checkpoint and V4 all frozen.

### Independent rate source

- Source: `memory/handoffs/_archive/2026-05-07_handoff_v14.md`, prior
  small-signal modal analysis; inter-area mode `f_mode=0.579 Hz`,
  damping ratio 2.45%.
- Modal period: `T_mode=1/f_mode=1.7271157 s`.
- V4 controller interval: `dt=0.2 s`.
- Full alpha travel rule, fixed before new bank:
  `delta_alpha_max=alpha_cap*dt/T_mode=0.02895`.
- R265 action-TV, transition quantiles and 25% guard were not used to choose
  this value. No rate sweep is allowed.

## Experiment contract

### Sealed bank

- Generator:
  `generate_test_scenarios(n=20, seed=20260725, include_anchors=False)`.
- Bank created only after implementation/tests/preflight pass.
- Canonical UTF-8 JSON, byte hash + manifest before first trajectory.
- Bank of record: `memory/rounds/R267/scenario_bank.json`.
- Bank SHA-256:
  `3e0cdf16758f6e3adcfeb336c891dce94340c0ee96e759783d1b5fcbcc4e2bd5`.
- Bank must have no LS1/LS2 anchors and no exact scenario overlap with R265.
- Evaluator re-hashes bank, manifest, checkpoints and evaluation sources.
- Existing traces are immutable; resume only on exact provenance match.

### Controllers

Exactly three:

1. `static_a0p25`: fixed learned/droop blend;
2. `raw_mode_gate_c0p25`: frozen R264/R265 selector;
3. `slew_mode_gate_c0p25_da0p02895`: frozen selector plus above slew.

Common components:

- checkpoint `results/r201_w1_hreg_tau005_s54`, suffix `best`;
- droop `k=10`;
- V4 paper-faithful anchor, env seed 42;
- 150 control steps;
- scenario-local controller order cyclically rotated.

R201 is legacy mechanism evidence only. No corrected recurrent training in
this round.

### Endpoints and uncertainty

All lower-is-better. Primary contrast is slew minus static.

Co-primary:

1. physical `vsg_mean_iae_hz_s`;
2. physical `normalized_sync_loss_hz2`.

Guards:

- completion/failure and exact 95% interval;
- worst-bus peak and sampled RoCoF mean, CVaR90 and bank worst;
- 0.05-Hz settling success;
- action L1, total variation, saturation;
- raw minus static and slew minus raw for mechanism interpretation.

Use shared-row paired percentile bootstrap, 10,000 resamples,
seed `2026072501`. With n=20, empirical CVaR90 is descriptive worst-two,
not strong tail inference.

## Pre-registered outcomes

### Decision gate

First classify INVALID on any bank/hash/source/checkpoint/provenance drift,
runner error, missing endpoint, non-finite value or failed verification.
Infrastructure-only INVALID may be repaired without changing the scientific
contract.

For a valid result:

### POSITIVE

- all 60 traces complete;
- slew vs static point effect `<0` on both co-primary means;
- at least one co-primary paired 95% CI upper `<0`;
- slew failure not higher than static;
- worst-bus peak and max RoCoF CVaR90 not worse by `>5%`, bank worst not
  worse by `>10%`;
- settling success not lower;
- action-TV CVaR90 vs static not worse by `>25%`;
- slew action-TV point effect vs raw `<0`.

### PARTIAL

- all safety/failure/settling/action guards pass;
- both co-primary point effects `<0`;
- neither co-primary CI upper is `<0`.

This is feasibility signal only, not confirmatory success.

### NEGATIVE

Every other valid result, including:

- either co-primary point effect `>=0`;
- any failure/tail/settling/action guard failure;
- slew does not lower action-TV relative to raw.

POSITIVE or PARTIAL closes Q-0029 and advances to corrected bounded residual.
NEGATIVE closes Q-0029 and the whole hand-designed selector family, then
advances to corrected bounded residual. No second smoothing variant.

## Implementation scope

- Add reusable slew-limited selector beside `ModeRatioGatedBlend` in
  `src/andes_rl_kundur/evaluation/hybrid.py`.
- Add focused deterministic unit tests in
  `tests/test_hybrid_evaluation.py`.
- Reuse sealed-bank/statistics primitives. Generalise the sealed gate driver
  only as much as needed for a three-controller smoothing profile.
- Do not change `base_env.py`, V4 dynamics/config, `train.py`,
  `paper_grade_axes.py`, R201 checkpoints or any R265/R266 artifact.
- Write no manuscript section, paper figure or submission text.

## Planned outputs

- `memory/rounds/R267/scenario_bank.json` + hash + manifest;
- `results/r267_q0029_slew_replication/` provenance, 60 immutable traces,
  JSON/Markdown experiment summary;
- `memory/claims/CLM-0535.md`;
- R267 verdict and Q-0029 closure;
- next priority question choosing corrected bounded residual.

## Verification before launch

- `python memory/tools/round_preflight.py R267`;
- focused hybrid/sealed tests;
- full `python -m pytest tests -q`;
- `python memory/tools/dual_metric_lint.py`;
- `python memory/tools/validate.py`;
- `python memory/tools/render.py`.

## Cross-references

- CLM-0525: raw gate physical means small-positive but action-TV negative.
- CLM-0530: 67.83% switching triangle share; corr 0.99956.
- `docs/research/2026-07-25_q0029_gate_smoothing_landscape.md`.
