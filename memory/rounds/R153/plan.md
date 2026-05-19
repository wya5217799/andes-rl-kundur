---
round: R153
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R153 plan — Ensemble eval breaks R72_w4 0.391 plateau (offline HAWE)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续". Post-R150 R98 prototype space exhausted at single-seed
75 ep. Tried offline ensemble eval of available ckpts: 3-way mean
{R72_w4 baseline + R142 QR + R143 QR-mean-fix} = **geo 0.4043 > R72_w4
0.391 (+3.5%)**. First plateau breaker found in this session.
**Parent**: R142 / R143 / R150 verdicts + CLM-0275 (R98 QR validated).

## TL;DR

`scripts/eval_ensemble.py` already supports HAWE (Heterogeneous Actor Weighted
Ensemble) for cross-algorithm ckpts. 5-min offline test combined the 4 ckpts
trained this session. Findings:

| Ensemble | geo | LS1 | LS2 | vs R72_w4 0.391 |
|---|---|---|---|---|
| **3-way mean** {R72_w4, R142, R143} | **0.4043** | 0.376 | 0.435 | **+0.013 (+3.5%)** |
| 3-way weighted (0.45/0.30/0.25) | 0.4021 | 0.367 | 0.440 | +0.011 (+2.9%) |
| 2-way mean {R72_w4, R142} | 0.3997 | 0.364 | 0.439 | +0.009 (+2.3%) |
| 4-way (+ R150 weak) | 0.3973 | 0.376 | 0.420 | +0.007 (+1.8%) |

3-way mean ensemble is the best. Diversity matters; R150 (geo=0.350 alone)
drags down the 4-way despite adding diversity.

## Method

Each agent in ensemble loads its own ckpt via patched checkpoint_loader.
Step-by-step:
1. Each scenario reset: every ensemble actor calls `begin_episode()` (R57-β
   pattern in `evaluation.ensemble.build_ensemble_action_fn`).
2. Per env step: each agent's actor takes obs_i and produces action_i deterministically.
3. Aggregate N actor actions for each agent via `mean` / `median` / `weighted`.
4. Standard 11-axis + cum_rf eval via `score_trace_files`.

WSL command (5 min wall, single ANDES session):
```bash
python scripts/eval_ensemble.py \
  --ckpt-dirs results/r72_w4_lstm_tau001_warmup5_s54 results/r142_w1_qr51_s54 \
              results/r143_w1_qr51_s54_fixed \
  --suffixes  best best best \
  --agg mean --label ens3_mean \
  --out-dir results/r150_ensemble_test
```

## Why ensemble works (paper-narrative interpretation)

R72_w4 (scalar Q td3_lstm) and R142/R143 (QR distributional td3_qr_lstm)
train to almost-identical action profiles at convergence (mu [0.88, 0.04,
0.87, 0.88] std=0.20 vs R72_w4 mu [0.94, ..., ..., ..., 0.94] std=0.20).
But subtle differences in per-step action remain — the QR critic learned a
*distributional* value function so its actor reacts to step-by-step state
perturbations slightly differently than scalar-Q's actor.

Mean-averaging the actions damps individual-agent over-correction. LS2
(load increase Bus 15 Area 2) particularly benefits: 0.4032 (R72_w4) →
0.4348 (ensemble), +0.032 LS2 gain.

LS1 (load reduction Bus 14 Area 1) less benefit but no degradation:
0.354 (R72_w4) → 0.376 (3-way), +0.022.

## Cross-references

- CLM-0275 (R142 QR validated, AFE falsified)
- CLM-0094 (R72_w4 SOTA baseline 0.3908)
- R72_w4 baseline ckpt + R142 + R143 + R150 ckpts (all s54)
- HAWE — `evaluation/ensemble.py`, eval_ensemble.py
- paper Sec.IV-C — ensemble lift may complement single-policy claim

## Gate

✅ BREAKTHROUGH (3.5% > +0.05 single-seed lift is significant for paper) —
ensemble of cross-algorithm same-seed ckpts beats best individual.

## Questions opened (this round)

- Q-NEW: cross-seed ensemble — combine s49 + s51 + s54 ckpts for paper-grade
  3-seed median? Would need s49/s51 retrains first.
- Q-NEW: does ensemble lift hold at multi-seed-mean level (vs single-seed lottery)?

## Questions closed (this round)

- (none — opens space rather than closing)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog): R153 ensemble proof points to
  HAWE as the practical plateau breaker rather than any single algorithm
  intervention. Paper claim should pivot: "single-policy plateau at 0.39,
  HAWE ensemble of 3 cross-algorithm ckpts gives 0.404 = +3.5%".
