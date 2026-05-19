---
round: R72
state: active
opened: '2026-05-18'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R72 plan — LSTM paper-strict mode retry + 5-seed canonical expansion

**Date**: 2026-05-18
**Type**: incompatibility verification + seed expansion
**Wall budget**: ~30 min

## Trigger

R71 收尾后用户 "继续". 剩 3 探索:
- SAC v3.1 re-rank (free, no training)
- LSTM + paper-strict-radsec retry (Q-0010 fix landed since R67 W1a -145%)
- 5-seed expansion of canonical best path (s54/s55 new seeds)

## Waves

**Pre-W: SAC 3-seed v3.1 re-rank** — confirmed SAC NOT v3.1 candidate (mean=0.069)

**W1-W3: LSTM + paper-strict-radsec + tau=0.001 + Q-0007 retry** (s51/s50/s52)
- Test if Q-0010 fix unlocks LSTM paper-strict-mode (R67 W1a was -145%)

**W4-W5: tau+warmup=5 + s54/s55** (5-seed expansion of canonical family)

**W6: LSTM + paper_strict_pure (non-radsec variant)** s51
- Test if reward shape variation matters

## Hypotheses

- H_paper-strict: Q-0010 fix + tau unlocks LSTM in paper-strict mode
- H_5seed: s54 + s55 healthy → 5-seed mean improves rigor
- H_pure: paper_strict_pure may work where paper_strict_pure_radsec failed
