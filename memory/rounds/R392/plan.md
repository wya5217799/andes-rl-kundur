---
round: R392
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R392 plan — one-variable-at-a-time parameter-perturbation mechanism gate

**Opened**: 2026-08-14
**Driver**: R391/CLM-1100 validly locates two reproducible positive-real local modes in the exact initialized four-stock-REGF2 reduced model, but participation is association, not causality. The PI explicitly authorizes a diagnostic successor that perturbs exactly one explicit REGF2 parameter per arm and re-runs the frozen no-time-advance EIG gate to attribute each material root to a concrete parameter or feedback path.
**Parent**: CLM-1100; CLM-1090; Q-0109

## TL;DR

Add one new runner and classifier that build the exact R389/R391 object eight
times serially. The reference arm A0 repeats R391's r389_reference_tol_1e-4
arm and must reproduce its two material roots. Seven perturbation arms change
exactly one parameter each — mf x4 / mf /4 (VSM inertia), Tpm x10 / Tr x10
(sensing and signal chain), KIv x4 / KIv /4 (voltage outer PI), Sn 900->100
MVA (rating scale) — applied after object build and before setup. No arm calls
TDS.run(), applies an action, or trains. A frozen prediction table maps root
movement to mechanism attribution. This diagnoses the stopped object only; it
reopens no authority, controller, or learning work.

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0109 [opened R392] Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?

## Recently Closed (last 3)

- Q-0108 closed-positive @ R391, by CLM-1100 — Does the exact R389 four-REGF2 equilibrium contain a finite, numerically resolved positive-real mode in the ANDES reduced state matrix that reproduces across two independently initialized numerical arms without advancing simulation time?
- Q-0107 closed-negative @ R389, by CLM-1090 — Can four stock REGF2 VSM devices replace the four Kundur source models one-for-one and complete structurally clean native initialization plus a no-exogenous-action short trajectory without residual, convergence, finite-value, or electrical-guard failure?
- Q-0106 closed-negative @ R388, by CLM-1085 — Do one-device-at-a-time signed Pref and Qref steps on the structurally clean four-REGCV1 Kundur object produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure?

## Methodology

### Frozen scientific object and bank

- Preserve the exact R391 chain: ANDES 2.0.0, packaged/derived Kundur static
  cases, ten-bus/fifteen-line connectivity, four stock REGF2 + four PLL2,
  the frozen R389 input card (REGF2_PARAMETER_CARD: mf=0.15, dd=0.11,
  Tpm=0.025, Tr=0.005, KIv=10.0, xf=0.2, wdrp=0.033, Qdrp=0.045, ...),
  900-MVA device rating, 100-MVA system base, and operating point.
- Every arm is built fresh and run serially in one process. No arm calls
  TDS.run(), applies an action, changes a controller, or trains. All arms use
  the R389 native TDS tolerance 1e-4.
- Ordered bank (frozen):
  1. A0 reference — exact R391 r389_reference_tol_1e-4 repeat, no
     perturbation.
  2. H1a mf x4 (0.15 -> 0.60) — VSM inertia (Tint = mf*wdrp).
  3. H1b mf /4 (0.15 -> 0.0375).
  4. H2a Tpm x10 (0.025 -> 0.25) — power-signal lag (Psig/Qsig).
  5. H2b Tr x10 (0.005 -> 0.05) — transducer lag (Psen/Qsen).
  6. H3a KIv x4 (10 -> 40) — voltage outer PI integrator (PIvd/PIvq).
  7. H3b KIv /4 (10 -> 2.5).
  8. H4 Sn 900 -> 100 MVA — rating scale (device base conversion).

### Perturbation mechanics

- After build_regf2_static_kundur_object and before system.setup(), alter the
  named NumParam on all four REGF2 devices; no card edit, no source edit.
- Record the perturbation spec and the exact four-device readback; any
  readback mismatch with the expected value is an arm integrity defect.
- The A0 arm alters nothing and must reproduce R391's sealed leading root
  46.41533383454654 s^-1 and second root 4.606789511264594 s^-1 (CLM-1100)
  with relative deviation < 1e-6; otherwise the bank is uninterpretable.

### Frozen attribution table

Material root = eigenvalue with Re > 1e-6 (R391's near-zero region excluded
for the attribution analysis; the full spectrum is always archived).
Movement = |Re(arm) - Re(A0)| / |Re(A0)| > 0.10, or a change in the material
positive-real root count.

- H1 prediction: H1a and H1b both move lambda1 -> VSM inertia carries lambda1.
- H2 prediction: H2a and H2b both move lambda1 -> sensing/signal chain carries
  lambda1.
- H3 prediction: H3a and H3b both move lambda2 while neither moves lambda1 ->
  voltage outer PI carries lambda2.
- H4 prediction: the Sn arm moves both lambda1 and lambda2 -> rating scale
  carries both.
- Multiple supported families -> MECHANISM-MIXED with the supported set
  listed. No arm moves any material root -> MECHANISM-NONE-ISOLATED.

### Per-arm guards (identical to R391)

