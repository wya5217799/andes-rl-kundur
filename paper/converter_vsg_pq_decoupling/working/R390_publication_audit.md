# R390 publication audit

## Coverage and authority

Scope: `paper/converter_vsg_pq_decoupling/reports/R390.md`,
`paper/converter_vsg_pq_decoupling/working/R390_diagnosis.md`,
`memory/claims/CLM-1095.md`, and `memory/rounds/R390/verdict.md`.

Authority order: immutable formal analysis and execution; formal manifest and
seal; registered claim and verdict; diagnosis; feed prose. The formal analysis
is `ANALYSIS-INVALID`, so captured matrix values cannot support a scientific
claim.

## Evidence audit

| ID | Atomic claim | Canonical source and locator | Verification | Status |
|---|---|---|---|---|
| E-001 | R390 is analysis-invalid | `formal_analysis.json#/classification` and `#/checks/arm_integrity` | `ANALYSIS-INVALID`; `false` | VERIFIED |
| E-002 | The invalid record contains two ordered arms and no trajectory/action/training | `formal_execution.json#/arms`, `#/trajectory_count`, `#/post_init_action_executed`, `#/training_executed` | two arms; zero; false; false | VERIFIED |
| E-003 | Formal artifacts remain bound | `formal_manifest.json#/entries` plus SHA-256 sidecars | all attempt/execution/analysis hashes recompute exactly | VERIFIED |
| E-004 | Direct sparse-to-NumPy conversion is the Jacobian-status defect | R390 runner `_dense_matrix`; installed `kvxopt.base.spmatrix`; established source-adapter fallback | direct conversion raises `TypeError`; `andes.shared.matrix` conversion is finite | VERIFIED as implementation diagnosis only |
| E-005 | Configured-index text caused state-binding rejection | `formal_execution.json#/arms/0/matrix/state_bindings/0`; classifier token condition | archived `idx=PLL2_1`, `dae_name=PI_xi PLL2 1`, with exact original/reduced address binding | VERIFIED as implementation diagnosis only |
| E-006 | The object has or lacks a positive-real direction | no valid formal outcome | integrity failure precedes the scientific outcome tree | CONFLICTED; excluded |

No unresolved evidence artifact remains for the allowed invalid-attempt claim.
The feed inventory and `feed_check.py` complete successfully. Claim, verdict,
feed, and diagnosis use the same invalid boundary and keep Q-0108 unresolved.

**Evidence decision: PASS** for the bounded invalid-attempt statement only.

## Power-systems domain audit

- The sealed object remains the exact R389 phasor-domain Kundur/REGF2/PLL2
  object; no topology, operating-point, converter-card, or actuator change is
  claimed.
- No time-domain trajectory, disturbance, control action, or training is
  reported as executed.
- No equilibrium-validity, eigenvalue-sign, participation, local small-signal
  stability, transient stability, safety, robustness, topology-generalization,
  hardware, or deployment inference is made.
- The two identified causes are code/evidence-interface defects. They are not
  described as converter dynamics, physical instability, or a numerical mode.
- Any successor is required to preserve the scientific contract and obtain a
  fresh prospective seal.

**Domain decision: DOMAIN PASS**. Presentation, citation, and journal-package
checks are not applicable to this local invalid-result feed.

## Maximum defensible claim

R390 is a sealed, complete but analysis-invalid two-arm no-trajectory attempt;
two implementation integrity defects were diagnosed. It provides no valid
equilibrium or reduced-spectrum result, leaves Q-0108 unresolved, and
authorizes no retry or downstream work.

