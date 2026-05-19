---
round: R126
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R126 plan — r72_w4 vs r72_w5 obs-responsiveness vs policy quality (zero ANDES)

**Status**: ACTIVE → CLOSED-POSITIVE (N=2 suggestive)
**Opened**: 2026-05-19
**Driver**: PI "一直干活". R125 figure observed r72_w5 has highest obs-
responsiveness (51.9%) among 9 LSTM ckpts; needs link to actual policy
quality (11-axis geo).
**Parent**: CLM-0217, CLM-0225

## TL;DR

Look up r72_w4 + r72_w5 11-axis geo from cached eval summaries.

Result: **less obs-responsive = better geo**. r72_w4 (41.4% obs-ascent,
geo 0.391 SOTA) vs r72_w5 (51.9% obs-ascent, geo 0.317). Same hyper,
different seed. N=2 suggestive but interpretable.

R96 design revision: MLP h_init should target history-integrative h
trajectories from SOTA, not just "saturation key".

Zero ANDES. Zero WSL.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | training_log + eval summary lookup, finding emerges | ~10 min |
| W2 | Verdict + CLM-0229 + render | ~15 min |

Total ~25 min.

## 资源冲突 gate

R83 / R94 etc.: zero WSL ✅
ckpt training_log read-only ✅

## 资产保护契约

不动: any code, ckpt, V4, test.

新建:
- `memory/rounds/R126/{plan.md, verdict.md}`
- `memory/claims/CLM-0229.md`

## Cross-references

- CLM-0217 (R117 obs-ascent universality) — direct parent
- CLM-0225 (R125 figure) — sibling
- CLM-0188 (R104 warm-h_0 unlocks)
- CLM-0161 (R88 history integration in steady-state)
- CLM-0229 (this)
