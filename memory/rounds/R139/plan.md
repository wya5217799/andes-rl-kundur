---
round: R139
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R139 plan — Cluster density quantification (truly novel from R134-R137 chain)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究". R137 post-mortem flagged "discrete attractor
cluster structure" as one of three salvageable novel contributions.
R139 quantifies the structure with explicit bin counts.
**Parent**: CLM-0260 (R137), CLM-0250 (R135)

## TL;DR

3-region partition of N=91 fresh-scored ckpts by geo:
- 40% degenerate (geo < 0.10)
- 42% LSTM SOTA (geo > 0.30)
- 19% mid

LSTM SOTA cluster has 13× tighter cum_rf range than degenerate cluster
— homogeneous attractor. Reframes 91-round "plateau" as **attractor
selection** rather than algorithm-class limits.

Zero ANDES.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | `r139_cluster_density.py` + run | ~15 min |
| W2 | CLM-0264 + verdict + render | ~20 min |

## 资源冲突 gate

R83-R137 done; WSL free ✅
Read-only: R135 freshscore summary ✅

## 资产保护契约

不动: any code, V4, ckpt, test.

新建:
- `scripts/r139_cluster_density.py`
- `results/r139_cluster_density/{density.png, .pdf, summary.json}`
- `memory/rounds/R139/{plan.md, verdict.md}`
- `memory/claims/CLM-0264.md`

## Cross-references

- CLM-0260 (R137 post-mortem flagged this as salvageable) — parent
- CLM-0250 (R135 fresh re-score) — data source
- CLM-0264 (this round)
