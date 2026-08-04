---
round: R306
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R306 plan — physical-60-Hz model-first Stage-0 seam

**Opened**: 2026-08-03
**Driver**: Q-0062; the model-first line requires an implementation-faithful
plant and telemetry seam before any predictor, controller, or learning gate.
**Parent**: `paper/decoupling_marl_model_first/working/model_contract.md`;
ADR-0006; CLM-0735 is background only and supplies no endpoint.

## TL;DR

Use TDD to add a separate physical-60-Hz model-first execution path and exact
public math/telemetry seams, then run exactly one five-step no-disturbance
Stage-0 ANDES canary.  Stop fail-closed on any guard.  Stage 1, controller
comparison, a broad bank, neural residuals, and training are not authorized.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0062 [opened R306] Can a separate physical-60-Hz model-first ANDES execution seam pass the frozen Stage-0 plant, coordinate, actuator, and telemetry invariants without changing legacy V4 semantics?

## Recently Closed (last 3)

- Q-0061 closed-negative @ R305, by CLM-0735 — Do stable network configurations create locally observable topology-information value for genuine zero-sum VSG vector-inertia coordination?
- Q-0060 closed-positive @ R303, by CLM-0725 — Does heterogeneous BESS headroom make independent projection leak a zero-sum differential residual into the common-power coordinate?
- Q-0059 closed-partial @ R302, by CLM-0720 — Can architecture-aware EVAL-v2 audit genuine vector distributed traces, and does current evidence justify neural distributed-agent training beyond 2Kv?

## Research-Supervisor route card

- Academic goal: establish an executable plant/model seam capable of testing
  the manuscript's frozen sampled-DAE equations without interpreting control
  performance.
- Scientific acceptance: physical 60 Hz; coherent GENCLS device/system-base
  conversion and actual-array readback; exact invertible inertia-weighted
  coordinates with retained cross blocks; exact source-positive action
  incidence; full ESD1 request/command/internal/actual telemetry and guards;
  G4 retained; Line_8 toggler disabled; every Stage-0 gate valid.
- Engineering blocker: legacy V4 intentionally preserves incompatible
  historical 50-Hz semantics and contains mixed-base/direct-write seams.
- Authority and write scope: Q-0062/R306 may add reusable code under
  `src/andes_rl_kundur/`, focused tests, one stable Stage-0 adapter, and R306
  create-only artifacts plus the selected manuscript navigation.  It may not
  change V4, base_env, older rounds/results, controllers, trainers, or another
  manuscript line.
- Return gate: a sealed Stage-0 PASS/INVALID record with measured provenance.
  Ask Matt returns engineering evidence here; Research Supervisor alone owns
  the scientific verdict and keeps Stage 1/training blocked.

## TDD public seams

1. A model-first configuration/factory seam owns physical-frequency and plant
   invariants; legacy V4 behavior is a regression boundary.
2. Pure public math seams own GENCLS base conversion, the weighted coordinate
   transform/inverse/block reconstruction, and edge-to-node active-power map.
3. The environment step/info seam exposes requested, externally commanded,
   internal/limited, and achieved actuator values plus independent M/D
   readbacks and graph/topology provenance.
4. A stable Stage-0 adapter emits a machine-readable guarded report.  Tests
   target these seams only, use realistic values, and do not mock internals.

Each vertical slice must fail first for the missing behavior, then pass with
the smallest implementation.  One deliberate failure per guard family is
required before the live canary.

## Methodology

### Slice A — pure model contract

- Freeze controlled indices and the action path `(0,1),(1,2),(2,3)` with
  source-positive, target-negative incidence.
- Convert GENCLS input `M/D` from device base to live system base using
  `Sn/Ssys`; for four 200-MVA devices on 100-MVA system base, device
  `M/D=200/100` must read back as system arrays `400/200`.
- Construct the exact inertia-weighted common coordinate and a full-rank
  differential complement, expose inverse/reconstruction, and transform every
  registered linear block without deleting measured common/differential cross
  terms.

### Slice B — separate execution seam

- Add a new model-first class/config rather than changing V4.  Freeze physical
  frequency at the ANDES uniform nominal 60 Hz, `zero_g4_inertia=false`, no
  communication failures, deterministic reset, and no Line_8 toggle.
- Apply M/D at one declared layer only and read actual values independently
  from live `GENCLS.M/D.v`; a zero action must not cause a base jump.
- Expose ESD1 requested power, external command after feasibility projection,
  internal/limited reference, achieved active power, SOC, current/limit state,
  and guard flags.  Missing required telemetry is invalid, never inferred as
  zero.

### Slice C — Stage-0 adapter and live canary

- Fresh system, PFlow, then 0.5 s no-disturbance TDS initialization.
- Execute five zero M/D and zero ESD-power commands of exactly 0.2 s each; do
  not edit PQ loads.
- Evaluate only the pre-registered validity and zero-input invariants.  No
  frequency-performance comparison or outcome-dependent threshold change is
  permitted.

## Comparison-identifiability gate

The later SN-J/SN-N/MA-J/MA-N factorial is `QUALIFY`, not frozen for execution:
its shared physical chain and estimand can in principle separate information
locality from network factorization, but only after R306 establishes one
identical action/readback path.  R306 itself compares no controller arms and
identifies no architecture, information, or efficacy effect.

## Gate

Stage-0 is `PASS` only if all structural and live guards pass: five time
increments equal `0.2 +/- 1e-9 s`; equilibrium DAE residual `<=1e-8`; all four
actual controlled system-base `M/D=400/200 +/-1e-10`; requested, commanded,
internal, and achieved active power satisfy their registered zero tolerances;
SOC drift and required current/limiter telemetry pass; all values are finite;
the electrical, communication, action, and disturbance graph/index identities
match the seal; G4 remains in service with nonzero inertia; and Line_8 remains
in service.  Any missing field, incomplete artifact, hash/provenance mismatch,
or failed guard yields `INVALID-STAGE0` and stops immediately.

`PASS` closes only the implementation-validity question and may motivate a
separate prospective Stage-1 round.  It is not controller efficacy, safety,
decoupling success, distributed-agent value, topology generalization, or
training authority.

## 资产保护契约

- Immutable/read-only: `base_env.py`, `andes_vsg_env_v4.py`, historical V4
  semantics, existing claims/rounds/results/seals/checkpoints, ICEMS and SCI
  manuscript lines.
- Additive writes only: new model-first source modules, focused tests, one R306
  stable adapter, `memory/questions/Q-0062.md`, R306 plan/seal/results/feed/
  claim/verdict, programme state, and model-first line navigation.
- Result artifacts are create-only and source-hash bound.  No broad bank,
  Stage 1, controller implementation, or training may begin in R306.

## Cross-references

- Q-0062; ADR-0006.
- `paper/decoupling_marl_model_first/working/model_contract.md` sections
  `equation-to-implementation-reconciliation` and
  `stage-0-and-stage-1-non-learning-probe-contract`.
