---
round: R393
state: aborted
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'analysis-invalid by CLM-1110: three instrumentation seams (Model.get
  variable readback, unfrozen 0.2-second horizon, post-init source snapshot)'
superseded_note: null
---
# R393 plan — PPVSM1 two-unit object, stationarity, and spectrum gate

**Opened**: 2026-08-14
**Driver**: R392/CLM-1105 stops the stock REGF2 object (coupled positive-real modes + eight conserved integrator directions). The PI authorizes the external control-design main successor: a projected-passive dual-droop VSM (PPVSM1) on a survey-conformant two-unit diagnostic cell. This round only qualifies the new object at initialization, zero-input stationarity, and spectrum; it opens no authority or controller work.
**Parent**: CLM-1105; Q-0110; route contract "PPVSM1 successor decision"

## TL;DR

Implement a new ANDES device model PPVSM1 that deletes the Psen/Psig/limit-PI
chain, restores the dissipative swing equation with projected P limits, uses a
gradient-flow Q-V outer loop with projected Q limits, keeps the inner
voltage/current PI cascade with a virtual resistor, and drops the PLL from the
main loop. Build a two-unit cell (buses 1-2; StaticGen 3-4 unchanged) and run
one serial arm: power flow, native init, zero-input 0.2-s trajectory, and
equilibrium EIG. Frozen gates: drift <= 2e-4 pu; no eigenvalue with Re > 1e-7;
no root with |lambda| < 1e-6 beyond one allowed network common-angle
degeneracy. A valid pass opens only a signed authority gate.

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0110 [opened R393] Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?

## Recently Closed (last 3)

- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?
- Q-0108 closed-positive @ R391, by CLM-1100 — Does the exact R389 four-REGF2 equilibrium contain a finite, numerically resolved positive-real mode in the ANDES reduced state matrix that reproduces across two independently initialized numerical arms without advancing simulation time?
- Q-0107 closed-negative @ R389, by CLM-1090 — Can four stock REGF2 VSM devices replace the four Kundur source models one-for-one and complete structurally clean native initialization plus a no-exogenous-action short trajectory without residual, convergence, finite-value, or electrical-guard failure?

## Methodology

### Frozen object and bank

- Platform ANDES 2.0.0; unchanged packaged/derived Kundur static case
  (ten-bus, fifteen-line); StaticGen 1, 2 replaced by PPVSM1 at buses 1, 2;
  StaticGen 3, 4 remain static anchors; forbidden models absent; system base
  100 MVA; device rating 900 MVA; no Toggler; no PLL device.
- Frozen PPVSM1 card (device base unless noted): fn=60, w0=2*pi*fn,
  mf=0.15, wdrp=0.033, D_P=1/wdrp, Qdrp=0.045, k_rho=20 (system base),
  rho_rate_max=10, KPv=3, KIv=10, KPi=0.5, KIi=20, Te=0.005, rf=0,
  xf=0.2, Rv=0.05 (system base), Pmax/Pmin=+-1, Qmax/Qmin=+-1,
  dwmax/dwmin=+-75, Sn=900 MVA.
- One ordered serial arm in one process: build, setup, power flow, native
  TDS init/test, equilibrium EIG (no time advance), then one zero-input
  0.2-second TDS.run with the R389 drift ceiling 2e-4 system pu.
- No action, controller, disturbance, reward, training, or PLL in the main
  loop. TDS tolerance 1e-4 (R389 native).

### Frozen model spec (per device)

- eta = INTw - 1; d(delta)/dt = sat(w0*eta, dwmin, dwmax);
  mf*d(INTw)/dt = P^c(eta) - Pe with Pe = vd*Id + vq*Iq;
  P^c(eta) = projection of (P* - D_P*eta) onto [Pmin, Pmax] (system-pu
  values, device-base card converted by u=9).
- rho = ln V; d(rho)/dt = -k_rho*sat(Qe - Q^c(V), +-rho_rate_max);
  V = exp(rho); Q^c(V) = projection of (Q* - (V - V*)/Qdrp) onto
  [Qmin, Qmax]; V* = initial bus voltage magnitude.
- Inner cascade retained: PIvd(vref2 - vd), PIvq(-vq) with vref2 = V;
  PIId, PIIq; udref/uqref feedforward; Te output lags; current equations
  with virtual resistor: 0 = vd + (rf+Rv)*Id - xf*Iq - ud and
  0 = vq + (rf+Rv)*Iq + xf*Id - uq; vd = v*cos(delta - a),
  vq = -v*sin(delta - a); Qe = -vd*Iq + vq*Id.
