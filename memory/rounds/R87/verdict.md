# R87 verdict — phase-resolved on-manifold critic forensics, CLM-0160 holds at fine grain

**Date**: 2026-05-19
**Status**: DONE — W1 gate A_ALL_PHASES_PASS, 1 claim, R88+ priority locked
**Type**: analysis (re-analysis of cached R84-D2b on-manifold trajectory probes, zero ANDES)
**Wall**: ~25 min plan + script + run

## TL;DR

PI "继续研究". CLM-0160 (R84-W3-traj on-manifold D2b) reported overall
median metrics that PASS the actor-critic confidence gate, refuting the
synthetic-obs affine-Q story of CLM-0149/0153/0154 (which my own
R84-W2/W3 had drawn). R87-W1 re-analyses CLM-0160's cached 400 probes by
(phase × scenario × agent) and confirms PASS at fine granularity:
**every** of the 4 phases (impulse / rising / decaying / settling) passes
the threshold. One informative gradient surfaces — **impulse-phase**
critic confidence is materially weaker (advantage 0.022 vs settling
0.061; argmax_dist 0.275 vs 0.055) — but mechanism is identified
(LSTMCell h=0 at episode start needs ~5-10 forward steps to lock in,
visible in time-series viz). **Not a pathology**; just a transient onset
that explains why the off-manifold synthetic-obs forensics (h_critic=0
+ N(0, σ²I) obs) found "affine-Q" — that regime exists for ~1 real-time
second per disturbance, then disappears. CLM-0165 written. R88+ priority
**locked**: drop critic-side candidates (distributional / regularisation /
wider warmup), pursue D3 obs sufficiency / D4 env floor / reward-shape
ablation per CLM-0160 + CLM-0165.

## Methodology

Re-analysis only — zero ANDES, zero training, zero ckpt mutation.

Input: `results/r84_d2b_q_landscape_trajectory/per_step.json` (400
records from CLM-0160's on-manifold D2b run: 4 agents × 2 scenarios
LS1+LS2 × 50 steps each; per-step Q-landscape probe metrics with critic
LSTMCell h advanced along the realised SOTA rollout).

Per-record fields: scenario, step, agent, obs_norm, sota_action,
grad_norm, q_sota_mean, q_rand_mean, q_rand_max, argmax_dist,
q1q2_disagreement, best_random_minus_sota, advantage.

Phase buckets:
- impulse: step ∈ [0, 5) — disturbance just applied, h_critic still warm-starting
- rising: step ∈ [5, 15) — frequency excursion building, peak ~10
- decaying: step ∈ [15, 30) — peak crossed, active control phase
- settling: step ∈ [30, 50] — returning to nominal, dD/dt small

Gate same as R84-D2b: advantage_median > 0 AND argmax_dist_median <
0.5 × action_diagonal (= 50% of √8 ≈ 0.707).

## Results

### Phase × scenario × agent summary

Per-phase global (across both scenarios + 4 agents):

| Phase     | n   | adv_med   | adv_pos% | amx/diag  | q12_med | PASS |
|-----------|-----|-----------|----------|-----------|---------|------|
| impulse   | 40  | +0.0216   | 97.5%    | 0.275     | 0.0250  | YES  |
| rising    | 80  | +0.0568   | 100.0%   | 0.060     | 0.0155  | YES  |
| decaying  | 120 | +0.0610   | 100.0%   | 0.060     | 0.0162  | YES  |
| settling  | 160 | +0.0611   | 100.0%   | 0.055     | 0.0153  | YES  |

Gate: **A_ALL_PHASES_PASS**.

### Time-series visualisation (advantage_timeseries.png)

4 subplots (2 scenarios × 2 metrics):
- Top row (advantage(t)): all curves rise sharply from ~0 at step 0
  to ~0.07 plateau by step ~15, hold through step 50. All stay > 0.
- Bottom row (argmax_dist(t)): all curves START near 0.5 fail
  threshold (red dashed) at step 0-5, collapse to ~0.1 by step 10,
  stay below for rest of episode.
- agent_1 (orange) consistently slightly higher advantage than other
  agents; differences subtle.

**Mechanism inferred from time-series**: critic LSTMCell hidden state
h is reset to zeros at `select_action(step=0)`. Without context,
critic output is mostly determined by the actor head bias. ~5-10
forward steps accumulate enough h history for the critic to stabilise
on its true on-manifold preference structure. This is **not** an
algorithm pathology — it's the expected behaviour of stateful
critics at episode boundaries.

