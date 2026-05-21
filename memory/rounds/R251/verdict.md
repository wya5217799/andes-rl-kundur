# R251 verdict — Scalar s50 baseline ANCHOR: 0.266 (not 0.327), revises R246 -28% → -12%

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — anchor baseline established; R246 over-stated
**Type**: research
**Wall**: ~13 min training + 2 min scoring

## TL;DR

scalar+s50+full V4 reward (phi_h=phi_d=0.0056, phi_f=100, phi_abs=50).
Result: geo=**0.2662**, LS1=0.284, LS2=0.249, cum_rf=**-0.0878**.

**True scalar s50 baseline = 0.266, not the estimated 0.327**. R246
(scalar s50 only-phi_abs = 0.235) is **-11.9% from this true baseline**
(not -28% as CLM-0410 inferred). Consistent with R242 (scalar s51
-15.7%) magnitude band.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0.0056 --phi-d 0.0056 --phi-f 100 --phi-abs 50 \
    --save-dir results/r251_w1_scalar_full_v4_s50

python scripts/score_run.py --label r251_w1_scalar_full_v4 \
    --ckpt-dirs results/r251_w1_scalar_full_v4_s50 \
    --out-dir results/r251_w1_scalar_full_v4_s50
```

## DUAL-METRIC table (final scalar cross-seed, all baselines measured)

geo (11-axis v3.1):

| Seed | scalar full (measured) | scalar only-phi_abs | Δ |
|------|------------------------|---------------------|---|
| s54  | 0.391 (R72_w4)         | 0.3954 (R239)       | +1.1%   |
| s51  | 0.3562 (R154_w2)       | 0.3003 (R242)       | -15.7%  |
| s50  | **0.2662 (R251 NEW)**  | 0.2346 (R246)       | **-11.9%** |

cum_rf (paper §IV-C):

| Seed | scalar full cum_rf | scalar only-phi_abs cum_rf | Δ |
|------|---------------------|----------------------------|---|
| s54  | (R72_w4 no summary) | -0.0694 (R239)             | (no ref) |
| s51  | -0.0691 (R154_w2)   | -0.0731 (R242)             | -5.8% |
| s50  | **-0.0878 (R251)**  | -0.0917 (R246)             | **-4.4%** |

## Result classification

R251 plan pre-registered outcomes:
- 0.32-0.35 (R242/R246 real drop): partial — actual 0.266, lower
  than the 0.32 prediction. But still LARGER than R246's 0.235.
- 0.24-0.28 (R246 at-baseline): close — R251 0.266 is at the high
  end of this band; R246 0.235 is still -11.9% below.
- < 0.10: ❌ not collapsed

**Outcome**: scalar s50 baseline 0.266 is **lower than estimated 0.327
but higher than R246 0.235**. The "scalar seed-sensitive" finding is
real but smaller in magnitude than CLM-0410 stated.

## Big NEW finding: scalar's basin ceiling is highly seed-dependent

Comparing 3-seed baselines:

| Seed | scalar full V4 | hreg full V4 | scalar/hreg ratio |
|------|----------------|--------------|-------------------|
| s54  | 0.391 (R72_w4) | 0.4152 (R201) | 0.94 |
| s51  | 0.3562 (R154_w2) | 0.3901 (R203) | 0.91 |
| s50  | **0.2662 (R251)** | 0.3515 (R185) | **0.76** |

scalar/hreg ratio drops from 0.94 (s54) to 0.76 (s50) — scalar's
basin ceiling at s50 is 24% BELOW the hreg ratio of other seeds.

**scalar's full-V4 baseline spans 0.266→0.391 across seeds (32%
spread); hreg spans 0.352→0.4152 (15% spread)**. scalar is 2×
more variance-sensitive across RNG basins, consistent with
CLM-0181/0182 LSTM-hidden-state-drift mechanism.

## Revised paper claim 5 narrative

(Full text in CLM-0435.) Three findings:
1. paper-strict universal collapse (gauge invariance) — robust both metrics
2. hreg + only-phi_abs paper-faithful drop-in: ±2% on geo, -3 to -6% on cum_rf
3. scalar seed-sensitive on BOTH baseline AND paper-term contribution

Recommendation: hreg+phi_abs (paper-rescaled R18 weights) is the
V4-compatible drop-in, accepting 3-6% cum_rf cost.

## Questions opened (this round)

- (none — anchor experiment closes the R242/R246 baseline question)

## Questions closed (this round)

- "Is R242/R246 scalar s50/s51 drop real, or estimated-baseline
  artifact?" Answered: **real, but smaller magnitude than
  initially framed** (-11.9% not -28% at s50).

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：R251 是 CRITICAL anchor experiment. 之前 R242/R246/R247
所有 verdict 都比 estimated scalar s50 baseline (~0.327), 但**从来没
measured**. R251 直接训 scalar s50 full V4 reward 来 anchor.

**结果（一句话）**：R251 = geo **0.2662** (cum_rf -0.0878). 估计 baseline
0.327 too high (off by 19%). R246 (only-phi_abs 0.2346) 真实 drop =
**-11.9% on geo, -4.4% on cum_rf**, **不是 -28%**.

**意外**：两个大意外:
1. **scalar s50 baseline 比估计低 19%** — 之前 estimate (= R204 hreg s50
   × s54 ratio 0.94) 错误地假设 ratio cross-seed 不变. 实际 scalar/hreg
   ratio 在 s50 是 0.76 (vs s54 0.94, s51 0.91). scalar 在 s50 basin
   ceiling 本身就低.
2. **R246 drop 跟 R242 drop 现在同 magnitude band** (-12% vs -16% on geo).
   之前 R246 看起来是 "scalar-seed-sensitivity 极端 outlier", 现在 看起来
   是 "scalar 在 non-s54 seeds 普遍 -12 to -16% on geo + -4 to -6% on
   cum_rf 的 stable pattern". 仍然 substantial drop, 但 not outlier.

**paper claim 5 corrections accumulated** (CLM-0430 dual-metric +
CLM-0435 baseline anchor):
- 旧版: "paper Eq.14 universally vestigial except scalar+s51 -16% outlier"
- 中版 (CLM-0410): "scalar seed-sensitive, hreg universal-inert"
- 新版 (CLM-0435): "hreg paper-faithful drop-in (±2% geo, -3 to -6%
  cum_rf 一致); scalar 既 basin-ceiling-sensitive 又 paper-term-
  sensitive on non-s54 seeds (-12 to -16% geo + -4 to -6% cum_rf)"

**我默认下一步做**：
1. 把 CLM-0435 sync 到 gauge-invariance memo (R246 number update +
   final paper claim 5 corrected magnitudes).
2. 评估 paper-Sec.IV-D-contribution-5 现在 **publishable**: gauge
   invariance + 4-cell paper-strict collapse + 3-seed hreg cum_rf
   pattern + 3-seed scalar baseline+only-phi_abs cross + dual-metric
   honest framing + R18-rescale-and-phi_abs-both-required recipe.
   8 layer 全完整, 数据足 paper figure.
3. 推荐 **暂停 autonomous loop 一阵**, 写 paper draft 用现有数据.
   继续跑只是 incremental, 已 saturated.

**你想插一脚就说**：CLM-0430 + CLM-0435 修正后, paper claim 现在 strong
+ honest. 如果你 OK 这个 narrative, 我建议 close 这轮 autonomous loop,
focus 写 paper draft (sec_iv_d_paper_eq14_gauge_invariance.md 是 ready
foundation). 如果还想 continue 跑, 我可以 design R252+ — 但建议 stop.

## Cross-references

- R246 (scalar s50 only-phi_abs = 0.2346 — what R251 anchors)
- R242 (scalar s51 only-phi_abs = 0.3003)
- R239 (scalar s54 only-phi_abs = 0.3954)
- R249 (hreg s50 only-phi_abs = 0.3581 — algo-class anchor)
- R185 (hreg s50 full = 0.3515 — same-algo cross-seed reference)
- R154_w2 (scalar s51 full = 0.3562 — same-algo+config cross-seed reference)
- R72_w4 (scalar s54 full = 0.391 — same-algo+config cross-seed reference)
- CLM-0410 (R246 -28% drop claim, **superseded by R251 anchor**)
- CLM-0430 (dual-metric methodological audit)
- CLM-0435 (this round's claim)
- docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md
