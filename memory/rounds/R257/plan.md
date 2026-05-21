---
round: R257
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R257 plan — Probe action smoothness (anticipation / jitter) as RL cum_rf plateau mechanism

**Status**: ACTIVE
**Opened**: 2026-05-20
**Driver**: R256/CLM-0470 found RL "over-actuates" (mean|dD|≈563 vs droop k=10
mean|dD|=421) with policy-class inductive bias toward max-out. Mechanism
candidate 2 from R255/CLM-0460 (anticipation lack / action jitter) is the
natural follow-up probe: if RL action is NOT only larger-magnitude but ALSO
choppier (high step-to-step change rate), then `LAMBDA_SMOOTH > 0` training
is mechanism-motivated. If RL is just as smooth as droop k=10 but bigger-
magnitude, smoothness penalty won't help and we pivot to magnitude
regularization (CLM-0470 candidate b).
**Parent**: CLM-0470 (R256 — over-actuation), CLM-0445 (Pareto), CLM-0460
(candidates 1-4).

## TL;DR

Probe-first per NOTES_ANDES.md. Same trace JSONs as R256 (R201 hreg SOTA,
R254 phi_f-only, R246 only-phi_abs, droop k=10, droop k=2, no-control).
Extract per-step action change rate; compare RL vs droop "jitter". If RL
is choppier → R258 = LAMBDA_SMOOTH > 0 training motivated. If equal →
R258 candidate switches to direct magnitude penalty.

## Snapshot at plan-time (oracle as of 2026-05-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing

## Recently Closed (last 3)

- Q-0008 closed-negative @ R252, by CLM-0415
- Q-0021 closed-positive @ R252, by CLM-0231
- Q-0005 closed-partial @ R186, by CLM-0350

## Methodology

**Probe-first; no env / agent / config change.**

1. Read trace JSONs for 6 controllers (same set as R256 for cross-reference).
2. Extract per-step action delta: `dAm[t] = delta_M[t] - delta_M[t-1]`,
   `dAd[t] = delta_D[t] - delta_D[t-1]`. Per-agent, per-step.
3. Compute smoothness diagnostics per controller: mean / max / total-
   variation of |dAm|, |dAd|; transient (t<=5s) vs steady (t>=25s) split.
4. Compare RL vs droop: if RL mean|dAd| > 2x droop k=10's, LAMBDA_SMOOTH
   is motivated; else pivot.

## Gate

| Outcome | Decision | Next round |
|---------|----------|------------|
| RL chop > 2x droop k=10 | SUPPORT — LAMBDA_SMOOTH motivated | R258 = LAMBDA_SMOOTH > 0 train (~13 min ANDES WSL) |
| RL chop <= 1.5x droop | REFUTE — magnitude not jitter | R258 = magnitude penalty (-lambda*|a|^2) train |
| 1.5x < RL chop <= 2x droop | borderline | run BOTH R258A and R258B |

## Pre-registered outcomes

| Pre-reg | Interp |
|---------|--------|
| droop k=10 TV_dD << RL TV_dD | droop mechanically smooth; RL chatters |
| droop k=10 TV_dD ~ RL TV_dD | both equal-jitter; magnitude is gap |
| droop k=2 TV_dD < droop k=10 TV_dD | smoother droop also smaller; confound |

## 资产保护契约

Read-only on all assets. No env / agent / config / paper_grade_axes changes.
Probe script: `scripts/r257_probe_action_smoothness.py`. Output:
`results/r257_probe_action_smoothness.json`. ASCII-only (Windows GBK).
`Path(__file__).resolve().parents[1]` for ROOT.

## Cross-references

- CLM-0445 (R252 — Pareto contribution)
- CLM-0460 (R255 — mechanism candidates 1-4)
- CLM-0470 (R256 — over-actuation, motivates this probe)
- CLM-0175 (R195 — widebound regression)
- `scripts/r256_probe_action_bound_saturation.py` (template)
- `src/andes_rl_kundur/env/andes/base_env.py:388-419` (LAMBDA_SMOOTH infra)
- `docs/eng-notes/NOTES_ANDES.md` (probe-first protocol)
