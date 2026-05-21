# R97 verdict — Cross-ckpt action-coordination universalisation (CLM-0170 N=1 → N=6)

**Date**: 2026-05-19
**Status**: _TBD post-W1 (pending r97_cross_ckpt_action_coord/cross_ckpt_aggregate.json)_
**Type**: analysis (cross-ckpt ANDES rollout + R92-W1 axes replication, zero training)
**Wall**: ~5-10 min (6 ckpts × ~30-60s ANDES rollout each + analysis)

## TL;DR

_TBD — fill in after W1 completes_

Pattern: mirror R86 (CLM-0149 N=1 → CLM-0155 N=6) universalisation. R92 CLM-0170
discovered R72_w4 SOTA = bang-bang policy + action saturation 76% on N=1 ckpt.
R97-W1 replicates R92-W1 action coordination analysis on 6 ckpts spanning
3 algo classes (SAC + 5× TD3-LSTM) × multi-seed × multi-round.

## Methodology

`scripts/r97_w1_cross_ckpt_action_coord.py` — for each of N=6 ckpts:
1. Load ckpt via `andes_rl_kundur.agents.checkpoint_loader.load_agents`
2. ANDES rollout 2 scenarios × 50 steps × 4 agents (env_seed=42)
3. Record sota_action per (scen, step, agent)
4. Apply R92-W1 axes: effort distribution, 4×4 corr matrix, saturation
   frequency, ΔM/ΔD specialisation, cross-scenario consistency
5. Per-ckpt flags: max_saturation ≥ 0.50, max\|off-diag corr\| > 0.8,
   ΔD pair \|r\| ≥ 0.9 (lockstep), Kundur 2-area signature (ag0-ag1 dM r>0.8 AND
   ag0-ag2 dM r<-0.8)

Cross-ckpt aggregate: count ckpts hitting each flag, gate UNIVERSALISED if
saturation_high ≥ 5/6 AND lockstep_dD ≥ 4/6.

Schema mirrors R86 N=6 critic forensics for direct comparison.

## Results

### Cross-ckpt summary table

| ckpt_id | sat_max | max\|r\| | dD_lockstep | Kundur_sig |
|---|---|---|---|---|
| _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

### Aggregate

| metric | value | gate threshold |
|---|---|---|
| n_ckpts_saturation_high (≥0.50) | _TBD_ / 6 | ≥ 5/6 |
| n_ckpts_lockstep_dD (≥0.9) | _TBD_ / 6 | ≥ 4/6 |
| n_ckpts_kundur_sig_dM_LS1 | _TBD_ / 6 | ≥ 4/6 |
| median_saturation_across_ckpts | _TBD_ | informational |
| median \|off-diag corr\| | _TBD_ | informational |
| **GATE** | **_TBD_** | UNIVERSALISED / PARTIAL / FAIL |

## Interpretation

_TBD — fill in based on gate outcome:_

- **UNIVERSALISED** path: CLM-0170 is project-level finding, R94+ widen-bound is correct
  R57-R86 plateau fix. Paper writeup: "across 6 SOTA ckpts (SAC + 5 TD3-LSTM × multi-seed),
  uniformly observe bang-bang policy + action saturation X%, plateau ceiling is
  bound-limited."
- **PARTIAL** path: bang-bang is hyper-specific (e.g. only LSTM tau=0.001), SAC differs.
  R94 widen-bound applies narrowly to LSTM family.
- **FAIL** path: R72_w4 finding is single-ckpt artefact, R94 widen-bound hypothesis
  not generalisable.

## Cross-references

- R92 verdict + [CLM-0170](../../claims/CLM-0170.md) — N=1 baseline
- R86 verdict + [CLM-0155](../../claims/CLM-0155.md) — universalisation pattern template
- R84-d2b script — ANDES rollout protocol source
- R94 plan/verdict — falsification test (widen-bound DM_MAX 600→1500), R97 mechanism layer
- Q-0014 — algorithm exploration backlog, R97 might narrow to "action-bound exploration"

## Questions opened (this round)

- _TBD post-W1_

## Questions closed (this round)

- (none) — R97 universalisation/falsification of CLM-0170, not Q closure

## Questions advanced (this round, status unchanged)

- _TBD: Q-0014 priority update if R97 confirms_

## 给 PI 的话

_TBD post-W1_
