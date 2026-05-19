---
round: R106
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R106 plan — D4 env stochasticity floor: disturbance-magnitude stress envelope

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: After [[CLM-0160]] (critic OK) + [[CLM-0168]] / [[CLM-0169]]
(value-horizon mismatch refuted), the surviving plateau-mechanism
candidates from the R84 plan are env-side / reward / policy class.
R103 covers reward shape (in-flight). R106 covers the env-side: how
much does eval geo vary across legitimate disturbance magnitudes?
**Parent**: R84 plan §D4 axis (env stochasticity floor — never run
until now), CLM-0169 R85+ candidate list.

## TL;DR

R72_w4 SOTA × magnitude_scale ∈ {0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0}
× LS1+LS2 = 14 ANDES evals. Score canonical 6-axis via
`evaluation/summary.score_trace_files`. Report:

- geo distribution mean / median / std / IQR / range across scales
- σ_geo / mean_geo (coefficient of variation)
- Whether 0.391 is a noise ceiling (cv ≥ 0.30) or policy ceiling (cv ≤ 0.15)

Wall: ~3.5 min ANDES, 1 slot.

## Why this is meaningful

Every prior round (R37 onwards) reports a single geo number per ckpt
× LS1 + LS2 fixed at paper magnitudes. **No round has ever measured
variance under disturbance magnitude variation**. If the 0.391 plateau
varies by ±15-30% across legitimate magnitudes, then the headline
number is implicitly drawing on a single operating point and "plateau
mechanism" interpretations are subject to noise.

## Methodology

Same `paper_path.run_scenario` + canonical `score_trace_files` as
`scripts/eval_ddic.py`. delta_u is paper baseline × magnitude_scale:
- LS1: -2.48 × scale at Bus 14
- LS2: +1.88 × scale at Bus 15

STEPS = 150 (30s @ DT=0.2, matches canonical eval). Env seed = 42
(deterministic, comm_fail_prob = 0). The SOTA + V4 env are fully
deterministic; the only variance source IS the magnitude.

## Gate criteria

| Outcome | Verdict | R107+ implication |
|---|---|---|
| cv_geo > 0.30 | ENV_FLOOR_HIGH_DOMINATES_PLATEAU | 0.391 is a noise ceiling; future eval must report multi-magnitude range |
| cv_geo ∈ (0.15, 0.30] | ENV_FLOOR_MODERATE_REPORT_AS_RANGE | acknowledge variance but 0.391 is meaningful |
| cv_geo ≤ 0.15 | POLICY_CEILING_NOT_ENV_FLOOR | plateau is a real policy limit; env-side mechanism candidates removed |
| TDS_FAILED at extreme magnitudes | informative — defines stable operating envelope |

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建: `scripts/r106_d4_env_floor.py`, `results/r106_d4_env_floor/`,
`memory/rounds/R106/{plan.md, verdict.md}`, 1 CLM (≥ 0178).

## Cross-references

- [[CLM-0144]] (91-round algo plateau evidence — R106 may reframe it)
- [[CLM-0160]] (on-manifold critic OK)
- [[CLM-0168]] (CLM-0163 retraction, value-horizon refuted)
- [[CLM-0169]] (multi-seed MLP rigor; R85+ candidate list includes D4)
- R84 plan §D4 (this round implements that axis)
- R103 plan (reward shape ablation, in-flight — complementary mechanism test)
