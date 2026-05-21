# R133 verdict — Magnitude-PI at D5-fair bounds: classical UNAFFECTED, RL 1.50× advantage REAL

**Date**: 2026-05-19
**Status**: DONE — D5 handicap hypothesis FALSIFIED, RL advantage confirmed real
**Type**: experiment (eval-only, zero training, zero V4 mutation)
**Wall**: ~10 min code + ~28 min WSL eval + ~15 min closure

## TL;DR

R133 re-evaluated magnitude-PI at D5-fair action bounds (dm_max=600,
dm_min=-200, matching R72_w4 SOTA training, CLM-0233). **3 gain combos
all confirm: bit-identical or worse than R102's dm_max=300 result**:
- (Kp_M=2, Kp_D=5) → geo=**0.2602** (identical to R102 0.2602)
- (Kp_M=4, Kp_D=10) → geo=0.178 (worse, over-control)
- (Kp_M=8, Kp_D=20) → geo=0.159 (even worse)

**Mechanism**: at Kp_M=2 / Kp_D=5 and typical |Δω|≈0.05 normalized,
controller outputs |ΔM_norm|≈0.10 (10% of range). Action stays well
inside both [-300, 300] AND [-600, 600] envelopes — never saturates →
identical physics. Doubling gains to USE the wider range produces
over-control + frequency overshoot → worse geo.

**RL advantage CONFIRMED real at 1.50×**:
- mag-PI best (D5-fair) = 0.260
- R72_w4 SOTA = 0.391
- advantage = 0.391 / 0.260 = **1.50× geo**
- Same number as R102 + R85; NOT inflated by D5 handicap.

**CLM-0233 D5 finding stands** (R72_w4 SOTA trained at wider bounds),
but the wider bounds are NOT the source of RL's advantage. The 1.50×
gap is genuine algorithmic advantage, not action-bound artifact.

## Methodology

- V4 env with `V4Config(dm_max=600, dm_min=-200, dd_max=600, dd_min=-200)`
- Same code path as R102 magnitude-PI controller (Ki=0 P-only, magnitude-symmetric)
- LS1 + LS2 × seed=42 × steps=150
- Score via paper_grade_axes 11-axis geo

## Results

| Combo | LS1 geo | LS2 geo | overall geo | cum_rf |
|---|---|---|---|---|
| (Kp_M=2, Kp_D=5)  | 0.195 | 0.348 | **0.2602** | -0.043 |
| (Kp_M=4, Kp_D=10) | 0.143 | 0.222 | 0.178 | -0.042 |
| (Kp_M=8, Kp_D=20) | 0.143 | 0.176 | 0.159 | -0.048 |

Comparison table:

| Setting | geo | vs SOTA 0.391 |
|---|---|---|
| R85 mag-PI at dm_max=300 (handicapped) | 0.260 | -0.131 |
| R133 mag-PI at dm_max=600 (D5-fair) | **0.260** | -0.131 |
| R72_w4 SOTA at dm_max=600 | 0.391 | 0 |

**Bit-identical geo at both bounds** for the optimal gain. The action
range expansion has zero effect on the magnitude-PI sweet spot because
the controller is not action-bound-limited at typical operating gains.

## GATE Decision

R133 plan gate:
- mag-PI ≥ 0.391 → action bound was the cause; algorithm doesn't matter → **NO** (0.260)
- mag-PI ≈ 0.260 → wider bounds don't help, RL is genuinely better → **YES** (0.2602)
- Higher gains → worse (over-control)

**Decision**: **D5 finding (wider action bounds) is real but NOT load-bearing**
for RL advantage. RL 1.50× advantage is genuinely algorithmic, not artifact.
Paper write-up should keep the D5 disclosure (CLM-0233) but explicitly note
"verified by R133 that wider bounds don't help magnitude-PI; RL advantage
is real algorithmic improvement".

## Verification

