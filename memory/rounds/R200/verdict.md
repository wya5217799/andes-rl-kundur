# R200 verdict — lr=5e-5 collapses (compute-budget threshold confirmed)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — lower lr at 75ep equivalent to 50ep at default lr (collapse)
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at s54 with lr=5e-5 (half of R174's
clamped 1e-4). Result: geo=**0.0631**, **LS1=0.000**, LS2=0.399.
LS1=0 collapse pattern — same as R199's 50ep collapse.

## Compute-budget threshold

R199 (lr=1e-4, ep=50): LS1=0, geo=0.067
R200 (lr=5e-5, ep=75): LS1=0, geo=0.063

Effectively the same: at half-budget (~37 effective epochs at default
lr), the actor cannot learn LS1. Confirms a **minimum compute budget
threshold** ~50-60 effective epochs is needed for the LS1 axis to
become non-zero.

This is paper-relevant: **the bang-bang attractor (LS1=0) is the
default training landing zone**; only after sufficient training does
the actor find LS1 > 0 policies. The hreg λ=0.002 helps lock in
LS1>0 once found (R174 0.367) but doesn't accelerate finding it.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

R200 = lr=5e-5 at 75ep = geo 0.0631, LS1=0 collapse。跟 R199 (lr=1e-4,
ep=50) 一样 — compute budget 不够。

**Compute threshold finding**: 大约 ~50-60 effective epochs (lr=1e-4
等价) 是 LS1>0 的 minimum. 低于阈值, actor 卡在 bang-bang LS1=0 attractor.

R201 候选: tau=0.005 (default, R174 用 0.001) — 测 target-update speed
是否 load-bearing.

## Cross-references

- R174 (SOTA at lr=1e-4 ep=75)
- R199 (50ep collapse)
- R191 (200ep regression — over-training)
