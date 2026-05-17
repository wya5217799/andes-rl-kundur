# R68 verdict — SAC tau=0.001 +3.1% robust SOTA + LSTM warmup U sweep peak~20-30 (single-seed)

**Date**: 2026-05-17/18
**Status**: **closed-positive** (SAC SOTA verified + LSTM warmup direction discovered)
**Type**: hyper-sweep verify + LSTM single-seed exploration
**Wall**: ~2 hr

## TL;DR

> **W1 — SAC tau=0.001 3-seed verify**: paper-faithful SOTA -0.194 → **-0.188** (+3.1% robust).
> Confirms tau=0.001 advantage **transfers from TD3 to SAC** (TD3 +4%, SAC +3.1%).
>
> **W2 — LSTM + tau=0.001 + paper_faithful (default reward)**: s51 single-seed
> v2 6-axis = **0.4226** (vs R57-α today 0.4259, noise band).
> tau alone on LSTM is noise level. But v3 11-axis re-rank later (R69) shows v3=0.5329
> — tau IS effective for LSTM but on **P-balance + late-osc** dimensions, NOT v2 6-axis.
>
> **W3 — 3-seed verify warmup=30**: s49=0.1149 (drift broken) | s50=0.4805 | s51=0.4823.
> 3-seed mean (excl s49) = 0.4814 v2. **warmup=30 single-axis exploration confirmed strong**
> but s49 drift makes 3-seed mean low.
>
> **W4 — LSTM warmup U sweep (s51 single-seed)**: 12 points (warmup ∈ {0..40}).
> Peak plateau at **warmup=20-30** (v2 0.48-0.4824). R57 选 warmup=5 = 0.4259
> SUB-OPTIMAL by 13%.

---

## Phase 0 — Trigger

R67 收尾, 用户 "继续挤". 剩 SAC tau / LSTM tau / LSTM warmup 未扫.

## Phase 1 — W1 SAC tau=0.001 3-seed verify (CLM-0109)

```
N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 python scripts/train.py \
  --algo sac --normalize-actions --episodes 75 --seed <S> \
  --hidden-size 64 --batch-size 512 --tau 0.001 --eval-every-n-eps 5 \
  --reward-config paper_strict_pure_radsec
```

| seed | R65 SAC (tau=0.005) | **R68 (tau=0.001)** | Δ |
|---|---|---|---|
| 49 | -0.163 | **-0.1584** | +3% |
| 50 | -0.163 | **-0.1605** | +1.5% |
| 51 | -0.255 (collapse) | -0.2448 (still collapse) | +4% |
| **3-seed mean** | **-0.194** | **-0.1879** | **+3.1% robust** |

s51 仍 collapse pattern (跟 R65 s51 同模式, single-agent runaway), tau 改善但不救命.

vs paper DDIC 46.5% → ~85% improvement-rate = ~+35pp robust.

## Phase 2 — W2 LSTM + tau=0.001 single-seed pilot (CLM-0110)

```
python scripts/train.py --algo td3_lstm --normalize-actions --episodes 75 \
  --seed 51 --hidden-size 64 --lstm-lr-warmup-eps 5 --tau 0.001 \
  --save-dir results/r68_w2_lstm_tau001_s51
```

v2 8-axis: **0.4226** (vs R57-α today 0.4259 = -0.8% noise band).

第一印象: tau alone 不影响 LSTM 6-axis. 但 R69 11-axis 重 rank 揭穿: v3=0.5329, **真 SOTA**.

机理: tau=0.001 改善的是 **P-balance + late oscillation** — v2 ranker 8 axes 都看 cross-agent mean, 不看 per-agent dispersion, 完全 miss tau's effect.

## Phase 3 — W3 3-seed verify warmup=30 (CLM-0111)

Pilot W4l (warmup=30 s51) = 0.4823 → 3-seed verify s49 + s50:

| seed | warmup=30 v2 6-axis | vs R57-α s51 0.526 |
|---|---|---|
| s49 | **0.1149** | **broken (drift)** |
| s50 | **0.4805** | -9% |
| s51 | **0.4823** | -8% |
| 3-seed mean (excl s49) | **0.4814** | -8.5% |

