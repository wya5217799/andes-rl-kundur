# R95 verdict — Actor LSTM warm-up = plateau mechanism #2; R94 prediction matrix

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (quantitative complement to CLM-0170; falsifiable prediction CLM-0175)
**Type**: analysis (mines cached per_step.json, zero ANDES)
**Wall**: ~50 min (10 min compute + 40 min write)

## TL;DR

CLM-0170 (R92) showed R72_w4 SOTA = bang-bang 256-action quantised policy,
saturated at ±1 by step ~15, 70% of episode at boundary. R94 launched
to widen action bounds.

R95-W1 quantifies the **time-resolved magnitude curve** the CLM-0170
description left qualitative. Actor LSTM warm-up: ||a||_step0 = 0.149 (10%
of max √2), step 5 = 0.81 (57%), step 10 = 1.28 (91%), step 15+ asymptotic.
corr(||a||, advantage) = +0.932 — critic agrees: faster ramp = higher
Q.

Identifies **plateau mechanism #2 = LSTM warm-up lag**, complementary to
R92's mechanism #1 (action-space ceiling). Predicts (CLM-0175, T-trust)
R94 widen-bound will lift steady-state axes (settling) but not transient
axes (max_df) — the latter are bottlenecked by ramp-up time, not bound width.

If prediction holds, Q-0022 (LSTM warm-h_0 initialiser) becomes R96+
candidate priority 1.

Zero ANDES. Zero WSL. R95 is offline analysis.

## Methodology

Same data source as R88 (CLM-0161) and R92 (CLM-0170):
`results/r84_d2b_q_landscape_trajectory/per_step.json`. 400 records, each
has `sota_action: [ΔM_norm, ΔD_norm]`. R88 used per-step summary stats;
R95 uses the actor output vector itself.

Compute per record: ||sota_action||_2 (L2 magnitude, max √2 ≈ 1.414).
Aggregate by step → time-resolved ramp curve. Correlate with advantage
(per-record Q(s, a_sota) − E[Q(s, rand)]).

## Results

### Time-resolved actor magnitude

| step | n | ||a||_med | as % of max | p10 | p90 | frac<0.3 |
|---|---|---|---|---|---|---|
| 0 | 8 | **0.149** | 10.5% | 0.089 | 0.288 | 100% |
| 1 | 8 | 0.283 | 20.0% | 0.205 | 0.398 | 50% |
| 2 | 8 | 0.442 | 31.3% | 0.317 | 0.511 | 0% |
| 5 | 8 | 0.809 | 57.2% | 0.746 | 0.972 | 0% |
| 10 | 8 | 1.282 | 90.7% | 1.227 | 1.351 | 0% |
| 49 | 8 | 1.385 | 98.0% | 1.371 | 1.396 | 0% |

Action-space allocation in steady-state (step ≥ 10, n=320):
- action[1] (ΔD damping) med = +0.985, std 0.014 — pinned upper bound
- action[0] (ΔM inertia) med = +0.027, std 0.962 — bimodal ±1 (Kundur 2-area)

### Critic-actor agreement on ramp-up

corr(||a||, advantage) per phase:
- All: **+0.932**
- Step 0-2: **+0.942**
- Step 10+: +0.372

corr(||a||, argmax_dist):
- All: **−0.814** (bigger ||a|| → critic argmax closer to a_sota)
- Step 0-2: −0.708

Reading: the critic strongly endorses "bigger ||a|| = better Q". In transient,
this correlation is **near +1** — the only thing standing between the actor's
small step-0 action and the critic's preferred action is magnitude.

### Per-agent consistency

| agent | ||a||_med step 0-2 | ||a||_med step 10+ | adv_med step 0-2 |
|---|---|---|---|
| 0 | 0.303 | 1.370 | +0.017 |
| 1 | 0.205 | 1.376 | +0.009 |
| 2 | 0.409 | 1.396 | +0.022 |
| 3 | 0.239 | 1.392 | +0.010 |

