# R99 verdict — Q-0022 architectural premise CONFIRMED via h_0 gradient-ascent

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (Q-0022 has architectural slack independent of R94 result)
**Type**: analysis (frozen-weight grad-ascent, zero ANDES)
**Wall**: ~50 min (20 min code + 5 min compute + 25 min write)

## TL;DR

R95 / CLM-0174 quantified the R72_w4 SOTA actor's 10-step LSTM warm-up
(step 0: ||a||=0.149 = 10% of max; step 10: 91% of max; corr(||a||,
advantage) = +0.932). Q-0022 proposed h_0 = MLP(obs_0) as the
architectural fix. R99 tests the architectural premise:

**Does there EXIST an (h_0, c_0) for the FROZEN R72_w4 actor such
that step-0 output reaches near-saturation AND the critic prefers
it over the h=0 output?**

YES. Across 4 agents × 100 step-0-like synthetic obs (||obs||=0.25):
- Norm lift: median ||a|| 10.4% → 99.5% of max (+89.2 percentage points)
- Q lift: median +57.8% of |Q_zero| (range +30.9% to +253.7%)
- Optimal ||h*|| ≈ 11-15 (within easy reach of an MLP head)

The LSTM weights are NOT the bottleneck; the (0, 0) initial hidden
state is. CLM-0174 "LSTM warm-up lag is architectural" upgrades from
observation (forward-pass ramp) to mechanism (h=0 is the single
inhibiting state, removable by warm-h_0 init).

Q-0022 architectural premise **confirmed** independent of R94's
action-bound widening result. R96 W1 = Q-0022 implementation should
proceed regardless of R94 outcome.

Zero ANDES. Zero WSL. Zero conflict.

## Methodology

100 synthetic step-0-like obs sampled as: x ~ N(0, I)^7, normalised to
||x|| = 0.25 (matches CLM-0161 median step-0 obs_norm). Load R72_w4
SOTA ckpts read-only (4 agents × td3_lstm, hidden=64). For each agent:

1. Baseline: h, c = 0 → forward actor → a_zero, Q(s, a_zero).
2. Optimisation: Adam(h, c; lr=0.05) for 500 steps, maximise
   min(Q1, Q2)(s, actor(s, h, c)) with critic h_critic also at 0.
3. Compare ||a||, Q at the two endpoints. Aggregate by median (robust
   to outliers in 100-sample batch).

Critic Q uses TD3 target convention min(Q1, Q2) — what training maximises.

## Results

Per-agent (median across 100 synthetic step-0 obs):

| agent | ||a||(h=0) | ||a||(h*) | norm lift | Q(h=0) | Q(h*) | Q gain |
|---|---|---|---|---|---|---|
| 0 | 0.167 (11.8%) | 1.408 (99.6%) | +87.8 pp | -0.131 | -0.083 | +36.7% |
| 1 | 0.126 (8.9%)  | 1.403 (99.2%) | +90.3 pp | -0.022 | +0.034 | **+253.7%** |
| 2 | 0.276 (19.5%) | 1.410 (99.7%) | +80.2 pp | -0.163 | -0.112 | +30.9% |
| 3 | 0.080 (5.7%)  | 1.407 (99.5%) | +93.8 pp | -0.065 | -0.014 | +78.8% |

Cross-agent median:
- norm_lift = **89.2 pp** (gate: > 50 pp; threshold passed by 39 pp)
- q_lift = **+57.8%** (gate: > 20%; threshold passed by 38 pp)
- ||h*|| ~ 12, ||c*|| ~ 12.5

**Feasibility: FEASIBLE**.

### What this means

The R72_w4 LSTM actor architecture has **architectural slack** for
warm-h_0:
- The LSTMCell internal weights can saturate the action when (h, c) ≠ 0
- The (0, 0) initial state forces the LSTM into a low-magnitude region
- A non-zero h_0 ~ 12 (norm) pushes the LSTM into the saturated region
- The critic agrees this is better (Q +58%)

The optimal h* norm of ~12 is reachable by trivially-sized MLPs. Example:
a `nn.Linear(7, 64)` with output gain ~3-4 trained from random init
produces vector norms in the right range.

The result is robust:
- 4/4 agents pass the feasibility gate
- All Q gains > 30%, all norm lifts > 80 pp
- The variation across agents (Q gain 31% — 254%) reflects different
  baseline Q magnitudes, not architectural inconsistency

### Caveats

1. **Synthetic obs**: ||obs||=0.25 with random direction. Real ANDES
   step-0 obs has specific structure (P_es / d_omega / omega_dot scaled).
   The per-direction feasibility may differ from the averaged 99.5%
   result. To upgrade V-trust without this caveat: cached step-0 obs
   vector (not just norm) needed. Currently per_step.json only stores
   `obs_norm` scalar. R96+ would need to instrument a single ANDES
   eval rollout to dump full obs vectors.

2. **Critic h_critic = 0 convention**: matches R86/R84-W2 forensics
   convention, but on-manifold critic also has accumulated hidden state.
   The Q values reported here are the critic's view from cold-start —
   they may differ from on-manifold Q. This is the same caveat that
   applies to all critic-side h=0 forensics work (R84-W2, R86, R88
   sub-step-0 analysis).

3. **Necessary not sufficient**: R99 shows the LSTM CAN saturate from
   step 0 given the right h_0. It does NOT show a learnable MLP can
   find that h_0 from obs alone. That's R96+ training territory.
   But the result moves Q-0022 from "speculative architectural fix"
   to "architecturally guaranteed potential headroom".

## Decision

