# R198 verdict — s55 viable but -18% below SOTA; s54 remains lucky seed

**Date**: 2026-05-19
**Status**: CLOSED-NEUTRAL (viable seed, no SOTA change)
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at s55. Result: geo=**0.3402**,
LS1=0.276, LS2=0.420. Viable training (above gate 0.30) but well
below R174 SOTA 0.4139 at s54. **s55 is not luckier than s54.**

## Updated seed table for R174 hyper

| seed | geo | rank |
|------|-----|------|
| 49 | 0.046 ✗ collapse |
| 50 | 0.3515 ✓ |
| **55** | **0.3402 ✓** (R198 new) |
| 51 | 0.3888 ✓ |
| 54 | **0.4139 ✓ SOTA** |

Cross-seed mean across 4 viable seeds: (0.3515 + 0.3402 + 0.3888 +
0.4139) / 4 = **0.374**. Adding the collapsed seed for disclosure
(5-seed mean): 0.308.

## What this shows

s54 was the lucky seed by ~6-22% margin over other tested viable
seeds {s50, s51, s55}. The "lucky seed s54" caveat in the paper now
has 4 supporting cross-seed data points (s55 confirms s54 outperforms,
not just s50/s51).

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — adds data to existing Q-0005 mechanism narrative)

## Questions advanced (this round, status unchanged)

(none directly)

## 给 PI 的话

R198 = hreg λ=0.002 at **s55** = geo 0.3402 (viable, 不是新 SOTA).

**4-seed viable mean** 现在 = (0.3515 + 0.3402 + 0.3888 + 0.4139)/4
= **0.374**. s54 仍是 lucky seed by ~6-22%.

R199 候选: 试 shorter training (50ep, R174 是 75ep) — 反向测试 over-
training 跟 under-training. R191 已经测 200ep (parallel) = 0.3161
regression. Maybe 50ep 反而更好.

## Cross-references

- R174 (s54 SOTA 0.4139)
- R181 (s51 0.3888)
- R185 (s50 0.3515)
- R183 (s49 collapse)
- CLM-0350 (Q-0005 mechanism)
