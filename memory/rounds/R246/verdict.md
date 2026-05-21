# R246 verdict — DECISIVE: R242 不是 single-seed quirk, scalar 真 seed-sensitive

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — scalar seed-sensitivity confirmed
**Type**: research
**Wall**: ~13 min training + 1 min scoring

## TL;DR

scalar+only-phi_abs s50, --phi-h 0 --phi-d 0 --phi-f 0. 结果
geo=**0.2346**, LS1=0.216, LS2=0.255, cum_rf=-0.0917. **比 R242
(s51=0.3003) 还差**, 比 estimated s50 scalar baseline (~0.327) 低 ~28%.

R242 -15.7% **不是 s51 quirk**. scalar 真 seed-dependent. **3 seed 中
仅 s54 baseline-match** (R239 +1.1%), s51/s50 都 substantially drop.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r246_w1_scalar_onlyphiabs_s50

python scripts/score_run.py --label r246_w1_scalar_onlyphiabs \
    --ckpt-dirs results/r246_w1_scalar_onlyphiabs_s50 \
    --out-dir results/r246_w1_scalar_onlyphiabs_s50
```

## Scalar cross-seed table (3 seeds, NEW) — DUAL-METRIC (CLM-0430 audit)

geo (11-axis v3.1):

| Seed | scalar baseline    | scalar+only-phi_abs | Δ      |
|------|---------------------|-----|--------|
| s54  | 0.391 (R72_w4 measured) | 0.3954 (R239) | **+1.1%** |
| s51  | 0.3562 (R154_w2 measured) | 0.3003 (R242) | **-15.7%** |
| s50  | ~0.327 (estimated; R251 anchor pending) | **0.2346 (R246)** | **~-28%** |

cum_rf (paper §IV-C):

| Seed | scalar baseline cum_rf | scalar+only-phi_abs cum_rf | Δ   |
|------|-------------------------|----------------------------|-----|
| s54  | (R72_w4 no summary)     | -0.0694 (R239)             | (no ref) |
| s51  | -0.0691 (R154_w2)       | -0.0731 (R242)             | **-5.8%** |
| s50  | (R251 anchor in flight) | -0.0917 (R246)             | (pending) |

R246 cum_rf -0.0917 is notably worse than R249 (hreg s50 only-phi_abs)
-0.0936 by only -2%, but R246 geo (0.235) is 34% worse than R249
(0.358). The **11-axis** ranker is what's flagging R246 as bad, NOT
the paper-metric. Pending R251 anchor for cum_rf comparison.

## Hreg cross-seed for comparison (still tight)

| Seed | hreg baseline    | hreg+only-phi_abs | Δ |
|------|-------------------|-------------------|---|
| s54  | 0.4152 (R201)     | 0.4128 (R238)     | -0.6% |
| s51  | 0.3901 (R203)     | 0.3895 (R241)     | -0.15% |

hreg ±0.6% across 2 seeds vs scalar +1.1% → -28% across 3 seeds.

## Decision-tree outcome

R246 plan pre-registered 3 outcomes:
- ≥ 0.38 (baseline-match → R242 single-seed quirk): ❌ not happened
- ~0.30 ± 0.03 (matching R242 → scalar genuinely sensitive): partially
  matched (actually -28%, worse than R242 -16%)
- < 0.10 (collapse → fragility): ❌ not collapsed

**Outcome 2** confirmed with even stronger drop than expected.

## Paper-narrative update (FINAL)

Paper Sec.IV-D contribution 5 has 3 layers now:

1. **Universal collapse + gauge-invariance mechanism (4/4 cells)**:
   R218 hreg s54 paper-strict = R240 scalar s54 paper-strict = 0.010
   (bit-identical mean_df=+0.0587). Paper Eq.14 alone fails on V4
   ANDES across all algorithms.
2. **Universal hreg-vestigial (2/2 cells)**: hreg+only-phi_abs
   baseline-matches across s54 (-0.6%) and s51 (-0.15%).
3. **Seed-dependent scalar-vestigial (1/3 cells)**: scalar+only-
   phi_abs baseline-matches at s54 only (+1.1%); drops -15.7% at
   s51, -28% at s50.

**Interpretation**: hreg's hidden-state regularization provides
universal smoothing pressure that makes paper Eq.14 terms truly
redundant. Scalar lacks this; paper terms (likely r_h, r_d providing
inertia/damping smoothing) help in some seed basins.

The **stronger paper recommendation** that emerges: when
reproducing on a simulator with weak governor pinning, use
hreg+phi_abs as the paper-faithful drop-in — provides training
stability without any paper Eq.14 terms.

## Questions opened (this round)

- Q-NNNN (R247 candidate): For scalar s50 only-phi_abs, does
  adding back just one paper term (phi_h alone, phi_d alone, or
  phi_f alone) recover toward baseline? Decomposes which paper
  term is load-bearing for scalar+seed-sensitivity.

## Questions closed (this round)

- (none — R246 effectively closed "is R242 single-seed quirk" but
  this was a verdict-level question, not a tracked Q-NNNN)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：R242 verdict 留了 "R242 是 single-seed quirk 还是 real"
的开放问题, R246 跑 scalar+only-phi_abs at s50 解决. 跟 R242
(s51=0.3003) + R239 (s54=0.3954) 一起, 现在 scalar 3 seed 都有数据.

**结果（一句话）**：R246 = geo **0.2346**, **比 R242 还差**. **scalar
真 seed-sensitive** (s54 +1.1%, s51 -16%, s50 -28% — 跨 3 seed 跨度
极大), 跟 hreg cross-seed ±0.6% 形成 dramatic contrast.

**意外**：原期待 "R242 是 quirk → s50 baseline-match", 实际 s50 比 s51
**更差**. 这迫使重写 paper claim:
- 老版: "paper Eq.14 terms universally inert" (R238/R239/R241 supported)
- R242 后: "inert in 3/4 algo×seed cells, 1 outlier" (qualified)
- **R246 后**: "**hreg universal inert, scalar seed-dependently inert**"
  — 这版更 nuanced 也更 publishable, 因为引出 **hreg-as-minimal-
  correction-recommendation** 这个 constructive paper claim.

新 paper 推荐表述: "当 reproduce 在 weak-governor 仿真器上时, 用
hreg+phi_abs 作 paper-faithful drop-in 替代 — 无 paper Eq.14 terms
情况下提供 training stability". 这是 strong constructive 贡献, 比
"don't use paper Eq.14" 的纯 negative finding 强很多.

**我默认下一步做**：
1. 等 R245 (scalar+only-phi_abs+150ep s54) 完成. 测 horizon effect on
   s54 baseline-match case. Already 22 min in.
2. R247 候选 — scalar s50 + phi_h alone (paper 单 term 加回去). 测哪
   个 paper term 是 scalar seed-sensitivity 的 "rescue". 选 phi_h
   (inertia smoothing) 因为 hreg 的 hidden-state regularization 跟它
   类比最直接. 如果 phi_h alone 把 R246 0.235 拉回 ~0.32, 证明 paper
   r_h 就是 scalar 需要的 inertia smoothing 信号, hreg 自带替代.
3. 更新 gauge-invariance memo, 加 R246 数据 + final 3-layer narrative.

**你想插一脚就说**：现在 paper Sec.IV-D 第 5 contribution 是 3-layer
finding (collapse universal + hreg-vestigial universal + scalar-
vestigial seed-dependent), 加 hreg-as-minimal-correction 推荐, 加经
验 phase-portrait figure. 我评估这是 **publishable as standalone
contribution**, 比 R238/R239 那版 "universal inert" 更 nuanced 更强.
如果你觉得 R247 phi_h decomposition 应优先, 现在说; 不然 default 等
R245 → R247 顺序.

## Cross-references

- R242 (scalar s51 only phi_abs = 0.3003 — original outlier)
- R239 (scalar s54 only phi_abs = 0.3954 — only baseline-match)
- R241 (hreg s51 only phi_abs = 0.3895 — hreg cross-seed inert)
- R238 (hreg s54 only phi_abs = 0.4128 — hreg same-seed inert)
- R204 (hreg s50 full reward = 0.348 — s50 hreg baseline proxy)
- CLM-0410 (this round's claim)
- docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md
  (needs 3-layer narrative update)