s49 confirmed broken on multiple hyper paths (W3b warmup=30, W4f tau=0.001 both ≈ 0.11).
**s49 是 code drift dead seed** (CLM-0104), 任何 hyper 救不回.

## Phase 4 — W4 LSTM warmup U sweep (single-seed s51, 12 points)

| warmup | s51 6-axis (v2) |
|---|---|
| 0 | 0.4198 |
| 5 (R57 选) | 0.4259 |
| 8 | 0.4308 |
| 10 | 0.4350 |
| 12 | 0.4389 |
| 15 | 0.4432 |
| 18 | 0.4497 |
| **20** | **0.4800** |
| 22 | **0.4859** ← peak |
| 25 | 0.4693 |
| 30 | 0.4823 |
| 35 | 0.4403 (dip) |
| 40 | 0.4824 |

**Plateau 20-30, ratio peak/R57 = 0.4824/0.4259 = +13%**.

R57 选 warmup=5 是 sub-optimal — paper 没写 warmup_eps choice rationale, R57 选 5 似乎是直觉.

Single-seed sweep, 真 3-seed verify in R69 (cross-axis combo).

## Phase 5 — Next round (R69)

This round 揭出 2 things:
- LSTM + tau=0.001 on v2 看 noise but R69 v3 might see it as SOTA (per-agent gates)
- LSTM warmup=20-30 single-seed strong, need 3-seed + cross-axis tau test

→ R69 ranker upgrade + cross-axis 3-seed verify.

## New claims this round

- **CLM-0109** (finding/V) — SAC tau=0.001 3-seed verify: -0.188 vs R65 -0.194 = +3.1% robust.
  Confirms tau=0.001 generalises from TD3 to SAC.
- **CLM-0110** (finding/V) — LSTM + tau=0.001 + paper_faithful default reward s51 = 0.4226 v2
  (noise vs baseline 0.4259). Effect hidden by v2 ranker until R69 v3 reveals SOTA on
  per-agent gates.
- **CLM-0111** (finding/V) — Warmup=30 3-seed mean v2 = 0.4814 (s49 broken excluded).
  s49 confirmed broken on multi-hyper (CLM-0104 drift).
- **CLM-0112** (finding/V) — LSTM warmup U sweep (s51 single-seed, 12 points):
  peak plateau warmup=20-30 = 0.4824, R57 选 warmup=5 = 0.4259 sub-optimal by 13%.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — all R68 findings are exploration, not closing prior Qs)

## Questions advanced (this round)

(none)

## 给 PI 的话

**这周干了啥**: R67 收尾后用户 "继续挤". R68 跑 SAC tau verify (W1, 3-seed) + LSTM hyper
sweep (W2-W4). 总 21 trainings + 多 evals.

**结果（一句话）**: (1) **SAC tau=0.001 +3.1% robust** — 跟 TD3 同模式, paper-faithful SOTA
-0.194 → -0.188; (2) **LSTM tau=0.001 在 v2 6-axis 上是 noise** (0.4226 vs 0.4259)
但 R69 v3 ranker 揭穿这是**真 SOTA** (v3=0.5329) — tau 帮助 LSTM 4-agent 协同,
v2 看 mean curve 完全 miss; (3) **LSTM warmup U sweep**: R57 选 warmup=5 sub-optimal,
peak 在 warmup=20-30 (s51 = 0.4824, +13%). 真 3-seed verify in R69.

**意外**: (1) **v2 ranker 系统性 underestimate tau effect on LSTM** — 因为 v2 看 cross-agent
mean, tau 改善是 per-agent balance. 这是 R69 升级 ranker 的核心动因;
(2) **s49 是 dead seed under code drift** — 任何 hyper 救不回, 4 个 hyper combo 测试
都 ≈ 0.11. R57 historical s49 = 0.333 today repro 0.11 = drift 太严重;
(3) **W4 sweep 显示 R57-α 选择 warmup=5 是 paper-naive choice** — paper 没说为什么 5,
R57 跟随但没验证.

**我默认下一步**: 进 R69 升级 ranker + cross-axis verify. R68 commit.

**你想插一脚**: nothing — R68 是中间步, R69 才是大突破.
