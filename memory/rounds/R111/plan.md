---
round: R111
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R111 plan — Cross-algo-class step-0 saturation control (zero ANDES)

**Status**: ACTIVE → CLOSED-POSITIVE (with mechanism reframing)
**Opened**: 2026-05-19
**Driver**: PI "一直干活". CLM-0193 (R107) and CLM-0188 (R104) confirmed
LSTM-specific step-0 saturation deficit. R111 tests whether MLP-based
actors (TD3-MLP, SAC) also suffer the deficit, to determine whether
warm-h_0 fix targets a LSTM-specific bottleneck or a general one with
an LSTM-specific symptom.
**Parent**: CLM-0193, CLM-0188

## TL;DR

6 R86 ckpts × 4 agents × 100 synthetic step-0-like obs. Report
tanh-bounded ||a|| at step 0 (h=0 for LSTM, tanh(mean) for MLP /
SAC).

Result: **deficit is near-universal across actor architectures**.
5/6 ckpts have step-0 ||a|| ≤ 15% of max; only r63 (TD3-MLP with
unusual hyper combo) reaches 65%. SAC and TD3-MLP r58 are similarly
under-saturated as LSTM.

Implication: paper-faithful 7-dim obs is insufficient to produce
saturated step-0 output across any actor class in this codebase.
Warm-h_0 (Q-0022) is the LSTM-specific instantiation of a broader
"step-0 saturation" issue.

Zero ANDES. Zero WSL. Zero conflict.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | `r111_action_norm_by_algo_class.py` + tanh-fix + run | ~25 min |
| **W2** | Verdict + CLM-0207 + render | ~15 min |

Total wall ~40 min.

## 资源冲突 gate

R83 / R94 / R110 / R102 (WSL): R111 zero ✅
ckpt R57+ read-only: ✅
Output namespace: `results/r111_action_norm_by_algo_class/` ✅

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt / any test.

新建:
- `scripts/r111_action_norm_by_algo_class.py`
- `results/r111_action_norm_by_algo_class/summary.json`
- `memory/rounds/R111/{plan.md, verdict.md}`
- `memory/claims/CLM-0207.md`

## Cross-references

- CLM-0193 (R107 LSTM-h=0 deficit) — R111 generalises across algos
- CLM-0188 (R104 cross-ckpt feasibility) — sibling
- CLM-0155 (R86 cross-ckpt monotone-Q) — related universality
- CLM-0174 (R95 LSTM ramp-up)
- CLM-0207 (this round)
