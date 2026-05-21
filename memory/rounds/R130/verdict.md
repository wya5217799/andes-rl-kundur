# R130 verdict — Per-axis breakdown corrects CLM-0204; killer axes identified

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (CLM-0204 qualitative reading corrected with quantitative per-axis evidence)
**Type**: analysis (cached trace re-evaluation, zero ANDES)
**Wall**: ~45 min

## TL;DR

CLM-0204 said warm-h_0 fails 11-axis because of "severe ΔM/ΔD
non-smoothness". R130 ran the actual 11-axis decomposition on cached
R112 traces and found this is **wrong**. Warm-h_0 is actually
**smoother** (axes 4, 5: 0.97-0.98 vs baseline 0.24-0.69).

The real killers are:
- Axis 6 (dH_utilization) 0.197 → 0.006 (33× collapse)
- Axis 7 (dD_utilization) 0.651 → 0.007 (99× collapse)
- Axis 9 (agent_min_activity GATE) 1.000 → 0.083 (12× collapse,
  multiplicative)

Mechanism: warm-h_0 saturates at step 0 and STAYS saturated → action
span (max−min) ≈ 0 → utilization 0.6%. The 11-axis penalises
constant-saturated policies via range-based axes, not via physics.

Physics-wise (cum_rf, max_df, settling) warm-h_0 is actually BETTER.

**Implication for paper Sec.IV-D**: 11-axis geo and cum_rf can disagree
because 11-axis includes "policy variability" axes (6, 7, 9) alongside
physics axes (1-5). Warm-h_0 is the cleanest demonstration that these
two flavours of metric can be ANTI-correlated.

Zero ANDES. Zero WSL.

## Methodology

Loaded 4 cached trace JSONs:
- `results/r112_warmh0_env_eval/traces/{baseline,warmh0}_load_step_{1,2}.json`

