# R106 verdict — D4 env stress envelope reveals magnitude overfit

**Date**: 2026-05-19
**Status**: DONE — single-wave closure
**Type**: D4 axis from R84 plan (env stochasticity floor)
**Wall**: ~13 min ANDES (under 3-slot contention) + scoring

## TL;DR

R72_w4 SOTA × disturbance magnitude scale ∈ {0.5, 0.75, 1.0, 1.25, 1.5,
1.75, 2.0} × LS1+LS2 = 14 evals. **geo profile is inverted-U peaked at
scale=1.0 (paper baseline)**: 0.298 / 0.361 / **0.391** ← peak / 0.366 /
0.330 / 0.261 / 0.185. cv_geo = 0.21 (moderate env variance). The
SOTA is **distributionally overfit to paper magnitude**: smaller (0.5×)
and larger (2.0×) disturbances both drop performance by 24-53%.

Gate: `ENV_FLOOR_MODERATE_REPORT_AS_RANGE`. 0.391 is partially a noise
ceiling (cv 0.21), but mostly an overfit-to-training-distribution
artefact, not a pure policy ceiling. [[CLM-0202]] records this.

R85+ candidate PROMOTED: random-magnitude training (domain
randomisation over disturbance amplitude).

## Methodology

`scripts/r106_d4_env_floor.py`. Canonical `evaluation/paper_path.run_scenario`
+ `evaluation/summary.score_trace_files`. Same env_seed=42 across all
14 evals; only delta_u scaled. STEPS=150 (30s @ DT=0.2). No training,
read-only ckpt load.

ANDES occupancy: 14 × ~10s ANDES = ~140s pure ANDES under 3-slot
contention (R103 training + R100 hreg training + R102 magnitude-pi
analysis concurrently). Total wall stretched to ~13 min due to
contention but no TDS divergence at any magnitude.

## Per-scale results

| scale | LS1 11-axis | LS2 11-axis | geo | cum_rf | n_steps |
|---|---|---|---|---|---|
| 0.50 | 0.218 | 0.409 | 0.298 | -0.020 | 150 |
| 0.75 | 0.298 | 0.436 | 0.361 | -0.040 | 150 |
| **1.00** | 0.354 | 0.432 | **0.391** | -0.068 | 150 |
| 1.25 | 0.341 | 0.392 | 0.366 | -0.105 | 150 |
| 1.50 | 0.308 | 0.353 | 0.330 | -0.152 | 150 |
| 1.75 | 0.232 | 0.293 | 0.261 | -0.211 | 150 |
| 2.00 | 0.162 | 0.211 | 0.185 | -0.285 | 150 |

Geo distribution: mean=0.313, median=0.330, σ=0.066, cv=0.21.

## Cross-references

- [[CLM-0144]] (91-round algo plateau)
- [[CLM-0202]] (this round's main finding)
- [[CLM-0200]] (synthesis — D4 axis result feeds in)
- R84 plan §D4 (this round implements that axis)
- R103 plan (reward shape ablation — companion mechanism test)

## Questions opened (this round)

- (none new — magnitude-randomised training proposal goes into R85+ candidate list, not Q-form)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog) — env-floor axis answered: moderate variance, not the plateau mechanism but it IS distributional overfit.

## 给 PI 的话

**这周干了啥**：R84 plan 的 D4 axis (env stochasticity floor) 一直 deferred. 用户 "继续研究 别提醒", 我跑 R72_w4 SOTA × 7 个 magnitude scale (0.5×-2.0× paper baseline) × LS1+LS2 = 14 evals. 量 σ_geo / mean_geo.

**结果（一句话）**：**Inverted-U peaked at paper baseline** — geo 0.298 / 0.361 / **0.391** / 0.366 / 0.330 / 0.261 / 0.185 across scales 0.5-2.0. cv_geo = 0.21 moderate. Policy 对 paper magnitude **distributionally overfit**, 0.5× / 2.0× 两端 drop 24-53%.

**意外**：(1) 0.5× scale geo=0.298 比 1.0× 还低 — smaller disturbance 不是 "easier", 是 "policy 没训过这个 regime". 这把 0.391 plateau 的解读从 "pure algo ceiling" 改成 "magnitude-distributional artefact". (2) cv=0.21 不是 noise ceiling (那需要 cv≥0.30) — 是真 overfit signal. (3) 2.0× 没 TDS 发散 — operating envelope 没破, policy 退化是 graceful degradation 不是 catastrophic failure.

**我默认下一步做**：(1) R106 closure + CLM-0202 入库 ✓. (2) R85+ 新 candidate **R113 = magnitude-randomised training**: 每 episode delta_u 乘 U[0.5, 2.0] random scale, R72_w4 hyper otherwise unchanged, 75 ep s54. Eval canonical (scale=1.0) + distribution. 如果 scale=1.0 geo ≥ 0.40 → plateau 部分破解 by domain randomization. 沉默就开 R113.

**你想插一脚就说**：(a) 想我立刻开 R113 magnitude-randomised training — 1 个 training run, ~30 min wall, 1 slot; (b) 想 R114 = cross-ckpt magnitude sweep (R75 / R63) 看 magnitude overfit 是不是 R72_w4 specific — 1 ANDES burst per ckpt, ~5 min total; (c) 等 R112 warm-h_0 env eval 出来 (跑中, ~80s wall) 一起看再决定. 我推荐 (默认) 等 R112 完成评估优先级再决定 R113 / R114.
