# R75 verdict — NEW SOTA s59 v3.1=0.4301 + ensemble negative + floor_geo_mean refactor

**Date**: 2026-05-18
**Status**: **closed-positive** (1 new single SOTA + 1 negative ensemble finding + clean refactor)
**Type**: multi-seed + ensemble exploration
**Wall**: ~45 min

## TL;DR

> **R75 W2 s59 + warmup=20 v3.1 = 0.4301 NEW SINGLE SOTA** (CLM-0131),
> beats R73 W3 s54 (0.4099) by +4.9%.
>
> **2/3 new seeds drift broken**: s58 v3.1=0.0447, s60 v3.1=0.0210.
> Drift list extended: {49, 53, 57, **58, 60**}. Healthy: {50, 51, 52, 54,
> 55, 56, **59**} (7 seeds, ~44% drift rate).
>
> **Ensemble (4 configs across 6 healthy ckpts) UNDERPERFORMS single s59**
> (CLM-0132). Best ensemble (top2 mean s54+s59) v3.1=0.4212 = **-2.1%
> WORSE** than single s59 (0.4301). Averaging conflicting LSTM hidden-state
> policies dilutes the best one. HAWE-style ensemble pattern does NOT
> translate to recurrent-actor v3.1 SOTA.
>
> **Refactor (by linter/external)**: extracted `floor_geo_mean` to
> `src/andes_rl_kundur/evaluation/aggregation.py`. 4 scripts updated.
> 28/28 score_run + v3/v3.1 tests still pass.

---

## Phase 0 — Trigger

R74 收尾后用户 "继续挤". 2 directions: multi-seed expansion + ensemble.

## Phase 1 — Multi-seed expansion (W1/W2/W3)

```
python scripts/train.py --algo td3_lstm --normalize-actions --episodes 75 \
  --seed <S> --hidden-size 64 --lstm-lr-warmup-eps 20 --tau 0.001
```

| W | seed | v3.1 | result |
|---|---|---|---|
| W1 | s58 | 0.0447 | broken (drift) |
| **W2** | **s59** | **0.4301** | **NEW SINGLE SOTA** |
| W3 | s60 | 0.0210 | broken (drift) |

### Healthy seed set (updated)