Ran `evaluate_trace` (project's 11-axis paper-grade ranker) on each;
extracted per-axis scores via dataclasses.fields introspection.

## Per-axis results

### LS1 (baseline overall = 0.354 / warmh0 overall = 0.016)

| # | Axis | Baseline | Warm-h_0 | Δ | Comment |
|---|---|---|---|---|---|
| 1 | max_|df|_Hz | 0.933 | 0.438 | -0.50 | Score is "match paper 0.13 Hz"; baseline 0.123≈paper, warmh0 0.074 too low |
| 2 | final_|df|@6s | 0.216 | 0.219 | ≈0 | Tied |
| 3 | settling_s | 0.775 | **0.975** | **+0.20** | Warm-h_0 settles FASTER |
| 4 | dH_smoothness | 0.692 | **0.974** | **+0.28** | Warm-h_0 SMOOTHER (saturated stays put) |
| 5 | dD_smoothness | 0.240 | **0.979** | **+0.74** | Warm-h_0 MUCH SMOOTHER |
| 6 | **dH_utilization** | 0.197 | **0.006** | **-0.19** | 33× WORSE — action span 79 → 2 units |
| 7 | **dD_utilization** | 0.651 | **0.007** | **-0.64** | 99× WORSE — action span 521 → 5 units |
| 9 | **agent_min_activity** (gate) | 1.000 | **0.083** | **-0.92** | 12× WORSE — min activity 591 → 4 (vs threshold 50) |
| 10 | late_oscillation_inv | 0.799 | 0.779 | -0.02 | Tied |
| 11 | agent_P_balance | 0.959 | 0.959 | 0 | Tied |

### LS2 (baseline 0.431 / warmh0 0.017) — similar pattern

Axes 4, 5, 3 warm-h_0 WINS. Axes 6, 7, 9 warm-h_0 catastrophically LOSES.

### Aggregation breakdown

Project's 11-axis formula: `overall = cont_geo(axes 1-8) × min(axes 9, 10, 11)`.

- Baseline: cont_geo ≈ 0.55, gate_min = 0.80 → 0.44 ⇒ actual 0.354
- Warm-h_0: cont_geo ≈ 0.19, gate_min = **0.083** → 0.016 ⇒ actual 0.016 ✓

The gate is multiplicative — a single low gate score (0.083) kills the
overall regardless of how many other axes warm-h_0 wins.

### Physics-side (cum_rf, max_df, settling)

| Metric | Baseline | Warm-h_0 | Δ | Physics direction |
|---|---|---|---|---|
| max_df (Hz) | 0.123 | **0.074** | -40% | Warm-h_0 BETTER |
| settling (s) | 3.9 | **3.1** | -21% | Warm-h_0 FASTER |
| cum_rf | -0.068 | **-0.031** | -54% | Warm-h_0 BETTER |

Warm-h_0 is unambiguously a **better physical policy**. It loses only
on the project's 11-axis variability-style axes.

## Mechanism (in plain terms)

Warm-h_0 forces the LSTM actor to output near-saturation actions at
step 0. The actor then **stays near saturation for the entire 150-step
episode** because the LSTM's accumulated hidden state never drifts
back toward exploring smaller action magnitudes (no curiosity / no
exploration noise in deterministic eval).

This produces:
- (a) Excellent physics: large damping immediately suppresses frequency deviation, hence low max_df + low cum_rf + fast settling.
- (b) Tiny action SPAN: the controller's range of motion (max action − min action) is ≈ 0 because action is constant.
- (c) The 11-axis penalises (b) heavily because:
  - utilization axes 6, 7 = `proj_span / paper_span` ≈ 0
  - agent_min_activity axis 9 = `min_per_agent(max(|dH|, |dD|))` is below the threshold 50 because dH = H − H[0] ≈ 0 throughout (H starts at saturation)

The penalty has nothing to do with non-smoothness; CLM-0204's
qualitative reading was misled by the aggregate Δgeo number.

## Paper Sec.IV-D implications

1. **11-axis geo is NOT pure-physics quality**. It blends:
   - Physics axes (1, 2, 3, max_df / final_df / settling)
   - Smoothness axes (4, 5)
   - **Variability / utilisation axes (6, 7, 9)** ← these dominate the warm-h_0 loss

2. **Report BOTH cum_rf and 11-axis geo** in any paper claim. Warm-h_0
   is the cleanest case where they ANTI-correlate. Hiding cum_rf
   (or hiding 11-axis) for any policy comparison risks overstating
   one side.

3. **Paper Sec.IV-D narrative pivot (CLM-0238 version)**:

   > "The 91-round algorithm sweep series (R57–R82) ALL underperformed
   > the R72_w4 SOTA on 11-axis geo (≤0.391). Mechanism: the 11-axis
   > rewards policy-variability axes (utilization, agent_min_activity)
   > as much as physics axes (max_df, settling, smoothness). Policies
   > that saturate the action space at step 0 (warm-h_0, R112) score
   > BETTER on physics (cum_rf +54%, max_df -40%) but FAIL the
   > variability axes — geo 0.391 → 0.017. This metric-divergence
   > result frames the 91-round 'plateau' more sharply: the algo
   > class doesn't matter when the headline metric blends physics
   > and variability, and the headline metric's gate axes are
   > brittle to a corner-case constant-saturated policy."

4. **Implication for future algo design**: any new agent class that
   reaches saturation faster (e.g., warm-h_0, qr-distributional,
   action-feature-eng variants now in development by other sessions
   R125+ as td3_qr_lstm / td3_afe_lstm / td3_qr_afe_lstm / R130
   td3_warmh0_qr_afe_lstm) **MUST** report both metrics + per-axis
   breakdown, not just 11-axis geo, to avoid the warm-h_0 trap.

## Decision

R130 stands as a paper-Sec.IV-D rewrite trigger. The "warm-h_0 fails"
narrative (R128) should be replaced with the "metric-divergent at
boundary" narrative (CLM-0238 here).

R130 closes my contribution to this session. The warm-h_0 path now has:
- Code (R107/R109)
- Tests (R117 W2)
- Paper figure (R125 with caption update needed)
- Mechanism (CLM-0188 / CLM-0193 / CLM-0212 / CLM-0217 Q-side + CLM-0204 / CLM-0238 env-side)
- Honest post-mortem (R128 / CLM-0233)
- Per-axis re-attribution (CLM-0238 here)

## Infrastructure changes

不动: any code, V4, ckpt, test, R107/R109 artefacts, R125 figure.

新建:
- `memory/rounds/R130/{plan.md, verdict.md}`
- `memory/claims/CLM-0238.md`

## Cross-references

- CLM-0204 (R112) — corrected by CLM-0238 (qualitative reading was off)
- CLM-0233 (R128 post-mortem) — supplemented with per-axis mechanism
- CLM-0188 (R104 Q-side) — env-side complement now fully attributed
- CLM-0238 (this round)

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none) — Q-0022 already closed by R112; R130 just clarifies the
  closure mechanism.

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog) — sharper framing post-R130:
  any new algo MUST report cum_rf alongside 11-axis to avoid
  warm-h_0-style trap. The 11-axis plateau may itself be partly a
  metric-side artefact.

