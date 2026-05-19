---
round: R102
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R102 plan — Magnitude-PI variant + TGOV1 ablation (Q-0023 + Q-0021)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: R85 closed (PI sign-bug discovery, magnitude-symmetric VSG control finding) + R89 closed (TGOV1 u=1.0 in JSON vs R08 V3 "ineffective" 表面 conflict). Two Qs deferred to R102: Q-0023 magnitude-PI retry + Q-0021 TGOV1 ablation. Both need ANDES WSL TDS, both small (<~30 min). Bundle into single round to amortise ANDES session init (~30s) + share no_control cache.
**Parent**: CLM-0184/0185/0186 (R85 droop OK + naive-PI fail + aggregate); CLM-0173 (R89 audit aggregate).

## TL;DR

Two waves, both V4 paper-faithful Kundur (LS1+LS2, seed=42, steps=150),
both 11-axis paper_grade_axes geo. Wave W1 = magnitude-PI Kp grid (~15 min);
Wave W2 = TGOV1 u=1 vs u=0 ablation with zero-action (~10 min). Reuse R85
no_control cache. Single WSL python session bundles both. ~25 min wall.

## W1: Magnitude-PI variant (Q-0023)

Control law:
```
err_i = obs[i][1]            # local normalized Δω
|err|_i = abs(err_i)
ΔM_norm[i] = clip(Kp_M * |err|_i, 0, 1)    # always add inertia
ΔD_norm[i] = clip(Kp_D * |err|_i, 0, 1)    # always add damping
```
(Optional Ki on |∫|err|| if budget allows; first pass P-only.)

Grid: Kp_M × Kp_D ∈ {0.5, 1.0, 2.0, 5.0} × {0.5, 1.0, 2.0, 5.0} = 16 combo
× 2 scen = 32 eval. Following R85 finding that droop K=2 is sweet spot,
expect best around Kp_M, Kp_D ∈ [1, 5].

**Gates**:
- best magnitude-PI geo ≥ 0.30 → 1-input PI breaks droop ceiling; RL gap smaller (paper-narrative weaker)
- ∈ [0.18, 0.30] → matches droop (0.197); 1-input magnitude controllers all ceiling at half-SOTA; **RL advantage from neighbor info / nonlinearity**
- < 0.18 → magnitude-PI also fails; integral wind-up or saturation; PI paradigm itself not fit (Q-0023 closed-negative)

## W2: TGOV1 ablation (Q-0021)

Two zero-action eval (`zero_action_fn`) × 2 scen, with V4 env modified at
runtime to toggle TGOV1.u:
- **u=1 (default)**: TGOV1 governors active, R=0.05 droop
- **u=0**: all 4 governors disabled (`ss.TGOV1.set("u", g, 0.0, attr="v")`
  after setup, before reset's first ANDES init)

Compare per-scenario max_df + cum_rf:
- If diff < 1% → TGOV1 silently DAE-inactive in V4 (R08 V3 finding extends to V4)
- If diff ≥ 5% → TGOV1 truly active, contributes effective damping (Q-0021 closed-positive)
- ∈ [1%, 5%] → partial wiring; borderline; needs longer scenario probe

## Bundled script

`scripts/r102_magnitude_pi_plus_tgov1.py`:
- Reuses R85 `_no_control_cache` (already exists at
  `results/r85_classical_baseline/_no_control_cache/no_control_*.json`)
- W1 + W2 in sequence, both write to `results/r102_*/`

**Wall budget**: 32 W1 evals + 2 W2 cache + 4 W2 evals = ~38 ANDES eval calls × ~25s each = ~16 min + overhead = ~25 min total.

## Resource conflict gate

- R83 W3 (training, ~30 min in) may still be running — share WSL ANDES slot (max 3). R102 brings total to 2 if R83 ongoing, 1 if done. Safe.
- R86/R87/R88/R90-R101 are mostly zero-ANDES forensics. No WSL conflict.
- R102 outputs to NEW `results/r102_*/` — no overlap.

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py / 任何 R57+ ckpt / R85 outputs / 任何已有 test.

新建: `scripts/r102_magnitude_pi_plus_tgov1.py`, `results/r102_*/` 输出 dir,
`memory/rounds/R102/{plan.md, verdict.md}`, 2-3 CLM-NEW claims.

## Cross-references

- R85 verdict + CLM-0184/0185/0186 (droop best, naive PI fail, aggregate)
- R89 verdict + CLM-0171/0172/0173 (R09 audit, F4 TGOV1 NEEDS VERIFICATION)
- Q-0021 (TGOV1 ablation, R89-opened)
- Q-0023 (magnitude-PI retry, R85-opened)
- paper §IV-C (DDIC > classical, RL > no_ctrl claim)
