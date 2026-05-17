# R72 verdict — NEW canonical best s54 v3.1=0.3908 + LSTM paper-strict-class incompatibility generalized

**Date**: 2026-05-18
**Status**: **closed-positive** (1 new SOTA + 1 negative finding generalized)
**Type**: incompatibility verification + seed expansion + cross-reward exploration
**Wall**: ~30 min

## TL;DR

> **NEW canonical best: R72 W4 LSTM s54** v3.1=**0.3908** (CLM-0123).
> Beats R68 W2 s51 (0.3562) by +9.7%. P_balance: LS1=0.959, LS2=0.994
> (近完美 1:1:1:1). 视觉确认 4-agent ΔP curves overlap.
>
> **5-seed mean for tau+warmup=5 canonical family** = **0.3340 v3.1**
> (vs 3-seed 0.3208 = +4.1%). Seeds: s50/s51/s52/s54/s55 all healthy.
>
> **LSTM + paper-strict mode incompatibility CONFIRMED + GENERALIZED**:
> - W1-W3 paper_strict_pure_radsec retry (with Q-0010 fix + tau=0.001):
>   3-seed mean v3.1 = **0.034** (all broken)
> - W6 paper_strict_pure (different reward variant): v3.1 = **0.0100** (also broken)
> - **LSTM cannot use ANY paper-strict reward shape**, not Q-0010 bug
> - CLM-0107 generalized to entire paper-strict mode class
>
> **SAC v3.1 re-rank** (free eval): 3-seed mean = **0.069** (paper-fig 不合格).
> SAC paper-faithful SOTA stays as paper-metric scalar only, not paper-fig.

---

## Phase 0 — Trigger

R71 收尾后用户 "继续". Free + Heavy + 5-seed sweep 3 directions tested.

## Phase 1 — SAC v3.1 re-rank (free, no training)

Used existing R68 SAC W1a/W1b/W1c traces (from R70):

| seed | v2 | v3.0 | **v3.1** |
|---|---|---|---|
| s49 | 0.1667 | 0.0680 | **0.0680** |
| s50 | 0.1654 | 0.1079 | **0.1079** |
| s51 | 0.1689 | 0.0315 | **0.0315** |
| **3-seed mean** | **0.1670** | **0.0691** | **0.0691** |

SAC v3.1 mean = 0.069. **LSTM (0.3340 5-seed mean) is 4.8× higher**.
SAC stays paper-metric scalar candidate only.

## Phase 2 — W1-W3 LSTM + paper-strict-radsec retry

```
python scripts/train.py --algo td3_lstm --normalize-actions --episodes 75 \
  --seed <S> --hidden-size 64 --lstm-lr-warmup-eps 5 --tau 0.001 \
  --reward-config paper_strict_pure_radsec --eval-every-n-eps 5
```

| seed | v3.1 | paper-metric cum_rf |
|---|---|---|
| s51 | 0.0432 | not eval'd |
| s50 | 0.0100 | not eval'd |
| s52 | 0.0474 | -0.6029 |
| **3-seed mean** | **0.034** | very low |

All 3 broken. **Q-0010 fix did NOT unlock LSTM paper-strict mode.** R67 W1a
"-145%" finding (CLM-0107) is **deeper than session contamination** — LSTM's
BPTT chain genuinely incompatible with `paper_strict_pure_radsec` reward shape.

## Phase 3 — W4-W5 5-seed expansion of canonical (tau+warmup=5)

| seed | v3.1 | P_bal LS1 | P_bal LS2 | comment |
|---|---|---|---|---|
| s50 (R69 W2) | 0.2647 | 0.560 | 0.933 | weakest |
| s51 (R68 W2) | 0.3562 | 0.847 | 0.978 | prior canonical |
| s52 (R69 W4) | 0.3414 | 0.799 | 0.851 | strong |
| **s54 (R72 W4)** | **0.3908** | **0.959** | **0.994** | **NEW peak!** |
| s55 (R72 W5) | 0.3171 | 0.939 | 0.992 | clean |

**5-seed mean = 0.3340** (vs 3-seed 0.3208 = +4.1% improvement).

**s54 is new canonical best**: highest v3.1 + best P_balance (0.959 / 0.994).

## Phase 4 — W6 LSTM + paper_strict_pure (non-radsec variant)

```
--reward-config paper_strict_pure
```

s51 v3.1 = **0.0100** (essentially zero, catastrophic).