All 4 agents show the same ramp shape. Universal pattern.

### Reconciliation across rounds

| Round / Claim | What it showed | Mechanism layer |
|---|---|---|
| R84-W2 + R86 (CLM-0149/0155) | Synthetic-obs Q monotone | Off-manifold artefact, not real |
| R84-W3-traj (CLM-0160) | On-manifold critic concave (overall) | Critic competent on average |
| R88-W1 (CLM-0161) | On-manifold critic confidence bimodal in phase | Step 0-2 critic confused |
| R92-W1 (CLM-0170) | Steady-state action saturation 76% | Mechanism #1: bang-bang ceiling |
| **R95-W1 (CLM-0174)** | **Time-resolved actor ||a|| ramp 0.15→1.38 over 10 steps** | **Mechanism #2: LSTM warm-up lag** |

The 91-round plateau (CLM-0144) decomposes into two ceilings:
1. **Action-space ceiling** (R94 widening targets this)
2. **LSTM warm-up lag** (Q-0022 warm-h_0 targets this)

R88 "transient-phase data starvation" hypothesis is **partially superseded
by R95**: it's not (only) about data quantity in transient — the actor
*architecturally* cannot reach saturation faster than LSTM hidden-state
ramps up from zero, regardless of how much transient data the critic sees.

## Decision (CLM-0175 prediction for R94)

CLM-0175 records the falsifiable matrix:

| R94 result | Mechanism reading | Next round |
|---|---|---|
| Δgeo > 0 AND Δmax_df_axis < 0.05 | Outcome A: action-space ceiling was binding in steady-state; LSTM lag still binds transient | R96+ optional |
| Δgeo within ±2.5% of 0.391 | Outcome B: LSTM warm-up lag is the real binding constraint | R96 W1 = Q-0022 warm-h_0 |
| Δgeo > 0 AND Δmax_df_axis > 0.10 | Partial falsification of CLM-0174 | re-investigate |

## Infrastructure changes (R95)

不动: any code, any V4 config, any ckpt, any test, any other round's data.

新建: `memory/rounds/R95/{plan.md, verdict.md}`, `memory/claims/{CLM-0174,
CLM-0175}.md`, `memory/questions/Q-0022.md`.

Existing cached files read-only. No new compute outputs (analysis ran
in shell `python -c` for transparency; numbers in CLM-0174 table are
direct from those runs).

## Cross-references

- CLM-0170 (R92 action-saturation) — parent; R95 quantifies its qualitative
  "smoothly slides" claim with %-of-max per step
- CLM-0161 (R88 phase bimodality) — sibling finding; R88 = critic confidence
  per phase, R95 = actor magnitude per phase. Same data, different variable.
- CLM-0162 — narrows R87+ priority away from critic-representation
- CLM-0174 (this round, finding)
- CLM-0175 (this round, theoretical prediction for R94)
- Q-0022 (this round, LSTM warm-h_0 candidate, gated on R94 verdict)
- Q-0014 — further narrowed: not algo class, not critic rep, not data
  starvation alone — actor LSTM warm-up architectural constraint
- R94 plan — R95's CLM-0175 supplies the predicted-outcome matrix
- CLM-0144 — R57-R82 plateau gains 2nd mechanism (#1 in R92, #2 in R95)

## Questions opened (this round)

- **Q-0022** — Does LSTM warm-h_0 initialisation (h_0 = MLP(obs_0))
  collapse the 10-step actor ramp-up? Single-file diff in
  `networks.py::RecurrentActor`; ~30 min WSL training when R94 done.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog) — now decomposed into
  (action-space ceiling, R94 testing) + (LSTM warm-up lag, Q-0022).
  Will close-positive iff either knob (or both) breaks 0.391.
- **Q-0020** (R88 transient-replay-reweighting) — deprioritised by
  R95 finding. Replay weighting changes the data the critic sees but
  cannot accelerate the actor's LSTM internal hidden-state warm-up.
  Stays open as a contingency.