Source identity, no-time-advance equilibrium snapshot (t exactly 0.0 before
and after EIG, unchanged x/y/z), complete residual diagnostics with zero bad
rows and no clamps, finite DAE/Jacobian/state matrix, eigenpair backward
error, leading-eigenvector conditioning, catalog/name uniqueness, and the
R391 corrected dense sparse adapter.

## Outcomes

Frozen magnitude meanings (no post-hoc interpretation):

- A0 reproduces both R391 roots within 1e-6 relative deviation and every
  guard passes -> bank interpretable; any A0 failure -> platform STOP.
- A perturbation arm moves a material root by >10% relative (or changes the
  material positive-real count) -> that arm family carries that root per the
  frozen prediction table.
- Exactly one family matches its prediction -> MECHANISM-<family>;
  several -> MECHANISM-MIXED; none but movements exist ->
  MECHANISM-UNPREDICTED; no movement anywhere -> MECHANISM-NONE-ISOLATED.
- An arm that fails power flow/init/finite guard is a typed ARM-STOP-INIT
  and contributes no attribution; the bank continues.

## Gate

- ANALYSIS-INVALID: contract/schema, provenance, perturbation readback,
  capture, unexpected execution, or artifact-integrity defect.
- STOP-REGF2-PERTURBATION-PLATFORM: A0 fails any guard or fails to reproduce
  R391's two roots within the frozen tolerance.
- ARM-STOP-INIT: a perturbation arm fails power flow, TDS initialization, or
  a finite guard — typed per arm; the bank continues and the failed arm
  contributes no attribution.
- MECHANISM-VSM-INERTIA / MECHANISM-SENSING-CHAIN /
  MECHANISM-VOLTAGE-OUTER-PI / MECHANISM-RATING-SCALE / MECHANISM-MIXED /
  MECHANISM-NONE-ISOLATED / MECHANISM-UNPREDICTED: final attribution per
  the frozen table (UNPREDICTED = movements observed but none match the
  frozen prediction table).

Exactly one formal bank is permitted. No automatic retry. A pre-seal defect
may be repaired prospectively and then rehearsed/sealed; any post-seal defect
aborts R392 and requires a separately authorized successor.

## 资产保护契约

R383--R391 seals, attempts, executions, analyses, manifests, claims, feeds,
diagnoses, audits, and verdicts remain immutable and read/hash-only. R392
adds one runner, one classifier, tests, plan/rehearsal/seal, and one
create-only eight-arm result root. It changes no Kundur topology, static
case, prior threshold, sealed evidence, controller, or learning asset. The
baseline REGF2 card is untouched; perturbations are runtime alters inside the
new gate only. The stock-REGF2 route remains stopped before authority;
attribution is parameter sensitivity, not a physical-device causality,
stability, safety, or repair claim.

## Formal launch contract

- formal_entry: scripts/run_r392_regf2_loop_perturbation_gate.py
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r392_regf2_loop_perturbation_gate.py rehearse
- rehearsal_scope: setup-only construction, perturbation-injection canary
  (alter + exact readback on a constructed system), parent-chain
  R389->R390->R391 hash checks, installed case/source/API identity,
  output-collision checks, elapsed/resource capture; no PFlow, TDS
  initialization, EIG, or trajectory.
- rehearsal_checks: canonical science-equivalence contract; complete
  R389/R390/R391 seal-to-manifest chains and closure hashes; installed
  case/source/API identities; real sparse-adapter conversion; exact
  perturbation readback; structural absence; native thread environment;
  create-only absence; capacity and competing-process telemetry.
- capacity_evidence: memory/rounds/R392/capacity_evidence.json.
- host_process_budget: 1
- wsl_python_processes: 1
- native_threads_per_process: 1
- other_reserved_processes: 0

One WSL Python formal process runs all eight arms serially; native numerical
library threads are pinned to 1 (OpenMP, OpenBLAS, MKL, NumExpr); competing
research processes are measured immediately before seal and required 0.
- seal_command: /home/wya/andes_venv/bin/python scripts/run_r392_regf2_loop_perturbation_gate.py prepare
- seal_path: memory/rounds/R392/formal_seal.json.
- formal_execute_command: from a clean scratch launch directory invoke
  /home/wya/andes_venv/bin/python <repo>/scripts/andes_scratch.py <repo>/scripts/run_r392_regf2_loop_perturbation_gate.py execute --expected-seal-sha256 <sha256>.
- formal_output: create-only results/research_loop/r392_regf2_loop_perturbation_gate.
- completion: one immutable eight-arm execution, analysis, and manifest.
- monitoring: inspect once at the rehearsal-derived ETA or terminal artifact.
- retry: none automatically; post-seal defects require a successor.

## Cross-references

- Q-0109
- CLM-1100
- CLM-1090
- CLM-1095
- paper/converter_vsg_pq_decoupling/working/R391_diagnosis.md
- paper/converter_vsg_pq_decoupling/working/R389_diagnosis.md
- paper/converter_vsg_pq_decoupling/reports/R391.md
- paper/converter_vsg_pq_decoupling/working/route_contract.md
