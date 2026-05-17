# R65 plan — Hyper sweep transfer to SAC + LSTM

**Date**: 2026-05-17
**Type**: hyper transfer + algo-specific verification
**Wall budget**: ~2 hr (4 waves)

## Trigger

R64 closed with TD3 +37.5pp paper-metric. SAC and LSTM never tested
with new hyper (lr=3e-3, gc=0.5, bs=512, ns=3). R65 transfers and
sweeps any LSTM-specific lr.

## Waves

**W1** — SAC h64 + R64 combo + lr=3e-3 + paper_strict_pure_radsec 3-seed
**W2** — LSTM h64 + R64 combo + warmup-5 + s49/s51/s53 3-seed (no Q-0007 — Q-0010 bug)
**W3** — LSTM lr {3e-4, 5e-4, 1e-3} s51 (oops: clamp to 1e-4 in train.py:305)
**W4** — LSTM lr {3e-4, 5e-4, 1e-3} unclamped (LSTM_LR_UNCLAMP=1)

## Hypotheses

- H_sac_transfer: new hyper combo lifts SAC paper-faithful
- H_lstm_transfer: new hyper combo lifts LSTM 6-axis
- H_lstm_lr_clamp: clamp 1e-4 in train.py:305 is correct
