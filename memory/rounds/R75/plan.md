# R75 plan — multi-seed expansion + ensemble exploration

**Date**: 2026-05-18
**Type**: marginal sweep + ensemble (free)
**Wall budget**: ~30 min

## Trigger

R74 收尾. 用户 "继续挤". 剩余探索:
1. Multi-seed expansion (s58/s59/s60) at warmup=20 — drift rate ~33%, 期望 1-2 healthy
2. Ensemble of healthy ckpts (free, no training, R57-β HAWE pattern reuse)

## Waves

**W1**: s58 + warmup=20 (new seed)
**W2**: s59 + warmup=20
**W3**: s60 + warmup=20
**W4-W7**: 4 ensemble configs across 6 healthy ckpts (mean / top3 / weighted / top2)

## Hypotheses

- H_seeds: expect 1-2 of 3 new seeds healthy (~33% drift rate)
- H_ensemble: HAWE-style averaging may yield +5-10% over single best (R57-β history)

## Out of scope

- Architecture refactor (Q-0013 deferred)
- More TDD/tooling work (R74 done)
