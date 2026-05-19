---
round: R96
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R96 plan — Cross-ckpt validation of CLM-0163 value-horizon mismatch

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: [[CLM-0163]] established on R72_w4 SOTA that obs→return at
paper γ=0.99 gives R²=−0.41 (worse than predicting mean) while γ=0/γ=1.0
give R²=0.93/0.71. R72_w4 is one ckpt (LSTM warmup=5 hyper basin) — the
finding could be hyper-specific or a paper-setup universal property.
R96 distinguishes by replicating on 3 other SOTA ckpts.
**Parent**: R91 / CLM-0163. Companion to R86 cross-ckpt synthetic
(but on-manifold, single-axis instead of multi-axis).

## TL;DR

4 ckpts × LS1+LS2 × 50 steps × 4 agents = 1600 records. Per ckpt, fit
4 R1 regressors (obs → return at γ ∈ {0, 0.9, 0.99, 1.0}) + 1 R2
(obs → SOTA action). Cross-agent median test R². Universal threshold:

| Outcome | Implication |
|---|---|
| All ckpts R²<0 at γ=0.99 AND R²>0.5 at γ=0 | **UNIVERSAL** — paper-setup property; γ × paper reward × paper obs creates the mismatch. R97+ ablates problem setup. |
| All ckpts R²<0.2 at γ=0.99 (not all <0) | weak universal — consistent direction, not as catastrophic as R72_w4 |
| Some ckpts replicate | partial — R72_w4 partly special |
| No replication | R72_w4-specific; CLM-0163 narrow. Less paper impact. |

## Ckpts under test

| Ckpt | Algorithm | Reason |
|---|---|---|
| `r72_w4_lstm_tau001_warmup5_s54` | TD3+LSTM warmup=5 | baseline (re-confirms R91-W1) |
| `r75_w2_lstm_tau001_warmup20_s59` | TD3+LSTM warmup=20 | different warmup, same algo class |
| `r63_w4_td3_combo_s49` | TD3 MLP (combo hyper) | different algorithm |
| `td3_norm_h64_s49` | TD3 MLP normalized actions h=64 | yet another TD3 MLP variant |

R21 V4_h50_s49 (SAC lucky basin) not available locally (archived).
Cross-class SAC representative would be ideal but is logistic blocker;
TD3 MLP variants serve as the algorithm-class-disjoint comparison.

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建: `scripts/r96_d3_cross_ckpt.py`, `results/r96_d3_cross_ckpt/`,
`memory/rounds/R96/{plan.md, verdict.md}`, 1 CLM (next free ≥ 0167).

ANDES: 4 short eval bursts × ~30s = ~2 min total occupancy, 1 slot at a
time. R85-classical + R94 occupy 2/3 slots concurrently → 3/3 brief touch,
under hard limit but no further headroom; if any slot is contested, R96
should serialise.

## Cross-references

- [[CLM-0163]] (R91 D3 finding on R72_w4 SOTA — the hypothesis under test)
- [[CLM-0160]] (R84 W3-traj on-manifold critic — companion methodology)
- [[CLM-0144]] (R57-R82 91-round algo plateau — R96 tests if value-horizon
  is plateau mechanism universally or just R72_w4)
- R86 plan (cross-ckpt synthetic critic monotone — different framing,
  comparable cross-ckpt scope)
- Q-0015 (closed-negative by CLM-0164 — γ ablation unblocked for R93+ if
  R96 confirms universal)
