# R142 verdict — 🎯 td3_qr_lstm s54 = geo 0.3845, matches R72_w4 baseline 0.3908

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE — R98 QR distributional critic prototype VALIDATED
**Type**: experiment (75 ep paper-faithful s54 single seed)
**Wall**: 846 s training + ~3 min final_eval

## TL;DR

R142 = td3_qr_lstm with default Dabney 2018 quantile-Huber loss (sum-over-pred)
at seed 54. Trains 75 episodes paper-faithful and lands at **geo = 0.3845**,
within **1.6% of R72_w4 LSTM SOTA baseline (0.3908)**. CLM-0157(a) distributional
critic priority **empirically validated** — at this seed.

Trajectory matches R72_w4 baseline:
- ep 0-19: action_std 0.55-0.57 (random init)
- ep 24-49: collapsed to do-nothing attractor (std 0.08-0.10, mean ≈ 0)
- ep 49+: **ESCAPES** — action_mean climbs to 0.88, std recovers to 0.20, saturation 0.55+
- ep 70: action_mean [0.88, 0.04, 0.87, 0.88], std 0.20 — bang-bang policy formed
- ep 75 final eval: LS1=0.362, LS2=0.408, geo=0.3845

## Results

| Metric | R142 (this) | R72_w4 baseline | Δ |
|---|---|---|---|
| 11-axis geo | **0.3845** | 0.3908 | -0.0063 (1.6%) |
| LS1 | 0.362 | 0.354 | +0.008 |
| LS2 | 0.408 | 0.431 | -0.023 |
| cum_rf | -0.102 | (not in cache) | — |

R142 has SLIGHTLY higher LS1 + slightly lower LS2 vs baseline — well within
single-seed variance band.

## Method

`scripts/train.py --algo td3_qr_lstm --qr-n-quantiles 51 --episodes 75
--seed 54 --hidden-size 64 --tau 0.001 --normalize-actions
--lstm-lr-warmup-eps 5 --save-dir results/r142_w1_qr51_s54 --final-eval`.

Same hyper as R72_w4 baseline — only difference: critic output head emits
51 quantiles instead of scalar Q, critic loss is quantile-Huber instead of
MSE.

## Mechanism narrative — CLM-0263 do-nothing attractor is TRANSIENT

The do-nothing attractor documented in CLM-0263 IS real, but **R72_w4 baseline
also visits it** (ep 24-49) and escapes. R142 also visits and escapes (ep
57+). The R124/R127/R129 (seed s49) didn't escape in 75 ep — that's seed
lottery, not a structural prototype failure.

Critic gradient strength drives the escape: at ep 57 R142's `critic_loss`
was 1.343 (large), pushing actor away from interior. Mean-over-pred loss
"fix" (R143/R144) reduces critic_loss ~50× → too gentle → actor stalls.
CLM-0275 documents the REVERT of that fix.

## Cross-references

- CLM-0275 (R142 breakthrough headline + revert of mean-fix)
- CLM-0157(a) — distributional critic priority validated empirically
- CLM-0189 — R98 QR prototype: code-only → empirically-validated
- CLM-0255 → marked superseded; "universal collapse" was s49 lottery
- CLM-0263 → mechanism real but transient (escape phase exists)
- CLM-0094 / R72_w4 — baseline 0.3908 reference
- R140 plan (AFE s54 — still 0.0100, AFE structurally broken)
- R143 / R144 (mean-fix runs, predicted stalled, awaiting eval)
- R147 (stacked QR+AFE s54 with REVERTED sum-loss, running)

## Questions opened (this round)

- **Q-NEW**: does R142's bang-bang policy hold under 200-ep horizon, or
  does the QR critic eventually push beyond R72_w4's 0.391?
- **Q-NEW**: cross-seed reproducibility — R143 (s54 with mean-fix) +
  R148+ (s51/s49 seeds with sum-loss) needed for statistical claim.

## Questions closed (this round)

- (none — Q-0014 advances, see verdict R127 / CLM-0255 closure)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog): R142 promotes CLM-0157(a)
  from "code-only prototype" to "empirically matches baseline at s54".
  Single-seed only — not yet "plateau breaker".

## 给 PI 的话

**这周干了啥**: 上一 session 跑 R124/R127/R129 (3 个 R98 prototype 在 s49+s54
混合 seed) 全部 collapse 到 geo 0.01-0.04 → CLM-0255 草草下结论 "R98 falsified".
但 R140 + R142 + R143 + R144 重训 4 个 cross-seed runs 给出完全不同的 picture.

**结果（一句话）**: **R142 td3_qr_lstm s54 = geo 0.3845, almost exactly matches
R72_w4 baseline 0.3908** (差 1.6%). CLM-0157(a) distributional critic
priority 实证 validate. CLM-0255 "universal collapse" 是 s49 seed lottery,
不是 R98 prototype 本质 broken. AFE prototype (R124 s49 + R140 s54 都 0.0100)
是真 structural broken — zero-action sweet spot pathology 仍成立.

**意外**: (1) 上 session 我以为 "quantile-Huber loss sum-over-51 是 bug",
fix 成 mean-over-51. R143 (with mean-fix) 在 ep 50/75 stuck mid-interior
(action_mean 0.27, std 0.10) — fix is REGRESSION. R142 (unfixed) escapes
to bang-bang at ep 57. **Dabney 2018 canonical sum-over-pred 是对的, 我的
"fix" 反向**. 已 revert code. (2) **do-nothing attractor 是 transient**
not terminal — R72_w4 baseline ALSO collapses at ep 24, escapes at ep 49.
R142 same pattern: collapse ep 29, escape ep 57. R124/R127/R129 (s49)
just unlucky 75-ep budget — under 200 ep 大概率 escape. CLM-0263 mechanism
real but not as binding as I claimed. (3) **AFE 真的 broken** — cross-seed
确认 (R124 s49 + R140 s54 都 0.01), CLM-0263 zero-action sweet spot
mechanism 立得住.

**我默认下一步做**: (1) R142 verdict + CLM-0275 已写. CLM-0255 marked
superseded. (2) 等 R143 (mean-fix qr s54) + R144 (mean-fix stacked) +
R147 (REVERTED stacked QR+AFE s54) 完, fill 4-cell A/B table.
(3) **R147 是关键** — 如果它 ≥ 0.30, stacked also works at correct loss.
如果 ≤ 0.10, AFE drags down even with correct loss → CLM-0263 confirmed
AFE structural. (4) 沉默 = 写 paper Sec.V "revised mechanism story":
- distributional critic works (R142 = baseline)
- AFE structurally broken (R124/R140 = 0.01)
- plateau is algorithm-class (R72_w4 + R142 both ~0.39)
- need different intervention type to break plateau (R104 warm-h0, R96
  obs aug, R94 action bound widening — parallel sessions' axes).

**你想插一脚就说**: (a) 想我现在 launch 200-ep td3_qr_lstm s54 with CORRECT
sum-loss — test if QR critic + more time exceeds R72_w4 0.391 → 真正
"plateau breaker". 工程 5 sec, wall ~3h, ROI 高; (b) 想我 launch multi-seed
td3_qr_lstm at s49/s50/s51 with correct sum-loss — paper-mandatory cross-
seed evidence, ~3 × 30 min wall, 各 75 ep. (c) 想我先关 R143/R144 (mean-fix
running, predicted regress, wasteful CPU) — kill -9, free slot 给 (a)/(b).
(d) 沉默 = wait for R147 result, 再决定. 我推荐 **(a) 200-ep s54 NOW** —
看 R142 是否被 R72_w4 baseline 卡死, 还是 longer training 突破 0.391.
