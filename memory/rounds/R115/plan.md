---
round: R115
state: superseded
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: R103
abort_reason: null
superseded_note: paper_strict_pure closed-negative by CLM-0203 (R103)
---
# R115 plan — paper_strict_pure reward test, closes CLM-0192

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究，一直继续，别问我了". CLM-0191 (R105) found R72_w4
SOTA's training reward is **substantively divergent from paper Eq.14-18**
(PHI_H/D ÷178 from paper, PHI_ABS=50 added as Kundur-tight-coupling
augmentation, normalized vs physical action_penalty). CLM-0192 (R105)
opened the load-bearing test: train `paper_strict_pure` LSTM and compare
its eval geo to R72_w4's 0.391. R111-R114 reserved by parallel sessions,
R115 is the next free round.
**Parent**: CLM-0192 R90+ open question.

## TL;DR

Train 1 wave at R72_w4 same hyper + s54 + 75 ep with
`--reward-config paper_strict_pure` (paper Eq.14-18 verbatim: PHI_ABS=0,
PHI_H=PHI_D=1.0, action_penalty_mode=physical). Falsifies:

- **PHI_ABS=50 load-bearing**: if geo ≪ 0.391, R72_w4's 0.391 depends
  on the Kundur-tight-coupling reward augmentation; CLM-0192 decision
  (keep PHI_ABS=50) is justified.
- **PHI_ABS=50 cosmetic**: if geo ≈ 0.391 or higher, PHI_ABS=50 is
  not load-bearing; CLM-0192 paper write-up can drop it for paper
  Eq.14 purity.

Combined with R100-W1 (CLM-0190 marginal hreg) and R83 (obs aug failed),
this becomes the **last orthogonal axis** unexplored: training-time
reward shape, **not** policy structure.

Important context (CLM-0194 R110): all R57-R100 train+eval used
compound disturbance (paper load step + ANDES default Toggler Line_8
trip at t=2s). R115 inherits the compound disturbance — it's not a
paper-pure test, it's a within-V4 reward ablation.

## Methodology

### Training command

```
LR=1e-4 python scripts/train.py \
    --algo td3_lstm \
    --reward-config paper_strict_pure \
    --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r115_w1_strict_pure_s54
```

Note: paper_strict_pure uses action_penalty_mode=physical, so
`--normalize-actions` is dropped. PHI_F=100 unchanged. PHI_ABS=0,
PHI_H=PHI_D=1.0.

ANDES WSL ~15 min.

### Eval

Automatic final_eval at end of training → final_eval_summary.json.

## Gate criteria

- **LOAD-BEARING (geo < 0.30)**: PHI_ABS=50 was lifting R72_w4 from
  ~0.25-0.29 to 0.391. Reward augmentation justified; paper write-up
  defends it as Kundur engineering choice.
- **MILDLY LOAD-BEARING (geo ∈ [0.30, 0.36])**: PHI_ABS=50 added ~10-20%
  geo. Paper write-up presents both numbers honestly.
- **NOT LOAD-BEARING (geo ≥ 0.36)**: PHI_ABS=50 was cosmetic;
  paper_strict_pure achieves comparable geo. Drop PHI_ABS=50 from
  paper write-up.
- **HIGHER (geo > 0.42)**: PHI_ABS=50 was actually hurting; remove it
  for both paper purity and SOTA improvement.

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/td3_lstm.py /
任何 R57+ ckpt. 不动 R100 ckpt. 不动 R72_w4 ckpt. 用现成 td3_lstm 类
+ V4Config.paper_strict_pure() (already supported via --reward-config).
新建: `results/r115_w1_strict_pure_s54/` outputs, `memory/rounds/R115/`,
1 CLM (≥0195 buffer).

## Cross-references

- CLM-0191 / CLM-0192 (R105 reward divergence audit + decision)
- CLM-0094 (R72_w4 SOTA 0.391)
- CLM-0144 (91-round plateau)
- CLM-0190 (R100-W1 LSTM-norm reg marginal, drift falsified as
  mechanism)
- CLM-0194 (R110 compound disturbance Toggler issue)
- R85 / CLM-0184 / CLM-0186 (classical baseline + RL advantage)
