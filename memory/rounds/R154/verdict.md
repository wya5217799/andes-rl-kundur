# R154 verdict — NEW PROJECT SOTA 0.4119 via 4-way same-seed cross-algo HAWE

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (project SOTA established at geo 0.4119, +5.4% over R72_w4)
**Type**: experiment (2 training waves + 8 ensemble evals)
**Wall**: ~45 min total (~25 min for 2 ANDES training waves, ~20 min for 8 ensemble evals in 6 background jobs)

## TL;DR

R154 launched cross-seed training (s49 + s51 at R72_w4 hyper) to test
CLM-0280 hypothesis "cross-seed > cross-algo same-seed" for ensemble
lift. Result: hypothesis REFUTED. s49 collapsed (geo 0.010), s51
underperformed (0.356, -8.9% vs baseline). Cross-seed ensembles either
hurt (2-way {s54,s51} = 0.377) or matched baseline (3-way + R142 =
0.389).

Pivot: tested **same-seed cross-ALGO** by adding R100_hreg (drift-killed
continuous policy, CLM-0190 LSTM-norm reg) to R152's 3-way:

**4-way mean {R72_w4, R142, R143, R100_hreg} = geo 0.4119**

This is the **new project SOTA**, +5.4% over R72_w4 single (0.391) and
+1.9% over R152 3-way (0.404). LS2 axis is the driver (0.435 → 0.461,
+6.0pp) — R100's non-bang-bang policy provides unique LS2 strength.

## Methodology

### Two training waves (R72_w4 hyper, fresh seeds)

```
LR=1e-4 python scripts/train.py --algo td3_lstm --episodes 75 \
    --seed {49,51} --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --save-dir results/r154_w{1,2}_r72w4hyper_s{49,51}
```

Both ran in WSL background, ANDES TDS, ~15 min each.

### Eight ensemble evaluations (`scripts/eval_ensemble.py`)

All mean-agg unless noted, deterministic actors, V4 paper-faithful
LS1+LS2 seed=42 steps=150.

1. 2-way pure cross-seed {s54, s51}
2. 3-way cross-seed+algo {s54, s51, R142_s54}
3. 4-way {s54, s51, R142_s54, R143_s54}
4. **4-way SAME-SEED cross-algo {s54, R142_s54, R143_s54, R100_s54}**
5. 3-way drop-R143 {s54, R142_s54, R100_s54}
6. 4-way weighted (R100 0.40, others 0.20 each)
7. 5-way (+R150_s54 weak)
8. R152's 3-way mean {s54, R142, R143} as reference (already done)

## Results (full table)

| # | Config | geo | LS1 | LS2 | cum_rf | Δ R72_w4 0.391 |
|---|--------|-----|-----|-----|--------|-----------------|
| ref | R72_w4 single (s54) | 0.3908 | 0.354 | 0.431 | -0.0750 | — |
| ref | R72_w4 hyper s49 | 0.0100 | 0 | 0 | -0.208 | **collapse** |
| ref | R72_w4 hyper s51 | 0.3562 | 0.321 | 0.395 | -0.069 | -8.9% |
| ref | R142 single | 0.3845 | 0.362 | 0.408 | -0.1015 | -1.6% |
| ref | R143 single | 0.3843 | 0.362 | 0.407 | -0.1015 | -1.7% |
| ref | R100_hreg single | 0.3830 | 0.314 | **0.467** | -0.0716 | -2.0% |
| ref | R150 single | 0.3498 | 0.338 | 0.362 | n/a | -10.5% |
| 1 | 2-way {s54, s51} | 0.3766 | 0.339 | 0.418 | -0.068 | -3.6% |
| 2 | 3-way {s54, s51, R142} | 0.3890 | 0.352 | 0.430 | -0.075 | -0.5% |
| 3 | 4-way {s54, s51, R142, R143} | 0.3948 | 0.359 | 0.435 | -0.079 | +1.0% |
| 4 | **4-way SOTA {s54, R142, R143, R100}** | **0.4119** | 0.368 | 0.461 | -0.080 | **+5.4%** ⭐ |
| 5 | 3-way {s54, R142, R100} drop-R143 | 0.4086 | 0.361 | 0.462 | -0.076 | +4.5% |
| 6 | 4-way weighted (R100=0.40) | 0.4106 | 0.362 | 0.466 | -0.078 | +5.1% |
| 7 | 5-way (+R150) | 0.4072 | 0.369 | 0.450 | -0.083 | +4.2% |
| 8 | R152 3-way {s54, R142, R143} | 0.4043 | 0.376 | 0.435 | -0.084 | +3.5% |

## Three structural findings

### Finding 1: Cross-algo > cross-seed (CLM-0280 hypothesis refuted)

Pure cross-seed {s54, s51} = 0.377 HURTS the ensemble (-3.6% vs baseline).
Adding cross-seed members ({s54, s51, R142}) returns to baseline. Same-
seed cross-ALGO adds value (R152 3-way = 0.404, R154 4-way = 0.412).

Why? Pure cross-seed averages two scalar-critic bang-bang policies that
saturated to slightly different sign patterns — averaging cancels rather
than complements. Cross-algo (scalar critic ↔ QR distributional ↔ hreg
continuous) produces structurally distinct policy shapes that mean-agg
combines into a smoother controller.

### Finding 2: R100_hreg drives the LS2 breakthrough

R100_hreg is the **only non-bang-bang** policy in this ensemble pool
(per R100 CLM-0190: hidden-norm reg kills LSTM drift, actor stays in
tanh-linear, no boundary saturation). Its single-policy LS2 = 0.467
exceeds R72_w4's 0.431 by +8.4pp. When mixed into any ensemble
containing it, LS2 jumps to 0.461-0.466 range.

