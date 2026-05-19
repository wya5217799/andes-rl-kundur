# R226 verdict — 1.75× inertia robust (-4.0%); cliff is in (1.75×, 2×]

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE — narrows cliff to a 0.25× wide window
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --vsg-m0 350 (1.75×
trained). Result: geo=**0.3984**, LS1=0.351, LS2=0.452, cum_rf=-0.0607.
**vs R201: -4.0% only**. Still robust at 1.75×; cliff is in
**(1.75×, 2×]** — very narrow window.

## Complete inertia curve

| ratio | vsg_m0 | geo | Δ |
|-------|--------|-----|------|
| 0.25× | 50 | 0.3832 | -7.7% |
| 0.5× | 100 | 0.4028 | -3.0% |
| 1× trained | 200 | **0.4152** | (ref) |
| 1.5× | 300 | 0.4031 | -2.9% |
| **1.75×** | **350** | **0.3984** | **-4.0%** |
| 2× | 400 | 0.2753 | **-33.7%** ⬇️ |

The breakdown cliff is **between 1.75× and 2× only** — an extraordinarily
sharp transition. Likely a resonance / control-timing instability
threshold at ~H₀=200s.

## Paper Sec.IV-D contribution 6 (final version)

> "The SOTA controller is robust within a [0.25×, 1.75×] inertia window
> of trained inertia (max degradation -7.7%) but exhibits sharp cliff
> breakdown above 1.75× (-33.7% at 2×). The breakdown is sudden, not
> gradual. This identifies an operational guideline: deployment inertia
> should be within [0.25, 1.75]× of training inertia, with asymmetric
> safer margin toward lower inertia."

## R227 candidate

**Critical test**: retrain SOTA hyper AT vsg_m0=400 (train-on-deploy).
If retrained model gives geo ≥ 0.40, the env fundamentally supports
high-inertia control; R224's collapse was pure deployment-time
mismatch. If retraining also collapses, high inertia is intrinsically
harder for hreg-SOTA hyper.

This tests train-time vs eval-time inertia separately — important
for paper interpretation.

## Questions opened (this round)

(implicitly: "Can SOTA hyper train at vsg_m0=400?" — R227 test)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — robustness curve characterized)

## 给 PI 的话

R226 = vsg_m0=350 (1.75×) = **0.3984, -4.0%**. Cliff **极 sharp** —
在 (1.75×, 2×] 之间. 0.25× 区间内从 -4% 暴跌到 -34%.

**Safe deployment window**: [0.25×, 1.75×] trained inertia.

R227 critical test = **retrain** SOTA hyper at vsg_m0=400. 看 env 是否
支持 high-inertia control (deployment mismatch only) 还是 high inertia
intrinsically harder for hreg-SOTA.

## Cross-references

- R201/R222/R223/R224/R225 (inertia curve)
