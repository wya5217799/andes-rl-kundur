# R66 plan — Q-0010 LSTM eval probe fix + Q-0013 LSTM per-axis ablation

**Date**: 2026-05-17
**Type**: bug-fix + ablation
**Wall budget**: ~45 min

## Trigger

R65 ended with two open questions: Q-0010 (LSTM + Q-0007 corrupted training, R62 W1
gave 0.115 vs R57-α 0.333) and Q-0013 (which axis of R64 combo hurts LSTM transfer).
User: "执行 2 和 3" — do both.

## Waves

**W1 — Q-0013 single-axis ablation on LSTM s51** (3 parallel, R57-α + ONE axis change):
- N_SUBSTEPS=3 only
- MAX_GRAD_NORM=0.5 only
- batch_size=512 only

**W2 — Q-0010 fix verification**: LSTM + Q-0007 with `--eval-every-n-eps 5` and fix
applied (eval probe moved after `env.close()` + RNG state save/restore).

## Hypothesis

- H_q010: Eval probe ANDES global state pollution causes LSTM corruption.
  Moving probe to after `env.close()` will eliminate it.
- H_q013: One of (nsub3, gc05, bs512) is LSTM-friendly in isolation.

## Schema plan

- CLM-0102 (decision/S) — Q-0010 fix landed, eval probe moved
- CLM-0103 (finding/V) — Q-0013 ablation: architecturally none reach LSTM
- CLM-0104 (finding/V) — Code drift R57→R66: LSTM s51 0.526 → 0.4259 (-19%)
- Q-0010 closed positive
- Q-0013 closed negative
