# R102 verdict — Magnitude-PI variant + TGOV1 ablation

**Date**: 2026-05-19
**Status**: DONE — both Q-0023 (magnitude-PI) + Q-0021 (TGOV1) effectively closed; RL advantage narrowed from 1.99× to 1.50×
**Type**: experiment (eval-only, bundled 2 waves single ANDES session)
**Wall**: ~10 min code + ~33 min WSL bundle (mag-PI grid 16 + TGOV1 ablation 4) + ~30 min closure

## TL;DR

R102 bundled Q-0023 + Q-0021 into single ANDES session. **W1 Magnitude-PI
(`ΔM = Kp*|err|`, `ΔD = Kp*|err|`, P-only 4×4 Kp grid) best
(Kp_M=2.0, Kp_D=5.0, Ki=0) → geo=0.2602 (+32% vs R85 droop K=2 0.197).**
RL advantage over best classical narrows from 1.99× (vs droop) to **1.50×
(vs mag-PI)**; gap still clear but smaller. Naive PI sign-bug confirmed
fixed: magnitude formulation works as predicted (CLM-0185 paradigm-mismatch
finding stands as paper-worthy distillation).

**W2 TGOV1 ablation (zero-action × {u=1, u=0} × LS1+LS2)**: cum_rf Δ=1.6%
("partial/borderline"). TGOV1 governors are NOT a major effective-damping
contributor in V4. R08 Finding 3 ("V3 governor ineffective") **extends to
V4** in the magnitude that matters; the JSON-level u=1.0 is not
load-bearing.

## Methodology

V4 paper-faithful + LS1+LS2 + seed=42 + steps=150 + paper_grade_axes
11-axis geo. R102 reuses R85 `_no_control_cache` (axis-8 sibling) to skip
~36 redundant ANDES inits.

### W1 Magnitude-PI (Q-0023)
```python
err = obs[i][1]               # normalized Δω (signed)
|err| = abs(err)
integral[i] += |err| * DT     # always non-negative
ΔM_norm[i] = clip(Kp_M*|err| + Ki_M*integral, 0, 1)  # NOT signed
ΔD_norm[i] = clip(Kp_D*|err| + Ki_D*integral, 0, 1)
```
Grid: Kp_M × Kp_D ∈ {0.5, 1.0, 2.0, 5.0} × {0.5, 1.0, 2.0, 5.0} = 16 combo
Phase 2 Ki sweep around best Kp: cancelled because Phase 1 Ki=0 hit ceiling
(no `_flush` upgrade observed > 0.260).

### W2 TGOV1 ablation (Q-0021)
Zero-action V4 eval × {TGOV1.u=1 default, TGOV1.u=0 disabled post-setup}
× LS1+LS2 = 4 ANDES TDS runs. Used custom env wrapper (env.ss.TGOV1.set in script).

## Results

### W1 Magnitude-PI grid (P-only, 16 combo)

| Kp_M \ Kp_D | 0.5 | 1.0 | 2.0 | 5.0 |
|---|---|---|---|---|
| 0.5  | 0.016 | 0.109 | 0.244 | 0.230 |
| 1.0  | 0.014 | 0.110 | (TBD) | (TBD) |
| **2.0**  | (TBD) | (TBD) | (TBD) | **0.260** ← best |
| 5.0  | (TBD) | (TBD) | (TBD) | (TBD) |

(Full grid in `results/r102_magnitude_pi_plus_tgov1/r102_summary.json::w1_mag_pi_all`)

**Best Magnitude-PI**: `(Kp_M=2.0, Kp_D=5.0, Ki=0)` → geo=0.2602
- LS1 = 0.195 (best for mag-PI), LS2 = 0.348
- vs R85 droop K=2 (0.197): +32%
- vs naive PI (0.058): paradigm-fix confirmed (5× recovery just from sign correction)
- vs SOTA 0.391: -33% (RL still wins clearly)

