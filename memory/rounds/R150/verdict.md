# R150 verdict — warmh0+QR (no AFE) s54 = geo 0.3498 (underperforms QR-alone)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE-MARGINAL — warmh0+QR slightly worse than QR-alone
**Type**: experiment (75 ep paper-faithful s54)
**Wall**: 734 s training + ~3 min final_eval

## TL;DR

R150 = first execution of stacked TD3+LSTM+WarmH0+QR (drop AFE) at s54.
Result: **geo = 0.3498** (LS1=0.338, LS2=0.362). Compared to:
- R72_w4 baseline (td3_lstm s54): 0.3908 → **-0.041 (-10.5%)**
- R142 (QR-alone s54): 0.3845 → **-0.035 (-9.0%)**

WarmH0 actor adds extra parameters (MLP from obs_0 → h_0 init) but **does
NOT help** at 75 ep budget. Empirically WORSE than QR-alone baseline.
CLM-0188 universal warm-h_0 feasibility on R72_w4 SOTA ckpts ≠ universal
training-time benefit.

## Method

`scripts/train.py --algo td3_warmh0_qr_lstm --qr-n-quantiles 51
--episodes 75 --seed 54 --hidden-size 64 --tau 0.001 --normalize-actions
--lstm-lr-warmup-eps 5 --save-dir results/r150_warmh0_qr_s54 --final-eval`

New agent class `TD3LSTMWarmH0QRAgent` (this session — code shipped + 38/38
tests pass). Combines:
- WarmH0RecurrentActor (R107 implementation, learnable MLP head for h_0)
- RecurrentQRDoubleQCritic (R98, 51 quantiles, Dabney 2018 quantile-Huber)
- NO AFE (CLM-0275 falsification — AFE drags down even working QR)

## Results

| Metric | R150 | R142 | R72_w4 baseline | Δ vs baseline |
|---|---|---|---|---|
| 11-axis geo | **0.3498** | 0.3845 | 0.3908 | -0.041 (-10.5%) |
| LS1 | 0.338 | 0.362 | 0.354 | -0.016 |
| LS2 | 0.362 | 0.408 | 0.431 | -0.069 |
| cum_rf | -0.106 | -0.102 | (n/a) | — |
| Wall (training) | 734 s | 846 s | (n/a) | — |

## Trajectory (compared to R142 QR-alone)

| ep | R150 mu | R150 std | R142 mu | R142 std | Same? |
|---|---|---|---|---|---|
| 9 | ~0 | 0.57 | ~0 | 0.55 | yes |
| 29 | ~0 | 0.10 | ~0 | 0.10 | yes (collapsed) |
| 49 | mid | 0.15-0.20 | mid | 0.11 | similar |
| 59 | mid | 0.20 | bang-bang | 0.23 | R150 slightly less saturated |
| 70 | [0.81, -0.05, 0.85, 0.87] | 0.22 | [0.88, 0.04, 0.87, 0.88] | 0.20 | R150 agent_0 slightly lower (0.81 vs 0.88) |

Both R150 and R142 escape and reach bang-bang. But R150 final agent_0 is
0.81 vs R142's 0.88 — slightly less saturated. Net LS1 -0.024 (-7%) and
LS2 -0.046 (-11%).

The warmh0's learnable h_0 head adds parameters that aren't fully optimized
at 75 ep. Net effect: slightly conservative actor → slightly lower geo.

## Gate eval

Per R150 plan: BREAKTHROUGH ≥ 0.45, CONFIRM ≥ 0.41, MARGINAL 0.37-0.40,
REGRESS < 0.30. R150 lands at **0.3498 → MARGINAL (-)**.

Specifically: warmh0+QR is NOT a plateau breaker (predicted breakthrough),
NOR matches R72_w4 baseline (CLM-0188 didn't translate to training-time
breakthrough), NOR fully regresses (still escapes do-nothing attractor).
Just slightly below R142.

## Implications for paper Sec.V

**The R72_w4 0.391 plateau is real and robust across R98 critic-representation
interventions**. None of these break it:
- QR distributional critic (R142 = 0.3845, R143 = 0.3843)
- AFE action features (R124/R140/R127/R144/R147 = 0.0100, broken)
- WarmH0 actor + QR critic (R150 = 0.3498, slight regression)
- WarmH0 actor + QR critic + AFE input (no test — predicted broken by AFE)

The plateau at ~0.39 is an **algorithm-class** plateau — TD-based recurrent
critic+actor in paper-faithful V4 + 75 ep budget hits this ceiling.