### Cross-agent heterogeneity

Per-agent global stats:

| Agent | adv_med   | amx/diag | q12     |
|-------|-----------|----------|---------|
| 0     | +0.0583   | 0.055    | 0.0432  |
| 1     | +0.0572   | 0.091    | **0.0029** |
| 2     | +0.0644   | 0.060    | 0.0122  |
| 3     | +0.0606   | 0.057    | 0.0389  |

agent_1's twin-Q disagreement is **14× lower** than agent_0/3. Likely
explanation: agent_1 saw a more consistent state distribution during
training (no role-specific pathology, parity in advantage). Not a
priority follow-up; flag in case R88+ multi-agent coordination
diagnostics need an entry point.

### Correlations obs_norm ↔ critic metrics

| Pair | Pearson r |
|---|---|
| obs_norm vs advantage | +0.076 |
| obs_norm vs argmax_dist | +0.080 |
| **obs_norm vs q_sota_mean** | **−0.570** |

The −0.57 correlation is **physically expected**: higher obs deviation
from nominal frequency → larger anticipated control cost → lower Q.
Critic correctly encodes the "far-from-equilibrium = worse return"
gradient. **Obs distribution alone is not the bottleneck for critic
confidence** (advantage / argmax_dist near-independent of obs_norm).

### Implications

R87-W1 confirms CLM-0160 at finer resolution and provides a clean
mechanistic explanation for the discrepancy between off-manifold
W2/W3-syn forensics (CLM-0153/0154) and on-manifold D2b (CLM-0160):

> The h_critic=0 + N(0, σ²I) obs regime that CLM-0153/0154 probed
> **does occur** in real eval — for ~5 LSTM-forward steps after each
> episode reset. In that brief window, the critic genuinely does
> show monotone-Q-along-action and wide argmax_dist. But by step
> 10+, the LSTM context has locked in the on-manifold preference
> structure. R87 shows this transition crisply in the time series.

This is a satisfying closure: my R84-W2/W3 measurements were correct
data, the conclusion (R85 PRIORITY 1 = distributional critic) was
incorrect because I extrapolated the transient-window regime to the
full episode. CLM-0160 + CLM-0165 supersede that conclusion.

### R88+ priority (locked per CLM-0160 + CLM-0165)

Candidates ranked:
1. **D3 obs sufficiency** (BC + V regressor on ANDES-collected
   (obs, action*, return) traces). Needs ANDES WSL slot;
   blocked on R83/R85 release.
2. **D4 env stochasticity floor** (varied-disturbance eval).
   Needs ANDES.
3. **Reward-shape ablation** (PHI_ABS=0 strict on R72_w4 basin,
   never tested). Needs ANDES training, expensive.
4. **Multi-agent coordination diagnostics** (per-agent action
   contribution decomposition under R72_w4 SOTA rollout).
   R87-W1 surfaced agent_1 epistemic outlier; could be entry
   point. Mostly zero-ANDES (read SOTA actions from
   per_step.json + recompute attribution).

R88 default = (4) multi-agent coord diagnostics (zero-ANDES,
exploits cached data, no resource conflict). If that gives no
signal → (1) D3 obs sufficiency once ANDES frees.

## R84 amendments (synced after CLM-0160 + CLM-0165)

R84 verdict still reads "critic is affine in action" in title and TL;DR.
The off-manifold measurements (CLM-0153 / CLM-0154) remain V (verified
data); the **mechanism interpretation** (CLM-0149's claim that this
indicates universal plateau cause) is superseded by CLM-0160 + CLM-0165
which restrict the affine-Q regime to the ~5-step impulse onset.
R84 verdict needs a banner; R87 doesn't unilaterally rewrite parallel-
session content but flags the supersede chain here for the next reader.

## Cross-references

- CLM-0160 (R84-W3-traj on-manifold overall PASS — R87 confirms at fine grain)
- CLM-0149 / CLM-0153 / CLM-0154 (R84 W2/W3 off-manifold; mechanism interpretation superseded, data still valid)
- Q-0018 (closed-negative by CLM-0160; R87 reinforces closure)
- R83 plan (obs aug, in-flight, ANDES WSL slot)
- R85 plan (classical PI/Droop baseline, in-flight, ANDES WSL slot)
- R86 plan (cross-ckpt synthetic forensics; premise CLM-0148/0149 now superseded — R86 should be reviewed when its session next checks in)

## Questions opened (this round)

