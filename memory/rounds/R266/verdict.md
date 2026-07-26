# R266 verdict — R265 gate 抖动来自 alpha switching；只选 alpha slew

**Date**: 2026-07-25
**Status**: CLOSED-PARTIAL — 机制已选，Q-0029 仍需新 sealed bank
**Type**: retrospective mechanism diagnosis + literature synthesis
**Claim**: CLM-0530

## TL;DR

不跑 ANDES、不训练、不扫参数。R266 从 R265 的 20 条 sealed-development
trace 精确重建 `alpha`、learned action 和 droop action，再把每步 action
increment 拆成 frozen-alpha base 与
`delta_alpha * previous controller disagreement`。结果满足预设
switch-dominant gate：switch triangle share 67.83%，逐场景 switching TV
与 actual TV 相关 0.99956。结合 22 篇已核验的一手文献，本轮只冻结一个
机制族：在 alpha 上加对称、单参数、projection-style slew limiter。数值
rate 尚未冻结，必须由独立物理 rise-time 或 small-signal/actuator analysis
给出；R265 不得用于扫 rate 或追 25% guard。

## Evidence

### Exact reconstruction

对 `results/r265_sealed_gate_replication/traces/random_*` 的 20 条
`mode_gate_c0p25` 轨迹，按 `ModeRatioGatedBlend` 冻结公式重构：

\[
u_t=(1-\alpha_t)p_t+\alpha_t s_t,
\]

\[
\Delta u_t=
\underbrace{(1-\alpha_t)\Delta p_t+\alpha_t\Delta s_t}_{B_t}
+\underbrace{\Delta\alpha_t(s_{t-1}-p_{t-1})}_{S_t}.
\]

- action 最大重构误差：`1.11e-16`；
- alpha mean 对保存 telemetry 的最大误差：`9.36e-9`；
- alpha saturated fraction 误差：`0`；
- 完整覆盖：`20/20` scenarios。

### Action-TV decomposition

| Quantity | 20-scenario mean | Interpretation |
|---|---:|---|
| actual raw-gate action-TV | 5.506335 | 与 R265 summary 一致 |
| base variation | 1.608869 | 固定当前 alpha 时两个基动作的变化 |
| switching-disagreement | 4.064090 | `delta alpha × previous disagreement` |
| norm interaction/cancellation | -0.166624 | L1 三角不等式抵消 |
| switching triangle share | 67.8285% | 通过 `>=60%` gate |
| corr(actual TV, switching TV) | 0.999559 | 通过 `>=0.90` gate |
| corr(actual TV, base TV) | -0.426270 | 不支持 base-dominant |

`abs(delta_alpha)` 在 2,980 个 transitions 中的 median / p90 / p95 /
p99 / max 分别为 0.00513 / 0.05484 / 0.08538 / 0.18052 / 0.25。
每场景 alpha increment 符号反转平均 74.35 次；但 TV burden 集中于较少
大 slope：

- 22.248% transitions 满足 `abs(delta_alpha)>0.025`，贡献 77.579%
  switching TV；
- 11.107% transitions 满足 `abs(delta_alpha)>0.05`，贡献 55.308%
  switching TV；
- 逐步 `abs(delta_alpha)` 与 switching magnitude 相关 0.85496。

这说明 R265 同时有 chatter 和 sparse large-slope；后者承担大部分
switching burden。分解只定位代数来源，不是候选 smoother 的反事实效果。
历史轨迹离线截断会漏掉 smoother 对后续状态、observation、raw alpha 和
controller disagreement 的闭环反馈，因此本轮没有做 post-hoc rate replay。

## Literature synthesis and mechanism choice

调研从经典 gain scheduling/switched systems、VSG/virtual inertia、
bumpless/governor、residual/safe RL 五个机制分支核验 22 篇一手来源。共同
约束为：

1. 固定调度点的稳定不能自动推出随时间调度的稳定；scheduling rate 与
   controller interpolation 必须进入论证。
2. low-pass 能衰减高频，但每一步都改写 alpha 并持续引入 lag。
3. hysteresis/dwell 能限制切换频率，却不给连续 alpha jump magnitude
   一个直接硬界，且至少引入双阈值/路径依赖。
4. rate limiter 能直接给 `abs(delta_alpha)` 硬界，并在 limiter 不 active
   时完全透明；但它是一个新动态控制器，可能造成 phase lag、
   windup-like transient、longer settling，甚至 instability。
5. post-hoc filter 与训练策略分离会改变 MDP；若 Q-0029 只证明 feasibility，
   后续 corrected policy 必须把 filter state 纳入 observation/training。

因此只冻结机制族：