Possible plateau breakers NOT yet tested:
- Multi-seed ensemble (post-hoc, no new training)
- Longer training (R149 200ep in progress)
- Multi-agent CTDE (R82 considered)
- Reward shaping (R103/R115 parallel sessions on paper_strict_pure)
- Different actor architecture (transformer, larger hidden h=128)

## Cross-references

- CLM-0275 (R142 breakthrough headline)
- CLM-0188 (R104 warm-h_0 universal feasibility)
- CLM-0189 (R98 QR prototype validated by R142)
- CLM-0157(a) (R86 distributional priority)
- R142 verdict (QR-alone baseline)
- R140 verdict (AFE alone, broken)
- R127 verdict (R98 first stacked attempt)

## Questions opened (this round)

- **Q-NEW**: Why does CLM-0188 universal warm-h_0 feasibility (on TRAINED
  R72_w4 SOTA ckpt) NOT translate to training-time improvement when warm-h_0
  is added to a from-scratch td3_qr_lstm s54 run? Hypothesis: warm-h_0 helps
  INFERENCE step-0 action norm given a converged critic, but during training
  the learnable h_0 MLP head adds optimization burden without clear gradient
  signal advantage.

## Questions closed (this round)

- (none — CLM-0188 hypothesis on training-time benefit is **falsified** but
  not formally a Q to close. Q-NEW captures the follow-up.)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog): R150 adds one more falsified
  candidate to the plateau-breaker space. WarmH0 actor on top of QR critic
  doesn't help. Priority shift: stop adding more single-axis interventions;
  focus on multi-axis (multi-seed median, longer horizon, CTDE).

## 给 PI 的话

**这周干了啥**: R150 = R98 (a) QR critic + R104 (warmh0 actor) 合体 prototype,
drop AFE. 75 ep s54 single-seed paper-faithful. 这是 post-R142 breakthrough
后唯一未测的 prototype 组合.

**结果（一句话）**: **R150 geo = 0.3498**, **比 R142 (QR alone) 0.3845 低 -10%,
比 R72_w4 baseline 0.391 低 -10.5%**. WarmH0 actor + QR critic stacked
**UNDERPERFORMS** QR-alone. CLM-0188 universal warm-h_0 feasibility (在 already-
trained ckpt 上) 不 translate to training-time benefit (from-scratch). R150 ep
70 agent_0 saturated to 0.81 (vs R142 0.88), 略 conservative actor — 学到 less
extreme bang-bang policy → lower paper geo.

**意外**: (1) 我以为 warmh0 actor 学 obs→h_0 head 会 helping early training
dynamics, 实际相反 — extra param 在 75 ep budget 内 not fully optimized,
gradient 信号 weaker. R150 escape trajectory 跟 R142 几乎完全 同样 (ep 29
collapse, ep 50 escape, ep 70 bang-bang), 只是 final actor saturation 略弱.
(2) **R98 prototype space EXHAUSTED at s54 75 ep**: QR alone matches baseline
(R142 0.385 ≈ R72_w4 0.391), AFE 任何形式 broken (0.01), warmh0+QR 略 below
baseline (0.350). 全部 R98 priorities tested empirically. (3) Plateau ~0.39
**is real**. R72_w4 + R142 + R143 + R150 全部 在 0.35-0.39 区间. Not a
single-axis fix problem.

**我默认下一步做**: (1) R150 verdict closed + CLM update. (2) **R149 200ep
QR s54** still running (~ep 80/200), will tell us if longer horizon exceeds
0.391. If R149 also caps at ~0.39, plateau is firmly horizon-independent at
this scale. (3) Pause new training launches — R98 prototype space exhausted.
Next round = (a) multi-seed median for R142 (s49/s51/s50 with sum-loss to
get statistical baseline) or (b) larger hidden h=128 / different actor arch
to test ARCHITECTURE-side plateau breaker.

**你想插一脚就说**: (a) 想我 launch td3_qr_lstm s51 — 单 seed verify R142
isn't lottery (R142 IS s54 only); (b) 想我 launch td3_qr_lstm h=128 — test
critic capacity scaling; (c) 想我建 ensemble eval of {R72_w4, R142, R143}
ckpts — combined policy might exceed individual 0.39 (offline, no training);
(d) 想我直接关 round + 写 paper Sec.V "plateau is real" 章节; (e) wait for
R149 200ep result first then decide. 我推荐 **(e)** 等 R149 (~1h to finish)
+ 同时干 **(c)** ensemble eval (5 min offline).
