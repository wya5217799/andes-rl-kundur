# R262 verdict — fixed R201/droop blending is Pareto-only, not a dual-metric win

**Date**: 2026-07-24
**Status**: CLOSED-NEGATIVE for the strict dual objective; CLOSED-POSITIVE as a reusable Pareto baseline
**Type**: research
**Wall**: ~18 min real ANDES scan + implementation, audit, and full regression

## TL;DR

Real ANDES evaluation of seven pre-registered R201/droop-k10 action blends
found no controller that improved both the paper `cum_rf` metric and the
project 11-axis `geo` metric. The two endpoints were reproduced exactly and
all five interior points moved monotonically along the trade-off, so fixed
convex blending does not achieve the strict research objective.

## What was tested

The controller was:

`action = (1 - alpha) * action_R201 + alpha * action_droop(k=10)`

with `alpha={0,.1,.25,.5,.75,.9,1}` fixed before launch. Each point received
fresh seed-42, 150-step LS1 and LS2 trajectories through the corrected R261
evaluation path. The implementation is reusable (`evaluation/hybrid.py` and
`scripts/eval_hybrid.py`), not a round-specific one-off.

## Results

Higher `geo` is better; less-negative `cum_rf` is better.

| alpha | geo | cum_rf | Interpretation |
|---:|---:|---:|---|
| 0.00 | **0.415239** | -0.069158 | Exact R201 endpoint |
| 0.10 | 0.402842 | -0.063989 | Paper +7.47%, geo -2.99% vs R201 |
| 0.25 | 0.372745 | -0.057163 | Closest high-geo compromise; misses balanced gate |
| 0.50 | 0.247825 | -0.048012 | Midpoint trade-off |
| 0.75 | 0.223811 | -0.041256 | Droop-heavy trade-off |
| 0.90 | 0.194266 | -0.038268 | Near droop endpoint |
| 1.00 | 0.179184 | **-0.036712** | Exact droop-k10 endpoint |

All five interior points are sampled Pareto points: improving one headline
metric worsens the other. No hidden nonlinear benefit appeared from static
action averaging.

## Pre-registered gate evaluation

| Gate | Outcome |
|---|---|
| DUAL GOAL MET: `geo>0.4152` and `cum_rf>-0.0367117` | **MISS** — no interior point |
| FOLLOW-UP CANDIDATE: `geo>=0.35` and `cum_rf>=-0.055` | **MISS** — alpha .25 has `cum_rf=-0.057163`; alpha .5 has `geo=0.247825` |
| PARETO ONLY | **MET** |
| INVALID: failed/incomplete trace or endpoint mismatch | **NOT met** |

R262 therefore closes fixed convex blending as a route to the strict goal.
It remains useful as a measured, continuously tunable comparison baseline.

## What this says about the original research goal

The answer is graded:

1. **Custom multi-axis improvement — achieved on the legacy implementation.**
   R201 reaches `geo=0.4152`, about 6.25% above R72 (`0.3908`) and roughly
   2.1x the geo-best classical droop k=2 (`0.1971`).
2. **Paper metric improvement by the same learned algorithm — not achieved.**
   Droop k=10 reaches `cum_rf=-0.0367`, 46.9% closer to zero than R201.
3. **One controller better on both headline evaluations — not achieved.**
   R252 established the two-endpoint Pareto frontier; R262 shows fixed action
   blending fills it in but does not advance it.
4. **General algorithm superiority — not established.**
   The current evidence is seed-42 LS1+LS2, lacks a sealed held-out
   topology/disturbance test, and uses legacy 50-Hz reporting fields.
5. **Corrected TD3-LSTM superiority — untested.**
   R261 proved R201 was trained with legacy recurrent target alignment.

The Yang et al. metric formula is implemented, but this modified ANDES Kundur
environment is not an exact numerical reproduction of the paper's withheld
Simulink setup. Absolute numerical equivalence to the original paper must not
be claimed.

## Claim + Falsification

