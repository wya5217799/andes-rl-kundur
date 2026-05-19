---
round: R144
state: aborted
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: stacked QR+AFE replaced by R127 path; R154 SOTA closes ensemble direction
superseded_note: null
---
# R144 plan — stacked td3_qr_afe_lstm s54 with FIXED quantile-Huber loss

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: R143 (QR alone with fix, in progress) tests loss-magnitude
hypothesis. R144 = stacked QR+AFE with fix, retests R127's stacked collapse
(0.0100) at proper loss scaling. If R143 works but R144 doesn't → AFE input
is the additional pathology. If both work → loss-magnitude was sole bug.
**Parent**: CLM-0255, CLM-0263, R143 plan.

## TL;DR

Re-run R127 (`--algo td3_qr_afe_lstm --seed 54` 75 ep) with the new
``mean-over-pred`` quantile-Huber loss aggregation. Direct test of whether
the do-nothing attractor in CLM-0263 is loss-magnitude-induced (fix wins)
or AFE-input-induced (fix doesn't help).

## Gate (matrix with R143)

| R143 (QR fixed) | R144 (stacked fixed) | Interpretation |
|---|---|---|
| ≥ 0.30 | ≥ 0.30 | Loss-mag was binding constraint, paper Sec.V claim "QR+AFE work" |
| ≥ 0.30 | < 0.10 | Loss-mag fixes QR only; AFE has separate "zero-action preference" bug |
| < 0.10 | < 0.10 | Loss-mag NOT binding; mechanism deeper (critic class architecture) |

## Cross-references

- CLM-0255 (3-prototype collapse)
- CLM-0263 (do-nothing mechanism candidate)
- R142 / R143 plans (peer trainings)
- R127 verdict (the buggy stacked precedent at 0.0100)
