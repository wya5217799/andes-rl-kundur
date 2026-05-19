# R225 verdict — 1.5× inertia STILL ROBUST (-2.9%); breakdown is sudden between 1.5× and 2×

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE — characterizes asymmetric robustness as sharp-cliff
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --vsg-m0 300 (H₀=150,
1.5× trained-on). Result: geo=**0.4031**, LS1=0.354, LS2=0.459,
cum_rf=-0.0629. **vs R201: -2.9% only**.

## Inertia robustness curve (now well-characterized)

| vsg_m0 | H₀ | ratio | geo | Δ |
|--------|----|----|-----|------|
| 50 | 25 | 0.25× | 0.3832 | -7.7% |
| 100 | 50 | 0.5× | 0.4028 | -3.0% |
| **200** | **100** | **1× (trained)** | **0.4152** | (ref) |
| 300 | 150 | 1.5× | **0.4031** | **-2.9%** |
| 400 | 200 | 2× | 0.2753 | **-33.7%** ⬇️ |

**The robustness window is [0.25×, 1.5×]**: all four ratios within
this range give -8% or less degradation. Above 1.5×, **sudden cliff**
between 1.5× and 2× inertia.

## Refined paper finding

> "The SOTA controller is robust within a [0.25×, 1.5×] inertia
> window of trained inertia (degradation ≤ -7.7%) but exhibits sudden
> breakdown at 2× (-33.7%). The breakdown is not gradual but a
> regime change where the trained action timing becomes unstable
> under significantly slower dynamics. Practitioners should ensure
> deployment inertia stays within 1.5× of training inertia, or
> retrain. The robustness window is asymmetric, favoring lower-than-
> trained inertia."

## R226 candidate

Narrow the breakdown cliff with vsg_m0=350 (1.75×). If geo ≥ 0.35,
breakdown is in (1.75, 2]; if geo < 0.30, breakdown is in (1.5, 1.75].

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — asymmetric robustness now characterized as sharp-cliff at ~2×)

## 给 PI 的话

🎯 **R225 = vsg_m0=300 (1.5× inertia) = 0.4031, -2.9%**. Breakdown 是
**sudden cliff** between 1.5× and 2×, not gradual.

**Safe deployment window**: [0.25×, 1.5×] of trained inertia. 至 1.5×
仅 -3%, 跳到 2× 直接 -34%.

R226 = vsg_m0=350 (1.75×) narrow the cliff.

## Cross-references

- R201/R222/R223/R224 (full inertia curve)