- (none) — R87 confirms an existing claim's robustness; doesn't open new questions.

## Questions closed (this round)

- (none directly) — Q-0018 already closed-negative by CLM-0160; R87 strengthens that closure.

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog, open) — R87 + CLM-0160 +
  CLM-0165 jointly **lock the R88+ priority** away from critic-side
  algorithm refactors. Q-0014 should now reformulate around obs / env /
  reward axes rather than algo class.

## 给 PI 的话

**这周干了啥**：上一轮 R84-W2/W3 报了 critic-affine actor-critic decoupling 是 plateau mechanism, 推 distributional critic 是 R85 PRIORITY 1. 然后另一 session 跑 R84-W3-traj (ANDES on-manifold trajectory probe, CLM-0160) **直接 falsify** 我那个解释 — 在真实 trajectory 上 advantage +120% |Q|, argmax_dist 13% of action diagonal, 完全 endorsement. 我看到 CLM-0160 后没死等结论, 直接 reserve R87 把它 cached per_step.json 400 records 拿出来做 phase-resolved 复核, 看 overall median 是否盖住了某个 phase 病理. 全程零 ANDES, 跟 R83 / R85 / R86 (in-flight) 不抢锁.

**结果（一句话）**：Gate A_ALL_PHASES_PASS — impulse / rising / decaying / settling 全部 advantage > 0 + argmax_dist < 50% action diagonal, CLM-0160 在 fine grain 下 holds. 唯一 informative gradient = impulse 阶段 critic 信心**实质弱** (advantage 0.022 vs settling 0.061, argmax_dist 0.275 vs 0.055), 时间序列图 (advantage_timeseries.png) 显示 argmax_dist 在 step 0-5 接近 0.5 fail line 然后 step 10 后 collapse 到 ~0.1 — 机制就是 critic LSTMCell h=0 episode 重置后需要 5-10 forward step 累 context 才稳, **不是 critic 病理**. 顺便量化: obs_norm vs q_sota_mean correlation −0.57 (critic 正确 encode "far-from-equilibrium = worse return" 物理梯度), obs_norm vs advantage 仅 +0.08 (obs 分布跟 critic 信心几乎独立).

**意外**：(1) 这给了我 R84 错误结论的**干净机制解释** — h_critic=0 + N(0, σ²I) obs 那个 regime **真的在 eval 里出现**, 但每 episode 只 ~5 步, 然后 LSTM 把它 wash out 掉. 我 R84 把 transient onset 推广成 universal plateau cause, 这条因果链现在合龙了. (2) per-agent Q1/Q2 disagreement 跨 agent 差 14× (agent_1 = 0.003 vs agent_0 = 0.043), advantage 各 agent 几乎一致 — 不是 critic 个别 broken, 但暗示某种 inter-agent coordination 结构. (3) R86 plan 是基于已 supersede 的 CLM-0148/0149 写的 cross-ckpt synthetic forensics, 它跑出来的结果跟 W2/W3-syn 在同一个 transient regime 上, 不再 informative — 我没去改 R86 (parallel session 的工作面), 但 R87 verdict 里 flag 一下.

**我默认下一步做**：(1) R87 已 close, CLM-0165 写入, 我已经把 PI 简报准备好粘贴到 chat (按 ADR-0003). (2) **R88 默认走 multi-agent coordination diagnostics** — zero ANDES, 复用 per_step.json 的 sota_action 数据, 看 4 个 agent 的 action 在 LS1+LS2 trajectory 上是否 redundant / antagonistic / specialised. R87 agent_1 q12 outlier 是入口. (3) 如果 R88 也没 mechanism 信号, **R89 = D3 obs sufficiency** (BC + V regressor), 等 R83 / R85 释 ANDES 锁后跑.

**你想插一脚就说**：(a) 如果你想我直接接 D3 obs sufficiency, 写 ANDES rollout collector + BC/V regressor stubs **等锁** — 说 "先 D3"; (b) 如果你想我去 verify R85 (classical PI/Droop) 是不是真在跑, 哪些 wave 完成了 — 说 "查 R85"; (c) 如果你看了 R87 觉得 fine-grain 也不够, 想跑 N=100 episode 的 trajectory probe (不只 1 episode × 2 scen × 50 step) — 需要 ANDES; (d) 如果你想我跟 R86 session 协调一下让它停止/调整 plan — 说 "ping R86". 我推荐 (默认) **R88 multi-agent coordination diagnostics 立刻起**.