- Psen/Qsig/Psig/PIplim/PIqlim states do not exist in PPVSM1; the eight
  conserved directions of the stopped object are removed by construction.
- Initialization: delta = a, INTw = 1, V = v, Id = Pref/v, Iq = -Qref/v,
  all PI states consistent, limiters inactive at the operating point.

### Frozen spectrum guards

- Material positive-real: any eigenvalue with Re > 1e-7 =>
  STOP-PPVSM1-POSITIVE-REAL.
- Neutral degeneracy: any root with |lambda| < 1e-6 beyond exactly one
  allowed network common-angle degeneracy => STOP-PPVSM1-NEUTRAL-DEGENERACY.
- All other integrity, residual, finite-value, catalog, and
  no-time-advance guards follow R389-R391.

## Gate

- ANALYSIS-INVALID: contract/schema, provenance, capture, unexpected
  execution, or artifact-integrity defect.
- STOP-PPVSM1-OBJECT-INIT: power flow, TDS init/test, residual, finite-value,
  or zero-input drift failure.
- STOP-PPVSM1-POSITIVE-REAL / STOP-PPVSM1-NEUTRAL-DEGENERACY: frozen spectrum
  guards above.
- PPVSM1-OBJECT-PASS: complete valid pass of every guard; opens only a
  separately registered signed P/Q authority gate.

Exactly one formal bank is permitted. No automatic retry. A pre-seal defect
may be repaired prospectively and then rehearsed/sealed; any post-seal defect
aborts R393 and requires a separately authorized successor.

## Outcomes

Frozen magnitude meanings (no post-hoc interpretation):

- Zero-input drift stays within 2e-4 system pu over 0.2 s -> stationarity
  passes; any breach -> STOP-PPVSM1-OBJECT-INIT.
- Every eigenvalue has Re <= 1e-7 -> no positive-real mode.
- Exactly one root with |lambda| < 1e-6 (the network common-angle reference)
  -> neutral-degeneracy guard passes; more than one -> STOP.
- All guards pass -> PPVSM1-OBJECT-PASS; the reported leading real part and
  smallest nonzero root magnitude are archived for the authority round.

## 资产保护契约

R383--R392 seals, attempts, executions, analyses, manifests, claims, feeds,
diagnoses, audits, and verdicts remain immutable and read/hash-only. R393
adds one new device model, one builder, one classifier, tests,
plan/rehearsal/seal, and one create-only single-arm result root. It changes
no sealed evidence, prior threshold, controller, or learning asset. The
stock REGF2 card and its stopped disposition stay untouched.

## Formal launch contract

- formal_entry: scripts/run_r393_ppvsm1_object_gate.py
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r393_ppvsm1_object_gate.py rehearse
- rehearsal_scope: setup-only construction, two-unit mapping and forbidden-
  model checks, perturbation-free model-card readback, parent-chain
  (R389->R392) hash checks, output-collision checks; no PFlow, TDS, or EIG.
- rehearsal_checks: canonical contract equivalence; R389/R391/R392 closure
  hashes; installed case/source/API identities; structural absence; native
  thread environment; create-only absence; capacity telemetry.
- capacity_evidence: memory/rounds/R393/capacity_evidence.json.
- host_process_budget: 1
- wsl_python_processes: 1
- native_threads_per_process: 1
- other_reserved_processes: 0

One WSL Python formal process runs the single arm; native numerical library
threads are pinned to 1; competing research processes are measured
immediately before seal and required 0.

- seal_command: /home/wya/andes_venv/bin/python scripts/run_r393_ppvsm1_object_gate.py prepare
- seal_path: memory/rounds/R393/formal_seal.json.
- formal_execute_command: from a clean scratch launch directory invoke
  /home/wya/andes_venv/bin/python <repo>/scripts/andes_scratch.py <repo>/scripts/run_r393_ppvsm1_object_gate.py execute --expected-seal-sha256 <sha256>.
- formal_output: create-only results/research_loop/r393_ppvsm1_object_gate.
- completion: one immutable execution, analysis, and manifest.
- retry: none automatically; post-seal defects require a successor.

## Cross-references

- Q-0110
- CLM-1105
- CLM-1100
- CLM-1090
- paper/converter_vsg_pq_decoupling/working/route_contract.md#ppvsm1-successor-decision
- tmp/regf2_control_math_problem.md
