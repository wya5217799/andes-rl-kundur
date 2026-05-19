---
round: R240
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R240 plan — scalar (no hreg) + paper-strict reward (phi_h=1, phi_d=1, phi_f=100, phi_abs=0)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, paper-integrity matrix completion)
**Driver**: R218 demonstrated paper-strict reward COLLAPSE under
hreg (geo=0.010). R239 demonstrated only-phi_abs near-SOTA under
scalar (geo=0.3954). R240 fills the missing 4th cell of the cross-algo
× reward 2×2 matrix: does paper-strict ALSO collapse under scalar?
If yes (predicted): paper Eq.14 reward function fails to train ANY
algorithm class we tested — strongest possible paper-integrity claim.

**Parent**: R218 (hreg paper-strict collapse), R239 (scalar only-phi_abs).

## TL;DR

Train `td3_lstm` scalar at s54 with paper-strict reward weights
(phi_h=1, phi_d=1, phi_f=100, phi_abs=0). Outcomes:
- **COLLAPSE (geo < 0.10)**: predicted; paper Eq.14 fails universally
  across algorithms. Completes 2×2 matrix decisively.
- **PARTIAL (0.10 ≤ geo < 0.30)**: scalar partially uses paper terms;
  hreg's collapse was algo-specific. Weakens the universality claim
  but introduces an interesting "hreg-amplifies-collapse" mechanism.
- **SOTA (geo ≥ 0.30)**: scalar trains fine on paper-strict; R218
  collapse was hreg-specific. Refutes universality entirely.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 1 --phi-d 1 --phi-f 100 --phi-abs 0 \
    --save-dir results/r240_w1_scalar_paperstrict_s54
```

After training:
```
python scripts/score_run.py --label r240_w1_scalar_paperstrict \
    --ckpt-dirs results/r240_w1_scalar_paperstrict_s54 \
    --out-dir results/r240_w1_scalar_paperstrict_s54
```

## Pre-registered 2×2 matrix (post R240 + R241)

| Algo \ Reward | full (R201/R72) | only-phi_abs (R238/R239) | paper-strict (R218/R240) |
|---------------|------------------|--------------------------|--------------------------|
| hreg          | 0.4152 SOTA      | 0.4128                   | 0.010 COLLAPSE           |
| scalar        | 0.391            | 0.3954                   | **R240 ?**               |
| cross-seed s51 hreg | 0.3901       | **R241 ?**               | —                        |

R240 + R241 together close all unknown cells in the algo × reward ×
seed matrix at this resolution.

## Cross-references

- R218 (hreg paper-strict = 0.010 COLLAPSE)
- R239 (scalar only-phi_abs = 0.3954)
- R241 (hreg only-phi_abs s51, in flight)
- R72_w4 (scalar full reward = 0.391)
- R201 (hreg full reward = 0.4152)
- CLM-0385 (R239 universal-inertness claim)
- ADR-0002 (paper-strict vs paper-faithful split)
