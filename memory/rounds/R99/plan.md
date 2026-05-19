---
round: R99
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R99 plan — Q-0022 LSTM warm-h_0 architectural feasibility (zero ANDES)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究". CLM-0174 (R95) identified LSTM warm-up lag
as plateau mechanism #2; Q-0022 proposed warm-h_0 = MLP(obs_0) as fix.
R99 tests whether the frozen R72_w4 actor weights have architectural
slack for this fix BEFORE committing WSL training resources.
**Parent**: CLM-0174, CLM-0170, Q-0022

## TL;DR

100 synthetic step-0-like obs × 4 R72_w4 agents × 500-step gradient
ascent over (h_0, c_0). Measure: with frozen weights, does there
EXIST a hidden state that pushes actor output from 10% of max to
~100% AND raises critic Q?

Result: **FEASIBLE**. ||a|| lifts from 10.4% → 99.5% of max (89.2 pp),
Q lifts +57.8% median (range +31% to +254% across 4 agents). Optimal
h* norms 11-15, reachable by a small MLP head. Q-0022 architectural
premise confirmed independent of R94 widen-bound outcome.

Zero ANDES, zero WSL, zero conflict.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | Write `scripts/r99_warm_h0_feasibility.py` + run grad-ascent | ~20 min |
| **W2** | Verdict + CLM-0183 + render | ~30 min |

Total wall ~50 min.

## 资源冲突 gate

R83 / R85 / R89 (WSL): R99 zero ANDES. ✅
R91 (D3 obs sufficiency on cached traj): different cached file (r84_d2b), R99 reads only ckpt + critic. ✅
R94 (widen-bound training, WSL): orthogonal mechanism, R99 strengthens Q-0022 independently. ✅

Output namespace: `results/r99_warm_h0_feasibility/summary.json` (new namespace).

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt (read-only torch.load) / R84/R86/R92/R95
scripts / any test.

新建: `scripts/r99_warm_h0_feasibility.py`,
`results/r99_warm_h0_feasibility/summary.json`,
`memory/rounds/R99/{plan.md, verdict.md}`,
`memory/claims/CLM-0183.md`.

## 测试不变量

V4 regression 不重跑. R72_w4 ckpt weights_only=True load.

## Cross-references

- CLM-0174 (R95 LSTM warm-up lag finding) — parent
- CLM-0170 (R92 bang-bang saturation) — sibling mechanism
- CLM-0175 (R94 prediction matrix) — independent path
- Q-0022 (warm-h_0 candidate) — architectural premise tested here
- CLM-0183 (this round)