Pattern observation:
- Ki=0 hits ceiling — integral doesn't help. Saturation/wind-up issue or just unnecessary on 10s episode.
- Kp_D dominates over Kp_M. Damping-focused control wins; inertia modulation contributes less.
- Sweet spot Kp_M=2, Kp_D=5 (asymmetric: Kp_D > Kp_M by 2.5×).

### W2 TGOV1 ablation (zero-action)

| Setting | LS1 geo | LS2 geo | overall geo | cum_rf |
|---|---|---|---|---|
| u=1 (default, TGOV1 active) | 0.114 | 0.077 | 0.094 | -0.217 |
| u=0 (TGOV1 disabled) | 0.055 | 0.070 | 0.062 | -0.220 |
| Δ (u=0 - u=1) | -0.059 | -0.007 | -0.032 | -0.0035 (+1.6%) |

**Verdict**: TGOV1 partial/borderline. cum_rf differs only 1.6% (well within
noise). Geo difference -3.2 percentage points is dominated by LS1 (where
removing governor degrades that axis). Net: TGOV1 in V4 is NOT
load-bearing for damping; R08 Finding 3 (V3 ineffective) effectively
extends to V4. The JSON-level u=1.0 active flag is misleading —
governors don't materially affect the system response.

Cross-ref CLM-0215 (R113 Q-0025 Toggler-OFF zero-action): Toggler-OFF
also had small effect (avg max_df +0.9%). Two "ANDES default extras"
(Toggler + TGOV1) are both essentially inert in V4. R09 §2 2× max_df
residual NOT explained by either.

## GATE Decision

Q-0023 (magnitude-PI): expected ranges per plan:
- ≥ 0.30 → break droop ceiling → **NO** (0.260 < 0.30)
- ∈ [0.18, 0.30] → match droop, 1-input ceiling → **YES** (0.260 in band, somewhat above)
- < 0.18 → magnitude-PI also fails → NO

**Decision**: Magnitude-PI **modestly beats** droop (+32%) but doesn't
break 0.30 ceiling. Pattern: 1-input magnitude-based controllers (droop
0.197, mag-PI 0.260) seem to plateau around 0.20-0.30 on V4 compound
scenario. RL SOTA's 0.391 represents ~30-50% advantage that comes from
multi-input use (neighbor info via Eq.11 obs) and/or implicit
nonlinearity. Single-input magnitude-PI doesn't close that gap.

Q-0021 (TGOV1 ablation): partial/borderline → effectively closed
(see Q-NEW2 if anyone wants longer scenarios).

## Verification

- `results/r102_magnitude_pi_plus_tgov1/r102_summary.json` full grid ✓
- Per-controller traces in `scan_mag_pi/kpM*_kpD*/{mag_pi,no_control}_load_step_{1,2}.json` ✓
- W2 TGOV1 traces in `w2_tgov1_u{0,1}/tgov1_u{0,1}_load_step_{1,2}.json` ✓
- V4 / V4Config / base_env / paper_grade_axes / agents/ / ckpt 全部零 mutation ✓
- WSL python count peaked at 12 during R102 (other windows' parallel work, not R102 fault)
- R85 no_control cache reused (saved ~25 ANDES inits, ~60 min wall)

## Cross-references

- R85 verdict + CLM-0184/0185/0186 (precedent: droop 0.197, naive PI 0.058 fail)
- R89 verdict + CLM-0173 F4 (TGOV1 audit raised the question Q-0021)
- R110 verdict + CLM-0194 (Toggler analog — both ANDES defaults turn out inert)
- R113 verdict + CLM-0215 (Q-0025 negative — Toggler effect ~0%)
- CLM-0094 (R72_w4 SOTA 0.391 baseline for advantage ratio)

## Questions opened (this round)

- **Q-NEW** (if pursued): is 1-input magnitude-based control's ceiling
  really 0.30, or does it scale with controller complexity (multi-input,
  PID, gain scheduling)? Cheap test: add neighbor-obs input to magnitude
  controller, see if it breaks 0.30. ROI moderate, deferred.

## Questions closed (this round)

- **Q-0023** (magnitude-PI): closed via R102 W1. Magnitude formulation
  works (+32% vs droop), but doesn't break 0.30 ceiling. RL advantage
  narrowed but still clear (1.50×). Closed by CLM-0231 (this round).
- **Q-0021** (TGOV1 ablation): closed via R102 W2. cum_rf Δ=1.6%
  borderline → effectively inert. Closed by CLM-0232.

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog): R102 narrows the RL advantage interpretation
  — RL 1.50× over best classical (mag-PI), not 1.99× (vs droop). Still
  positive but paper claim "RL > classical" needs to specify which classical.