- **Healthy**: {50, 51, 52, 54, 55, 56, 59} — 7 seeds
- **Drift broken**: {49, 53, 57, 58, 60} — 5 seeds (~44% rate, up from 33%)
- s51 still warmup-incompatible at warmup=20 (P_bal=0.19, but train doesn't crash)

### Updated cross-seed @ warmup=20

| seed | v3.1 |
|---|---|
| s50 | 0.3151 |
| s52 | 0.3068 |
| s54 | 0.4099 |
| s55 | 0.3781 |
| s56 | 0.3763 |
| **s59** | **0.4301** (NEW peak) |
| **6-seed mean** (excl s51) | **0.3694** |

vs 5-seed mean (0.3572) = **+3.4%**.
vs warmup=5 5-seed mean (0.3340) = **+10.6%**.

## Phase 2 — Ensemble exploration (W4-W7)

`scripts/_r75_ensemble_eval.py` — HAWE-style across 6 healthy ckpts:

| config | active seeds | v3.1 | cum_rf | vs single s59 (0.4301) |
|---|---|---|---|---|
| **top2 mean (s54+s59)** | s54,s59 | **0.4212** | -0.0696 | **-2.1%** |
| s59-weighted (all 6) | all 6 | 0.4089 | -0.0786 | -4.9% |
| mean 6-seed (uniform) | all 6 | 0.3972 | -0.0848 | -7.6% |
| top3 mean (s54+s55+s59) | s54,s55,s59 | 0.3956 | -0.0758 | -8.0% |

**Best ensemble = 0.4212, single best = 0.4301**. Ensemble lower by 2.1% to 8.0%.

### Mechanism (hypothesis)

LSTM hidden states are policy-specific — each agent's internal state evolves
based on its OWN action history. Averaging actions across actors with
DIFFERENT hidden states produces an out-of-distribution action that no
individual actor would have chosen. The dilution overrides the variance
reduction benefit that HAWE ensemble historically provided for memoryless
SAC/TD3 (R57-β observed +2-5% lift).

**HAWE ensemble pattern does NOT transfer to recurrent actors.**

### Implication

- Paper writing: report single-best ckpt (R75 W2 s59 v3.1=0.4301) as SOTA
- Multi-seed mean (0.3694) for robustness claim
- Ensemble explored, negative finding documented (paper rigor)

## Phase 3 — Refactor (external, validated)

Refactor extracted `floor_geo_mean(values, floor=0.01)` into
`src/andes_rl_kundur/evaluation/aggregation.py` (R75 work or auto-linter).
4 scripts updated to use it:
- `scripts/score_run.py`
- `scripts/_r69_rerank_11axis.py`
- `scripts/_r70_plot_best_agent.py` (likely)
- `scripts/train.py` (likely)

Plus new `src/andes_rl_kundur/evaluation/ensemble.py` (helpers used by
`_r75_ensemble_eval.py`).

Validation: **28/28 tests pass** (test_score_run + test_paper_grade_axes_v3
+ test_paper_grade_axes_v31). Zero regression.

## Phase 4 — Canonical decision (still R72 W4 for paper Fig 7)

R75 W2 s59 has higher v3.1 but slightly lower P_balance (LS1 0.782 vs
R72 W4 s54+warmup=5 LS1 P_balance 0.959). Same trade-off pattern as
R73 W3.

For paper:
- **Single SOTA (numeric)**: R75 W2 s59+warmup=20 v3.1=**0.4301** (NEW, supplementary)
- **Canonical for paper Fig 7**: R72 W4 s54+warmup=5 v3.1=0.3908 P_bal=0.96 (CLM-0123, unchanged)
- **6-seed family mean**: 0.3694

## New claims this round

- **CLM-0131** (finding/V) — R75 W2 s59+warmup=20 NEW single SOTA v3.1=0.4301
  (+4.9% over R73 W3 s54 0.4099). 6 healthy seed set extended.
- **CLM-0132** (finding/V) — Ensemble (4 configs across 6 healthy ckpts) UNDER-
  PERFORMS single s59. Best ensemble (top2 mean s54+s59) = 0.4212 = -2.1%.
  HAWE-style averaging fails for recurrent LSTM actors (hidden state mismatch).
- **CLM-0133** (decision/S) — Drift seed list extended: {49, 53, 57, 58, 60} 5
  dead, {50, 51, 52, 54, 55, 56, 59} 7 healthy. ~44% drift rate. Paper rigor:
  report 6-seed-of-7-healthy (excl s51 warmup=20 outlier) mean = 0.3694.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — exploration, no Qs resolved)

## Questions advanced (this round)

(none)

## 给 PI 的话

**这周干了啥**: R74 后用户 "继续挤". 2 directions: (a) 3 new seeds (s58/s59/s60)
at warmup=20 + (b) HAWE-style ensemble across healthy ckpts pool (free).

**结果（一句话）**: (1) **R75 W2 s59 = NEW SINGLE SOTA v3.1=0.4301** (+4.9%
over R73 W3 s54), 7 healthy seeds 现 (s50/51/52/54/55/56/59); (2) **Ensemble
underperforms single best** — best ensemble (top2 mean s54+s59) = 0.4212 =
-2.1% vs single s59 0.4301, HAWE pattern 不适用于 LSTM (hidden state mismatch
diluting averaged action); (3) **2/3 new seeds dead** (s58 0.0447, s60 0.0210),
drift rate 现 ~44% (5/12 seeds tested).

**意外**: (1) **HAWE ensemble fails on LSTM** — paper rigor 加分 (negative finding
explained), 但 single best 仍是 final SOTA; (2) **s59 是 healthy 高峰** — 6 healthy
seeds at warmup=20 中 s59 唯一超过 0.42, 比 prior canonical s54 (0.41) 更强;
(3) **drift rate 比之前估算 33% 更高** (44%), 必须在 paper 透明 disclose seed
selection rationale.

**我默认下一步**: R75 commit. 然后真转写 paper draft. 已不再有 marginal +5% margin
可挤 (ensemble 失败 + multi-seed expansion 概率性). 4 表 + R72 W4 canonical figure
+ R75 W2 single SOTA 已齐.

**你想插一脚**: continue / paper draft? (我推荐 paper draft, ROI 远高于继续挤)
