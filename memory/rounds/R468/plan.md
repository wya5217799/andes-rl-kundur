---
round: R468
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R468 plan — U7 complete local physical-parameter tensors and lifted maps

**Opened**: 2026-08-21
**Driver**: Execute GPT Pro U7 without duplicating the sealed R444 trajectory bank: complete the missing local tensors, fixed-mode audit, and 30-step additive/bilinear lifts at the R446 equilibrium.
**Parent**: CLM-1380/R444, CLM-1390/R446, CLM-1435/R459; owner-authorized GPT Pro data request imported on 2026-08-21.

## TL;DR

Build full physical-unit derivatives for the eight per-device parameters
`(M1..M4,D1..D4)` on three simultaneous central-difference levels, preserve
all matrices, and combine them with the already sealed 288-trajectory
amplitude ladder.  The normalized action decoder and deterministic law are
piecewise at zero, so a single smooth normalized-action Taylor theorem is not
pre-assumed.

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

- Work class: **evidence**. New root: `results/research_loop/r468_u7_local_taylor` (create-only).
- Nominal point is Object A/R446: four GENCLS devices, `M=400`, `D=100`, 0.2 s sample, fixed Kundur topology and equilibrium.
- Reuse R444 read-only for the zero-action versus zero-bias direct-M/D law amplitude result: 288 complete 30-step trajectories, six geometric amplitudes. No duplicate TDS job is allowed.
- New model jobs: nominal plus `8 parameters x 3 h levels x 2 signs = 49` unique ANDES linearizations. Base steps are 4 physical M units and 1 physical D unit; selected derivative is `h/4`.

### Quantities

- In the fixed nominal gauge quotient, export continuous and sampled tensors
  `N=dA/dq` (8,n,n), `E=dB/dq` (8,n,7), `R=dC/dq` (8,4,n), and
  `S=dD/dq` (8,4,7), where the seven additive inputs are four energy-port
  commands followed by three registered load disturbances.
- Save all three central-difference estimates, Richardson differences,
  equilibrium residuals, name/mode hashes, and independent swing-row formula
  checks.  Also compare direct sampled derivatives with exact ZOH Frechet
  derivatives at sampled parameter directions.
- Build a 30-step differential additive-command map and its complete singular
  spectrum. Build the 30-step bilinear pseudo-input map from all products
  `q_j*x` and `q_j*r` to four frequency outputs; save the complete matrix.
- Re-express every R444 block as `||Delta y_MD||/eps` and
  `||Delta y_MD||/eps^2`; evaluate additive lifted responses at the same six
  geometric levels and save `||Delta y_add||/eps`.

### Hardware and launch

- Formal entry: `scripts/andes_scratch.py scripts/run_r468_u7_local_taylor.py run`.
- Rehearsal command: `scripts/andes_scratch.py scripts/run_r468_u7_local_taylor.py rehearse`; scope: nominal plus one M corner, strict serialization and dimension/mode/residual checks through the formal pre-attempt path.
- Formal preparation: same entry with `prepare`, only after rehearsal and preflight.
- `wsl_python_processes=16`: 15 workers plus one orchestrator; `native_threads_per_process=1`; `host_process_budget=17`; `other_reserved_processes=0`.
- Capacity evidence reuses the R460 measured optimum (15 workers was 50.96% faster than 8) with a fresh memory snapshot. GPU excluded: no CUDA path for ANDES DAE or these modest dense matrices. Linear post-processing may use four native threads after the process pool exits.
- Retry policy: none. Any post-seal pre-attempt failure aborts this round and requires a successor.

## Formal launch contract

- `formal_entry`: `scripts/run_r468_u7_local_taylor.py run`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r468_u7_local_taylor.py rehearse`
- `rehearsal_scope`: two unique linearization points only; no formal output.
- `rehearsal_checks`: authority/source hashes, Linux/installed case, output absence, finite matrices, strict JSON, dimensions, equilibrium residual, mode/name identity.
- `capacity_evidence`: `memory/rounds/R468/capacity_evidence.json`
- `wsl_python_processes`: 16
- `native_threads_per_process`: 1
- `host_process_budget`: 17
- `other_reserved_processes`: 0

## Gate

`TENSOR-VALID` requires every point finite, unchanged names/mode hash,
equilibrium residual <=1e-8, and each material tensor Richardson relative
difference <=1% (near-zero absolute <=1e-9).  The additive map must have
nonzero stable `norm/eps`.  Direct-M/D is called quadratic-leading only from
the R444 measured ladder; because the normalized decoder has unequal one-sided
slopes and the law contains absolute-value branches, the smooth normalized
Taylor statement must be classified `LOCAL-TAYLOR-NOT-APPLICABLE`, even when
the physical-parameter tensors pass.  Any mode/name change, singular solve,
or residual failure also returns `LOCAL-TAYLOR-NOT-APPLICABLE` and blocks a
smooth theorem claim.

### Outcomes

- `PHYSICAL-TENSORS-VALID_NORMALIZED-TAYLOR-NOT-APPLICABLE`: all physical
  tensor/additive gates pass, but the measured nonsmooth normalized interface
  forbids the unqualified smooth-policy theorem.
- `LOCAL-TAYLOR-NOT-APPLICABLE`: any residual, mode, name, convergence,
  Frechet, or additive nondegeneracy gate fails; preserve data and make no
  tensor-valid claim.
- No outcome upgrades the finite R444 ladder to a global asymptotic theorem.

## 资产保护契约

Preserve R444/R446/R459 and all imported GPT material byte-for-byte. Do not
alter environments, controllers, manuscript prose, training, or sealed roots.
Add only the reusable U7 evaluator, one lifecycle adapter, tests, R468
create-only results, report, claim, verdict, and required registrations.

## Cross-references

- CLM-1380: sealed empirical quadratic-leading direct-M/D signed response.
- CLM-1390: zero first-order direct-M/D authority at the frozen equilibrium.
- CLM-1435: shared Object A/Object B model and execution semantics.

## Theory intake

- Algebra retained: bilinear first variation uses physical-parameter
  derivatives of `(A,B,C,D)` and a lifted pseudo-input representation.
- Observable prediction: physical tensors converge on three h levels;
  additive response is first-order and nonzero; R444 direct-M/D response has
  decreasing `norm/eps` and stabilizing `norm/eps^2` trend.
- Qualification tested explicitly: equilibrium residual, fixed names/mode,
  zero first-order authority, normalized decoder one-sided slopes, controller
  zero bias, and nonsmooth branches. No unqualified C2 normalized-policy
  premise is imported.
