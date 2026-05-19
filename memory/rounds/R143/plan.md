---
round: R143
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
closed_note: QR-LSTM fixed-loss results recorded in CLM-0275
---
# R143 plan — td3_qr_lstm s54 with FIXED quantile-Huber loss magnitude

**Status**: ACTIVE (training)
**Opened**: 2026-05-19
**Driver**: PI "继续科研, 有问题就优化". CLM-0255 (R124/R127/R129 collapse)
+ CLM-0263 (do-nothing attractor mechanism) point to **critic loss magnitude
~51× MSE** as root cause: ``sum(dim=1)`` over N=51 quantiles in QR-Huber loss
makes critic over-fit in 30 ep → actor collapses to a=0 to avoid value
variance penalty.

**Fix**: changed `sum(dim=1)` → `mean(dim=1)` in
``networks_critic_variants.quantile_huber_loss``. Loss magnitude now
comparable to scalar-Q MSE; preserves distributional gradient structure
(Dabney 2018 Eq. 3 with N-normalised pred-dim aggregation).
**Parent**: CLM-0255 (R98 prototype empirical collapse), CLM-0263 (mechanism).

## TL;DR

Re-run R142 (`--algo td3_qr_lstm --seed 54` 75 ep) with FIXED critic loss.
Direct A/B vs R142 (same algo + seed, BUGGY loss still running in parallel).
If R143 ≥ 0.30, loss-magnitude was the binding constraint — paper Sec.V claim
"distributional critic works once loss is properly normalised". If R143 also
collapses, mechanism is deeper than loss scaling.

## A/B comparison matrix (when 3 runs land)

| Round | Algo | Loss aggregation | seed | Expected geo |
|---|---|---|---|---|
| R142 | td3_qr_lstm | **sum(dim=1)** (buggy) | 54 | ≤ 0.10 |
| R143 | td3_qr_lstm | **mean(dim=1)** (fixed) | 54 | TBD — key data point |
| R129 | td3_qr_lstm | sum (buggy) | 49 | 0.0387 (CLM-0255) |
| R140 | td3_afe_lstm | n/a (scalar Q) | 54 | TBD |
| R124 | td3_afe_lstm | n/a (scalar Q) | 49 | 0.0100 (CLM-0255) |
| (ref) | R72_w4 td3_lstm baseline | scalar Q | 54 | 0.391 |
| (ref) | no_control | n/a | 42 | 0.104 |

## Gate

- BREAKTHROUGH ≥ 0.45: distributional critic + fix unlocks paper plateau-breaker
- CONFIRM ≥ 0.30: fix is significant, paper claim "QR works at correct scaling"
- MARGINAL [0.15, 0.30]: fix helps but not sufficient; need more interventions
- REGRESS ≤ 0.10 (matching buggy R142): mechanism deeper than loss magnitude

## Resource

WSL fresh post-restart. 3 process running (R140, R142, R143). Load expected
~6 cores out of 32. Memory low. Wall ~30 min on clean machine.

## Cross-references

- CLM-0255 (3-prototype collapse headline)
- CLM-0263 (do-nothing attractor mechanism candidate)
- CLM-0189 (QR prototype original V tag; if R143 breaks plateau, CLM-0189
  upgrades from "code-prototype-only" back to "validated")
- R142 plan (peer with buggy loss)
- R98 / R108 verdicts (original prototype + dispatch)
