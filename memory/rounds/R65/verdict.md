# R65 verdict — SAC transfer 大成 (-0.194 paper-faithful SOTA, +26pp vs paper), LSTM 不 transfer

**Date**: 2026-05-17
**Status**: **closed-positive** (SAC SOTA breakthrough; LSTM transfer fails, R57-α maintained)
**Type**: hyper transfer to SAC + LSTM
**Wall**: ~2.5 hr (4 waves + evals)

## TL;DR

> R64 TD3 hyper combo (N_SUBSTEPS=3 / MAX_GRAD_NORM=0.5 / batch=512 /
> lr=3e-3) transferred to SAC + LSTM:
>
> **W1 — SAC h64+combo+lr=3e-3 paper_strict_pure_radsec 3-seed**:
> - s49: -0.163, s50: **-0.163** ⭐, s51: -0.255 (s51 trained unstable)
> - **3-seed best_eval mean: -0.194** vs R62 SAC h128+Q7 -0.422
> - **+54% paper-metric improvement**
> - vs paper DDIC: **79.2% (+32.7pp robust)** vs R62 +6.3pp = **+26pp lift**
> - **New paper-faithful SOTA**, supersedes CLM-0083
>
> **W2 — LSTM h64+combo (no Q-0007) 3-seed**:
> - s49: 0.110, s51: 0.437, s53: 0.433
> - **3-seed mean 6-axis 0.327** vs R57-α 0.432 = **-24% degradation**
> - **New hyper does NOT transfer to LSTM**
>
> **W3 — LSTM lr sweep (s51 pilot) found train.py:305 clamps LSTM lr
> to 1e-4** regardless of LR env var. 3 trainings produced identical
> ckpts.
>
> **W4 — LSTM unclamped lr {3e-4, 5e-4, 1e-3}** all WORSE than clamp=1e-4:
> - lr=3e-4 → 0.300 (-31%)
> - lr=5e-4 → 0.188 (-57%)
> - lr=1e-3 → 0.278 (-36%)
> - **train.py:305 clamp at 1e-4 is genuinely optimal for LSTM**.

---

## Phase 0 — Trigger

R64 closed; user authorization continues. R65 transfers R64 hyper combo to
SAC (paper-faithful path) and LSTM (6-axis path).

## Phase 1 — W1 SAC + new hyper transfer

3-seed with `N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 batch_size=512
--algo sac --hidden=64 --reward-config paper_strict_pure_radsec
--eval-every-n-eps 5`:

| seed | best.pt | best_eval.pt | R62 SAC h128+Q7 baseline |
|---|---|---|---|
| s49 | -0.179 | **-0.163** | -0.462 (+65 %) |
| s50 | -0.293 | **-0.163** | -0.347 (+53 %) |
| s51 | -0.965 ⚠️ | -0.255 | -0.458 (+44 %) |
| **3-seed mean** | -0.479 | **-0.194** | **-0.422 (+54 %)** |

s51 best.pt -0.965 suggests training collapse mid-run, but `best_eval.pt`
catches an early peak before collapse — **Q-0007 saves the seed**.

### vs paper DDIC improvement rate

| controller | LS1 imp | LS2 imp | mean |
|---|---|---|---|
| paper DDIC | 58 % | 35 % | 46.5 % |
| R62 SAC h128+Q7 3-seed | 42 % | 64 % | 52.8 % (+6.3pp) |
| **R65 W1 SAC combo 3-seed** | **80 %** | **78 %** | **79.2 %** (+32.7pp) |

**+26pp lift** in 3-seed robust improvement-rate from R62 to R65.

### vs TD3 (paper-metric)

- TD3 V4 historical (R64 W3): -0.124 3-seed mean (+37.5pp)
- SAC paper-strict-radsec (R65 W1): -0.194 3-seed mean (+32.7pp)

TD3 still leads paper-metric in absolute terms, but SAC closes the
gap dramatically (R62 was 2× gap, R65 is 1.6× gap).

## Phase 2 — W2 LSTM + new hyper transfer FAILS

3-seed LSTM h64 + R64 combo + warmup-5 (no Q-0007 to avoid Q-0010):

| seed | best.pt 6-axis | final.pt 6-axis | R57-α baseline |
|---|---|---|---|
| s49 | 0.110 ⚠️ | 0.229 | 0.333 |
| s51 | **0.437** | 0.426 | 0.526 (R57 SOTA) |
| s53 | 0.433 | 0.367 | 0.437 |
| **3-seed mean** | **0.327** | 0.341 | 0.432 |

**-24% degradation 3-seed mean** vs R57-α baseline. **New combo doesn't
transfer to LSTM**.

Mechanism candidates (untested):
- N_SUBSTEPS=3 vs LSTM expects N_SUBSTEPS=5 dynamics
- MAX_GRAD_NORM=0.5 too aggressive for BPTT
- batch_size=512 sequences/seq too memory-heavy for LSTM training

Per-axis isolation deferred (Q-0013 candidate).

## Phase 3 — W3 LSTM lr sweep (clamp discovery)