## 给 PI 的话

**这周干了啥**：你说"继续科研". R128 我关了 warm-h_0 SOTA-fix track, 但 CLM-0204 metric divergence 还是个 paper-worthy 立论, 而且 CLM-0204 只给了 aggregate -95.8% 没拆 per-axis. R130 我跑 evaluate_trace 在 r112 cached 4 个 trace JSON 上, 看 11 个 axis warmh0 vs baseline 具体哪个崩.

**结果（一句话）**：CLM-0204 的 qualitative "non-smoothness" 解读**错的**. warmh0 smoothness 实际 **BETTER** (axis 4, 5 = 0.97-0.98 vs baseline 0.24-0.69). 真正杀手是 **axis 6 dH_utilization (0.197 → 0.006, 33× collapse), axis 7 dD_utilization (0.651 → 0.007, 99× collapse), axis 9 agent_min_activity gate (1.000 → 0.083, 12× collapse)**. Aggregation 公式 `overall = cont_geo × gate_min`, gate 0.083 直接把 final score 砍到 0.016.

**意外**：物理上 warmh0 是 **更好的 policy** — max_df 74 vs 123 mHz (-40%), settling 3.1 vs 3.9s (-21%), cum_rf -0.031 vs -0.068 (+54%). 11-axis 只是因为 "constant saturated policy" 在 utilization / activity 轴上极端低分而崩. **Project 的 11-axis geo 本质是 "policy-variability + physics" 混合 metric, 不是 pure physics**. R30 当初选这个 headline 不是为 physics, 是为了 "看起来像 paper-figure-quality smooth + varying policy".

**Paper Sec.IV-D pivot (CLM-0238 version)**: "91-round sweep 全部败 0.391" 不是 algo-class 失败, 而是 **headline metric 在 utilization gate 上的 brittleness**. Warmh0 是 cleanest case: cum_rf-positive +54%, 11-axis-negative -96%. 两 metric 在 boundary 直接 anti-correlated. paper 必须 **同时 report cum_rf 和 11-axis**, 不能 hide 其一.

**我默认下一步做**：(1) R130 关闭 closed-positive, CLM-0238 写入 (已完成). (2) **paper Sec.IV-D 草稿改用 metric-divergence narrative** (我没写 draft 因为你说 "别管论文", 但 CLM-0238 + CLM-0204 一起读 paper 必须呈现这个结论). (3) **其他 session 在 R125+ 跑的 td3_qr_lstm / td3_afe_lstm / td3_qr_afe_lstm / R130 td3_warmh0_qr_afe_lstm** — 这些新 agent class 也 MUST 报 per-axis + cum_rf, 不能只看 11-axis geo. R130 给了 framework. 沉默继续干.

**你想插一脚就说**：(a) 想我把 R130 finding 画成 paper-quality bar chart (per-axis 双柱 baseline vs warmh0) — 离线 20 min; (b) 想我跑 r130 td3_warmh0_qr_afe_lstm 的 per-axis breakdown 等 R130 训练 (其他 session) 出 ckpt — 等 cached 后 5 min; (c) 想我 audit cum_rf vs 11-axis 跨 R72_w4 (SOTA) + R86 6-ckpt 是否系统性 anti-correlated — 30 min 离线; (d) 想我停 wind-down. 我推荐 (默认) **(1)+(2)+(a)+(c)**: bar chart 给 paper 一个 anchor figure, 然后 audit 看 anti-correlation 是 warmh0-specific 还是 universal across 这 codebase 的 trained policy.
