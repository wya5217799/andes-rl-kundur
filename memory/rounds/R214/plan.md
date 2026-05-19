---
round: R214
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R214 plan — hreg SOTA with --phi-abs 0 (paper-faithfulness test)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, paper-faithfulness)
**Driver**: V4 default reward has phi_abs=50, a non-paper "Kundur tight-
coupling patch" (per v4_config.py docstring). R214 disables it
(--phi-abs 0) at the SOTA hyper. Tests whether R201 0.4152 SOTA
depends on a non-paper reward term. If geo stays high, the SOTA is
paper-faithful; if drops, SOTA is artifact of the non-paper term.
**Parent**: R201 (SOTA at phi_abs=50 default).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --phi-abs 0
(remove the non-paper Kundur tight-coupling penalty). Three outcomes:
- **PRESERVED (geo ≥ 0.40)**: SOTA is paper-faithful; the phi_abs=50
  term is not load-bearing. **Paper claim strengthens**.
- **DEGRADED BUT VIABLE (0.30 ≤ geo < 0.40)**: phi_abs partly
  contributes; paper should disclose the dependency.
- **REGRESS (geo < 0.30)**: SOTA implicitly depends on phi_abs=50;
  must be disclosed prominently in paper.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-abs 0 \
    --save-dir results/r214_w1_hreg_phiabs0_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (SOTA at phi_abs=50 default)
- v4_config.py docstring (phi_abs=50 is non-paper)
- ADR-0002 (paper-strict-vs-paper-faithful split)
