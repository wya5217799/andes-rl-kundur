---
round: R127
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R127 plan — Stacked QR+AFE critic first training (td3_qr_afe_lstm s54)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent, 别让我提醒你". R122 (td3_qr_lstm s54) + R123
(td3_afe_lstm s54 queued) + R124 (td3_afe_lstm s49) cover single-axis fixes.
R127 stacks (a)+(b) — critic input AFE'd `[obs, a, a², |a|, sign(a)]` **AND**
critic output 51 quantiles. If single-axis prototypes only partly break the
plateau, R127 + tests whether stacking is additive (R98 design hypothesis).
**Parent**: CLM-0189 (QR proto), CLM-0190 (AFE proto), R98+R108 verdicts.

## TL;DR

Run `--algo td3_qr_afe_lstm --seed 54` 75 ep, same hyper as R72_w4 baseline.
Tests **stacked** critic-representation fix. Wall ~50 min.

## Command

```bash
LR=1e-4 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/train.py \
    --algo td3_qr_afe_lstm \
    --qr-n-quantiles 51 \
    --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r127_w1_qr_afe_s54 \
    --final-eval
```

## Gate

- BREAKTHROUGH (geo ≥ 0.50): stacked fix breaks plateau, paper Sec.V wins
- CONFIRM (geo ≥ 0.42): stacked is meaningfully better than baseline 0.391
- MARGINAL [0.36, 0.42]: stacking has small extra over single-axis
- EQUAL (~0.39): stacking 不 additive, single axes already exhaust
- REGRESS (< 0.36): stacked over-parametrised, hurts

Comparison matrix when R122/R123/R124/R127 all closed:
| Algo | seed | expected geo |
|---|---|---|
| td3_lstm baseline (R72_w4) | 54 | 0.391 ref |
| td3_qr_lstm (R122) | 54 | TBD |
| td3_afe_lstm (R123) | 54 | TBD |
| td3_afe_lstm (R124) | 49 | TBD |
| **td3_qr_afe_lstm (R127)** | 54 | **TBD** |

## Code prerequisites (already done in this session)

- ``src/andes_rl_kundur/agents/td3_qr_afe_lstm.py`` — R127 agent class (this session)
- ``src/andes_rl_kundur/agents/networks_critic_variants.py`` —
  ``RecurrentQRAfeQNetwork`` + ``RecurrentQRAfeDoubleQCritic`` (this session)
- ``scripts/train.py`` — dispatch wired (--algo td3_qr_afe_lstm + import +
  choices + ctde-reject + warmstart-reject + elif build branch) (this session)
- ``tests/test_critic_variants.py`` — 4 stacked QR-AFE test cases (this session)
- ``tests/test_train_critic_variants_smoke.py`` — 1 stacked dispatch test (this session)
- All 35 tests pass on Windows native pytest ✓

## 资源冲突 gate

WSL processes: R102 (PI eval, ~25 min in, completes soon) + R115/R119/R122
(training, 50-70 min in) + R121 (forensic, ~10 min in) + R124 (my AFE s49,
~5 min in). Plus R127 = 7 process. WSL memory 24 GB / 3.8 GB used — plenty.
ANDES TDS single-core; 7 cores out of 32 = 22 % utilisation. Safe.

R127 uses BLAS thread limit `MKL_NUM_THREADS=1 OMP_NUM_THREADS=1` to prevent
PyTorch backward from over-subscribing under the contention.

## 资产保护契约

不动: src/agents/td3_lstm.py / td3_qr_lstm.py / td3_afe_lstm.py / networks.py /
V4 / V4Config / base_env / paper_grade_axes / 任何 R57+ ckpt / 任何 existing test.

新建: `results/r127_w1_qr_afe_s54/` + 1-2 CLM + plan/verdict.

## 测试不变量

- R98 / R108 / R125 (stacked) 全部 35 测试 pass ✓
- V4 regression `tests/test_v4_env_regression.py` 不需重跑

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | (this) plan.md | done |
| **W2** | WSL launch + monitor | ~50 min |
| **W3** | Verdict + CLM(s) + chat brief | ~25 min |

## Cross-references

- CLM-0157 (R86 R87+ priority a > b > c, R127 stacks a+b)
- CLM-0189 (QR proto), CLM-0190 (AFE proto)
- CLM-0205 (R108 train.py wire)
- R122/R123/R124 plan (single-axis trainings, R127 is stack-additive test)
