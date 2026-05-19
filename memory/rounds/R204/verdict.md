# R204 verdict — s50 REGRESSES at tau=0.005 (-1.0%); tau lift not universal

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for tau-universality claim; tau is within noise
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at s50 with tau=0.005. Result:
geo=**0.3481**, LS1=0.312, LS2=0.388. Compared to R185 (s50,
tau=0.001) = 0.3515: **-1.0% REGRESSION**, not the expected +0.3%
lift.

## Updated cross-seed table at new hyper

| seed | tau=0.001 | tau=0.005 | Δ |
|------|-----------|-----------|------|
| 50 | 0.3515 (R185) | **0.3481 (R204)** | **-1.0%** |
| 51 | 0.3888 (R181) | 0.3901 (R203) | +0.3% |
| 54 | 0.4139 (R174) | 0.4152 (R201) | +0.3% |
| **mean** | **0.3847** | **0.3845** | **-0.05%** |
| **stdev** | **0.031** | **0.034** | (no change) |

**Cross-seed mean is essentially identical** at tau=0.001 vs tau=0.005.
The per-seed +0.3% / -1.0% spread is seed-specific noise, not a
hyperparameter improvement.

## Honest paper claim

R201 was NOT a true SOTA improvement — it was within seed noise. The
correct paper statement:

> "Single-policy SOTA at (s54, λ=0.002, hreg, 75ep) is robust to tau ∈
> {0.001, 0.005}: geo 0.4139–0.4152, within evaluation noise (CV
> ~2.5%, eval std ≈ 0.010)."

R201 still has the highest recorded point estimate, but it's not
statistically separable from R174.

## Cross-seed mean (paper number)

3-seed viable mean at any tau ≈ **0.385** — defensible robust number.
Single-(seed=54, offset=0) max ≈ 0.415 — single-config peak.

## What's productive now

Pure single-axis search is exhausted. The remaining levers are
ensemble-side (test diversity combinations) or paper-side (write up
findings). For R205: try a cross-seed ensemble at the new hyper —
if seeds give complementary policies, ensemble could exceed single
SOTA.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

R204 s50 at tau=0.005 = **0.3481**, 比 R185 (s50 tau=0.001) 0.3515 跌
**-1.0%**. tau lift 不是 seed-universal.

Cross-seed mean 在 tau=0.001 跟 tau=0.005 几乎一样 (0.3847 vs 0.3845).
**R201 的 "+0.3% SOTA" 其实在 noise band 内**, 不是真 hyperparameter
improvement.

**诚实 paper claim**: "tau ∈ {0.001, 0.005} 给等价 SOTA, 0.4139-0.4152".
R174 跟 R201 statistical 等价.

R205 候选: cross-seed ensemble {R201 s54, R203 s51, R204 s50} all at
tau=0.005 — 看 seed diversity 给不给 ensemble lift. R154 用 R72_w4
hyper 时 cross-seed 不 work (s49 collapse 污染), 但 R201 hyper at
s50/51/54 都 viable, 可能 cross-seed diversity 给 lift.

## Cross-references

- R185 (s50 tau=0.001 baseline)
- R203 / R201 (other seeds at tau=0.005)
- CLM-0325 (cross-seed ensemble theory, R154 negative finding)
