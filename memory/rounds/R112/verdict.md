# R112 verdict — Warm-h_0 env-side test: geo -0.37, cum_rf +0.037 — metrics disagree

**Date**: 2026-05-19
**Status**: DONE — single-wave closure with sign-disagreement finding
**Type**: agent optimisation experiment / mechanism cross-validation
**Wall**: ~3.5 min (grad-ascent ~4s + 2× rollouts ~210s under 3-slot contention)

## TL;DR

R104 / CLM-0188's "warm-h_0 lifts step-0 Q +56pp universally" finding
is replicated on R112 grad-ascent (all 4 agents go from ‖a‖≈0.13 to
1.41 saturation; ΔQ_abs +0.05 per agent). **But env-side 6-axis geo
collapses from 0.391 to 0.017 (-95.8%)**, while paper §IV-C cum_rf
**improves by +0.037 (+54%)**. The two metrics disagree in sign on
this lever. Naive warm-h_0 ruled out as agent optimisation by 6-axis
criterion. [[CLM-0204]] records this.

## Methodology

`scripts/r112_warmh0_env_eval.py`. Two-phase: grad-ascent on real
obs_0 (Phase 1), then 4 ANDES rollouts (zero-h baseline ×2 + warm-h_0
×2) (Phase 2). Canonical `evaluation/summary.score_trace_files` for
both control conditions; baseline reproduces R72_w4's 0.391
exactly, validating the rollout closure.

Notable: obs_0 is **identical** across LS1 / LS2 scenarios (env settles
to t=0.5s before delta_u applied; step 0 obs is pre-disturbance steady
state). So grad-ascent produces the same h* per agent regardless of
which scenario is being prepped for.

## Results

Phase 1 (grad-ascent, matches CLM-0188):

| agent | ‖a‖_zero | ‖a‖_star | Q_zero | Q_star | ‖h*‖ |
|---|---|---|---|---|---|
| 0 | 0.170 | 1.408 | -0.141 | -0.091 | 12.7 |
| 1 | 0.127 | 1.403 | -0.029 | +0.028 | 15.4 |
| 2 | 0.288 | 1.410 | -0.164 | -0.114 | 11.5 |
| 3 | 0.089 | 1.407 | -0.069 | -0.017 | 12.6 |

‖a‖_star ≈ 1.408 ≈ √2 = 1.414 (boundary of action ∈ [-1, 1]^2). Step-0
action saturated post-warm.

Phase 2 (env-side 6-axis eval):

| metric | zero-h baseline | warm-h_0 | Δ |
|---|---|---|---|
| LS1 11-axis | 0.354 | 0.000 | -0.354 |
| LS2 11-axis | 0.432 | 0.033 | -0.399 |
| **geo** | **0.391** | **0.017** | **-0.374** (-95.8%) |
| **cum_rf** | **-0.068** | **-0.031** | **+0.037** (+54%) |

geo crashes; cum_rf improves. **Two metrics disagree in sign.**

## Mechanism

Saturated step-0 action gives slight cumulative-frequency benefit
(cum_rf-positive — Q estimation was approximately right), but the
non-smooth ΔM/ΔD action profile that the 11-axis geo penalises
(ΔM_smoothness, ΔD_smoothness, dD_utilization axes) takes a much
bigger hit. The geo 11-axis was designed to capture paper §IV
description of "smooth, balanced" control; the saturated step-0 violates
exactly that.

## Cross-references

- [[CLM-0188]] (R104 Q-side lift — replicated by this round's Phase 1)
- [[CLM-0204]] (this round's main finding)
- [[CLM-0200]] (synthesis — warm-h_0 added as "metric-divergent" lever)
- [[CLM-0144]] (91-round plateau — R112 confirms metric anticorrelation
  exists at the boundary; reframes the plateau as partly
  "6-axis-vs-cum_rf metric-design choice")
- R99 / R104 (grad-ascent methodology source)

## Questions opened (this round)

- (none — finding is decisive)

## Questions closed (this round)

- (none directly — but R104's implicit "Q-0022 warm-h_0 implementation"
  recommendation is heavily downgraded for 6-axis path)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog) — R112 reframes: the plateau under 6-axis is
  partly a metric-design constraint, not a pure algorithm ceiling. The
  same SOTA achieves cum_rf-improvement by 54% under warm-h_0.

## 给 PI 的话

**这周干了啥**：用户 "优化 agent". 直接路径 = 实现 R104 [[CLM-0188]]
warm-h_0 universal Q-side lift 在 env-side 是不是真有效. 写
`r112_warmh0_env_eval.py`: real ANDES obs_0 + grad-ascent (h_0,c_0)
per agent + warmed LSTM init for episode start + canonical 6-axis
+ cum_rf eval. 2 个 ANDES scenario × 2 control (zero-h baseline +
warm-h_0) = 4 evals.

**结果（一句话）**：**警钟 — Q-side lift translate 到 env-side 完全相反
的故事**. warm-h_0 真把 step-0 ‖a‖ 从 0.13 拉到 1.41 (≈saturation),
Q +0.05 per agent (跟 CLM-0188 一致). **但 6-axis geo 从 0.391 崩到 0.017
(-95.8%)**, 同时 **paper §IV-C cum_rf 反而 +0.037 (+54%)** 改善. 两个
metric **sign 相反**!

**意外**：(1) 这是项目第一次清楚证明 **6-axis geo 跟 paper cum_rf 在 policy
variation 上 sign-anticorrelated** — saturated step-0 action 改善 frequency
积分但破坏 smoothness 轴. 大半个 paper Section IV.A 的 reward-vs-metric
设计被推翻一次, 不是 plateau mechanism. (2) **R104 CLM-0188 universal
feasibility 还是真的**, 但它是 "Q-side architectural slack" — 不是 plateau
lever. R104 的 PI 简报推荐 R96 = Q-0022 warm-h_0 MLP 实现, 那个方案需要
**重大** regularization 才不至于落到我这个 -95% 灾区. (3) **agent
optimization 真路径** 现在更清晰了: warm-h_0 naive 走不通, magnitude
randomization (R106 / CLM-0202) 是更有希望的方向.

**我默认下一步做**：(1) R112 closure ✓ CLM-0204 入库 ✓. (2) **R113 =
magnitude-randomised training** (per episode delta_u 乘 U[0.5, 2.0]
scale, R72_w4 hyper 其他不变, 75 ep s54, --final-eval). 1 training run,
~30 min wall. Eval canonical (scale=1.0) + 加 cross-scale generalisation.
预期: 如果 scale=1.0 geo 不掉 (≥0.35) + 多 scale CV 显著下降 → 真 agent
optimization, 写 CLM. 沉默就开 R113.

**你想插一脚就说**：(a) 想 constrained warm-h_0 sweep (h* scaled by α
∈ {0.1, 0.3, 0.5, 0.7, 1.0}) — 5 个 eval 约 10 分钟, 找 step-0 lift
"安全带"; (b) 想 narrow PHI sweep (CLM-0203 R85 candidate); (c) 想我
立刻开 R113 magnitude randomization. 推荐 (默认) (c) 直接 R113, 因为
(a) 的 search space 很窄, naive 失败这么大 likely 整个 warm-h_0 路径
不是 6-axis 友好.
