# R390 strict invalid-result diagnosis

## Scope and authority

R390 is `ANALYSIS-INVALID`. The authoritative analysis records
`arm_integrity=false`; therefore no eigenvalue sign, count, participation, or
mechanism statement may be recovered from the captured matrices. This
diagnosis uses the immutable attempt/execution/analysis/manifest only to locate
the implementation defects. It is not a scientific reanalysis and it does not
authorize an R390 retry.

## Preserved observations

- The manifest binds the attempt, execution, and analysis, and their SHA-256
  sidecars recompute exactly.
- The execution contains two ordered arms, `formal_input_complete=true`, no
  execution or typed scientific error, no action, no training, and no
  trajectory.
- Both arms report completed setup, converged power flow, successful native
  initialization/test, a successful EIG call, zero recorded time/state advance,
  finite reduced matrices, and zero registered initialization residuals.
- Both arms nevertheless record `jacobian_finite=false`; the classifier also
  rejects their registered-state bindings. These are integrity failures, so the
  scientific outcome tree is not entered.

## Root cause 1 — sparse Jacobian adapter

The R390 runner's `_dense_matrix()` accepts objects exposing `.toarray()` and
otherwise calls `numpy.asarray(..., dtype=float)`. Installed ANDES 2.0.0 stores
these Jacobians as `kvxopt.base.spmatrix`, which exposes no compatible direct
NumPy conversion. A source-only library probe reproduces
`TypeError: float() argument must be a string or a real number, not
'kvxopt.base.spmatrix'`; converting first through `andes.shared.matrix` yields a
finite dense array. The repository's existing
`vsg_energy_port_source_adapter._dense_matrix()` already implements this exact
fallback. R390 therefore recorded an adapter failure as a false nonfinite
Jacobian result.

## Root cause 2 — configured index versus ANDES display token

The address chain itself is coherent: every archived binding resolves a model
variable address to the exact DAE state name and then to the same unique
reduced-state name. The classifier adds an incorrect textual assertion that
the configured object index must be a token in that DAE name. For example, the
formal record binds configured index `PLL2_1` to `PI_xi PLL2 1`; installed ANDES
uses the device ordinal `1`, not the configured string `PLL2_1`, in the display
name. The unit fixtures used the latter form and masked the mismatch.

## Rejected alternatives

- **Scientific equilibrium failure**: not established. The formal
  classification stops at record integrity, before the equilibrium or spectrum
  outcome tree.
- **Physical growing mode**: not established. Even if a diagnostic-only replay
  can operate on the serialized matrices, an invalid formal record cannot
  support a mode-sign or stability claim.
- **Topology, converter card, or tolerance change**: not observed. Both defects
  are evidence-adapter/classifier errors; the sealed object and two numerical
  arms were not scientifically modified.

## Smallest successor repair

Any successor must be separately registered, rehearsed, reviewed, and sealed.
It may change only two implementation seams:

1. convert ANDES sparse matrices through the established
   `andes.shared.matrix` fallback before finite-value checks;
2. validate the exact address-to-name-to-reduced-name chain and the frozen
   device ordinal, without requiring the configured index string to occur
   verbatim in the ANDES display name.

The successor must add a real `kvxopt.spmatrix` conversion regression and an
actual ANDES-style `PI_xi PLL2 1` binding regression. It must preserve the R390
scientific object, two-arm order, tolerances, thresholds, no-time-advance rule,
resource budget, and no-action/no-training boundary. R390 itself is not rerun.