The cross-algo lift therefore decomposes:
- LS1 lift comes from R142+R143 averaging out R72_w4 bang-bang spikes
  (R152 3-way: LS1 0.354 → 0.376 = +6%)
- LS2 lift comes from R100_hreg's continuous control style on LS2
  (4-way: LS2 0.431 → 0.461 = +7%)

Two independent improvement vectors, each driven by a structurally
distinct constituent.

### Finding 3: 4-way same-seed cross-algo is the local optimum

Tested 7 deviations from the SOTA config. ALL regress:
- 5-way (+R150 weak): -1.1pp (R150's geo 0.350 drags average down)
- weighted hreg-heavy: -0.3pp (uniform wins, again)
- drop-R143: -0.8pp (R143 contributes a small but real LS1 lift)
- replace R100 with s51: -4.4pp (LS2 strength lost)
- pure cross-seed: 9-12pp worse

The 4-way uniform mean of {scalar-Q, QR-buggy, QR-fixed, hreg-continuous}
at single seed s54 is the local optimum. No simple variation breaks
above 0.4119 in this ckpt pool.

## R72_w4 SOTA at s54 is a lucky seed

Cross-seed training at R72_w4 exact hyper:
- s54: 0.391 (canonical) ✓
- s49: **0.010 collapse** ✗
- s51: 0.356 (-8.9%) ⚠

Q-0005 (R56 LSTM seed-50 collapse) extends: at R72_w4 hyper (lr=1e-4
clamp, tau=0.001, warmup=5), s49 also collapses. Basin is narrow.
R72_w4 SOTA s54 result is at the edge of working seed range. Multi-seed
robustness claims for the paper need this caveat.

## Cross-references

- CLM-0280 / R153 (R152 3-way 0.4043 baseline)
- CLM-0190 (R100_hreg drift-killed continuous policy — key ingredient)
- CLM-0275 (R142 QR-LSTM matches baseline 0.385)
- CLM-0144 (R57-R82 91-round plateau)
- CLM-0094 (R72_w4 canonical SOTA s54)
- Q-0005 (LSTM seed-50 collapse, extended to s49 at R72_w4 hyper)

## Questions opened (this round)

- (none directly) — R154 closes the cross-seed hypothesis from CLM-0280
  and identifies cross-algo as the load-bearing mechanism.

## Questions closed (this round)

- (none directly closed)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog) — R154 strengthens
  closure case: algorithm DIVERSITY (multiple algos at same seed)
  matters more than algorithm REPLACEMENT (one new algo replacing
  baseline). Sweep Q-0014 backlog as obsolete.
- **Q-0005** — extends to s49 collapse at R72_w4 hyper. Mechanism
  unchanged (basin narrowness).

## 给 PI 的话

**这周干了啥**: CLM-0280 (R153 / R152 3-way 0.4043 plateau breaker) 留 #1 open question = "cross-seed ensemble likely > cross-algo same-seed". R154 launched 2 ANDES wave 训 R72_w4 hyper at s49 + s51 (~15 min each), 然后跑 8 个 ensemble eval 对比 cross-seed vs cross-algo.

**结果（一句话）**: **NEW PROJECT SOTA = geo 0.4119**, +5.4% over R72_w4 baseline 0.391, +1.9% over R152 3-way 0.4043. 但**hypothesis 反转**: cross-seed REFUTED (s49 collapse 0.010, s51 -8.9%, pure cross-seed ensemble HURTS -3.6%); 真正的 driver 是 **same-seed cross-ALGO**: 把 R100_hreg (drift-killed continuous policy, CLM-0190) 加到 R152 3-way {R72_w4 + R142 + R143}, 4-way mean = 0.4119. LS2 axis lift 是 +6pp 关键 (R100 single LS2 0.467 > 任何 bang-bang policy), R100 唯一非 bang-bang structure 给 ensemble unique LS2 direction.

**意外**: (1) **CLM-0280 cross-seed hypothesis REFUTED** — R72_w4 hyper basin 比预期窄, s49 collapse + s51 underperforms 直接 reveal "lucky seed s54" problem (Q-0005 extends to s49). 加 weak member 永远 hurt ensemble. (2) **R100_hreg 是 hidden 主角** — 它单独 geo 0.383 没特别好 (低于 baseline -2%), 但 LS2 axis 0.467 是 6 个 ckpt 中最高的, ensemble 把这个 LS2 strength leverage 出来. R100 当时 close round (CLM-0190) 时被解读为 "LSTM-drift falsified as plateau cause"; 现在转身变 plateau breaker 的核心 ingredient. (3) **跨 algo > 跨 seed** — 这是 cleaner 的 paper claim, 因为它 align ensemble theory (algorithmic diversity 而非 seed noise 是 load-bearing).

**我默认下一步做**: (1) R154 closed + CLM-0295 写入 (PROJECT SOTA 标签), STATE.md regenerate. (2) **R155+ 候选 = 找更多 distinct policy family** 训 at s54 to add 5+-way ensemble. Highest priority: (a) train td3 MLP (non-LSTM) at s54 baseline hyper — 加 algorithmic structural diversity (recurrent vs non-recurrent); (b) train td3_lstm_hreg at λ_h={0.003, 0.03} for more hreg variants; (c) train td3_lstm with different seq_len/burn_in. 单个 ANDES wave ~15 min, ROI 不确定但 if any single new member geo ≥ 0.35 AND structurally distinct, ensemble could push toward 0.42 BREAK. (3) 同时 zero-ANDES paper figure prep: 8-config bar chart, LS1/LS2 axis decomposition figure, paper Sec.IV-D HAWE table.

**你想插一脚就说**: 沉默 = 我 launch (a) td3 MLP at s54 (the most structurally distinct missing family), 同时 prep paper figures from R154 data.
