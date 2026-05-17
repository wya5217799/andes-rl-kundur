# R68 plan — SAC tau=0.001 verify + LSTM hyper sweep

**Date**: 2026-05-17/18
**Type**: hyper-sweep verify + LSTM exploration
**Wall budget**: ~2 hr (multiple waves of 3 parallel)

## Trigger

R67 收尾后用户问 "继续挤", 答:
- SAC tau=0.001 未 verify (R67 只测 TD3)
- LSTM 未试 tau=0.001 (R66 closed Q-0013 negative on R64 combo, 但 tau is not in that ablation set)

## Waves

**W1 (3-seed SAC verify)**: SAC h=64 combo + tau=0.001, s49/s50/s51
**W2 (LSTM pilot)**: LSTM + tau=0.001 + warmup=5 s51 (R57-α default)
**W3 (3-seed verify LSTM warmup=30)**: s49/s50/s51
**W4 (LSTM warmup U sweep)**: warmup ∈ {0, 8, 10, 12, 15, 18, 20, 22, 25, 30, 35, 40} s51 single-seed

## Hypotheses

- H_W1: SAC tau=0.001 也 +3-4% (TD3 pattern transfer)
- H_W2: LSTM + tau=0.001 不 corrupt (Q-0010 fix landed)
- H_W4: LSTM warmup=5 (R57 选) 是 U bottom (验证 R57-α 选择)

## Out of scope

- LSTM cross-axis (tau + warmup) — deferred to R69
- v3 ranker upgrade — deferred to R69
- Code drift bisect (CLM-0104, deferred)