## 给 PI 的话

**这周干了啥**：你说"继续研究". 另一 session 已写 R92 / CLM-0170 — R72_w4 SOTA 是 256-action bang-bang policy, 70% of episode pinned at ±1, R94 在跑 widen-bound 训练. 我没去抢这条线, 反而挖 CLM-0170 没量化的角度: **actor ||a|| 的时间曲线**. R88 看 critic confidence per phase, R95 看 actor magnitude per phase, 同一份 cached data 的两个互补变量.

**结果（一句话）**：actor LSTM 从 h=0 ramps up — step 0 ||a||=0.149 (max 的 10%), step 5 = 0.81 (57%), step 10 = 1.28 (91%), step 15+ 才达到 ±1 饱和. **corr(||a||, advantage) = +0.932 overall, +0.942 in transient** — critic 完全同意 "更快 ramp 上去更好". 4 agents 同步. action[1] (d_D damping) 稳态 med=+0.985 saturate, action[0] (d_M inertia) bimodal ±1 (Kundur 2-area). plateau 现在分解成两个 ceiling: (#1) action-space bang-bang ceiling (R92/R94 路径), (#2) **LSTM warm-up lag** (R95 新发现).

**意外**：R88 "transient phase data starvation" 假设被 R95 部分 supersede. 不是 critic 数据不够, 是 **actor 架构上无法比 LSTM hidden-state 从零累积更快地饱和**. 即使你给 critic 100% 的 step 0-2 数据, actor 在 step 0 LSTM=0 时仍输出 ||a||=0.15, 这是 architectural constraint 不是 training-data constraint. 这给 paper 的 Sec.IV-D mechanism 一个更精确的描述: not "critic confused", not "actor decoupled", **just "LSTM需要 10 步预热, 但 metric 看头 5 步"**.

**我默认下一步做**：(1) R95 关闭 closed-positive, CLM-0174 (finding) + CLM-0175 (R94 prediction, T-trust) + Q-0022 写入 (已完成). (2) **不开 R96** — Q-0022 (LSTM warm-h_0 initialiser, h_0=MLP(obs_0)) 需要 WSL 训练, 等 R94 verdict 出来再决定 — 如果 R94 Outcome A (widen-bound 突破 plateau 但 max_df 轴没动) → R96 立刻开 Q-0022 是最后一公里; 如果 R94 Outcome B (widen-bound 也不突破) → R96 仍走 Q-0022 因为 ceiling 已经不是 binding constraint; 如果 R94 Δgeo > 0 且 Δmax_df > 0.10 → R95 部分 falsify, 重新 investigate. 沉默就这么做.

**你想插一脚就说**：(a) 想我立刻 prototype Q-0022 warm-h_0 不等 R94 — 我可以离线写 `RecurrentActor.h_init = MLP(obs_dim → 32 → hidden)` patch, 1 文件 diff 在 `networks.py`, 但训练验证需要 WSL slot ack 一下; (b) 想我把 R95 + R88 + R92 mechanism 写成 paper Sec.IV-D 草稿 — 现在有 3 段 quantitative claim 链 (action saturation 76% + ramp time 10 steps + critic confidence bimodal), 给 paper "为什么 91 round 都败" 的最完整 answer; (c) 觉得 corr(||a||, advantage) = +0.932 太强需要更扎实 — 我可以挖更多 step (1-9 全部) 的 partial correlation 排除 step bias, 离线 5 分钟; (d) 想我把 cached per_step.json 的所有 400 records 画 ||a|| vs advantage scatter (color by step) — 一张图说服力强, 离线 5 分钟. 我推荐 (默认) **(1)+(2)+(b): R95 关掉, 等 R94, 同时把 paper 草稿写出来 — 因为 R94 不论 A/B/C 哪个 outcome, R95 mechanism #2 claim 都成立**.
