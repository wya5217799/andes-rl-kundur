# R388 evidence and power-system domain audit

## Coverage and authority

- Scope: `paper/converter_vsg_pq_decoupling/reports/R388.md`, `CLM-1085`,
  `paper/converter_vsg_pq_decoupling/working/R388_diagnosis.md`, the R388
  plan/seal, and all create-only formal result JSON/sidecar artifacts.
- Evidence precedence: formal seal and immutable execution/analysis/manifest;
  prospective plan; strict read-only diagnosis; bounded claim/feed wording.
- Two independent reviews were required. The first reconciled evidence identity
  and every quantitative statement. The second audited power-system model,
  bases, units, action semantics, solver/electrical interpretation, experiment
  design, and claim boundaries.
- External citation, novelty, venue, comparison, and manuscript cross-section
  review are not applicable to this pre-draft model-qualification feed.

## Claim-evidence audit

| ID | Atomic claim | Canonical source and locator | Independent verification | Status |
|---|---|---|---|---|
| E-001 | Corrected formal classification is STOP with record integrity true | `formal_analysis.json#/classification`, `#/checks` | Direct identity and sidecar/hash replay | VERIFIED |
| E-002 | Exact 17-arm bank completed record capture without execution exception | `formal_execution.json#/arms`, `#/trajectory_attempted_count`, `#/trajectory_executed_count`, `#/execution_error` | Recomputed 17, 17, exact order, null error | VERIFIED |
| E-003 | Zero arm completes within all guards; every action arm leaves the envelope | `formal_execution.json#/arms` | Recomputed zero clean and 16/16 action failures | VERIFIED |
| E-004 | Violation counts are 16 voltage, 10 current, 13 apparent power, six speed | `formal_execution.json#/arms/*/trajectory` | Recomputed over explicit initial plus all native samples with frozen limits | VERIFIED |
| E-005 | Eight partial arms end natively nonconverged in the reported range | `formal_execution.json#/arms/*/scientific_error`, `#/solver` | Recomputed count and min/max terminal time | VERIFIED |
| E-006 | All 16 requested/applied writes are exact and isolated | `formal_execution.json#/arms/*/action` | Maximum target/readback/non-target deviation is zero | VERIFIED |
| E-007 | Early target-output sign observations are diagnostic only | `formal_execution.json#/arms/*/trajectory` | Recomputed after zero-arm subtraction at first sample and 0.5 s | QUALIFIED |
| E-008 | Installed equations lack direct same-sign Qref guarantee and registered saturation guards | seal source hash plus installed `regcv1.py` | Source identity/equations inspected; no causal or terminal-sign inference | QUALIFIED |

The initial evidence review required one major wording correction: the early
`Pe/Qe` quantities are zero-arm-subtracted changes, not raw values or the
registered terminal magnitude-floor result. The domain review required the
`Qref` observation to remain diagnostic rather than causal, `kw=0` to be
described as no frequency-droop feedback, and the device-enable `ue` terms to
remain in the equation transcript. Both reviewers approved the corrected text.

## Power-system domain audit

- `0.09` system pu on the 100-MVA base is 9 MW or 9 Mvar and one percent of a
  900-MVA device rating. `Pe/Qe` and `Id/Iq` are interpreted on the system base.
  The apparent-power guard is `900/100=9 pu`; the current guard is
  `(900/100)/0.9=10 pu`.
- Requested setpoint, applied/read-back setpoint, and achieved power are kept
  separate. A correct receipt does not establish a correct physical response.
- The clean zero arm localizes the registered failure to nonzero action under
  the exact card; it does not prove that a particular eigenmode or source term
  causes the excursions.
- Native nonconvergence is preserved rather than censored. Electrical guard
  violation rejects the registered experiment envelope but is not hardware
  safety/protection certification.
- One deterministic bank supports an exact-formulation rejection only. No
  statistical population, robustness, universal converter, or stability-
  theorem claim is made.

**Evidence decision: PASS for the bounded negative feed.**

**Domain decision: PASS for the exact-formulation rejection.**

## Maximum defensible claim

On the exact sealed ANDES 2.0.0, Kundur, four-REGCV1, parameter-card,
operating-point, and 17-arm bank, all direct writes were exact, the zero arm
remained admissible, every nonzero arm violated at least one registered
electrical guard, and eight ended with native nonconvergence. The formulation
therefore fails signed-authority qualification and opens no terminal/paired
authority, P/Q-decoupling, controller, or MARL claim.

## Stay-out boundary

- No universal REGCV1 or converter-class rejection.
- No proved terminal sign failure from early diagnostic checkpoints.
- No certified instability, safety, protection, robustness, topology/VSG-count
  generalization, EMT, HIL, hardware, real-time, field, or deployment claim.
- No deterministic controller or learning experiment is authorized on the
  rejected formulation.
