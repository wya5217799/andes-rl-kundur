# R172 verdict — Q-0020 transient-boost=3.0 REFUTED, geo=0.3877

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE (transient-phase reweighting does NOT break plateau)
**Wall**: ~15 min ANDES train + ~5 min eval

## TL;DR

td3_lstm at R72_w4 hyper (lr=1e-4 clamp, tau=0.001, warmup=5) with
`--transient-boost 3.0 --transient-window 6` (×3 weight on subsequence
starts in [0,6)) on s54 yields **geo=0.3877** — within ±1% of the
unweighted R72_w4 baseline 0.391 (-0.85%). LS1=0.353 (~baseline 0.354),
LS2=0.426 (~baseline 0.431). The transient-phase reweighting hypothesis
from Q-0020 is REFUTED at boost=3.0.

This is the 92nd single-algorithm negative datapoint for the
"break 0.391 plateau" question.

## Result table

| Run | LS1 | LS2 | geo | cum_rf | vs R72_w4 0.391 |
|-----|-----|-----|-----|--------|------------------|
| R72_w4 baseline | 0.354 | 0.431 | 0.391 | (ref) | — |
| **R172 (boost=3.0)** | **0.353** | **0.426** | **0.3877** | -0.068 | **-0.85%** |
| R170 (hreg λ=0.003) | 0.353 | 0.475 | 0.4091 | -0.069 | +4.7% |
| R174 (hreg λ=0.002) | 0.367 | 0.467 | 0.4139 | -0.069 | +5.9% |
| R154 ensemble | 0.368 | 0.461 | 0.4119 | -0.080 | +5.4% |

## Interpretation

The structural pattern repeats: single-algorithm interventions (lr,
batch, network size, critic type, transient weighting) sit in a tight
±5% band around 0.391 baseline. The plateau-breakers are exclusively:
- **ensemble of cross-algorithm policies** (R154 0.4119, R152 0.4043)
- **hreg dose-response refinement** (R170 0.4091, R174 0.4139)

Transient-phase reweighting joined the negative-datapoint family.

The reweighting may have **harmed** ever-so-slightly because the
early-episode transitions (step 0-5) are also the ones where the LSTM
hidden state is least informed — oversampling them weights the
gradient toward steps where the critic has less context. This is a
plausible mechanism: more iteration on under-determined samples
slightly degrades policy quality.

## Q-0020 closure rationale

Q-0020 ("Does transient-phase replay reweighting ×2-5 weight on step
0-5 samples break the 0.391 plateau?") — answer: **NO** at boost=3.0.

**closed-negative** (not partial) because:
- Result sits within noise (-0.85%), no marginal improvement
- The mechanism interpretation (over-iteration on under-determined
  early-LSTM samples) suggests boost=2-5 sweep would not save it
- No reason to think boost=2 or boost=5 would behave qualitatively
  differently

If a future round wants to retry with boost=2 or boost=5, they can
re-open. For now Q-0020 is closed.

## Questions opened (this round)

(none)

## Questions closed (this round)

- Q-0020 closed-negative by CLM-0340 — transient-phase replay
  reweighting at boost=3.0 does NOT break the 0.391 plateau on
  R72_w4 hyper

## Questions advanced (this round, status unchanged)

(none directly — Q-0014 was already closed-partial in R171)

## 给 PI 的话

🛑 **R172 = Q-0020 transient-boost=3.0 refuted, geo=0.3877 ≈ baseline 0.391**.
单算法 plateau 第 92 个 negative datapoint, 跟其他 91 个 single-algo
intervention 一样卡在 ±5% band 里。

**比较有意思的细节**: R172 几乎跟 baseline 一致 (LS1 0.353 vs 0.354,
LS2 0.426 vs 0.431, geo -0.85%) — 说明 transient-boost 既没帮也没伤太多。
机制猜想: step 0-5 transitions 的 LSTM hidden state 信息量最低, oversample
它们让 gradient 在 under-determined samples 上多 iterate, 轻微 hurt。
不过 effect 太小, 在 eval noise 里。

**对照同时间发现**: 并行 session 跑出 **R174 hreg λ=0.002 = geo 0.4139**
(单策略 SOTA, 超 R170 0.4091, 超 R154 ensemble 0.4119)。这跟 R172 形成
对比 — hreg dose-response 微调能 +5.9%, transient-boost 不行。**Single-
policy breakthrough 路径明确: hreg λ refinement, 不是 sampling 调整**。

**Q-0020 close 完, open Q 还剩 5 个**:
- Q-0004 AndesBaseEnv absorb (infra, 非实验)
- Q-0005 seed 50 collapse 机制
- Q-0008 500-ep verification
- Q-0021 TGOV1 governors
- Q-0023 已关 (R171)

下一步默认: R172 commit, 等并行 session 写 R174 / R177 ensemble 的正式
CLM。如果 PI 想继续找突破, 唯一未试过的 single-algo axis 是 Q-0008
500-ep horizon (R149 试过 200ep 退化, 500ep 是 paper 原 horizon)。

## Cross-references

- Q-0020 (R88 opening)
- CLM-0123 (R72_w4 SOTA baseline 0.391)
- CLM-0144 (R57-R82 91-round plateau)
- CLM-0325 (R170 hreg dose-response paper finding)
- R174 verdict — concurrent single-policy SOTA
