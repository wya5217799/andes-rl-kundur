---
round: R376
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R376 plan — Gate B feasibility-native deterministic physical gate

**Opened**: 2026-08-12
**Driver**: Execute the first physical comparison of the feasibility-native
successor seam: zero, local-only, and neighbour-message normalized per-VSG
actions through the same feasible-interval map, with the outer VSG-energy-port
projection held to identity on every trajectory, on development and held-out
banks untouched by R374/R375.
**Parent**: CLM-1020 (R375 stop), Gate A contract
(`working/feasibility_native_four_vsg_contract.md`), Gate B contract
(`working/gate_b_deterministic_physical_contract.md`)

## TL;DR

R376 is the prospective Gate B evidence round for the fixed-title line. It
compares three deterministic arms — `zero_feedback`, `local_feasibility_native`,
and four `distributed_feasibility_native_ks<ks>_kc<kc>` candidates — executing
one normalized action per VSG through `FeasibilityNativeVSGActionMap.map_action`
with the energy-port projection as identity guard. All gains, internal
saturation (`0.70`), probe magnitude (`0.25`), bank conditions, endpoints,
thresholds, selection rule, seeds, and stop rules are frozen in the Gate B
contract. Training, retry, gain changes, and random/MARL arms are forbidden.

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
- One VSG-owned active-power-reference port per unit via
  `AndesVSGEnergyPortEnv` and `r272_frozen_bess_contract` (100 MVA system
  base; 36 MW / 28 MWh per device; SOC `[0.20, 0.80]` initial `0.50`).
- Every arm outputs one scalar normalized action per VSG inside `[-1, 1]`
  and maps it through the same `FeasibilityNativeVSGActionMap.map_action`;
  the external projection is identity-only. 0.2 s update, 50 steps per
  trajectory, seed 42.

### Frozen deterministic laws

- `zero_feedback`: all-zero normalized actions.
- `local_feasibility_native`: per-VSG normalized PI
  `u_i = kp_n * e_i + I_i`, `kp_n = 4.0 /Hz`, `ki_n = 0.8 /(Hz*s)`,
  clamp-based integrator anti-windup, internal saturation `0.70`.
- `distributed_feasibility_native_ks<ks>_kc<kc>`: the same local PI driven
  by a dynamic-average common estimate plus a zero-sum Laplacian sync
  channel on the four-node ring, `ks_n in {0.5, 1.0} /Hz`,
  `kc_n in {0.5, 1.0} /s` (four candidates).
- Paired probes are injected in the normalized-action domain in the four
  registered arithmetic modes at magnitude `0.25`; with the `0.70` internal
  bound, `|a_probed| <= 0.95` always, so the identity guard is structural.

### Frozen banks

- Development: probe condition `PQ_Bus15 -0.40`; disturbances
  `PQ_0 +0.55`, `PQ_Bus14 +0.50`. Six arms x 10 records = 60 records.
- Held-out: probe condition `PQ_1 +0.35`; disturbances
  `PQ_Bus14 -0.45`, `PQ_0 -0.65`. Three arms x 10 records = 30 records.
- Every condition is untouched by R374/R375.

### Guards, endpoints, selection, classification

- Per-trajectory hard guards: 50 completed steps, no TDS failure, identity
  at `atol=1e-12` with empty `saturation_reasons` every step, SOC bounds,
  zero-sum differential request, channel reconstruction, zero legacy M/D
  telemetry, finite arrays, correct timing, and full common-plus-three-
  differential action rank across the eight paired probes.
- Endpoints: co-primary probe off-diagonal response energy and normalized
  cross response; disturbance differential-frequency energy and settling;
  no-harm common IAE, worst peak, RoCoF; reported control stress including
  internal headroom fraction and bound-contact counts.
- Development selection and held-out classification use the threshold
  family and precedence of R375 (`0.98 / 0.95 / 1.10 / 1.05 / 1.10`,
  settling band 0.01 Hz), applied to the normalized-action arms.
- Terminal classes: `STOP-UNSAFE-CONTROL`, `STOP-NO-CROSS-DECOUPLING`,
  `STOP-NO-DIFFERENTIAL-BENEFIT`, `STOP-COMMON-MODE-HARM`,
  `STOP-DEVELOPMENT-NO-CANDIDATE`, or `DETERMINISTIC-DECOUPLING-PASS`.
  Only the pass class authorises the next registered Gate C
  (non-learning time-varying headroom); it never authorises training.

### Capacity and launch contract

- Work: 60 development + at most 30 held-out records = at most 4500
  environment steps, serial, one WSL Python process, one native thread per
  numerical library, `other_reserved_processes = 0`.
- Runtime anchor: R374 completed 60 records in 447.5055512560066 s; the
  90-record maximum projection is ~671 s point estimate, ~1007 s at the 1.5
  safety factor. Capacity evidence is written to
  `memory/rounds/R376/capacity_evidence.json` before any seal.
- Rehearsal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r376_gate_b_deterministic.py rehearse`.
- Seal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r376_gate_b_deterministic.py prepare`.
- Sole formal ANDES entry:
  `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r376_gate_b_deterministic.py execute --expected-seal-sha256 <sha256>`.
- Before formal launch: focused tests (Windows + WSL), Ruff, diff check,
  R376 round preflight, experiment-efficiency-gate card, capacity evidence,
  rehearsal, and seal verification must all pass.

## Gate

One question: does the feasibility-native deterministic neighbour controller
clear the frozen physical gate on untouched banks with identity outer
projection on every trajectory?

- `ANALYSIS-INVALID`: contract, identity, provenance, hash, or guard violation.
- `STOP-UNSAFE-CONTROL`: any external projection repairs an action, or any
  hard guard fails on any trajectory.
- `STOP-DEVELOPMENT-NO-CANDIDATE` / `STOP-NO-CROSS-DECOUPLING` /
  `STOP-NO-DIFFERENTIAL-BENEFIT` / `STOP-COMMON-MODE-HARM`: valid analysis
  that fails a registered gate; no held-out (where applicable) and no
  training.
- `DETERMINISTIC-DECOUPLING-PASS`: the selected distributed candidate clears
  every registered held-out criterion with guards intact. This authorises
  only the next registered Gate C; it does not authorise MARL training.

## 资产保护契约

- Protected and immutable: all R364-R375 sources, plans, seals, executions,
  analyses, feeds, claims, hashes; the Gate A action seam
  (`feasibility_native_vsg_action.py`), energy port, V4 environment, and
  R375 frozen classifier (`deterministic_decoupling.py`).
- Allowed additions only: one R376 runner, the Gate B contract
  (`paper/paralleled_vsg_marl/working/gate_b_deterministic_physical_contract.md`),
  a new classifier/analysis module for the normalized-action arms, focused
  tests, R376 round records, the R376 result root, and the required
  claim/feed/navigation records after terminal analysis.
- No gain, saturation bound, probe magnitude, bank condition, endpoint,
  threshold, selection rule, or physical model may change after the seal.
- No overwrite and no formal retry. Every formal artifact is create-only and
  hash-bound.

## Cross-references

- CLM-1020 / R375: terminal stop of the frozen power-reference formulation;
  identity guard discipline and endpoint definitions are reused as design
  donors only.
- Gate A contract: `paper/paralleled_vsg_marl/working/feasibility_native_four_vsg_contract.md`
  (offline action-manifold gate, qualified by focused tests).
- Gate B contract: `paper/paralleled_vsg_marl/working/gate_b_deterministic_physical_contract.md`
  (all frozen values above, sealed byte-for-byte at prepare).
