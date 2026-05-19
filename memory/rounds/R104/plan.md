---
round: R104
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R104 plan — Multi-ckpt warm-h_0 feasibility (R99 universalisation)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究, 一直干活, 别让我提醒你". CLM-0183 (R99) tested
Q-0022's architectural premise on the R72_w4 SOTA only (N=1 ckpt × 4
agents). R104 extends to 9 ckpts spanning R58 / R62 / R72 × 7 seeds ×
hidden=64+128 to test universality.
**Parent**: CLM-0183, Q-0022

## TL;DR

9 ckpts × 4 agents = **36 LSTM critic instances**. Per-instance:
100 step-0-like synthetic obs × grad-ascent on (h_0, c_0). Compare
||a||(h=0) vs ||a||(h*), record absolute ΔQ (avoids R99's +254% rel%
outlier issue).

Result: **9/9 UNIVERSAL_FEASIBLE**. Median norm_zero=8.5%, norm_star=
95.6%, lift=+86.8 pp. ΔQ_abs always positive (range +0.005 to +0.065
across ckpts). Q-0022 architectural premise NOT R72_w4-specific.

Zero ANDES, zero WSL.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | Write `scripts/r104_warm_h0_multickpt.py`, run on 9 ckpts | ~25 min |
| **W2** | Verdict + CLM-0188 + render | ~25 min |

Total wall ~50 min.

## 资源冲突 gate

R83 / R85 / R89 (WSL): R104 zero ANDES ✅
R91 (D3 obs sufficiency): different forensics, zero ckpt conflict ✅
R94 (widen-bound training): R104 strengthens Q-0022 independently of R94 ✅
R100-R103 (other concurrent windows): unrelated forensics, no resource overlap ✅

Output namespace: `results/r104_warm_h0_multickpt/{summary.json,
per_agent_table.csv}` (new).

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt / R84/R86/R92/R95/R99 scripts / any test.

新建: `scripts/r104_warm_h0_multickpt.py`,
`results/r104_warm_h0_multickpt/`,
`memory/rounds/R104/{plan.md, verdict.md}`,
`memory/claims/CLM-0188.md`.

## 测试不变量

V4 regression 不重跑. R57+ ckpt read-only.

## Cross-references

- CLM-0183 (R99 N=1 architectural feasibility) — parent
- CLM-0174 (R95 LSTM warm-up lag) — mechanism this confirms universal
- CLM-0155 (R86 cross-ckpt monotone) — sibling universality finding
- Q-0022 (warm-h_0 candidate) — premise upgraded
- CLM-0188 (this round)
