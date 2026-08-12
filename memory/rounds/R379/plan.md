---
round: R379
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds:
- R378
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R379 plan — Gate B-3 low-corner high-pass damping gate

**Opened**: 2026-08-12
**Driver**: Execute the registered successor deterministic gate after R378
stopped the alpha-0.60 high-pass family: the same damping structure with the
corner frequency moved below the measured 0.4 Hz dominant differential
oscillation mode (alpha 0.90, corner ~0.084 Hz), justified by spectral
diagnosis of the immutable R378 held-out records.
**Parent**: CLM-1035 (R378 stop), CLM-1030 (R377 stop), CLM-1025 (R376 stop),
Gate B-3 contract (`working/gate_b3_deterministic_physical_contract.md`)

## TL;DR

R379 is the prospective Gate B-3 evidence round. Spectral analysis of the
R378 held-out records shows all differential modes oscillate at ~0.4 Hz,
while the R378 high-pass pole (alpha 0.60) put the corner at ~0.41 Hz,
exactly on the mode; the filter therefore cut the very oscillation it should
damp (explaining 0.962x vs 0.95 threshold) while correctly suppressing the
DC probe (explaining 0.79x cross-response). R379 freezes alpha 0.90 (corner
~0.084 Hz, ~4.8x below the mode) and re-runs the same feasibility-native
comparison structure. Training, retry, gain changes, and random/MARL arms
are forbidden.

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

### Registered scientific object

- Four VSG energy units (`VSG_1..VSG_4` at buses `12, 16, 14, 15`) on the
  modified-Kundur V4 topology, legacy M/D action path pinned to zero.
- Same VSG-owned power-reference ports, `r272_frozen_bess_contract`,
  feasibility-native zero-anchored map, identity-only outer projection;
  0.2 s update, 50 steps, seed 42.

### Frozen successor law

- `zero_feedback`: all-zero normalized actions.
- `local_feasibility_native`: per-VSG normalized PI (`kp_n=4.0 /Hz`,
  `ki_n=0.8 /(Hz*s)`, clip 0.70), unchanged.
- `distributed_lowhp_damping_ks<ks>_kc<kc>_alpha0p9`: R378 dynamic-average
  common channel plus first-order high-pass mutual damping on the Laplacian
  frequency-difference sum with frozen `alpha = 0.90` (corner ~0.084 Hz,
  ~4.8x below the measured 0.4 Hz mode). Frozen grid
  `ks_n x kc_n in {0.5, 1.0} x {0.5, 1.0}`.
- Paired probes in the action domain at magnitude 0.25; `|a_probed| <= 0.95`.

### Frozen banks

- Development: probe `PQ_Bus15 -0.45`; disturbances `PQ_1 +0.65`,
  `PQ_Bus14 -0.55`. Six arms x 10 records = 60 records.
- Held-out: probe `PQ_0 -0.40`; disturbances `PQ_0 +0.60`,
  `PQ_Bus15 +0.55`. Three arms x 10 records = 30 records.
- Every condition untouched by R374-R378.

### Guards, endpoints, selection, classification

- Hard guards identical to R376-R378 (identity, SOC, zero-sum, channel
  reconstruction, M/D zero, timing, rank).
- Primary: mean differential-frequency energy and settling (band 0.01 Hz).
- No-harm: common IAE <= 1.05, peak/RoCoF <= 1.10, probe cross <= 1.10.
- Development: diff-energy ratio <= 0.98, settling no worse than local,
  common IAE <= 1.05, probe cross <= 1.10; rank by energy x settling.
- Held-out: diff-energy ratio <= 0.95 vs both baselines, single condition
  <= 1.10, settling no worse than local; classes include
  `STOP-NO-DIFFERENTIAL-BENEFIT`, `STOP-NO-HARM-EXCEEDED`, and
  `DETERMINISTIC-DECOUPLING-PASS` (pass authorises only Gate C).

### Capacity and launch contract

- 60 development + at most 30 held-out records, serial, one WSL Python
  process, one native thread, `other_reserved_processes = 0`.
- Anchor: R377 60 records / 449.2 s; 90-record projection ~674 s point,
  ~1011 s at 1.5x. Capacity evidence to `memory/rounds/R379/capacity_evidence.json`.
- Rehearsal: `python scripts/run_r379_gate_b3_deterministic.py rehearse`;
  seal: `prepare`; sole formal entry: `scripts/andes_scratch.py ... execute
  --expected-seal-sha256 <sha256>`.

## Gate

One question: with the corner moved below the measured 0.4 Hz mode, does the
low-corner high-pass damping law reduce disturbance-driven differential
oscillation below the local feasibility-native controller on untouched banks,
without exceeding the probe cross-response no-harm ceiling, with identity
outer projection on every trajectory?

- `ANALYSIS-INVALID`, `STOP-UNSAFE-CONTROL`,
  `STOP-DEVELOPMENT-NO-CANDIDATE`, `STOP-NO-DIFFERENTIAL-BENEFIT`,
  `STOP-COMMON-MODE-HARM`, `STOP-NO-HARM-EXCEEDED`: valid terminal stops;
  no training.
- `DETERMINISTIC-DECOUPLING-PASS`: authorises only the next registered Gate
  C (non-learning time-varying headroom); never training. If this spectral-
  tuned law also fails the 0.95 primary threshold, R376-R379 jointly support
  the registered no-differential-benefit conclusion for this
  topology/action domain.

## 资产保护契约

- Protected and immutable: all R364-R378 sources, plans, seals, executions,
  analyses, feeds, claims, hashes; R376-R378 development records are design
  donors only.
- Allowed additions only: one R379 runner, the Gate B-3 contract, the
  low-corner candidate ids, the R379 classifier, focused tests, R379 round
  records, the R379 result root, and required claim/feed/navigation records.
- No gain, clip, probe magnitude, alpha, bank, endpoint, threshold,
  selection rule, or physical model may change after the seal.
- No overwrite and no formal retry.

## Cross-references

- CLM-1035 / R378: held-out stop at 0.962x vs 0.95 threshold; spectral
  diagnosis of the corner-on-mode mismatch is the successor justification.
- CLM-1030 / R377: settling-floor rule correction precedent.
- CLM-1025 / R376: Laplacian-sync family stop.
- Gate B-3 contract: `paper/paralleled_vsg_marl/working/gate_b3_deterministic_physical_contract.md`.