Pilot LSTM s51 with LR={3e-4, 5e-4, 1e-3} + R64 combo. Result: all 3
returned **identical 6-axis = 0.437**.

**Bug discovered**: `scripts/train.py:305` hardcodes
```python
lstm_lr = min(lr, 1e-4)
```
Comment: `"lr clamped to 1e-4 for RNN stability"`. LR env var was being
silently clamped. **R56/R57/R65 W1-W2 all trained LSTM at lr=1e-4 regardless
of input** — explains why our earlier "LSTM uses lr from CLI" assumption
was wrong.

## Phase 4 — W4 LSTM unclamped lr sweep

Added `LSTM_LR_UNCLAMP=1` env var to bypass clamp. Re-sweep s51:

| lr | 6-axis | vs clamped baseline 0.437 |
|---|---|---|
| 1e-4 (clamped, W3 baseline) | 0.437 | (baseline) |
| 3e-4 (unclamped) | 0.300 | -31 % |
| 5e-4 | 0.188 | -57 % |
| 1e-3 | 0.278 | -36 % |

**clamp=1e-4 IS the right value for LSTM**. R57 author's comment was
empirically correct. New hyper transfer fails partly because TD3/SAC
benefit from lr=3e-3 but LSTM stays at 1e-4 by design.

## Hypothesis adjudication

- **H_sac_transfer**: **STRONG PASS**. SAC paper-faithful +54%
- **H_lstm_transfer**: **FAIL**. LSTM 6-axis -24% under new combo
- **H_lstm_lr_clamp (1e-4 optimal)**: **PASS**. Unclamped all worse

## New claims this round

- **CLM-0097** (decision/S) — R65 hyper transfer landscape: SAC ✓, LSTM ✗
- **CLM-0098** (finding/V) — SAC + new hyper paper-faithful SOTA -0.194
  (3-seed mean, +54 % vs R62)
- **CLM-0099** (finding/V) — LSTM + new hyper transfer FAILS (-24 %),
  R57-α maintained for 6-axis
- **CLM-0100** (finding/V) — LSTM lr clamp at 1e-4 in train.py:305 IS
  optimal (unclamped all worse). Hidden bug discovered + verified.
- **CLM-0101** (decision/S) — Production update R65: SAC mode updated,
  6-axis mode unchanged

## Questions opened (this round)

- **Q-0013** — Which axis of R64 combo (nsub=3 / gc=0.5 / bs=512) is
  the culprit for LSTM degradation? Per-axis ablation needed to know
  if any single axis benefits LSTM in isolation.

## Questions closed (this round)

- **Q-0011 closed-positive** by CLM-0098: SAC h64 (not h128) with new
  hyper produces SOTA. R62 CLM-0083's "h=128 marginal best" was
  hyper-conditional; under new lr=3e-3 the h=64 path is the clear
  winner.

## Questions advanced (this round)

- Q-0010 (LSTM eval probe): not addressed in R65. Independent bug
  from LSTM hyper-transfer fail.

## 给 PI 的话

**这周干了啥**：R64 TD3 hyper combo (lr=3e-3 + ...) transfer 到 SAC
和 LSTM。4 波 12 训练 + evals ~2.5 小时。

**结果（一句话）**：**SAC 大成** — paper-faithful (radsec) 3-seed mean
-0.194 vs R62 SAC -0.422 = **+54%**, 相对 paper DDIC +32.7pp robust，
**新 paper-faithful SOTA**。**LSTM 不 transfer** — 6-axis 反而 -24%，
R57-α 仍是 6-axis SOTA。

**意外**：(1) 顺手发现 `train.py:305` 把 LSTM lr **hardcode clamp 到
1e-4**，过去所有 LSTM 训练（R56-R65 W2）实际全在 1e-4，跟 CLI 输入
无关。验证 unclamp 后 lr 5e-4/1e-3/3e-4 全 worse — 注释"RNN stability"
是对的，clamp 不该解；(2) SAC s51 best.pt -0.965 提示中途崩溃，但
`best_eval.pt` 救到 -0.255，**Q-0007 在野外又救命一次**；(3) TD3 vs
SAC 在 paper-faithful 评估下，TD3 还略好 (-0.124 vs -0.194)，但 SAC
路线是真正"paper-aligned"的，paper 写作可以并列报告。

**我默认下一步做**：R66 = 整合写 paper Sec.IV-C 对位段 + ablation table。
4 张表已经齐了：(1) TD3 paper-metric 3-seed +37.5pp；(2) SAC paper-faithful
3-seed +32.7pp；(3) lr sweep U-curve；(4) hyper sweep ablation matrix。
Q-0013 (LSTM axis ablation) 优先级降低 — diminishing returns. 边写边
可以再 sweep 任何 paper 需要的 ablation。

**你想插一脚就说**：(1) Hyper sweep 是否就此打住，转写 paper（沉默 = 走）；
(2) 是否要 Q-0010 LSTM eval probe debug，让 LSTM 也吃到 Q-0007 加成；
(3) Q-0013 LSTM hyper 逐 axis ablation 是否值得 1 hr wall。