R96 W1 = Q-0022 implementation (`RecurrentActor.__init__` adds
`self.h_init = nn.Sequential(nn.Linear(obs_dim, 32), nn.Tanh(),
nn.Linear(32, hidden))`; `forward` initial step uses h_init(obs_0)
instead of zeros) is **recommended to proceed independent of R94
outcome**. R99 has decoupled Q-0022 from R94's verdict.

Original CLM-0175 prediction matrix still applies for R94 separately:
- Outcome A (Δgeo > 0, Δmax_df < 0.05): action-bound was binding;
  Q-0022 still recommended for max_df axis
- Outcome B (Δgeo ≈ 0): LSTM warm-up is the real binding constraint;
  Q-0022 is the primary candidate
- Either way, R96 = Q-0022.

## Infrastructure changes

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt / R84/R86/R92/R95 scripts / R94 in-flight
data / any test.

新建:
- `scripts/r99_warm_h0_feasibility.py`
- `results/r99_warm_h0_feasibility/summary.json`
- `memory/rounds/R99/{plan.md, verdict.md}`
- `memory/claims/CLM-0183.md`

V4 regression 不需重跑. R72_w4 ckpt read-only `torch.load(...,
weights_only=True)`.

## Cross-references

- CLM-0174 (R95 LSTM ramp-up quantification) — R99 upgrades its
  "architectural lag" claim from observed to mechanism-confirmed
- CLM-0170 (R92 bang-bang saturation) — sibling mechanism (action-space ceiling)
- CLM-0175 (R94 prediction) — independent path; R99 decouples Q-0022 from R94
- Q-0022 (warm-h_0 candidate) — architectural premise confirmed; R96 implementation cleared
- CLM-0183 (this round)
- R94 plan — independent path

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none) — Q-0022's status stays `open` until R96 W1 verifies a
  learnable MLP h_0 can capture the optimal h*. R99 confirms
  architectural slack (necessary condition) but doesn't close the
  Q until learnability (sufficient condition) is verified.

## Questions advanced (this round, status unchanged)

- **Q-0022** (LSTM warm-h_0 candidate) — premise upgraded from
  "speculative" to "architecturally feasible". Log entry added.
- **Q-0014** (algorithm exploration backlog) — implicit progress:
  Q-0022 is now the architectural candidate independent of R94.
  Q-0014's closing condition remains "geo > 0.45 by any single knob",
  R96 = Q-0022 is the next test.

## 给 PI 的话

**这周干了啥**：你说"继续研究". R95 / CLM-0174 我已经发现 actor LSTM 10 步 warm-up lag, Q-0022 提出 h_0 = MLP(obs_0) 作为 fix, 但没测**架构上是否真有 slack** — 即固定 R72_w4 权重, 能否找到 (h_0, c_0) 让 step-0 actor 直接输出 saturation? R99 用 gradient ascent 测了这件事, 完全离线, 零 WSL.

**结果（一句话）**：FEASIBLE. 4/4 agents × 100 step-0-like synthetic obs, ||a|| 从 10.4% of max 跳到 **99.5% of max** (lift 89.2 pp), Q +58% median (range +31% 到 +254%). 最优 ||h*|| ≈ 12, 一个 `nn.Linear(7, 64)` 就能轻松输出这个 norm. **R72_w4 LSTM 的权重本身完全有 capacity 在 step 0 飙到 saturation, 阻挡它的就是 (0,0) 这一个初始状态**.

**意外**：CLM-0174 我以为 LSTM warm-up 是"内部 hidden state 累积 dynamics 决定的, 你给 warm h_0 也 dampen 不掉 10 步" — R99 否定了这个担忧. 给对 h_0 一步到位, 不需要 ramp 累积. Q-0022 从 "speculative" 升级到 "architecturally guaranteed headroom". R96 = Q-0022 实施现在跟 R94 widen-bound 完全 decoupled — 不论 R94 哪种 outcome, R96 都该开.

**我默认下一步做**：(1) R99 关闭 closed-positive, CLM-0183 写入 (已完成). (2) **R96 = Q-0022 实施候选保持等 R94 verdict**: 不是因为 architectural 不 ready (R99 证明 ready), 而是 WSL 3-slot 限制 + R94 跑出来再开能复用 R94 的训练 infrastructure 改动 (R94 改了 V4Config). (3) 写完 R99 等 R94. 沉默就这么做.

**你想插一脚就说**：(a) 想我现在就把 Q-0022 的 networks.py patch (RecurrentActor.h_init = MLP) 写出来准备 drop-in — 我可以, 文件 diff 大约 15 行, 但训练验证需要 R94 释放 WSL slot ack; (b) 想我把 R99 的 "synthetic obs caveat" 解决 — 我可以从 r80_v5_cross_eval 的 cached LS1/LS2 traces 反推真实 step-0 obs vector (需要 ω, ω_dot, P_es per agent + 邻居延迟规则, 跟 base_env.py::_build_obs 复刻一遍), 离线 20 分钟; (c) 想我把 R99 升级到 multi-ckpt (R58 / R66 / R72_w1-3 等其他 LSTM ckpt 也 grad-ascent 一下看 feasibility 是否 universal) — 5 个 ckpt × 4 agent × 500 step ≈ 10 分钟离线; (d) 觉得 +254% Q gain 不像真的 (agent 1 |Q_zero| 太小 division 不稳) — 可以加 absolute Q gain reporting + min(|Q_zero|) lower-bound 过滤, 5 分钟离线. 我推荐 (默认) **(1)+(2)+(c)**: R99 关掉, 等 R94, 同时跑 multi-ckpt 让 Q-0022 architectural premise 在 N=20+ agents 上确认而非 N=4.
