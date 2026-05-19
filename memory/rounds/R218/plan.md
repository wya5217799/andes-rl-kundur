---
round: R218
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R218 plan — paper-strict reward weights (phi_h=1, phi_d=1, phi_f=100) + phi_abs=0

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, paper-faithfulness critical test)
**Driver**: phi_abs sweep showed V4 needs phi_abs ≥10 to escape
collapse. V4 default rescales phi_h=phi_d to 1/178 of paper nominal
(0.0056 vs 1.0). Hypothesis: at PAPER-original weights (phi_h=1,
phi_d=1), phi_abs=0 might be sufficient. If yes, **R201 SOTA is
restorable in paper-faithful form** by using paper Eq.14 weights
directly.

**Parent**: R217 verdict (threshold characterization).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with paper Eq.14 weights:
--phi-h 1 --phi-d 1 --phi-f 100 --phi-abs 0. Three outcomes:
- **PAPER-FAITHFUL SOTA (geo ≥ 0.30)**: paper weights work; phi_abs=50
  was a V4-rescale artifact. **Paper claim restored**: we ARE faithful
  to Eq.14 weights, just at different absolute magnitudes than V4 default.
- **PARTIAL (0.10 ≤ geo < 0.30)**: paper weights help but don't fully
  rescue; phi_abs adds value.
- **COLLAPSE (geo < 0.10)**: paper Eq.14 weights are insufficient at
  any rescale; phi_abs is a genuine additional contribution. R214's
  finding stands.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-f 100 --phi-h 1 --phi-d 1 --phi-abs 0 \
    --save-dir results/r218_w1_hreg_paperstrict_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R214 (phi_abs=0, V4 default phi_h/phi_d = 0.0056 → collapse)
- R201 (V4 default + phi_abs=50 = SOTA 0.4152)
- R215 (phi_abs=10, V4 default phi_h/phi_d → 0.4061)
- CLM-0203 (R103 paper_strict_pure: similar config attempt, low result)
- ADR-0002 (paper-strict vs paper-faithful split)