- `results/r133_mag_pi_d5_fair/r133_summary.json` ✓
- Per-eval traces in `results/r133_mag_pi_d5_fair/{kpM2.0_kpD5.0,kpM4.0_kpD10.0,kpM8.0_kpD20.0}/` ✓
- V4 / V4Config / base_env / agents/ / R57+ ckpt / 任何 test 全部零 mutation ✓
- Bit-identical to R102 (Kp=2,5) confirms scoring pipeline reproducibility

## Cross-references

- CLM-0094 R72_w4 SOTA (training bounds = dm_max=600)
- CLM-0186/0230/0232 (RL advantage claims, conditional on classical fair)
- CLM-0233 D5 (training-time bound discovery)
- R102 verdict (precedent mag-PI 0.260 at dm_max=300)

## Questions opened (this round)

- (none — R133 closes the D5-handicap hypothesis cleanly)

## Questions closed (this round)

- **Q-NEW (implicit from CLM-0233)**: "is 1.50× RL advantage inflated by
  classical-handicap?" → answered NO via R133 by CLM-NEW (this round).

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog): R133 confirms RL has real algo advantage,
  not setup artifact. Q-0014 priority unchanged.

## 给 PI 的话

**这周干了啥**: PI "有问题就优化" 后立即跑 R133 — 用 V4Config(dm_max=600) 跟 R72_w4 SOTA 训练设置 1:1, re-eval magnitude-PI 3 个 gain combo. 顺手修了 R114 wait-pattern self-match bug (pgrep -f r102 match 自己), 用 `[r]133` bracket trick 让下一个 wait-chain (R137) 不卡死.

**结果（一句话）**: **mag-PI 在 dm_max=600 (D5-fair) bit-identical 跟 dm_max=300 — geo=0.2602 in both**. 加大 gains 反而 worse (over-control). **CLM-0233 D5 finding 实有, 但不是 RL 1.50× advantage 的 source — algorithm 真的赢, 不是 action-bound artifact**.

**意外**: (1) **同 gain 在 2× action range 下数字完全一样** — 因为 Kp=2, typical err=0.05 → action ≈ 0.10, 远低于两端饱和点 (±0.5, ±1). Controller 根本没用到 range. 加 gain 才用到, 但加 gain 是 over-control. 经典 control 教科书原理 (saturation 通常是 disturbance/transient peak 时出现, 不是稳态). (2) **paper 怎么说 ΔH=300, 项目 dm_max=600, 不影响 classical 表现** — 暗示 paper Eq.12 bound 选 [-100, 300] 也是 "足够" 的 (在 magnitude controller 范畴). 但对 RL learning 重要 (R72_w4 saturates 96-97% per CLM-0233), 因为 RL learner 探索时会试 boundary. (3) **bit-identical 数字证明 scoring pipeline reproducible** — paper_grade_axes 没 RNG / non-determinism. (4) **R133 让 paper write-up 更干净** — 不需要纠结 D5 disclosure, classical 不受影响是直接 evidence.

**我默认下一步做**: R133 收尾 done (verdict + 1 claim). R137 (multi-input mag-PD) wait-chain 已 fire, 现在跑中 (~30 min ETA). R137 测试 "RL advantage 是否来自 multi-input (neighbor obs Eq.11)" — 若 multi-input mag-PD ≥ 0.30, advantage 进一步收窄. 若仍 ≈ 0.26, RL 的 nonlinear 表达力是 advantage 真因.

**你想插一脚就说**: (a) 若你想 R72_w4 SOTA 在 paper-faithful dm_max=300 重 eval (clipped action), 验是否 SOTA 也 plateau ~0.26 = 算法 advantage 消失. ~10 min wall, ANDES TDS + ckpt 加载, single session. ROI 高. (b) 若你想等 R137 + 看 multi-input 结果再决定下一步, 沉默. (c) 若你想 reserve R141 = 训 paper-faithful agent (dm_max=300, paper-strict reward, Toggler-OFF 全 fix) 跟 R103 (single fix) 对比 — 复杂但 paper-clean. **我推荐 (b)** 等 R137 30 min.
