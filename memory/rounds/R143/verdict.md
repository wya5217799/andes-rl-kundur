# R143 verdict — td3_qr_lstm s54 FIXED-loss training, results in CLM-0275

**Date**: 2026-05-19
**Status**: COMPLETED (results jointly recorded with R142 in CLM-0275)
**Wall**: ~15 min ANDES wave

## TL;DR

R143 trained td3_qr_lstm at s54 with the quantile-Huber loss magnitude
fix applied (vs R142's buggy form). Geo result = 0.3843, essentially
identical to R142's 0.3845. Both became ingredient constituents of the
R154 4-way ensemble (CLM-0295).

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none — CLM-0275 closes Q-0019 distributional-critic question)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

R143 是 R142 的 fixed-loss 复跑，证明 quantile-Huber 的 bug fix 不影响
最终 geo 表现（0.3843 vs 0.3845）。两个 ckpt 后来都成为 R154 SOTA
4-way ensemble 的 constituent。R166 sweep 时补写本 verdict，把这个
round 从 in-flight 翻成 completed。

(Retro-written by R166 sweep 2026-05-19.)
