---
round: R87
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R87 plan — Time-resolved on-manifold critic forensics, zero ANDES

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究". CLM-0160 (R84-W3-traj, on-manifold D2b) refuted the
synthetic-obs affine-Q story of CLM-0149/0153/0154 with **overall median**
metrics (advantage +120% of |Q|, argmax_dist 13% of action diagonal).
But the cached `results/r84_d2b_q_landscape_trajectory/per_step.json`
contains 400 individual probes (4 agents × 2 scenarios × 50 steps). Per-step
breakdown was never reported. If critic confidence drops in the transient
disturbance peak (step 5-25 in LS1/LS2) but stays high in steady state,
that's a **phase-dependent** pathology — a different mechanism story than
the W2/W3 off-manifold artefact or the CLM-0160 on-manifold endorsement.
**Parent**: R84 / CLM-0160 (overall on-manifold pass).

## TL;DR

Re-analyse 400 cached on-manifold Q-landscape probes by (scenario, step,
agent). Question: does critic on-manifold confidence vary by trajectory
phase? Threshold for phase-dependent pathology:
- transient (step ≤ 15) advantage_median < 0 OR argmax_dist > 0.5
- AND steady (step ≥ 30) PASS
→ critic competent in steady state but unreliable during disturbance
peak. R87 result becomes mechanism candidate B (vs CLM-0160 mechanism
candidate A "critic is competent everywhere on-manifold").

Zero ANDES, zero training, ~30 min wall. Fully orthogonal to R83 obs aug
(in-flight), R85 classical baseline (in-flight), R86 cross-ckpt synthetic
(reserved by another session — but its premise CLM-0148/0149 is now
superseded by CLM-0160).

## Wave 1 (W1) — Phase-resolved Q-landscape

Inputs: `results/r84_d2b_q_landscape_trajectory/per_step.json` (400 records).

Each record has fields: scenario, step, agent, obs_norm, sota_action,
grad_norm, q_sota_mean, q_rand_mean, q_rand_max, argmax_dist,
q1q2_disagreement, best_random_minus_sota, advantage.

Analysis axes:
1. **Phase split**: step ∈ [0, 5] (impulse), (5, 15] (rising), (15, 30]
   (decaying), (30, 50] (settling). For each phase × scenario × agent,
   report median + P10 / P90 of (advantage, argmax_dist, q1q2_disagree).
2. **Per-agent ranking**: which agent's critic is **least** confident on
   the on-manifold trajectory? Cross-ref against R72_w4 SOTA's per-agent
   action contribution (CLM-0123-equivalent if exists).
3. **Time-series visualization** (4 agents × 2 scen subplots): plot
   `advantage(t)` + `argmax_dist(t)` along the rollout. Flag any t window
   where median advantage < 0 or argmax_dist > 0.5.
4. **Correlation**: corr(obs_norm, advantage), corr(obs_norm, argmax_dist).
   If high obs_norm correlates with low advantage, that's evidence that
   "obs unusual → critic uncertain" — supports R85+ D3 obs sufficiency
   PRIORITY 1 framing.

Output: `results/r87_w1_phase_resolved/{summary.json, advantage_timeseries.png,
per_phase_table.csv}`.

## Gate criteria (R87 closure)

- **A: ALL_PHASES_PASS** (advantage > 0 + argmax_dist < 0.5 in ALL phases ×
  agents × scenarios): CLM-0160 confirmed at fine resolution; critic is
  uniformly competent on-manifold. R88+ priority = D3 obs sufficiency
  (PI brief recommendation).
- **B: TRANSIENT_FAIL_STEADY_PASS** (transient phase advantage < 0 OR
  argmax_dist > 0.5, steady phases PASS): phase-dependent pathology found.
  New mechanism candidate: critic learns the slow / settling regime but
  not the disturbance peak. R88+ should test reward shape during transient,
  or curriculum prioritising transient experience.
- **C: ALL_PHASES_FAIL**: CLM-0160 overall pass was misleading; per-step
  median was driven by long settling tail. Re-evaluate CLM-0160 status.

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建: `scripts/r87_w1_phase_resolved_q_forensics.py`,
`results/r87_w1_phase_resolved/` outputs, `memory/rounds/R87/verdict.md`,
1 CLM (numbered ≥ 0161 to dodge R83/R86 reservations).

## Cross-references

- CLM-0160 (overall on-manifold D2b PASS — R87 stress-tests at finer resolution)
- CLM-0149/0153/0154 (R84 W2/W3 off-manifold mechanism interpretation,
  superseded by CLM-0160; raw measurements still V)
- R83 plan / R85 plan / R86 plan (all in-flight or reserved; R87 doesn't
  touch their resources)
- Q-0018 (closed-negative by CLM-0160 — R87 cannot re-open, but the
  question of "is critic competent **throughout** trajectory phases?" is
  the natural granularity follow-up)
