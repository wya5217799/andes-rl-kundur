# U1–U9 complete mathematical resolution package

This package answers every open item in `gpt_pro_unresolved_math_delta_20260821.md` to the strongest level identifiable from the uploaded evidence.

## Main result

- U2–U9 are resolved by explicit propositions, identities, counterexamples, estimands, numerical bounds, and falsifiable verification contracts.
- U1 is sharply delimited rather than fabricated: the shipped artifacts do not contain the complete Object-B sampled input/output model, a verified DCF/SLS map, lifted finite-window response arrays, or an unscaled primal-dual point. Consequently, neither a feasible FIR-Youla witness nor a positive infeasibility certificate is currently identifiable. The report supplies a precisely named 10-tap class, exact conic formulation, nonconvex saturation boundary, certificate checker contract, and the minimum computation needed to close it.
- The source package integrity was checked against all 1,554 `SHA256SUMS` entries with zero failures.

## Files

- `00_problem_brief_snapshot.md` — exact U1–U9 delta brief supplied in the input package.
- `01_complete_solution.md` — full Chinese mathematical solution, proofs, dimensions, units, signs, evidence paths, algorithms, falsification experiments, paper-safe wording, prohibited wording, and final summary table.
- `02_paper_ready_wording.md` — bounded English paragraphs ready to adapt into the manuscript.
- `03_source_map.md` — exact source files/fields and unresolved quantities.
- `machine_checks/verify_solution.py` — integrity and numerical recomputation.
- `machine_checks/derived_results.json` — generated decision-bearing values.
- `machine_checks/math_blueprints.py` — reusable implementations for slew semantics, fractional ZOH delay, total transfer sensitivity, mixed tensors, and commutator checks.
- `machine_checks/test_blueprints.py` — self-contained tests; all pass in the delivery environment.
- `SHA256SUMS` — hashes of this solution package.

## Recommended reading order

Read `01_complete_solution.md` first. For manuscript insertion, use `02_paper_ready_wording.md`. Before relying on a recomputed number, run the two commands in `machine_checks/README.md` against the original evidence package.

## Scope

No R458 outcome is predicted. No missing plant matrix, trajectory, uncertainty norm, or nonlinear remainder was invented. The conclusions do not authorize universal controller impossibility, successful MARL, topology generalization, stability, safety, HIL/EMT, or deployment claims.
