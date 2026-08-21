---
round: R391
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R391 plan — integrity-corrected equilibrium and reduced-spectrum gate

**Opened**: 2026-08-14
**Driver**: R390's sole sealed attempt is analysis-invalid because its Jacobian finite guard cannot convert the installed ANDES sparse-matrix type and its state-name validator confuses configured object indices with ANDES display ordinals; repair only those two evidence seams without changing the scientific bank.
**Parent**: CLM-1095; Q-0108

## TL;DR

Repeat R390's exact two fresh, no-time-advance equilibrium/EIG arms under a new
seal and create-only root. Change only the Jacobian conversion adapter and the
state-name evidence validator. All topology, device, parameter, operating-
point, tolerance, spectral, numerical, and stopping thresholds remain exactly
R390's. R390 remains immutable and cannot be reclassified or retried.

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0108 [opened R390] Does the exact R389 four-REGF2 equilibrium contain a finite, numerically resolved positive-real mode in the ANDES reduced state matrix that reproduces across two independently initialized numerical arms without advancing simulation time?

## Recently Closed (last 3)

- Q-0107 closed-negative @ R389, by CLM-1090 — Can four stock REGF2 VSM devices replace the four Kundur source models one-for-one and complete structurally clean native initialization plus a no-exogenous-action short trajectory without residual, convergence, finite-value, or electrical-guard failure?
- Q-0106 closed-negative @ R388, by CLM-1085 — Do one-device-at-a-time signed Pref and Qref steps on the structurally clean four-REGCV1 Kundur object produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure?
- Q-0105 closed-positive @ R386, by CLM-1075 — Can the same four-device REGCV1 card pass native initialization and a zero-input short TDS when the unchanged packaged Kundur static tables are reconstructed with no legacy synchronous-machine, governor, or exciter records?

## Methodology

### Frozen scientific object and bank

- Preserve the exact R390 contract for ANDES 2.0.0, installed source/case
  hashes, R389-derived ten-bus/fifteen-line Kundur object, four stock REGF2 and
  four linked PLL2 objects, parameter cards, ratings, references, and static
  operating point.
- Preserve the ordered arms `r389_reference_tol_1e-4` and
  `sensitivity_tol_1e-6`, each built fresh and executed serially inside one
  process. No arm calls `TDS.run()`, applies an action, changes a controller or
  model parameter, or trains a model.
- Preserve every equilibrium, provenance, residual, finite-value, exact
  x/y/z/time, catalog, spectrum-reconciliation, eigenpair-error, conditioning,
  cross-arm reproduction, near-zero, and positive-real threshold from R390.

### Evidence correction 1 — installed sparse Jacobians

Convert each ANDES `fx/fy/gx/gy` value using the already established
`vsg_energy_port_source_adapter` rule: attempt a direct finite two-dimensional
NumPy conversion; on installed sparse-type conversion failure, convert first
through `andes.shared.matrix`. Any dimensional, nonfinite, or conversion defect
still fails closed. Bind the installed `andes.shared` source, `kvxopt.base`
binary, and `kvxopt` version. Add a regression using a real
`kvxopt.base.spmatrix` in the registered WSL environment and a unit fake that
exercises the fallback.

### Evidence correction 2 — exact state-name semantics

Continue to prove model-variable address -> `dae.x_name[address]` -> unique
`EIG.x_name` without using a raw DAE address as a reduced eigenvector row. For
the exact four-device object, require each original display name to be exactly
`<variable> <model> <device-ordinal>` where the ordinal is derived from the
frozen configured index suffix, for example configured `PLL2_1` maps to
`PI_xi PLL2 1`. Do not require configured text `PLL2_1` inside the ANDES display
name. Retain all folded/eliminated/address/Tf/catalog checks and add forged
ordinal/address/name tests.

### Independent correction classifier

Validate the raw R391 correction contract and original ANDES-style binding
records first. Only after that validation, construct a detached name-normalized
copy for reuse of R390's already reviewed non-name integrity and scientific
classifier. The normalization changes no matrix value, index, catalog length,
threshold, or outcome and is never archived as raw evidence. Any correction-
schema or raw-binding defect is `ANALYSIS-INVALID`.

## Gate

- `ANALYSIS-INVALID`: correction contract/schema, raw ANDES binding,
  provenance, evidence capture, unexpected execution, or artifact-integrity
  defect.