\[
\alpha^{exec}_0=\alpha^{raw}_0,
\qquad
\alpha^{exec}_t=
\operatorname{clip}\left(
\alpha^{raw}_t,
\alpha^{exec}_{t-1}-\delta_\alpha,
\alpha^{exec}_{t-1}+\delta_\alpha
\right).
\]

固定 `ratio_full_scale=0.05`、`alpha_cap=0.25`、droop `k=10` 与 R201
checkpoint。不滤 final action，不加 asymmetric rate、deadband、hysteresis
或第二参数。

## Decision and next experiment contract

本轮机制、文献与选择三门均 PASS，但 Q-0029 不关闭：

- **冻结**：alpha-only symmetric single-parameter slew family；
- **未冻结**：`delta_alpha` 数值；
- **rate 来源**：新 bank 生成前，只能用物理/actuator full-scale rise-time
  `T_r`，令 `delta_alpha=alpha_cap*dt/T_r`，或独立 small-signal/actuator
  analysis；
- **禁止**：在 R265 扫 rate、按 action-TV 25% guard 反解 rate、增加第二个
  rate 或其他平滑参数；
- **确认比较**：新 no-anchor sealed bank 上 `slew vs static alpha=0.25`
  为主，`slew vs raw gate` 解释机制；
- **判据**：两项 physical co-primary 保持改善方向，failure/tail/settling
  不回退，action-TV CVaR90 相对 static 不坏超过 25%；
- **kill rule**：一次预注册失败即关闭 hand-designed gate family，转向
  training/deployment 一致的 bounded learned residual。

## Outcome against plan

| Gate | Result |
|---|---|
| exact action/alpha reconstruction | PASS |
| switch share `>=0.60` | PASS — 0.678285 |
| corr(total, switch) `>=0.90` | PASS — 0.999559 |
| at least three mechanism branches with counterevidence | PASS — five branches, 22 sources |
| select at most one auditable mechanism | PASS — alpha-only slew family |
| new ANDES / training / R265 sweep forbidden | PASS — none performed |
| Q-0029 closed on new bank | NOT ATTEMPTED — remains open |

## Limitations

- 所有数值只来自 modified Kundur、legacy R201、R265 development bank。
- `n=20` 只够机制定位；不是 topology/general population inference。
- 没有新闭环 smoother trace，没有 stability certificate，也没有
  converter/actuator feasibility 证明。
- alpha rate 的物理单值仍为空；拿不出独立依据就不能 unseal。
- R261 recurrent-target defect 影响的 checkpoint 仍只能作为 legacy
  mechanism evidence，不能写成 corrected-algorithm evidence。

## Assets

- `docs/research/2026-07-25_q0029_gate_smoothing_landscape.md`
- `memory/claims/CLM-0530.md`
- `results/r265_sealed_gate_replication/traces/`（只读）
- `src/andes_rl_kundur/evaluation/hybrid.py`（只读）

## Verification

- `python memory/tools/round_preflight.py --latest`: PASS
- citation/reference integrity audit: PASS — 22 unique references, all cited,
  no unresolved local links or TODOs
- `python memory/tools/dual_metric_lint.py`: PASS — 271 claims
- `python memory/tools/validate.py`: PASS — 271 claims, 29 questions,
  24 notes; 22 pre-existing missing-provenance warnings
- `python memory/tools/render.py`: PASS

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- Q-0029 — action-TV source measured and one mechanism family selected; new
  physical-rate derivation plus sealed closed-loop bank still required.

## 给 PI 的话

**这轮干了啥**：没跑新 ANDES。把 R265 20 条 gate trace 每步 alpha、learned action、droop action 重构，再把 action-TV 拆成 base 和 `delta-alpha × 分歧`；同时从 gain scheduling、VSG、switched control、residual RL 查 22 篇一手文献。

**结果（一句话）**：抖动根因定位了：raw gate mean TV 5.506，base 只 1.609，alpha switching 项 4.064；后者占 triangle 67.83%，逐场景跟 total TV corr 0.9996。

**意外**：不是“RL actor 太抖”。R201/droop 在当前 blend 下的 base TV 接近 static；少数大 alpha slope 是主因。22.25% transitions 扛 77.58% switching TV。

**我默认下一步做**：只选 alpha 上单参数对称 slew limiter；不滤 final action、不改 0.05/0.25。但 rate 不能从 R265 追 25% guard，先用物理 rise-time 或 small-signal/actuator 分析冻结，再开新 bank。

**你想插一脚就说**：你可以指定/否决 rate 的物理来源；若拿不出独立依据，我不会 unseal。新 bank 失败就关 hand-designed gate family，转 bounded learned residual。
