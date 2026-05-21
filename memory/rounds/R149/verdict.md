# R149 verdict — td3_qr_lstm s54 200ep horizon = over-training regression

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE (longer horizon hurts; R72_w4 0.391 unbeaten)

## TL;DR

R149 tested whether extending the training horizon from R72_w4's
75-episode budget to 200 episodes would let the QR-LSTM critic
discover a better policy. Result: over-training regression — geo
drops below R72_w4 baseline. The R149 plan.md self-declared this
closed-negative; R166 sweep retro-writes the verdict in canonical form.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none — null result on horizon-extension hypothesis; no Q was open
  for this specific question)

## Questions advanced (this round, status unchanged)

- Q-0014 (algorithm-side breakthrough) — R149 contributes another
  negative datapoint against single-algorithm interventions

## 给 PI 的话

R149 试了"训久一点能不能突破 plateau"，结论是不行（200ep 反而比
75ep 差）。这进一步坐实 R57-R154 的 plateau finding：单算法路径已经
exhausted，集成是唯一突破口（CLM-0280, CLM-0295）。R166 sweep 时补
verdict 把这轮正式 closed-negative。

(Retro-written by R166 sweep 2026-05-19.)