- `STOP-REGF2-EQUILIBRIUM-INVALID`: complete valid evidence fails power flow,
  initialization/test, residual, finite-value, or exact no-advance guards.
- `STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED`: valid equilibria fail the
  frozen spectrum, eigenpair, conditioning, or cross-arm reproduction guards.
- `STOP-REGF2-POSITIVE-REAL-GUARD`: a valid reproducible finite mode has
  `Re(lambda) > 1e-7`. This supports only an exact-model local growing-direction
  diagnostic, not physical instability, causality, safety, or deployment.
- `REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE`: both valid arms contain no mode
  above the frozen threshold. This does not repair R389 or prove stability.

Exactly one formal bank is permitted. There is no automatic retry. A pre-seal
defect may be repaired prospectively and then rehearsed/sealed. Any post-seal
defect aborts R391 and requires another separately authorized successor.

## 资产保护契约

R389 and R390 seals, attempts, executions, analyses, manifests, claims, feeds,
diagnoses, audits, and verdicts remain immutable and read/hash-only. R391 adds
only one correction classifier, one stable runner adapter, correction tests,
one plan/rehearsal/seal, and one create-only two-arm output. It changes no
Kundur topology, static case, converter/PLL object, model parameter, reference,
threshold, controller, action, learning, or manuscript result.

Pre-seal governance repair: the R390 claim's invalid root locator `/` was
replaced with the existing `/round` field so the repository validator can
resolve it. The statement and scientific evidence are unchanged. The old file
SHA-256 was `ef6902892c09e10c68f7f14c4af5ff1fd1bda01233edbe2138fb3be3912d4b23`;
the corrected SHA-256 is
`d4b3b75ea53ce9a69bf6684dfd080aa611d3d6f626c442e15338d6c5079e2e28`.
R391 freezes the corrected metadata identity before rehearsal; no sealed R390
formal artifact was changed.

## Formal launch contract

- `formal_entry`: `scripts/run_r391_regf2_equilibrium_eig_correction_gate.py`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r391_regf2_equilibrium_eig_correction_gate.py rehearse`
- `rehearsal_scope`: setup-only construction, installed sparse-conversion and
  runtime/API canaries, exact R390/R389 parent-chain and source/case checks,
  output-collision checks, and elapsed/resource capture; no PFlow, TDS
  initialization, EIG calculation, or trajectory.
- `rehearsal_checks`: canonical science-equivalence contract; complete R390
  seal/attempt/execution/analysis/manifest/claim/feed/verdict/diagnosis/audit
  hashes and internal links; transitive R389 chain; installed case/source/API
  identities; real sparse-adapter conversion; exact builder/inventory/cards;
  structural absence; native thread environment; create-only absence; capacity
  and competing-process telemetry.
- `capacity_evidence`: `memory/rounds/R391/capacity_evidence.json`.
- `host_process_budget`: 1 WSL Python formal process.
- `wsl_python_processes`: 1; both arms run serially.
- `native_threads_per_process`: 1 for OpenMP, OpenBLAS, MKL, and NumExpr.
- `other_reserved_processes`: measured immediately before seal and required 0.
- `seal_command`: `/home/wya/andes_venv/bin/python scripts/run_r391_regf2_equilibrium_eig_correction_gate.py prepare`
- `seal_path`: `memory/rounds/R391/formal_seal.json`.
- `formal_execute_command`: from a clean scratch launch directory invoke
  `/home/wya/andes_venv/bin/python /mnt/c/Users/27443/Desktop/andes-rl-kundur/scripts/andes_scratch.py /mnt/c/Users/27443/Desktop/andes-rl-kundur/scripts/run_r391_regf2_equilibrium_eig_correction_gate.py execute --expected-seal-sha256 <sha256>`.
- `formal_output`: create-only
  `results/research_loop/r391_regf2_equilibrium_eig_correction_gate`.
- `completion`: one immutable two-arm execution, analysis, and manifest.
- `monitoring`: inspect once at the rehearsal-derived ETA or terminal artifact.
- `retry`: none automatically; post-seal defects require a successor.

## Cross-references

- Q-0108
- CLM-1090
- CLM-1095
- `paper/converter_vsg_pq_decoupling/working/R390_diagnosis.md`
- `paper/converter_vsg_pq_decoupling/reports/R390.md`
- `paper/converter_vsg_pq_decoupling/working/route_contract.md`