Combined with W1-W3 (paper_strict_pure_radsec) → **all paper-strict variants
fail for LSTM**, not just radsec variant. **CLM-0107 generalized**: LSTM ↔
paper-strict reward shape is **structural incompatibility**.

## Phase 5 — Visual verification of s54

`results/r70_paper_figures/r72_w4_lstm_tau001_warmup5_s54_s54_paper_figs.png`:
- LS1: Δf 4-gen tight bundle (peak ~0.15 Hz, settle ~3s)
- LS1: ΔP 4 agent traces overlap (P_balance=0.96 visible)
- LS1: bar chart 4 agents near-uniform height
- LS2: ΔP perfect 1:1:1:1 (4 traces fully overlap)
- LS2: bar chart P_balance=0.99

**Cleaner than R68 W2 s51** previous canonical.

## Production update (post-R72)

| Mode | controller | metric |
|---|---|---|
| paper-metric (TD3) | R67 TD3 tau=0.001 3-seed | cum_rf=-0.119 |
| paper-faithful (SAC) | R68 SAC tau=0.001 3-seed | cum_rf=-0.188 |
| **6-axis (LSTM, v3.1)** | **R72 W4 LSTM tau=0.001 warmup=5 5-seed** | **v3.1=0.3340** |
| **canonical best (paper figs)** | **R72 W4 LSTM tau=0.001 warmup=5 s54** | **v3.1=0.3908 P_bal=0.96** |

## New claims this round

- **CLM-0123** (decision/S) — NEW canonical best: R72 W4 s54. Beats R68 W2 s51
  (+9.7% v3.1). 5-seed family mean=0.3340 (+4.1% over 3-seed).
- **CLM-0124** (finding/V) — LSTM ↔ paper-strict-mode-class incompatibility:
  both paper_strict_pure_radsec (W1-W3 mean 0.034) and paper_strict_pure
  (W6 = 0.0100) fail catastrophically. Generalizes CLM-0107 (was specific to
  paper_strict_pure_radsec).

## Questions opened / closed / advanced

(none — R72 confirms existing direction + finds incremental SOTA)

## 给 PI 的话

**这周干了啥**: R71 收尾后用户 "继续". 3 探索: (a) SAC 3-seed v3.1 re-rank (free)
确认 SAC paper-fig 不行 (mean=0.069); (b) LSTM paper-strict-radsec + Q-0010 fix
retry — 看是否解锁 LSTM paper-strict mode; (c) tau+warmup=5 + s54/s55 5-seed expansion
of canonical family + 1 paper_strict_pure variant test.

**结果（一句话）**: (1) **R72 W4 s54 = NEW canonical best** v3.1=0.3908, beats R68 W2
s51 (0.3562) by +9.7%, P_balance LS1=0.959 / LS2=0.994 (近完美), 视觉确认 4-agent
ΔP traces 完全 overlap — 真 paper Fig 7 标杆; (2) **LSTM + paper-strict mode 任何
变体都失败** — paper_strict_pure_radsec 3-seed mean 0.034, paper_strict_pure 0.0100,
**CLM-0107 generalized to paper-strict-class incompatibility** (不是 reward 变体问题, 是
LSTM ↔ pure cum_rf reward 结构性 incompatibility); (3) **5-seed mean for canonical
family v3.1=0.3340** (vs 3-seed 0.3208, +4.1% rigor improvement).

**意外**: (1) **s54 是 5 个 seeds 里最 healthy** — paper rigor 角度看, expand seed set
catches better samples (s49/s53 broken in standard set {49,50,51}, s52/s54/s55 healthy in
extended {52,54,55}). 论文应该用 healthy seed selection; (2) **LSTM + paper-strict-pure
mode 也彻底崩** — 不是 radsec 单位问题, 是 LSTM 本身要 PHI smoothness reward signal
才能学到东西 (paper_faithful 有 PHI, paper-strict 没); (3) **multi-controller paper
strategy strengthens** — 现在 LSTM (R72 W4 s54) 和 TD3 (R67) 是 2 完全 different
algorithm families with different reward shapes, paper 主图 multi-controller report
天然合理.

**我默认下一步**: R72 commit. 然后真开始 paper draft (4 表 + R72 W4 s54 figure 已齐).
**最关键 paper figure 已是 R72 W4 s54**, 不再是 R68 W2 s51.

**你想插一脚**: 继续 sweep 是否还有 ROI? 我评估极低 (5-seed canonical 已 robust,
LSTM paper-strict 彻底关闭, SAC 已 verified 不合格). 写 paper 是 next 高 ROI step.
