---
round: R256
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R256 plan — Probe action-bound saturation as RL cum_rf plateau mechanism

**Status**: CLOSED (see verdict.md / CLM-0470)
**Opened**: 2026-05-20
**Driver**: R255 closed-negative on local-vs-global r_f hypothesis
(CLM-0460). Mechanism candidate 1 (action-bound saturation) is the cheapest
of R255's 4 follow-up candidates — 30-min probe on existing trajectories,
no env touch. Tests "RL is action-bound-constrained while droop k=10 demands
larger actions" hypothesis.
**Parent**: CLM-0445 (paper Sec.IV-D contribution-1 Pareto), CLM-0460
(mechanism candidates 1-4), CLM-0175 (R195 widebound regression).

## TL;DR

Probe-first per NOTES_ANDES.md. Read existing trace JSONs for 6 controllers
spanning the cum_rf Pareto frontier (R201 hreg SOTA, R254 phi_f-only,
R246 only-phi_abs, droop k=10, droop k=2, no-control); extract per-step
per-agent `delta_M` / `delta_D`; compute saturation diagnostics relative
to V4 action bounds [-200, +600]; test if RL is bound-limited.

## Snapshot at plan-time (oracle as of 2026-05-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing

## Recently Closed (last 3)

- Q-0008 closed-negative @ R252, by CLM-0415 — Verify paper-metric ranking persists at 500-ep paper convergence horizon
- Q-0021 closed-positive @ R252, by CLM-0231 — V4 env TGOV1 governors u=1.0 in ANDES JSON but R08 Finding 3 says "completely ineffective" — which is true post-R37 refactor?
- Q-0005 closed-partial @ R186, by CLM-0350 — Why does TD3+LSTM seed 50 collapse while seeds 49/51 converge?

## Methodology

**Probe-first; no env / agent / config change.**

1. **Read trace JSONs** for 6 controllers — R201 hreg SOTA, R254 phi_f-only,
   R246 only-phi_abs, droop k=10, droop k=2, no-control.
2. **Extract per-step actions** from `delta_M` and `delta_D` fields
   (per-agent VSG inertia/damping perturbations recorded in trace).
3. **Compute saturation diagnostics**: fraction of (step, agent) with
   |delta| ≥ 95% bound; mean / max magnitude; transient vs steady-state
   split.
4. **Compare RL vs droop**: is best RL bound-constrained while droop k=10
   demands larger actions?

## Gate

| Outcome | Decision |
|---------|----------|
| RL saturation > 5% AND droop demands > RL bound | SUPPORT — bound is bottleneck; R257 candidate = widen bounds |
| RL saturation < 5% AND mean RL action < droop mean | REFUTE direction; pivot to mechanism candidate 2 |
| Mixed | refined probe |

## 资产保护契约

Read-only on all assets. No env / agent / config / paper_grade_axes changes.
Probe script: `scripts/r256_probe_action_bound_saturation.py`. Probe output:
`results/r256_probe_action_bound_saturation.json`.

## Cross-references

- CLM-0445 (R252 — Pareto trade-off)
- CLM-0460 (R255 — mechanism candidates 1-4)
- CLM-0175 (R195 — widebound regression: refutes "naive widen" path)
- `scripts/r255_probe_local_vs_global_rf.py` (template)
- `docs/eng-notes/NOTES_ANDES.md` (probe-first protocol)