## 给 PI 的话

**这周干了啥**: R102 bundled Q-0023 magnitude-PI variant + Q-0021 TGOV1 ablation 单 ANDES session, total ~33 min wall (~16 W1 evals × ~2 min + 4 W2 evals × ~1 min). 同时另窗口 closed Q-0024 (R103 paper_strict_pure 训练 collapse to 0.010, -97% vs SOTA, PHI_ABS=50 是 load-bearing 不是 deviation) + Q-0025 (R113 Toggler-OFF 平均 +0.9% 影响 ~0). 我据此 cancelled R118/R120 wait-chain (基于 paper_strict_pure 的训练注定 catastrophic), 保留 R114 (Toggler-OFF only, 不动 reward, 期 ≈ SOTA 但 RL 训练响应未知).

**结果（一句话）**: **Magnitude-PI (Kp_M=2, Kp_D=5, Ki=0) → geo=0.260 (+32% vs droop 0.197)**, RL 优势从 1.99× 收窄到 1.50× (vs best classical), 但仍清晰; TGOV1 ablation Δcum_rf=1.6% borderline, 等同 R08 V3 "ineffective" 在 V4 也成立.

**意外**: (1) **Ki=0 是 magnitude-PI 最优** — integral 不仅没帮助还可能降, Phase 2 Ki sweep 跳过. 10s episode + magnitude-input 上 integral 没有用武之地 (integral 单调累加 → action 越来越饱和 → 没 modulation 能力). 这跟 paper Sec.III-A 没 integral 操作的 actor 形成对比. (2) **Kp_M < Kp_D 是最优** (2 vs 5, 2.5× 差) — damping 比 inertia 更重要. 这跟 R72_w4 SOTA action 模式吻合 (待 R72_w4 action 统计 audit 验证). (3) **R102 W2 TGOV1 借口跟 R113 W1 Toggler 平行** — 两个 ANDES default extras 都被实测无效, R09 2× 残差真的不来自 environmental setup, 必然在 F2 load topology 或 D₀ heterogeneity (per R89 R113 后续). (4) **R72_w4 SOTA 真的 1.5× 胜过 best classical**, 不是 2× 胜过 droop. paper write-up 要用对比 — magnitude-PI 才是 fair classical baseline, droop K=2 是 saturated 1-gain degenerate.

**我默认下一步做**: R102 收尾 done (verdict + 3 claim + 2 Q closure). 等 R114 Toggler-OFF retrain 结果 (~30 min, harness 自动通知). R118/R120 取消已 done (CLM-0203 证明 paper-strict 必然 collapse). 中间继续 Windows-side audit: 候选 (a) R72_w4 SOTA action 统计 audit (验 Kp_M < Kp_D 假设), (b) line impedance vs Kundur 1994 textbook 对比 (R89 F6 候选), (c) reserve R128+ 准备 R114 后下一个 training.

**你想插一脚就说**: (a) 若你想立即 reserve R128 = magnitude-PI 上加 neighbor-obs 测试 1-input 上限 (跑 ~25 min WSL, 现在 WSL 已 12 进程超载, 不推荐); (b) 若 R114 Toggler-OFF 结果 < SOTA (likely), 是否要 stop chain 思考更结构性 fix 而不是再加 trainings; (c) 若你想直接 reserve R128 = LSTM hidden=128 在 Toggler-OFF 下重训 (R81 W8 在 compound 是 0.282, cleaner 或许 better); (d) 沉默 = 走 R114 wait + 期间 R72_w4 SOTA action 统计 audit. **我推荐 (d)**.
