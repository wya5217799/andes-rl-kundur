---
round: R294
state: completed
opened: '2026-08-02'
closed: '2026-08-02'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R294 plan — model-first coupled distributed control synthesis

**Driver**: Stop heuristic architecture iteration and derive the control object
before any further neural training.

**Parent**: Q-0051; CLM-0565, CLM-0580, CLM-0585, CLM-0615.

## TL;DR

Treat full ANDES as truth, compare control-oriented model families, quantify
rather than assume common--differential and fast--slow separation, audit M/D/P
authority, and select a constrained centralized/distributed controller.  No
new neural training is allowed.  Simulation is a required model-validation
gate, not an algorithm search.

## Snapshot at plan-time (oracle as of 2026-08-02)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0049 closed-partial @ R292, by CLM-0675 — Does a neighbour-only distributed edge policy retain reproducible differential-allocation value against a matched centralized vector actor?
- Q-0048 closed-negative @ R291, by CLM-0670 — Does deterministic state-aware smooth handoff provide timing-specific value beyond fixed 3 s and fixed 5 s fast-support schedules?
- Q-0047 closed-partial @ R290, by CLM-0665 — Does genuine network-configuration variation create material small-signal value for topology-conditioned differential-inertia allocation?

## Methodology

1. Recover the exact GENCLS, governor/AVR, ESD1, network, disturbance,
   measurement, action, saturation, and timing equations from source.
2. Form the nonlinear descriptor DAE truth model and four candidate control
   models: equilibrium modal/LTI, descriptor-LPV or trajectory-linearized,
   reduced nonlinear DAE, and graph-local surrogate.
3. Define inertia-weighted common coordinates and an orthonormal differential
   basis.  Retain and measure the cross blocks instead of deleting them.
4. Compute or specify modal/trajectory authority for active power, inertia,
   and damping, including their state-dependent or bilinear input structure.
5. Compare LQR/H-infinity, robust LPV/tube MPC, nonlinear MPC, passivity-based
   distributed control, and cooperative distributed MPC against constraints,
   computational tractability, locality, and stability evidence.
6. Bind the multi-agent object to per-device local dynamics/actions and
   neighbour messages with decentralized execution.  Define a matched
   centralized upper reference without conflating information and architecture.
7. Produce one cited shared research memo and one prospective non-learning
   simulation-validation protocol.  Do not execute that probe until its model
   fidelity metrics, operating-point bank, and decision tree are frozen.

## Gate

- `DESCRIPTOR-LPV-SUFFICIENT`: the model preserves registered modes,
  trajectory sensitivity, constraints, and residual coupling over the domain.
- `NONLINEAR-MODEL-REQUIRED`: LPV error is structurally too large or branch
  changes invalidate the reduction.
- `DECOUPLING-NO-GO`: the proposed coordinate/time-scale decomposition is not
  valid over the declared domain.
- `MULTIAGENT-SEAM-NOT-IDENTIFIED`: the problem still collapses to centralized
  or scalar coordination and cannot support the MARL title.

## Frozen Stage-A execution contract (2026-08-02, before first eigenvalue)

The first eligible validation is local equilibrium/modal/coupling fidelity;
it is not a controller experiment.  The plant is
`AndesMultiVSGEnvV4Storage` with the default Toggler disabled.  Every point
uses all four ESD1 devices and the public ANDES `Model.set` path.

- LPV identification bank: the 16 corners of
  `M scale={0.75,1.25}`, `D scale={0.75,1.25}`,
  `tie k={1,2}`, and `SOCinit={0.3,0.7}`.
- Fixed-LTI anchor: `(M scale,D scale,tie k,SOC)=(1,1,1,0.5)`.
- Held-out bank: eight prospectively named interior/face points declared in
  `scripts/run_r294_model_validation.py`; none may be moved after sealing.
- LPV predictor: four-axis multilinear interpolation of the 16 state-matrix
  corners.  Fixed LTI repeats the anchor matrix at every held-out point.
- Registered mode: 0.2--1.5 Hz, maximum normalized area-participation
  contrast using the four GENROU and four VSG speed states.
- Coordinate response: orthonormal common/differential VSG-speed initial
  conditions, 10 s horizon, 201 samples, with both cross/self ratios retained.
- Pointwise pass: frequency relative error <=5%, damping-ratio absolute error
  <=0.01, participation cosine >=0.90, coordinate-response NRMSE <=0.15,
  and each cross-ratio absolute error <=0.05.
- Hard decoupling is rejected when either full-DAE cross/self ratio exceeds
  0.20; ratios in `(0.05,0.20]` require retaining cross blocks; only ratios
  <=0.05 are eligible for an approximate-decoupling description.
- Every point must pass `PFlow`, `EIG`, `TDS.test_ok`, `exit_code=0`, the TDS
  initialization residual tolerance, finite matrix/spectrum, no eigenvalue
  real part above `1e-7`, registered-mode presence, and eigenvector condition
  number <=`1e12` for the registered mode.  A failed point is retained and
  makes Stage A invalid.

Decision tree: all eight LPV holdouts pass ->
`STAGE-A-DESCRIPTOR-LPV-ELIGIBLE`; otherwise ->
`STAGE-A-NONLINEAR-OR-NARROWER-DOMAIN-REQUIRED`.  This decision cannot by
itself issue the round-level `DESCRIPTOR-LPV-SUFFICIENT` gate because nonlinear
trajectory fidelity and actuator authority remain Stage B/C obligations.

## 资产保护契约

- Preserve R274--R293 plans, seals, checkpoints, traces, results, failures, and
  negative/invalid classifications byte-for-byte.
- R293 is aborted and its partial formal artifacts remain non-evidence.
- Add only R294/Q-0051 state, a shared cited model-selection memo under
  `docs/research/`, and later prospectively sealed model-validation artifacts.
- No paper LaTeX, neural checkpoint, training script, reward, formal endpoint,
  or result interpretation is in scope.

## Cross-references

- CLM-0565: M/D-only equilibrium authority boundary.
- CLM-0580: independent active-power restoration authority.
- CLM-0585: bounded fast common-inertia value.
- CLM-0615: differential inertia changes the inter-area mode but non-monotonically.
