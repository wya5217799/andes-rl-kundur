---
round: R377
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R377 plan — Gate B-2 high-pass damping deterministic physical gate

**Opened**: 2026-08-12
**Driver**: Execute the registered successor deterministic gate after R376
stopped the Laplacian-sync law family: a high-pass filtered mutual-damping
law whose neighbour messages act only on oscillatory differential motion,
with disturbance-driven differential oscillation as primary endpoints and
probe cross-response as a no-harm ceiling.
**Parent**: CLM-1025 (R376 stop), CLM-1020 (R375 stop), Gate B-2 contract
(`working/gate_b2_deterministic_physical_contract.md`)

## TL;DR

R377 is the prospective Gate B-2 evidence round. It compares
`zero_feedback`, `local_feasibility_native`, and four
`distributed_hp_damping_ks<ks>_kc<kc>_alpha0p6` candidates through the same
feasibility-native map with identity outer projection. The successor law
high-pass filters the Laplacian frequency-difference message so sustained
action-domain probes are attenuated while oscillatory differential motion is
damped. All gains, alpha (0.60), probe magnitude (0.25), internal clip
(0.70), bank conditions, primary/no-harm endpoints, thresholds, selection
rule, seeds, and stop rules are frozen in the Gate B-2 contract. Training,
retry, gain changes, and random/MARL arms are forbidden.

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
- Same VSG-owned power-reference ports and `r272_frozen_bess_contract`
  (100 MVA system base; 36 MW / 28 MWh per device; SOC `[0.20, 0.80]`
  initial `0.50`); same feasibility-native zero-anchored map with the
  identity-only outer projection; 0.2 s update, 50 steps, seed 42.

### Frozen successor law

- `zero_feedback`: all-zero normalized actions.
- `local_feasibility_native`: per-VSG normalized PI
  (`kp_n=4.0 /Hz`, `ki_n=0.8 /(Hz*s)`, clip 0.70), unchanged from R376.
- `distributed_hp_damping_ks<ks>_kc<kc>_alpha0p6`: the R376 dynamic-average
  common channel plus a differential channel
  `u_d = -ks_n * s_i`, where `s_i` is the first-order high-pass state
  (alpha 0.60) of the Laplacian frequency-difference sum. The high-pass
  attenuates the sustained probe-induced component (`1 - alpha` per step)
  while passing oscillatory differential motion. Frozen grid
  `ks_n x kc_n in {0.5, 1.0} x {0.5, 1.0}`.
- Paired probes in the normalized-action domain at magnitude 0.25; with the
  0.70 internal bound, `|a_probed| <= 0.95` always.

### Frozen banks

- Development: probe condition `PQ_0 -0.45`; disturbances `PQ_1 +0.60`,
  `PQ_Bus15 +0.50`. Six arms x 10 records = 60 records.
- Held-out: probe condition `PQ_0 +0.40`; disturbances `PQ_Bus14 -0.55`,
  `PQ_1 -0.70`. Three arms x 10 records = 30 records.
- Every condition is untouched by R374/R375/R376.

### Guards, endpoints, selection, classification

- Per-trajectory hard guards identical to R376: 50 completed steps, no TDS
  failure, identity at `atol=1e-12` with empty saturation reasons every
  step, SOC bounds, zero-sum differential action, channel reconstruction,
  zero legacy M/D telemetry, finite arrays, uniform timing, and full
  common-plus-three-differential action rank across the eight paired probes.
- Primary endpoints: mean differential-frequency energy and mean
  differential settling time (band 0.01 Hz) on the disturbance bank.
- No-harm: common IAE <= 1.05, worst peak and RoCoF <= 1.10, probe
  off-diagonal energy and normalized cross ratio <= 1.10 against baselines.
- Development eligibility against the local arm: differential-energy ratio
  <= 0.98, settling improvement of at least one `dt`, common IAE <= 1.05,
  probe cross no-harm <= 1.10; rank by energy x settling ratio.
- Held-out classification (guard first): `STOP-UNSAFE-CONTROL`,
  `STOP-NO-DIFFERENTIAL-BENEFIT`, `STOP-COMMON-MODE-HARM`,
  `STOP-NO-HARM-EXCEEDED`, or `DETERMINISTIC-DECOUPLING-PASS`; only the pass
  class authorises the next registered Gate C (non-learning time-varying
  headroom); it never authorises training.

### Capacity and launch contract

- Work: 60 development + at most 30 held-out records = at most 4500
  environment steps, serial, one WSL Python process, one native thread per
  numerical library, `other_reserved_processes = 0`.
- Runtime anchor: R374/R375 empirical anchor 60 records / 447.5 s; the
  90-record maximum projection is ~671 s point estimate, ~1007 s at the 1.5
  safety factor. Capacity evidence is written to
  `memory/rounds/R377/capacity_evidence.json` before any seal.
- Rehearsal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r377_gate_b2_deterministic.py rehearse`.
- Seal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r377_gate_b2_deterministic.py prepare`.
- Sole formal ANDES entry:
  `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r377_gate_b2_deterministic.py execute --expected-seal-sha256 <sha256>`.
- Before formal launch: focused tests (Windows + WSL), Ruff, diff check,
  R377 round preflight, experiment-efficiency-gate card, capacity evidence,
  rehearsal, and seal verification must all pass.

## Gate

One question: does the high-pass mutual-damping successor law reduce
disturbance-driven differential oscillation below the local feasibility-
native controller on untouched banks, without exceeding the probe
cross-response no-harm ceiling and with identity outer projection on every
trajectory?

- `ANALYSIS-INVALID`: contract, identity, provenance, hash, or guard violation.
- `STOP-UNSAFE-CONTROL`: any external projection repairs an action, or any
  hard guard fails on any trajectory.
- `STOP-DEVELOPMENT-NO-CANDIDATE` / `STOP-NO-DIFFERENTIAL-BENEFIT` /
  `STOP-COMMON-MODE-HARM` / `STOP-NO-HARM-EXCEEDED`: valid analysis that
  fails a registered gate; no held-out (where applicable) and no training.
- `DETERMINISTIC-DECOUPLING-PASS`: the selected candidate clears every
  registered held-out primary and no-harm criterion with guards intact.
  This authorises only the next registered Gate C; it does not authorise
  MARL training.

## 资产保护契约

- Protected and immutable: all R364-R376 sources, plans, seals, executions,
  analyses, feeds, claims, hashes; the Gate A action seam, energy port, V4
  environment, and all frozen classifiers.
- Allowed additions only: one R377 runner, the Gate B-2 contract
  (`paper/paralleled_vsg_marl/working/gate_b2_deterministic_physical_contract.md`),
  the HP-damping controller, the R377 classifier/analysis module, focused
  tests, R377 round records, the R377 result root, and the required
  claim/feed/navigation records after terminal analysis.
- No gain, saturation bound, probe magnitude, high-pass alpha, bank
  condition, endpoint, threshold, selection rule, or physical model may
  change after the seal.
- No overwrite and no formal retry. Every formal artifact is create-only and
  hash-bound.

## Cross-references

- CLM-1025 / R376: terminal stop of the Laplacian-sync law family; its
  endpoint-机制 mismatch diagnosis motivates the high-pass successor law.
- CLM-1020 / R375: identity-guard discipline and endpoint families reused as
  design donors only.
- Gate B-2 contract: `paper/paralleled_vsg_marl/working/gate_b2_deterministic_physical_contract.md`
  (all frozen values above, sealed byte-for-byte at prepare).
