---
round: R469
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R469 plan — U8 I/O separation bounds without an invented full-state projector

**Opened**: 2026-08-21
**Driver**: Execute GPT Pro U8 on complete reduced models while refusing an unverified 102-state common/differential projector.
**Parent**: CLM-1180/R405, CLM-1435/R459, CLM-1465/R468; owner-authorized GPT Pro data request imported on 2026-08-21.

## TL;DR

Export physically labelled four-channel input/output projectors, exact 30-step
common-input to differential-output lifts, 0--Nyquist transfer/conditioning,
an effective dynamic-stiffness Schur identity, and homogeneous-to-heterogeneous
scaling.  Do not report `[A,P_x]` or `epsilon_A/B/C` because no verified
full-state symmetry action exists for the asymmetric Kundur network.

## Snapshot at plan-time (oracle as of 2026-08-21)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Evidence identity

- Work class: **evidence**; create-only root `results/research_loop/r469_u8_separation_bound`.
- Profiles: the eight R405 `baseline_m0/baseline_d0` vectors. For each, run
  `alpha in {0,0.25,0.5,1}` with `M=mean(M)+alpha*(M-mean(M))` and likewise D:
  32 unique fixed-equilibrium ANDES linearizations, no reused output root.
- Each point exports the complete joint-input reduced model: four additive
  energy-port commands, three load disturbances, four frequency outputs,
  continuous matrices, exact 0.2-s ZOH matrices, names, gauge, DAE residual,
  and active-mode hash.

### Projectors and bounds

- `q_c=ones(4)/2`; `T_d` is the registered orthonormal three-row differential
  basis. Export `P_u=q_c q_c'`, `Q_u=I-P_u`, `P_y=P_u`, `Q_y=Q_u`, plus basis
  labels. Verify symmetry, idempotence, orthogonality, ranks, and completeness.
- Do **not** export `P_x/Q_x`: 101 quotient states include network and controller
  coordinates without a verified device-permutation representation. Therefore
  `epsilon_A`, `epsilon_B`, and `epsilon_C` are `unavailable`; `epsilon_D` is
  reported only as the directly defined I/O feedthrough cross norm.
- For every point, build the exact 30-step block Toeplitz map from scalar common
  power command to three differential frequency outputs. Verify it by an
  independently coded direct impulse recursion.
- On 1025 points from DC to Nyquist, export `G_dc`, actual norm, resolvent
  condition, and direct-feedthrough cross norm. For nonzero frequency, define
  the exact effective dynamic stiffness `Z_eff(s)=s G_uu(s)^-1`, transform it by
  `[q_c,T_d']`, and export `Z_dd,S_c,z_dc,b_c=1`, lower/upper Schur bounds, and
  exact-block reconstruction error. Near-singular G/Z/Schur points are flagged,
  never inverted silently.
- For each R405 profile, compare `H(alpha)-H(0)` and transfer differences over
  the registered alpha ladder. Export M/D standard deviations and the analytic
  heterogeneity numerator separately; do not equate it with total cross response.

### Hardware and launch

- Formal entry: `scripts/andes_scratch.py scripts/run_r469_u8_separation_bound.py run`.
- Rehearsal: same entry with `rehearse`; two points, full pre-attempt authority,
  source/case/output checks, projector tests, strict serialization, dimensions,
  residual, mode/name, and Toeplitz/direct-impulse equality.
- Prepare: same entry with `prepare`, after preflight and rehearsal.
- Capacity: 15 workers plus one orchestrator, one native thread each; 16 WSL
  Python processes under host budget 17; other reserved processes 0. Reuse the
  R460 measured throughput optimum and capture fresh memory. Post-processing
  uses four numerical threads only after workers exit. GPU excluded because
  ANDES and the small dense frequency solves have no measured CUDA advantage.
- Retry none; post-seal pre-attempt failure requires a successor.

## Formal launch contract

- `formal_entry`: `scripts/run_r469_u8_separation_bound.py run`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r469_u8_separation_bound.py rehearse`
- `rehearsal_scope`: two unique points; no formal root.
- `rehearsal_checks`: authority/hash/runtime/output absence, projector algebra,
  finite matrices, 101-state quotient, residual/mode/name, lift/direct impulse.
- `capacity_evidence`: `memory/rounds/R469/capacity_evidence.json`
- `wsl_python_processes`: 16
- `native_threads_per_process`: 1
- `host_process_budget`: 17
- `other_reserved_processes`: 0

## Gate

### Outcomes

- `IO-BOUND-COMPLETE`: all projector, residual (`<=1e-8`), mode/name,
  Toeplitz, frequency conditioning, and Schur-bound checks pass; report the
  bounded I/O/effective-stiffness result and explicit absence of `P_x`.
- `BOUND-INCOMPLETE`: any actual cross norm exceeds its computed Schur bound
  beyond `1e-8` relative/absolute slack, an unflagged inverse is singular, or
  direct impulse disagrees with the lift beyond `1e-10`.
- `LOCAL-MODE-INVALID`: residual, mode, name, or gauge gate fails.
- No outcome authorizes a universal heterogeneity-to-cross-energy law, a
  full-state commutator number, or a robust bound.

## 资产保护契约

Preserve R405/R459/R468, all paper-cited environments, and imported GPT
material byte-for-byte. Add only the U8 evaluator, execution adapter, tests,
create-only results, report, claim, verdict, and registrations. No training,
controller change, manuscript prose change, or sealed-root rewrite.

## Cross-references

- CLM-1180: R405 profile M/D vectors and bounded homogenization failure.
- CLM-1435: complete shared Object B matrices and execution semantics.
- CLM-1465: physical M/D tensor boundary and nonsmooth-interface qualification.

## Theory intake

- Algebra retained: I/O projector identities, finite Toeplitz lift, effective
  dynamic-stiffness block inverse, and its singular-value upper/lower bounds.
- Observable prediction: actual cross transfer stays inside the pointwise
  Schur bound; heterogeneity-only scaling has a nonzero network-asymmetry
  intercept and needs conditioning to explain magnitude.
- Blocked import: the general commutator-resolvent bound is not evaluated
  numerically without a physically verified full-state projector; no arbitrary
  101-state padding is permitted.