**Claim**: On seed-42 canonical LS1+LS2, fixed convex R201/droop-k10 blending
does not advance the measured `geo`/`cum_rf` frontier; seven sampled weights
produce a monotonic trade-off from one exactly reproduced endpoint to the
other.

| Dimension | Evidence / limitation |
|---|---|
| Independence | Five interior controllers share the same R201 and droop components; they are policy-composition points, not independent training replicates. |
| Coverage | The pre-registered grid covers both endpoints and five interior weights, but not every real-valued alpha or other droop gains. |
| Counterfactual | Alpha 0 and 1 exactly reproduce measured R201 and droop-k10 baselines. |
| Generalization | No claim beyond V4 LS1+LS2 seed 42 or beyond the legacy-control-Hz metric basis. |
| Robustness | The trade-off is much larger than numerical noise, but no multi-seed or held-out-topology replication was run. |

**Killshot**: A fine alpha scan could reveal a very narrow non-monotonic
window, or a state-dependent/nonlinear gate could create synergy that a fixed
weight cannot. Either would refute generalization from R262 to all hybrids;
R262 only closes the fixed-grid convex controller tested here.

**Independent verification path**: rerun `scripts/eval_hybrid.py` from the
R201 checkpoint and compare `hybrid_blend_summary.json`; endpoint equality,
14 complete 150-step traces, and dual-metric monotonicity are independently
checkable without the verdict prose.

## Verification

| Layer | Result |
|---|---|
| Real ANDES traces | **14/14 complete**, 150/150 steps, no TDS failure |
| Frequency provenance | all traces `legacy_control_hz`, control 50 Hz, ANDES physical 60 Hz |
| Endpoint reproduction | R201 and droop k10 exact to stored precision |
| Windows full pytest | **311 passed, 3 skipped, 1 expected xfail** |
| WSL full pytest with real ANDES | **324 passed, 1 expected xfail** |
| Targeted hybrid/paper-path tests | **13 passed** on Windows and WSL |
| Ruff (`src tests scripts`) | **all checks passed** on Windows |
| `git diff --check` | passed; only pre-existing line-ending warnings |

WSL does not have ruff installed, so lint used the same shared worktree from
Windows. The expected xfail remains the known 60/50-Hz plant/contract mismatch.

## Assets

- `results/r262_hybrid_blend/hybrid_blend_summary.json`
- `src/andes_rl_kundur/evaluation/hybrid.py`
- `scripts/eval_hybrid.py`
- `tests/test_hybrid_evaluation.py`
- CLM-0510

## Questions opened (this round)

- Q-0027 — can a state-dependent droop residual policy, followed by
  corrected recurrent training, advance both metrics?

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：我先没有重训，而是做了最低成本、预注册的真实 ANDES
实验，把当前多轴最强的 R201 与论文指标最强的 droop k=10 按七个固定权重混合。

**结果（一句话）**：严格目标还没有达成；R201 是
`geo=0.4152/cum_rf=-0.0692`，droop 是 `0.1792/-0.0367`，五个中间点全部只是在
两者之间换取一个指标、牺牲另一个，没有任何点同时更好，也没有点通过预注册
的平衡门槛。

**意外**：α=0.10 确实能用约 3.0% 的 geo 损失换来 7.5% 的论文指标改善，
说明 droop 归纳偏置有效；但曲线没有出现协同拐点。固定线性平均不是新算法突破，
只能作为可调 Pareto 基线。

**我默认下一步做**：沿 Q-0027 走状态依赖的 droop residual/gating，小探针先于
训练；若探针有协同迹象，再用 R261 修正后的 recurrent target 做多种子训练，
并加 held-out 扰动或拓扑。不会再把 legacy R201 当成“修正后 TD3-LSTM”的证据。

**你想插一脚就说**：你可以改变成功标准，例如允许“论文指标显著改善、geo
小幅下降”的工程折中；如果不改变，我继续按“同一算法双指标都进步”的严格标准推进。
