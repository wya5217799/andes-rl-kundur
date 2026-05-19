---
round: R131
state: aborted
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: triple-stack queue never fired; R154 SOTA changed direction (CLM-0295)
superseded_note: null
---
# R131 plan — triple-stack training td3_warmh0_qr_afe_lstm s54 (queued)

**Status**: QUEUED (fires when R124 / R127 / R129 frees a WSL slot)
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent, 一直干活, 别让我提醒你". CLM-0234 ships
triple-stack agent code (warmh0 actor + QR distributional critic + AFE
input) + 38/38 tests + train.py dispatch wired. R131 is the first
production training of this triple-stack: combines R104/CLM-0188 universal
warm-h_0 feasibility with R98 CLM-0157(a)+(b) critic-representation fixes.
**Parent**: CLM-0234 (R127 code addition), CLM-0157, CLM-0188.

## TL;DR

Single 75-ep paper-faithful s54 training of `td3_warmh0_qr_afe_lstm` for
first observation of triple-stack agent performance vs R72_w4 baseline 0.391
+ R122/R123/R124/R127 single/stacked critic fixes. If R127 (QR+AFE alone)
plateaus, R131 tests whether adding warm-h_0 makes the fix additive — i.e.,
whether actor-side and critic-side fixes compose constructively.

## Command (queued, launch when WSL slot frees)

```bash
LR=1e-4 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 nohup python -u scripts/train.py \
    --algo td3_warmh0_qr_afe_lstm \
    --qr-n-quantiles 51 \
    --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r131_w1_warmh0_qr_afe_s54 \
    --final-eval \
    > results/r131_w1_stdout.log 2>&1 &
```

## Gate

| 比较点 | R131 geo | Decision |
|---|---|---|
| ≥ 0.50 BREAKTHROUGH | triple-stack 突破 plateau, paper Sec.V 翻盘 |
| ≥ 0.45 STRONG | triple-stack 比 R72_w4 baseline 强 14%+, multi-seed verify next |
| ≥ 0.42 CONFIRM | triple-stack 比 baseline 强, 也比 stacked QR+AFE 强 (R127) — additive |
| [0.36, 0.42] MARGINAL | triple-stack 跟 single 一档, additivity 不显著 |
| < 0.36 REGRESS | triple-stack 过参, over-fitting on small training data |
| < 0.20 COLLAPSE | R56 s50 / R57 collapse mechanism recurs |

Cross-axis verdict matrix (when R122/R123/R124/R127/R131 all closed):

| Algo | s54 | s49 |
|---|---|---|
| td3_qr_lstm (a) | R122 | R129 |
| td3_afe_lstm (b) | R123 | R124 |
| td3_qr_afe_lstm (a+b) | R127 | — |
| **td3_warmh0_qr_afe_lstm (a+b+warmh0)** | **R131** | — |

## 资源冲突 gate

R131 launches **only** when at least one of R124/R127/R129 finishes.
WSL load currently 47 over 32 cores (1.5× over-subscribed); adding 4th
training now would push 60-70 load average. Launch is gated by an
already-running background watcher that signals on completion.

## 资产保护契约

不动 任何 in-flight session 文件. R131 仅 launch existing code path.
新建: `results/r131_w1_warmh0_qr_afe_s54/` + R131 verdict + 1 CLM.

## 测试不变量

- 38/38 critic_variants + smoke tests already pass (CLM-0234)
- triple-stack 单测包括: warm_h0 obs-conditional (different obs0 → different a0),
  quantile-Huber loss finite, save/load roundtrip
- V4 regression 不需重跑

## Cross-references

- CLM-0234 (R127 code ship, R131 is launch follow-up)
- CLM-0188 (warm-h_0 universal feasibility)
- CLM-0157 (R87+ priority order)
- CLM-0189 / CLM-0190 (QR + AFE single-axis prototypes)
- R127 plan (R131 expects R127 geo as comparison anchor)
- R122 / R123 / R124 / R129 plans (single-axis trainings)
